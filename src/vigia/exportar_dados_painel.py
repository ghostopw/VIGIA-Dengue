"""Exporta os dados do painel em JSON compacto, para embutir na pagina HTML.

Usado por `gerar_painel_html.py`. Mantem apenas o que a pagina consome, e nao
a base inteira, para que o arquivo final fique pequeno o bastante para abrir
rapido no navegador.
"""

import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "dados" / "processado" / "painel_dados.json"

COD_FOCO = 5300108
ORDEM = ["baixo", "moderado", "alto", "muito alto"]

painel = pd.read_csv(RAIZ / "dados/processado/painel.csv",
                     parse_dates=["data_ini_se"], low_memory=False)
# Ultima semana com cobertura completa do territorio. A semana mais recente
# costuma trazer so os municipios cuja notificacao ja foi processada -- exibir
# essa parcial daria um panorama do territorio baseado em poucos municipios.
cobertura = painel.groupby("se_codigo")["cod_ibge"].nunique()
completas = cobertura[cobertura == painel["cod_ibge"].nunique()]
semana = int(completas.index.max())
horizonte = int(painel["horizonte_semanas"].iloc[0])
atual = painel[painel["se_codigo"] == semana].copy()

foco = atual[atual["cod_ibge"] == COD_FOCO].iloc[0]
serie_foco = painel[painel["cod_ibge"] == COD_FOCO].sort_values("data_ini_se")
anterior = serie_foco[serie_foco["se_codigo"] < semana]

variacao = None
if not anterior.empty and anterior["casos_est"].iloc[-1]:
    base = anterior["casos_est"].iloc[-1]
    variacao = round((foco["casos_est"] - base) / base * 100)

# Serie das ultimas 156 semanas para o grafico do panorama.
recorte = serie_foco.tail(156)
serie = [{
    "d": r["data_ini_se"].strftime("%Y-%m-%d"),
    "se": int(r["se_codigo"]),
    "n": int(r["casos"]),
    "e": round(float(r["casos_est"]), 1),
    "lo": round(float(r["casos_est_min"]), 1),
    "hi": round(float(r["casos_est_max"]), 1),
} for _, r in recorte.iterrows()]

# Comparacao Brasilia x Entorno, incidencia padronizada.
grupos = painel.assign(grupo=painel["cod_ibge"].map(
    lambda c: "Brasilia" if c == COD_FOCO else "Entorno"))
comp = grupos.groupby(["grupo", "data_ini_se"], as_index=False).agg(
    {"casos_est": "sum", "pop": "sum"})
comp["inc"] = comp["casos_est"] / comp["pop"] * 1e5
comp = comp[comp["data_ini_se"] >= recorte["data_ini_se"].min()]
comparacao = {
    g: [{"d": r["data_ini_se"].strftime("%Y-%m-%d"), "v": round(r["inc"], 2)}
        for _, r in sub.sort_values("data_ini_se").iterrows()]
    for g, sub in comp.groupby("grupo")
}

municipios = [{
    "cod": int(r["cod_ibge"]), "nome": r["municipio"], "uf": r["uf"],
    "casos": int(r["casos"]), "est": round(float(r["casos_est"]), 1),
    "inc": round(float(r["incidencia_100k"]), 1),
    "risco": str(r["risco"]), "prob": round(float(r["probabilidade_alerta"]), 3),
    "fatores": r["fatores_alerta"], "pop": int(r["pop"]),
    "provisorio": int(r["dado_provisorio"]),
} for _, r in atual.sort_values("probabilidade_alerta", ascending=False).iterrows()]

malha = json.loads((RAIZ / "dados/externo/malha_ride_df.geojson").read_text(encoding="utf-8"))
malha_ras = json.loads((RAIZ / "dados/externo/malha_ras_df.geojson").read_text(encoding="utf-8"))

desempenho = pd.read_csv(RAIZ / "saidas/desempenho_modelos.csv")
nomes = {"referencia": "Referencia", "interpretavel": "Logistica",
         "aprendizado": "LightGBM"}
desempenho["modelo"] = desempenho["modelo"].map(nomes).fillna(desempenho["modelo"])
por_ano = [{"ano": int(r["ano"]), "modelo": r["modelo"], "auc": round(float(r["auc"]), 3),
            "sens": round(float(r["sensibilidade"]), 3),
            "espec": round(float(r["especificidade"]), 3)}
           for _, r in desempenho.iterrows()]
resumo = [{"modelo": m,
           "auc": round(float(s["auc"].mean()), 3),
           "sens": round(float(s["sensibilidade"].mean()), 3),
           "espec": round(float(s["especificidade"].mean()), 3),
           "vpp": round(float(s["vpp"].mean()), 3),
           "brier": round(float(s["brier"].mean()), 3)}
          for m, s in desempenho.groupby("modelo")]

ras = [{"nome": f["properties"]["ra_nome"],
        "pop": f["properties"].get("populacao"),
        "dens": f["properties"].get("densidade_hab_km2"),
        "area": f["properties"].get("area_km2")}
       for f in malha_ras["features"]]

entorno = atual[atual["cod_ibge"] != COD_FOCO]

dados = {
    "semana": semana,
    "semanaRotulo": f"{semana % 100:02d}/{semana // 100}",
    "horizonte": horizonte,
    "totalMunicipios": int(atual["cod_ibge"].nunique()),
    "foco": {
        "casos": int(foco["casos"]), "est": round(float(foco["casos_est"]), 1),
        "inc": round(float(foco["incidencia_100k"]), 1),
        "risco": str(foco["risco"]), "prob": round(float(foco["probabilidade_alerta"]), 3),
        "fatores": foco["fatores_alerta"], "variacao": variacao,
        "provisorio": int(foco["dado_provisorio"]),
        "completude": round(float(foco["completude"]), 3),
    },
    "entorno": {
        "municipios": int(len(entorno)),
        "est": round(float(entorno["casos_est"].sum()), 1),
        "altoRisco": int((entorno["risco_codigo"] >= 2).sum()),
        "emAlerta": int((entorno["probabilidade_alerta"] >= 0.5).sum()),
    },
    "serie": serie,
    "comparacao": comparacao,
    "municipios": municipios,
    "desempenho": {"porAno": por_ano, "resumo": resumo},
    "ras": ras,
    "malha": malha,
    "malhaRas": malha_ras,
    "ordemRisco": ORDEM,
}

SAIDA.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("gravado:", SAIDA, f"{SAIDA.stat().st_size/1024:.0f} KB")
print("municipios:", dados["totalMunicipios"], "| semana:", dados["semanaRotulo"])
print("RAs:", len(ras), "| serie:", len(serie), "semanas")
