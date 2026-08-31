"""Condicao de criadouro por setor censitario do Distrito Federal.

A ESCALA
--------
O setor censitario e a menor unidade que o IBGE publica: no DF sao 5.418 deles,
5.021 urbanos, cada um com algumas quadras e cerca de trezentos domicilios. E
159 vezes mais fino que as 31 Regioes Administrativas.

Nao ha nome de rua aqui: no Distrito Federal o campo de bairro da malha vem
vazio, porque o IBGE organiza o DF por subdistrito -- a propria RA. O que existe
e o poligono da quadra. Sobre o mapa base, que desenha e nomeia as ruas, o
poligono pintado responde a pergunta na escala em que ela foi feita: nesta
quadra, nestas ruas.

O QUE SE MEDE AQUI, E O QUE NAO
-------------------------------
Mede-se CONDICAO DE CRIADOURO, nao caso. Nao existe serie de dengue por setor
censitario -- nao existe nem por Regiao Administrativa, como `ras_df.py`
documenta. O que o Censo 2022 da neste nivel:

  sem_bueiro_pct     faces de quadra sem boca de lobo. E a variavel de fluxo
                     das aguas na escala do mosquito: sem drenagem a chuva
                     empoca, e o Aedes se cria em agua parada, nao corrente.
                     No DF, 653 setores tem 100% das faces sem bueiro.
  sem_pavimento_pct  faces sem pavimento, onde a agua empoca mesmo havendo
                     drenagem.
  esgoto_inadequado_pct, sem_agua_rede_pct, lixo_sem_coleta_pct
                     as mesmas tres dimensoes de `vulnerabilidade_ras.py`,
                     agora por quadra.

COMO LER O RESULTADO
--------------------
O risco de dengue continua sendo municipal, porque so existe caso nesse nivel.
Esta camada diz onde, dentro de Brasilia, a condicao local favorece o vetor --
e permite dirigir a visita, o mutirao e a remocao de criadouro a quadra, em vez
de a cidade inteira.

Uso:  python src/vigia/executar_setores_df.py
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[2]
EXTERNO = RAIZ / "dados" / "externo"
MALHA = EXTERNO / "DF_setores_CD2022.gpkg"
DESTINO_GEO = EXTERNO / "setores_df.geojson"
DESTINO_TABELA = EXTERNO / "setores_df.csv"

FTP_MALHA = ("https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
             "Agregados_por_Setores_Censitarios/malha_com_atributos/setores/"
             "gpkg/UF/DF/DF_setores_CD2022.gpkg")
FTP_ENTORNO = ("https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
               "Agregados_por_Setores_Censitarios_Caracteristicas_urbanisticas_"
               "do_entorno_dos_domicilios/Agregados_por_Setor_csv/"
               "Agregados_por_setores_entorno_faces_BR.zip")
FTP_DOMICILIO = ("https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
                 "Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/"
                 "Agregados_por_setores_caracteristicas_domicilio2_BR_20250417.zip")
# O total de domicilios nao esta na Parte 2 -- so na Parte 1. Sem ele, todas as
# proporcoes de saneamento saem vazias.
FTP_TOTAL = ("https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
             "Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/"
             "Agregados_por_setores_caracteristicas_domicilio1_BR.zip")

PREFIXO_DF = "5300108"

COM_BUEIRO, SEM_BUEIRO = "V05409", "V05410"
COM_PAVIMENTO, SEM_PAVIMENTO = "V05406", "V05407"
ESGOTO_INADEQUADO = ["V00312", "V00313", "V00315"]
SEM_AGUA_REDE = ["V00464"]
LIXO_SEM_COLETA = ["V00399", "V00400", "V00402"]
DOMICILIOS = "V00001"

# Tolerancia da simplificacao, em graus. Cerca de onze metros: preserva a forma
# da quadra e corta o arquivo o bastante para o mapa abrir no navegador.
TOLERANCIA = 0.0001


def _baixar_zip(url: str, filtrar_df: bool = True) -> pd.DataFrame:
    """Baixa um agregado por setor e devolve so as linhas do DF.

    Os arquivos sao nacionais e chegam a dezenas de megabytes; filtrar aqui
    evita carregar o Brasil inteiro na memoria do resto do pipeline.
    """
    resposta = requests.get(url, timeout=1800)
    resposta.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resposta.content)) as pacote:
        nome = pacote.namelist()[0]
        dados = pd.read_csv(pacote.open(nome), sep=";", dtype=str, encoding="latin-1")

    dados = dados.rename(columns={dados.columns[0]: "CD_SETOR"})
    if filtrar_df:
        dados = dados[dados["CD_SETOR"].astype(str).str.startswith(PREFIXO_DF)]
    return dados.reset_index(drop=True)


def _numero(coluna: pd.Series) -> pd.Series:
    """Trata os codigos de ausencia do IBGE: "X" e sigilo, vazio e nao se aplica."""
    return pd.to_numeric(coluna.replace({"X": None, "": None}), errors="coerce")


def _proporcao(dados: pd.DataFrame, variaveis: list[str],
               denominador: pd.Series) -> pd.Series:
    """Proporcao sobre o denominador, guardando contra divisao por zero.

    Usa `where` e nao `replace`: trocar 0 por NA com `replace` devolve uma serie
    de tipo object, e ai o arredondamento falha.
    """
    soma = sum(_numero(dados[v]) for v in variaveis if v in dados.columns)
    return (soma / denominador.where(denominador != 0) * 100).round(1)


def coletar(destino_geo: Path = DESTINO_GEO,
            destino_tabela: Path = DESTINO_TABELA) -> gpd.GeoDataFrame:
    """Monta a camada de setores com drenagem e saneamento."""
    if not MALHA.exists():
        print("baixando a malha de setores do DF...")
        MALHA.parent.mkdir(parents=True, exist_ok=True)
        MALHA.write_bytes(requests.get(FTP_MALHA, timeout=1800).content)

    malha = gpd.read_file(MALHA)
    print(f"malha: {len(malha)} setores")

    print("baixando o entorno por setor (faces de quadra)...")
    entorno = _baixar_zip(FTP_ENTORNO)
    print("baixando as caracteristicas do domicilio por setor...")
    domicilio = _baixar_zip(FTP_DOMICILIO)
    print("baixando o total de domicilios por setor...")
    totais = _baixar_zip(FTP_TOTAL)[["CD_SETOR", DOMICILIOS]]

    dados = (entorno.merge(domicilio, on="CD_SETOR", how="outer", suffixes=("", "_dom"))
             .merge(totais, on="CD_SETOR", how="left", suffixes=("", "_tot")))

    faces_bueiro = _numero(dados[COM_BUEIRO]) + _numero(dados[SEM_BUEIRO])
    faces_pavimento = _numero(dados[COM_PAVIMENTO]) + _numero(dados[SEM_PAVIMENTO])
    domicilios = _numero(dados[DOMICILIOS]) if DOMICILIOS in dados else pd.Series(dtype=float)

    tabela = pd.DataFrame({
        "CD_SETOR": dados["CD_SETOR"],
        "domicilios": domicilios,
        "sem_bueiro_pct": (_numero(dados[SEM_BUEIRO]) / faces_bueiro.where(faces_bueiro != 0)
                           * 100).round(1),
        "sem_pavimento_pct": (_numero(dados[SEM_PAVIMENTO])
                              / faces_pavimento.where(faces_pavimento != 0) * 100).round(1),
        "esgoto_inadequado_pct": _proporcao(dados, ESGOTO_INADEQUADO, domicilios),
        "sem_agua_rede_pct": _proporcao(dados, SEM_AGUA_REDE, domicilios),
        "lixo_sem_coleta_pct": _proporcao(dados, LIXO_SEM_COLETA, domicilios),
    })

    # Indice de criadouro: media das quatro dimensoes, cada uma normalizada
    # dentro do proprio DF. Mesma construcao de `vulnerabilidade_ras.py`, para
    # que as duas escalas se leiam juntas.
    dimensoes = ["sem_bueiro_pct", "sem_pavimento_pct",
                 "esgoto_inadequado_pct", "lixo_sem_coleta_pct"]
    partes = []
    for coluna in dimensoes:
        faixa = tabela[coluna].max() - tabela[coluna].min()
        partes.append((tabela[coluna] - tabela[coluna].min()) / faixa if faixa else 0.0)
    tabela["indice_criadouro"] = (sum(partes) / len(partes) * 100).round(1)

    setores = malha.merge(tabela, on="CD_SETOR", how="left")
    setores["geometry"] = setores.geometry.simplify(TOLERANCIA, preserve_topology=True)

    colunas = ["CD_SETOR", "NM_SUBDIST", "SITUACAO", "AREA_KM2", "domicilios",
               "sem_bueiro_pct", "sem_pavimento_pct", "esgoto_inadequado_pct",
               "sem_agua_rede_pct", "lixo_sem_coleta_pct", "indice_criadouro",
               "geometry"]
    setores = setores[[c for c in colunas if c in setores.columns]]

    com_dado = int(setores["sem_bueiro_pct"].notna().sum())
    print(f"\n{len(setores)} setores | {com_dado} com dado de drenagem")
    print(f"  setores com 100% das faces sem bueiro: "
          f"{int((setores['sem_bueiro_pct'] == 100).sum())}")

    destino_geo.parent.mkdir(parents=True, exist_ok=True)
    setores.to_file(destino_geo, driver="GeoJSON")
    setores.drop(columns="geometry").to_csv(destino_tabela, index=False, encoding="utf-8")
    tamanho = destino_geo.stat().st_size / 1024 / 1024
    print(f"gravado em {destino_geo.name} ({tamanho:.1f} MB) e {destino_tabela.name}")
    return setores


if __name__ == "__main__":
    coletar()
