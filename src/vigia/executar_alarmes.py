"""Gera o artefato de alarmes do painel (saidas/alarmes.json)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.alarmes import salvar  # noqa: E402
from vigia.base_analitica import ler_base  # noqa: E402

if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[2]
    base = ler_base(raiz / "dados" / "processado" / "base_com_risco.csv")
    payload = salvar(base, raiz / "saidas" / "alarmes.json")
    print("semana de referencia:", payload["gerado_da_semana"])
    print("alarmes ligados:", len(payload["alarmes"]))
    for alarme in payload["alarmes"]:
        print(
            f"  [{alarme['id']}] {alarme['municipio']} (SE {alarme['semana']}): "
            f"gatilho {alarme['valor_gatilho']}, lift historico "
            f"{alarme['lift_historico']}, olhar {alarme['lag_semanas']} semanas a frente"
        )
