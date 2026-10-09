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

# A lista preditora foi podada por medicao em 27/09/2026: oito experimentos
# no harness comum (validacao temporal identica a deste modulo), cada ganho
# verificado por dois ceticos independentes -- vazamento e reproducao. O
# registro completo esta em docs/achados_modelagem.md, secao 8. Resumo:
#
#  - Bloco climatico (12 colunas): remove-lo melhorou TODAS as medias
#    2019-2025 (AUC 0,8308 -> 0,8333; Brier 0,1715 -> 0,1648). O comentario
#    antigo deste arquivo estimava o efeito na base de 33 municipios; na de
#    34 a direcao se confirma com magnitude menor.
#  - Chuva (12 colunas): pagava ~0,006 de AUC sem o bloco de transmissao;
#    com Rt/p_rt1 e os hiperparametros novos, a versao com chuva perde para
#    a sem (AUC 0,8458 contra 0,8482). Saiu do treino.
#  - Vulnerabilidade (3 colunas): neutra (delta de AUC -0,0005).
#  - Entraram Rt, p_rt1, receptivo, transmissao e nivel_inc do InfoDengue,
#    mais as defasagens de Rt e p_rt1: 100% preenchidas e nowcast da propria
#    semana -- nenhuma informacao futura.
#
# As colunas climaticas, de chuva e de vulnerabilidade CONTINUAM na base:
# alimentam a leitura de receptividade do painel e o motor de alarmes. So
# nao entram mais no treino.
VARIAVEIS_ESSENCIAIS = [
    # O nucleo sem o qual uma previsao nao se sustenta: historico da dengue,
    # porte, sazonalidade, canal endemico e o estado corrente da transmissao.
    # Tudo vem do proprio payload do InfoDengue e esta sempre presente na
    # semana mais recente -- e o que o alerta ao vivo exige.
    "incidencia_100k", "incidencia_lag1", "incidencia_lag2", "incidencia_lag4",
    "incidencia_mm3", "incidencia_mm8",
    "casos_est_mm3", "casos_est_mm8", "razao_mm3_mm8", "variacao_semanal",
    "log_pop", "semana", "canal_mediana", "canal_q3",
    "Rt", "p_rt1",
]

VARIAVEIS = VARIAVEIS_ESSENCIAIS + [
    # Complementos de transmissao: indicadores categoricos do InfoDengue e a
    # trajetoria recente de Rt/p_rt1. As defasagens faltam nas duas primeiras
    # semanas de cada municipio; o LightGBM trata valor ausente nativamente.
    "receptivo", "transmissao", "nivel_inc",
    "Rt_lag1", "Rt_lag2", "p_rt1_lag1", "p_rt1_lag2",
]

# Pesos da combinacao boosting + persistencia usados no painel e no alerta.
# Medidos em 27/09/2026 numa varredura completa: 0,8/0,2 maximiza AUC (0,8515)
# e Brier (0,1557) sobre o boosting sozinho (0,8482/0,1577); o peso otimo da
# logistica na mistura foi zero. Em Brasilia, no limiar 0,80, a combinacao
# leva a especificidade a 0,747 -- acima do piso de 0,74 da literatura EWARS
# -- com sensibilidade 0,767 e VPP 0,902.
PESO_BOOSTING = 0.8
PESO_PERSISTENCIA = 0.2


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

    # Hiperparametros medidos em 27/09/2026 (busca em estagios, 15
    # configuracoes): para ~20 mil linhas de treino, menos capacidade ganha
    # em todos os eixos -- a config antiga (400 arvores, lr 0,05, 31 folhas)
    # ficou em 11o de 15. AUC 0,8308 -> 0,8415 so com esta mudanca.
    return LGBMClassifier(
        n_estimators=200,
        learning_rate=0.03,
        num_leaves=15,
        min_child_samples=20,
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
    horizonte: int = HORIZONTE_PADRAO,
) -> pd.DataFrame:
    """Treina em janela expansiva e avalia no ano seguinte."""
    variaveis = [v for v in VARIAVEIS if v in dados.columns]
    linhas: list[dict] = []

    # A data que cada linha de treino vai OBSERVAR, e nao a data em que ela
    # esta. Cortar por `ano < ano` deixa passar as ultimas semanas de dezembro,
    # cujo alvo cai dentro do ano de teste: no Centro-Oeste sao 1.860 linhas por
    # dobra treinando com o rotulo que deveriam prever.
    datas = pd.to_datetime(dados["data_ini_se"])
    data_alvo = datas.groupby(dados["cod_ibge"]).shift(-horizonte)

    for ano in anos_avaliacao:
        inicio_teste = pd.Timestamp(f"{ano}-01-01")
        treino = dados[(dados["ano"] < ano) & (data_alvo < inicio_teste)]
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
        prob_boosting = boosting.predict_proba(X_teste)[:, 1]
        linhas.append({
            "ano": ano, "modelo": "aprendizado",
            **_metricas(y_teste, prob_boosting, corte),
        })

        # Combinado: o boosting ponderado com o estado presente. A persistencia
        # e quase descorrelacionada dos modelos treinados, e a media com ela
        # dominou todas as alternativas na varredura de 27/09/2026.
        prob_combinada = (PESO_BOOSTING * prob_boosting
                          + PESO_PERSISTENCIA * teste["risco_atual_alto"].to_numpy())
        linhas.append({
            "ano": ano, "modelo": "combinado",
            **_metricas(y_teste, prob_combinada, corte),
        })

    return pd.DataFrame(linhas)
