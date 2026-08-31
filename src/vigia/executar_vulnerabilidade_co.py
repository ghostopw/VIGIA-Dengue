"""Vulnerabilidade socioambiental dos 468 municipios do Centro-Oeste (treino)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.territorio_centro_oeste import municipios  # noqa: E402
from vigia.vulnerabilidade import coletar  # noqa: E402

if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[2]
    lista = municipios()
    catalogo = dict(zip(lista["cod_ibge"], lista["municipio"]))
    print(f"coletando vulnerabilidade de {len(catalogo)} municipios...")

    tabela = coletar(
        destino=raiz / "dados" / "externo" / "vulnerabilidade_centro_oeste.csv",
        municipios=catalogo,
    )
    print()
    print(f"{len(tabela)} municipios")
    for coluna in ("esgoto_inadequado_pct", "sem_agua_rede_pct", "lixo_sem_coleta_pct"):
        if coluna in tabela:
            faltando = tabela[coluna].isna().sum()
            print(f"  {coluna:24} sem valor em {faltando} municipios "
                  f"| mediana {tabela[coluna].median():.1f}%")
