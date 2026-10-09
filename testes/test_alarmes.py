"""Testes do motor de alarmes.

O contrato central e epidemiologico, nao tecnico: so regra APROVADA na
medicao historica pode disparar alarme no painel. Se alguem ligar uma regra
reprovada (ou desligar uma aprovada) sem refazer a medicao, o primeiro teste
acusa. Os demais garantem que o gatilho liga e desliga como anunciado e que
o JSON gravado mantem as chaves que o painel le.

Execucao:  python -m pytest testes/test_alarmes.py -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from vigia.alarmes import (  # noqa: E402
    EVIDENCIA,
    LIMIAR_P_RT1,
    REGRAS,
    SEMANAS_SEGUIDAS,
    _AVALIADORES,
    avaliar,
    salvar,
)

BASE_REAL = RAIZ / "dados" / "processado" / "base_com_risco.csv"

CHAVES_ALARME = {
    "id", "municipio", "cod_ibge", "semana", "valor_gatilho",
    "lag_semanas", "lift_historico", "frase",
}


def base_sintetica() -> pd.DataFrame:
    """Serie curta onde se sabe exatamente quem liga e quem nao liga a R3.

    Os codigos IBGE sao reais de proposito: Agua Fria de Goias tem o maior
    lift municipal da R3 (34.52) e Valparaiso o menor (0.67), o que permite
    testar a ordenacao por lift sem inventar historico.
    """
    series = [
        # (cod_ibge, municipio, p_rt1 das 3 ultimas semanas)
        (5221858, "Valparaiso de Goias", [0.50, 0.91, 0.93]),   # liga
        (5200175, "Agua Fria de Goias", [0.20, 0.95, 0.97]),    # liga
        (5208004, "Formosa", [0.95, 0.50, 0.97]),               # so a atual: nao liga
        (5212501, "Luziania", [0.95, np.nan, 0.92]),            # sem Rt na anterior: nao liga
    ]
    linhas = []
    for cod_ibge, municipio, valores in series:
        for passo, p_rt1 in enumerate(valores):
            linhas.append({
                "cod_ibge": cod_ibge,
                "municipio": municipio,
                "se_codigo": 202632 + passo,
                "p_rt1": p_rt1,
            })
    # Municipio com uma unica semana: nao ha como confirmar 2 seguidas.
    linhas.append({
        "cod_ibge": 5204003, "municipio": "Cabeceiras",
        "se_codigo": 202634, "p_rt1": 0.99,
    })
    return pd.DataFrame(linhas)


def test_regras_do_motor_sao_exatamente_as_aprovadas():
    """Nenhuma regra entra ou sai do motor sem passar pela medicao."""
    aprovadas = [regra for regra in EVIDENCIA["regras"] if regra["aprovada"]]
    assert [regra["id"] for regra in REGRAS] == [regra["id"] for regra in aprovadas]
    # Todo alarme possivel precisa de avaliador, e nenhum avaliador pode
    # existir para regra reprovada.
    assert set(_AVALIADORES) == {regra["id"] for regra in aprovadas}
    for motor, medida in zip(REGRAS, aprovadas):
        assert motor["condicao"] == medida["condicao"]
        assert motor["lag_semanas"] == medida["lag_semanas"]
        assert motor["frase_evidencia"] == medida["frase_evidencia"]


def test_limiar_do_motor_confere_com_a_condicao_medida():
    """Os numeros do codigo devem ser os mesmos da condicao aprovada."""
    r3 = next(regra for regra in REGRAS if regra["id"] == "R3")
    assert "0,9" in r3["condicao"]
    assert LIMIAR_P_RT1 == 0.9
    assert SEMANAS_SEGUIDAS == 2


def test_avaliar_liga_e_desliga_a_r3_como_esperado():
    alarmes = avaliar(base_sintetica())

    assert [alarme["cod_ibge"] for alarme in alarmes] == [5200175, 5221858]
    for alarme in alarmes:
        assert set(alarme) == CHAVES_ALARME
        assert alarme["id"] == "R3"
        assert alarme["semana"] == 202634
        assert alarme["lag_semanas"] == 4

    primeiro = alarmes[0]
    assert primeiro["municipio"] == "Agua Fria de Goias"
    assert primeiro["valor_gatilho"] == pytest.approx(0.97)
    assert primeiro["lift_historico"] == pytest.approx(34.52)
    assert primeiro["frase"].startswith("Agua Fria de Goias: ")
    r3 = next(regra for regra in REGRAS if regra["id"] == "R3")
    assert primeiro["frase"].endswith(r3["frase_evidencia"])


def test_avaliar_sem_gatilho_devolve_lista_vazia():
    quieta = base_sintetica()
    quieta["p_rt1"] = 0.1
    assert avaliar(quieta) == []


def test_avaliar_exige_colunas_obrigatorias():
    with pytest.raises(ValueError, match="p_rt1"):
        avaliar(pd.DataFrame({"cod_ibge": [1], "municipio": ["X"], "se_codigo": [202601]}))


def test_salvar_escreve_o_contrato_do_painel(tmp_path: Path):
    destino = tmp_path / "alarmes.json"
    payload = salvar(base_sintetica(), destino)

    gravado = json.loads(destino.read_text(encoding="utf-8"))
    assert set(gravado) == {"gerado_da_semana", "alarmes", "regras"}
    assert gravado == payload
    assert gravado["gerado_da_semana"] == 202634
    assert gravado["regras"] == EVIDENCIA
    assert len(gravado["alarmes"]) == 2
    assert all(set(alarme) == CHAVES_ALARME for alarme in gravado["alarmes"])


@pytest.mark.skipif(not BASE_REAL.exists(), reason="base_com_risco.csv nao esta neste ambiente")
def test_avaliar_roda_na_base_real():
    base = pd.read_csv(BASE_REAL)
    alarmes = avaliar(base)
    assert isinstance(alarmes, list)
    ids_aprovados = {regra["id"] for regra in REGRAS}
    for alarme in alarmes:
        assert alarme["id"] in ids_aprovados
        assert set(alarme) == CHAVES_ALARME
