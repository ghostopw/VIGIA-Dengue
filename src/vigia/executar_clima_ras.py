"""Coleta o clima semanal das Regioes Administrativas do DF (Open-Meteo / ERA5)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.clima_ras import coletar  # noqa: E402

if __name__ == "__main__":
    tabela = coletar()
    print()
    print(tabela["data_ini_se"].min(), "a", tabela["data_ini_se"].max())
