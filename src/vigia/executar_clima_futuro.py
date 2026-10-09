"""Coleta a previsao de 14 dias e grava saidas/clima_futuro.json.

Roda dentro do ciclo de atualizacao (onde ha rede); o painel apenas le o
JSON resultante. A previsao e contexto de painel, nunca preditora do modelo.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.clima_futuro import ARQUIVO_PADRAO, salvar  # noqa: E402

if __name__ == "__main__":
    payload = salvar()
    print()
    print("gravado:", ARQUIVO_PADRAO)
    print(
        "semana:", payload["coletado_para_semana"],
        "| municipios:", len(payload["municipios"]),
        "| faltantes:", len(payload["faltantes"]),
    )
    if payload["faltantes"]:
        print("faltantes:", ", ".join(m["municipio"] for m in payload["faltantes"]))
