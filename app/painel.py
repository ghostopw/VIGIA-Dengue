"""VIGIA-Dengue -- sala de situacao do risco de dengue no DF e na RIDE-DF.

Execucao:  streamlit run app/painel.py
"""

from __future__ import annotations

import html
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
CAMINHO_ALARMES = RAIZ / "saidas" / "alarmes.json"
CAMINHO_CLIMA_FUTURO = RAIZ / "saidas" / "clima_futuro.json"
CAMINHO_VULNERABILIDADE_RAS = (
    RAIZ / "dados" / "externo" / "vulnerabilidade_ras.csv"
)
CAMINHO_SETORES = RAIZ / "dados" / "externo" / "setores_df.geojson"
CAMINHO_DICIONARIO = RAIZ / "docs" / "dicionario_de_dados.csv"

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

# Chips de risco na rampa terracota do sistema. Risco e magnitude, entao a
# leitura e sequencial: um tom so, do claro ao queimado. O chip nunca fala por
# cor sozinha -- o texto do nivel vai junto, e a cor do texto troca de escura
# para clara quando o fundo escurece. Sobre os fundos escuros o texto vai em
# branco puro, e nao no cinza do tema: sobre o "alto" o cinza fica em 4,3:1 de
# contraste, abaixo do minimo de 4,5:1 para texto pequeno.
CORES_RISCO = {
    "baixo": "#dcc7b6",
    "moderado": "#c78d5f",
    "alto": "#b25a33",
    "muito alto": "#7f2f18",
}
TEXTO_SOBRE_RISCO = {
    "baixo": TEXTO,
    "moderado": TEXTO,
    "alto": "#ffffff",
    "muito alto": "#ffffff",
}
ORDEM_RISCO = ["baixo", "moderado", "alto", "muito alto"]

# Setas de tendencia: subir e o unico movimento quente da tela, na mesma
# familia do risco alto; cair vai no azul do sistema e estavel fica neutro.
CORES_TENDENCIA = {"▲": "#b25a33", "▼": ACENTO, "▬": NEUTRO_600}

# Regra de leitura herdada do painel: a serie em foco vai solida no azul
# escuro; as de comparacao vao neutras e tracejadas, para nao disputar.
CORES_MODELO = ["#b7b7ba", "#749dc4", "#1d2d3d"]

# Municipio foco do projeto. A RIDE-DF entra como territorio de comparacao.
FOCO = "Brasilia"
COD_FOCO = 5300108

# Indices da semana, no formato de cartao de previsao do tempo. Cada cartao
# fala pelo nivel escrito e pela bolinha -- nunca so pela cor. As cores sao
# semanticas (calmo, atencao, alerta) e independem da rampa de risco, que
# mede magnitude e tem outro trabalho na tela.
COR_INDICE = {
    "calmo": "#3f8f5a",
    "atencao": "#d9a420",
    "elevado": "#c8682c",
    "alerta": "#a63a24",
    "sem_dado": "#9a9a9d",
}

# Faixa termica favoravel ao Aedes aegypti, a mesma de base_analitica.py
# (semanas_favoraveis_8): o cartao de clima e a base leem o clima com a
# mesma regua.
FAIXA_TERMICA_AEDES = (21.0, 32.0)

# Chuva frequente na janela de 14 dias: metade dos dias ou mais. Corte de
# leitura, nao de previsao -- no historico do territorio, gatilho climatico
# isolado nao antecipou dengue (docs/achados_modelagem.md, secao 8). Por isso
# o cartao de clima se apresenta como contexto.
DIAS_CHUVA_FREQUENTE = 7

# Desempenho operacional do alerta em Brasilia no limiar de 0,80, medido na
# validacao temporal 2019-2025 (docs/achados_modelagem.md, secao 8). Vale so
# para Brasilia e so para esse limiar; os demais casos mostram a AUC do
# territorio, lida de saidas/desempenho_modelos.csv.
VPP_BRASILIA_LIMIAR_080 = 0.902
LIMIAR_DO_VPP = 0.80

# Sala de situacao nao tem barra de ferramentas flutuando sobre o grafico.
CONFIG_GRAFICO = {"displayModeBar": False}

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
    "hoverlabel": {"font": {"family": FONTE_CORPO, "size": 12}},
})
pio.templates.default = "plotly_white+vigia"

# Barlow e a tipografia do painel; sem rede, cai no fallback do sistema.
# Os hexes abaixo repetem os tokens definidos no topo do arquivo: CSS nao
# enxerga as constantes Python, entao quem mudar a paleta muda aqui tambem.
st.markdown(
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Barlow+Condensed:wght@600&family=Barlow:wght@400;500;600'
    '&display=swap">'
    """<style>
      html, body, [class*="css"] { font-family: "Barlow", system-ui, sans-serif; }
      h1, h2, h3, h4 { font-family: "Barlow Condensed", "Arial Narrow", sans-serif;
                       font-weight: 600; letter-spacing: 0.2px; }

      /* Casca do aplicativo: o menu e o rodape do Streamlit nao pertencem a
         uma sala de situacao, e a faixa decorativa colorida briga com o navy. */
      #MainMenu, [data-testid="stMainMenu"] { visibility: hidden; }
      footer { visibility: hidden; }
      [data-testid="stDecoration"] { display: none; }

      /* Algarismos tabulares: colunas de numeros alinham na vertical. */
      [data-testid="stMetricValue"], [data-testid="stMetricDelta"] {
        font-variant-numeric: tabular-nums;
      }

      /* Cartoes de metrica com borda de 1px no lugar de sombra pesada. */
      [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid rgba(29,31,32,0.16);
        border-radius: 6px;
        padding: 0.65rem 0.9rem 0.55rem;
      }

      /* Abas em caixa alta condensada, como rotulos de bancada. */
      button[data-baseweb="tab"] p {
        font-family: "Barlow Condensed", "Arial Narrow", sans-serif;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        font-size: 0.95rem;
      }

      /* Faixa de cabecalho: navy, nome do sistema em condensada caixa alta. */
      .vigia-cabecalho {
        background: #1d2d3d;
        color: #f2f2f3;
        border-radius: 6px;
        padding: 1.05rem 1.3rem 0.95rem;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        gap: 1rem;
        margin-bottom: 0.4rem;
      }
      .vigia-cabecalho-nome {
        font-family: "Barlow Condensed", "Arial Narrow", sans-serif;
        font-size: 2rem;
        font-weight: 600;
        letter-spacing: 3px;
        text-transform: uppercase;
        line-height: 1;
      }
      .vigia-cabecalho-sub {
        color: rgba(242,242,243,0.72);
        font-size: 0.95rem;
        margin-top: 0.4rem;
      }
      .vigia-cabecalho-tag {
        font-family: "Barlow Condensed", "Arial Narrow", sans-serif;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: rgba(242,242,243,0.85);
        border: 1px solid rgba(242,242,243,0.35);
        border-radius: 4px;
        padding: 0.3rem 0.6rem;
        text-align: right;
        font-size: 0.95rem;
        line-height: 1.3;
        white-space: nowrap;
      }

      /* Chips de estado (frescor, dado provisorio, risco). */
      .vigia-chip {
        display: inline-block;
        padding: 0.14rem 0.6rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.3px;
        margin: 0 0.4rem 0.3rem 0;
        font-variant-numeric: tabular-nums;
      }

      /* Cartao de alarme: borda fina e um fio quente na esquerda. */
      .vigia-alarme {
        background: #ffffff;
        border: 1px solid rgba(29,31,32,0.16);
        border-left: 3px solid #b25a33;
        border-radius: 6px;
        padding: 0.75rem 1rem 0.65rem;
        margin-bottom: 0.55rem;
      }
      .vigia-alarme-titulo {
        font-family: "Barlow Condensed", "Arial Narrow", sans-serif;
        font-size: 1.05rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.15rem;
      }
      .vigia-alarme-frase { font-size: 0.95rem; }
      .vigia-alarme-meta {
        color: #7a7a7d;
        font-size: 0.8rem;
        margin-top: 0.3rem;
        font-variant-numeric: tabular-nums;
      }

      /* Estado calmo dos alarmes: uma linha sobria, nunca tela vazia. */
      .vigia-sem-alarme {
        border: 1px dashed rgba(29,31,32,0.25);
        border-radius: 6px;
        color: #7a7a7d;
        padding: 0.6rem 0.9rem;
        font-size: 0.92rem;
      }

      /* Indices da semana: titulo, bolinha de nivel, nivel por extenso e uma
         linha de leitura. A evidencia vai embaixo, menor -- e ela que separa
         este indice de um indice climatico sem lastro. */
      .vigia-indice {
        background: #ffffff;
        border: 1px solid rgba(29,31,32,0.14);
        border-radius: 8px;
        padding: 0.8rem 1rem 0.75rem;
        height: 100%;
      }
      .vigia-indice-topo {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.45rem;
      }
      .vigia-indice-titulo {
        font-family: "Barlow Condensed", "Arial Narrow", sans-serif;
        font-size: 0.95rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        color: #55595c;
      }
      .vigia-indice-ponto {
        width: 0.8rem;
        height: 0.8rem;
        border-radius: 50%;
        flex: none;
      }
      .vigia-indice-nivel {
        font-family: "Barlow Condensed", "Arial Narrow", sans-serif;
        font-size: 1.55rem;
        font-weight: 600;
        line-height: 1.05;
        margin-bottom: 0.25rem;
      }
      .vigia-indice-leitura {
        font-size: 0.9rem;
        line-height: 1.35;
        font-variant-numeric: tabular-nums;
      }
      .vigia-indice-evidencia {
        color: #7a7a7d;
        font-size: 0.78rem;
        line-height: 1.35;
        border-top: 1px solid rgba(29,31,32,0.1);
        margin-top: 0.55rem;
        padding-top: 0.45rem;
      }
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
def carregar_alarmes() -> dict | None:
    """Alarmes de variaveis medidos por `executar_alarmes.py`.

    O arquivo traz os alarmes ativos da semana e, em `regras`, a medicao
    historica completa -- incluindo as regras reprovadas, que so aparecem na
    secao de metodologia e nunca como alarme.
    """
    if CAMINHO_ALARMES.exists():
        return json.loads(CAMINHO_ALARMES.read_text(encoding="utf-8"))
    return None


@st.cache_data(ttl=600)
def carregar_clima_futuro() -> dict | None:
    """Previsao de 14 dias coletada por `executar_clima_futuro.py`.

    O painel apenas le o arquivo: a chamada de rede ao Open-Meteo acontece no
    ciclo de atualizacao, nunca aqui.
    """
    if CAMINHO_CLIMA_FUTURO.exists():
        return json.loads(CAMINHO_CLIMA_FUTURO.read_text(encoding="utf-8"))
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
def carregar_vulnerabilidade_ras():
    """Indicadores do Censo 2022 por Regiao Administrativa, se ja coletados."""
    if CAMINHO_VULNERABILIDADE_RAS.exists():
        return pd.read_csv(CAMINHO_VULNERABILIDADE_RAS)
    return None


@st.cache_data
def carregar_setores():
    """Setores censitarios do DF -- a escala da quadra.

    So os urbanos e com dado: os rurais sao poucos, enormes e sem face de rua
    levantada, e pintados no mapa esconderiam a malha urbana, que e o que
    interessa aqui.
    """
    if not CAMINHO_SETORES.exists():
        return None
    bruto = json.loads(CAMINHO_SETORES.read_text(encoding="utf-8"))
    feicoes = [
        f for f in bruto["features"]
        if f["properties"].get("SITUACAO") == "Urbana"
        and f["properties"].get("indice_criadouro") is not None
    ]
    return {"type": "FeatureCollection", "features": feicoes}


@st.cache_data
def carregar_dicionario():
    """Dicionario de dados gerado da propria base analitica.

    Vem de `docs/dicionario_de_dados.csv`, reescrito por `gerar_dicionario.py`
    a cada vez que a base muda -- assim a documentacao no ar nunca descreve uma
    base que deixou de existir.
    """
    if not CAMINHO_DICIONARIO.exists():
        return None
    return pd.read_csv(CAMINHO_DICIONARIO)


@st.cache_data
def carregar_desempenho():
    if CAMINHO_DESEMPENHO.exists():
        return pd.read_csv(CAMINHO_DESEMPENHO)
    return None


def formatar_faixa(valor: float) -> str:
    """Numero curto para rotulo de legenda.

    Atende as duas escalas do mapa: contagens grandes, onde "348 mil" le melhor
    que 348000, e percentuais de um digito, onde arredondar para inteiro juntaria
    faixas distintas num mesmo rotulo.
    """
    if abs(valor) >= 1000:
        return f"{valor / 1000:.0f} mil"
    if abs(valor) >= 10 or valor == int(valor):
        return f"{valor:.0f}"
    return f"{valor:.1f}".replace(".", ",")


def formatar_semana(codigo: int) -> str:
    return f"{int(codigo) % 100:02d}/{int(codigo) // 100}"


def semana_epidemiologica(data: pd.Timestamp) -> int:
    """Semana epidemiologica brasileira (AAAASS) da data dada.

    Convencao do SINAN: semanas de domingo a sabado, e a SE 1 e a que termina
    no primeiro sabado de janeiro que caia no dia 4 ou depois. Serve para
    saber se um arquivo de previsao ainda e da semana corrente -- a base de
    casos fecha semanas atras, entao o frescor dela nao responde isso.
    """
    def inicio_da_se1(ano: int) -> pd.Timestamp:
        dia = pd.Timestamp(ano, 1, 4)
        while dia.dayofweek != 5:  # 5 = sabado
            dia += pd.Timedelta(days=1)
        return dia - pd.Timedelta(days=6)

    data = data.normalize()
    for ano in (data.year + 1, data.year, data.year - 1):
        inicio = inicio_da_se1(ano)
        if data >= inicio:
            return ano * 100 + int((data - inicio).days // 7) + 1
    raise ValueError(f"data fora do calendario epidemiologico: {data}")


def seta_tendencia(razao: float) -> str:
    """Seta de tendencia a partir da razao mm3/mm8.

    A razao compara a media movel curta (3 semanas) com a longa (8): acima de
    1 a curva acelera, abaixo desacelera. A faixa morta de 10% em volta de 1
    evita que ruido semanal vire seta. A seta nunca vai sozinha -- o numero
    acompanha, para que a cor nao seja o unico canal.
    """
    if pd.isna(razao):
        return ""
    if razao >= 1.1:
        return f"▲ {razao:.2f}"
    if razao <= 0.9:
        return f"▼ {razao:.2f}"
    return f"▬ {razao:.2f}"


def chip(texto: str, fundo: str, cor_texto: str) -> str:
    return (
        f'<span class="vigia-chip" style="background:{fundo};'
        f'color:{cor_texto}">{html.escape(texto)}</span>'
    )


def _milhar(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def cartao_indice(titulo: str, estado: str, nivel: str, leitura: str,
                  evidencia: str) -> str:
    """Um indice da semana em cartao.

    Todo texto passa por escape: nome de municipio e frase de evidencia vem de
    dado e entram em HTML cru.
    """
    cor = COR_INDICE.get(estado, COR_INDICE["sem_dado"])
    evidencia_html = (
        f'<div class="vigia-indice-evidencia">{html.escape(evidencia)}</div>'
        if evidencia else ""
    )
    return (
        '<div class="vigia-indice">'
        '<div class="vigia-indice-topo">'
        f'<span class="vigia-indice-titulo">{html.escape(titulo)}</span>'
        f'<span class="vigia-indice-ponto" style="background:{cor}" '
        f'title="{html.escape(nivel)}"></span>'
        '</div>'
        f'<div class="vigia-indice-nivel">{html.escape(nivel)}</div>'
        f'<div class="vigia-indice-leitura">{html.escape(leitura)}</div>'
        f'{evidencia_html}'
        '</div>'
    )


def indice_risco(linha: pd.Series, limiar: float, horizonte: int,
                 auc_territorio: float | None, eh_foco: bool) -> str:
    """Probabilidade do modelo combinado para o horizonte do alerta."""
    titulo = f"Risco em {horizonte} semanas"
    prob = linha.get("probabilidade_alerta")
    if prob is None or pd.isna(prob):
        return cartao_indice(
            titulo, "sem_dado", "Sem previsao",
            "A semana mais recente nao tem os preditores essenciais.", "")

    if prob >= limiar:
        estado, nivel = "alerta", "Alerta"
    elif prob >= 0.5:
        estado, nivel = "atencao", "Atencao"
    else:
        estado, nivel = "calmo", "Baixo"
    leitura = (f"{prob:.0%} de chance de risco alto ou muito alto em "
               f"{horizonte} semanas.")

    # O VPP medido so vale para Brasilia no limiar em que foi medido; mexer no
    # controle do limiar troca a evidencia pela AUC do territorio.
    if eh_foco and abs(limiar - LIMIAR_DO_VPP) < 1e-9:
        evidencia = (
            f"Validado em 2019-2025: em Brasilia, no limiar de "
            f"{LIMIAR_DO_VPP:.0%}, {VPP_BRASILIA_LIMIAR_080:.0%} dos alertas "
            "se confirmaram.")
    elif auc_territorio is not None:
        evidencia = (
            "Validacao temporal 2019-2025 nos 34 municipios: AUC de "
            f"{auc_territorio:.3f}.".replace(".", ",", 1))
    else:
        evidencia = ""
    return cartao_indice(titulo, estado, nivel, leitura, evidencia)


def indice_transmissao(serie: pd.DataFrame, regra: dict | None,
                       lift_municipal: float | None) -> str:
    """p(Rt>1) das duas ultimas semanas -- a variavel da regra R3."""
    titulo = "Transmissao"
    if "p_rt1" not in serie.columns or serie["p_rt1"].dropna().empty:
        return cartao_indice(
            titulo, "sem_dado", "Sem dado",
            "Probabilidade de Rt acima de 1 indisponivel nesta base.", "")

    ultimos = serie["p_rt1"].dropna().iloc[-2:]
    agora = float(ultimos.iloc[-1])
    antes = float(ultimos.iloc[0]) if len(ultimos) > 1 else None

    if antes is not None and agora >= 0.9 and antes >= 0.9:
        estado, nivel = "alerta", "Crescendo"
    elif agora >= 0.9:
        estado, nivel = "atencao", "Subindo"
    else:
        estado, nivel = "calmo", "Estavel"

    leitura = f"Probabilidade de Rt acima de 1: {agora:.0%} nesta semana"
    leitura += f", {antes:.0%} na anterior." if antes is not None else "."

    if regra is None:
        evidencia = ""
    elif lift_municipal is not None:
        evidencia = (
            "Aqui, quando passou de 90% por duas semanas, a incidencia "
            f"{regra.get('lag_semanas', 4)} semanas depois foi "
            f"{lift_municipal:.1f}x a normal da epoca.".replace(".", ",", 1))
    else:
        evidencia = (
            "No territorio, acima de 90% por duas semanas antecedeu incidencia "
            f"{regra['lift_mediano']:.1f}x a normal da epoca, em "
            f"{_milhar(regra['n_episodios'])} episodios desde 2014."
            .replace(".", ",", 1))
    return cartao_indice(titulo, estado, nivel, leitura, evidencia)


def indice_clima(clima_municipio: dict | None, clima_atual: bool) -> str:
    """Receptividade climatica dos proximos 14 dias -- contexto, nao previsao."""
    titulo = "Clima para o Aedes (14 dias)"
    contexto = ("Contexto, nao previsao: no historico do territorio, gatilhos "
                "climaticos sozinhos nao anteciparam dengue.")
    if clima_municipio is None:
        return cartao_indice(
            titulo, "sem_dado", "Sem previsao",
            "Previsao do tempo indisponivel para este municipio.", contexto)

    temp = clima_municipio.get("temp_media_14d")
    dias = int(clima_municipio.get("dias_chuva_14d") or 0)
    chuva = float(clima_municipio.get("chuva_14d_mm") or 0)
    na_faixa = (temp is not None
                and FAIXA_TERMICA_AEDES[0] <= temp <= FAIXA_TERMICA_AEDES[1])

    if not na_faixa or dias == 0:
        estado, nivel = "calmo", "Pouco favoravel"
    elif dias >= DIAS_CHUVA_FREQUENTE:
        estado, nivel = "elevado", "Muito favoravel"
    else:
        estado, nivel = "atencao", "Favoravel"

    temp_txt = ("temperatura indisponivel" if temp is None
                else f"media de {temp:.0f} °C")
    leitura = f"{chuva:.0f} mm em {dias} dias de chuva; {temp_txt}."
    if not clima_atual:
        contexto = "Previsao coletada em semana anterior. " + contexto
    return cartao_indice(titulo, estado, nivel, leitura, contexto)


def indice_dado(linha: pd.Series) -> str:
    """Quanto da semana ja foi digitado -- a incerteza na ponta da serie."""
    titulo = "Qualidade do dado"
    completude = linha.get("completude")
    provisorio = linha.get("dado_provisorio") == 1
    tem_completude = completude is not None and pd.notna(completude)

    if not provisorio or (tem_completude and completude >= 0.9):
        estado, nivel = "calmo", "Consolidado"
    elif tem_completude and completude >= 0.6:
        estado, nivel = "atencao", "Em consolidacao"
    else:
        estado, nivel = "elevado", "Provisorio"

    leitura = (f"{_milhar(linha['casos'])} casos notificados de "
               f"{_milhar(linha['casos_est'])} estimados")
    leitura += f" ({completude:.0%} digitado)." if tem_completude else "."
    evidencia = ("A notificacao chega com atraso; o nowcasting do InfoDengue "
                 "estima os casos que ainda vao entrar.")
    return cartao_indice(titulo, estado, nivel, leitura, evidencia)


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


def desenhar_mapa_setores(setores: dict, coluna: str, rotulo: str) -> None:
    """Mapa na escala da quadra: um poligono por setor censitario.

    Sao milhares de poligonos pequenos, entao aqui nao cabe o desenho usado nas
    RAs: nome sobre a regiao seria ilegivel, e borda em cada quadra viraria uma
    grade que esconde a cor. O nome do lugar sai no cursor, e as ruas quem
    desenha e o mapa base, quando se aproxima.
    """
    registros = pd.DataFrame([f["properties"] for f in setores["features"]])

    # As duas escalas medem as mesmas coisas com nomes diferentes, e nem tudo
    # existe nas duas: populacao e densidade sao atributos da RA, e o indice da
    # quadra se chama "criadouro" porque nela as quatro dimensoes sao de
    # condicao local, sem o componente populacional.
    EQUIVALENTE = {
        "indice_vulnerabilidade": "indice_criadouro",
        "populacao": "domicilios",
        "densidade_hab_km2": "domicilios",
    }
    coluna = EQUIVALENTE.get(coluna, coluna)
    if coluna == "domicilios":
        rotulo = "domicilios no setor"

    if coluna not in registros or registros[coluna].isna().all():
        disponiveis = [c for c in registros.columns
                       if c.endswith("_pct") or c == "indice_criadouro"]
        st.warning(
            "Este indicador nao existe na escala da quadra. Disponiveis: "
            + ", ".join(disponiveis) + "."
        )
        return

    mapa = px.choropleth_map(
        registros.dropna(subset=[coluna]),
        geojson=setores,
        locations="CD_SETOR",
        featureidkey="properties.CD_SETOR",
        color=coluna,
        color_continuous_scale=RAMPA_TERRITORIO[1:],
        map_style="carto-positron",
        zoom=9.2,
        center={"lat": -15.79, "lon": -47.93},
        opacity=0.75,
        hover_name="NM_SUBDIST",
        hover_data={"CD_SETOR": True, coluna: ":.1f", "domicilios": ":,.0f"},
        labels={coluna: rotulo},
    )
    # Sem borda: com milhares de poligonos ela dominaria a cor.
    mapa.update_traces(marker_line_width=0)
    mapa.update_layout(
        height=640, margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar={"title": rotulo, "thickness": 12},
    )
    st.plotly_chart(mapa, width="stretch", config=CONFIG_GRAFICO)

    st.caption(
        f"{len(registros):,} setores censitarios urbanos. ".replace(",", ".")
        + "O setor e a menor unidade que o IBGE publica -- algumas quadras, "
        "cerca de trezentos domicilios. Aproxime para o mapa base nomear as ruas. "
        "O risco de dengue continua sendo municipal: esta camada mostra onde a "
        "condicao local favorece o criadouro, nao onde ha caso."
    )

    piores = registros.nlargest(12, coluna)[
        [c for c in ("NM_SUBDIST", "CD_SETOR", coluna, "domicilios") if c in registros]
    ]
    st.markdown("**As doze quadras em pior situacao neste indicador**")
    st.dataframe(
        piores.rename(columns={
            "NM_SUBDIST": "Regiao Administrativa", "CD_SETOR": "Setor",
            coluna: rotulo, "domicilios": "Domicilios",
        }),
        hide_index=True, width="stretch",
    )


painel = carregar_painel()
n_municipios = int(painel["cod_ibge"].nunique())

# ------------------------------------------------------------------ cabecalho
st.markdown(
    '<div class="vigia-cabecalho">'
    '<div>'
    '<div class="vigia-cabecalho-nome">Vigia-Dengue</div>'
    '<div class="vigia-cabecalho-sub">Sala de situacao -- alerta precoce do '
    'risco de dengue em Brasilia e na RIDE-DF</div>'
    '</div>'
    f'<div class="vigia-cabecalho-tag">DF + RIDE<br>{n_municipios} municipios</div>'
    '</div>',
    unsafe_allow_html=True,
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

    # O padrao era 0,50 e alertava 47 semanas por ano -- alerta quase toda
    # semana nao e alerta. A taxa base de Brasilia e alta (58% das semanas com
    # risco alto no horizonte) e o modelo prevê mediana de 0,84, entao meio
    # caminho nao separa nada: a especificidade fica em 19%.
    #
    # Em 0,80 o alerta passa a acertar 3 de cada 4 vezes que dispara (VPP 74,8%)
    # e reconhece 67% das semanas calmas, ao custo de perder os surtos mais
    # fracos -- 29 alertas por ano em vez de 47. Medido em 209 semanas de
    # Brasilia, 2021 a 2025.
    limiar = st.slider(
        "Limiar de probabilidade para o alerta",
        min_value=0.05, max_value=0.95, value=0.80, step=0.05,
        help="Probabilidade acima da qual Brasilia entra em alerta. Em 0,80 o "
             "alerta acerta 3 de cada 4 disparos; em 0,50 dispararia em quase "
             "toda semana.",
    )

    sinalizar_provisorio = st.checkbox(
        "Sinalizar semanas com notificacao incompleta", value=True
    )

    st.caption(
        "O Monitor mostra sempre a semana mais recente da base; o filtro de "
        "semana vale para as demais abas."
    )

    st.divider()
    horizonte = int(painel["horizonte_semanas"].iloc[0])
    st.info(
        f"O alerta projeta o risco **{horizonte} semanas a frente**. "
        "Os casos estimados corrigem o atraso de notificacao."
    )

semana_atual = painel[painel["se_codigo"] == semana_escolhida].copy()

# `foco` e o retrato de Brasilia na semana ESCOLHIDA no filtro: alimenta o
# relatorio da semana. O Monitor nao passa por aqui -- ele e ao vivo e le
# sempre a ultima semana da base.
foco = semana_atual[semana_atual["cod_ibge"] == COD_FOCO]

(aba_monitor, aba_mapa, aba_serie, aba_relatorio, aba_modelo,
 aba_dicionario) = st.tabs(
    ["Monitor", "Brasilia por Regiao Administrativa", "Series temporais",
     "Relatorio da semana", "Desempenho do modelo", "Dicionario de dados"]
)

# ----------------------------------------------------------------- monitor
with aba_monitor:
    serie_foco = painel[painel["cod_ibge"] == COD_FOCO].sort_values("se_codigo")
    atual = serie_foco.iloc[-1]
    semana_monitor = int(atual["se_codigo"])

    # ---- faixa de status: Brasilia agora -------------------------------
    variacao = None
    if len(serie_foco) > 1:
        casos_antes = serie_foco["casos_est"].iloc[-2]
        if casos_antes:
            variacao = (atual["casos_est"] - casos_antes) / casos_antes * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Semana epidemiologica",
        formatar_semana(semana_monitor),
        help="Ultima semana consolidada na base. A fonte (InfoDengue) publica "
             "semanalmente.",
    )
    col2.metric(
        "Casos estimados em Brasilia",
        f"{atual['casos_est']:,.0f}".replace(",", "."),
        delta=None if variacao is None else f"{variacao:+.0f}% vs semana anterior",
        delta_color="inverse",
        help="Nowcasting do InfoDengue: corrige o atraso de notificacao.",
    )
    canal_q3 = atual["canal_q3"]
    col3.metric(
        "Incidencia / 100 mil",
        f"{atual['incidencia_100k']:.1f}",
        delta=(None if pd.isna(canal_q3)
               else f"{atual['incidencia_100k'] - canal_q3:+.1f} vs canal endemico"),
        delta_color="inverse",
        help=(None if pd.isna(canal_q3)
              else f"Limite esperado para esta semana do ano (Q3 historico): "
                   f"{canal_q3:.1f} por 100 mil."),
    )
    col4.metric(
        f"Prob. de alerta em {horizonte} semanas",
        f"{atual['probabilidade_alerta']:.0%}",
        help=f"Limiar configurado: {limiar:.0%}. Probabilidade de risco alto "
             "ou muito alto no horizonte do modelo.",
    )

    selos = [chip(
        f"dados da SE {formatar_semana(semana_monitor)} -- a fonte publica "
        "semanalmente",
        "#e9e9ea", TEXTO,
    )]
    risco_atual = str(atual["risco"])
    if risco_atual in CORES_RISCO:
        selos.append(chip(
            f"risco {risco_atual}",
            CORES_RISCO[risco_atual], TEXTO_SOBRE_RISCO[risco_atual],
        ))
    if sinalizar_provisorio and atual["dado_provisorio"] == 1:
        selos.append(chip(
            f"dado provisorio -- {atual['completude']:.0%} digitado; os casos "
            "tendem a subir",
            "#dcc7b6", TEXTO,
        ))
    st.markdown("".join(selos), unsafe_allow_html=True)

    if atual["probabilidade_alerta"] >= limiar:
        st.error(
            f"**Brasilia em alerta.** Probabilidade de "
            f"{atual['probabilidade_alerta']:.0%} de risco alto ou muito alto "
            f"em {horizonte} semanas. Principais fatores: "
            f"{atual['fatores_alerta']}."
        )

    # ---- indices da semana ----------------------------------------------
    st.subheader("Indices da semana")
    municipios_idx = (painel[["cod_ibge", "municipio"]].drop_duplicates()
                      .sort_values("municipio"))
    opcoes_idx = [int(c) for c in municipios_idx["cod_ibge"]]
    rotulos_idx = dict(zip(opcoes_idx, municipios_idx["municipio"]))
    cod_idx = st.selectbox(
        "Municipio", opcoes_idx,
        index=opcoes_idx.index(COD_FOCO) if COD_FOCO in opcoes_idx else 0,
        format_func=lambda codigo: rotulos_idx.get(codigo, str(codigo)),
        key="municipio_indices",
    )
    serie_idx = painel[painel["cod_ibge"] == cod_idx].sort_values("se_codigo")
    linha_idx = serie_idx.iloc[-1]
    st.caption(
        f"Semana {formatar_semana(int(linha_idx['se_codigo']))}. Cada indice "
        "traz embaixo a evidencia medida que o sustenta."
    )

    # Evidencia da regra de transmissao: a medicao do territorio e, quando o
    # municipio tem episodios bastantes, a dele proprio.
    regra_r3, lift_r3 = None, None
    alarmes_idx = carregar_alarmes()
    if alarmes_idx:
        regras_idx = alarmes_idx.get("regras", {})
        regra_r3 = next(
            (r for r in regras_idx.get("regras", [])
             if r.get("id") == "R3" and r.get("aprovada")), None)
        for item in regras_idx.get("por_municipio", {}).get("R3", []):
            if int(item.get("cod_ibge", 0)) == cod_idx:
                lift_r3 = item.get("lift")

    clima_idx = carregar_clima_futuro()
    clima_municipio_idx, clima_atual_idx = None, False
    if clima_idx:
        clima_municipio_idx = next(
            (m for m in clima_idx.get("municipios", [])
             if int(m["cod_ibge"]) == cod_idx), None)
        clima_atual_idx = (int(clima_idx.get("coletado_para_semana", 0))
                           == semana_epidemiologica(pd.Timestamp.today()))

    auc_territorio = None
    desempenho_idx = carregar_desempenho()
    if desempenho_idx is not None and "modelo" in desempenho_idx.columns:
        combinado = desempenho_idx[desempenho_idx["modelo"] == "combinado"]
        if not combinado.empty:
            auc_territorio = float(combinado["auc"].mean())

    cartoes_idx = [
        indice_risco(linha_idx, limiar, horizonte, auc_territorio,
                     cod_idx == COD_FOCO),
        indice_transmissao(serie_idx, regra_r3, lift_r3),
        indice_clima(clima_municipio_idx, clima_atual_idx),
        indice_dado(linha_idx),
    ]
    for coluna_idx, cartao_html in zip(st.columns(4), cartoes_idx):
        coluna_idx.markdown(cartao_html, unsafe_allow_html=True)

    # ---- quadro dos 34 municipios ---------------------------------------
    st.subheader("O territorio agora")
    st.caption(
        f"Os {n_municipios} municipios ordenados pela probabilidade de alerta, "
        "cada um na sua semana mais recente -- series municipais podem fechar "
        "antes da de Brasilia."
    )

    # Uma linha por municipio: a mais recente de cada serie, porque municipio
    # pequeno as vezes fecha a semana antes do foco.
    recorte = painel.sort_values("se_codigo").groupby("cod_ibge").tail(1)
    quadro = recorte.sort_values("probabilidade_alerta", ascending=False).copy()
    quadro["tendencia"] = quadro["razao_mm3_mm8"].map(seta_tendencia)

    tabela = pd.DataFrame({
        "Municipio": quadro["municipio"].values,
        "Semana": [formatar_semana(s) for s in quadro["se_codigo"]],
        "Casos est.": quadro["casos_est"].values,
        "Incidencia /100 mil": quadro["incidencia_100k"].values,
        "Risco": quadro["risco"].astype(str).values,
        "Prob. de alerta": (quadro["probabilidade_alerta"] * 100).values,
        "Tendencia": quadro["tendencia"].values,
    })

    def _pintar_risco(coluna: pd.Series) -> list[str]:
        estilos = []
        for valor in coluna:
            fundo = CORES_RISCO.get(valor)
            if fundo is None:
                estilos.append("")
                continue
            texto = TEXTO_SOBRE_RISCO.get(valor, TEXTO)
            estilos.append(
                f"background-color:{fundo};color:{texto};font-weight:600"
            )
        return estilos

    def _pintar_tendencia(coluna: pd.Series) -> list[str]:
        estilos = []
        for valor in coluna:
            cor = CORES_TENDENCIA.get(valor[:1], NEUTRO_600) if valor else NEUTRO_600
            estilos.append(f"color:{cor};font-weight:600")
        return estilos

    st.dataframe(
        tabela.style
        .apply(_pintar_risco, subset=["Risco"])
        .apply(_pintar_tendencia, subset=["Tendencia"]),
        hide_index=True, width="stretch", height=520,
        column_config={
            "Casos est.": st.column_config.NumberColumn(
                format="%.0f",
                help="Nowcasting da semana mais recente do municipio.",
            ),
            "Incidencia /100 mil": st.column_config.NumberColumn(format="%.1f"),
            "Prob. de alerta": st.column_config.ProgressColumn(
                format="%.0f%%", min_value=0, max_value=100,
                help=f"Probabilidade de risco alto ou muito alto em "
                     f"{horizonte} semanas.",
            ),
            "Tendencia": st.column_config.TextColumn(
                help="Razao entre as medias moveis de 3 e 8 semanas da "
                     "incidencia: acima de 1,1 sobe, abaixo de 0,9 cai.",
            ),
        },
    )

    # ---- alarmes de variaveis -------------------------------------------
    st.subheader("Alarmes de variaveis")
    alarmes_estado = carregar_alarmes()

    if alarmes_estado is None:
        st.info(
            "`saidas/alarmes.json` nao encontrado. Gere-o com "
            "`python src/vigia/executar_alarmes.py`: ele mede cada regra "
            "contra o historico 2014-2026 e grava os alarmes da semana."
        )
    else:
        ativos = alarmes_estado.get("alarmes", [])
        regras_info = alarmes_estado.get("regras", {})
        todas_regras = regras_info.get("regras", [])
        catalogo = {r["id"]: r for r in todas_regras}
        aprovadas = [r for r in todas_regras if r.get("aprovada")]

        if ativos:
            # Ja chegam ordenados por lift historico decrescente: o alarme com
            # mais sustentacao no passado abre a lista.
            for alarme in ativos:
                nome_regra = catalogo.get(alarme["id"], {}).get("nome", alarme["id"])
                st.markdown(
                    '<div class="vigia-alarme">'
                    '<div class="vigia-alarme-titulo">'
                    f'{html.escape(alarme["municipio"])} -- {html.escape(nome_regra)}'
                    '</div>'
                    f'<div class="vigia-alarme-frase">{html.escape(alarme["frase"])}</div>'
                    '<div class="vigia-alarme-meta">'
                    f'Regra {html.escape(alarme["id"])} · gatilho p_rt1 '
                    f'{alarme["valor_gatilho"]:.2f} · olhe {alarme["lag_semanas"]} '
                    f'semanas a frente · lift historico {alarme["lift_historico"]:.1f}x '
                    f'· SE {formatar_semana(alarme["semana"])}'
                    '</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            vigiadas = ", ".join(
                f"{r['id']} ({r['nome'].lower()})" for r in aprovadas
            )
            complemento = (
                f" As regras com evidencia historica seguem vigiadas: {vigiadas}."
                if vigiadas else ""
            )
            st.markdown(
                '<div class="vigia-sem-alarme">Nenhum alarme de variavel '
                "ligado nesta semana (medido na SE "
                f'{formatar_semana(alarmes_estado["gerado_da_semana"])}).'
                f"{html.escape(complemento)}</div>",
                unsafe_allow_html=True,
            )

        with st.expander("Metodologia: todas as regras medidas, aprovadas ou nao"):
            st.caption(
                f"Base: {regras_info.get('base', '?')}. Medido em "
                f"{regras_info.get('gerado_em', '?')}. Regras reprovadas "
                "aparecem aqui por transparencia e nunca disparam alarme."
            )
            st.caption(regras_info.get("metodo", ""))

            if todas_regras:
                medicao = pd.DataFrame({
                    "Regra": [r["id"] for r in todas_regras],
                    "Nome": [r["nome"] for r in todas_regras],
                    "Condicao": [r["condicao"] for r in todas_regras],
                    "Horizonte (sem.)": [r["lag_semanas"] for r in todas_regras],
                    "Episodios": [r["n_episodios"] for r in todas_regras],
                    "Lift mediano": [r["lift_mediano"] for r in todas_regras],
                    "Acima do normal (%)": [
                        r["frac_lift_acima_1"] * 100 for r in todas_regras
                    ],
                    "Situacao": [
                        "aprovada" if r["aprovada"] else "reprovada"
                        for r in todas_regras
                    ],
                })

                def _pintar_situacao(coluna: pd.Series) -> list[str]:
                    return [
                        f"background-color:{ACENTO_200};color:{TEXTO};font-weight:600"
                        if v == "aprovada" else f"color:{NEUTRO_600}"
                        for v in coluna
                    ]

                st.dataframe(
                    medicao.style.apply(_pintar_situacao, subset=["Situacao"]),
                    hide_index=True, width="stretch",
                    column_config={
                        "Lift mediano": st.column_config.NumberColumn(format="%.2f"),
                        "Acima do normal (%)": st.column_config.NumberColumn(
                            format="%.0f%%"
                        ),
                    },
                )

                for regra in todas_regras:
                    st.markdown(
                        f"- **{regra['id']} -- {regra['nome']}:** "
                        f"{regra['frase_evidencia']}"
                    )

            por_municipio = regras_info.get("por_municipio", {})
            for regra in aprovadas:
                medidas = por_municipio.get(regra["id"], [])
                if not medidas:
                    continue
                st.markdown(
                    f"**Onde {regra['id']} ({regra['nome'].lower()}) mais se "
                    "confirmou** -- lift historico por municipio, so quem tem "
                    "8 ou mais episodios:"
                )
                st.dataframe(
                    pd.DataFrame(medidas).rename(columns={
                        "municipio": "Municipio", "n": "Episodios",
                        "lift": "Lift historico", "cod_ibge": "Codigo IBGE",
                    })[["Municipio", "Episodios", "Lift historico"]],
                    hide_index=True, width="stretch", height=280,
                    column_config={
                        "Lift historico": st.column_config.NumberColumn(
                            format="%.2f"
                        ),
                    },
                )

    # ---- clima dos proximos 14 dias --------------------------------------
    st.subheader("Clima dos proximos 14 dias")
    clima = carregar_clima_futuro()

    if clima is None:
        st.caption(
            "`saidas/clima_futuro.json` nao encontrado. Gere-o com "
            "`python src/vigia/executar_clima_futuro.py` (previsao Open-Meteo "
            "para os municipios do territorio)."
        )
    else:
        se_corrente = semana_epidemiologica(pd.Timestamp.today())
        coletado = int(clima.get("coletado_para_semana", 0))
        if coletado != se_corrente:
            st.caption(
                f"Previsao coletada na SE {formatar_semana(coletado)}; a "
                f"semana corrente e {formatar_semana(se_corrente)}. Rode "
                "`python src/vigia/executar_clima_futuro.py` para atualizar."
            )

        por_codigo = {int(m["cod_ibge"]): m for m in clima.get("municipios", [])}
        # Brasilia abre a lista; depois, os cinco municipios que o modelo poe
        # no topo da probabilidade de alerta -- e onde a chuva a frente mais
        # importa para quem decide a semana.
        prioridade = [COD_FOCO] + [
            int(c) for c in quadro["cod_ibge"] if int(c) != COD_FOCO
        ][:5]
        linhas_clima = []
        for codigo in prioridade:
            municipio_clima = por_codigo.get(codigo)
            if municipio_clima is None:
                continue
            linhas_clima.append({
                "Municipio": municipio_clima["municipio"],
                "Chuva 7 dias (mm)": municipio_clima["chuva_7d_mm"],
                "Chuva 14 dias (mm)": municipio_clima["chuva_14d_mm"],
                "Dias de chuva (14 d)": municipio_clima["dias_chuva_14d"],
                "Temp. media (C)": municipio_clima["temp_media_14d"],
            })

        if not linhas_clima:
            st.caption(
                "A previsao coletada nao cobre os municipios em foco nesta "
                "semana."
            )
        else:
            st.dataframe(
                pd.DataFrame(linhas_clima),
                hide_index=True, width="stretch",
                column_config={
                    "Chuva 7 dias (mm)": st.column_config.NumberColumn(
                        format="%.1f"
                    ),
                    "Chuva 14 dias (mm)": st.column_config.NumberColumn(
                        format="%.1f"
                    ),
                    "Dias de chuva (14 d)": st.column_config.NumberColumn(
                        format="%d",
                        help="Dias com 1 mm ou mais, o mesmo criterio da "
                             "serie observada.",
                    ),
                    "Temp. media (C)": st.column_config.NumberColumn(
                        format="%.1f"
                    ),
                },
            )
            st.caption(
                "Previsao Open-Meteo para Brasilia e os cinco municipios com "
                "maior probabilidade de alerta. Leitura honesta: chuva e "
                "temperatura a frente dizem se o territorio fica receptivo ao "
                "mosquito nas proximas semanas -- **nao entram no modelo**, "
                "que preve com o clima ja observado. Dias sem previsao ficam "
                "fora das somas e da media."
            )
        faltantes = clima.get("faltantes", [])
        if faltantes:
            st.caption(
                f"Sem previsao para {len(faltantes)} municipio(s) nesta coleta."
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

        # Indicadores do Censo 2022 por RA. Sao eles que dao conteudo proprio a
        # cada area: sem eles o mapa so sabe repetir o tamanho da populacao.
        vulnerabilidade = carregar_vulnerabilidade_ras()
        if vulnerabilidade is not None:
            regioes = regioes.merge(
                vulnerabilidade.drop(columns=["ra_nome"]),
                on="cod_subdistrito", how="left",
            )

        indicadores = {
            "Populacao": ("populacao", "habitantes"),
            "Densidade": ("densidade_hab_km2", "hab./km2"),
        }
        if vulnerabilidade is not None:
            indicadores.update({
                "Vulnerabilidade": ("indice_vulnerabilidade", "indice (0 a 100)"),
                "Esgoto inadequado": ("esgoto_inadequado_pct", "% dos domicilios"),
                "Sem agua de rede": ("sem_agua_rede_pct", "% dos domicilios"),
                "Lixo sem coleta": ("lixo_sem_coleta_pct", "% dos domicilios"),
                "Sem bueiro": ("sem_bueiro_pct", "% dos domicilios"),
                "Rua sem pavimento": ("sem_pavimento_pct", "% dos domicilios"),
            })

        setores = carregar_setores()
        escala = "Regiao Administrativa"
        if setores is not None:
            escala = st.radio(
                "Escala do mapa",
                ["Regiao Administrativa", "Quadra (setor censitario)"],
                horizontal=True,
                index=1,
                help="O setor censitario e a menor unidade que o IBGE publica: "
                     "algumas quadras, cerca de trezentos domicilios.",
            )

        escolhido = st.radio(
            "Indicador exibido no mapa",
            list(indicadores),
            horizontal=True,
            index=2 if vulnerabilidade is not None else 0,
        )
        coluna, rotulo = indicadores[escolhido]
        if coluna not in regioes:
            coluna, rotulo = "populacao", "habitantes"

        explicacao = {
            "indice_vulnerabilidade":
                "Media das tres dimensoes abaixo, cada uma como distancia relativa "
                "dentro do proprio DF. Ordena as RAs numa leitura so; nao pondera as "
                "dimensoes, porque nao ha estudo local que sustente pesos diferentes.",
            "esgoto_inadequado_pct":
                "Domicilios com esgoto em fossa rudimentar, vala ou outra forma -- "
                "agua parada exposta.",
            "sem_agua_rede_pct":
                "Domicilios sem ligacao a rede geral. Levam ao armazenamento em "
                "caixas e toneis, criadouro classico do Aedes aegypti.",
            "lixo_sem_coleta_pct":
                "Lixo queimado, enterrado ou com outro destino, que acumula "
                "recipientes com agua parada.",
            "sem_bueiro_pct":
                "Domicilios em face de rua sem boca de lobo. E a drenagem que "
                "decide se a chuva escoa ou empoca, e o Aedes se cria em agua "
                "parada, nao corrente -- por isso este e o indicador de fluxo "
                "das aguas na escala em que o mosquito vive.",
            "sem_pavimento_pct":
                "Domicilios em face de rua sem pavimento, onde a agua empoca "
                "mesmo havendo drenagem.",
        }
        if coluna in explicacao:
            st.caption(
                explicacao[coluna] + " Fonte: Censo 2022 (IBGE), agregados por "
                "subdistrito -- no DF, o subdistrito e a Regiao Administrativa."
            )

        if escala.startswith("Quadra"):
            desenhar_mapa_setores(setores, coluna, rotulo)
        else:
            # Classes por quantil, e nao escala linear. A populacao das RAs vai de
            # 2.286 a 348.000: numa escala linear, 18 das 31 caem nos dois tons mais
            # claros da rampa -- quase brancos sobre um mapa base quase branco, e
            # indistinguiveis entre si. Por quantil cada faixa recebe seis ou sete
            # RAs, e todas se separam.
            faixas = pd.qcut(regioes[coluna], q=4, duplicates="drop")
            # A borda esquerda que o `qcut` devolve fica um pouco abaixo do minimo,
            # para incluir o proprio minimo no intervalo. No rotulo isso aparecia
            # como "-0 a 3"; o valor observado e o que interessa a quem le.
            limites = [float(regioes[coluna].min())] + [
                float(categoria.right) for categoria in faixas.cat.categories
            ]
            rotulos = [
                f"{formatar_faixa(limites[i])} a {formatar_faixa(limites[i + 1])}"
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
            st.plotly_chart(mapa_ras, width="stretch", config=CONFIG_GRAFICO)
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
    st.plotly_chart(figura, width="stretch", config=CONFIG_GRAFICO)

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
    st.plotly_chart(canal, width="stretch", config=CONFIG_GRAFICO)
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

        if sinalizar_provisorio and r["dado_provisorio"] == 1:
            st.warning(
                f"Notificacao ainda incompleta em Brasilia nesta semana "
                f"({r['completude']:.0%} digitado). Os casos observados tendem a subir."
            )

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
        st.plotly_chart(linha_auc, width="stretch", config=CONFIG_GRAFICO)

# ------------------------------------------------------- Dicionario de dados
with aba_dicionario:
    dicionario = carregar_dicionario()

    if dicionario is None:
        st.warning(
            "Dicionario nao encontrado. Gere-o com `gerar_dicionario.py` para "
            "que esta aba mostre as colunas da base."
        )
    else:
        st.subheader("As colunas da base analitica")
        st.markdown(
            "Cada linha e uma coluna da base municipio-semana que sustenta a "
            "previsao. O campo **papel** diz como ela entra: *preditor "
            "essencial* e o que a previsao nao dispensa, *preditor* e tudo que "
            "o modelo usa, *origem do alvo* e a coluna de onde sai o desfecho, "
            "e *apoio* sustenta calculo, conferencia e painel sem entrar no "
            "treino."
        )

        preditoras = int(dicionario["papel"].str.startswith("preditor").sum())
        essenciais = int((dicionario["papel"] == "preditor essencial").sum())
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Colunas na base", len(dicionario))
        col_b.metric("Preditoras do modelo", preditoras)
        col_c.metric("Essenciais", essenciais)

        filtro_a, filtro_b = st.columns(2)
        blocos = ["todos"] + sorted(dicionario["bloco"].unique())
        papeis = ["todos"] + sorted(dicionario["papel"].unique())
        bloco_escolhido = filtro_a.selectbox("Bloco", blocos)
        papel_escolhido = filtro_b.selectbox("Papel na previsao", papeis)
        busca = st.text_input(
            "Buscar", placeholder="nome da coluna, descricao ou fonte",
            label_visibility="collapsed",
        )

        visivel = dicionario
        if bloco_escolhido != "todos":
            visivel = visivel[visivel["bloco"] == bloco_escolhido]
        if papel_escolhido != "todos":
            visivel = visivel[visivel["papel"] == papel_escolhido]
        if busca:
            alvo = (visivel["coluna"] + " " + visivel["descricao"] + " "
                    + visivel["fonte"])
            visivel = visivel[alvo.str.contains(busca, case=False, na=False)]

        st.caption(
            f"{len(visivel)} de {len(dicionario)} colunas"
            if len(visivel) != len(dicionario) else f"{len(dicionario)} colunas"
        )
        st.dataframe(
            visivel.rename(columns={
                "coluna": "Coluna", "bloco": "Bloco", "tipo": "Tipo",
                "papel": "Papel", "preenchida_pct": "Preenchida (%)",
                "fonte": "Fonte", "descricao": "Descricao",
            }),
            hide_index=True, width="stretch", height=520,
            column_config={
                "Preenchida (%)": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

        st.download_button(
            "Baixar o dicionario completo (CSV)",
            data=dicionario.to_csv(index=False).encode("utf-8"),
            file_name="dicionario_de_dados_vigia.csv",
            mime="text/csv",
            help="As 124 colunas com bloco, papel, fonte e descricao -- "
                 "o arquivo inteiro, sem os filtros da tela.",
        )

        st.caption(
            "Nenhuma variavel enxerga o futuro: medias moveis sao deslocadas em "
            "uma semana, as anomalias sazonais e o canal endemico usam apenas "
            "anos anteriores, e a dobra de validacao corta pela data que o alvo "
            "observa. As colunas abaixo de 100% de preenchimento faltam por "
            "construcao -- o canal endemico exige anos anteriores, e o primeiro "
            "ano da serie nao os tem."
        )

st.divider()
st.caption(
    "Fontes: InfoDengue (Fiocruz/FGV) para casos e clima observado; Open-Meteo "
    "para a previsao de clima; IBGE para populacao e malha municipal. "
    "Ferramenta de apoio a vigilancia -- nao substitui a analise da equipe de "
    "vigilancia epidemiologica local."
)
