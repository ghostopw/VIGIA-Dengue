"""Peso relativo de cada Regiao Administrativa do Distrito Federal.

O QUE ESTE NUMERO E
-------------------
Para cada RA e cada semana, a probabilidade que o modelo -- treinado nos 34
municipios da RIDE-DF -- atribuiria aquele lugar se ele fosse um municipio com:

  - o quadro epidemiologico de Brasilia, que e o unico observado, porque o
    Distrito Federal e um municipio so na malha do IBGE;
  - a populacao da propria RA;
  - o clima medido na propria RA (ERA5, ver `clima_ras.py`).

Os municipios vizinhos entram apenas como treino. Nenhum deles aparece no
resultado: o que sai daqui e uma tabela de RAs do DF.

O QUE ELE NAO E
---------------
Nao e incidencia por RA nem casos por RA. Nao existe fonte publica com essa
serie -- `ras_df.py` documenta a busca. O peso responde a uma pergunta
condicional: dado o quadro do DF nesta semana, em que RAs as condicoes locais
sao mais favoraveis ao vetor.

A HIPOTESE QUE ELE CARREGA, E COMO VERIFICA-LA
----------------------------------------------
Como nao ha incidencia por RA, o modulo assume incidencia uniforme no DF e
reparte os casos estimados na proporcao da populacao. Isso mantem cada linha
internamente coerente -- populacao P, incidencia I, casos I x P -- que e a forma
das linhas com que o modelo foi treinado.

A consequencia e que as RAs so podem diferir entre si pelo clima e pelo porte
populacional. Se o peso resultante for uma funcao monotona da populacao, o mapa
nao acrescenta nada ao mapa populacional, e `ras_df.py` adverte explicitamente
contra publicar um mapa assim. Por isso `diagnosticar()` mede a correlacao de
Spearman entre peso e populacao e devolve esse numero junto com o resultado:
ele deve ser lido antes de qualquer leitura do mapa.

Uso:  python src/vigia/executar_peso_ras.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from .base_analitica import construir
from .modelagem import VARIAVEIS, modelo_aprendizado, preparar

RAIZ = Path(__file__).resolve().parents[2]
BASE_COM_RISCO = RAIZ / "dados" / "processado" / "base_com_risco.csv"
CLIMA_RAS = RAIZ / "dados" / "externo" / "clima_ras.csv"
DESTINO = RAIZ / "dados" / "processado" / "peso_ras.csv"

COD_FOCO = 5300108

# Colunas que descrevem o quadro epidemiologico do DF e valem igualmente para
# todas as RAs, por falta de medida intraurbana.
HERDADAS_DE_BRASILIA = [
    "canal_q1", "canal_mediana", "canal_q3", "nivel_canal",
    "esgoto_inadequado_pct", "sem_agua_rede_pct", "lixo_sem_coleta_pct",
]


def _clima_de_referencia(clima: pd.DataFrame) -> pd.DataFrame:
    """Clima medio do DF, ponderado pela populacao das RAs.

    A ponderacao por populacao faz a media representar o clima do morador
    tipico, e nao o do territorio: assim os desvios das RAs se anulam em torno
    do valor de Brasilia, e o conjunto fica centrado no municipio observado.
    """
    def media(coluna: str) -> pd.Series:
        produto = clima[coluna] * clima["populacao"]
        soma = produto.groupby(clima["data_ini_se"]).sum()
        pesos = clima.groupby("data_ini_se")["populacao"].sum()
        return soma / pesos

    return pd.DataFrame({
        coluna: media(coluna)
        for coluna in ("tempmed", "tempmin", "tempmax", "umidmed")
    }).reset_index()


def montar_base_sintetica(base: pd.DataFrame, clima: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por RA e semana, na forma que o modelo espera de um municipio.

    Cada RA vira um "municipio" identificado pelo codigo de subdistrito do IBGE,
    com o historico de Brasilia repartido pela populacao e o clima trocado pelo
    da propria RA.
    """
    brasilia = base[base["cod_ibge"] == COD_FOCO].copy()
    brasilia["data_ini_se"] = pd.to_datetime(brasilia["data_ini_se"])
    clima = clima.copy()
    clima["data_ini_se"] = pd.to_datetime(clima["data_ini_se"])

    referencia = _clima_de_referencia(clima)
    clima = clima.merge(referencia, on="data_ini_se", suffixes=("", "_ref"))

    # A temperatura e a umidade da base municipal vem do InfoDengue; as das RAs
    # vem do ERA5. Somar o desvio -- e nao substituir o valor -- mantem o modelo
    # na escala em que foi treinado e injeta so a diferenca entre as RAs.
    for coluna in ("tempmed", "tempmin", "tempmax", "umidmed"):
        clima[f"desvio_{coluna}"] = clima[coluna] - clima[f"{coluna}_ref"]

    pop_df = float(brasilia["pop"].iloc[-1])
    colunas_brasilia = [
        "data_ini_se", "se_codigo", "ano", "semana", "casos", "casos_est",
        "casos_est_min", "casos_est_max", "pop", "tempmed", "tempmin",
        "tempmax", "umidmed", "uf",
    ] + HERDADAS_DE_BRASILIA
    colunas_brasilia = [c for c in colunas_brasilia if c in brasilia.columns]

    pedacos = []
    for nome, serie in clima.groupby("ra_nome", sort=False):
        juncao = brasilia[colunas_brasilia].merge(
            serie[["data_ini_se", "cod_subdistrito", "populacao",
                   "chuva_semana_mm", "chuva_dias_com_chuva",
                   "desvio_tempmed", "desvio_tempmin", "desvio_tempmax",
                   "desvio_umidmed"]],
            on="data_ini_se", how="inner",
        )
        if juncao.empty:
            continue

        fracao = juncao["populacao"] / pop_df
        juncao["cod_ibge"] = juncao["cod_subdistrito"].astype("int64")
        juncao["municipio"] = nome
        juncao["pop"] = juncao["populacao"]

        # Incidencia uniforme no DF: os casos acompanham a populacao, o que
        # preserva a coerencia interna da linha (casos = incidencia x pop).
        for coluna in ("casos", "casos_est", "casos_est_min", "casos_est_max"):
            if coluna in juncao:
                juncao[coluna] = juncao[coluna] * fracao

        for coluna in ("tempmed", "tempmin", "tempmax", "umidmed"):
            juncao[coluna] = juncao[coluna] + juncao[f"desvio_{coluna}"]

        pedacos.append(juncao.drop(columns=[
            c for c in juncao.columns if c.startswith("desvio_")
        ] + ["populacao", "cod_subdistrito"]))

    return pd.concat(pedacos, ignore_index=True)


def calcular(base: pd.DataFrame | None = None,
             clima: pd.DataFrame | None = None) -> pd.DataFrame:
    """Treina nos municipios e aplica a cada Regiao Administrativa."""
    if base is None:
        base = pd.read_csv(BASE_COM_RISCO, parse_dates=["data_ini_se"])
    if clima is None:
        clima = pd.read_csv(CLIMA_RAS, parse_dates=["data_ini_se"])

    # ---- treino: os 34 municipios, exatamente como em `painel_dados.gerar`
    preparado = preparar(base)
    variaveis = [v for v in VARIAVEIS if v in preparado.columns]
    treino = preparado.dropna(subset=["alvo"])
    modelo = modelo_aprendizado().fit(treino[variaveis], treino["alvo"])

    # ---- aplicacao: as RAs, passando pela mesma cadeia de derivacao
    sintetica = montar_base_sintetica(base, clima)
    chuva = sintetica[["cod_ibge", "data_ini_se", "chuva_semana_mm",
                       "chuva_dias_com_chuva"]].copy()
    derivada = construir(sintetica.drop(
        columns=["chuva_semana_mm", "chuva_dias_com_chuva"]), chuva)

    # `canal_*` e a vulnerabilidade vem de Brasilia e atravessam a derivacao
    # sem alteracao; as demais variaveis do modelo foram recalculadas por RA.
    faltando = [v for v in variaveis if v not in derivada.columns]
    if faltando:
        raise RuntimeError(f"variaveis ausentes na base das RAs: {faltando}")

    derivada["peso"] = modelo.predict_proba(derivada[variaveis])[:, 1]

    resultado = derivada[[
        "municipio", "cod_ibge", "se_codigo", "data_ini_se", "pop", "peso",
        "tempmed", "umidmed", "chuva_semana_mm",
    ]].rename(columns={"municipio": "ra_nome", "cod_ibge": "cod_subdistrito"})

    # Peso relativo: quanto a RA se afasta da media do DF naquela semana. E a
    # leitura util no mapa -- o nivel absoluto ja esta no painel de Brasilia.
    media_semana = resultado.groupby("se_codigo")["peso"].transform("mean")
    resultado["peso_relativo"] = resultado["peso"] / media_semana

    return resultado.sort_values(["se_codigo", "peso"], ascending=[True, False])


def diagnosticar(resultado: pd.DataFrame) -> dict:
    """Mede o quanto o peso e apenas a populacao repintada.

    Se a correlacao de Spearman entre peso e populacao for proxima de 1, o mapa
    por RA nao carrega informacao alem do mapa populacional, e nao deve ser
    publicado como se carregasse.
    """
    ultima = resultado[resultado["se_codigo"] == resultado["se_codigo"].max()]
    rho, p = stats.spearmanr(ultima["pop"], ultima["peso"])
    return {
        "semana": int(ultima["se_codigo"].iloc[0]),
        "ras": int(len(ultima)),
        "spearman_peso_populacao": round(float(rho), 3),
        "p_valor": round(float(p), 4),
        "amplitude_peso_relativo": round(
            float(ultima["peso_relativo"].max() - ultima["peso_relativo"].min()), 3
        ),
    }


def salvar(destino: Path = DESTINO) -> pd.DataFrame:
    resultado = calcular()
    destino.parent.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(destino, index=False)
    return resultado


if __name__ == "__main__":
    tabela = salvar()
    print(f"linhas: {len(tabela)} | RAs: {tabela['ra_nome'].nunique()}")
    print()
    for chave, valor in diagnosticar(tabela).items():
        print(f"  {chave}: {valor}")
