"""Testes da previsao de 14 dias (contexto de painel, nunca preditora).

A agregacao e o contrato do JSON sao testados com resposta simulada, sem
rede: o formato que o painel le nao pode depender da API estar de pe na hora
do teste. O unico teste que toca a rede e o de fumaca, pulado quando ela
falta.

Execucao:  python -m pytest testes -q
"""

from __future__ import annotations

import json
import socket
import sys
from datetime import date
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from vigia import clima_futuro  # noqa: E402
from vigia.territorio import TERRITORIO  # noqa: E402


def resposta_simulada() -> dict:
    """Bloco `daily` da Open-Meteo com 14 dias e valores conhecidos.

    O ultimo dia vem como None nas duas variaveis, porque a API devolve null
    na ponta do horizonte e a agregacao nao pode transformar isso em zero.
    """
    return {
        "time": [f"2026-09-{dia:02d}" for dia in range(1, 15)],
        "precipitation_sum": [0.0, 5.0, 0.4, 12.0, 0.0, 1.0, 3.6,
                              0.0, 8.0, 0.9, 0.0, 20.0, 0.0, None],
        "temperature_2m_mean": [24.0, 25.0, 26.0, 27.0, 24.0, 23.0, 22.0,
                                21.0, 25.0, 26.0, 24.0, 25.0, 24.0, None],
    }


def _fingir_rede(monkeypatch, baixar=None):
    """Substitui centroide e API por versoes locais, sem rede nem malha."""
    monkeypatch.setattr(
        clima_futuro, "centroides",
        lambda codigos: {c: (-15.8, -47.9) for c in codigos},
    )
    monkeypatch.setattr(
        clima_futuro, "_baixar_previsao",
        baixar or (lambda latitude, longitude: resposta_simulada()),
    )


def test_resumo_agrega_chuva_e_temperatura():
    resumo = clima_futuro.resumir(resposta_simulada())
    assert resumo["chuva_7d_mm"] == pytest.approx(22.0)
    assert resumo["chuva_14d_mm"] == pytest.approx(50.9)
    # Dias com >= 1 mm: 5.0, 12.0, 1.0, 3.6, 8.0 e 20.0.
    assert resumo["dias_chuva_14d"] == 6
    # Media das 13 temperaturas validas; o None do ultimo dia fica de fora.
    assert resumo["temp_media_14d"] == pytest.approx(24.3)


def test_resumo_sem_temperatura_valida_devolve_none():
    diario = resposta_simulada()
    diario["temperature_2m_mean"] = [None] * 14
    assert clima_futuro.resumir(diario)["temp_media_14d"] is None


def test_dia_sem_previsao_nao_vira_dia_seco():
    """None nao pode entrar na soma como zero nem na contagem de dias."""
    diario = resposta_simulada()
    diario["precipitation_sum"] = [None] * 13 + [7.0]
    resumo = clima_futuro.resumir(diario)
    assert resumo["chuva_7d_mm"] == pytest.approx(0.0)
    assert resumo["chuva_14d_mm"] == pytest.approx(7.0)
    assert resumo["dias_chuva_14d"] == 1


def test_semana_epidemiologica_segue_o_criterio_brasileiro():
    """SE 1 e a semana que contem 4 de janeiro; a semana comeca no domingo."""
    assert clima_futuro._se_codigo(date(2026, 1, 4)) == 202601
    # 3/1/2026 (sabado) ainda pertence a ultima semana de 2025, a SE 53.
    assert clima_futuro._se_codigo(date(2026, 1, 3)) == 202553
    # Toda a semana de 27/9 a 3/10 de 2026 leva o mesmo rotulo.
    assert clima_futuro._se_codigo(date(2026, 9, 27)) == 202639
    assert clima_futuro._se_codigo(date(2026, 10, 3)) == 202639


def test_contrato_do_json_que_o_painel_le(monkeypatch, tmp_path):
    """As chaves gravadas sao o contrato com o time do painel."""
    _fingir_rede(monkeypatch)
    destino = tmp_path / "clima_futuro.json"
    clima_futuro.salvar(destino, pausa=0)

    gravado = json.loads(destino.read_text(encoding="utf-8"))
    assert set(gravado) == {
        "coletado_para_semana", "fonte", "municipios", "faltantes"
    }
    assert gravado["fonte"] == "Open-Meteo forecast"
    assert gravado["coletado_para_semana"] == clima_futuro._se_codigo(date.today())
    assert gravado["faltantes"] == []
    assert len(gravado["municipios"]) == len(TERRITORIO)
    for registro in gravado["municipios"]:
        assert set(registro) == {
            "cod_ibge", "municipio", "chuva_7d_mm", "chuva_14d_mm",
            "dias_chuva_14d", "temp_media_14d",
        }
        assert registro["cod_ibge"] in TERRITORIO


def test_falha_num_municipio_nao_derruba_a_coleta(monkeypatch):
    """Previsao e contexto: quem falhar vai para faltantes e a coleta segue."""
    chamadas = {"n": 0}

    def baixar_com_uma_falha(latitude, longitude):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise RuntimeError("falha simulada")
        return resposta_simulada()

    _fingir_rede(monkeypatch, baixar=baixar_com_uma_falha)
    payload = clima_futuro.coletar(pausa=0)
    assert len(payload["municipios"]) == len(TERRITORIO) - 1
    assert len(payload["faltantes"]) == 1
    assert set(payload["faltantes"][0]) == {"cod_ibge", "municipio"}


def test_municipio_sem_centroide_vira_faltante(monkeypatch):
    codigos = sorted(TERRITORIO)
    sem_o_primeiro = {c: (-15.8, -47.9) for c in codigos[1:]}
    monkeypatch.setattr(clima_futuro, "centroides", lambda cs: sem_o_primeiro)
    monkeypatch.setattr(
        clima_futuro, "_baixar_previsao",
        lambda latitude, longitude: resposta_simulada(),
    )
    payload = clima_futuro.coletar(pausa=0)
    assert any(f["cod_ibge"] == codigos[0] for f in payload["faltantes"])
    assert len(payload["municipios"]) == len(TERRITORIO) - 1


def _tem_rede() -> bool:
    try:
        socket.create_connection(("api.open-meteo.com", 443), timeout=5).close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _tem_rede(), reason="sem rede para o teste de fumaca")
def test_fumaca_previsao_real_para_brasilia():
    """Uma chamada real, so para acusar mudanca de formato na API."""
    diario = clima_futuro._baixar_previsao(-15.78, -47.93)
    assert len(diario["time"]) == clima_futuro.DIAS_DE_PREVISAO
    resumo = clima_futuro.resumir(diario)
    assert resumo["chuva_14d_mm"] >= 0
    assert 0 <= resumo["dias_chuva_14d"] <= clima_futuro.DIAS_DE_PREVISAO
