"""Testes do dicionario de dados.

A regra que estes testes protegem: a documentacao publicada nunca pode
descrever uma base que deixou de existir. Se alguem acrescentar coluna a base
sem descreve-la, ou mudar a base sem regenerar os artefatos, um teste falha
apontando exatamente o que ficou para tras.

Execucao:  python -m pytest testes -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from vigia.dicionario import SAIDA_CSV, gerar, sem_descricao  # noqa: E402
from vigia.modelagem import VARIAVEIS, VARIAVEIS_ESSENCIAIS  # noqa: E402

CAMINHO_BASE = RAIZ / "dados" / "processado" / "base_com_risco.csv"

pytestmark = pytest.mark.skipif(
    not CAMINHO_BASE.exists(),
    reason="exige a base local (dados/processado nao e versionado); "
           "gere com executar_analise.py",
)


@pytest.fixture(scope="module")
def base() -> pd.DataFrame:
    return pd.read_csv(CAMINHO_BASE, low_memory=False)


@pytest.fixture(scope="module")
def tabela(base) -> pd.DataFrame:
    return gerar(base)


def test_toda_coluna_da_base_tem_descricao(tabela):
    faltando = sem_descricao(tabela)
    assert not faltando, (
        "colunas da base sem descricao no dicionario -- acrescente em "
        f"src/vigia/dicionario.py: {faltando}")


def test_dicionario_cobre_exatamente_as_colunas_da_base(base, tabela):
    assert set(tabela["coluna"]) == set(base.columns)
    assert len(tabela) == len(base.columns)


def test_papeis_batem_com_as_listas_do_modelo(tabela):
    preditoras = set(tabela.loc[tabela["papel"].str.startswith("preditor"),
                                "coluna"])
    assert preditoras == set(VARIAVEIS), (
        "o papel 'preditor' do dicionario divergiu de modelagem.VARIAVEIS")
    essenciais = set(tabela.loc[tabela["papel"] == "preditor essencial",
                                "coluna"])
    assert essenciais == set(VARIAVEIS_ESSENCIAIS)
    assert (tabela.loc[tabela["coluna"] == "risco_codigo", "papel"]
            .item() == "origem do alvo")


def test_csv_publicado_esta_sincronizado_com_a_base(base):
    """O CSV que a aba Dicionario do painel le nao pode ficar para tras.

    Falhou aqui? Rode: python src/vigia/executar_dicionario.py
    """
    assert SAIDA_CSV.exists(), "docs/dicionario_de_dados.csv nao existe"
    publicado = pd.read_csv(SAIDA_CSV)
    assert set(publicado["coluna"]) == set(base.columns), (
        "docs/dicionario_de_dados.csv descreve outra versao da base -- "
        "regenere com: python src/vigia/executar_dicionario.py")
    colunas = {"coluna", "bloco", "tipo", "descricao", "fonte", "papel",
               "preenchida_pct"}
    assert colunas.issubset(publicado.columns)
    assert publicado["descricao"].notna().all()
