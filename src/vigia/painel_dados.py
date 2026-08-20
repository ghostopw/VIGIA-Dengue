"""Preparo do artefato que alimenta o painel VIGIA-Dengue.

Treina o modelo escolhido com todo o historico disponivel ate a ultima semana
observada e gera, para cada municipio-semana, a probabilidade de alerta no
horizonte definido, junto das variaveis que mais pesaram naquela previsao.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .modelagem import VARIAVEIS, modelo_aprendizado, preparar

COLUNAS_PAINEL = [
    "cod_ibge", "municipio", "uf", "ano", "semana", "se_codigo", "data_ini_se",
    "casos", "casos_est", "casos_est_min", "casos_est_max", "pop",
    "incidencia_100k", "incidencia_mm3", "incidencia_mm8",
    "casos_est_mm3", "razao_mm3_mm8", "variacao_semanal",
    "tempmed", "umidmed", "tempmed_anomalia", "semanas_favoraveis_8",
    "canal_mediana", "canal_q3", "risco", "risco_codigo", "nivel_canal",
    "nivel_absoluto", "completude", "dado_provisorio", "incerteza_nowcast",
    "clima_imputado", "porte_populacional", "Rt",
]


def _contribuicoes(modelo, X: pd.DataFrame, variaveis: list[str], top: int = 3) -> list[str]:
    """Descreve as variaveis que mais elevaram a probabilidade de cada linha.

    Usa a decomposicao por preditor do LightGBM (`pred_contrib`), que devolve o
    quanto cada variavel somou ou subtraiu do log-odds daquela previsao.
    """
    contribuicoes = modelo.predict_proba(X, pred_contrib=True)
    # A ultima coluna e o termo base; as demais seguem a ordem das variaveis.
    matriz = contribuicoes[:, :-1]
    explicacoes: list[str] = []

    for linha in matriz:
        ordem = np.argsort(linha)[::-1][:top]
        termos = [variaveis[i] for i in ordem if linha[i] > 0]
        explicacoes.append(", ".join(termos) if termos else "sem fator dominante")

    return explicacoes


def gerar(base_com_risco: pd.DataFrame, horizonte: int = 4) -> pd.DataFrame:
    """Produz a tabela final do painel, com previsao e explicacao do alerta.

    O treino exige alvo observado, mas a exibicao nao: as semanas mais recentes
    -- justamente as que interessam ao alerta precoce -- ainda nao tem desfecho
    conhecido e mesmo assim precisam aparecer no painel com sua previsao. Por
    isso o modelo e treinado no subconjunto com alvo e aplicado a toda a base.
    """
    treino = preparar(base_com_risco, horizonte=horizonte)
    variaveis = [v for v in VARIAVEIS if v in treino.columns]

    modelo = modelo_aprendizado().fit(treino[variaveis], treino["alvo"])

    # Previsao para todas as linhas com preditores completos, inclusive as
    # semanas recentes cujo desfecho ainda nao pode ser observado.
    dados = base_com_risco.sort_values(["cod_ibge", "data_ini_se"]).copy()
    risco_alto = (dados["risco_codigo"] >= 2).astype(float)
    dados["alvo"] = risco_alto.groupby(dados["cod_ibge"]).shift(-horizonte)
    dados = dados.dropna(subset=variaveis).reset_index(drop=True)

    dados["probabilidade_alerta"] = modelo.predict_proba(dados[variaveis])[:, 1]
    dados["fatores_alerta"] = _contribuicoes(modelo, dados[variaveis], variaveis)
    dados["horizonte_semanas"] = horizonte
    # Marca as linhas cujo desfecho ainda nao ocorreu: servem para operar o
    # alerta, mas nao podem entrar em nenhuma avaliacao de desempenho.
    dados["alvo_observado"] = dados["alvo"].notna().astype("int8")

    colunas = [c for c in COLUNAS_PAINEL if c in dados.columns]
    colunas += [
        "probabilidade_alerta", "fatores_alerta", "horizonte_semanas",
        "alvo", "alvo_observado",
    ]
    return dados[colunas]


def salvar(base_com_risco: pd.DataFrame, destino: Path, horizonte: int = 4) -> pd.DataFrame:
    painel = gerar(base_com_risco, horizonte)
    destino.parent.mkdir(parents=True, exist_ok=True)
    painel.to_csv(destino, index=False, encoding="utf-8")
    return painel
