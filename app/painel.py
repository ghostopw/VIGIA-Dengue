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
CAMINHO_MALHA_RAS = RAIZ / "dados" / "externo" / "malha_ras_df.geojson"
CAMINHO_DESEMPENHO = RAIZ / "saidas" / "desempenho_modelos.csv"
CAMINHO_ALERTA = RAIZ / "saidas" / "alerta.json"

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

# Rampa sequencial de 9 passos, na familia azul do sistema.
RAMPA = ["#eef6ff", "#d6ebff", "#b5d9fd", "#94bce3",
         "#749dc4", "#597ea3", "#416180", "#2c455d", "#1d2d3d"]

# Rampa do mapa territorial, no terracota do sistema -- o mesmo tom de "risco
# muito alto". No azul, os poligonos disputavam com o mapa base cinza-azulado e
# com o resto da interface; o tom quente se descola dos dois.
#
# Foi gerada em OKLCH sobre a MESMA escala de luminosidade da rampa azul, passo
# a passo, de modo que as duas se equivalham em valor. O croma acompanha o do
# azul multiplicado por 1,7, que e quanto o vermelho-alaranjado comporta a mais
# na mesma luminosidade antes de sair do sRGB.
RAMPA_TERRITORIO = ["#fef4f1", "#fde3dd", "#fec5b9", "#f79781",
                    "#da7967", "#b45b4a", "#904436", "#6a2d22", "#451e17"]

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


# O cache expira em 10 minutos. Sem prazo, o painel serviria a mesma tabela ate
# alguem reiniciar o processo -- e o ciclo de atualizacao pode ter trazido uma
# semana nova nesse meio-tempo.
@st.cache_data(ttl=600)
def carregar_alerta() -> dict | None:
    """Estado deixado pelo ultimo ciclo de `executar_atualizacao.py`."""
    if CAMINHO_ALERTA.exists():
        return json.loads(CAMINHO_ALERTA.read_text(encoding="utf-8"))
    return None


@st.cache_data(ttl=600)
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


def formatar_milhar(valor: float) -> str:
    """Numero curto para rotulo de legenda: 348000 vira "348 mil"."""
    if valor >= 1000:
        return f"{valor / 1000:.0f} mil"
    return f"{valor:.0f}"


def _aneis(geometria: dict) -> list[list]:
    """Todos os aneis externos da geometria, seja Polygon ou MultiPolygon."""
    coordenadas = geometria["coordinates"]
    if geometria["type"] == "Polygon":
        return [coordenadas[0]]
    return [parte[0] for parte in coordenadas]


def _centro_do_anel(anel: list) -> tuple[float, float, float]:
    """Centroide de area e area assinada de um anel, pela formula do sapateiro."""
    soma = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(anel, anel[1:] + anel[:1]):
        cruzado = x1 * y2 - x2 * y1
        soma += cruzado
        cx += (x1 + x2) * cruzado
        cy += (y1 + y2) * cruzado
    if soma == 0:
        return anel[0][1], anel[0][0], 0.0
    area = soma / 2
    return cy / (3 * soma), cx / (3 * soma), abs(area)


def centroides_ras(malha: dict) -> dict[str, tuple[float, float]]:
    """Ponto para ancorar o nome de cada RA.

    Usa o centroide de area do maior anel, e nao o centro da caixa envolvente:
    em regiao alongada ou recortada -- o Lago Norte contornando o lago, por
    exemplo -- o centro da caixa cai fora do proprio poligono, e o nome flutua
    sobre a vizinha.
    """
    centros: dict[str, tuple[float, float]] = {}
    for feicao in malha["features"]:
        candidatos = [_centro_do_anel(anel) for anel in _aneis(feicao["geometry"])]
        latitude, longitude, _ = max(candidatos, key=lambda c: c[2])
        centros[feicao["properties"]["ra_nome"]] = (latitude, longitude)
    return centros


def desempilhar(nomes: list[str], centros: dict, distancia: float = 0.07) -> list[str]:
    """Descarta rotulos que cairiam em cima de outro ja colocado.

    Percorre na ordem recebida -- as maiores primeiro -- e so aceita um nome se
    ele estiver a mais de `distancia` grau de todos os aceitos. Sem isso a
    conurbacao central vira uma pilha de nomes sobrepostos, que e pior do que
    nome nenhum.
    """
    aceitos: list[str] = []
    postos: list[tuple[float, float]] = []
    for nome in nomes:
        latitude, longitude = centros[nome]
        if all((latitude - la) ** 2 + (longitude - lo) ** 2 > distancia ** 2
               for la, lo in postos):
            aceitos.append(nome)
            postos.append((latitude, longitude))
    return aceitos


def formatar_semana(codigo: int) -> str:
    return f"{int(codigo) % 100:02d}/{int(codigo) // 100}"


painel = carregar_painel()

st.title("VIGIA-Dengue")
st.caption(
    "Alerta precoce do risco de dengue em Brasilia e nas suas Regioes "
    "Administrativas -- as cidades satelites do Distrito Federal"
)

# ----------------------------------------------------------- estado da coleta
# Um painel de alerta precisa dizer de quando e o dado que mostra. Sem isso
# nao da para distinguir "esta calmo" de "ninguem atualizou".
estado_alerta = carregar_alerta()
ultima_semana = int(painel[painel["cod_ibge"] == COD_FOCO]["se_codigo"].max())

if estado_alerta is None:
    st.warning(
        f"Dado ate a semana **{formatar_semana(ultima_semana)}**. O ciclo de "
        "atualizacao nunca rodou: execute `python src/vigia/executar_atualizacao.py` "
        "para o painel passar a acompanhar o InfoDengue sozinho."
    )
else:
    verificado = pd.to_datetime(estado_alerta["estado"]["verificado_em"])
    horas = (pd.Timestamp.now(tz="UTC") - verificado).total_seconds() / 3600
    quando = (f"ha {horas * 60:.0f} min" if horas < 1
              else f"ha {horas:.0f} h" if horas < 48
              else f"em {verificado.tz_convert(None):%d/%m}")
    recado = (
        f"Dado do InfoDengue ate a semana **{formatar_semana(ultima_semana)}** - "
        f"fonte verificada {quando}."
    )
    # Mais de tres dias sem verificar ja e sinal de que o agendamento parou.
    (st.warning if horas > 72 else st.caption)(recado)

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

    limiar = st.slider(
        "Limiar de probabilidade para o alerta",
        min_value=0.05, max_value=0.95, value=0.50, step=0.05,
        help="Probabilidade acima da qual Brasilia entra em alerta.",
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

aba_mapa, aba_serie, aba_relatorio, aba_modelo = st.tabs(
    ["Brasilia por Regiao Administrativa", "Series temporais",
     "Relatorio da semana", "Desempenho do modelo"]
)

# ------------------------------------------- Brasilia por Regiao Administrativa
with aba_mapa:
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

        # Classes por quantil, e nao escala linear. A populacao das RAs vai de
        # 2.286 a 348.000: numa escala linear, 18 das 31 caem nos dois tons mais
        # claros da rampa -- quase brancos sobre um mapa base quase branco, e
        # indistinguiveis entre si. Por quantil cada faixa recebe seis ou sete
        # RAs, e todas se separam.
        faixas = pd.qcut(regioes[coluna], q=4, duplicates="drop")
        limites = [faixas.cat.categories[0].left] + [
            categoria.right for categoria in faixas.cat.categories
        ]
        rotulos = [
            f"{formatar_milhar(limites[i])} a {formatar_milhar(limites[i + 1])}"
            for i in range(len(limites) - 1)
        ]
        regioes["faixa"] = faixas.cat.rename_categories(rotulos).astype(str)

        # Quatro passos alternados da rampa. Sao os que mais se separam entre si;
        # o extremo claro fica de fora porque sumiria sobre o mapa base.
        cores_faixa = dict(zip(rotulos, RAMPA_TERRITORIO[2:9:2]))

        mapa_ras = px.choropleth_map(
            regioes,
            geojson=malha_ras,
            locations="ra_nome",
            featureidkey="properties.ra_nome",
            color="faixa",
            color_discrete_map=cores_faixa,
            category_orders={"faixa": rotulos},
            map_style="carto-positron",
            zoom=8.55,
            center={"lat": -15.79, "lon": -47.87},
            opacity=0.88,
            hover_name="ra_nome",
            hover_data={"faixa": False, coluna: ":,.0f"},
            labels={coluna: rotulo, "faixa": rotulo.capitalize()},
        )
        # Borda clara: sem ela duas RAs vizinhas da mesma faixa viram uma mancha.
        mapa_ras.update_traces(marker_line_color="#f2f2f3", marker_line_width=1.1)

        # O nome sobre a regiao. Era o que mais faltava: com 31 poligonos, ter
        # de passar o cursor um a um para saber qual e qual inviabiliza a leitura.
        #
        # So as RAs com area suficiente recebem rotulo: doze das trinta e uma tem
        # menos de 30 km2 -- o Varjao tem 1 km2 -- e ficam amontoadas no centro,
        # onde os nomes se sobreporiam e piorariam justamente o que se quer
        # resolver. Elas continuam no `hover` e na tabela abaixo do mapa.
        centros = centroides_ras(malha_ras)
        # As maiores primeiro: quando duas competem pelo mesmo espaco, quem fica
        # e a que o leitor consegue localizar no mapa.
        ordem = regioes.sort_values("area_km2", ascending=False)["ra_nome"].tolist()
        nomeadas = desempilhar(ordem, centros)
        cabe_rotulo = regioes[regioes["ra_nome"].isin(nomeadas)]

        # Texto escuro sobre as duas faixas claras, claro sobre as duas escuras.
        # Vao em dois tracos porque `textfont.color` do scattermap aceita uma cor
        # so por traco, e nao uma lista.
        clara = {rotulos[i] for i in range(min(2, len(rotulos)))}
        for faixas_do_traco, cor in ((clara, TEXTO), (set(rotulos) - clara, "#f2f2f3")):
            grupo = cabe_rotulo[cabe_rotulo["faixa"].isin(faixas_do_traco)]
            if grupo.empty:
                continue
            mapa_ras.add_trace(go.Scattermap(
                lat=[centros[n][0] for n in grupo["ra_nome"]],
                lon=[centros[n][1] for n in grupo["ra_nome"]],
                mode="text",
                text=list(grupo["ra_nome"]),
                textfont={"size": 10, "family": FONTE_CORPO, "color": cor},
                hoverinfo="skip",
                showlegend=False,
            ))
        mapa_ras.update_layout(
            height=620,
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            legend={"title_text": rotulo.capitalize(), "y": 0.98, "x": 0.01,
                    "bgcolor": "rgba(242,242,243,0.88)", "bordercolor": DIVISOR,
                    "borderwidth": 1},
        )
        st.plotly_chart(mapa_ras, width="stretch")
        st.caption(
            f"Nomeadas no mapa {len(cabe_rotulo)} das 31 RAs: onde varias se "
            "aglomeram, fica o nome da maior, e as demais aparecem ao passar o "
            "cursor e na tabela abaixo -- uma pilha de nomes sobrepostos seria "
            "pior do que nome nenhum. As faixas sao quartis, com cerca de oito "
            "RAs cada; numa escala linear, 18 das 31 cairiam no mesmo tom claro."
        )

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
    serie = painel[painel["cod_ibge"] == COD_FOCO].sort_values("data_ini_se")
    st.caption(
        "Serie de **Brasilia**. O InfoDengue publica casos no nivel municipal, "
        "e o Distrito Federal e um unico municipio: esta e a serie do territorio "
        "inteiro, cidades satelites incluidas."
    )

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

# ----------------------------------------------------------- relatorio da semana
with aba_relatorio:
    if foco.empty:
        st.warning("Sem dado de Brasilia nesta semana.")
    else:
        r = foco.iloc[0]
        st.subheader(f"Brasilia -- semana {formatar_semana(semana_escolhida)}")

        resumo = pd.DataFrame({
            "Indicador": [
                "Casos notificados",
                "Casos estimados",
                "Incidencia / 100 mil",
                "Nivel de risco",
                f"Probabilidade de alerta ({horizonte} semanas)",
                "Principais fatores",
                "Notificacao completa",
            ],
            "Valor": [
                f"{r['casos']:,.0f}".replace(",", "."),
                f"{r['casos_est']:,.0f}".replace(",", "."),
                f"{r['incidencia_100k']:.1f}",
                str(r["risco"]).capitalize(),
                f"{r['probabilidade_alerta']:.0%}",
                r["fatores_alerta"],
                "nao" if r["dado_provisorio"] == 1 else "sim",
            ],
        })
        st.dataframe(resumo, hide_index=True, width="stretch")

    # A serie inteira, e nao so a semana: quem leva o CSV costuma querer
    # remontar a curva, nao apenas o retrato de uma semana.
    serie_bsb = painel[painel["cod_ibge"] == COD_FOCO].sort_values("se_codigo")[
        ["se_codigo", "data_ini_se", "casos", "casos_est", "incidencia_100k",
         "risco", "probabilidade_alerta", "fatores_alerta", "dado_provisorio"]
    ]
    st.download_button(
        "Baixar a serie completa de Brasilia (CSV)",
        data=serie_bsb.to_csv(index=False).encode("utf-8"),
        file_name="vigia_dengue_brasilia.csv",
        mime="text/csv",
    )
    st.caption(
        f"{len(serie_bsb)} semanas, de {formatar_semana(serie_bsb['se_codigo'].iloc[0])} "
        f"a {formatar_semana(serie_bsb['se_codigo'].iloc[-1])}."
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
