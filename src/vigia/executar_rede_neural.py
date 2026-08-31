"""Treina a rede neural no Centro-Oeste e compara com o LightGBM."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from vigia.rede_neural import BASE, RELATORIO, montar_janelas, preparar, treinar_ano  # noqa: E402

ANOS = [2020, 2021, 2022, 2023, 2024, 2025]

if __name__ == "__main__":
    if not BASE.exists():
        raise SystemExit("base_centro_oeste.csv ausente; rode executar_base_centro_oeste.py")

    print("lendo a base do Centro-Oeste...")
    base = pd.read_csv(BASE)
    dados = preparar(base)
    print(f"  {len(dados):,} linhas | {dados.cod_ibge.nunique()} municipios".replace(",", "."))

    print("montando as janelas...")
    janelas = montar_janelas(dados)
    print(f"  {len(janelas['alvo']):,} janelas de {janelas['serie'].shape[1]} semanas "
          f"x {janelas['serie'].shape[2]} canais".replace(",", "."))
    print(f"  positivas: {janelas['alvo'].mean():.1%}")

    linhas = []
    for ano in ANOS:
        print(f"\n=== {ano} ===")
        r = treinar_ano(janelas, ano)
        if not r:
            print("  sem dado suficiente"); continue
        print(f"  treino {r['n_treino']:,} | teste {r['n_teste']:,}".replace(",", "."))
        print(f"  AUC {r['auc']:.3f} | AUPRC {r['auprc']:.3f} | Brier {r['brier']:.3f}")
        linhas.append({k: r[k] for k in ("ano", "n_treino", "n_teste", "auc", "auprc", "brier")})

    if linhas:
        tabela = pd.DataFrame(linhas)
        RELATORIO.parent.mkdir(parents=True, exist_ok=True)
        tabela.to_csv(RELATORIO, index=False)
        print(f"\nmedia: AUC {tabela.auc.mean():.3f} | AUPRC {tabela.auprc.mean():.3f} "
              f"| Brier {tabela.brier.mean():.3f}")
        print(f"gravado em {RELATORIO}")
