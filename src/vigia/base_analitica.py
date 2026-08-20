"""Construcao da tabela analitica municipio-semana epidemiologica (Etapa 2).

Parte da serie bruta do InfoDengue e produz a tabela principal do projeto,
com incidencia, medias moveis, defasagens epidemiologicas e climaticas,
indicadores contextuais e flags de qualidade do dado.

Regra que atravessa todo o modulo: nenhuma variavel explicativa pode usar
informacao de semana futura. Todas as janelas moveis sao calculadas com
`closed="left"` ou deslocadas por `shift`, de modo que a linha da semana t
contenha apenas o que se sabia ate t.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFASAGENS_EPI = [1, 2, 3, 4, 8]
DEFASAGENS_CLIMA = [1, 2, 3, 4, 6, 8]
COLUNAS_CLIMA = ["tempmed", "tempmin", "tempmax", "umidmed", "umidmin", "umidmax"]

# Semanas recentes tem notificacao incompleta: a razao casos/casos_est abaixo
# deste limiar marca a linha como provisoria.
LIMIAR_COMPLETUDE = 0.90

# Teto para as razoes de crescimento quando a semana anterior teve zero casos:
# passar de nenhum caso para algum e crescimento, mas a divisao seria infinita.
TETO_CRESCIMENTO = 10.0


def interpolar_clima(painel: pd.DataFrame) -> pd.DataFrame:
    """Preenche falhas curtas das series climaticas dentro de cada municipio.

    Falhas de ate 3 semanas sao interpoladas linearmente; o que sobra recebe a
    mediana da mesma semana epidemiologica no municipio (padrao sazonal).
    """
    dados = painel.sort_values(["cod_ibge", "data_ini_se"]).copy()

    for coluna in COLUNAS_CLIMA:
        if coluna not in dados.columns:
            continue
        dados[f"{coluna}_imputado"] = dados[coluna].isna().astype("int8")
        dados[coluna] = dados.groupby("cod_ibge")[coluna].transform(
            lambda serie: serie.interpolate(limit=3, limit_direction="both")
        )
        sazonal = dados.groupby(["cod_ibge", "semana"])[coluna].transform("median")
        dados[coluna] = dados[coluna].fillna(sazonal)

    return dados


def adicionar_epidemiologicas(painel: pd.DataFrame) -> pd.DataFrame:
    """Incidencia, medias moveis e defasagens dos casos."""
    dados = painel.sort_values(["cod_ibge", "data_ini_se"]).copy()
    por_municipio = dados.groupby("cod_ibge", sort=False)

    # Incidencia por 100 mil habitantes a partir dos casos estimados, que
    # corrigem o atraso de notificacao; p_inc100k do InfoDengue usa casos brutos.
    dados["incidencia_100k"] = dados["casos_est"] / dados["pop"] * 1e5

    for lag in DEFASAGENS_EPI:
        dados[f"casos_est_lag{lag}"] = por_municipio["casos_est"].shift(lag)
        dados[f"incidencia_lag{lag}"] = por_municipio["incidencia_100k"].shift(lag)

    # Medias moveis calculadas ate a semana anterior (nao usam a semana corrente).
    for janela in (3, 4, 8):
        dados[f"casos_est_mm{janela}"] = por_municipio["casos_est"].transform(
            lambda serie, j=janela: serie.shift(1).rolling(j, min_periods=2).mean()
        )
        dados[f"incidencia_mm{janela}"] = por_municipio["incidencia_100k"].transform(
            lambda serie, j=janela: serie.shift(1).rolling(j, min_periods=2).mean()
        )

    # Razao de crescimento entre a media movel curta e a longa.
    #
    # As duas razoes abaixo dividem por um denominador que pode ser zero em
    # municipios pequenos e em semanas sem casos. Deixar NaN eliminaria essas
    # linhas da modelagem e do painel -- justamente os municipios calmos, que
    # precisam aparecer como risco baixo. A leitura correta e semantica:
    # sem casos antes e sem casos agora significa estabilidade, nao ausencia
    # de informacao. Ja passar de zero para algum caso e crescimento, tratado
    # como o teto da escala.
    razao = dados["casos_est_mm3"] / dados["casos_est_mm8"].replace(0, np.nan)
    sem_base_mm = (dados["casos_est_mm8"].fillna(0) == 0)
    razao = razao.mask(sem_base_mm & (dados["casos_est_mm3"].fillna(0) == 0), 1.0)
    dados["razao_mm3_mm8"] = razao.mask(
        sem_base_mm & (dados["casos_est_mm3"].fillna(0) > 0), TETO_CRESCIMENTO
    )

    # Variacao relativa semana contra semana anterior.
    anterior = por_municipio["casos_est"].shift(1)
    variacao = (dados["casos_est"] - anterior) / anterior.replace(0, np.nan)
    sem_base = anterior.fillna(0) == 0
    variacao = variacao.mask(sem_base & (dados["casos_est"].fillna(0) == 0), 0.0)
    dados["variacao_semanal"] = variacao.mask(
        sem_base & (dados["casos_est"].fillna(0) > 0), TETO_CRESCIMENTO
    )

    return dados


def adicionar_climaticas(painel: pd.DataFrame) -> pd.DataFrame:
    """Defasagens climaticas e anomalias sazonais."""
    dados = painel.sort_values(["cod_ibge", "data_ini_se"]).copy()
    por_municipio = dados.groupby("cod_ibge", sort=False)

    for coluna in ("tempmed", "tempmin", "tempmax", "umidmed"):
        for lag in DEFASAGENS_CLIMA:
            dados[f"{coluna}_lag{lag}"] = por_municipio[coluna].shift(lag)

    # Anomalia: desvio em relacao a media historica da mesma semana no municipio.
    for coluna in ("tempmed", "umidmed"):
        media_sazonal = dados.groupby(["cod_ibge", "semana"])[coluna].transform("mean")
        dados[f"{coluna}_anomalia"] = dados[coluna] - media_sazonal

    # Receptividade climatica acumulada: semanas recentes com temperatura na
    # faixa favoravel ao Aedes aegypti (entre 21 e 32 graus).
    faixa_favoravel = dados["tempmed"].between(21, 32).astype("int8")
    dados["semanas_favoraveis_8"] = (
        faixa_favoravel.groupby(dados["cod_ibge"])
        .transform(lambda serie: serie.shift(1).rolling(8, min_periods=4).sum())
    )

    return dados


def adicionar_contextuais(painel: pd.DataFrame) -> pd.DataFrame:
    """Porte populacional e marcadores territoriais."""
    dados = painel.copy()
    dados["porte_populacional"] = pd.cut(
        dados["pop"],
        bins=[0, 20_000, 100_000, 500_000, np.inf],
        labels=["pequeno", "medio", "grande", "metropole"],
    )
    dados["log_pop"] = np.log10(dados["pop"])
    return dados


def adicionar_flags_qualidade(painel: pd.DataFrame) -> pd.DataFrame:
    """Marcadores operacionais de completude e confiabilidade da linha."""
    dados = painel.sort_values(["cod_ibge", "data_ini_se"]).copy()

    # Completude da notificacao: casos confirmados sobre casos estimados.
    # Semana sem nenhum caso estimado e dado legitimo, nao dado incompleto:
    # nesse caso a completude e definida como 1 e a linha nao e provisoria.
    sem_casos = dados["casos_est"].fillna(0) == 0
    dados["completude"] = (dados["casos"] / dados["casos_est"].replace(0, np.nan)).clip(upper=1)
    dados.loc[sem_casos, "completude"] = 1.0
    dados["dado_provisorio"] = (dados["completude"] < LIMIAR_COMPLETUDE).fillna(True).astype("int8")

    # Largura relativa do intervalo de nowcasting: incerteza da estimativa.
    dados["incerteza_nowcast"] = (
        (dados["casos_est_max"] - dados["casos_est_min"]) / dados["casos_est"].replace(0, np.nan)
    ).fillna(0)

    colunas_imputadas = [c for c in dados.columns if c.endswith("_imputado")]
    dados["clima_imputado"] = dados[colunas_imputadas].max(axis=1) if colunas_imputadas else 0

    # Semanas iniciais nao tem historico suficiente para as janelas moveis.
    ordem = dados.groupby("cod_ibge").cumcount()
    dados["historico_insuficiente"] = (ordem < 8).astype("int8")

    return dados


def construir(bruto: pd.DataFrame) -> pd.DataFrame:
    """Encadeia todas as etapas e devolve a tabela analitica final."""
    dados = bruto.copy()
    dados["data_ini_se"] = pd.to_datetime(dados["data_ini_se"])
    dados = interpolar_clima(dados)
    dados = adicionar_epidemiologicas(dados)
    dados = adicionar_climaticas(dados)
    dados = adicionar_contextuais(dados)
    dados = adicionar_flags_qualidade(dados)
    return dados.sort_values(["cod_ibge", "data_ini_se"]).reset_index(drop=True)
