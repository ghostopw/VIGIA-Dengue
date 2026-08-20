"""VIGIA-Dengue -- painel de alerta precoce para o DF e a RIDE-DF.

Execucao:  streamlit run app/painel.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_PAINEL = RAIZ / "dados" / "processado" / "painel.csv"
CAMINHO_MALHA = RAIZ / "dados" / "externo" / "malha_ride_df.geojson"
CAMINHO_DESEMPENHO = RAIZ / "saidas" / "desempenho_modelos.csv"

CORES_RISCO = {
    "baixo": "#2E7D32",
    "moderado": "#F9A825",
    "alto": "#EF6C00",
    "muito alto": "#C62828",
}
ORDEM_RISCO = ["baixo", "moderado", "alto", "muito alto"]

st.set_page_config(page_title="VIGIA-Dengue", page_icon="\U0001F99F", layout="wide")


@st.cache_data
def carregar_painel() -> pd.DataFrame:
    dados = pd.read_csv(CAMINHO_PAINEL, parse_dates=["data_ini_se"])
    dados["risco"] = pd.Categorical(dados["risco"], categories=ORDEM_RISCO, ordered=True)
    return dados


@st.cache_data
def carregar_malha() -> dict:
    return json.loads(CAMINHO_MALHA.read_text(encoding="utf-8"))


@st.cache_data
def carregar_desempenho():
    if CAMINHO_DESEMPENHO.exists():
        return pd.read_csv(CAMINHO_DESEMPENHO)
    return None


def formatar_semana(codigo: int) -> str:
    return f"{int(codigo) % 100:02d}/{int(codigo) // 100}"


painel = carregar_painel()
malha = carregar_malha()

st.title("VIGIA-Dengue")
st.caption(
    "Alerta precoce e estratificacao espaco-temporal do risco de dengue -- "
    "Distrito Federal e RIDE-DF"
)

# ---------------------------------------------------------------- barra lateral
with st.sidebar:
    st.header("Filtros")

    semanas = sorted(painel["se_codigo"].unique())
    semana_escolhida = st.select_slider(
        "Semana epidemiologica",
        options=semanas,
        value=semanas[-1],
        format_func=formatar_semana,
    )

    municipios = ["(todos)"] + sorted(painel["municipio"].dropna().unique())
    municipio_escolhido = st.selectbox("Municipio", municipios)

    limiar = st.slider(
        "Limiar de probabilidade para o alerta",
        min_value=0.05, max_value=0.95, value=0.50, step=0.05,
        help="Probabilidade acima da qual o municipio entra em alerta.",
    )

    sinalizar_provisorio = st.checkbox(
        "Sinalizar semanas com notificacao incompleta", value=True
    )

    st.divider()
    horizonte = int(painel["horizonte_semanas"].iloc[0])
    st.info(
        f"O alerta projeta o risco **{horizonte} semanas a frente**. "
        "Os casos estimados corrigem o atraso de notificacao."
    )

semana_atual = painel[painel["se_codigo"] == semana_escolhida].copy()
semana_atual["em_alerta"] = semana_atual["probabilidade_alerta"] >= limiar

# ------------------------------------------------------------------- indicadores
col1, col2, col3, col4 = st.columns(4)
col1.metric("Semana epidemiologica", formatar_semana(semana_escolhida))
col2.metric(
    "Casos estimados no territorio",
    f"{semana_atual['casos_est'].sum():,.0f}".replace(",", "."),
)
col3.metric(
    "Municipios em risco alto/muito alto",
    int((semana_atual["risco_codigo"] >= 2).sum()),
    help=f"De {len(semana_atual)} municipios com dado na semana.",
)
col4.metric(
    f"Em alerta para {horizonte} semanas a frente",
    int(semana_atual["em_alerta"].sum()),
    help=f"Probabilidade prevista maior ou igual a {limiar:.0%}.",
)

if sinalizar_provisorio and semana_atual["dado_provisorio"].sum():
    incompletos = semana_atual.loc[semana_atual["dado_provisorio"] == 1, "municipio"].tolist()
    st.warning(
        "Notificacao ainda incompleta nesta semana em: "
        + ", ".join(incompletos)
        + ". Os casos observados tendem a subir com a digitacao retroativa."
    )

aba_mapa, aba_serie, aba_ranking, aba_modelo = st.tabs(
    ["Mapa de risco", "Series temporais", "Ranking e relatorio", "Desempenho do modelo"]
)

# ------------------------------------------------------------------------ mapa
with aba_mapa:
    esquerda, direita = st.columns([3, 2])

    with esquerda:
        mapa = px.choropleth_map(
            semana_atual,
            geojson=malha,
            locations="cod_ibge",
            featureidkey="properties.cod_ibge",
            color="risco",
            color_discrete_map=CORES_RISCO,
            category_orders={"risco": ORDEM_RISCO},
            hover_name="municipio",
            hover_data={
                "cod_ibge": False,
                "casos_est": ":.0f",
                "incidencia_100k": ":.1f",
                "probabilidade_alerta": ":.0%",
            },
            center={"lat": -15.8, "lon": -47.6},
            zoom=6.2,
            map_style="carto-positron",
            opacity=0.75,
            height=560,
        )
        mapa.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, legend_title="Risco")
        st.plotly_chart(mapa, width="stretch")

    with direita:
        st.subheader("Distribuicao dos niveis")
        contagem = (
            semana_atual["risco"].value_counts().reindex(ORDEM_RISCO).fillna(0).reset_index()
        )
        contagem.columns = ["risco", "municipios"]
        barras = px.bar(
            contagem, x="municipios", y="risco", orientation="h",
            color="risco", color_discrete_map=CORES_RISCO,
            category_orders={"risco": ORDEM_RISCO},
        )
        barras.update_layout(showlegend=False, height=240, margin={"t": 10, "b": 10})
        st.plotly_chart(barras, width="stretch")

        st.subheader("Maiores probabilidades de alerta")
        topo = semana_atual.nlargest(6, "probabilidade_alerta")[
            ["municipio", "probabilidade_alerta", "risco"]
        ].copy()
        topo["probabilidade_alerta"] = topo["probabilidade_alerta"].map("{:.0%}".format)
        st.dataframe(
            topo.rename(columns={
                "municipio": "Municipio",
                "probabilidade_alerta": "Prob.",
                "risco": "Risco atual",
            }),
            hide_index=True, width="stretch",
        )

# -------------------------------------------------------------- series temporais
with aba_serie:
    if municipio_escolhido != "(todos)":
        alvo = municipio_escolhido
    else:
        alvo = semana_atual.nlargest(1, "casos_est")["municipio"].iloc[0]
        st.caption(f"Nenhum municipio selecionado: exibindo **{alvo}** (maior volume na semana).")

    serie = painel[painel["municipio"] == alvo].sort_values("data_ini_se")

    figura = go.Figure()
    figura.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["casos_est_max"],
        line={"width": 0}, showlegend=False, hoverinfo="skip",
    ))
    figura.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["casos_est_min"],
        fill="tonexty", fillcolor="rgba(198,40,40,0.15)",
        line={"width": 0}, name="Intervalo do nowcasting", hoverinfo="skip",
    ))
    figura.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["casos_est"],
        name="Casos estimados", line={"color": "#C62828", "width": 2},
    ))
    figura.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["casos"],
        name="Casos notificados", line={"color": "#546E7A", "width": 1, "dash": "dot"},
    ))
    marcador = serie.loc[serie["se_codigo"] == semana_escolhida, "data_ini_se"]
    if not marcador.empty:
        figura.add_vline(x=marcador.iloc[0], line_dash="dash", line_color="#37474F")
    figura.update_layout(
        height=380, margin={"t": 30},
        yaxis_title="Casos por semana", xaxis_title=None,
        legend={"orientation": "h", "y": 1.12},
    )
    st.plotly_chart(figura, width="stretch")

    canal = go.Figure()
    canal.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["canal_q3"],
        name="Limite esperado (Q3 historico)",
        line={"color": "#F9A825", "dash": "dash"},
    ))
    canal.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["incidencia_100k"],
        name="Incidencia por 100 mil", line={"color": "#1565C0", "width": 2},
    ))
    canal.update_layout(
        height=300, margin={"t": 30},
        yaxis_title="Incidencia / 100 mil hab.",
        legend={"orientation": "h", "y": 1.15},
    )
    st.plotly_chart(canal, width="stretch")
    st.caption(
        "Incidencia acima do limite esperado indica atividade acima do padrao "
        "historico daquela semana do ano no municipio (canal endemico)."
    )

# ------------------------------------------------------------ ranking e relatorio
with aba_ranking:
    tabela = semana_atual.sort_values("probabilidade_alerta", ascending=False)[
        ["municipio", "uf", "casos", "casos_est", "incidencia_100k", "risco",
         "probabilidade_alerta", "fatores_alerta", "dado_provisorio"]
    ].copy()
    tabela["probabilidade_alerta"] = tabela["probabilidade_alerta"].round(3)
    tabela["incidencia_100k"] = tabela["incidencia_100k"].round(1)
    tabela["dado_provisorio"] = tabela["dado_provisorio"].map({1: "sim", 0: "nao"})

    st.dataframe(
        tabela.rename(columns={
            "municipio": "Municipio", "uf": "UF", "casos": "Casos notificados",
            "casos_est": "Casos estimados", "incidencia_100k": "Incid./100mil",
            "risco": "Risco", "probabilidade_alerta": "Prob. alerta",
            "fatores_alerta": "Principais fatores", "dado_provisorio": "Provisorio",
        }),
        hide_index=True, width="stretch", height=460,
    )

    st.download_button(
        "Baixar relatorio da semana (CSV)",
        data=tabela.to_csv(index=False).encode("utf-8"),
        file_name=f"vigia_dengue_SE{semana_escolhida}.csv",
        mime="text/csv",
    )

# ------------------------------------------------------------ desempenho do modelo
with aba_modelo:
    desempenho = carregar_desempenho()
    if desempenho is None:
        st.info("Execute a validacao temporal para preencher esta aba.")
    else:
        st.subheader("Validacao temporal em janela expansiva")
        st.caption(
            "Cada ano e previsto por um modelo treinado apenas com os anos "
            "anteriores. Nenhuma informacao do futuro entra no treino."
        )
        medias = desempenho.groupby("modelo")[
            ["sensibilidade", "especificidade", "vpp", "auc", "auprc", "brier"]
        ].mean().round(3).reset_index()
        st.dataframe(
            medias.rename(columns={
                "modelo": "Modelo", "sensibilidade": "Sensibilidade",
                "especificidade": "Especificidade", "vpp": "VPP",
                "auc": "AUC", "auprc": "AUPRC", "brier": "Brier",
            }),
            hide_index=True, width="stretch",
        )

        linha_auc = px.line(
            desempenho, x="ano", y="auc", color="modelo", markers=True,
            labels={"auc": "AUC", "ano": "Ano avaliado", "modelo": "Modelo"},
        )
        linha_auc.update_layout(height=360)
        st.plotly_chart(linha_auc, width="stretch")

st.divider()
st.caption(
    "Fontes: InfoDengue (Fiocruz/FGV) para casos e clima; IBGE para populacao e "
    "malha municipal. Ferramenta de apoio a vigilancia -- nao substitui a "
    "analise da equipe de vigilancia epidemiologica local."
)
