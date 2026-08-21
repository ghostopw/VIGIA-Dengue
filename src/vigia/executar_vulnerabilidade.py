"""Coleta os indicadores municipais de vulnerabilidade socioambiental."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.vulnerabilidade import coletar  # noqa: E402

if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[2]
    tabela = coletar(raiz / "dados" / "externo" / "vulnerabilidade.csv")
    print(tabela.to_string(index=False))
