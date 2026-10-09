"""Previsao do tempo dos proximos 14 dias para o territorio (Open-Meteo).

A chuva OBSERVADA vem de `clima_chuva.py` (reanalise ERA5) e alimenta o
modelo. Este modulo olha na direcao oposta: a PREVISAO meteorologica dos
proximos 14 dias, que da contexto de painel -- "vem chuva por ai, criadouro
se forma em dias" -- para quem decide acao de campo hoje.

REGRA: a previsao e CONTEXTO de painel, jamais preditora do modelo. O modelo
so pode aprender com o que era conhecido em cada semana historica, e nao
existe arquivo de previsoes passadas para treinar sem vazamento; alem disso
a previsao meteorologica erra, e esse erro entraria no modelo disfarcado de
dado.

O painel NAO importa este modulo nem chama rede: ele so LE o JSON gravado em
`saidas/clima_futuro.json` pelo ciclo de atualizacao. Assim o container do
painel continua enxuto (streamlit+pandas+plotly), como manda a regra do
projeto.

Fonte: Open-Meteo Forecast API -- gratuita, sem chave, mesmo provedor da
chuva observada -- consultada nas mesmas coordenadas de centroide por
municipio que `clima_chuva.centroides` ja calcula da malha do IBGE. Por ser
contexto, falhar e aceitavel: nao ha fonte de reserva, e quem nao responder
fica registrado em "faltantes".
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

import requests

from .clima_chuva import centroides
from .territorio import TERRITORIO

PREVISAO = "https://api.open-meteo.com/v1/forecast"
DIAS_DE_PREVISAO = 14

# Mesmo criterio de "dia com chuva" da serie observada (clima_chuva.py:
# precipitacao >= 1 mm), para que os dois numeros sejam comparaveis no painel.
LIMIAR_DIA_COM_CHUVA_MM = 1.0

RAIZ = Path(__file__).resolve().parents[2]
ARQUIVO_PADRAO = RAIZ / "saidas" / "clima_futuro.json"
FONTE = "Open-Meteo forecast"


def _se_codigo(dia: date) -> int:
    """Codigo AAAASS da semana epidemiologica brasileira de uma data.

    A semana epidemiologica comeca no domingo e pertence ao ano que contem
    pelo menos 4 dos seus 7 dias -- na pratica, o ano da quarta-feira da
    semana. Disso decorre que a SE 1 e sempre a semana que contem o dia 4 de
    janeiro. E o mesmo criterio do `data_ini_se` do InfoDengue, para que o
    rotulo gravado aqui case com o `se_codigo` da base analitica.
    """
    # weekday(): segunda=0 ... domingo=6. Recuar ate o domingo da semana.
    domingo = dia - timedelta(days=(dia.weekday() + 1) % 7)
    ano = (domingo + timedelta(days=3)).year
    referencia = date(ano, 1, 4)
    inicio_se1 = referencia - timedelta(days=(referencia.weekday() + 1) % 7)
    return ano * 100 + (domingo - inicio_se1).days // 7 + 1


def _baixar_previsao(latitude: float, longitude: float) -> dict:
    """Bloco `daily` da previsao de 14 dias para um ponto."""
    parametros = {
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "daily": "precipitation_sum,temperature_2m_mean",
        "forecast_days": DIAS_DE_PREVISAO,
        "timezone": "America/Sao_Paulo",
    }
    resposta = requests.get(PREVISAO, params=parametros, timeout=60)
    resposta.raise_for_status()
    return resposta.json()["daily"]


def resumir(diario: dict) -> dict:
    """Agrega a resposta diaria da API nos numeros que o painel exibe.

    A API pode devolver null em dias na ponta do horizonte; esses dias saem
    das somas, das contagens e da media em vez de virarem zero -- zero seria
    afirmar tempo seco onde so ha ausencia de previsao. Sem nenhuma
    temperatura valida, `temp_media_14d` sai como None (null no JSON).
    """
    chuva = list(diario.get("precipitation_sum") or [])[:DIAS_DE_PREVISAO]
    temperatura = list(diario.get("temperature_2m_mean") or [])[:DIAS_DE_PREVISAO]

    chuva_7d = [v for v in chuva[:7] if v is not None]
    chuva_14d = [v for v in chuva if v is not None]
    temperaturas = [v for v in temperatura if v is not None]

    return {
        "chuva_7d_mm": round(sum(chuva_7d), 1),
        "chuva_14d_mm": round(sum(chuva_14d), 1),
        "dias_chuva_14d": sum(1 for v in chuva_14d if v >= LIMIAR_DIA_COM_CHUVA_MM),
        "temp_media_14d": (
            round(sum(temperaturas) / len(temperaturas), 1) if temperaturas else None
        ),
    }


def coletar(pausa: float = 1.0) -> dict:
    """Coleta a previsao de 14 dias de todo o territorio.

    Uma requisicao por municipio, com pausa curta entre elas para respeitar a
    cota da API gratuita -- 14 dias de duas variaveis e um pedido leve, sem
    comparacao com as series historicas de `clima_chuva.py`. Municipio que
    falhar (rede, cota, malha sem o codigo) nao derruba a coleta: entra em
    "faltantes" e o painel mostra os que responderam.

    Retorna o payload completo do JSON:
    {"coletado_para_semana", "fonte", "municipios", "faltantes"}.
    """
    pontos = centroides(sorted(TERRITORIO))

    municipios: list[dict] = []
    faltantes: list[dict] = []
    for indice, codigo in enumerate(sorted(TERRITORIO), start=1):
        nome = TERRITORIO[codigo]
        ponto = pontos.get(codigo)
        if ponto is None:
            faltantes.append({"cod_ibge": codigo, "municipio": nome})
            print(f"[{indice:2d}/{len(TERRITORIO)}] {nome:28s} sem centroide na malha")
            continue

        try:
            resumo = resumir(_baixar_previsao(*ponto))
        except Exception as erro:
            # Previsao e contexto: quem nao responder fica registrado e a
            # coleta segue para o proximo municipio.
            faltantes.append({"cod_ibge": codigo, "municipio": nome})
            print(f"[{indice:2d}/{len(TERRITORIO)}] {nome:28s} falhou: {erro}")
        else:
            municipios.append({"cod_ibge": codigo, "municipio": nome, **resumo})
            print(
                f"[{indice:2d}/{len(TERRITORIO)}] {nome:28s} "
                f"chuva 14d {resumo['chuva_14d_mm']:6.1f} mm"
            )
        time.sleep(pausa)

    return {
        "coletado_para_semana": _se_codigo(date.today()),
        "fonte": FONTE,
        "municipios": municipios,
        "faltantes": faltantes,
    }


def salvar(caminho: Path | None = None, pausa: float = 1.0) -> dict:
    """Coleta e grava o JSON que o painel le. Retorna o payload gravado."""
    if caminho is None:
        caminho = ARQUIVO_PADRAO
    payload = coletar(pausa=pausa)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload
