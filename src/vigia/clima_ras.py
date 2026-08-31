"""Clima semanal por Regiao Administrativa do Distrito Federal.

Por que este modulo existe
--------------------------
Nao ha serie semanal de casos de dengue por RA -- `ras_df.py` documenta a busca
pelas fontes e o porque de nenhuma servir. Por isso o mapa intraurbano do painel
nunca passou de uma camada populacional.

Clima, porem, e medido. A reanalise ERA5, servida pelo Open-Meteo, cobre o
Distrito Federal numa grade de cerca de 11 km, que resolve 22 celulas distintas
para as 31 RAs. A diferenca entre elas nao e ruido: em 2024 a chuva anual foi de
1.129 mm no Cruzeiro e 1.430 mm em Santa Maria -- 27% de diferenca dentro do
mesmo municipio.

Esta serie alimenta `peso_ras.py`, que da a cada RA um peso proprio a partir de
condicao ambiental medida no proprio lugar. E o contrario de repartir os casos
de Brasilia na proporcao da populacao, que `ras_df.py` adverte a nao fazer: ali
o mapa apenas repintaria o mapa populacional; aqui ele carrega informacao que
nao estava no denominador.

LIMITE CONHECIDO
----------------
Nove RAs centrais dividem celula da grade com uma vizinha -- Cruzeiro,
Sudoeste/Octogonal, SIA e SCIA caem todas na mesma -- e nesse caso recebem
clima identico. A coluna `celula_era5` registra qual celula serviu cada RA, para
que o painel possa dizer quando duas RAs nao se distinguem pelo clima.

Uso:  python src/vigia/executar_clima_ras.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[2]
MALHA_RAS = RAIZ / "dados" / "externo" / "malha_ras_df.geojson"
DESTINO = RAIZ / "dados" / "externo" / "clima_ras.csv"

ARQUIVO_HISTORICO = "https://archive-api.open-meteo.com/v1/archive"

# As mesmas variaveis que o bloco climatico do modelo consome, na nomenclatura
# do Open-Meteo. A umidade relativa media fecha o par com a temperatura: sao as
# duas grandezas que o InfoDengue publica por municipio.
DIARIAS = [
    "temperature_2m_mean",
    "temperature_2m_min",
    "temperature_2m_max",
    "relative_humidity_2m_mean",
    "precipitation_sum",
]

RENOMEAR = {
    "temperature_2m_mean": "tempmed",
    "temperature_2m_min": "tempmin",
    "temperature_2m_max": "tempmax",
    "relative_humidity_2m_mean": "umidmed",
    "precipitation_sum": "chuva_dia_mm",
}


def centroides() -> pd.DataFrame:
    """Centro geometrico de cada RA, a partir da malha de subdistritos.

    Usa o centro da caixa envolvente, e nao o centroide de area: e o mesmo
    criterio de `clima_chuva.centroides`, o que mantem as duas coletas
    comparaveis.
    """
    malha = json.loads(MALHA_RAS.read_text(encoding="utf-8"))
    linhas = []
    for feicao in malha["features"]:
        longitudes: list[float] = []
        latitudes: list[float] = []

        def percorrer(no) -> None:
            if isinstance(no, list) and no and isinstance(no[0], (int, float)):
                longitudes.append(no[0])
                latitudes.append(no[1])
            elif isinstance(no, list):
                for parte in no:
                    percorrer(parte)

        percorrer(feicao["geometry"]["coordinates"])
        propriedades = feicao["properties"]
        linhas.append({
            "ra_nome": propriedades["ra_nome"],
            "cod_subdistrito": propriedades["cod_subdistrito"],
            "populacao": propriedades["populacao"],
            "latitude": (min(latitudes) + max(latitudes)) / 2,
            "longitude": (min(longitudes) + max(longitudes)) / 2,
        })
    return pd.DataFrame(linhas)


def _baixar_bloco(centros: pd.DataFrame, inicio: str, fim: str) -> list[dict]:
    """Uma requisicao com todas as RAs de uma vez, num intervalo de tempo.

    O Open-Meteo aceita listas de coordenadas e devolve um objeto por ponto, na
    mesma ordem -- trinta e uma chamadas separadas levariam cerca de 45 minutos,
    e esta leva segundos. O corte e no tempo porque o servidor recusa a
    combinacao de muitas coordenadas com muitos anos ("requests too much data").
    """
    parametros = {
        "latitude": ",".join(f"{v:.4f}" for v in centros["latitude"]),
        "longitude": ",".join(f"{v:.4f}" for v in centros["longitude"]),
        "start_date": inicio,
        "end_date": fim,
        "daily": ",".join(DIARIAS),
        "timezone": "UTC",
    }
    # O Open-Meteo mede a cota pelo volume, nao pelo numero de chamadas: um
    # pedido com 31 pontos e varios anos consome muitas unidades e devolve 429.
    # Esperar e repetir e o comportamento pedido pelo servico.
    for tentativa in range(8):
        resposta = requests.get(ARQUIVO_HISTORICO, params=parametros, timeout=600)
        if resposta.status_code != 429:
            resposta.raise_for_status()
            corpo = resposta.json()
            return corpo if isinstance(corpo, list) else [corpo]

        # O servico distingue dois limites: o de minuto, que passa em segundos,
        # e o horario, que so libera na virada da hora. Esperar 5 minutos entre
        # tentativas cobre os dois sem martelar o servidor.
        horario = "hourly" in resposta.text.lower()
        espera = 300 if horario else 30 * (tentativa + 1)
        print(f"    cota {'horaria' if horario else 'de minuto'} atingida; "
              f"aguardando {espera}s (tentativa {tentativa + 1}/8)")
        time.sleep(espera)

    raise RuntimeError(
        "Open-Meteo manteve o limite de taxa por mais de 40 minutos. "
        "Rode de novo mais tarde: a coleta e retomavel."
    )


def _baixar(centros: pd.DataFrame, inicio: str, fim: str,
            anos_por_bloco: int = 2) -> list[pd.DataFrame]:
    """Percorre o periodo em blocos e devolve a serie diaria de cada RA."""
    limites = pd.date_range(inicio, fim, freq=pd.DateOffset(years=anos_por_bloco))
    limites = list(limites) + [pd.Timestamp(fim)]

    por_ra: dict[str, list[pd.DataFrame]] = {}
    celulas: dict[str, str] = {}

    for principio, termino in zip(limites, limites[1:]):
        if principio >= termino:
            continue
        janela = (principio.strftime("%Y-%m-%d"), termino.strftime("%Y-%m-%d"))
        print(f"  {janela[0]} a {janela[1]}...")
        resultados = _baixar_bloco(centros, *janela)

        for (_, ra), ponto in zip(centros.iterrows(), resultados):
            pedaco = pd.DataFrame(ponto["daily"]).rename(
                columns={**RENOMEAR, "time": "data"}
            )
            pedaco["ra_nome"] = ra["ra_nome"]
            por_ra.setdefault(ra["ra_nome"], []).append(pedaco)
            # A grade do ERA5 encaixa o pedido na celula mais proxima; guardar a
            # celula devolvida e o que permite saber quais RAs nao se distinguem.
            celulas[ra["ra_nome"]] = (
                f"{ponto['latitude']:.4f},{ponto['longitude']:.4f}"
            )

    diarios = []
    for nome, pedacos in por_ra.items():
        serie = pd.concat(pedacos, ignore_index=True).drop_duplicates("data")
        serie["celula_era5"] = celulas[nome]
        diarios.append(serie)
    return diarios


def agregar_semana_epidemiologica(diario: pd.DataFrame) -> pd.DataFrame:
    """Converte a serie diaria em semana epidemiologica.

    A semana epidemiologica brasileira comeca no domingo, e o rotulo e a data
    desse domingo -- o mesmo criterio de `data_ini_se` do InfoDengue, o que
    garante o encaixe exato com a base municipal.
    """
    dados = diario.copy()
    dados["data"] = pd.to_datetime(dados["data"])
    dados["data_ini_se"] = dados["data"] - pd.to_timedelta(
        (dados["data"].dt.weekday + 1) % 7, unit="D"
    )

    semanal = dados.groupby(["ra_nome", "data_ini_se"], as_index=False).agg(
        tempmed=("tempmed", "mean"),
        tempmin=("tempmin", "min"),
        tempmax=("tempmax", "max"),
        umidmed=("umidmed", "mean"),
        chuva_semana_mm=("chuva_dia_mm", "sum"),
        chuva_dias_com_chuva=("chuva_dia_mm", lambda s: int((s >= 1.0).sum())),
        chuva_max_diaria_mm=("chuva_dia_mm", "max"),
        dias_no_periodo=("chuva_dia_mm", "size"),
    )

    # Semanas incompletas nas bordas da serie nao representam o total real.
    completas = semanal[semanal["dias_no_periodo"] == 7].drop(columns="dias_no_periodo")
    return completas.reset_index(drop=True)


def coletar(inicio: str = "2014-01-01", fim: str | None = None,
            destino: Path | None = DESTINO) -> pd.DataFrame:
    """Baixa e agrega o clima semanal das 31 Regioes Administrativas."""
    if fim is None:
        fim = (pd.Timestamp.today() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")

    centros = centroides()
    print(f"coletando clima de {len(centros)} Regioes Administrativas "
          f"({inicio} a {fim})...")

    diario = pd.concat(_baixar(centros, inicio, fim), ignore_index=True)
    semanal = agregar_semana_epidemiologica(diario)

    celulas = diario.drop_duplicates("ra_nome")[["ra_nome", "celula_era5"]]
    semanal = semanal.merge(celulas, on="ra_nome", how="left")
    semanal = semanal.merge(
        centros[["ra_nome", "cod_subdistrito", "populacao"]], on="ra_nome", how="left"
    )

    distintas = semanal["celula_era5"].nunique()
    print(f"{len(semanal)} linhas | {semanal['ra_nome'].nunique()} RAs | "
          f"{distintas} celulas distintas do ERA5")

    if destino is not None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        semanal.to_csv(destino, index=False)
        print(f"gravado em {destino}")
    return semanal


if __name__ == "__main__":
    coletar()
