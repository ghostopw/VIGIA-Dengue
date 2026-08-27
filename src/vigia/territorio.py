"""Definicao do territorio piloto: Distrito Federal e RIDE-DF.

A RIDE-DF (Regiao Integrada de Desenvolvimento do Distrito Federal e Entorno)
foi instituida pela Lei Complementar 94/1998 e ampliada pela LC 163/2018.
Reune o Distrito Federal, 29 municipios goianos do Entorno e 3 municipios
mineiros do noroeste de Minas -- 33 unidades territoriais no total.

Todos os codigos IBGE abaixo foram resolvidos e conferidos contra a API de
localidades do IBGE. A funcao `validar_territorio` refaz essa conferencia sob
demanda, para que a base analitica nunca seja construida sobre codigo errado.
"""

from __future__ import annotations

import unicodedata

import requests

IBGE_LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades"

# O Distrito Federal e um unico municipio na malha do IBGE.
#
# Por que nao aparecem aqui Ceilandia, Taguatinga, Samambaia e as demais
# "cidades de Brasilia": elas nao sao municipios, e sim Regioes Administrativas
# criadas pela legislacao distrital. O IBGE reconhece no DF exatamente um
# municipio (5300108, "Brasilia") e um distrito -- o que se verifica chamando
# .../localidades/estados/53/municipios. As 35 RAs existem no IBGE apenas como
# SUBDISTRITOS (ver RAS_DF abaixo), um nivel para o qual nao ha dado semanal de
# dengue publicado: o InfoDengue opera somente no nivel municipal e devolve
# lista vazia para esses codigos.
DISTRITO_FEDERAL = {5300108: "Brasilia"}

# As 35 Regioes Administrativas, na codificacao de subdistrito do IBGE.
# Nao entram na base analitica por falta de serie epidemiologica semanal nesse
# nivel; ficam registradas porque delimitam o desdobramento intraurbano mais
# valioso do projeto, caso a Secretaria de Saude do DF ceda os dados por RA.
RAS_DF = {
    53001080506: "Plano Piloto",
    53001080507: "Gama",
    53001080508: "Taguatinga",
    53001080509: "Brazlandia",
    53001080510: "Sobradinho",
    53001080511: "Planaltina",
    53001080512: "Paranoa",
    53001080513: "Riacho Fundo",
    53001080514: "Nucleo Bandeirante",
    53001080515: "Ceilandia",
    53001080516: "Guara",
    53001080517: "Cruzeiro",
    53001080518: "Samambaia",
    53001080519: "Candangolandia",
    53001080520: "Recanto das Emas",
    53001080521: "Lago Norte",
    53001080523: "Lago Sul",
    53001080525: "Santa Maria",
    53001080530: "Sao Sebastiao",
    53001080531: "Sol Nascente/Por do Sol",
    53001080532: "Arniqueira",
    53001080533: "SIA",
    53001080534: "SCIA",
    53001080535: "Sudoeste/Octogonal",
    53001080536: "Aguas Claras",
    53001080537: "Vicente Pires",
    53001080538: "Itapoa",
    53001080539: "Fercal",
    53001080540: "Jardim Botanico",
    53001080541: "Riacho Fundo II",
    53001080542: "Park Way",
    53001080543: "Varjao",
    53001080544: "Sobradinho II",
    53001080545: "Arapoanga",
    53001080546: "Agua Quente",
}

RIDE_GO = {
    5200100: "Abadiania",
    5200175: "Agua Fria de Goias",
    5200258: "Aguas Lindas de Goias",
    5200308: "Alexania",
    5200605: "Alto Paraiso de Goias",
    5200803: "Alvorada do Norte",
    5203203: "Barro Alto",
    5204003: "Cabeceiras",
    5205307: "Cavalcante",
    5205497: "Cidade Ocidental",
    5205513: "Cocalzinho de Goias",
    5205802: "Corumba de Goias",
    5206206: "Cristalina",
    5207907: "Flores de Goias",
    5208004: "Formosa",
    5208608: "Goianesia",
    5212501: "Luziania",
    5213053: "Mimoso de Goias",
    5214606: "Niquelandia",
    5215231: "Novo Gama",
    5215603: "Padre Bernardo",
    5217302: "Pirenopolis",
    5217609: "Planaltina",
    5219753: "Santo Antonio do Descoberto",
    5220009: "Sao Joao d'Alianca",
    5220686: "Simolandia",
    5221858: "Valparaiso de Goias",
    5222203: "Vila Boa",
    5222302: "Vila Propicio",
}

RIDE_MG = {
    3109303: "Buritis",
    3109451: "Cabeceira Grande",
    3170404: "Unai",
}

TERRITORIO = {**DISTRITO_FEDERAL, **RIDE_GO, **RIDE_MG}

UF_POR_CODIGO = {
    **{c: "DF" for c in DISTRITO_FEDERAL},
    **{c: "GO" for c in RIDE_GO},
    **{c: "MG" for c in RIDE_MG},
}


def normalizar(texto: str) -> str:
    """Remove acentos e padroniza caixa, para comparar nomes de municipio."""
    if texto is None:
        return ""
    decomposto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in decomposto if not unicodedata.combining(c)).strip().upper()


def municipios_uf(uf: str) -> dict[int, str]:
    """Retorna {codigo_ibge: nome} de todos os municipios de uma UF."""
    resposta = requests.get(f"{IBGE_LOCALIDADES}/estados/{uf}/municipios", timeout=90)
    resposta.raise_for_status()
    return {int(m["id"]): m["nome"] for m in resposta.json()}


def validar_territorio() -> list[str]:
    """Confere cada codigo do territorio contra a API do IBGE.

    Retorna a lista de divergencias encontradas; lista vazia significa que
    todos os codigos existem e correspondem ao nome declarado.
    """
    divergencias: list[str] = []
    oficiais: dict[int, str] = {}
    for uf in ("DF", "GO", "MG"):
        oficiais.update(municipios_uf(uf))

    for codigo, nome in TERRITORIO.items():
        oficial = oficiais.get(codigo)
        if oficial is None:
            divergencias.append(f"{codigo} ({nome}): codigo inexistente no IBGE")
        elif normalizar(oficial).replace("'", "") != normalizar(nome).replace("'", ""):
            divergencias.append(f"{codigo}: declarado '{nome}', IBGE diz '{oficial}'")
    return divergencias
