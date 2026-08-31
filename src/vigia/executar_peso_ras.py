"""Calcula o peso relativo de cada Regiao Administrativa do DF."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.peso_ras import diagnosticar, salvar  # noqa: E402

if __name__ == "__main__":
    tabela = salvar()
    print(f"linhas: {len(tabela)} | RAs: {tabela['ra_nome'].nunique()}")
    print()
    print("diagnostico -- leia antes de publicar o mapa:")
    for chave, valor in diagnosticar(tabela).items():
        print(f"  {chave}: {valor}")
