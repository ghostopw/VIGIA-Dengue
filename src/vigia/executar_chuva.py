"""Coleta a precipitacao semanal do territorio (Open-Meteo / ERA5)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.clima_chuva import coletar  # noqa: E402

if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[2]
    tabela = coletar(destino=raiz / "dados" / "externo" / "chuva_semanal.csv")
    print()
    print("linhas:", len(tabela), "| municipios:", tabela["cod_ibge"].nunique())
    print(tabela["data_ini_se"].min(), "a", tabela["data_ini_se"].max())
