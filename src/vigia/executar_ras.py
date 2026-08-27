"""Prepara a malha das Regioes Administrativas do DF para o painel."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.ras_df import DESTINO_GEOJSON, exportar_geojson, resumo  # noqa: E402

if __name__ == "__main__":
    colecao = exportar_geojson()
    print(f"malha das RAs: {len(colecao['features'])} feicoes -> {DESTINO_GEOJSON.name}")
    print()
    tabela = resumo()
    print(tabela.round(1).to_string(index=False))
    print()
    print("populacao total coberta:", f"{tabela['populacao'].sum():,.0f}".replace(",", "."))
