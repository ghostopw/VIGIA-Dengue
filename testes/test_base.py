"""Testes das regras criticas da base analitica.

O teste mais importante deste arquivo e o de vazamento temporal: se uma
variavel explicativa passar a enxergar o futuro, as metricas do modelo ficam
otimistas e a ferramenta falha em operacao real. Esse erro e silencioso, por
isso e verificado automaticamente.

Execucao:  python -m pytest testes -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from vigia.base_analitica import construir  # noqa: E402
from vigia.risco import classificar  # noqa: E402
from vigia.territorio import TERRITORIO, UF_POR_CODIGO  # noqa: E402


def serie_sintetica(n_semanas: int = 120, n_municipios: int = 3) -> pd.DataFrame:
    """Painel artificial com sazonalidade, para testar as regras sem rede."""
    gerador = np.random.default_rng(42)
    linhas = []
    for indice in range(n_municipios):
        codigo = 5300108 + indice
        for passo in range(n_semanas):
            ano = 2014 + passo // 52
            semana = passo % 52 + 1
            sazonal = 40 + 35 * np.sin(2 * np.pi * semana / 52)
            casos = max(0, int(sazonal + gerador.normal(0, 8)))
            linhas.append({
                "cod_ibge": codigo,
                "municipio": f"Municipio {indice}",
                "uf": "DF",
                "ano": ano,
                "semana": semana,
                "se_codigo": ano * 100 + semana,
                "data_ini_se": pd.Timestamp("2014-01-05") + pd.Timedelta(weeks=passo),
                "casos": casos,
                "casos_est": float(casos),
                "casos_est_min": float(casos),
                "casos_est_max": float(casos),
                "pop": 100_000 * (indice + 1),
                "tempmed": 24 + 4 * np.sin(2 * np.pi * semana / 52),
                "tempmin": 19.0,
                "tempmax": 30.0,
                "umidmed": 70.0,
                "umidmin": 50.0,
                "umidmax": 90.0,
            })
    return pd.DataFrame(linhas)


@pytest.fixture(scope="module")
def base() -> pd.DataFrame:
    return construir(serie_sintetica())


def test_territorio_tem_33_unidades():
    assert len(TERRITORIO) == 33
    assert 5300108 in TERRITORIO  # Distrito Federal
    assert set(UF_POR_CODIGO.values()) == {"DF", "GO", "MG"}


def test_chave_municipio_semana_e_unica(base: pd.DataFrame):
    assert not base.duplicated(subset=["cod_ibge", "se_codigo"]).any()


def test_incidencia_confere_com_casos_e_populacao(base: pd.DataFrame):
    esperado = base["casos_est"] / base["pop"] * 1e5
    assert np.allclose(base["incidencia_100k"], esperado, equal_nan=True)


def test_medias_moveis_nao_usam_a_semana_corrente(base: pd.DataFrame):
    """A media movel da semana t deve reproduzir as 3 semanas ANTERIORES."""
    municipio = base[base["cod_ibge"] == 5300108].sort_values("data_ini_se").reset_index(drop=True)
    for posicao in (20, 50, 90):
        anteriores = municipio.loc[posicao - 3:posicao - 1, "casos_est"].mean()
        assert municipio.loc[posicao, "casos_est_mm3"] == pytest.approx(anteriores)


def test_defasagem_reproduz_valor_passado(base: pd.DataFrame):
    municipio = base[base["cod_ibge"] == 5300108].sort_values("data_ini_se").reset_index(drop=True)
    for posicao in (15, 60, 100):
        assert municipio.loc[posicao, "casos_est_lag4"] == municipio.loc[posicao - 4, "casos_est"]


def test_lag_nao_correlaciona_com_futuro(base: pd.DataFrame):
    """Nenhuma variavel defasada pode coincidir com o valor da semana seguinte."""
    municipio = base[base["cod_ibge"] == 5300108].sort_values("data_ini_se").reset_index(drop=True)
    futuro = municipio["casos_est"].shift(-1)
    coincidencias = (municipio["casos_est_lag1"] == futuro).sum()
    assert coincidencias < len(municipio) * 0.1


def test_flag_provisorio_ignora_semana_sem_casos(base: pd.DataFrame):
    """Semana sem nenhum caso e dado legitimo, nao dado incompleto."""
    sem_casos = base[base["casos_est"] == 0]
    if not sem_casos.empty:
        assert (sem_casos["dado_provisorio"] == 0).all()


def test_clima_sem_faltantes_apos_imputacao(base: pd.DataFrame):
    assert base["tempmed"].isna().sum() == 0
    assert base["umidmed"].isna().sum() == 0


def test_risco_usa_apenas_anos_anteriores():
    """O canal endemico do primeiro ano nao pode existir: nao ha historico."""
    classificado = classificar(construir(serie_sintetica()))
    primeiro_ano = classificado[classificado["ano"] == 2014]
    assert primeiro_ano["canal_q3"].isna().all()


def test_niveis_de_risco_sao_os_quatro_previstos():
    classificado = classificar(construir(serie_sintetica()))
    assert set(classificado["risco"].dropna().unique()) <= {
        "baixo", "moderado", "alto", "muito alto"
    }
    assert classificado["risco_codigo"].between(0, 3).all()
