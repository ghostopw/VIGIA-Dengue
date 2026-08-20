"""Script de execucao da Etapa 2: baixa a base bruta do territorio piloto."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.ingestao_infodengue import baixar_territorio  # noqa: E402

ANO_INICIO = 2014
ANO_FIM = 2026
RAIZ = Path(__file__).resolve().parents[2]

if __name__ == "__main__":
    consolidado = baixar_territorio(
        ano_inicio=ANO_INICIO,
        ano_fim=ANO_FIM,
        destino=RAIZ / "dados" / "bruto" / "infodengue",
    )
    saida = RAIZ / "dados" / "processado" / "infodengue_territorio.csv"
    saida.parent.mkdir(parents=True, exist_ok=True)
    consolidado.to_csv(saida, index=False, encoding="utf-8")
    print()
    print(f"CONSOLIDADO: {len(consolidado)} linhas, "
          f"{consolidado['cod_ibge'].nunique()} municipios")
    print(f"periodo: {consolidado['se_codigo'].min()} a {consolidado['se_codigo'].max()}")
    print(f"salvo em: {saida}")
