"""Gera o painel VIGIA-Dengue como um unico arquivo HTML estatico.

O painel Streamlit exige servidor rodando. Este modulo produz a mesma leitura
em um HTML autocontido, que abre com dois cliques no navegador e pode ser
enviado por e-mail ou anexado a um relatorio -- util para a orientadora, a
banca ou a equipe de vigilancia, que nao vao instalar Python.

Os graficos continuam interativos: a biblioteca Plotly e os dados sao embutidos
no proprio arquivo. A unica dependencia externa que resta sao os tiles de fundo
dos dois mapas, servidos por OpenStreetMap/Carto -- sem internet os poligonos e
as cores de risco aparecem normalmente, apenas sobre fundo vazio.

Uso:  python src/vigia/exportar_html.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_PAINEL = RAIZ / "dados" / "processado" / "painel.csv"
CAMINHO_MALHA = RAIZ / "dados" / "externo" / "malha_ride_df.geojson"
CAMINHO_MALHA_RAS = RAIZ / "dados" / "externo" / "malha_ras_df.geojson"
CAMINHO_DESEMPENHO = RAIZ / "saidas" / "desempenho_modelos.csv"
DESTINO = RAIZ / "Painel VIGIA-Dengue (offline).html"

FOCO = "Brasilia"
COD_FOCO = 5300108
ORDEM_RISCO = ["baixo", "moderado", "alto", "muito alto"]
CORES_RISCO = {
    "baixo": "#2E7D32",
    "moderado": "#F9A825",
    "alto": "#EF6C00",
    "muito alto": "#C62828",
}

# Paleta escura, herdada da versao anterior do painel offline.
FUNDO = "#1d2d3d"
CARTAO = "#22354a"
TEXTO = "#e8eef4"
SUAVE = "#9fb3c8"
BORDA = "#2c455d"

MODELO_GRAFICO = go.layout.Template(layout=go.Layout(
    paper_bgcolor=CARTAO,
    plot_bgcolor=CARTAO,
    font={"color": TEXTO, "family": "system-ui, -apple-system, sans-serif", "size": 13},
    xaxis={"gridcolor": BORDA, "zerolinecolor": BORDA},
    yaxis={"gridcolor": BORDA, "zerolinecolor": BORDA},
    legend={"bgcolor": "rgba(0,0,0,0)"},
    margin={"t": 40, "r": 20, "b": 40, "l": 50},
))


def formatar_semana(codigo: int) -> str:
    return f"{int(codigo) % 100:02d}/{int(codigo) // 100}"


def _numero(valor: float, casas: int = 0) -> str:
    """Formata no padrao brasileiro: milhar com ponto, decimal com virgula."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _figura(figura: go.Figure, altura: int = 420) -> str:
    figura.update_layout(template=MODELO_GRAFICO, height=altura)
    return pio.to_html(figura, include_plotlyjs=False, full_html=False,
                       config={"displayModeBar": False, "responsive": True})


def _cartao(titulo: str, valor: str, nota: str = "") -> str:
    rodape = f'<div class="nota">{nota}</div>' if nota else ""
    return (f'<div class="metrica"><div class="rotulo">{titulo}</div>'
            f'<div class="valor">{valor}</div>{rodape}</div>')


def _tabela(dados: pd.DataFrame) -> str:
    cabecalho = "".join(f"<th>{c}</th>" for c in dados.columns)
    linhas = []
    for _, linha in dados.iterrows():
        celulas = "".join(f"<td>{v}</td>" for v in linha)
        linhas.append(f"<tr>{celulas}</tr>")
    return (f'<div class="rolagem"><table><thead><tr>{cabecalho}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def secao_brasilia(painel: pd.DataFrame, semana: int, horizonte: int) -> str:
    """Bloco de destaque com a situacao atual de Brasilia."""
    atual = painel[painel["se_codigo"] == semana]
    foco = atual[atual["cod_ibge"] == COD_FOCO]
    if foco.empty:
        return "<p>Sem dado de Brasilia nesta semana.</p>"

    linha = foco.iloc[0]
    anterior = painel[(painel["cod_ibge"] == COD_FOCO)
                      & (painel["se_codigo"] < semana)].sort_values("se_codigo")

    variacao = ""
    if not anterior.empty and anterior["casos_est"].iloc[-1]:
        delta = (linha["casos_est"] - anterior["casos_est"].iloc[-1]) / anterior["casos_est"].iloc[-1] * 100
        variacao = f"{delta:+.0f}% vs semana anterior"

    cartoes = "".join([
        _cartao("Casos estimados", _numero(linha["casos_est"]), variacao),
        _cartao("Incidencia / 100 mil", _numero(linha["incidencia_100k"], 1)),
        _cartao("Nivel de risco", str(linha["risco"]).capitalize()),
        _cartao(f"Prob. de alerta em {horizonte} semanas",
                f"{linha['probabilidade_alerta']:.0%}"),
    ])

    aviso = ""
    if linha["probabilidade_alerta"] >= 0.5:
        aviso = (f'<div class="alerta">Brasilia em alerta: probabilidade de '
                 f'{linha["probabilidade_alerta"]:.0%} de risco alto ou muito alto em '
                 f'{horizonte} semanas. Principais fatores: {linha["fatores_alerta"]}.</div>')

    entorno = atual[atual["cod_ibge"] != COD_FOCO]
    contexto = (f'<p class="legenda">Entorno ({len(entorno)} municipios): '
                f'{_numero(entorno["casos_est"].sum())} casos estimados, '
                f'{int((entorno["risco_codigo"] >= 2).sum())} em risco alto ou muito alto.</p>')

    return f'<div class="metricas">{cartoes}</div>{aviso}{contexto}'


def secao_mapa(painel: pd.DataFrame, semana: int) -> str:
    atual = painel[painel["se_codigo"] == semana].copy()
    malha = json.loads(CAMINHO_MALHA.read_text(encoding="utf-8"))

    mapa = px.choropleth_map(
        atual, geojson=malha, locations="cod_ibge",
        featureidkey="properties.cod_ibge", color="risco",
        color_discrete_map=CORES_RISCO, category_orders={"risco": ORDEM_RISCO},
        map_style="carto-darkmatter", zoom=6.4,
        center={"lat": -15.9, "lon": -47.6}, opacity=0.78,
        hover_name="municipio",
        hover_data={"cod_ibge": False, "casos_est": ":.0f", "incidencia_100k": ":.1f"},
    )
    mapa.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0},
                       legend={"orientation": "h", "y": -0.03})

    distribuicao = (atual["risco"].value_counts()
                    .reindex(ORDEM_RISCO).fillna(0).astype(int).reset_index())
    distribuicao.columns = ["risco", "municipios"]
    barras = px.bar(distribuicao, x="risco", y="municipios", color="risco",
                    color_discrete_map=CORES_RISCO, text="municipios")
    barras.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Municipios")

    return (f'<div class="duas-colunas"><div>{_figura(mapa, 520)}</div>'
            f'<div>{_figura(barras, 520)}</div></div>')


def secao_series(painel: pd.DataFrame) -> str:
    serie = painel[painel["cod_ibge"] == COD_FOCO].sort_values("data_ini_se")

    casos = go.Figure()
    casos.add_trace(go.Scatter(x=serie["data_ini_se"], y=serie["casos_est_max"],
                               line={"width": 0}, showlegend=False, hoverinfo="skip"))
    casos.add_trace(go.Scatter(x=serie["data_ini_se"], y=serie["casos_est_min"],
                               fill="tonexty", fillcolor="rgba(116,157,196,0.25)",
                               line={"width": 0}, name="Faixa do nowcasting"))
    casos.add_trace(go.Scatter(x=serie["data_ini_se"], y=serie["casos"],
                               name="Casos notificados", line={"color": SUAVE, "width": 1}))
    casos.add_trace(go.Scatter(x=serie["data_ini_se"], y=serie["casos_est"],
                               name="Casos estimados", line={"color": "#EF6C00", "width": 2}))
    casos.update_layout(title="Brasilia: casos notificados e estimados",
                        yaxis_title="Casos na semana",
                        legend={"orientation": "h", "y": 1.12})

    # Brasilia frente ao Entorno, com incidencia padronizada pela populacao.
    grupos = painel.assign(grupo=painel["cod_ibge"].map(
        lambda c: "Brasilia" if c == COD_FOCO else "Entorno (RIDE)"))
    comparacao = grupos.groupby(["grupo", "data_ini_se"], as_index=False).agg(
        {"casos_est": "sum", "pop": "sum"})
    comparacao["incidencia_100k"] = comparacao["casos_est"] / comparacao["pop"] * 1e5

    confronto = px.line(comparacao, x="data_ini_se", y="incidencia_100k", color="grupo",
                        color_discrete_map={"Brasilia": "#C62828",
                                            "Entorno (RIDE)": "#749dc4"})
    confronto.update_layout(title="Brasilia frente ao Entorno",
                            yaxis_title="Incidencia / 100 mil", xaxis_title=None,
                            legend={"orientation": "h", "y": 1.12, "title_text": ""})

    return _figura(casos, 400) + _figura(confronto, 360)


def secao_ranking(painel: pd.DataFrame, semana: int) -> str:
    atual = painel[painel["se_codigo"] == semana].sort_values(
        "probabilidade_alerta", ascending=False)

    tabela = pd.DataFrame({
        "Municipio": atual["municipio"],
        "UF": atual["uf"],
        "Casos estimados": atual["casos_est"].map(lambda v: _numero(v)),
        "Incid./100mil": atual["incidencia_100k"].map(lambda v: _numero(v, 1)),
        "Risco": atual["risco"].astype(str).str.capitalize(),
        "Prob. alerta": atual["probabilidade_alerta"].map(lambda v: f"{v:.0%}"),
        "Principais fatores": atual["fatores_alerta"],
    })

    posicao = list(atual["municipio"]).index(FOCO) + 1 if FOCO in set(atual["municipio"]) else None
    nota = (f'<p class="legenda">Brasilia ocupa a posicao {posicao} de {len(atual)} '
            f'no ranking desta semana.</p>' if posicao else "")
    return nota + _tabela(tabela)


def secao_modelo() -> str:
    if not CAMINHO_DESEMPENHO.exists():
        return "<p>Metricas ainda nao geradas.</p>"

    desempenho = pd.read_csv(CAMINHO_DESEMPENHO)
    nomes = {"referencia": "Referencia (persistencia)",
             "interpretavel": "Interpretavel (logistica)",
             "aprendizado": "Aprendizado (LightGBM)"}
    desempenho["modelo"] = desempenho["modelo"].map(nomes).fillna(desempenho["modelo"])

    curva = px.line(desempenho, x="ano", y="auc", color="modelo", markers=True,
                    color_discrete_sequence=["#749dc4", "#F9A825", "#C62828"])
    curva.update_layout(title="Area sob a curva ROC, por ano de avaliacao",
                        yaxis_title="AUC", xaxis_title=None,
                        legend={"orientation": "h", "y": 1.15, "title_text": ""})

    resumo = desempenho.groupby("modelo")[
        ["sensibilidade", "especificidade", "vpp", "auc", "brier"]].mean().round(3).reset_index()
    resumo.columns = ["Modelo", "Sensibilidade", "Especificidade", "VPP", "AUC", "Brier"]
    for coluna in resumo.columns[1:]:
        resumo[coluna] = resumo[coluna].map(lambda v: _numero(v, 3))

    return _figura(curva, 380) + _tabela(resumo)


def secao_ras() -> str:
    if not CAMINHO_MALHA_RAS.exists():
        return "<p>Malha das Regioes Administrativas ainda nao gerada.</p>"

    malha = json.loads(CAMINHO_MALHA_RAS.read_text(encoding="utf-8"))
    regioes = pd.DataFrame([f["properties"] for f in malha["features"]])
    regioes["populacao"] = pd.to_numeric(regioes["populacao"], errors="coerce")

    mapa = px.choropleth_map(
        regioes, geojson=malha, locations="ra_nome",
        featureidkey="properties.ra_nome", color="populacao",
        color_continuous_scale="YlOrRd", map_style="carto-darkmatter",
        zoom=8.1, center={"lat": -15.78, "lon": -47.93}, opacity=0.78,
        labels={"populacao": "habitantes"},
    )
    mapa.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    tabela = regioes.sort_values("populacao", ascending=False)[["ra_nome", "populacao"]].copy()
    tabela.columns = ["Regiao Administrativa", "Populacao (PDAD 2021)"]
    tabela["Populacao (PDAD 2021)"] = tabela["Populacao (PDAD 2021)"].map(lambda v: _numero(v))

    aviso = ('<div class="observacao">Este mapa nao exibe casos de dengue por Regiao '
             'Administrativa porque nao existe fonte publica com essa serie: o InfoDengue '
             'opera apenas no nivel municipal, o painel da SES-DF nao expoe os dados de '
             'forma programatica, o LIRAa e publicado como relatorio fechado e os '
             'microdados do SINAN dependem do FTP do DATASUS. Repartir os casos do DF '
             'entre as RAs na proporcao da populacao produziria um mapa apenas '
             'aparentemente informativo, que reproduziria o mapa populacional e '
             'esconderia a desigualdade intraurbana real.</div>')

    return (f'<div class="duas-colunas"><div>{_figura(mapa, 520)}</div>'
            f'<div>{_tabela(tabela)}</div></div>{aviso}')


ESTILO = f"""
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: {FUNDO}; color: {TEXTO};
        font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        line-height: 1.5; padding: 28px 20px 60px; }}
.pagina {{ max-width: 1180px; margin: 0 auto; }}
header {{ border-bottom: 1px solid {BORDA}; padding-bottom: 18px; margin-bottom: 28px; }}
h1 {{ font-size: 30px; font-weight: 650; letter-spacing: -0.3px; }}
h2 {{ font-size: 22px; font-weight: 600; margin: 0 0 14px; }}
.subtitulo {{ color: {SUAVE}; font-size: 14px; margin-top: 6px; }}
section {{ background: {CARTAO}; border: 1px solid {BORDA}; border-radius: 12px;
           padding: 20px 22px; margin-bottom: 22px; }}
.metricas {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
             gap: 14px; margin-bottom: 16px; }}
.metrica {{ background: {FUNDO}; border: 1px solid {BORDA}; border-radius: 10px; padding: 14px 16px; }}
.rotulo {{ color: {SUAVE}; font-size: 12px; text-transform: uppercase; letter-spacing: 0.4px; }}
.valor {{ font-size: 27px; font-weight: 650; margin-top: 4px; }}
.nota {{ color: {SUAVE}; font-size: 12px; margin-top: 2px; }}
.alerta {{ background: #5c2b2e; border: 1px solid #C62828; border-radius: 8px;
           padding: 12px 14px; margin: 12px 0; font-size: 14px; }}
.observacao {{ background: {FUNDO}; border-left: 3px solid #F9A825; border-radius: 6px;
               padding: 12px 14px; margin-top: 14px; color: {SUAVE}; font-size: 13px; }}
.legenda {{ color: {SUAVE}; font-size: 13px; margin: 8px 0 12px; }}
.duas-colunas {{ display: grid; grid-template-columns: 1.35fr 1fr; gap: 18px; }}
@media (max-width: 900px) {{ .duas-colunas {{ grid-template-columns: 1fr; }} }}
.rolagem {{ overflow-x: auto; max-height: 460px; overflow-y: auto; border-radius: 8px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ position: sticky; top: 0; background: {FUNDO}; color: {SUAVE}; text-align: left;
      padding: 9px 11px; font-weight: 600; border-bottom: 1px solid {BORDA}; white-space: nowrap; }}
td {{ padding: 8px 11px; border-bottom: 1px solid {BORDA}; }}
tr:hover td {{ background: rgba(116,157,196,0.10); }}
footer {{ color: {SUAVE}; font-size: 12px; text-align: center; margin-top: 30px;
          padding-top: 18px; border-top: 1px solid {BORDA}; }}
"""


def gerar(destino: Path = DESTINO) -> Path:
    painel = pd.read_csv(CAMINHO_PAINEL, parse_dates=["data_ini_se"], low_memory=False)
    painel["risco"] = pd.Categorical(painel["risco"], categories=ORDEM_RISCO, ordered=True)

    semana = int(painel["se_codigo"].max())
    horizonte = int(painel["horizonte_semanas"].iloc[0])
    municipios = painel["cod_ibge"].nunique()

    # Extrai o bundle do Plotly para embutir na pagina: sem ele, os graficos
    # nao renderizam ao abrir o arquivo sem internet. O `to_html` devolve
    # varios <script>, e o da biblioteca e, de longe, o maior deles.
    import re

    referencia = pio.to_html(go.Figure(), include_plotlyjs=True, full_html=False)
    blocos = re.findall(r"<script[^>]*>.*?</script>", referencia, flags=re.DOTALL)
    biblioteca = max(blocos, key=len)

    secoes = [
        ("Brasilia", secao_brasilia(painel, semana, horizonte)),
        ("Mapa de risco", secao_mapa(painel, semana)),
        ("Series temporais", secao_series(painel)),
        ("Ranking e relatorio", secao_ranking(painel, semana)),
        ("Desempenho do modelo", secao_modelo()),
        ("Brasilia por Regiao Administrativa", secao_ras()),
    ]
    corpo = "".join(f"<section><h2>{titulo}</h2>{conteudo}</section>"
                    for titulo, conteudo in secoes)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel VIGIA-Dengue</title>
<style>{ESTILO}</style>
{biblioteca}
</head>
<body>
<div class="pagina">
<header>
  <h1>VIGIA-Dengue</h1>
  <div class="subtitulo">
    Alerta precoce e estratificacao espaco-temporal do risco de dengue &mdash;
    Brasilia e a RIDE-DF ({municipios} municipios) &middot;
    semana epidemiologica {formatar_semana(semana)}
  </div>
</header>
{corpo}
<footer>
  Gerado em {date.today().strftime('%d/%m/%Y')} a partir de dados do InfoDengue
  (Fiocruz/FGV), IBGE e NASA POWER.<br>
  Ferramenta de apoio a vigilancia epidemiologica; nao substitui a analise da
  equipe local nem orienta conduta clinica individual.
</footer>
</div>
</body>
</html>"""

    destino.write_text(html, encoding="utf-8")
    return destino


if __name__ == "__main__":
    caminho = gerar()
    tamanho = caminho.stat().st_size / 1024 / 1024
    print(f"painel gerado: {caminho}")
    print(f"tamanho: {tamanho:.1f} MB")
