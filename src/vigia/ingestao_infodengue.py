"""Ingestao da serie municipio-semana epidemiologica do InfoDengue.

O InfoDengue (Fiocruz/FGV) publica, por municipio e semana epidemiologica,
casos notificados, casos estimados por nowcasting (corrigidos pelo atraso de
notificacao), incidencia por 100 mil habitantes, numero reprodutivo Rt e
variaveis climaticas agregadas na semana.

Documentacao da API: https://info.dengue.mat.br/services/api
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

from .territorio import TERRITORIO, UF_POR_CODIGO

API = "https://info.dengue.mat.br/api/alertcity"

# Colunas numericas que a API devolve como texto e precisam ser convertidas.
COLUNAS_NUMERICAS = [
    "casos", "casos_est", "casos_est_min", "casos_est_max", "casprov",
    "p_inc100k", "p_rt1", "Rt", "pop", "nivel", "nivel_inc",
    "tempmin", "tempmed", "tempmax", "umidmin", "umidmed", "umidmax",
    "receptivo", "transmissao", "notif_accum_year",
]


def baixar_municipio(
    geocode: int,
    ano_inicio: int,
    ano_fim: int,
    doenca: str = "dengue",
    tentativas: int = 3,
) -> pd.DataFrame:
    """Baixa a serie semanal completa de um municipio no intervalo de anos."""
    parametros = {
        "geocode": geocode,
        "disease": doenca,
        "format": "json",
        "ew_start": 1,
        "ew_end": 53,
        "ey_start": ano_inicio,
        "ey_end": ano_fim,
    }
    ultimo_erro: Exception | None = None
    for tentativa in range(tentativas):
        try:
            resposta = requests.get(API, params=parametros, timeout=180)
            resposta.raise_for_status()
            return pd.DataFrame(resposta.json())
        except Exception as erro:  # rede instavel: espera progressiva
            ultimo_erro = erro
            time.sleep(5 * (tentativa + 1))
    raise RuntimeError(f"falha ao baixar geocode {geocode}: {ultimo_erro}")


def padronizar(bruto: pd.DataFrame, geocode: int) -> pd.DataFrame:
    """Converte tipos e cria as chaves de identificacao do municipio-semana."""
    dados = bruto.copy()
    for coluna in COLUNAS_NUMERICAS:
        if coluna in dados.columns:
            dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")

    # data_iniSE vem em milissegundos desde a epoca (inicio da semana epidemiologica).
    dados["data_ini_se"] = pd.to_datetime(dados["data_iniSE"], unit="ms")
    dados["cod_ibge"] = geocode
    dados["municipio"] = TERRITORIO.get(geocode)
    dados["uf"] = UF_POR_CODIGO.get(geocode)
    dados["ano"] = (dados["SE"] // 100).astype("int64")
    dados["semana"] = (dados["SE"] % 100).astype("int64")
    return dados.rename(columns={"SE": "se_codigo"})


def baixar_territorio(
    ano_inicio: int,
    ano_fim: int,
    destino: Path,
    doenca: str = "dengue",
) -> pd.DataFrame:
    """Baixa e consolida a serie de todas as unidades do territorio piloto."""
    destino.mkdir(parents=True, exist_ok=True)
    partes: list[pd.DataFrame] = []
    total = len(TERRITORIO)

    for indice, (geocode, nome) in enumerate(sorted(TERRITORIO.items()), start=1):
        bruto = baixar_municipio(geocode, ano_inicio, ano_fim, doenca)
        if bruto.empty:
            print(f"[{indice:2d}/{total}] {nome:28s} SEM DADOS")
            continue
        parte = padronizar(bruto, geocode)
        parte.to_csv(destino / f"{doenca}_{geocode}.csv", index=False, encoding="utf-8")
        partes.append(parte)
        print(f"[{indice:2d}/{total}] {nome:28s} {len(parte):4d} semanas")
        time.sleep(1)  # cortesia com a API publica

    if not partes:
        raise RuntimeError("nenhum municipio retornou dados")

    consolidado = pd.concat(partes, ignore_index=True)
    return consolidado.sort_values(["cod_ibge", "se_codigo"]).reset_index(drop=True)
