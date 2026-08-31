"""Rede neural contra LightGBM, na mesma particao e com a mesma informacao.

POR QUE ISTO PRECISA EXISTIR
----------------------------
O LightGBM do projeto marca AUC 0,818, e a rede marcou 0,777 no Centro-Oeste.
Comparar os dois numeros seria erro grosseiro: sao territorios diferentes -- 34
municipios da RIDE contra 467 do Centro-Oeste -- e conjuntos de teste
diferentes. Um territorio com centenas de municipios pequenos e mais dificil de
prever que um com trinta e quatro, entao o numero menor pode significar
problema mais dificil, e nao modelo pior.

Aqui os dois correm no MESMO dado, na MESMA particao temporal e com a MESMA
informacao disponivel, que e a unica forma de a comparacao dizer algo.

DUAS COMPARACOES, PORQUE SAO DUAS PERGUNTAS
-------------------------------------------
1. Arquitetura: LightGBM recebe a janela achatada -- as mesmas 16 semanas x 6
   canais, mais os estaticos, so que como 102 colunas planas. Aqui a unica
   diferenca entre os dois e saber ou nao que aquelas colunas formam uma
   sequencia. Responde se a estrutura temporal vale alguma coisa.

2. Abordagem: LightGBM recebe as variaveis escritas a mao do projeto --
   incidencia_mm3, canal_q3, chuva_acum12 e as demais. Responde se a rede,
   aprendendo a defasagem sozinha, supera a defasagem que nos escolhemos.

Se a rede perder nas duas, o resultado e esse, e fica registrado. Trocar um
modelo que funciona por outro mais sofisticado que erra mais nao e avanco.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from .modelagem import VARIAVEIS, modelo_aprendizado
from .rede_neural import HORIZONTE, JANELA

RAIZ = Path(__file__).resolve().parents[2]
RELATORIO = RAIZ / "saidas" / "comparacao_modelos.csv"


def _metricas(nome: str, ano: int, verdadeiro: np.ndarray,
              probabilidade: np.ndarray, n_treino: int) -> dict:
    return {
        "modelo": nome,
        "ano": ano,
        "n_treino": int(n_treino),
        "n_teste": int(len(verdadeiro)),
        "auc": round(float(roc_auc_score(verdadeiro, probabilidade)), 4),
        "auprc": round(float(average_precision_score(verdadeiro, probabilidade)), 4),
        "brier": round(float(brier_score_loss(verdadeiro, probabilidade)), 4),
    }


def lightgbm_na_janela(janelas: dict, ano: int) -> dict:
    """LightGBM com a janela achatada: mesma informacao, sem a estrutura."""
    treino = janelas["ano"] < ano
    teste = janelas["ano"] == ano
    if treino.sum() == 0 or teste.sum() == 0:
        return {}

    def achatar(mascara):
        serie = janelas["serie"][mascara]
        return np.hstack([serie.reshape(len(serie), -1), janelas["fixo"][mascara]])

    modelo = modelo_aprendizado().fit(achatar(treino), janelas["alvo"][treino])
    probabilidade = modelo.predict_proba(achatar(teste))[:, 1]
    return _metricas("lightgbm_janela", ano, janelas["alvo"][teste],
                     probabilidade, treino.sum())


def lightgbm_variaveis(dados: pd.DataFrame, ano: int) -> dict:
    """LightGBM com as variaveis escritas a mao -- a abordagem atual do projeto."""
    disponiveis = [v for v in VARIAVEIS if v in dados.columns]
    tabela = dados.dropna(subset=disponiveis + ["alvo"])

    treino = tabela[tabela["ano"] < ano]
    teste = tabela[tabela["ano"] == ano]
    if treino.empty or teste.empty or treino["alvo"].nunique() < 2:
        return {}

    modelo = modelo_aprendizado().fit(treino[disponiveis], treino["alvo"])
    probabilidade = modelo.predict_proba(teste[disponiveis])[:, 1]
    return _metricas("lightgbm_variaveis", ano, teste["alvo"].to_numpy(),
                     probabilidade, len(treino))


def comparar(dados: pd.DataFrame, janelas: dict, anos: list[int],
             destino: Path = RELATORIO) -> pd.DataFrame:
    """Roda as tres abordagens ano a ano e devolve a tabela de desempenho."""
    from .rede_neural import treinar_ano

    linhas = []
    for ano in anos:
        print(f"\n=== {ano} ===")

        rede = treinar_ano(janelas, ano)
        if rede:
            linhas.append({
                "modelo": "rede_neural", "ano": ano,
                "n_treino": rede["n_treino"], "n_teste": rede["n_teste"],
                "auc": round(rede["auc"], 4), "auprc": round(rede["auprc"], 4),
                "brier": round(rede["brier"], 4),
            })
            print(f"  rede_neural        AUC {rede['auc']:.3f} | "
                  f"AUPRC {rede['auprc']:.3f} | Brier {rede['brier']:.3f}")

        for funcao, argumento in ((lightgbm_na_janela, janelas),
                                  (lightgbm_variaveis, dados)):
            resultado = funcao(argumento, ano)
            if resultado:
                linhas.append(resultado)
                print(f"  {resultado['modelo']:18} AUC {resultado['auc']:.3f} | "
                      f"AUPRC {resultado['auprc']:.3f} | Brier {resultado['brier']:.3f}")

    tabela = pd.DataFrame(linhas)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(destino, index=False)
    return tabela
