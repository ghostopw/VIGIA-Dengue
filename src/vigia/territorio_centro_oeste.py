"""Territorio de treino: os 468 municipios do Centro-Oeste.

POR QUE UM TERRITORIO DE TREINO MAIOR QUE O DE APLICACAO
---------------------------------------------------------
O alerta e de Brasilia e das suas cidades satelites -- e so isso aparece no
painel. Mas o Distrito Federal e um municipio unico na malha do IBGE, e um
modelo que aprendesse apenas com ele teria 660 linhas e nenhuma variacao
espacial: nao ha como aprender o que separa um municipio em surto de um
municipio calmo olhando para um lugar so.

O Centro-Oeste resolve isso sem trocar de problema. Sao 468 municipios -- GO
246, MT 142, MS 79 e o DF -- no mesmo bioma predominante, no mesmo regime de
chuva de verao e seca de inverno, com a mesma sazonalidade de arbovirose. O
modelo aprende a relacao entre condicao e surto num regime climatico parecido
com o de Brasilia, e depois e aplicado so onde interessa.

Isso multiplica a base por cerca de 15: de 20.638 linhas para perto de 310.000.
E o volume que justifica uma rede neural; com o territorio antigo, ela so teria
como decorar.

REGRA: `TERRITORIO_APLICACAO` e o recorte que aparece na tela. `coletar()` e o
recorte de treino. Nunca inverta os dois.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

from .ingestao_infodengue import baixar_municipio, padronizar

IBGE_REGIOES = "https://servicodados.ibge.gov.br/api/v1/localidades/regioes"
CODIGO_CENTRO_OESTE = 5

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "dados" / "processado" / "infodengue_centro_oeste.csv"
PARCIAIS = RAIZ / "dados" / "bruto" / "centro_oeste"

COD_FOCO = 5300108  # Brasilia: o unico municipio onde o alerta e exibido


def municipios() -> pd.DataFrame:
    """Os 468 municipios do Centro-Oeste, direto do IBGE.

    A lista vem da API de localidades e nao de uma copia local, para que a
    criacao ou fusao de um municipio nao passe despercebida.
    """
    resposta = requests.get(f"{IBGE_REGIOES}/{CODIGO_CENTRO_OESTE}/municipios", timeout=300)
    resposta.raise_for_status()

    linhas = []
    for item in resposta.json():
        # A API aninha a UF por caminhos diferentes conforme a divisao usada;
        # o DF, sem microrregiao, cai no ramo da regiao imediata.
        no = item.get("microrregiao") or item.get("regiao-imediata") or {}
        while isinstance(no, dict) and "UF" not in no:
            no = no.get("mesorregiao") or no.get("regiao-intermediaria") or {}
        sigla = no.get("UF", {}).get("sigla", "?") if isinstance(no, dict) else "?"
        linhas.append({"cod_ibge": int(item["id"]), "municipio": item["nome"], "uf": sigla})

    return pd.DataFrame(linhas).sort_values("cod_ibge").reset_index(drop=True)


def coletar(ano_inicio: int = 2014, ano_fim: int | None = None,
            destino: Path = DESTINO, pausa: float = 0.6) -> pd.DataFrame:
    """Baixa a serie do InfoDengue para todo o Centro-Oeste.

    Grava um arquivo por municipio em `dados/bruto/centro_oeste`: sao mais de
    quatrocentas chamadas, e uma queda no meio nao pode custar o trabalho todo.
    Rodar de novo aproveita o que ja esta em disco.
    """
    if ano_fim is None:
        ano_fim = pd.Timestamp.today().year

    lista = municipios()
    PARCIAIS.mkdir(parents=True, exist_ok=True)
    print(f"Centro-Oeste: {len(lista)} municipios ({ano_inicio}-{ano_fim})")

    partes: list[pd.DataFrame] = []
    reaproveitados = vazios = 0

    for indice, linha in enumerate(lista.itertuples(), start=1):
        arquivo = PARCIAIS / f"dengue_{linha.cod_ibge}.csv"

        if arquivo.exists():
            partes.append(pd.read_csv(arquivo))
            reaproveitados += 1
            continue

        bruto = baixar_municipio(linha.cod_ibge, ano_inicio, ano_fim)
        if bruto.empty:
            vazios += 1
            print(f"  [{indice:3d}/{len(lista)}] {linha.municipio[:26]:26} SEM DADOS")
            continue

        parte = padronizar(bruto, linha.cod_ibge)
        parte.to_csv(arquivo, index=False, encoding="utf-8")
        partes.append(parte)

        if indice % 25 == 0 or indice == len(lista):
            print(f"  [{indice:3d}/{len(lista)}] {linha.municipio[:26]:26} "
                  f"{len(parte):4d} semanas")
        time.sleep(pausa)  # cortesia com a API publica

    if not partes:
        raise RuntimeError("o InfoDengue nao devolveu dado algum")

    base = pd.concat(partes, ignore_index=True)
    base = base.drop_duplicates(subset=["cod_ibge", "se_codigo"])
    base = base.merge(lista[["cod_ibge", "uf"]], on="cod_ibge", how="left",
                      suffixes=("", "_lista"))
    if "uf_lista" in base.columns:
        base["uf"] = base["uf"].fillna(base["uf_lista"])
        base = base.drop(columns="uf_lista")

    destino.parent.mkdir(parents=True, exist_ok=True)
    base.to_csv(destino, index=False, encoding="utf-8")

    print(f"\n{len(base):,} linhas | {base['cod_ibge'].nunique()} municipios"
          .replace(",", "."))
    print(f"reaproveitados do disco: {reaproveitados} | sem dados: {vazios}")
    print(f"gravado em {destino}")
    return base


if __name__ == "__main__":
    coletar()
