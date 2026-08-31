"""Indicadores municipais de vulnerabilidade socioambiental (IBGE, Censo 2022).

O projeto preve, no item 4.4, um bloco contextual com vulnerabilidade social.
A fonte originalmente prevista era o Atlas da Vulnerabilidade Social do Ipea,
cujo IVS municipal e distribuido como planilha no portal e nao pela API do
ipeadata -- que serve apenas series nacionais e estaduais.

Este modulo usa o Censo Demografico 2022 do IBGE, que oferece pela API, no
nivel municipal, os componentes de saneamento que a literatura associa
diretamente a proliferacao do Aedes aegypti:

  - esgotamento sanitario inadequado (fossa rudimentar, vala, curso d'agua);
  - ausencia de ligacao a rede geral de agua, que leva ao armazenamento
    domiciliar em caixas e tonéis -- criadouro classico do vetor;
  - lixo sem coleta regular, que acumula recipientes com agua parada.

Densidade demografica entra a partir da area territorial, tambem do IBGE.

Todos os indicadores sao FIXOS no tempo: descrevem o municipio, nao a semana.
Entram na base analitica replicados em todas as semanas do municipio.

Resultado observado no territorio (agosto de 2026)
--------------------------------------------------
Medida contra a incidencia media municipal do periodo 2014-2026, a
vulnerabilidade socioambiental NAO apresentou associacao estatisticamente
significativa (Spearman rho = 0,119; p = 0,51), e os tercis de vulnerabilidade
tiveram incidencias medias equivalentes (34,6 / 39,0 / 35,7 por 100 mil).
Como preditor, o bloco acrescenta pouco: +0,0007 de AUC media em sete anos de
validacao temporal, ainda que positivo em cinco deles e maior em 2024.

Duas leituras possiveis, que o projeto deve discutir em vez de esconder:
o indicador e municipal e agregado, enquanto a vulnerabilidade relevante para
dengue e intraurbana -- dentro de Brasilia, a diferenca entre o Plano Piloto e
a periferia e enorme e nenhum indicador municipal a captura; e a notificacao
depende de acesso a servico de saude, o que pode subnotificar justamente as
areas mais vulneraveis e atenuar a associacao real.

O bloco foi mantido por constar do item 4.4 do projeto aprovado, por descrever
o territorio no painel e por nao prejudicar o desempenho.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

from .territorio import TERRITORIO

AGREGADOS = "https://servicodados.ibge.gov.br/api/v3/agregados"
MALHA_AREA = "https://servicodados.ibge.gov.br/api/v3/agregados/1301/periodos/2010/variaveis/615"

# Agregado, variavel, classificacao e categorias de cada indicador do Censo 2022.
ESGOTO = {
    "agregado": 10053, "variavel": 9599, "classificacao": 11558,
    "total": 46292,
    # Fossa rudimentar, vala, rio/lago/mar e outra forma: sem tratamento.
    "inadequado": [72113, 92858, 72114],
}
# Usa-se o agregado 6751, universal, e nao o 10341: aquele e um recorte que o
# IBGE omite ("...") na maioria dos municipios pequenos e cujo total nem sequer
# corresponde ao universo de domicilios.
AGUA = {
    "agregado": 6751, "variavel": 9599, "classificacao": 1821,
    "total": 72129,
    # Domicilios que possuem ligacao a rede e a utilizam como forma principal.
    "adequado": [72144],
}
LIXO = {
    "agregado": 9839, "variavel": 9599, "classificacao": 67,
    "total": 10972,
    "coletado": [2520],
}


def _consultar(agregado: int, variavel: int, periodo: int, classificacao: int,
               categorias: list[int], geocodigos: list[int]) -> dict[int, float]:
    """Consulta um agregado do IBGE e soma as categorias pedidas por municipio."""
    url = f"{AGREGADOS}/{agregado}/periodos/{periodo}/variaveis/{variavel}"

    # Em lotes: com centenas de municipios a lista de localidades estoura o
    # comprimento aceito na URL, e o IBGE devolve erro em vez de recusar so o
    # excedente.
    retornos = []
    LOTE = 60
    for inicio in range(0, len(geocodigos), LOTE):
        fatia = geocodigos[inicio:inicio + LOTE]
        parametros = {
            "localidades": "N6[" + ",".join(str(g) for g in fatia) + "]",
            "classificacao": f"{classificacao}[{','.join(str(c) for c in categorias)}]",
        }
        resposta = requests.get(url, params=parametros, timeout=180)
        resposta.raise_for_status()
        retornos.extend(resposta.json())

    totais: dict[int, float] = {}
    for variavel_retornada in retornos:
        for resultado in variavel_retornada["resultados"]:
            for serie in resultado["series"]:
                codigo = int(serie["localidade"]["id"])
                for valor in serie["serie"].values():
                    # O IBGE usa "-" e "..." para dado inexistente ou omitido.
                    numero = pd.to_numeric(valor, errors="coerce")
                    if pd.notna(numero):
                        totais[codigo] = totais.get(codigo, 0.0) + float(numero)
    return totais


def _proporcao(indicador: dict, categorias: list[int], periodo: int,
               geocodigos: list[int]) -> pd.Series:
    """Razao entre as categorias pedidas e o total do indicador."""
    parte = _consultar(
        indicador["agregado"], indicador["variavel"], periodo,
        indicador["classificacao"], categorias, geocodigos,
    )
    time.sleep(1)
    total = _consultar(
        indicador["agregado"], indicador["variavel"], periodo,
        indicador["classificacao"], [indicador["total"]], geocodigos,
    )
    time.sleep(1)
    return pd.Series({
        codigo: (parte.get(codigo, 0.0) / valor * 100) if valor else float("nan")
        for codigo, valor in total.items()
    })


def coletar(destino: Path | None = None,
            municipios: dict[int, str] | None = None) -> pd.DataFrame:
    """Monta a tabela municipal de vulnerabilidade socioambiental.

    `municipios` permite usar outro recorte que nao o territorio do painel --
    o Centro-Oeste inteiro, por exemplo, que e o territorio de treino. Sem ele,
    vale `TERRITORIO`, e o comportamento e o de sempre.
    """
    catalogo = municipios if municipios is not None else TERRITORIO
    geocodigos = sorted(catalogo)

    esgoto = _proporcao(ESGOTO, ESGOTO["inadequado"], 2022, geocodigos)
    agua = _proporcao(AGUA, AGUA["adequado"], 2022, geocodigos)
    lixo = _proporcao(LIXO, LIXO["coletado"], 2010, geocodigos)

    tabela = pd.DataFrame({
        "cod_ibge": geocodigos,
        "municipio": [catalogo[g] for g in geocodigos],
    })
    tabela["esgoto_inadequado_pct"] = tabela["cod_ibge"].map(esgoto)
    tabela["sem_agua_rede_pct"] = tabela["cod_ibge"].map(agua).rsub(100)
    tabela["lixo_sem_coleta_pct"] = tabela["cod_ibge"].map(lixo).rsub(100)

    # Indice sintetico: media dos tres componentes, na escala 0 a 100.
    # Exige os tres presentes -- uma media sobre componente faltante produziria
    # um indice silenciosamente incomparavel entre municipios.
    componentes = ["esgoto_inadequado_pct", "sem_agua_rede_pct", "lixo_sem_coleta_pct"]
    completo = tabela[componentes].notna().all(axis=1)
    tabela["vulnerabilidade_socioambiental"] = tabela[componentes].mean(axis=1).where(completo)

    faltantes = int((~completo).sum())
    if faltantes:
        print(f"aviso: {faltantes} municipios sem os tres componentes; indice nao calculado")

    if destino is not None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        tabela.to_csv(destino, index=False, encoding="utf-8")

    return tabela


def integrar(base: pd.DataFrame, vulnerabilidade: pd.DataFrame) -> pd.DataFrame:
    """Acopla os indicadores municipais a base municipio-semana.

    Os valores sao fixos no tempo: descrevem o municipio, nao a semana, e por
    isso se repetem em todas as linhas daquele municipio.
    """
    colunas = [
        "cod_ibge", "esgoto_inadequado_pct", "sem_agua_rede_pct",
        "lixo_sem_coleta_pct", "vulnerabilidade_socioambiental",
    ]
    return base.merge(vulnerabilidade[colunas], on="cod_ibge", how="left")
