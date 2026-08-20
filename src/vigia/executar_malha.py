"""Baixa a malha cartografica do territorio piloto."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.malha import baixar_malha  # noqa: E402

if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[2]
    colecao = baixar_malha(raiz / "dados" / "externo" / "malha_ride_df.geojson")
    print(f"\nfeicoes: {len(colecao['features'])}")
