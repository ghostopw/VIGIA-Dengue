"""Regenera o dicionario de dados a partir da base analitica corrente.

Rodar sempre que a base ganhar ou perder coluna. O teste
testes/test_dicionario.py falha quando os artefatos ficam para tras.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from vigia.dicionario import SAIDA_CSV, SAIDA_MD, salvar, sem_descricao  # noqa: E402

if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[2]
    base = pd.read_csv(raiz / "dados" / "processado" / "base_com_risco.csv",
                       low_memory=False)
    tabela = salvar(base)
    print("gravado:", SAIDA_MD)
    print("gravado:", SAIDA_CSV)
    print(tabela.groupby("papel").size().to_string())
    faltando = sem_descricao(tabela)
    if faltando:
        print("\nATENCAO - colunas sem descricao (acrescente em "
              "src/vigia/dicionario.py):", ", ".join(faltando))
        sys.exit(1)
