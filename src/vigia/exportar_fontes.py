"""Gera a lista das URLs de origem de cada arquivo bruto do projeto.

Documento de proveniencia: permite a qualquer pessoa refazer, uma a uma, as
requisicoes que produziram os dados, sem precisar executar o pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from vigia.ingestao_infodengue import API  # noqa: E402
from vigia.malha import MALHA_MUNICIPIO  # noqa: E402
from vigia.territorio import (  # noqa: E402
    IBGE_LOCALIDADES,
    TERRITORIO,
    UF_POR_CODIGO,
)

RAIZ = Path(__file__).resolve().parents[2]
ANO_INICIO = 2014
ANO_FIM = 2026
DOENCAS = ["dengue", "chikungunya", "zika"]


def url_infodengue(geocode: int, doenca: str) -> str:
    return (
        f"{API}?geocode={geocode}&disease={doenca}&format=json"
        f"&ew_start=1&ew_end=53&ey_start={ANO_INICIO}&ey_end={ANO_FIM}"
    )


def montar() -> pd.DataFrame:
    linhas = []
    for geocode, nome in sorted(TERRITORIO.items(), key=lambda item: item[1]):
        for doenca in DOENCAS:
            linhas.append({
                "municipio": nome,
                "uf": UF_POR_CODIGO[geocode],
                "cod_ibge": geocode,
                "fonte": "InfoDengue",
                "conteudo": f"{doenca}: serie municipio-semana {ANO_INICIO}-{ANO_FIM}",
                "arquivo_local": f"dados/bruto/infodengue/{doenca}_{geocode}.csv",
                "url": url_infodengue(geocode, doenca),
            })
        linhas.append({
            "municipio": nome,
            "uf": UF_POR_CODIGO[geocode],
            "cod_ibge": geocode,
            "fonte": "IBGE",
            "conteudo": "malha cartografica municipal (GeoJSON)",
            "arquivo_local": "dados/externo/malha_ride_df.geojson",
            "url": (
                MALHA_MUNICIPIO.format(codigo=geocode)
                + "?formato=application/vnd.geo+json&qualidade=intermediaria"
            ),
        })
    return pd.DataFrame(linhas)


def escrever_markdown(tabela: pd.DataFrame, destino: Path) -> None:
    partes = [
        "# Proveniencia dos dados -- VIGIA-Dengue",
        "",
        "Todo dado bruto do projeto veio de API publica, sem autenticacao.",
        "Cada URL abaixo pode ser aberta no navegador e devolve exatamente o",
        "conteudo que gerou o arquivo local correspondente.",
        "",
        "## Cadeia de origem",
        "",
        "```",
        "SINAN (Ministerio da Saude)",
        "   |  notificacoes de dengue, chikungunya e zika",
        "   v",
        "InfoDengue (Fiocruz + FGV EMAp)",
        "   |  repasse semanal do SINAN; aplica nowcasting do atraso de notificacao",
        "   v",
        "API publica alertcity  -->  dados/bruto/infodengue/ (99 arquivos)",
        "```",
        "",
        "## Portais das fontes",
        "",
        "| Fonte | Portal | Documentacao |",
        "|---|---|---|",
        "| InfoDengue | https://info.dengue.mat.br | https://info.dengue.mat.br/services/api |",
        "| IBGE -- localidades | https://servicodados.ibge.gov.br/api/docs/localidades | "
        f"{IBGE_LOCALIDADES} |",
        "| IBGE -- malhas | https://servicodados.ibge.gov.br/api/docs/malhas | "
        "https://servicodados.ibge.gov.br/api/v3/malhas |",
        "",
        "## Foco do projeto: Brasilia (DF)",
        "",
        "| Arbovirose | URL |",
        "|---|---|",
    ]
    for doenca in DOENCAS:
        partes.append(f"| {doenca} | {url_infodengue(5300108, doenca)} |")

    partes += [
        "",
        f"## Todas as requisicoes ({len(tabela)})",
        "",
        "| Municipio | UF | Fonte | Conteudo | URL |",
        "|---|---|---|---|---|",
    ]
    for _, linha in tabela.iterrows():
        partes.append(
            f"| {linha['municipio']} | {linha['uf']} | {linha['fonte']} | "
            f"{linha['conteudo']} | {linha['url']} |"
        )

    partes += [
        "",
        "## Como reconferir",
        "",
        "Abrir qualquer URL da tabela no navegador, ou:",
        "",
        "```bash",
        "curl 'https://info.dengue.mat.br/api/alertcity?geocode=5300108&disease=dengue"
        "&format=json&ew_start=1&ew_end=53&ey_start=2024&ey_end=2024'",
        "```",
        "",
        "Para refazer toda a coleta do zero:",
        "",
        "```bash",
        "python src/vigia/executar_ingestao.py      # dengue, 33 municipios",
        "python src/vigia/executar_arboviroses.py   # chikungunya e zika",
        "python src/vigia/executar_malha.py         # malha cartografica",
        "```",
    ]
    destino.write_text("\n".join(partes), encoding="utf-8")


if __name__ == "__main__":
    tabela = montar()
    destino_csv = RAIZ / "docs" / "fontes_dos_dados.csv"
    destino_md = RAIZ / "docs" / "fontes_dos_dados.md"
    destino_csv.parent.mkdir(parents=True, exist_ok=True)

    tabela.to_csv(destino_csv, index=False, encoding="utf-8")
    escrever_markdown(tabela, destino_md)

    print(f"{len(tabela)} requisicoes documentadas")
    print(f"  {destino_md}")
    print(f"  {destino_csv}")
