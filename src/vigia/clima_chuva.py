"""Precipitacao semanal por municipio (Open-Meteo, ERA5).

A revisao sistematica de modelos de alerta de dengue mostra que a chuva entra
em cerca de 83% dos modelos publicados, ao lado de temperatura (99%) e umidade
(80%). O InfoDengue entrega temperatura e umidade, mas NAO entrega
precipitacao -- era a maior lacuna da base frente a literatura.

A chuva atua sobre a dengue por dois mecanismos opostos, e por isso o modulo
gera mais de uma leitura do mesmo fenomeno: chuva moderada acumulada cria
criadouros (efeito positivo, com defasagem de 4 a 8 semanas ate o caso), mas
chuva intensa demais lava os criadouros (efeito negativo). Periodos secos
prolongados tambem elevam o risco em area urbana, porque levam ao
armazenamento domiciliar de agua.

Fonte: Open-Meteo Historical Weather API, que serve a reanalise ERA5 do ECMWF
em grade de aproximadamente 25 km. E gratuita, nao exige chave e cobre todo o
periodo do projeto. As coordenadas de cada municipio vem da API de localidades
do IBGE.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

from .territorio import TERRITORIO

ARQUIVO_HISTORICO = "https://archive-api.open-meteo.com/v1/archive"
NASA_POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"

# Apenas precipitacao: temperatura e umidade ja vem do InfoDengue, e pedi-las
# aqui quintuplicaria o volume por requisicao contra a cota horaria da API.
DIARIAS = ["precipitation_sum"]


def centroides(geocodigos: list[int]) -> dict[int, tuple[float, float]]:
    """Obtem latitude e longitude do centro de cada municipio.

    Usa a malha do IBGE ja baixada pelo projeto, calculando o centro do
    retangulo envolvente de cada poligono -- suficiente para consultar uma
    grade climatica de 25 km.

    O ponto e o centro geometrico do municipio, nao a sede urbana. Em
    municipios extensos isso desloca a medida para a area rural: no DF, o
    centroide rende cerca de 980 mm/ano contra os cerca de 1.300 mm medidos
    sobre o centro de Brasilia. A sazonalidade -- que e o que o modelo usa --
    fica preservada, mas o nivel absoluto nao deve ser lido como a chuva da
    cidade.
    """
    import json

    caminho = Path(__file__).resolve().parents[2] / "dados" / "externo" / "malha_ride_df.geojson"
    colecao = json.loads(caminho.read_text(encoding="utf-8"))

    pontos: dict[int, tuple[float, float]] = {}
    for feicao in colecao["features"]:
        codigo = int(feicao["properties"]["cod_ibge"])
        if codigo not in geocodigos:
            continue
        coordenadas: list[list[float]] = []

        def percorrer(no):
            if isinstance(no, (float, int)):
                return
            if len(no) == 2 and all(isinstance(v, (float, int)) for v in no):
                coordenadas.append(no)
                return
            for filho in no:
                percorrer(filho)

        percorrer(feicao["geometry"]["coordinates"])
        longitudes = [c[0] for c in coordenadas]
        latitudes = [c[1] for c in coordenadas]
        pontos[codigo] = (
            (min(latitudes) + max(latitudes)) / 2,
            (min(longitudes) + max(longitudes)) / 2,
        )
    return pontos


def _baixar_open_meteo(latitude: float, longitude: float,
                       inicio: str, fim: str) -> pd.DataFrame:
    """Serie diaria de precipitacao pela Open-Meteo (reanalise ERA5)."""
    parametros = {
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "start_date": inicio,
        "end_date": fim,
        "daily": ",".join(DIARIAS),
        "timezone": "America/Sao_Paulo",
    }
    resposta = requests.get(ARQUIVO_HISTORICO, params=parametros, timeout=240)
    resposta.raise_for_status()
    return pd.DataFrame(resposta.json()["daily"])


def _baixar_nasa_power(latitude: float, longitude: float,
                       inicio: str, fim: str) -> pd.DataFrame:
    """Serie diaria de precipitacao pela NASA POWER.

    Fonte de reserva: nao exige chave e nao aplica a cota horaria agressiva da
    Open-Meteo, o que a torna utilizavel quando a primeira se esgota. Entrega
    `PRECTOTCORR`, precipitacao corrigida por vies, em mm/dia.
    """
    parametros = {
        "parameters": "PRECTOTCORR",
        "community": "AG",
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "start": inicio.replace("-", ""),
        "end": fim.replace("-", ""),
        "format": "JSON",
    }
    resposta = requests.get(NASA_POWER, params=parametros, timeout=300)
    resposta.raise_for_status()
    serie = resposta.json()["properties"]["parameter"]["PRECTOTCORR"]

    tabela = pd.DataFrame(
        {"time": list(serie.keys()), "precipitation_sum": list(serie.values())}
    )
    tabela["time"] = pd.to_datetime(tabela["time"], format="%Y%m%d")
    # A NASA usa -999 como marcador de dado indisponivel.
    tabela.loc[tabela["precipitation_sum"] < 0, "precipitation_sum"] = pd.NA
    return tabela


def baixar_municipio(latitude: float, longitude: float, inicio: str, fim: str,
                     tentativas: int = 3) -> pd.DataFrame:
    """Baixa a serie diaria de um ponto, com fonte de reserva.

    Tenta a Open-Meteo e, se ela recusar (tipicamente 429 por cota horaria
    esgotada), recorre a NASA POWER. Assim a coleta nao fica refem da cota de
    um unico provedor.
    """
    ultimo_erro: Exception | None = None
    for tentativa in range(tentativas):
        for baixar in (_baixar_open_meteo, _baixar_nasa_power):
            try:
                return baixar(latitude, longitude, inicio, fim)
            except Exception as erro:
                ultimo_erro = erro
        time.sleep(15 * (tentativa + 1))
    raise RuntimeError(f"falha em ({latitude}, {longitude}): {ultimo_erro}")


def agregar_semana_epidemiologica(diario: pd.DataFrame) -> pd.DataFrame:
    """Converte a serie diaria em semana epidemiologica.

    A semana epidemiologica brasileira comeca no domingo. O rotulo usado aqui
    e a data do domingo inicial, o mesmo criterio de `data_ini_se` do
    InfoDengue, o que garante o encaixe exato entre as duas bases.
    """
    dados = diario.copy()
    dados["data"] = pd.to_datetime(dados["time"])
    # weekday(): segunda=0 ... domingo=6. Recuar ate o domingo anterior.
    dados["data_ini_se"] = dados["data"] - pd.to_timedelta(
        (dados["data"].dt.weekday + 1) % 7, unit="D"
    )

    semanal = dados.groupby("data_ini_se").agg(
        chuva_semana_mm=("precipitation_sum", "sum"),
        chuva_dias_com_chuva=("precipitation_sum", lambda s: int((s >= 1.0).sum())),
        chuva_max_diaria_mm=("precipitation_sum", "max"),
        dias_no_periodo=("precipitation_sum", "size"),
    ).reset_index()

    # Semanas incompletas nas bordas da serie nao representam o total real.
    return semanal[semanal["dias_no_periodo"] == 7].drop(columns="dias_no_periodo")


def coletar(inicio: str = "2014-01-01", fim: str | None = None,
            destino: Path | None = None, anos_por_bloco: int = 4) -> pd.DataFrame:
    """Baixa e consolida a precipitacao semanal de todo o territorio.

    A API gratuita impoe uma cota HORARIA de volume, e nao apenas um limite de
    requisicoes por minuto: uma serie longa de varias variaveis a esgota e
    passa a devolver 429 ate a hora virar. Por isso este coletor pede somente
    a precipitacao, baixa em blocos de poucos anos e grava o resultado parcial
    a cada municipio -- uma interrupcao por cota nao joga fora o ja coletado,
    e basta reexecutar para retomar de onde parou.
    """
    if fim is None:
        fim = (pd.Timestamp.today() - pd.Timedelta(days=6)).strftime("%Y-%m-%d")

    ano_inicial = int(inicio[:4])
    ano_final = int(fim[:4])
    blocos: list[tuple[str, str]] = []
    ano = ano_inicial
    while ano <= ano_final:
        ultimo = min(ano + anos_por_bloco - 1, ano_final)
        blocos.append((
            f"{max(ano, ano_inicial)}-01-01",
            fim if ultimo == ano_final else f"{ultimo}-12-31",
        ))
        ano = ultimo + 1

    pontos = centroides(sorted(TERRITORIO))

    # Retoma de onde parou, se ja houver arquivo parcial.
    ja_coletados: set[int] = set()
    partes: list[pd.DataFrame] = []
    if destino is not None and destino.exists():
        anterior = pd.read_csv(destino)
        partes.append(anterior)
        ja_coletados = set(anterior["cod_ibge"].unique())
        print(f"retomando: {len(ja_coletados)} municipios ja coletados")

    for indice, (codigo, (latitude, longitude)) in enumerate(sorted(pontos.items()), start=1):
        if codigo in ja_coletados:
            continue

        pedacos = []
        for bloco_inicio, bloco_fim in blocos:
            diario = baixar_municipio(latitude, longitude, bloco_inicio, bloco_fim)
            pedacos.append(diario)
            time.sleep(4)

        semanal = agregar_semana_epidemiologica(pd.concat(pedacos, ignore_index=True))
        semanal["cod_ibge"] = codigo
        partes.append(semanal)
        print(f"[{indice:2d}/{len(pontos)}] {TERRITORIO[codigo]:28s} {len(semanal):4d} semanas")

        if destino is not None:
            destino.parent.mkdir(parents=True, exist_ok=True)
            pd.concat(partes, ignore_index=True).to_csv(destino, index=False, encoding="utf-8")

    consolidado = pd.concat(partes, ignore_index=True)
    return consolidado.drop_duplicates(subset=["cod_ibge", "data_ini_se"])
