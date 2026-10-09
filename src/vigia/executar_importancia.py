"""Mede a importancia das variaveis e grava saidas/importancia_variaveis.csv.

O CSV original foi gerado por um script que nao ficou no repositorio, e seus
numeros fossilizaram na era dos 30 municipios. Este executor e o gerador
definitivo: treina os dois modelos na serie corrente (com o mesmo corte
temporal do alvo usado na validacao) e grava, por variavel:

  ganho  -- ganho total da variavel nas arvores do LightGBM
  coef   -- coeficiente padronizado da regressao logistica
  peso   -- ganho como porcentagem do total (soma 100)

Uso descritivo: diz o que o modelo aprendeu na serie inteira. O desempenho,
esse continua sendo medido so pela validacao temporal.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from vigia.base_analitica import ler_base  # noqa: E402
from vigia.modelagem import (  # noqa: E402
    VARIAVEIS,
    modelo_aprendizado,
    modelo_interpretavel,
    preparar,
)

if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[2]
    base = ler_base(raiz / "dados" / "processado" / "base_com_risco.csv")
    dados = preparar(base)
    presentes = [v for v in VARIAVEIS if v in dados.columns]

    X, y = dados[presentes], dados["alvo"].to_numpy()

    boosting = modelo_aprendizado().fit(X, y)
    ganho = pd.Series(
        boosting.booster_.feature_importance(importance_type="gain"),
        index=presentes)

    logistica = modelo_interpretavel().fit(X, y)
    coef = pd.Series(logistica.named_steps["logistica"].coef_[0],
                     index=presentes)

    tabela = pd.DataFrame({
        "variavel": presentes,
        "ganho": ganho.values,
        "coef": coef.values,
        "peso": (100 * ganho / ganho.sum()).values,
    }).sort_values("ganho", ascending=False)

    destino = raiz / "saidas" / "importancia_variaveis.csv"
    tabela.to_csv(destino, index=False, lineterminator="\n")
    print("gravado:", destino)
    print(f"\ntreino: {len(dados):,} linhas, {len(presentes)} variaveis")
    print("\ntop 10 por ganho:")
    print(tabela.head(10)[["variavel", "peso"]].round(2)
          .to_string(index=False))
