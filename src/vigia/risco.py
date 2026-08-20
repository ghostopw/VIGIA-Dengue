"""Estratificacao do risco epidemiologico em quatro niveis (Etapa 3).

O criterio combina duas leituras consagradas em vigilancia:

1. Canal endemico -- compara a incidencia observada na semana com a
   distribuicao historica daquela mesma semana epidemiologica no municipio.
   Responde: "esta semana esta acima do esperado para esta epoca do ano?"

2. Incidencia absoluta -- patamares por 100 mil habitantes usados na
   classificacao de risco de arboviroses do Ministerio da Saude.
   Responde: "o volume de casos ja e alto em termos populacionais?"

O nivel final e o maior dos dois, para que nem uma epidemia fora de epoca nem
um patamar alto sustentado passem despercebidos.

Os limiares historicos sao sempre calculados com anos ANTERIORES ao da linha
avaliada, para que a classificacao seja reproduzivel em tempo real e nao use
informacao do futuro.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

NIVEIS = ["baixo", "moderado", "alto", "muito alto"]

# Patamares de incidencia semanal por 100 mil habitantes.
LIMIARES_INCIDENCIA = [10.0, 30.0, 60.0]

# Minimo de anos historicos para que o canal endemico seja considerado valido.
MINIMO_ANOS_HISTORICO = 3


def canal_endemico(base: pd.DataFrame, coluna: str = "incidencia_100k") -> pd.DataFrame:
    """Calcula os quartis historicos de cada municipio-semana.

    Para cada linha, usa apenas os anos anteriores da mesma semana
    epidemiologica no mesmo municipio (janela expansiva), incluindo as duas
    semanas vizinhas para dar estabilidade em municipios pequenos.
    """
    dados = base.sort_values(["cod_ibge", "data_ini_se"]).copy()
    registros: list[pd.DataFrame] = []

    for codigo, municipio in dados.groupby("cod_ibge", sort=False):
        municipio = municipio.sort_values(["ano", "semana"]).copy()
        q1 = np.full(len(municipio), np.nan)
        q2 = np.full(len(municipio), np.nan)
        q3 = np.full(len(municipio), np.nan)
        anos_disponiveis = np.zeros(len(municipio), dtype=int)

        semanas = municipio["semana"].to_numpy()
        anos = municipio["ano"].to_numpy()
        valores = municipio[coluna].to_numpy(dtype=float)

        for i in range(len(municipio)):
            # Janela de +-2 semanas em torno da semana alvo, anos anteriores.
            distancia = np.abs(semanas - semanas[i])
            distancia = np.minimum(distancia, 53 - distancia)  # circularidade do ano
            historico = (anos < anos[i]) & (distancia <= 2)
            amostra = valores[historico]
            amostra = amostra[~np.isnan(amostra)]
            anos_disponiveis[i] = len(np.unique(anos[historico]))
            if len(amostra) >= 5:
                q1[i], q2[i], q3[i] = np.percentile(amostra, [25, 50, 75])

        municipio["canal_q1"] = q1
        municipio["canal_mediana"] = q2
        municipio["canal_q3"] = q3
        municipio["anos_historico"] = anos_disponiveis
        registros.append(municipio)

    return pd.concat(registros).sort_values(["cod_ibge", "data_ini_se"])


def _nivel_por_canal(linha: pd.Series) -> int:
    """Posicao da incidencia observada frente ao canal endemico (0 a 3)."""
    valor = linha["incidencia_100k"]
    if pd.isna(valor) or pd.isna(linha["canal_q3"]):
        return -1
    if linha["anos_historico"] < MINIMO_ANOS_HISTORICO:
        return -1
    if valor <= linha["canal_mediana"]:
        return 0
    if valor <= linha["canal_q3"]:
        return 1
    # Acima do quartil superior: zona epidemica. Distingue-se o quanto acima.
    limite_muito_alto = linha["canal_q3"] * 2 if linha["canal_q3"] > 0 else np.inf
    return 3 if valor > limite_muito_alto else 2


def _nivel_por_incidencia(valor: float) -> int:
    """Posicao da incidencia nos patamares absolutos (0 a 3)."""
    if pd.isna(valor):
        return -1
    return int(np.searchsorted(LIMIARES_INCIDENCIA, valor, side="right"))


def classificar(base: pd.DataFrame) -> pd.DataFrame:
    """Adiciona o nivel de risco de cada municipio-semana."""
    dados = canal_endemico(base)

    nivel_canal = dados.apply(_nivel_por_canal, axis=1)
    nivel_absoluto = dados["incidencia_100k"].apply(_nivel_por_incidencia)

    dados["nivel_canal"] = nivel_canal
    dados["nivel_absoluto"] = nivel_absoluto

    # O nivel final e o maior entre os dois criterios disponiveis.
    combinado = np.maximum(nivel_canal, nivel_absoluto)
    dados["risco_codigo"] = combinado.clip(lower=0)
    dados["risco"] = pd.Categorical(
        [NIVEIS[int(c)] for c in dados["risco_codigo"]],
        categories=NIVEIS,
        ordered=True,
    )
    # Sem historico suficiente, o criterio do canal nao entra na classificacao.
    dados["risco_sem_canal"] = (nivel_canal < 0).astype("int8")

    return dados
