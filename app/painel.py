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
CAMINHO_GLOSSARIO = RAIZ / "docs" / "glossario.csv"

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
# escuro; as de comparacao vao mais claras e tracejadas, para nao disputar.
# A cor e fixada por modelo, e nao por ordem: com uma lista de tres cores, o
# quarto modelo voltava a primeira e o combinado -- o modelo em operacao --
# saia no mesmo cinza da referencia.
NOMES_MODELO = {
    "referencia": "Referência (persistência)",
    "interpretavel": "Interpretável (logística)",
    "aprendizado": "Aprendizado (LightGBM)",
    "combinado": "Combinado (em operação)",
}
CORES_MODELO = {
    "Referência (persistência)": "#b7b7ba",
    "Interpretável (logística)": "#9fb8d0",
    "Aprendizado (LightGBM)": "#5980a6",
    "Combinado (em operação)": "#1d2d3d",
}
TRACO_MODELO = {
    "Referência (persistência)": "dot",
    "Interpretável (logística)": "dash",
    "Aprendizado (LightGBM)": "dash",
    "Combinado (em operação)": "solid",
}

# Municipio foco do projeto. A RIDE-DF entra como territorio de comparacao.
FOCO = "Brasília"
COD_FOCO = 5300108

# Os nomes chegam sem acento da base (o pipeline grava ASCII de proposito, para
# nao quebrar arquivo nem chave). A tela fala portugues: a grafia oficial entra
# so na exibicao, e quem nao esta aqui passa como veio.
MUNICIPIOS_COM_ACENTO = {
    "Brasilia": "Brasília", "Abadiania": "Abadiânia",
    "Agua Fria de Goias": "Água Fria de Goiás",
    "Aguas Lindas de Goias": "Águas Lindas de Goiás", "Alexania": "Alexânia",
    "Alto Paraiso de Goias": "Alto Paraíso de Goiás",
    "Cocalzinho de Goias": "Cocalzinho de Goiás",
    "Corumba de Goias": "Corumbá de Goiás", "Flores de Goias": "Flores de Goiás",
    "Goianesia": "Goianésia", "Luziania": "Luziânia",
    "Mimoso de Goias": "Mimoso de Goiás", "Niquelandia": "Niquelândia",
    "Pirenopolis": "Pirenópolis",
    "Santo Antonio do Descoberto": "Santo Antônio do Descoberto",
    "Sao Joao d'Alianca": "São João d'Aliança", "Simolandia": "Simolândia",
    "Unai": "Unaí", "Valparaiso de Goias": "Valparaíso de Goiás",
    "Vila Propicio": "Vila Propício",
}
RAS_COM_ACENTO = {
    "Aguas Claras": "Águas Claras", "Brazlandia": "Brazlândia",
    "Candangolandia": "Candangolândia", "Ceilandia": "Ceilândia",
    "Guara": "Guará", "Itapoa": "Itapoã", "Jardim Botanico": "Jardim Botânico",
    "Nucleo Bandeirante": "Núcleo Bandeirante", "Paranoa": "Paranoá",
    "Sao Sebastiao": "São Sebastião", "Varjao": "Varjão",
}
# Nomes das regras de alarme, gravados em ASCII por alarmes.py. Aparecem na
# linha de estado do Monitor e no titulo do cartao de alarme.
REGRAS_COM_ACENTO = {
    "Transmissao crescendo": "Transmissão crescendo",
    "Aceleracao epidemica": "Aceleração epidêmica",
    "Janela termica com chuva": "Janela térmica com chuva",
    "Seca x falta de rede de agua": "Seca x falta de rede de água",
}
GRAFIA = {**MUNICIPIOS_COM_ACENTO, **RAS_COM_ACENTO, **REGRAS_COM_ACENTO}


def acentuar(nome: str) -> str:
    """Grafia com acento de um municipio, RA ou regra, para exibicao."""
    return GRAFIA.get(nome, nome)


# As variaveis que mais pesaram na previsao chegam pelo nome da coluna. Para
# quem le o painel, `casos_est_mm3` nao diz nada; a descricao curta diz.
FATORES_LEGIVEIS = {
    "incidencia_100k": "incidência da semana",
    "incidencia_lag1": "incidência de 1 semana atrás",
    "incidencia_lag2": "incidência de 2 semanas atrás",
    "incidencia_lag4": "incidência de 4 semanas atrás",
    "incidencia_mm3": "incidência média de 3 semanas",
    "incidencia_mm8": "incidência média de 8 semanas",
    "casos_est_mm3": "casos das últimas 3 semanas",
    "casos_est_mm8": "casos das últimas 8 semanas",
    "razao_mm3_mm8": "aceleração da curva",
    "variacao_semanal": "variação semanal",
    "log_pop": "porte do município",
    "semana": "época do ano",
    "canal_mediana": "padrão histórico da época",
    "canal_q3": "limite esperado da época",
    "Rt": "ritmo de transmissão (Rt)",
    "p_rt1": "chance de transmissão crescente",
    "receptivo": "clima receptivo ao mosquito",
    "transmissao": "transmissão sustentada",
    "nivel_inc": "nível de incidência",
    "Rt_lag1": "Rt de 1 semana atrás",
    "Rt_lag2": "Rt de 2 semanas atrás",
    "p_rt1_lag1": "chance de transmissão crescente 1 semana atrás",
    "p_rt1_lag2": "chance de transmissão crescente 2 semanas atrás",
    "sem fator dominante": "sem fator dominante",
}


def fatores_legiveis(texto: str) -> str:
    """Troca os nomes de coluna da explicacao do modelo por descricoes."""
    if not isinstance(texto, str) or not texto:
        return "sem fator dominante"
    return ", ".join(FATORES_LEGIVEIS.get(f.strip(), f.strip())
                     for f in texto.split(","))

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

# Eixo de datas sem nome de mes: o Plotly so escreve "Jan", "Apr" em ingles.
# Em janela curta vai mes/ano; em janela de anos, so o ano.
EIXO_DATAS = {
    "tickformatstops": [
        {"dtickrange": [None, "M11"], "value": "%m/%Y"},
        {"dtickrange": ["M12", None], "value": "%Y"},
    ],
    "hoverformat": "semana de %d/%m/%Y",
}

st.set_page_config(page_title="VIGIA-Dengue", page_icon="\U0001F99F", layout="wide")

# Um gabarito unico evita repetir fonte e fundo em cada figura. O fundo
# transparente deixa o grafico assentar sobre a superficie do tema. Os
# separadores sao os brasileiros: virgula decimal, ponto de milhar.
pio.templates["vigia"] = go.layout.Template(layout={
    "separators": ",.",
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

      /* Abas em caixa alta condensada, como rotulos de bancada. O seletor e
         pelo papel da aba: o botao com data-baseweb virou uma div numa versao
         do Streamlit, e a regra deixou de pegar sem ninguem perceber. */
      [role="tab"] p {
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
      /* Corpo no formato do cartao de previsao do tempo: icone a esquerda,
         nivel em destaque e, embaixo dele, o que o numero quer dizer e o que
         fazer a respeito. */
      .vigia-indice-corpo {
        display: flex;
        gap: 0.75rem;
        align-items: flex-start;
      }
      .vigia-indice-icone {
        width: 2.2rem;
        height: 2.2rem;
        flex: none;
        color: #2c455d;
        margin-top: 0.1rem;
      }
      .vigia-indice-icone svg { width: 100%; height: 100%; display: block; }

      /* Botoes de medida do grafico semanal: no celular os quatro nao cabem
         numa linha, e sem quebra o ultimo sumia cortado na borda. */
      [data-testid="stButtonGroup"] [role="radiogroup"] {
        flex-wrap: wrap;
        row-gap: 0.35rem;
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
      .vigia-indice-conselho {
        color: #55595c;
        font-size: 0.9rem;
        line-height: 1.35;
        margin-top: 0.2rem;
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
    dados["municipio"] = dados["municipio"].map(acentuar)

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

    Vem de `docs/dicionario_de_dados.csv`, reescrito por `executar_dicionario.py`
    a cada vez que a base muda -- assim a documentacao no ar nunca descreve uma
    base que deixou de existir.
    """
    if not CAMINHO_DICIONARIO.exists():
        return None
    return pd.read_csv(CAMINHO_DICIONARIO)


@st.cache_data
def carregar_glossario():
    """Glossario gerado junto com o dicionario, por `executar_dicionario.py`."""
    if not CAMINHO_GLOSSARIO.exists():
        return None
    return pd.read_csv(CAMINHO_GLOSSARIO)


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
        while dia.day_of_week != 5:  # 5 = sabado
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
    numero = _decimal(razao, 2)
    if razao >= 1.1:
        return f"▲ {numero}"
    if razao <= 0.9:
        return f"▼ {numero}"
    return f"▬ {numero}"


def chip(texto: str, fundo: str, cor_texto: str) -> str:
    return (
        f'<span class="vigia-chip" style="background:{fundo};'
        f'color:{cor_texto}">{html.escape(texto)}</span>'
    )


def _milhar(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def _decimal(valor: float, casas: int = 1) -> str:
    """Numero com virgula decimal e ponto de milhar, como se le no Brasil."""
    return (f"{valor:,.{casas}f}".replace(",", "\x00").replace(".", ",")
            .replace("\x00", "."))


def _sinal(valor: float, casas: int = 1) -> str:
    """Diferenca com sinal explicito; o Streamlit le o "-" para a seta."""
    return ("+" if valor >= 0 else "-") + _decimal(abs(valor), casas)


def formato_br(tabela: pd.DataFrame, casas: dict[str, int]):
    """Styler que exibe as colunas numericas no formato brasileiro.

    O valor por baixo continua numerico, entao ordenar pela coluna segue
    ordenando por numero, e nao pelo texto "12,4".
    """
    return tabela.style.format(
        {coluna: (lambda v, c=c: "" if pd.isna(v) else _decimal(v, c))
         for coluna, c in casas.items() if coluna in tabela.columns}
    )


def _svg(corpo: str) -> str:
    """Icone de traco, na cor do texto ao redor, como os de previsao do tempo."""
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{corpo}</svg>')


# Um icone por indice. Desenhados aqui, em SVG inline: o painel nao depende de
# fonte de icones nem de imagem externa.
ICONES = {
    "mosquito": _svg(
        '<circle cx="12" cy="5" r="1.6"/><path d="M12 3.4 10.6 1.5"/>'
        '<path d="M12 6.6v10.4"/>'
        '<path d="M12 9c-2.5-3.6-6.4-4-8-2.4 1.2 2 4.6 3.4 8 3.4"/>'
        '<path d="M12 9c2.5-3.6 6.4-4 8-2.4-1.2 2-4.6 3.4-8 3.4"/>'
        '<path d="M11.2 12.5 7.5 14l-2 3.5M12.8 12.5l3.7 1.5 2 3.5"/>'
        '<path d="M11.4 15 8.6 18l-.8 3.5M12.6 15l2.8 3 .8 3.5"/>'),
    "transmissao": _svg(
        '<path d="M3 17l5.5-5.5 4 4L21 7"/><path d="M15 7h6v6"/>'),
    "clima": _svg(
        '<path d="M7 15.5a4 4 0 1 1 .9-7.9A5.2 5.2 0 0 1 17.6 9a3.3 3.3 0 0 1 '
        '.4 6.5H7z"/><path d="M8.5 18.5 7.5 21M12.5 18.5l-1 2.5M16.5 18.5l-1 2.5"/>'),
    "dado": _svg(
        '<rect x="5" y="4" width="14" height="17" rx="2"/>'
        '<path d="M9 4V2.8h6V4"/><path d="M8.5 10h7M8.5 13.5h7M8.5 17h4"/>'),
}


def cartao_indice(titulo: str, estado: str, nivel: str, leitura: str,
                  evidencia: str, icone: str = "", conselho: str = "") -> str:
    """Um indice da semana em cartao, no formato de previsao do tempo.

    Todo texto passa por escape: nome de municipio e frase de evidencia vem de
    dado e entram em HTML cru. O icone nao: e o SVG fixo de ICONES.
    """
    cor = COR_INDICE.get(estado, COR_INDICE["sem_dado"])
    evidencia_html = (
        f'<div class="vigia-indice-evidencia">{html.escape(evidencia)}</div>'
        if evidencia else ""
    )
    conselho_html = (
        f'<div class="vigia-indice-conselho">{html.escape(conselho)}</div>'
        if conselho else ""
    )
    icone_html = (f'<div class="vigia-indice-icone">{ICONES[icone]}</div>'
                  if icone in ICONES else "")
    return (
        '<div class="vigia-indice">'
        '<div class="vigia-indice-topo">'
        f'<span class="vigia-indice-titulo">{html.escape(titulo)}</span>'
        f'<span class="vigia-indice-ponto" style="background:{cor}" '
        f'title="{html.escape(nivel)}"></span>'
        '</div>'
        '<div class="vigia-indice-corpo">'
        f'{icone_html}'
        '<div>'
        f'<div class="vigia-indice-nivel">{html.escape(nivel)}</div>'
        f'<div class="vigia-indice-leitura">{html.escape(leitura)}</div>'
        f'{conselho_html}'
        '</div></div>'
        f'{evidencia_html}'
        '</div>'
    )


def indice_risco(linha: pd.Series, limiar: float, horizonte: int,
                 auc_territorio: float | None, eh_foco: bool) -> str:
    """Probabilidade do modelo combinado para o horizonte do alerta."""
    # "Previsao", e nao "risco": ao lado do chip com o risco de hoje, um
    # cartao chamado "Risco em 4 semanas: baixo" parecia contradize-lo.
    titulo = f"Previsão para {horizonte} semanas"
    prob = linha.get("probabilidade_alerta")
    if prob is None or pd.isna(prob):
        return cartao_indice(
            titulo, "sem_dado", "Sem previsão",
            "A semana mais recente não tem os preditores essenciais.", "",
            icone="mosquito")

    # O conselho segue o que o Ministerio da Saude repete em toda campanha:
    # o criadouro e a acao de cada um, e febre e motivo de procurar a rede.
    if prob >= limiar:
        estado, nivel = "alerta", "Alerta"
        conselho = ("Intensifique o combate aos criadouros. Com febre, procure "
                    "uma unidade de saúde.")
    elif prob >= 0.5:
        estado, nivel = "atencao", "Atenção"
        conselho = "Reforce a busca por água parada e o uso de repelente."
    else:
        estado, nivel = "calmo", "Sem alerta"
        conselho = "Mantenha a rotina: elimine água parada uma vez por semana."
    leitura = (f"{prob:.0%} de chance de risco alto ou muito alto em "
               f"{horizonte} semanas.")

    # O VPP medido so vale para Brasilia no limiar em que foi medido; mexer no
    # controle do limiar troca a evidencia pela AUC do territorio.
    if eh_foco and abs(limiar - LIMIAR_DO_VPP) < 1e-9:
        evidencia = (
            f"Validado em 2019-2025: em Brasília, no limiar de "
            f"{LIMIAR_DO_VPP:.0%}, {VPP_BRASILIA_LIMIAR_080:.0%} dos alertas "
            "se confirmaram.")
    elif auc_territorio is not None:
        evidencia = (
            "Validação temporal 2019-2025 nos 34 municípios: AUC de "
            f"{_decimal(auc_territorio, 3)}.")
    else:
        evidencia = ""
    return cartao_indice(titulo, estado, nivel, leitura, evidencia,
                         icone="mosquito", conselho=conselho)


def indice_transmissao(serie: pd.DataFrame, regra: dict | None,
                       lift_municipal: float | None) -> str:
    """p(Rt>1) das duas ultimas semanas -- a variavel da regra R3."""
    titulo = "Transmissão"
    if "p_rt1" not in serie.columns or serie["p_rt1"].dropna().empty:
        return cartao_indice(
            titulo, "sem_dado", "Sem dado",
            "Probabilidade de Rt acima de 1 indisponível nesta base.", "",
            icone="transmissao")

    ultimos = serie["p_rt1"].dropna().iloc[-2:]
    agora = float(ultimos.iloc[-1])
    antes = float(ultimos.iloc[0]) if len(ultimos) > 1 else None

    if antes is not None and agora >= 0.9 and antes >= 0.9:
        estado, nivel = "alerta", "Crescendo"
        conselho = ("Duas semanas seguidas em alta: costuma anteceder aumento "
                    "de casos.")
    elif agora >= 0.9:
        estado, nivel = "atencao", "Subindo"
        conselho = "Cada caso começa a gerar mais de um. Vale acompanhar."
    else:
        estado, nivel = "calmo", "Estável"
        conselho = "O ritmo de novos casos não está acelerando."

    leitura = f"Probabilidade de Rt acima de 1: {agora:.0%} nesta semana"
    leitura += f", {antes:.0%} na anterior." if antes is not None else "."

    if regra is None:
        evidencia = ""
    elif lift_municipal is not None:
        evidencia = (
            "Aqui, quando passou de 90% por duas semanas, a incidência "
            f"{regra.get('lag_semanas', 4)} semanas depois foi "
            f"{_decimal(lift_municipal)}x a normal da época.")
    else:
        evidencia = (
            "No território, acima de 90% por duas semanas antecedeu incidência "
            f"{_decimal(regra['lift_mediano'])}x a normal da época, em "
            f"{_milhar(regra['n_episodios'])} episódios desde 2014.")
    return cartao_indice(titulo, estado, nivel, leitura, evidencia,
                         icone="transmissao", conselho=conselho)


def indice_clima(clima_municipio: dict | None, clima_atual: bool) -> str:
    """Receptividade climatica dos proximos 14 dias -- contexto, nao previsao."""
    titulo = "Clima para o Aedes (14 dias)"
    contexto = ("Contexto, não previsão: no histórico do território, gatilhos "
                "climáticos sozinhos não anteciparam dengue.")
    if clima_municipio is None:
        return cartao_indice(
            titulo, "sem_dado", "Sem previsão",
            "Previsão do tempo indisponível para este município.", contexto,
            icone="clima")

    temp = clima_municipio.get("temp_media_14d")
    dias = int(clima_municipio.get("dias_chuva_14d") or 0)
    chuva = float(clima_municipio.get("chuva_14d_mm") or 0)
    na_faixa = (temp is not None
                and FAIXA_TERMICA_AEDES[0] <= temp <= FAIXA_TERMICA_AEDES[1])

    if not na_faixa or dias == 0:
        estado, nivel = "calmo", "Pouco favorável"
        conselho = "Tempo desfavorável ao mosquito nos próximos dias."
    elif dias >= DIAS_CHUVA_FREQUENTE:
        estado, nivel = "elevado", "Muito favorável"
        conselho = ("Esvazie pratos de planta, calhas e pneus depois de cada "
                    "chuva.")
    else:
        estado, nivel = "atencao", "Favorável"
        conselho = "Chuva e calor ajudam o mosquito: olho em recipientes com água."

    temp_txt = ("temperatura indisponível" if temp is None
                else f"média de {temp:.0f} °C")
    leitura = f"{chuva:.0f} mm em {dias} dias de chuva; {temp_txt}."
    if not clima_atual:
        contexto = "Previsão coletada em semana anterior. " + contexto
    return cartao_indice(titulo, estado, nivel, leitura, contexto,
                         icone="clima", conselho=conselho)


def indice_dado(linha: pd.Series) -> str:
    """Quanto da semana ja foi digitado -- a incerteza na ponta da serie."""
    titulo = "Qualidade do dado"
    completude = linha.get("completude")
    provisorio = linha.get("dado_provisorio") == 1
    tem_completude = completude is not None and pd.notna(completude)

    if not provisorio or (tem_completude and completude >= 0.9):
        estado, nivel = "calmo", "Consolidado"
        conselho = "Os números da semana já estão praticamente completos."
    elif tem_completude and completude >= 0.6:
        estado, nivel = "atencao", "Em consolidação"
        conselho = "Os números ainda podem subir um pouco."
    else:
        estado, nivel = "elevado", "Provisório"
        conselho = "Os números da semana ainda vão subir: leia como estimativa."

    leitura = (f"{_milhar(linha['casos'])} casos notificados de "
               f"{_milhar(linha['casos_est'])} estimados")
    leitura += f" ({completude:.0%} digitado)." if tem_completude else "."
    evidencia = ("A notificação chega com atraso; o nowcasting do InfoDengue "
                 "estima os casos que ainda vão entrar.")
    return cartao_indice(titulo, estado, nivel, leitura, evidencia,
                         icone="dado", conselho=conselho)


# O grafico semana a semana, no formato da previsao do tempo hora a hora:
# uma medida por vez, o valor escrito em cada ponto e a semana atual marcada.
# A cor de cada medida vem da paleta do sistema.
MEDIDAS_SEMANA = {
    "Casos": ("casos_est", ACENTO_800, lambda v: _milhar(v)),
    "Risco à frente": ("probabilidade_alerta", "#b25a33", lambda v: f"{v:.0%}"),
    # "26°", e nao "26°C": no celular doze rotulos com a unidade inteira
    # encostavam uns nos outros, e o botao ja diz que e temperatura.
    "Temperatura": ("tempmed", "#a2402f", lambda v: f"{v:.0f}°"),
    "Umidade": ("umidmed", ACENTO, lambda v: f"{v:.0f}%"),
}


def _transparente(cor: str, alfa: float) -> str:
    cor = cor.lstrip("#")
    r, g, b = (int(cor[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alfa})"


def grafico_semanal(serie: pd.DataFrame, medida: str, limiar: float,
                    horizonte: int, semanas: int = 12) -> go.Figure:
    """Ultimas semanas de uma medida, com o valor escrito em cada ponto.

    Em "Risco a frente" o eixo e a semana PREVISTA, e nao a semana em que a
    previsao foi feita: a probabilidade calculada na semana t fala do risco em
    t + horizonte. Por isso esse grafico avanca `horizonte` semanas alem do
    dado, e esse trecho sai tracejado, sobre um fundo que o marca como
    previsao.
    """
    coluna, cor, formatar = MEDIDAS_SEMANA[medida]
    recente = serie.sort_values("data_ini_se").tail(semanas).copy()
    ultima_data = recente["data_ini_se"].iloc[-1]
    deslocamento = horizonte if coluna == "probabilidade_alerta" else 0
    recente["alvo"] = recente["data_ini_se"] + pd.Timedelta(weeks=deslocamento)
    recente = recente.dropna(subset=[coluna])

    # So o numero da semana, com o nome no titulo do eixo: "SE 42" doze vezes
    # nao cabe no celular, e o Plotly inclinava os rotulos uns sobre os outros.
    rotulos = [f"{semana_epidemiologica(d) % 100:02d}" for d in recente["alvo"]]
    posicoes = list(range(len(recente)))
    valores = recente[coluna].astype(float).tolist()
    texto = [formatar(v) for v in valores]
    futuro = [d > ultima_data for d in recente["alvo"]]
    atual = next((i for i, d in enumerate(recente["alvo"]) if d == ultima_data),
                 len(posicoes) - 1)

    figura = go.Figure()
    # Passado solido e futuro tracejado; os dois dividem o ponto da semana
    # atual, para a linha nao abrir um buraco na emenda.
    corte = atual + 1
    for trecho, tracejado in ((slice(0, corte), False), (slice(atual, None), True)):
        xs, ys, ts = posicoes[trecho], valores[trecho], texto[trecho]
        if len(xs) < 2 and tracejado:
            continue
        figura.add_trace(go.Scatter(
            x=xs, y=ys, text=ts if not tracejado else [""] + ts[1:],
            mode="lines+markers+text", textposition="top center",
            textfont={"color": cor, "size": 12, "family": FONTE_CORPO},
            # Suavizacao contida: a curva cheia passava abaixo dos pontos
            # entre duas semanas, como se tivesse havido um vale que nao houve.
            line={"color": cor, "width": 2.4, "shape": "spline", "smoothing": 0.6,
                  "dash": "dash" if tracejado else "solid"},
            marker={"size": 5, "color": cor},
            fill="tozeroy", fillcolor=_transparente(cor, 0.07),
            hoverinfo="skip", showlegend=False,
        ))
    # A semana atual em circulo vazado, como a hora atual na previsao do tempo.
    figura.add_trace(go.Scatter(
        x=[posicoes[atual]], y=[valores[atual]], mode="markers",
        marker={"size": 13, "color": "#ffffff", "line": {"color": cor, "width": 2.5}},
        hoverinfo="skip", showlegend=False,
    ))

    if any(futuro):
        figura.add_vrect(
            x0=futuro.index(True) - 0.5, x1=posicoes[-1] + 0.5,
            fillcolor=_transparente(cor, 0.06), line_width=0, layer="below",
            annotation_text="previsão", annotation_position="top left",
            annotation_font={"color": NEUTRO_600, "size": 11},
        )
    if coluna == "probabilidade_alerta":
        figura.add_hline(
            y=limiar, line_dash="dot", line_color=NEUTRO_500, line_width=1,
            annotation_text=f"limiar {limiar:.0%}", annotation_position="bottom right",
            annotation_font={"color": NEUTRO_600, "size": 11},
        )

    topo = max(valores + ([limiar] if coluna == "probabilidade_alerta" else []))
    # Meia semana de folga em cada ponta: sem ela o primeiro e o ultimo ponto
    # encostavam na borda e o valor escrito saia cortado.
    figura.update_layout(
        height=300, margin={"t": 20, "b": 10, "l": 10, "r": 10},
        xaxis={"tickmode": "array", "tickvals": posicoes, "ticktext": rotulos,
               "tickangle": 0, "range": [-0.6, posicoes[-1] + 0.6],
               "title": {"text": "semana epidemiológica",
                         "font": {"size": 11, "color": NEUTRO_600}},
               "showgrid": False, "fixedrange": True},
        yaxis={"range": [0, topo * 1.28 if topo else 1], "showgrid": False,
               "showticklabels": False, "fixedrange": True},
    )
    return figura


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
        rotulo = "domicílios no setor"

    if coluna not in registros or registros[coluna].isna().all():
        disponiveis = [c for c in registros.columns
                       if c.endswith("_pct") or c == "indice_criadouro"]
        st.warning(
            "Este indicador não existe na escala da quadra. Disponíveis: "
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
        f"{_milhar(len(registros))} setores censitários urbanos. "
        "O setor é a menor unidade que o IBGE publica -- algumas quadras, "
        "cerca de trezentos domicílios. Aproxime para o mapa base nomear as ruas. "
        "O risco de dengue continua sendo municipal: esta camada mostra onde a "
        "condição local favorece o criadouro, não onde há caso."
    )

    # dict.fromkeys tira a coluna repetida quando o indicador ja e "domicilios";
    # o Styler nao aceita nome de coluna duplicado.
    piores = registros.nlargest(12, coluna)[
        list(dict.fromkeys(c for c in ("NM_SUBDIST", "CD_SETOR", coluna, "domicilios")
                           if c in registros))
    ].rename(columns={
        "NM_SUBDIST": "Região Administrativa", "CD_SETOR": "Setor",
        coluna: rotulo, "domicilios": "Domicílios",
    })
    st.markdown("**As doze quadras em pior situação neste indicador**")
    st.dataframe(
        formato_br(piores, {rotulo: 1, "Domicílios": 0}),
        hide_index=True, width="stretch",
    )


painel = carregar_painel()
n_municipios = int(painel["cod_ibge"].nunique())

# ------------------------------------------------------------------ cabecalho
st.markdown(
    '<div class="vigia-cabecalho">'
    '<div>'
    '<div class="vigia-cabecalho-nome">Vigia-Dengue</div>'
    '<div class="vigia-cabecalho-sub">Sala de situação -- alerta precoce do '
    'risco de dengue em Brasília e na RIDE-DF</div>'
    '</div>'
    f'<div class="vigia-cabecalho-tag">DF + RIDE<br>{n_municipios} municípios</div>'
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
        f"Dado até a semana **{formatar_semana(ultima_semana)}**. O ciclo de "
        "atualização nunca rodou: execute `python src/vigia/executar_atualizacao.py` "
        "para o painel passar a acompanhar o InfoDengue sozinho."
    )
else:
    verificado = pd.to_datetime(estado_alerta["estado"]["verificado_em"])
    horas = (pd.Timestamp.now(tz="UTC") - verificado).total_seconds() / 3600
    quando = (f"há {horas * 60:.0f} min" if horas < 1
              else f"há {horas:.0f} h" if horas < 48
              else f"em {verificado.tz_convert(None):%d/%m}")
    recado = (
        f"Dado do InfoDengue até a semana **{formatar_semana(ultima_semana)}** -- "
        f"fonte verificada {quando}."
    )
    # Mais de tres dias sem verificar ja e sinal de que o agendamento parou.
    (st.warning if horas > 72 else st.caption)(recado)

# ---------------------------------------------------------------- barra lateral
with st.sidebar:
    st.header("Filtros")

    semanas = sorted(painel["se_codigo"].unique())
    semana_escolhida = st.select_slider(
        "Semana epidemiológica",
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
    # Em pontos percentuais, e nao de 0 a 1: o controle mostra "80%", como o
    # resto da tela, em vez de "0.80" com ponto decimal americano.
    limiar = st.slider(
        "Limiar de probabilidade para o alerta",
        min_value=5, max_value=95, value=80, step=5, format="%d%%",
        help="Probabilidade acima da qual Brasília entra em alerta. Em 80% o "
             "alerta acerta 3 de cada 4 disparos; em 50% dispararia em quase "
             "toda semana.",
    ) / 100

    sinalizar_provisorio = st.checkbox(
        "Sinalizar semanas com notificação incompleta", value=True
    )

    st.caption(
        "O Monitor mostra sempre a semana mais recente da base; o filtro de "
        "semana vale para as demais abas."
    )

    st.divider()
    horizonte = int(painel["horizonte_semanas"].iloc[0])
    st.info(
        f"O alerta projeta o risco **{horizonte} semanas à frente**. "
        "Os casos estimados corrigem o atraso de notificação."
    )

semana_atual = painel[painel["se_codigo"] == semana_escolhida].copy()

# `foco` e o retrato de Brasilia na semana ESCOLHIDA no filtro: alimenta o
# relatorio da semana. O Monitor nao passa por aqui -- ele e ao vivo e le
# sempre a ultima semana da base.
foco = semana_atual[semana_atual["cod_ibge"] == COD_FOCO]

(aba_monitor, aba_mapa, aba_serie, aba_relatorio, aba_modelo,
 aba_dicionario) = st.tabs(
    ["Monitor", "Brasília por Região Administrativa", "Séries temporais",
     "Relatório da semana", "Desempenho do modelo", "Dicionário de dados"]
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
        "Semana epidemiológica",
        formatar_semana(semana_monitor),
        help="Última semana consolidada na base. A fonte (InfoDengue) publica "
             "semanalmente.",
    )
    col2.metric(
        "Casos estimados em Brasília",
        _milhar(atual["casos_est"]),
        delta=None if variacao is None else f"{variacao:+.0f}% vs semana anterior",
        delta_color="inverse",
        help="Nowcasting do InfoDengue: corrige o atraso de notificação.",
    )
    canal_q3 = atual["canal_q3"]
    col3.metric(
        "Incidência / 100 mil",
        _decimal(atual["incidencia_100k"]),
        delta=(None if pd.isna(canal_q3)
               else f"{_sinal(atual['incidencia_100k'] - canal_q3)} vs canal endêmico"),
        delta_color="inverse",
        help=(None if pd.isna(canal_q3)
              else f"Limite esperado para esta semana do ano (Q3 histórico): "
                   f"{_decimal(canal_q3)} por 100 mil."),
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
            f"risco hoje: {risco_atual}",
            CORES_RISCO[risco_atual], TEXTO_SOBRE_RISCO[risco_atual],
        ))
    if sinalizar_provisorio and atual["dado_provisorio"] == 1:
        selos.append(chip(
            f"dado provisório -- {atual['completude']:.0%} digitado; os casos "
            "tendem a subir",
            "#dcc7b6", TEXTO,
        ))
    st.markdown("".join(selos), unsafe_allow_html=True)

    if atual["probabilidade_alerta"] >= limiar:
        st.error(
            f"**Brasília em alerta.** Probabilidade de "
            f"{atual['probabilidade_alerta']:.0%} de risco alto ou muito alto "
            f"em {horizonte} semanas. O que mais pesou: "
            f"{fatores_legiveis(atual['fatores_alerta'])}."
        )

    # ---- indices da semana ----------------------------------------------
    st.subheader("Índices da semana")
    municipios_idx = (painel[["cod_ibge", "municipio"]].drop_duplicates()
                      .sort_values("municipio"))
    opcoes_idx = [int(c) for c in municipios_idx["cod_ibge"]]
    rotulos_idx = dict(zip(opcoes_idx, municipios_idx["municipio"]))
    cod_idx = st.selectbox(
        "Município", opcoes_idx,
        index=opcoes_idx.index(COD_FOCO) if COD_FOCO in opcoes_idx else 0,
        format_func=lambda codigo: rotulos_idx.get(codigo, str(codigo)),
        key="municipio_indices",
    )
    serie_idx = painel[painel["cod_ibge"] == cod_idx].sort_values("se_codigo")
    linha_idx = serie_idx.iloc[-1]

    # ---- semana a semana: o "hora a hora" da previsao do tempo -----------
    with st.container(border=True):
        titulo_semana, botoes_semana = st.columns([1, 1.6], vertical_alignment="center")
        titulo_semana.markdown(
            f"#### Semana a semana em {rotulos_idx.get(cod_idx, '')}"
        )
        medida = botoes_semana.segmented_control(
            "Medida", list(MEDIDAS_SEMANA), default="Casos",
            label_visibility="collapsed", key="medida_semana",
        ) or "Casos"
        st.plotly_chart(
            grafico_semanal(serie_idx, medida, limiar, horizonte),
            width="stretch", config={**CONFIG_GRAFICO, "staticPlot": True},
        )
        legenda_medida = {
            "Casos": "Casos estimados por semana, já corrigidos do atraso de "
                     "notificação. O círculo é a semana mais recente.",
            "Risco à frente": f"Chance de risco alto ou muito alto em cada "
                              f"semana, calculada {horizonte} semanas antes. "
                              "O trecho tracejado é a previsão para as próximas "
                              "semanas.",
            "Temperatura": "Temperatura média da semana, observada.",
            "Umidade": "Umidade relativa média da semana, observada.",
        }
        st.caption(legenda_medida[medida])

    st.caption(
        f"Semana {formatar_semana(int(linha_idx['se_codigo']))}. Cada índice "
        "traz embaixo a evidência medida que o sustenta."
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
    st.subheader("O território agora")

    # Uma linha por municipio: a mais recente de cada serie, porque municipio
    # pequeno as vezes fecha a semana antes do foco.
    recorte = painel.sort_values("se_codigo").groupby("cod_ibge").tail(1)
    quadro = recorte.sort_values("probabilidade_alerta", ascending=False).copy()
    quadro["tendencia"] = quadro["razao_mm3_mm8"].map(seta_tendencia)

    # Risco e probabilidade logo depois do nome: no celular a tabela mostra
    # tres colunas antes de rolar, e eram as que ficavam escondidas. A semana
    # so vira coluna quando nem todos os municipios estao na mesma; quando
    # estao, ela repetia o mesmo valor em todas as linhas e vai para a legenda.
    semanas_quadro = quadro["se_codigo"].unique()
    st.caption(
        f"Os {n_municipios} municípios ordenados pela probabilidade de alerta"
        + (f", todos na semana {formatar_semana(semanas_quadro[0])}."
           if len(semanas_quadro) == 1 else
           ", cada um na sua semana mais recente -- séries municipais podem "
           "fechar antes da de Brasília.")
    )
    colunas_quadro = {
        "Município": quadro["municipio"].values,
        "Risco": quadro["risco"].astype(str).values,
        "Prob. de alerta": (quadro["probabilidade_alerta"] * 100).values,
        "Casos est.": quadro["casos_est"].values,
        "Incidência /100 mil": quadro["incidencia_100k"].values,
        "Tendência recente": quadro["tendencia"].values,
    }
    if len(semanas_quadro) > 1:
        colunas_quadro["Semana"] = [formatar_semana(s) for s in quadro["se_codigo"]]
    tabela = pd.DataFrame(colunas_quadro)

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

    # As larguras de risco e probabilidade sao as que cabem, junto do nome,
    # numa tela de 390 px. O nome nao fica preso a esquerda (`pinned`): o
    # Streamlit pinta coluna presa de cinza e ignora a cor do Styler.
    st.dataframe(
        formato_br(tabela, {"Casos est.": 0, "Incidência /100 mil": 1})
        .apply(_pintar_risco, subset=["Risco"])
        .apply(_pintar_tendencia, subset=["Tendência recente"]),
        hide_index=True, width="stretch", height=520,
        column_config={
            "Risco": st.column_config.TextColumn(
                width=85,
                help="Nível de risco na semana mais recente, pela incidência "
                     "e pelo canal endêmico.",
            ),
            "Casos est.": st.column_config.NumberColumn(
                help="Nowcasting da semana mais recente do município.",
            ),
            "Prob. de alerta": st.column_config.ProgressColumn(
                format="%.0f%%", min_value=0, max_value=100, width=125,
                help=f"A previsão do modelo: probabilidade de risco alto ou "
                     f"muito alto daqui a {horizonte} semanas.",
            ),
            "Tendência recente": st.column_config.TextColumn(
                help="Não é previsão: compara a média de casos das últimas 3 "
                     "semanas com a das últimas 8. Acima de 1,1 a curva está "
                     "subindo; abaixo de 0,9, caindo. Entra no modelo como "
                     "uma das variáveis.",
            ),
        },
    )

    # ---- alarmes de variaveis -------------------------------------------
    st.subheader("Alarmes de variáveis")
    alarmes_estado = carregar_alarmes()

    if alarmes_estado is None:
        st.info(
            "`saidas/alarmes.json` não encontrado. Gere-o com "
            "`python src/vigia/executar_alarmes.py`: ele mede cada regra "
            "contra o histórico 2014-2026 e grava os alarmes da semana."
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
                nome_regra = acentuar(catalogo.get(alarme["id"], {}).get("nome", alarme["id"]))
                st.markdown(
                    '<div class="vigia-alarme">'
                    '<div class="vigia-alarme-titulo">'
                    f'{html.escape(acentuar(alarme["municipio"]))} -- '
                    f'{html.escape(nome_regra)}'
                    '</div>'
                    f'<div class="vigia-alarme-frase">{html.escape(alarme["frase"])}</div>'
                    '<div class="vigia-alarme-meta">'
                    f'Regra {html.escape(alarme["id"])} · gatilho p_rt1 '
                    f'{_decimal(alarme["valor_gatilho"], 2)} · olhe '
                    f'{alarme["lag_semanas"]} semanas à frente · lift histórico '
                    f'{_decimal(alarme["lift_historico"])}x '
                    f'· SE {formatar_semana(alarme["semana"])}'
                    '</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            vigiadas = ", ".join(
                f"{r['id']} ({acentuar(r['nome']).lower()})" for r in aprovadas
            )
            complemento = (
                f" As regras com evidência histórica seguem vigiadas: {vigiadas}."
                if vigiadas else ""
            )
            st.markdown(
                '<div class="vigia-sem-alarme">Nenhum alarme de variável '
                "ligado nesta semana (medido na SE "
                f'{formatar_semana(alarmes_estado["gerado_da_semana"])}).'
                f"{html.escape(complemento)}</div>",
                unsafe_allow_html=True,
            )

        with st.expander("Metodologia: todas as regras medidas, aprovadas ou não"):
            st.caption(
                f"Base: {regras_info.get('base', '?')}. Medido em "
                f"{regras_info.get('gerado_em', '?')}. Regras reprovadas "
                "aparecem aqui por transparência e nunca disparam alarme."
            )
            st.caption(regras_info.get("metodo", ""))

            if todas_regras:
                medicao = pd.DataFrame({
                    "Regra": [r["id"] for r in todas_regras],
                    "Nome": [acentuar(r["nome"]) for r in todas_regras],
                    "Condição": [r["condicao"] for r in todas_regras],
                    "Horizonte (sem.)": [r["lag_semanas"] for r in todas_regras],
                    "Episódios": [r["n_episodios"] for r in todas_regras],
                    "Lift mediano": [r["lift_mediano"] for r in todas_regras],
                    "Acima do normal (%)": [
                        r["frac_lift_acima_1"] * 100 for r in todas_regras
                    ],
                    "Situação": [
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
                    formato_br(medicao, {"Lift mediano": 2,
                                         "Acima do normal (%)": 0})
                    .apply(_pintar_situacao, subset=["Situação"]),
                    hide_index=True, width="stretch",
                )

                for regra in todas_regras:
                    st.markdown(
                        f"- **{regra['id']} -- {acentuar(regra['nome'])}:** "
                        f"{regra['frase_evidencia']}"
                    )

            por_municipio = regras_info.get("por_municipio", {})
            for regra in aprovadas:
                medidas = por_municipio.get(regra["id"], [])
                if not medidas:
                    continue
                st.markdown(
                    f"**Onde {regra['id']} ({acentuar(regra['nome']).lower()}) mais se "
                    "confirmou** -- lift histórico por município, só quem tem "
                    "8 ou mais episódios:"
                )
                lift_por_municipio = pd.DataFrame(medidas).assign(
                    municipio=lambda d: d["municipio"].map(acentuar)
                ).rename(columns={
                    "municipio": "Município", "n": "Episódios",
                    "lift": "Lift histórico", "cod_ibge": "Código IBGE",
                })[["Município", "Episódios", "Lift histórico"]]
                st.dataframe(
                    formato_br(lift_por_municipio, {"Lift histórico": 2}),
                    hide_index=True, width="stretch", height=280,
                )

    # ---- clima dos proximos 14 dias --------------------------------------
    st.subheader("Clima dos próximos 14 dias")
    clima = carregar_clima_futuro()

    if clima is None:
        st.caption(
            "`saidas/clima_futuro.json` não encontrado. Gere-o com "
            "`python src/vigia/executar_clima_futuro.py` (previsão Open-Meteo "
            "para os municípios do território)."
        )
    else:
        se_corrente = semana_epidemiologica(pd.Timestamp.today())
        coletado = int(clima.get("coletado_para_semana", 0))
        if coletado != se_corrente:
            st.caption(
                f"Previsão coletada na SE {formatar_semana(coletado)}; a "
                f"semana corrente é {formatar_semana(se_corrente)}. Rode "
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
                "Município": acentuar(municipio_clima["municipio"]),
                "Chuva 7 dias (mm)": municipio_clima["chuva_7d_mm"],
                "Chuva 14 dias (mm)": municipio_clima["chuva_14d_mm"],
                "Dias de chuva (14 d)": municipio_clima["dias_chuva_14d"],
                "Temp. média (°C)": municipio_clima["temp_media_14d"],
            })

        if not linhas_clima:
            st.caption(
                "A previsão coletada não cobre os municípios em foco nesta "
                "semana."
            )
        else:
            st.dataframe(
                formato_br(pd.DataFrame(linhas_clima), {
                    "Chuva 7 dias (mm)": 1, "Chuva 14 dias (mm)": 1,
                    "Dias de chuva (14 d)": 0, "Temp. média (°C)": 1,
                }),
                hide_index=True, width="stretch",
                column_config={
                    "Dias de chuva (14 d)": st.column_config.NumberColumn(
                        help="Dias com 1 mm ou mais, o mesmo critério da "
                             "série observada.",
                    ),
                },
            )
            st.caption(
                "Previsão Open-Meteo para Brasília e os cinco municípios com "
                "maior probabilidade de alerta. Leitura honesta: chuva e "
                "temperatura à frente dizem se o território fica receptivo ao "
                "mosquito nas próximas semanas -- **não entram no modelo**, "
                "que prevê com o clima já observado. Dias sem previsão ficam "
                "fora das somas e da média."
            )
        faltantes = clima.get("faltantes", [])
        if faltantes:
            st.caption(
                f"Sem previsão para {len(faltantes)} "
                + ("município" if len(faltantes) == 1 else "municípios")
                + " nesta coleta."
            )

# ------------------------------------------- Brasilia por Regiao Administrativa
with aba_mapa:
    malha_ras = carregar_malha_ras()

    if malha_ras is None:
        st.warning(
            "Malha das Regiões Administrativas ausente. "
            "Execute `python src/vigia/executar_ras.py` para gerá-la."
        )
    else:
        st.subheader("Estrutura territorial do Distrito Federal")
        st.caption(
            "As 31 Regiões Administrativas com geometria disponível. Brasília é um "
            "único município na malha do IBGE, e esta camada mostra a divisão "
            "intraurbana que o dado municipal não alcança."
        )

        regioes = pd.DataFrame([
            feicao["properties"] for feicao in malha_ras["features"]
        ])
        regioes["populacao"] = pd.to_numeric(regioes["populacao"], errors="coerce")
        # `ra_nome` e a chave da malha e fica como esta; o acento so no que se le.
        regioes["ra_exibicao"] = regioes["ra_nome"].map(acentuar)

        # Indicadores do Censo 2022 por RA. Sao eles que dao conteudo proprio a
        # cada area: sem eles o mapa so sabe repetir o tamanho da populacao.
        vulnerabilidade = carregar_vulnerabilidade_ras()
        if vulnerabilidade is not None:
            regioes = regioes.merge(
                vulnerabilidade.drop(columns=["ra_nome"]),
                on="cod_subdistrito", how="left",
            )

        indicadores = {
            "População": ("populacao", "habitantes"),
            "Densidade": ("densidade_hab_km2", "hab./km²"),
        }
        if vulnerabilidade is not None:
            indicadores.update({
                "Vulnerabilidade": ("indice_vulnerabilidade", "índice (0 a 100)"),
                "Esgoto inadequado": ("esgoto_inadequado_pct", "% dos domicílios"),
                "Sem água de rede": ("sem_agua_rede_pct", "% dos domicílios"),
                "Lixo sem coleta": ("lixo_sem_coleta_pct", "% dos domicílios"),
                "Sem bueiro": ("sem_bueiro_pct", "% dos domicílios"),
                "Rua sem pavimento": ("sem_pavimento_pct", "% dos domicílios"),
            })

        setores = carregar_setores()
        escala = "Região Administrativa"
        if setores is not None:
            escala = st.radio(
                "Escala do mapa",
                ["Região Administrativa", "Quadra (setor censitário)"],
                horizontal=True,
                index=1,
                help="O setor censitário é a menor unidade que o IBGE publica: "
                     "algumas quadras, cerca de trezentos domicílios.",
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
                "Média das três dimensões abaixo, cada uma como distância relativa "
                "dentro do próprio DF. Ordena as RAs numa leitura só; não pondera as "
                "dimensões, porque não há estudo local que sustente pesos diferentes.",
            "esgoto_inadequado_pct":
                "Domicílios com esgoto em fossa rudimentar, vala ou outra forma -- "
                "água parada exposta.",
            "sem_agua_rede_pct":
                "Domicílios sem ligação à rede geral. Levam ao armazenamento em "
                "caixas e tonéis, criadouro clássico do Aedes aegypti.",
            "lixo_sem_coleta_pct":
                "Lixo queimado, enterrado ou com outro destino, que acumula "
                "recipientes com água parada.",
            "sem_bueiro_pct":
                "Domicílios em face de rua sem boca de lobo. É a drenagem que "
                "decide se a chuva escoa ou empoça, e o Aedes se cria em água "
                "parada, não corrente -- por isso este é o indicador de fluxo "
                "das águas na escala em que o mosquito vive.",
            "sem_pavimento_pct":
                "Domicílios em face de rua sem pavimento, onde a água empoça "
                "mesmo havendo drenagem.",
        }
        if coluna in explicacao:
            st.caption(
                explicacao[coluna] + " Fonte: Censo 2022 (IBGE), agregados por "
                "subdistrito -- no DF, o subdistrito é a Região Administrativa."
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
                hover_name="ra_exibicao",
                hover_data={"faixa": False, "ra_nome": False, coluna: ":,.0f"},
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
                    text=list(grupo["ra_exibicao"]),
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
                f"Nomeadas no mapa {len(cabe_rotulo)} das 31 RAs: onde várias se "
                "aglomeram, fica o nome da maior, e as demais aparecem ao passar o "
                "cursor e na tabela abaixo -- uma pilha de nomes sobrepostos seria "
                "pior do que nome nenhum. As faixas são quartis, com cerca de oito "
                "RAs cada; numa escala linear, 18 das 31 cairiam no mesmo tom claro."
            )

        tabela_ras = regioes.sort_values("populacao", ascending=False)[
            [c for c in ("ra_exibicao", "populacao", "cod_subdistrito") if c in regioes]
        ].rename(columns={
            "ra_exibicao": "Região Administrativa",
            "populacao": "População (PDAD 2021)",
            "cod_subdistrito": "Código IBGE (subdistrito)",
        })
        st.dataframe(
            formato_br(tabela_ras, {"População (PDAD 2021)": 0}),
            hide_index=True, width="stretch", height=320,
        )

        st.info(
            "**Por que este mapa não mostra casos de dengue.** Não há fonte pública "
            "com série semanal de casos por Região Administrativa: o InfoDengue opera "
            "apenas no nível municipal, o painel de incidência da SES-DF não expõe "
            "dados de forma programática, o LIRAa é publicado como relatório fechado "
            "e os microdados do SINAN dependem do FTP do DATASUS. Repartir os casos do "
            "DF entre as RAs na proporção da população produziria um mapa apenas "
            "aparentemente informativo, que reproduziria o mapa populacional e "
            "esconderia a desigualdade intraurbana real. Obtida a série por RA junto "
            "à SES-DF, ela se acopla a esta malha pelo nome da região."
        )


# -------------------------------------------------------------- series temporais
with aba_serie:
    serie = painel[painel["cod_ibge"] == COD_FOCO].sort_values("data_ini_se")
    st.caption(
        "Série de **Brasília**. O InfoDengue publica casos no nível municipal, "
        "e o Distrito Federal é um único município: esta é a série do território "
        "inteiro, cidades-satélite incluídas."
    )

    # A serie inteira, de 2015 para ca, e dominada pelo pico de 2024 (25 mil
    # casos numa semana): a situacao de agora vira uma linha rente ao chao.
    # O padrao e olhar os dois ultimos anos; o eixo vertical se ajusta ao
    # periodo, o que um zoom no proprio grafico nao faz.
    periodos = {"1 ano": 1, "2 anos": 2, "5 anos": 5, "Tudo": None}
    periodo = st.segmented_control(
        "Período", list(periodos), default="2 anos",
        key="periodo_series",
    ) or "2 anos"
    anos = periodos[periodo]
    if anos is not None:
        inicio = serie["data_ini_se"].max() - pd.DateOffset(years=anos)
        serie = serie[serie["data_ini_se"] >= inicio]

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
    # Eixo em "25.000", e nao no "25k" do padrao do Plotly; o hover mostra a
    # semana pela data de inicio, no formato brasileiro.
    figura.update_layout(
        height=380, margin={"t": 30},
        yaxis_title="Casos por semana", xaxis_title=None,
        yaxis_tickformat=",d", hovermode="x unified", xaxis=EIXO_DATAS,
        legend={"orientation": "h", "y": 1.12},
    )
    st.plotly_chart(figura, width="stretch", config=CONFIG_GRAFICO)

    canal = go.Figure()
    canal.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["canal_q3"],
        name="Limite esperado (Q3 histórico)",
        line={"color": NEUTRO_500, "dash": "dash"},
    ))
    canal.add_trace(go.Scatter(
        x=serie["data_ini_se"], y=serie["incidencia_100k"],
        name="Incidência por 100 mil", line={"color": ACENTO_800, "width": 2},
    ))
    canal.update_layout(
        height=300, margin={"t": 30},
        yaxis_title="Incidência / 100 mil hab.",
        hovermode="x unified", xaxis=EIXO_DATAS,
        legend={"orientation": "h", "y": 1.15},
    )
    st.plotly_chart(canal, width="stretch", config=CONFIG_GRAFICO)
    st.caption(
        "Incidência acima do limite esperado indica atividade acima do padrão "
        "histórico daquela semana do ano no município (canal endêmico)."
    )

# ----------------------------------------------------------- relatorio da semana
with aba_relatorio:
    if foco.empty:
        st.warning("Sem dado de Brasília nesta semana.")
    else:
        r = foco.iloc[0]
        st.subheader(f"Brasília -- semana {formatar_semana(semana_escolhida)}")

        resumo = pd.DataFrame({
            "Indicador": [
                "Casos notificados",
                "Casos estimados",
                "Incidência / 100 mil",
                "Nível de risco",
                f"Probabilidade de alerta ({horizonte} semanas)",
                "Notificação completa",
            ],
            "Valor": [
                _milhar(r["casos"]),
                _milhar(r["casos_est"]),
                _decimal(r["incidencia_100k"]),
                str(r["risco"]).capitalize(),
                f"{r['probabilidade_alerta']:.0%}",
                "não" if r["dado_provisorio"] == 1 else "sim",
            ],
        })
        st.dataframe(resumo, hide_index=True, width="stretch")
        # Fora da tabela: e a linha mais longa, e numa celula ela era cortada.
        st.markdown(
            f"**O que mais pesou na previsão:** "
            f"{fatores_legiveis(r['fatores_alerta'])}."
        )

        if sinalizar_provisorio and r["dado_provisorio"] == 1:
            st.warning(
                f"Notificação ainda incompleta em Brasília nesta semana "
                f"({r['completude']:.0%} digitado). Os casos observados tendem a subir."
            )

    # A serie inteira, e nao so a semana: quem leva o CSV costuma querer
    # remontar a curva, nao apenas o retrato de uma semana.
    serie_bsb = painel[painel["cod_ibge"] == COD_FOCO].sort_values("se_codigo")[
        ["se_codigo", "data_ini_se", "casos", "casos_est", "incidencia_100k",
         "risco", "probabilidade_alerta", "fatores_alerta", "dado_provisorio"]
    ]
    st.download_button(
        "Baixar a série completa de Brasília (CSV)",
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
        st.info("Execute a validação temporal para preencher esta aba.")
    else:
        st.subheader("Validação temporal em janela expansiva")
        st.caption(
            "Cada ano é previsto por um modelo treinado apenas com os anos "
            "anteriores. Nenhuma informação do futuro entra no treino."
        )
        desempenho = desempenho.assign(
            modelo=desempenho["modelo"].map(NOMES_MODELO)
            .fillna(desempenho["modelo"]))
        ordem_modelos = [m for m in CORES_MODELO if m in set(desempenho["modelo"])]
        medias = (desempenho.groupby("modelo")[
            ["sensibilidade", "especificidade", "vpp", "auc", "auprc", "brier"]
        ].mean().round(3).reindex(ordem_modelos).reset_index())
        metricas = ["Sensibilidade", "Especificidade", "VPP", "AUC", "AUPRC", "Brier"]
        st.dataframe(
            formato_br(medias.rename(columns={
                "modelo": "Modelo", "sensibilidade": "Sensibilidade",
                "especificidade": "Especificidade", "vpp": "VPP",
                "auc": "AUC", "auprc": "AUPRC", "brier": "Brier",
            }), dict.fromkeys(metricas, 3)),
            hide_index=True, width="stretch",
        )

        linha_auc = px.line(
            desempenho, x="ano", y="auc", color="modelo", markers=True,
            color_discrete_map=CORES_MODELO, line_dash="modelo",
            line_dash_map=TRACO_MODELO,
            category_orders={"modelo": ordem_modelos},
            labels={"auc": "AUC", "ano": "Ano avaliado", "modelo": "Modelo"},
        )
        # A serie em operacao vai mais grossa: e a que a pessoa procura.
        linha_auc.for_each_trace(
            lambda tr: tr.update(line_width=3 if tr.name.startswith("Combinado")
                                 else 1.8))
        linha_auc.update_layout(height=360)
        st.plotly_chart(linha_auc, width="stretch", config=CONFIG_GRAFICO)

# ------------------------------------------------------- Dicionario de dados
with aba_dicionario:
    dicionario = carregar_dicionario()

    if dicionario is None:
        st.warning(
            "Dicionário não encontrado. Gere-o com `executar_dicionario.py` para "
            "que esta aba mostre as colunas da base."
        )
    else:
        st.subheader("As colunas da base analítica")
        st.markdown(
            "Cada linha é uma coluna da base município-semana que sustenta a "
            "previsão. O campo **papel** diz como ela entra: *preditor "
            "essencial* é o que a previsão não dispensa, *preditor* é tudo que "
            "o modelo usa, *origem do alvo* é a coluna de onde sai o desfecho, "
            "e *apoio* sustenta cálculo, conferência e painel sem entrar no "
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
        papel_escolhido = filtro_b.selectbox("Papel na previsão", papeis)
        busca = st.text_input(
            "Buscar", placeholder="nome da coluna, descrição ou fonte",
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
            formato_br(visivel.rename(columns={
                "coluna": "Coluna", "bloco": "Bloco", "tipo": "Tipo",
                "papel": "Papel", "preenchida_pct": "Preenchida (%)",
                "fonte": "Fonte", "descricao": "Descrição",
            }), {"Preenchida (%)": 1}),
            hide_index=True, width="stretch", height=520,
        )

        st.download_button(
            "Baixar o dicionário completo (CSV)",
            data=dicionario.to_csv(index=False).encode("utf-8"),
            file_name="dicionario_de_dados_vigia.csv",
            mime="text/csv",
            help=f"As {len(dicionario)} colunas com bloco, papel, fonte e "
                 "descrição -- o arquivo inteiro, sem os filtros da tela.",
        )

        st.caption(
            "Nenhuma variável enxerga o futuro: médias móveis são deslocadas em "
            "uma semana, as anomalias sazonais e o canal endêmico usam apenas "
            "anos anteriores, e a dobra de validação corta pela data que o alvo "
            "observa. As colunas abaixo de 100% de preenchimento faltam por "
            "construção -- o canal endêmico exige anos anteriores, e o primeiro "
            "ano da série não os tem."
        )

        # ---- glossario: o que cada termo da tabela significa ----------
        glossario_tab = carregar_glossario()
        if glossario_tab is not None:
            st.subheader("O que cada termo significa")
            st.caption(
                "Para quem não é da área: as colunas da tabela, os tipos de "
                "dado, os papéis na previsão, as fontes e os termos que "
                "aparecem nas descrições."
            )
            def _itens(linhas: pd.DataFrame) -> str:
                return "\n".join(
                    f"- **{html.escape(str(l.termo))}** -- "
                    f"{html.escape(str(l.significado))}"
                    for l in linhas.itertuples()
                )

            # Grupos curtos vao lado a lado, cada um na coluna que estiver
            # mais curta. Grupo comprido ocupa a largura toda, com os termos
            # repartidos nas duas colunas -- inteiro numa so, ele deixava a
            # outra coluna vazia pela metade da tela.
            grupos = list(dict.fromkeys(glossario_tab["grupo"]))
            tamanho = {g: int((glossario_tab["grupo"] == g).sum()) for g in grupos}
            curtos = [g for g in grupos if tamanho[g] <= 8]
            longos = [g for g in grupos if tamanho[g] > 8]

            colunas_glossario = st.columns(2)
            ocupado = [0, 0]
            for grupo in curtos:
                lado = 0 if ocupado[0] <= ocupado[1] else 1
                ocupado[lado] += tamanho[grupo] + 1
                linhas = glossario_tab[glossario_tab["grupo"] == grupo]
                with colunas_glossario[lado]:
                    st.markdown(f"**{html.escape(grupo).upper()}**\n\n"
                                f"{_itens(linhas)}")

            for grupo in longos:
                linhas = glossario_tab[glossario_tab["grupo"] == grupo]
                metade = (len(linhas) + 1) // 2
                st.markdown(f"**{html.escape(grupo).upper()}**")
                esquerda, direita = st.columns(2)
                esquerda.markdown(_itens(linhas.iloc[:metade]))
                direita.markdown(_itens(linhas.iloc[metade:]))

st.divider()
st.caption(
    "Fontes: InfoDengue (Fiocruz/FGV) para casos e clima observado; Open-Meteo "
    "para a previsão de clima; IBGE para população e malha municipal. "
    "Ferramenta de apoio à vigilância -- não substitui a análise da equipe de "
    "vigilância epidemiológica local."
)
