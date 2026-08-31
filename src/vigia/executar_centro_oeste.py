"""Baixa a serie do InfoDengue para os 468 municipios do Centro-Oeste (treino)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.territorio_centro_oeste import coletar  # noqa: E402

if __name__ == "__main__":
    base = coletar()
    print()
    print("por UF:")
    print(base.groupby("uf")["cod_ibge"].nunique().to_string())
