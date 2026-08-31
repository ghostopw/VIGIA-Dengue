"""Ciclo do alerta ao vivo: busca a fonte, reconstroi, avalia e avisa.

Uso:  python src/vigia/executar_atualizacao.py
      python src/vigia/executar_atualizacao.py --sem-busca   (so reavalia)
      python src/vigia/executar_atualizacao.py --limiar 0.6

Para agendar uma vez por dia no Windows (a fonte publica uma vez por semana,
em dia que varia):

  schtasks /create /tn "VIGIA-Dengue" /tr ^
    "python L:\\Dengue\\src\\vigia\\executar_atualizacao.py" /sc daily /st 08:00
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vigia.atualizar import atualizar  # noqa: E402
from vigia.notificar import emitir  # noqa: E402


def principal() -> int:
    analisador = argparse.ArgumentParser(description="Ciclo do alerta VIGIA-Dengue.")
    analisador.add_argument("--limiar", type=float, default=0.50,
                            help="probabilidade a partir da qual Brasilia entra em alerta")
    analisador.add_argument("--sem-busca", action="store_true",
                            help="nao consulta o InfoDengue; so reavalia o que ja existe")
    argumentos = analisador.parse_args()

    resultado = atualizar(limiar=argumentos.limiar, buscar=not argumentos.sem_busca)
    entregues = emitir(resultado)

    print()
    estado = resultado["estado"]
    rotulo = f"{estado['semana'] % 100:02d}/{estado['semana'] // 100}"
    print(f"semana no painel: SE {rotulo}", end="")
    print(" (nova)" if resultado["semana_nova"] else " (a mesma de antes)")

    if resultado["primeira_vez"]:
        print("primeira execucao: estado registrado, nada avisado.")
    elif resultado["eventos"]:
        print()
        print(resultado["mensagem"])
        print()
        canais = ", ".join(nome for nome, ok in entregues.items() if ok) or "nenhum"
        print(f"avisado por: {canais}")
    else:
        print("nada mudou; ninguem foi avisado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
