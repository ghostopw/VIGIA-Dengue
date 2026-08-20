"""Monta o pacote de dados do projeto para uso externo e arquivamento.

Reune tudo o que foi coletado e processado em `dados/pacote/`, acompanhado de
um manifesto que descreve cada arquivo, sua origem e sua contagem de linhas.
O objetivo e que o pacote possa ser entregue, versionado ou anexado a um
relatorio sem depender do restante do repositorio.
"""

from __future__ import annotations

import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
PACOTE = RAIZ / "dados" / "pacote"

ARQUIVOS = [
    ("dados/processado/infodengue_territorio.csv", "dengue_municipio_semana.csv",
     "Dengue: serie municipio-semana bruta do InfoDengue, 2014-2026."),
    ("dados/processado/chikungunya_territorio.csv", "chikungunya_municipio_semana.csv",
     "Chikungunya: serie municipio-semana bruta do InfoDengue, 2016-2026."),
    ("dados/processado/zika_territorio.csv", "zika_municipio_semana.csv",
     "Zika: serie municipio-semana bruta do InfoDengue, 2016-2026."),
    ("dados/processado/base_analitica.csv", "base_analitica.csv",
     "Tabela analitica: incidencia, medias moveis, defasagens e flags."),
    ("dados/processado/base_com_risco.csv", "base_com_risco.csv",
     "Base analitica acrescida do canal endemico e da estratificacao de risco."),
    ("dados/processado/painel.csv", "painel.csv",
     "Base do painel: probabilidade de alerta e fatores explicativos."),
    ("dados/externo/malha_ride_df.geojson", "malha_municipios.geojson",
     "Malha cartografica dos 33 municipios (IBGE)."),
    ("saidas/desempenho_modelos.csv", "desempenho_modelos.csv",
     "Metricas da validacao temporal dos tres modelos, por ano."),
]


def descrever(caminho: Path) -> tuple[int, int]:
    """Retorna (linhas, colunas) de um CSV; (0, 0) para outros formatos."""
    if caminho.suffix != ".csv":
        return 0, 0
    tabela = pd.read_csv(caminho, low_memory=False)
    return len(tabela), tabela.shape[1]


def montar() -> Path:
    PACOTE.mkdir(parents=True, exist_ok=True)
    linhas_manifesto = [
        "# Pacote de dados -- VIGIA-Dengue",
        "",
        f"Gerado em {date.today().isoformat()}.",
        "",
        "Territorio: Distrito Federal e RIDE-DF (33 municipios).",
        "Unidade de analise: municipio x semana epidemiologica.",
        "",
        "Fontes:",
        "- InfoDengue (Fiocruz/FGV) -- API alertcity: casos, casos estimados por",
        "  nowcasting, incidencia, Rt e clima semanal.",
        "- IBGE -- APIs de localidades e de malhas: populacao e cartografia.",
        "",
        "| Arquivo | Linhas | Colunas | Conteudo |",
        "|---|---|---|---|",
    ]

    for origem_relativa, nome_destino, descricao in ARQUIVOS:
        origem = RAIZ / origem_relativa
        if not origem.exists():
            print(f"  ausente, ignorado: {origem_relativa}")
            continue
        destino = PACOTE / nome_destino
        shutil.copy2(origem, destino)
        linhas, colunas = descrever(destino)
        medida = f"{linhas:,}".replace(",", ".") if linhas else "-"
        linhas_manifesto.append(
            f"| `{nome_destino}` | {medida} | {colunas or '-'} | {descricao} |"
        )
        print(f"  {nome_destino}")

    # Copia tambem os brutos por municipio, que preservam o retorno original da API.
    brutos = PACOTE / "brutos_por_municipio"
    brutos.mkdir(exist_ok=True)
    for arquivo in sorted((RAIZ / "dados" / "bruto" / "infodengue").glob("*.csv")):
        shutil.copy2(arquivo, brutos / arquivo.name)
    quantidade = len(list(brutos.glob("*.csv")))
    linhas_manifesto.append(
        f"| `brutos_por_municipio/` | - | - | {quantidade} CSVs: retorno original "
        "da API, um por municipio e arbovirose. |"
    )

    linhas_manifesto += [
        "",
        "## Dicionario das variaveis",
        "",
        "A descricao completa das 105 variaveis da base analitica esta em",
        "`docs/dicionario_de_dados.md` no repositorio do projeto.",
        "",
        "## Observacoes de uso",
        "",
        "- **Use `casos_est`, nao `casos`, para semanas recentes.** As ultimas semanas",
        "  vem subnotificadas por atraso de digitacao; `casos_est` corrige isso por",
        "  nowcasting. A coluna `dado_provisorio` sinaliza as linhas afetadas.",
        "- **`casos` x `casprov`.** `casos` conta todas as notificacoes; `casprov` conta",
        "  casos provaveis (descartados excluidos), que e o conceito usado nos boletins",
        "  do Ministerio da Saude.",
        "- **Chave de integracao:** `cod_ibge` + `se_codigo`.",
    ]

    manifesto = PACOTE / "MANIFESTO.md"
    manifesto.write_text("\n".join(linhas_manifesto), encoding="utf-8")

    caminho_zip = RAIZ / "dados" / "vigia_dengue_dados.zip"
    with zipfile.ZipFile(caminho_zip, "w", zipfile.ZIP_DEFLATED) as compactado:
        for arquivo in PACOTE.rglob("*"):
            if arquivo.is_file():
                compactado.write(arquivo, arquivo.relative_to(PACOTE))

    return caminho_zip


if __name__ == "__main__":
    print("montando o pacote...")
    caminho_zip = montar()
    tamanho = caminho_zip.stat().st_size / 1024 / 1024
    print(f"\npacote: {PACOTE}")
    print(f"zip:    {caminho_zip} ({tamanho:.1f} MB)")
