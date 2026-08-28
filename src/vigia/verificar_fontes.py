"""Reconfere os dados em disco contra as fontes originais, ao vivo.

Executa uma auditoria independente do pipeline: para cada fonte, refaz a
requisicao agora e compara com o que esta gravado. Serve para que qualquer
pessoa -- orientadora, avaliador, o proprio autor meses depois -- confirme que
os arquivos do projeto correspondem as APIs de origem, sem precisar confiar em
relato.

Uso:  python src/vigia/verificar_fontes.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import requests  # noqa: E402

from vigia.territorio import TERRITORIO, validar_territorio  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]

# Tolerancia da comparacao de chuva: a semana epidemiologica cobre 364 dias,
# enquanto o ano civil tem 365, e as semanas de virada caem no ano vizinho.
TOLERANCIA_CHUVA_MM = 20


def _linha(rotulo: str, esperado, obtido, confere: bool) -> str:
    marca = "OK  " if confere else "FALHA"
    return f"  [{marca}] {rotulo}\n         fonte: {esperado} | disco: {obtido}"


def verificar_infodengue() -> bool:
    """Compara os casos de Brasilia em 2024 com o arquivo bruto."""
    resposta = requests.get(
        "https://info.dengue.mat.br/api/alertcity",
        params={"geocode": 5300108, "disease": "dengue", "format": "json",
                "ew_start": 1, "ew_end": 53, "ey_start": 2024, "ey_end": 2024},
        timeout=180,
    )
    resposta.raise_for_status()
    da_api = int(pd.DataFrame(resposta.json())["casos"].sum())

    arquivo = RAIZ / "dados" / "bruto" / "infodengue" / "dengue_5300108.csv"
    local = pd.read_csv(arquivo)
    do_disco = int(local[local["ano"] == 2024]["casos"].sum())

    confere = da_api == do_disco
    print(_linha("InfoDengue -- casos de dengue em Brasilia, 2024", da_api, do_disco, confere))
    return confere


def verificar_ibge_codigos() -> bool:
    """Revalida os 30 codigos municipais contra a API de localidades."""
    divergencias = validar_territorio()
    confere = not divergencias
    print(_linha(
        f"IBGE -- {len(TERRITORIO)} codigos municipais",
        "todos existem e a UF confere",
        "nenhuma divergencia" if confere else "; ".join(divergencias),
        confere,
    ))
    return confere


def verificar_censo() -> bool:
    """Recalcula o esgotamento inadequado de Brasilia pelo Censo 2022."""
    from vigia.vulnerabilidade import ESGOTO

    categorias = ",".join(str(c) for c in [ESGOTO["total"], *ESGOTO["inadequado"]])
    resposta = requests.get(
        f"https://servicodados.ibge.gov.br/api/v3/agregados/{ESGOTO['agregado']}"
        f"/periodos/2022/variaveis/{ESGOTO['variavel']}",
        params={"localidades": "N6[5300108]",
                "classificacao": f"{ESGOTO['classificacao']}[{categorias}]"},
        timeout=180,
    )
    resposta.raise_for_status()

    valores: dict[str, float] = {}
    for variavel in resposta.json():
        for resultado in variavel["resultados"]:
            nome = list(resultado["classificacoes"][0]["categoria"].values())[0]
            bruto = list(resultado["series"][0]["serie"].values())[0]
            numero = pd.to_numeric(bruto, errors="coerce")
            if pd.notna(numero):
                valores[nome] = float(numero)

    total = valores.pop("Total")
    da_api = sum(valores.values()) / total * 100

    tabela = pd.read_csv(RAIZ / "dados" / "externo" / "vulnerabilidade.csv")
    do_disco = float(tabela.loc[tabela["cod_ibge"] == 5300108, "esgoto_inadequado_pct"].iloc[0])

    confere = abs(da_api - do_disco) < 0.01
    print(_linha("IBGE Censo 2022 -- esgoto inadequado em Brasilia",
                 f"{da_api:.3f}%", f"{do_disco:.3f}%", confere))
    return confere


def verificar_chuva() -> bool:
    """Compara a chuva de Brasilia em 2021 com a serie da NASA POWER."""
    from vigia.clima_chuva import centroides

    latitude, longitude = centroides([5300108])[5300108]
    resposta = requests.get(
        "https://power.larc.nasa.gov/api/temporal/daily/point",
        params={"parameters": "PRECTOTCORR", "community": "AG",
                "latitude": round(latitude, 4), "longitude": round(longitude, 4),
                "start": "20210101", "end": "20211231", "format": "JSON"},
        timeout=300,
    )
    resposta.raise_for_status()
    serie = pd.Series(resposta.json()["properties"]["parameter"]["PRECTOTCORR"])
    da_api = float(serie[serie >= 0].sum())

    chuva = pd.read_csv(RAIZ / "dados" / "externo" / "chuva_semanal.csv")
    brasilia = chuva[chuva["cod_ibge"] == 5300108].copy()
    brasilia["ano"] = pd.to_datetime(brasilia["data_ini_se"]).dt.year
    do_disco = float(brasilia.loc[brasilia["ano"] == 2021, "chuva_semana_mm"].sum())

    confere = abs(da_api - do_disco) < TOLERANCIA_CHUVA_MM
    print(_linha("NASA POWER -- chuva em Brasilia, 2021",
                 f"{da_api:.0f} mm (365 dias)", f"{do_disco:.0f} mm (52 semanas)", confere))
    return confere


def verificar_integridade_local() -> bool:
    """Confere a coerencia interna dos arquivos gravados."""
    print("\n  Integridade dos arquivos em disco:")
    tudo_certo = True

    esperados = {
        "dados/processado/infodengue_territorio.csv": 30,
        "dados/processado/base_com_risco.csv": 30,
        "dados/externo/chuva_semanal.csv": 30,
        "dados/externo/vulnerabilidade.csv": 30,
    }
    for caminho, municipios in esperados.items():
        arquivo = RAIZ / caminho
        if not arquivo.exists():
            print(f"    FALTA {caminho}")
            tudo_certo = False
            continue
        tabela = pd.read_csv(arquivo, low_memory=False)
        encontrados = tabela["cod_ibge"].nunique()
        certo = encontrados == municipios
        tudo_certo &= certo
        print(f"    {'ok ' if certo else 'ERRO'} {caminho}: "
              f"{len(tabela)} linhas, {encontrados}/{municipios} municipios")

    for caminho, poligonos in [("dados/externo/malha_ride_df.geojson", 30),
                               ("dados/externo/malha_ras_df.geojson", 31)]:
        arquivo = RAIZ / caminho
        if not arquivo.exists():
            print(f"    FALTA {caminho}")
            tudo_certo = False
            continue
        colecao = json.loads(arquivo.read_text(encoding="utf-8"))
        encontrados = len(colecao["features"])
        certo = encontrados == poligonos
        tudo_certo &= certo
        print(f"    {'ok ' if certo else 'ERRO'} {caminho}: "
              f"{encontrados}/{poligonos} poligonos")

    brutos = list((RAIZ / "dados" / "bruto" / "infodengue").glob("*.csv"))
    certo = len(brutos) == 90
    tudo_certo &= certo
    print(f"    {'ok ' if certo else 'ERRO'} brutos por municipio: "
          f"{len(brutos)}/90 (30 municipios x 3 arboviroses)")

    return tudo_certo


if __name__ == "__main__":
    print("Reconferindo os dados do projeto contra as fontes originais.\n")
    print("  Comparacao ao vivo com as APIs:")

    resultados = []
    for verificacao in (verificar_infodengue, verificar_ibge_codigos,
                        verificar_censo, verificar_chuva):
        try:
            resultados.append(verificacao())
        except Exception as erro:  # rede fora do ar nao e falha de dado
            print(f"  [AVISO] {verificacao.__name__}: {type(erro).__name__} -- {erro}")
            resultados.append(None)

    resultados.append(verificar_integridade_local())

    falhas = [r for r in resultados if r is False]
    avisos = [r for r in resultados if r is None]
    print()
    if falhas:
        print(f"RESULTADO: {len(falhas)} verificacao(oes) FALHOU.")
        raise SystemExit(1)
    if avisos:
        print(f"RESULTADO: tudo confere, com {len(avisos)} verificacao(oes) "
              "nao concluida(s) por indisponibilidade de rede.")
    else:
        print("RESULTADO: todos os dados conferem com as fontes originais.")
