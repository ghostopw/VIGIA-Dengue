"""Gera o artefato de dados do painel."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from vigia.painel_dados import salvar  # noqa: E402

if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[2]
    base = pd.read_csv(raiz / "dados" / "processado" / "base_com_risco.csv")
    painel = salvar(base, raiz / "dados" / "processado" / "painel.csv", horizonte=4)
    print("linhas:", len(painel))
    print(painel[["municipio", "ano", "semana", "risco", "probabilidade_alerta",
                  "fatores_alerta"]].tail(4).to_string(index=False))
