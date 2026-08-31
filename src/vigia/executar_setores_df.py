"""Monta a camada de setores censitarios do DF com drenagem e saneamento."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.setores_df import coletar  # noqa: E402

if __name__ == "__main__":
    setores = coletar()
    print()
    piores = setores.nlargest(10, "indice_criadouro")[
        ["CD_SETOR", "NM_SUBDIST", "sem_bueiro_pct", "sem_pavimento_pct",
         "esgoto_inadequado_pct", "indice_criadouro"]]
    print("os dez setores de pior condicao:")
    print(piores.to_string(index=False))
