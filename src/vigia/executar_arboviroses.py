"""Baixa as tres arboviroses do InfoDengue para todo o territorio piloto.

O InfoDengue serve dengue, chikungunya e zika pela mesma API. Chikungunya e
zika compartilham o mesmo vetor (Aedes aegypti) e as mesmas condicoes
climaticas, entao servem tanto para enriquecer a analise quanto para
verificar a consistencia do sinal epidemiologico.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from vigia.ingestao_infodengue import baixar_territorio  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
ANO_INICIO = 2014
ANO_FIM = 2026
DOENCAS = ["chikungunya", "zika"]

if __name__ == "__main__":
    processado = RAIZ / "dados" / "processado"
    processado.mkdir(parents=True, exist_ok=True)

    for doenca in DOENCAS:
        print(f"\n===== {doenca.upper()} =====")
        consolidado = baixar_territorio(
            ano_inicio=ANO_INICIO,
            ano_fim=ANO_FIM,
            destino=RAIZ / "dados" / "bruto" / "infodengue",
            doenca=doenca,
        )
        saida = processado / f"{doenca}_territorio.csv"
        consolidado.to_csv(saida, index=False, encoding="utf-8")
        print(f"{doenca}: {len(consolidado)} linhas -> {saida.name}")
        print(f"  casos no periodo: {consolidado['casos'].sum():,.0f}")
