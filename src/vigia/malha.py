"""Download da malha cartografica municipal do territorio piloto.

Usa a API de malhas do IBGE, que entrega o poligono de cada municipio em
GeoJSON. O arquivo resultante alimenta o mapa coropletico do painel.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from .territorio import TERRITORIO

MALHA_MUNICIPIO = "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{codigo}"


def baixar_malha(destino: Path, qualidade: str = "intermediaria") -> dict:
    """Monta um FeatureCollection com os poligonos do territorio."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    feicoes = []

    for indice, (codigo, nome) in enumerate(sorted(TERRITORIO.items()), start=1):
        resposta = requests.get(
            MALHA_MUNICIPIO.format(codigo=codigo),
            params={"formato": "application/vnd.geo+json", "qualidade": qualidade},
            timeout=120,
        )
        resposta.raise_for_status()
        geojson = resposta.json()
        for feicao in geojson.get("features", []):
            feicao["properties"] = {"cod_ibge": codigo, "municipio": nome}
            feicao["id"] = str(codigo)
            feicoes.append(feicao)
        print(f"[{indice:2d}/{len(TERRITORIO)}] {nome}")
        time.sleep(0.5)

    colecao = {"type": "FeatureCollection", "features": feicoes}
    destino.write_text(json.dumps(colecao), encoding="utf-8")
    return colecao
