"""Gera os dados do site do VIGIA-Dengue (vigia.guimm.site).

O site e estatico: uma pagina (site/index.html), o estilo e o JavaScript, que
leem um unico arquivo de dados, `dados/painel.json`. Este modulo monta esse
arquivo a partir do que o repositorio versiona -- o painel.csv do ciclo diario,
os alarmes, a previsao do tempo, as malhas, a vulnerabilidade das RAs e o
dicionario de dados. Roda no build da imagem (Dockerfile) e no servidor local
(app/servidor.py); nao ha copia manual em lugar nenhum.

Regra da casa: todo numero que o site escreve sai daqui, medido nos dados da
semana. A pagina nao traz numero fixo no texto.

Dois conjuntos vao em arquivos a parte, que o navegador so baixa quando
alguem pede: o mapa por quadra (`dados/setores.json`) e a serie completa de
cada municipio (`dados/municipios/<codigo>.json`), que alimenta o panorama,
as series e o relatorio de quem escolhe um municipio que nao e Brasilia.

Uso:  python src/vigia/exportar_site.py              (grava em site/dados/)
      python src/vigia/exportar_site.py --destino X
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "site" / "dados"

COD_FOCO = 5300108
ORDEM_RISCO = ["baixo", "moderado", "alto", "muito alto"]

# Limiar do alerta operacional. Em 0,50 o alerta disparava 47 semanas por ano
# em Brasilia (especificidade de 19%); em 0,80 dispara ~34 vezes e acerta 9 de
# cada 10 (docs/achados_modelagem.md, secoes 7 e 8).
LIMIAR_ALERTA = 0.80
# VPP do modelo combinado em Brasilia nesse limiar, validacao temporal
# 2019-2025 (achados_modelagem.md, secao 8). Vale so para Brasilia e so para
# este limiar; os demais municipios mostram a AUC do territorio.
VPP_BRASILIA = 0.902
# Peso do LightGBM no modelo combinado (o resto vai para a persistencia). E o
# mesmo de modelagem.PESO_BOOSTING; o teste test_site.py garante que nao
# divergem. Fica copiado aqui para o build da imagem nao precisar do lightgbm.
PESO_BOOSTING = 0.8

SEMANAS_FICHA = 12      # o "semana a semana" de cada municipio
# Probabilidades e completude vao com 6 casas, e nao 3: a pagina arredonda
# para porcentagem inteira, e arredondar duas vezes erra a meia unidade
# (0,1549 viraria 0,155 e depois 16%, quando o certo e 15%).
CASAS_PROB = 6
# Casas das coordenadas das quadras: 5 casas sao ~1 m no chao, mais que o
# bastante para desenhar quadra, e cortam o arquivo pela metade.
CASAS_COORD = 5

# Brasilia nao tem horario de verao desde 2019: o deslocamento e fixo.
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# A base grava os nomes em ASCII de proposito; a tela fala portugues.
GRAFIA = {
    "Brasilia": "Brasília", "Abadiania": "Abadiânia",
    "Agua Fria de Goias": "Água Fria de Goiás",
    "Aguas Lindas de Goias": "Águas Lindas de Goiás", "Alexania": "Alexânia",
    "Alto Paraiso de Goias": "Alto Paraíso de Goiás",
    "Cocalzinho de Goias": "Cocalzinho de Goiás",
    "Corumba de Goias": "Corumbá de Goiás", "Flores de Goias": "Flores de Goiás",
    "Goianesia": "Goianésia", "Luziania": "Luziânia",
    "Mimoso de Goias": "Mimoso de Goiás", "Niquelandia": "Niquelândia",
    "Pirenopolis": "Pirenópolis",
    "Santo Antonio do Descoberto": "Santo Antônio do Descoberto",
    "Sao Joao d'Alianca": "São João d'Aliança", "Simolandia": "Simolândia",
    "Unai": "Unaí", "Valparaiso de Goias": "Valparaíso de Goiás",
    "Vila Propicio": "Vila Propício",
    "Aguas Claras": "Águas Claras", "Brazlandia": "Brazlândia",
    "Candangolandia": "Candangolândia", "Ceilandia": "Ceilândia",
    "Guara": "Guará", "Itapoa": "Itapoã", "Jardim Botanico": "Jardim Botânico",
    "Nucleo Bandeirante": "Núcleo Bandeirante", "Paranoa": "Paranoá",
    "Sao Sebastiao": "São Sebastião", "Varjao": "Varjão",
}

FATORES = {
    "incidencia_100k": "incidência da semana",
    "incidencia_lag1": "incidência de 1 semana atrás",
    "incidencia_lag2": "incidência de 2 semanas atrás",
    "incidencia_lag4": "incidência de 4 semanas atrás",
    "incidencia_mm3": "incidência média de 3 semanas",
    "incidencia_mm8": "incidência média de 8 semanas",
    "casos_est_mm3": "casos das últimas 3 semanas",
    "casos_est_mm8": "casos das últimas 8 semanas",
    "razao_mm3_mm8": "aceleração da curva",
    "variacao_semanal": "variação semanal",
    "log_pop": "porte do município",
    "semana": "época do ano",
    "canal_mediana": "padrão histórico da época",
    "canal_q3": "limite esperado da época",
    "Rt": "ritmo de transmissão (Rt)",
    "p_rt1": "chance de transmissão crescente",
    "receptivo": "clima receptivo ao mosquito",
    "transmissao": "transmissão sustentada",
    "nivel_inc": "nível de incidência",
    "Rt_lag1": "Rt de 1 semana atrás",
    "Rt_lag2": "Rt de 2 semanas atrás",
    "p_rt1_lag1": "chance de transmissão crescente 1 semana atrás",
    "p_rt1_lag2": "chance de transmissão crescente 2 semanas atrás",
    # painel_dados.py grava este texto quando nenhuma variavel se destaca.
    "sem fator dominante": "sem fator dominante",
}

# Nome e descricao legiveis das regras de alarme (alarmes.py grava em ASCII).
# Cada frase traduz a "condicao" gravada em saidas/alarmes.json; mudou a
# regra la, mude a frase aqui.
REGRAS_TEXTO = {
    "R1": ("Seca prolongada",
           "Seis ou mais semanas secas entre as últimas oito."),
    "R2": ("Chuva acumulada alta",
           "Chuva de oito semanas entre as 20% maiores já vistas no município."),
    "R3": ("Transmissão crescendo",
           "Chance de transmissão crescente igual ou acima de 90% por duas "
           "semanas seguidas."),
    "R4": ("Aceleração epidêmica",
           "Média das últimas 3 semanas 20% acima da média de 8, com incidência "
           "de ao menos 5 casos por 100 mil."),
    "R5": ("Janela térmica com chuva",
           "Seis das últimas oito semanas com temperatura favorável ao mosquito "
           "e chuva de 4 semanas entre as 40% maiores do município."),
    "R6": ("Seca × falta de rede de água",
           "Seca prolongada (R1) nos municípios com mais domicílios sem rede de "
           "água que a mediana do território."),
}

NOMES_MODELO = {"referencia": "Referencia", "interpretavel": "Logistica",
                "aprendizado": "LightGBM", "combinado": "Combinado"}

# Copiados ao lado do painel.json: os dois CSVs sao os botoes de download da
# aba Dicionario; o alerta.json e o estado do alerta para quem quiser consumir
# de fora (um script, um painel de parede).
ARQUIVOS_PARA_BAIXAR = {
    "dicionario_de_dados.csv": RAIZ / "docs" / "dicionario_de_dados.csv",
    "glossario.csv": RAIZ / "docs" / "glossario.csv",
    "alerta.json": RAIZ / "saidas" / "alerta.json",
}


def grafia(nome: str) -> str:
    return GRAFIA.get(nome, nome)


def apelido(nome: str) -> str:
    """Nome curto para o endereco: "Planaltina" -> "planaltina",
    "Sao Joao d'Alianca" -> "sao-joao-d-alianca". Vai no link
    vigia.guimm.site/#panorama/planaltina."""
    ascii_ = unicodedata.normalize("NFD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


def numero(valor, casas: int | None = None):
    """float limpo para o JSON: NaN e infinito viram None."""
    if valor is None:
        return None
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(valor):
        return None
    return round(valor, casas) if casas is not None else valor


def fatores(texto) -> list[str]:
    if not isinstance(texto, str) or not texto.strip():
        return []
    return [FATORES.get(f.strip(), f.strip()) for f in texto.split(",")
            if f.strip()]


def ler_json(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def ler_csv(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def semana_completa(painel: pd.DataFrame) -> int:
    """Ultima semana com todos os municipios do territorio.

    A semana mais recente costuma trazer so os municipios cuja notificacao ja
    foi processada; um panorama sobre parte do territorio enganaria.
    """
    cobertura = painel.groupby("se_codigo")["cod_ibge"].nunique()
    completas = cobertura[cobertura == painel["cod_ibge"].nunique()]
    return int(completas.index.max())


def _municipios(painel: pd.DataFrame, semana: int, alarmes: dict) -> list[dict]:
    lift_r3 = {item["cod_ibge"]: item for item in
               alarmes["regras"].get("por_municipio", {}).get("R3", [])}
    ate = painel[painel["se_codigo"] <= semana].sort_values("se_codigo")
    saida = []
    for cod, grupo in ate.groupby("cod_ibge"):
        atual = grupo.iloc[-1]
        if int(atual["se_codigo"]) != semana:
            continue
        p_rt1 = grupo["p_rt1"].dropna()
        recentes = grupo.tail(SEMANAS_FICHA)
        r3 = lift_r3.get(int(cod))
        saida.append({
            "cod": int(cod),
            "nome": grafia(str(atual["municipio"])),
            "slug": apelido(grafia(str(atual["municipio"]))),
            "uf": str(atual["uf"]),
            "casos": int(atual["casos"]),
            "est": numero(atual["casos_est"], 1),
            "inc": numero(atual["incidencia_100k"], 1),
            "canalQ3": numero(atual["canal_q3"], 1),
            "risco": str(atual["risco"]),
            "prob": numero(atual["probabilidade_alerta"], CASAS_PROB),
            "fatores": fatores(atual["fatores_alerta"]),
            "pop": int(atual["pop"]),
            "provisorio": int(atual["dado_provisorio"]),
            "completude": numero(atual["completude"], CASAS_PROB),
            # Media de casos das ultimas 3 semanas sobre a das ultimas 8: a
            # "tendencia recente" do quadro. Nao e previsao.
            "tend": numero(atual["razao_mm3_mm8"], 2),
            "rt": numero(atual["Rt"], 2),
            "pRt1": numero(p_rt1.iloc[-1], CASAS_PROB) if len(p_rt1) else None,
            "pRt1Anterior": (numero(p_rt1.iloc[-2], CASAS_PROB)
                             if len(p_rt1) > 1 else None),
            # Lift historico da regra R3 so com historico suficiente; senao
            # o site usa o mediano do territorio.
            "liftR3": (numero(r3["lift"], 2) if r3 and r3.get("n", 0) >= 8
                       else None),
            "semanas": [{
                "d": r["data_ini_se"].strftime("%Y-%m-%d"),
                "se": int(r["se_codigo"]),
                "e": numero(r["casos_est"], 1),
                "p": numero(r["probabilidade_alerta"], CASAS_PROB),
                "t": numero(r["tempmed"], 1),
                "u": numero(r["umidmed"], 1),
            } for _, r in recentes.iterrows()],
        })
    saida.sort(key=lambda m: (m["prob"] is None, -(m["prob"] or 0)))
    return saida


def _serie(painel: pd.DataFrame, semana: int, cod: int = COD_FOCO) -> list[dict]:
    """A serie inteira de um municipio, desde a primeira semana da base.

    Alimenta os graficos de serie (de 1 ano a "tudo"), o canal endemico, o
    relatorio de qualquer semana e o CSV da serie completa. A de Brasilia vai
    no painel.json; as demais, cada uma no seu arquivo (ver `salvar`).
    """
    serie = (painel[(painel["cod_ibge"] == cod)
                    & (painel["se_codigo"] <= semana)]
             .sort_values("data_ini_se"))
    return [{
        "d": r["data_ini_se"].strftime("%Y-%m-%d"),
        "se": int(r["se_codigo"]),
        "n": int(r["casos"]),
        "e": numero(r["casos_est"], 1),
        "lo": numero(r["casos_est_min"], 1),
        "hi": numero(r["casos_est_max"], 1),
        "inc": numero(r["incidencia_100k"], 2),
        "q3": numero(r["canal_q3"], 2),
        "r": str(r["risco"]) if isinstance(r["risco"], str) else None,
        "p": numero(r["probabilidade_alerta"], CASAS_PROB),
        "f": fatores(r["fatores_alerta"]),
        "pv": int(r["dado_provisorio"]) if pd.notna(r["dado_provisorio"]) else 0,
        "c": numero(r["completude"], CASAS_PROB),
    } for _, r in serie.iterrows()]


def _comparacao(painel: pd.DataFrame, semana: int, inicio) -> dict:
    recorte = painel[(painel["se_codigo"] <= semana)
                     & (painel["data_ini_se"] >= inicio)]
    grupos = recorte.assign(grupo=recorte["cod_ibge"].map(
        lambda c: "Brasilia" if c == COD_FOCO else "Entorno"))
    soma = grupos.groupby(["grupo", "data_ini_se"], as_index=False).agg(
        casos_est=("casos_est", "sum"), pop=("pop", "sum"))
    soma["inc"] = soma["casos_est"] / soma["pop"] * 1e5
    return {g: [{"d": r["data_ini_se"].strftime("%Y-%m-%d"),
                 "v": numero(r["inc"], 2)}
                for _, r in sub.sort_values("data_ini_se").iterrows()]
            for g, sub in soma.groupby("grupo")}


def _desempenho(caminho: Path) -> dict:
    tabela = pd.read_csv(caminho)
    tabela["modelo"] = tabela["modelo"].map(NOMES_MODELO).fillna(tabela["modelo"])
    por_ano = [{"ano": int(r["ano"]), "modelo": r["modelo"],
                "auc": numero(r["auc"], 3)} for _, r in tabela.iterrows()]
    resumo = [{"modelo": m,
               "auc": numero(s["auc"].mean(), 3),
               "sens": numero(s["sensibilidade"].mean(), 3),
               "espec": numero(s["especificidade"].mean(), 3),
               "vpp": numero(s["vpp"].mean(), 3),
               "auprc": numero(s["auprc"].mean(), 3),
               "brier": numero(s["brier"].mean(), 3)}
              for m, s in tabela.groupby("modelo")]
    return {"porAno": por_ano, "resumo": resumo,
            "anos": [int(tabela["ano"].min()), int(tabela["ano"].max())],
            "vppBrasilia": VPP_BRASILIA, "pesoBoosting": PESO_BOOSTING}


def _alarmes(alarmes: dict) -> dict:
    regras = []
    for r in alarmes["regras"]["regras"]:
        nome, descricao = REGRAS_TEXTO.get(r["id"], (r["nome"], r["condicao"]))
        regras.append({
            "id": r["id"], "nome": nome, "descricao": descricao,
            "lag": int(r["lag_semanas"]), "lift": numero(r["lift_mediano"], 2),
            "episodios": int(r["n_episodios"]),
            "acimaDoNormal": numero(r.get("frac_lift_acima_1"), 3),
            "aprovada": bool(r["aprovada"]),
            # A condicao como o codigo a testa, para quem quiser conferir.
            "condicao": r["condicao"],
        })
    ativos = [{
        "id": a["id"], "nome": REGRAS_TEXTO.get(a["id"], (a["id"],))[0],
        "cod": int(a["cod_ibge"]), "municipio": grafia(a["municipio"]),
        "valor": numero(a["valor_gatilho"], 3), "lag": int(a["lag_semanas"]),
        "lift": numero(a["lift_historico"], 2),
        "semana": int(a["semana"]) if a.get("semana") else None,
    } for a in alarmes["alarmes"]]
    base = alarmes["regras"].get("base", "")
    periodo = re.search(r"(\d{4})-(\d{4})", base)
    tamanho = re.search(r"\((\d+) municipios, (\d+) semanas cada", base)
    # Lift de cada municipio nas regras aprovadas: onde a regra mais se
    # confirmou. So quem tem episodios bastantes para a mediana significar algo.
    aprovadas = {r["id"] for r in alarmes["regras"]["regras"] if r["aprovada"]}
    por_municipio = {
        rid: sorted(({"cod": int(i["cod_ibge"]), "nome": grafia(i["municipio"]),
                      "n": int(i["n"]), "lift": numero(i["lift"], 2)}
                     for i in itens if i.get("n", 0) >= 8),
                    key=lambda i: -(i["lift"] or 0))
        for rid, itens in alarmes["regras"].get("por_municipio", {}).items()
        if rid in aprovadas}
    # O criterio de aprovacao vem escrito no metodo do proprio alarmes.json;
    # sem ele, o site simplesmente omite a frase.
    criterio = re.search(r"lift mediano >= ([\d.]+) e n >= (\d+)",
                         alarmes["regras"].get("metodo", ""))
    return {
        "semana": int(alarmes["gerado_da_semana"]), "regras": regras,
        "ativos": ativos,
        "periodo": [int(periodo[1]), int(periodo[2])] if periodo else None,
        "base": ({"municipios": int(tamanho[1]), "semanas": int(tamanho[2])}
                 if tamanho else None),
        "medidoEm": alarmes["regras"].get("gerado_em"),
        "porMunicipio": por_municipio,
        "criterio": ({"lift": float(criterio[1]), "episodios": int(criterio[2])}
                     if criterio else None),
    }


def _clima(clima: dict) -> dict:
    return {
        "semana": int(clima["coletado_para_semana"]),
        "fonte": clima.get("fonte", ""),
        "municipios": [{
            "cod": int(m["cod_ibge"]), "nome": grafia(m["municipio"]),
            "chuva7": numero(m["chuva_7d_mm"], 1),
            "chuva14": numero(m["chuva_14d_mm"], 1),
            "dias": int(m["dias_chuva_14d"]),
            "temp": numero(m["temp_media_14d"], 1),
        } for m in clima["municipios"]],
        "faltantes": [grafia(m["municipio"]) for m in clima.get("faltantes", [])],
    }


def _ras(caminho_vul: Path) -> dict:
    vul = {}
    for linha in ler_csv(caminho_vul):
        vul[linha["cod_subdistrito"]] = {
            "nome": grafia(linha["ra_nome"]),
            "indice": numero(linha["indice_vulnerabilidade"], 1),
            "esgoto": numero(linha["esgoto_inadequado_pct"], 2),
            "agua": numero(linha["sem_agua_rede_pct"], 2),
            "lixo": numero(linha["lixo_sem_coleta_pct"], 2),
            "bueiro": numero(linha["sem_bueiro_pct"], 2),
            "pavimento": numero(linha["sem_pavimento_pct"], 2),
        }
    return vul


def _dicionario() -> dict:
    colunas = [{
        "coluna": l["coluna"], "bloco": l["bloco"], "tipo": l["tipo"],
        "descricao": l["descricao"], "fonte": l["fonte"], "papel": l["papel"],
        "preenchida": numero(l["preenchida_pct"], 1),
    } for l in ler_csv(RAIZ / "docs" / "dicionario_de_dados.csv")]
    glossario = ler_csv(RAIZ / "docs" / "glossario.csv")
    return {"colunas": colunas, "glossario": glossario}


def _malha_ras(caminho: Path) -> dict:
    malha = ler_json(caminho)
    for f in malha["features"]:
        p = f["properties"]
        f["properties"] = {
            "cod": str(p["cod_subdistrito"]), "nome": grafia(p["ra_nome"]),
            "pop": p.get("populacao"), "dens": p.get("densidade_hab_km2"),
            "area": p.get("area_km2"),
        }
    return malha


def _setores(caminho: Path) -> dict:
    """Setores censitarios urbanos do DF: o mapa na escala da quadra.

    So os urbanos e com dado: os rurais sao poucos, enormes e sem face de rua
    levantada, e pintados no mapa esconderiam a malha urbana. As coordenadas
    perdem casas (ver CASAS_COORD) e os atributos ficam so os que a tela mostra.
    """
    def encurtar(c):
        if c and isinstance(c[0], (int, float)):
            return [round(c[0], CASAS_COORD), round(c[1], CASAS_COORD)]
        return [encurtar(x) for x in c]

    bruto = ler_json(caminho)
    feicoes = []
    for f in bruto["features"]:
        p = f["properties"]
        if p.get("SITUACAO") != "Urbana" or p.get("indice_criadouro") is None:
            continue
        feicoes.append({
            "type": "Feature",
            "properties": {
                "cod": str(p["CD_SETOR"]), "ra": grafia(str(p["NM_SUBDIST"])),
                "dom": numero(p.get("domicilios"), 0),
                "indice": numero(p.get("indice_criadouro"), 1),
                "esgoto": numero(p.get("esgoto_inadequado_pct"), 1),
                "agua": numero(p.get("sem_agua_rede_pct"), 1),
                "lixo": numero(p.get("lixo_sem_coleta_pct"), 1),
                "bueiro": numero(p.get("sem_bueiro_pct"), 1),
                "pavimento": numero(p.get("sem_pavimento_pct"), 1),
            },
            "geometry": {"type": f["geometry"]["type"],
                         "coordinates": encurtar(f["geometry"]["coordinates"])},
        })
    return {"type": "FeatureCollection", "features": feicoes}


def _verificado_em(caminho: Path) -> str | None:
    """Quando o ciclo diario conferiu a fonte pela ultima vez (ISO, com fuso).

    E o que separa "esta calmo" de "ninguem atualizou": a pagina mostra ha
    quanto tempo a fonte foi verificada e avisa quando passa de tres dias.
    """
    if not caminho.exists():
        return None
    return ler_json(caminho).get("estado", {}).get("verificado_em")


def _malha_ride(caminho: Path) -> dict:
    malha = ler_json(caminho)
    for f in malha["features"]:
        f["properties"] = {"cod": int(f["properties"]["cod_ibge"])}
    return malha


def gerar(raiz: Path = RAIZ) -> dict:
    painel = pd.read_csv(raiz / "dados" / "processado" / "painel.csv",
                         parse_dates=["data_ini_se"], low_memory=False)
    alarmes = ler_json(raiz / "saidas" / "alarmes.json")
    clima = ler_json(raiz / "saidas" / "clima_futuro.json")

    semana = semana_completa(painel)
    horizonte = int(painel["horizonte_semanas"].iloc[0])
    municipios = _municipios(painel, semana, alarmes)
    foco = next(m for m in municipios if m["cod"] == COD_FOCO)
    serie = _serie(painel, semana)
    entorno = [m for m in municipios if m["cod"] != COD_FOCO]

    variacao = None
    if len(serie) > 1 and serie[-2]["e"]:
        variacao = round((serie[-1]["e"] - serie[-2]["e"]) / serie[-2]["e"] * 100)

    gerado = datetime.now(FUSO_BRASILIA)
    return {
        "geradoEm": gerado.strftime("%Y-%m-%dT%H:%M"),
        "verificadoEm": _verificado_em(raiz / "saidas" / "alerta.json"),
        "semana": semana,
        "semanaRotulo": f"{semana % 100:02d}/{semana // 100}",
        "dataInicio": serie[-1]["d"],
        "semanaMaisRecente": int(painel["se_codigo"].max()),
        "horizonte": horizonte,
        "limiar": LIMIAR_ALERTA,
        "totalMunicipios": len(municipios),
        "ordemRisco": ORDEM_RISCO,
        "foco": {**foco, "variacao": variacao},
        "entorno": {
            "municipios": len(entorno),
            "est": numero(sum(m["est"] or 0 for m in entorno), 1),
            "altoRisco": sum(m["risco"] in ("alto", "muito alto") for m in entorno),
            "emAlerta": sum((m["prob"] or 0) >= LIMIAR_ALERTA for m in entorno),
        },
        "serie": serie,
        "comparacao": _comparacao(painel, semana, pd.Timestamp(serie[0]["d"])),
        "municipios": municipios,
        "desempenho": _desempenho(raiz / "saidas" / "desempenho_modelos.csv"),
        "alarmes": _alarmes(alarmes),
        "clima": _clima(clima),
        "ras": _ras(raiz / "dados" / "externo" / "vulnerabilidade_ras.csv"),
        "malha": _malha_ride(raiz / "dados" / "externo" / "malha_ride_df.geojson"),
        "malhaRas": _malha_ras(raiz / "dados" / "externo" / "malha_ras_df.geojson"),
        "dicionario": _dicionario(),
    }


def salvar(destino: Path = DESTINO, raiz: Path = RAIZ) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    dados = gerar(raiz)
    caminho = destino / "painel.json"
    # allow_nan=False: se algum NaN escapar da limpeza, o build falha aqui em
    # vez de publicar um JSON que o navegador recusa.
    caminho.write_text(json.dumps(dados, ensure_ascii=False, allow_nan=False,
                                  separators=(",", ":")), encoding="utf-8")
    # A serie completa de cada municipio, num arquivo por municipio: juntas
    # pesariam mais que o resto do painel, e quem abre o site quase sempre so
    # olha Brasilia.
    painel = pd.read_csv(raiz / "dados" / "processado" / "painel.csv",
                         parse_dates=["data_ini_se"], low_memory=False)
    pasta = destino / "municipios"
    pasta.mkdir(exist_ok=True)
    for m in dados["municipios"]:
        (pasta / f"{m['cod']}.json").write_text(
            json.dumps({"cod": m["cod"], "nome": m["nome"],
                        "serie": _serie(painel, dados["semana"], m["cod"])},
                       ensure_ascii=False, allow_nan=False, separators=(",", ":")),
            encoding="utf-8")
    # As quadras ficam fora do painel.json: sao a maior parte do peso e so
    # quem abre a escala da quadra precisa delas.
    setores = _setores(raiz / "dados" / "externo" / "setores_df.geojson")
    (destino / "setores.json").write_text(
        json.dumps(setores, ensure_ascii=False, allow_nan=False,
                   separators=(",", ":")), encoding="utf-8")
    for nome, origem in ARQUIVOS_PARA_BAIXAR.items():
        if origem.exists():
            shutil.copyfile(origem, destino / nome)
    return caminho


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--destino", type=Path, default=DESTINO)
    caminho = salvar(argumentos.parse_args().destino)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    print(f"gravado: {caminho} ({caminho.stat().st_size / 1024:.0f} KB)")
    print(f"semana {dados['semanaRotulo']} | {dados['totalMunicipios']} municipios"
          f" | Brasilia: risco {dados['foco']['risco']}, "
          f"chance de alerta {dados['foco']['prob']:.0%}")
