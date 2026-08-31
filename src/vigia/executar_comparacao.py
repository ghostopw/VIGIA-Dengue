"""Compara a rede neural com o LightGBM na mesma particao temporal."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from vigia.comparar_modelos import RELATORIO, comparar  # noqa: E402
from vigia.rede_neural import BASE, montar_janelas, preparar  # noqa: E402

ANOS = [2021, 2022, 2023, 2024, 2025]

if __name__ == "__main__":
    print("lendo a base do Centro-Oeste...")
    dados = preparar(pd.read_csv(BASE))
    janelas = montar_janelas(dados)
    print(f"  {len(dados):,} linhas | {len(janelas['alvo']):,} janelas".replace(",", "."))

    tabela = comparar(dados, janelas, ANOS)

    print("\n" + "=" * 62)
    print("MEDIA DOS ANOS AVALIADOS")
    print("=" * 62)
    medias = tabela.groupby("modelo")[["auc", "auprc", "brier"]].mean().round(4)
    print(medias.sort_values("auc", ascending=False).to_string())
    melhor = medias.auc.idxmax()
    print(f"\nmelhor AUC media: {melhor}")
    print(f"gravado em {RELATORIO}")
