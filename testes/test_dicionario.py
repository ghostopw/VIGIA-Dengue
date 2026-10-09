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

from vigia.dicionario import (  # noqa: E402
    SAIDA_CSV,
    SAIDA_GLOSSARIO,
    gerar,
    glossario,
    sem_descricao,
)
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


def test_glossario_explica_todo_tipo_papel_e_fonte_da_tabela(tabela):
    """Quem le a tabela no site nao pode esbarrar em termo sem explicacao.

    Falhou aqui? Acrescente o termo em GLOSSARIO, em src/vigia/dicionario.py.
    """
    termos = set(glossario()["termo"])
    assert not set(tabela["tipo"]) - termos, "tipo sem explicacao"
    assert not set(tabela["papel"]) - termos, "papel sem explicacao"
    fontes_do_glossario = termos & {"InfoDengue", "SINAN", "IBGE",
                                    "ERA5/Open-Meteo", "Derivada"}
    for fonte in set(tabela["fonte"]):
        assert any(f in fonte for f in fontes_do_glossario), (
            f"fonte sem explicacao no glossario: {fonte}")


def test_glossario_publicado_esta_sincronizado():
    """O CSV que o painel le precisa ser o glossario do gerador.

    Falhou aqui? Rode: python src/vigia/executar_dicionario.py
    """
    assert SAIDA_GLOSSARIO.exists(), "docs/glossario.csv nao existe"
    publicado = pd.read_csv(SAIDA_GLOSSARIO)
    assert publicado.equals(glossario()), (
        "docs/glossario.csv esta defasado -- regenere com "
        "python src/vigia/executar_dicionario.py")
