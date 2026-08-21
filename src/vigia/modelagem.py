"""Modelos de alerta precoce com validacao temporal (Etapa 4).

Desfecho: ocorrencia de risco alto ou muito alto no municipio no horizonte de
h semanas a frente (padrao h = 4). O alvo e construido por deslocamento
negativo dentro de cada municipio, e as linhas sem alvo observavel no fim da
serie sao descartadas do treino e da avaliacao.

Tres estrategias sao comparadas, como previsto no projeto:

  - referencia   -- persistencia: repete o estado de risco da semana atual;
  - interpretavel-- regressao logistica sobre variaveis epidemiologicas e
                    climaticas padronizadas, com coeficientes legiveis;
  - aprendizado  -- gradient boosting (LightGBM), que captura interacoes e
                    nao linearidades.

A validacao e temporal em janela expansiva: treina-se com tudo ate um ano e
avalia-se no ano seguinte, nunca o contrario.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

HORIZONTE_PADRAO = 4

VARIAVEIS = [
    # Epidemiologicas -- o proprio historico de dengue. Concentram 59,6% do
    # ganho do modelo; a incidencia da semana corrente sozinha responde por 33,7%.
    "incidencia_100k", "incidencia_lag1", "incidencia_lag2", "incidencia_lag4",
    "incidencia_mm3", "incidencia_mm8",
    "casos_est_mm3", "casos_est_mm8", "razao_mm3_mm8", "variacao_semanal",
    # Climaticas -- condicao ambiental para o vetor, com defasagem compativel
    # com o ciclo do Aedes aegypti (2 a 8 semanas entre a condicao e o caso).
    "tempmed", "tempmed_lag2", "tempmed_lag4", "tempmed_lag8",
    "tempmin_lag4", "tempmax_lag4",
    "umidmed", "umidmed_lag2", "umidmed_lag4",
    "tempmed_anomalia", "umidmed_anomalia", "semanas_favoraveis_8",
    # Contextuais e historicas.
    "log_pop", "semana", "canal_mediana", "canal_q3",
]

# Nota metodologica sobre o bloco climatico.
#
# Medido no territorio da RIDE-DF, o clima praticamente nao agrega poder
# preditivo: sozinho alcanca AUC de 0,586 (o acaso e 0,50) e sua remocao nao
# piora o modelo completo (0,829 com clima contra 0,838 sem, media de sete anos
# de validacao temporal).
#
# Isso nao contradiz a literatura, que estabelece o clima como determinante da
# dengue. A razao e o recorte espacial: os 33 municipios ficam no mesmo bioma e
# na mesma faixa de altitude, e a temperatura varia apenas 0,68 grau entre eles
# na mesma semana. O clima explica QUANDO a dengue sobe -- a sazonalidade, que a
# variavel `semana` ja captura --, mas nao explica ONDE, que e o que a
# estratificacao espacial precisa distinguir. A correlacao com a incidencia
# futura confirma: 0,21 para a temperatura defasada contra 0,72 para a propria
# incidencia atual.
#
# O bloco foi mantido por tres motivos: consta do projeto aprovado (item 4.4),
# nao prejudica o desempenho, e sustenta a leitura de receptividade ambiental no
# painel. Em um territorio climaticamente heterogeneo -- um estado inteiro, por
# exemplo -- a conclusao provavelmente seria outra.


def preparar(base: pd.DataFrame, horizonte: int = HORIZONTE_PADRAO) -> pd.DataFrame:
    """Cria o alvo futuro e remove linhas sem alvo ou sem preditores."""
    dados = base.sort_values(["cod_ibge", "data_ini_se"]).copy()

    # Alerta: havera risco alto ou muito alto daqui a `horizonte` semanas.
    risco_alto = (dados["risco_codigo"] >= 2).astype(float)
    dados["alvo"] = risco_alto.groupby(dados["cod_ibge"]).shift(-horizonte)

    # Estado presente, usado pelo modelo de referencia.
    dados["risco_atual_alto"] = risco_alto

    dados = dados[dados["alvo"].notna()].copy()
    dados["alvo"] = dados["alvo"].astype(int)

    disponiveis = [v for v in VARIAVEIS if v in dados.columns]
    return dados.dropna(subset=disponiveis).reset_index(drop=True)


def _metricas(y_verdadeiro: np.ndarray, probabilidade: np.ndarray, corte: float) -> dict:
    """Metricas epidemiologicas de desempenho do alerta."""
    predito = (probabilidade >= corte).astype(int)
    matriz = confusion_matrix(y_verdadeiro, predito, labels=[0, 1])
    vn, fp, fn, vp = matriz.ravel()

    sensibilidade = vp / (vp + fn) if (vp + fn) else np.nan
    especificidade = vn / (vn + fp) if (vn + fp) else np.nan
    vpp = vp / (vp + fp) if (vp + fp) else np.nan
    vpn = vn / (vn + fn) if (vn + fn) else np.nan

    resultado = {
        "sensibilidade": sensibilidade,
        "especificidade": especificidade,
        "vpp": vpp,
        "vpn": vpn,
        "acuracia": (vp + vn) / matriz.sum(),
        "n": int(matriz.sum()),
        "prevalencia": float(np.mean(y_verdadeiro)),
    }
    # AUC e calibracao exigem as duas classes presentes no periodo avaliado.
    if len(np.unique(y_verdadeiro)) > 1:
        resultado["auc"] = roc_auc_score(y_verdadeiro, probabilidade)
        resultado["auprc"] = average_precision_score(y_verdadeiro, probabilidade)
        resultado["brier"] = brier_score_loss(y_verdadeiro, probabilidade)
    else:
        resultado.update({"auc": np.nan, "auprc": np.nan, "brier": np.nan})
    return resultado


def modelo_interpretavel() -> Pipeline:
    """Regressao logistica padronizada, com coeficientes interpretaveis."""
    return Pipeline([
        ("escala", StandardScaler()),
        ("logistica", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])


def modelo_aprendizado():
    """Gradient boosting para capturar nao linearidades e interacoes."""
    from lightgbm import LGBMClassifier

    return LGBMClassifier(
        n_estimators=400,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=40,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight="balanced",
        verbose=-1,
        random_state=42,
    )


def validacao_temporal(
    dados: pd.DataFrame,
    anos_avaliacao: list[int],
    corte: float = 0.5,
) -> pd.DataFrame:
    """Treina em janela expansiva e avalia no ano seguinte."""
    variaveis = [v for v in VARIAVEIS if v in dados.columns]
    linhas: list[dict] = []

    for ano in anos_avaliacao:
        treino = dados[dados["ano"] < ano]
        teste = dados[dados["ano"] == ano]
        if treino.empty or teste.empty or treino["alvo"].nunique() < 2:
            continue

        X_treino, y_treino = treino[variaveis], treino["alvo"].to_numpy()
        X_teste, y_teste = teste[variaveis], teste["alvo"].to_numpy()

        # Referencia: probabilidade e o proprio estado de risco atual.
        linhas.append({
            "ano": ano, "modelo": "referencia",
            **_metricas(y_teste, teste["risco_atual_alto"].to_numpy(), 0.5),
        })

        logistica = modelo_interpretavel().fit(X_treino, y_treino)
        linhas.append({
            "ano": ano, "modelo": "interpretavel",
            **_metricas(y_teste, logistica.predict_proba(X_teste)[:, 1], corte),
        })

        boosting = modelo_aprendizado().fit(X_treino, y_treino)
        linhas.append({
            "ano": ano, "modelo": "aprendizado",
            **_metricas(y_teste, boosting.predict_proba(X_teste)[:, 1], corte),
        })

    return pd.DataFrame(linhas)
