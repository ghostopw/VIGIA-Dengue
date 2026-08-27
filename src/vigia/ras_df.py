"""Malha das Regioes Administrativas do Distrito Federal.

As RAs -- Ceilandia, Taguatinga, Samambaia, Plano Piloto e demais -- sao a
divisao intraurbana do DF. Nao sao municipios: o IBGE reconhece no Distrito
Federal um unico municipio (5300108). Ele registra as RAs apenas como
SUBDISTRITOS, para os quais nao publica malha cartografica.

Este modulo prepara a geometria das RAs em GeoJSON, para o mapa intraurbano do
painel.

LIMITE CONHECIDO -- leia antes de usar
--------------------------------------
Nao existe, ate onde foi possivel verificar, fonte publica com serie semanal de
casos de dengue por RA:

  - o InfoDengue opera apenas no nivel municipal e devolve lista vazia para os
    codigos de subdistrito;
  - o painel de incidencia da SES-DF (infomapas.saude.df.gov.br) e uma
    aplicacao Streamlit, sem endpoint REST publico;
  - o painel do LIRAa da SES-DF e um relatorio Power BI embutido;
  - o portal de dados abertos do DF nao expoe API (CKAN retorna 404);
  - os microdados do SINAN, que trazem o bairro de residencia, dependem do
    FTP do DATASUS, inacessivel no ambiente do projeto.

Por isso o mapa por RA e apresentado como camada territorial e de
vulnerabilidade, e NAO como mapa de incidencia. Distribuir os casos do DF pelas
RAs na proporcao da populacao produziria um mapa que parece informativo e nao
e: ele apenas repintaria o mapa populacional, escondendo a heterogeneidade
intraurbana real -- exatamente o que se quer medir.

Quando a Secretaria de Saude do DF ceder os casos por RA, basta acoplar a
serie a esta malha pela coluna `ra_nome`.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .territorio import RAS_DF, normalizar

RAIZ = Path(__file__).resolve().parents[2]
SHAPEFILE = RAIZ / "dados" / "externo" / "ras_shp" / "ras_pdad_2013.shp"
DESTINO_GEOJSON = RAIZ / "dados" / "externo" / "malha_ras_df.geojson"

# Populacao das RAs (PDAD 2021, Codeplan/IPEDF). Usada como denominador da
# incidencia intraurbana quando os casos por RA estiverem disponiveis, e para
# dimensionar o mapa territorial enquanto isso.
POPULACAO_RA = {
    "Plano Piloto": 220393,
    "Gama": 145659,
    "Taguatinga": 205670,
    "Brazlandia": 53534,
    "Sobradinho": 65569,
    "Planaltina": 190495,
    "Paranoa": 65533,
    "Nucleo Bandeirante": 25334,
    "Ceilandia": 348000,
    "Guara": 137819,
    "Cruzeiro": 33334,
    "Samambaia": 254439,
    "Santa Maria": 133369,
    "Sao Sebastiao": 118853,
    "Recanto das Emas": 149707,
    "Lago Sul": 30553,
    "Riacho Fundo": 47154,
    "Lago Norte": 37135,
    "Candangolandia": 16886,
    "Aguas Claras": 152560,
    "Riacho Fundo II": 88478,
    "Sudoeste/Octogonal": 55631,
    "Varjao": 9520,
    "Park Way": 21988,
    "SCIA": 42186,
    "Sobradinho II": 100775,
    "Jardim Botanico": 55170,
    "Itapoa": 71298,
    "SIA": 2286,
    "Vicente Pires": 78152,
    "Fercal": 8801,
}


def _chave(texto: str) -> str:
    """Reduz o nome a letras maiusculas sem acento, para comparacao."""
    return "".join(c for c in normalizar(texto) if c.isalpha())


def _casar(nome_corrompido: str, candidatos: dict[str, object]) -> object | None:
    """Encontra o nome oficial correspondente a um nome com bytes corrompidos.

    O .dbf de origem gravou os acentos como bytes invalidos, e a leitura os
    devolve como letras erradas: "Brazlandia" chega como "BRAZLINDIA" e
    "Ceilandia" como "CEILINDIA". Como a corrupcao afeta um caractere por
    acento, sem mudar o comprimento nem a ordem das demais letras, a
    correspondencia e feita por similaridade: exige mesmo tamanho e apenas
    poucas posicoes divergentes.
    """
    chave = _chave(nome_corrompido)
    if chave in candidatos:
        return candidatos[chave]

    melhor, menor_distancia = None, 99
    for candidato, valor in candidatos.items():
        if len(candidato) != len(chave):
            continue
        distancia = sum(1 for a, b in zip(chave, candidato) if a != b)
        if distancia < menor_distancia:
            melhor, menor_distancia = valor, distancia

    # Ate duas letras trocadas: cobre nomes com um ou dois acentos.
    return melhor if menor_distancia <= 2 else None


def carregar_malha() -> gpd.GeoDataFrame:
    """Le o shapefile das RAs e padroniza nomes e colunas."""
    if not SHAPEFILE.exists():
        raise FileNotFoundError(
            f"shapefile das RAs ausente em {SHAPEFILE}; "
            "execute executar_ras.py para baixa-lo"
        )

    malha = gpd.read_file(SHAPEFILE)
    malha = malha.rename(columns={"nome": "ra_nome", "ra_num": "ra_numero"})

    # O .dbf de origem tem os acentos corrompidos (bytes invalidos gravados na
    # publicacao do arquivo), e nenhum encoding os recupera: "Ceilandia" chega
    # como "Ceil�ndia". O casamento e feito entao por uma chave sem
    # acentos e sem os caracteres de substituicao, o que e estavel a isso.
    canonico = {_chave(nome): nome for nome in RAS_DF.values()}
    por_nome = {_chave(nome): codigo for codigo, nome in RAS_DF.items()}
    populacao = {_chave(k): v for k, v in POPULACAO_RA.items()}

    originais = malha["ra_nome"].tolist()
    malha["ra_nome"] = [_casar(n, canonico) or n for n in originais]
    malha["cod_subdistrito"] = [_casar(n, por_nome) for n in originais]
    malha["populacao"] = [_casar(n, populacao) for n in originais]

    return malha.to_crs("EPSG:4326")


def exportar_geojson(destino: Path = DESTINO_GEOJSON) -> dict:
    """Grava a malha das RAs em GeoJSON, pronta para o mapa do painel."""
    malha = carregar_malha()
    destino.parent.mkdir(parents=True, exist_ok=True)

    # Densidade: area em projecao equivalente do Brasil (Albers, EPSG:5880).
    malha["area_km2"] = malha.to_crs("EPSG:5880").geometry.area / 1e6
    malha["densidade_hab_km2"] = (malha["populacao"] / malha["area_km2"]).round(1)

    colunas = ["ra_nome", "ra_numero", "cod_subdistrito", "populacao",
               "area_km2", "densidade_hab_km2", "geometry"]
    reduzida = malha[[c for c in colunas if c in malha.columns]].copy()
    reduzida["area_km2"] = reduzida["area_km2"].round(1)
    # Simplifica a geometria: o painel nao precisa da resolucao original, e o
    # arquivo menor carrega mais rapido no navegador.
    reduzida["geometry"] = reduzida["geometry"].simplify(0.0005, preserve_topology=True)

    colecao = json.loads(reduzida.to_json())
    for feicao in colecao["features"]:
        feicao["id"] = feicao["properties"]["ra_nome"]

    destino.write_text(json.dumps(colecao), encoding="utf-8")
    return colecao


def resumo() -> pd.DataFrame:
    """Tabela das RAs com area, populacao e densidade."""
    malha = carregar_malha()
    # Area em km2: projecao equivalente do Brasil (Albers, EPSG:5880).
    metrico = malha.to_crs("EPSG:5880")
    malha["area_km2"] = metrico.geometry.area / 1e6
    malha["densidade_hab_km2"] = malha["populacao"] / malha["area_km2"]

    colunas = ["ra_nome", "cod_subdistrito", "populacao", "area_km2", "densidade_hab_km2"]
    return malha[colunas].sort_values("populacao", ascending=False).reset_index(drop=True)
