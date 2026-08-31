"""Coleta a vulnerabilidade socioambiental por Regiao Administrativa (Censo 2022)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.vulnerabilidade_ras import coletar  # noqa: E402

if __name__ == "__main__":
    tabela = coletar()
    print()
    print(tabela.head(8).to_string(index=False))
