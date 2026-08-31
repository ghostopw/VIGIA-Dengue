"""VIGIA-Dengue -- painel de alerta precoce para o DF e a RIDE-DF.

Execucao:  streamlit run app/painel.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_PAINEL = RAIZ / "dados" / "processado" / "painel.csv"
CAMINHO_MALHA = RAIZ / "dados" / "externo" / "malha_ride_df.geojson"
CAMINHO_MALHA_RAS = RAIZ / "dados" / "externo" / "malha_ras_df.geojson"
CAMINHO_DESEMPENHO = RAIZ / "saidas" / "desempenho_modelos.csv"

# Paleta do painel VIGIA-Dengue (sistema "Industry"), a mesma do canvas em
# `Painel VIGIA-Dengue (offline).html`, para que as duas telas se leiam como
# uma coisa so. As rampas foram geradas em OKLCH sobre uma escala de
# luminosidade compartilhada.
ACENTO = "#5980a6"
ACENTO_200 = "#d6ebff"
ACENTO_200_T = "rgba(214,235,255,0.75)"  # a mesma opacidade do canvas
ACENTO_800 = "#2c455d"
NEUTRO_500 = "#98989b"
NEUTRO_600 = "#7a7a7d"
TEXTO = "#1d1f20"
DIVISOR = "rgba(29,31,32,0.16)"

FONTE_CORPO = "Barlow, system-ui, -apple-system, sans-serif"

# Rampa sequencial de 9 passos, usada nos mapas por intensidade.
RAMPA = ["#eef6ff", "#d6ebff", "#b5d9fd", "#94bce3",
         "#749dc4", "#597ea3", "#416180", "#2c455d", "#1d2d3d"]

# Niveis de risco: tres passos do azul e um terracota so no topo, para que
# "muito alto" seja o unico ponto quente da tela.
CORES_RISCO = {
    "baixo": "#94bce3",
    "moderado": "#597ea3",
    "alto": "#2c455d",
    "muito alto": "#a2402f",
}
ORDEM_RISCO = ["baixo", "moderado", "alto", "muito alto"]

# Regra de leitura herdada do painel: a serie em foco vai solida no azul
# escuro; as de comparacao vao neutras e tracejadas, para nao disputar.
CORES_MODELO = ["#b7b7ba", "#749dc4", "#1d2d3d"]

# Municipio foco do projeto. A RIDE-DF entra como territorio de comparacao.
FOCO = "Brasilia"
COD_FOCO = 5300108

st.set_page_config(page_title="VIGIA-Dengue", page_icon="\U0001F99F", layout="wide")

# Um gabarito unico evita repetir fonte e fundo em cada figura. O fundo
# transparente deixa o grafico assentar sobre a superficie do tema.
pio.templates["vigia"] = go.layout.Template(layout={
    "font": {"family": FONTE_CORPO, "color": TEXTO, "size": 13},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "colorway": [ACENTO_800, NEUTRO_600, ACENTO, "#a2402f"],
    "xaxis": {"gridcolor": DIVISOR, "linecolor": DIVISOR, "zeroline": False},
    "yaxis": {"gridcolor": DIVISOR, "linecolor": DIVISOR, "zeroline": False},
    "legend": {"font": {"size": 12}},
})
pio.templates.default = "plotly_white+vigia"

# Barlow e a tipografia do painel; sem rede, cai no fallback do sistema.
st.markdown(
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Barlow+Condensed:wght@600&family=Barlow:wght@400;500;600'
    '&display=swap">'
    """<style>
      html, body, [class*="css"] { font-family: "Barlow", system-ui, sans-serif; }
      h1, h2, h3, h4 { font-family: "Barlow Condensed", "Arial Narrow", sans-serif;
                       font-weight: 600; letter-spacing: 0.2px; }
    </style>""",
    unsafe_allow_html=True,
)


@st.cache_data
def carregar_painel() -> pd.DataFrame:
    dados = pd.read_csv(CAMINHO_PAINEL, parse_dates=["data_ini_se"])
    dados["risco"] = pd.Categorical(dados["risco"], categories=ORDEM_RISCO, ordered=True)

    # O InfoDengue deixa o limite do nowcasting vazio em algumas semanas. Sem
    # esse tratamento o preenchimento entre as duas curvas atravessa a lacuna
    # e desenha uma cunha que nao existe no dado; encostando a faixa na linha,
    # a ausencia de intervalo aparece como ausencia de faixa.
    for extremo in ("casos_est_min", "casos_est_max"):
        dados[extremo] = dados[extremo].fillna(dados["casos_est"])
    return dados


@st.cache_data
def carregar_malha() -> dict:
    return json.loads(CAMINHO_MALHA.read_text(encoding="utf-8"))


@st.cache_data
def carregar_malha_ras() -> dict | None:
    """Malha das 31 Regioes Administrativas do DF, se ja tiver sido gerada."""
    if CAMINHO_MALHA_RAS.exists():
        return json.loads(CAMINHO_MALHA_RAS.read_text(encoding="utf-8"))
    return None


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
    "Distrito Federal, com a RIDE-DF como territorio de comparacao"
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

    # Brasilia e o foco do projeto: concentra 69% da populacao e 63% dos casos
    # do territorio, por isso abre selecionada em vez de ordem alfabetica.
    outros = sorted(m for m in painel["municipio"].dropna().unique() if m != FOCO)
    municipios = [FOCO, "(territorio inteiro)"] + outros
    municipio_escolhido = st.selectbox("Municipio em detalhe", municipios, index=0)

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

# ------------------------------------------------- situacao de Brasilia (foco)
foco = semana_atual[semana_atual["cod_ibge"] == COD_FOCO]

st.subheader(f"Brasilia -- semana {formatar_semana(semana_escolhida)}")

if foco.empty:
    st.warning("Sem dado de Brasilia nesta semana.")
else:
    linha = foco.iloc[0]
    anterior = painel[
        (painel["cod_ibge"] == COD_FOCO) & (painel["se_codigo"] < semana_escolhida)
    ].sort_values("se_codigo")

    col1, col2, col3, col4 = st.columns(4)

    variacao = None
    if not anterior.empty:
        casos_antes = anterior["casos_est"].iloc[-1]
        if casos_antes:
            variacao = (linha["casos_est"] - casos_antes) / casos_antes * 100

    col1.metric(
        "Casos estimados",
        f"{linha['casos_est']:,.0f}".replace(",", "."),
        delta=None if variacao is None else f"{variacao:+.0f}% vs semana anterior",
        delta_color="inverse",
    )
    col2.metric(
        "Incidencia / 100 mil",
        f"{linha['incidencia_100k']:.1f}",
        help="Calculada sobre casos estimados, que corrigem o atraso de notificacao.",
    )
    col3.metric("Nivel de risco", str(linha["risco"]).capitalize())
    col4.metric(
        f"Prob. de alerta em {horizonte} semanas",
        f"{linha['probabilidade_alerta']:.0%}",
        help=f"Limiar configurado: {limiar:.0%}.",
    )

    if linha["probabilidade_alerta"] >= limiar:
        st.error(
            f"**Brasilia em alerta.** Probabilidade de {linha['probabilidade_alerta']:.0%} "
            f"de risco alto ou muito alto em {horizonte} semanas. "
            f"Principais fatores: {linha['fatores_alerta']}."
        )

    if sinalizar_provisorio and linha["dado_provisorio"] == 1:
        st.warning(
            f"Notificacao ainda incompleta em Brasilia nesta semana "
            f"({linha['completude']:.0%} digitado). Os casos observados tendem a subir."
        )

# ------------------------------------------------- contexto da RIDE (comparacao)
resto = semana_atual[semana_atual["cod_ibge"] != COD_FOCO]
with st.expander(
    f"Contexto da RIDE-DF -- {len(resto)} municipios do Entorno", expanded=False
):
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Casos estimados no Entorno",
        f"{resto['casos_est'].sum():,.0f}".replace(",", "."),
    )
    col2.metric(
        "Municipios em risco alto/muito alto",
        int((resto["risco_codigo"] >= 2).sum()),
        help=f"De {len(resto)} municipios do Entorno.",
    )
    col3.metric(
        f"Em alerta para {horizonte} semanas",
        int(resto["em_alerta"].sum()),
    )

    incompletos = resto.loc[resto["dado_provisorio"] == 1, "municipio"].tolist()
    if sinalizar_provisorio and incompletos:
        st.caption(
            "Notificacao ainda incompleta em: " + ", ".join(incompletos) + "."
        )
    st.caption(
        "O Entorno acompanha Brasilia pelo pendularismo diario: a circulacao viral "
        "atravessa a fronteira do DF nos dois sentidos."
    )

aba_mapa, aba_ras, aba_serie, aba_ranking, aba_modelo = st.tabs(
    ["Mapa de risco", "Brasilia por Regiao Administrativa", "Series temporais",
     "Ranking e relatorio", "Desempenho do modelo"]
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

# ------------------------------------------- Brasilia por Regiao Administrativa
with aba_ras:
    malha_ras = carregar_malha_ras()

    if malha_ras is None:
        st.warning(
            "Malha das Regioes Administrativas ausente. "
            "Execute `python src/vigia/executar_ras.py` para gera-la."
        )
    else:
        st.subheader("Estrutura territorial do Distrito Federal")
        st.caption(
            "As 31 Regioes Administrativas com geometria disponivel. Brasilia e um "
            "unico municipio na malha do IBGE, e esta camada mostra a divisao "
            "intraurbana que o dado municipal nao alcanca."
        )

        regioes = pd.DataFrame([
            feicao["properties"] for feicao in malha_ras["features"]
        ])
        regioes["populacao"] = pd.to_numeric(regioes["populacao"], errors="coerce")

        indicador = st.radio(
            "Indicador exibido no mapa",
            ["Populacao", "Densidade demografica"],
            horizontal=True,
        )

        if indicador == "Densidade demografica" and "densidade_hab_km2" in regioes:
            coluna, rotulo = "densidade_hab_km2", "hab./km2"
        else:
            coluna, rotulo = "populacao", "habitantes"

        mapa_ras = px.choropleth_map(
            regioes,
            geojson=malha_ras,
            locations="ra_nome",
            featureidkey="properties.ra_nome",
            color=coluna,
            color_continuous_scale=RAMPA,
            map_style="carto-positron",
            zoom=8.2,
            center={"lat": -15.78, "lon": -47.93},
            opacity=0.75,
            labels={coluna: rotulo},
            hover_data={"ra_nome": True, coluna: ":,.0f"},
        )
        mapa_ras.update_layout(height=560, margin={"r": 0, "t": 0, "l": 0, "b": 0})
        st.plotly_chart(mapa_ras, width="stretch")

        st.dataframe(
            regioes.sort_values("populacao", ascending=False)[
                [c for c in ("ra_nome", "populacao", "cod_subdistrito") if c in regioes]
            ].rename(columns={
                "ra_nome": "Regiao Administrativa",
                "populacao": "Populacao (PDAD 2021)",
                "cod_subdistrito": "Codigo IBGE (subdistrito)",
            }),
            hide_index=True, width="stretch", height=320,
        )

        st.info(
            "**Por que este mapa nao mostra casos de dengue.** Nao ha fonte publica "
            "com serie semanal de casos por Regiao Administrativa: o InfoDengue opera "
            "apenas no nivel municipal, o painel de incidencia da SES-DF nao expoe "
            "dados de forma programatica, o LIRAa e publicado como relatorio fechado "
            "e os microdados do SINAN dependem do FTP do DATASUS. Repartir os casos do "
            "DF entre as RAs na proporcao da populacao produziria um mapa apenas "
            "aparentemente informativo, que reproduziria o mapa populacional e "
            "esconderia a desigualdade intraurbana real. Obtida a serie por RA junto "
            "a SES-DF, ela se acopla a esta malha pelo nome da regiao."
        )


# -------------------------------------------------------------- series temporais
with aba_serie:
    if municipio_escolhido == "(territorio inteiro)":
        # Serie agregada: casos somados, incidencia recalculada sobre a
        # populacao total (a media simples entre municipios distorceria).
        serie = (
            painel.groupby(["se_codigo", "data_ini_se"], as_index=False)
            .agg({
                "casos": "sum", "casos_est": "sum",
                "casos_est_min": "sum", "casos_est_max": "sum",
                "pop": "sum", "canal_q3": "mean",
            })
            .sort_values("data_ini_se")
        )
        serie["incidencia_100k"] = serie["casos_est"] / serie["pop"] * 1e5
        alvo = "Territorio inteiro (DF + RIDE)"
    else:
        alvo = municipio_escolhido
        serie = painel[painel["municipio"] == alvo].sort_values("data_ini_se")

    st.caption(f"Serie de **{alvo}**.")

    figura = go.Figure()
    figura.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["casos_est_max"],
        line={"width": 0}, showlegend=False, hoverinfo="skip",
    ))
    figura.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["casos_est_min"],
        fill="tonexty", fillcolor=ACENTO_200_T,
        line={"width": 0}, name="Intervalo do nowcasting", hoverinfo="skip",
    ))
    figura.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["casos_est"],
        name="Casos estimados", line={"color": ACENTO_800, "width": 2},
    ))
    figura.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["casos"],
        name="Casos notificados",
        line={"color": NEUTRO_600, "width": 1, "dash": "dash"},
    ))
    marcador = serie.loc[serie["se_codigo"] == semana_escolhida, "data_ini_se"]
    if not marcador.empty:
        figura.add_vline(x=marcador.iloc[0], line_dash="dash", line_color=ACENTO)
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
        line={"color": NEUTRO_500, "dash": "dash"},
    ))
    canal.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["incidencia_100k"],
        name="Incidencia por 100 mil", line={"color": ACENTO_800, "width": 2},
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

    # Comparacao Brasilia x Entorno: mostra se o sinal do DF antecede, acompanha
    # ou segue o do Entorno -- leitura util para a vigilancia do pendularismo.
    st.subheader("Brasilia frente ao Entorno")
    agrupado = painel.assign(
        grupo=lambda d: d["cod_ibge"].map(
            lambda c: "Brasilia" if c == COD_FOCO else "Entorno (RIDE)"
        )
    )
    comparacao = (
        agrupado.groupby(["grupo", "data_ini_se"], as_index=False)
        .agg({"casos_est": "sum", "pop": "sum"})
    )
    comparacao["incidencia_100k"] = comparacao["casos_est"] / comparacao["pop"] * 1e5

    figura_comparacao = px.line(
        comparacao, x="data_ini_se", y="incidencia_100k", color="grupo",
        color_discrete_map={"Brasilia": ACENTO_800, "Entorno (RIDE)": NEUTRO_600},
        line_dash="grupo",
        line_dash_map={"Brasilia": "solid", "Entorno (RIDE)": "dash"},
        labels={
            "incidencia_100k": "Incidencia / 100 mil",
            "data_ini_se": "Semana",
            "grupo": "Grupo",
        },
    )
    figura_comparacao.update_layout(
        height=320, margin={"t": 20},
        xaxis_title=None,
        legend={"orientation": "h", "y": 1.15, "title_text": ""},
    )
    st.plotly_chart(figura_comparacao, width="stretch")
    st.caption(
        "Incidencia padronizada pela populacao de cada grupo, o que torna as duas "
        "curvas comparaveis apesar da diferenca de porte."
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

    # Posicao de Brasilia no ranking, para nao se perder entre os 33 municipios.
    posicao = tabela.reset_index(drop=True).index[tabela["municipio"].values == FOCO]
    if len(posicao):
        st.info(
            f"**Brasilia** ocupa a posicao **{int(posicao[0]) + 1} de {len(tabela)}** "
            "no ranking de probabilidade de alerta desta semana."
        )

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
            color_discrete_sequence=CORES_MODELO,
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
