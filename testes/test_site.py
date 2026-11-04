"""Testes do site (vigia.guimm.site) e do seu gerador de dados.

O que estes testes protegem:

- o painel.json que o navegador le e valido, completo e sem NaN;
- os numeros que o site escreve concordam com o resto do projeto (limiar do
  alerta, peso do modelo combinado);
- nenhum nome de coluna cru vaza para a tela, e toda regra de alarme tem
  frase em portugues;
- todo arquivo que a imagem copia esta nos tres lugares que precisam dele:
  Dockerfile, .dockerignore e o workflow de publicacao. Esquecer um dos tres
  ja derrubou o build uma vez.

Execucao:  python -m pytest testes -q
"""

from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from vigia import exportar_site  # noqa: E402


@pytest.fixture(scope="module")
def dados() -> dict:
    return exportar_site.gerar()


def test_json_e_valido_e_sem_nan(tmp_path):
    caminho = exportar_site.salvar(tmp_path)
    # allow_nan=False na gravacao; aqui, a releitura estrita confirma.
    texto = caminho.read_text(encoding="utf-8")
    assert "NaN" not in texto and "Infinity" not in texto
    json.loads(texto)
    for nome in exportar_site.ARQUIVOS_PARA_BAIXAR:
        if exportar_site.ARQUIVOS_PARA_BAIXAR[nome].exists():
            assert (tmp_path / nome).exists(), f"{nome} nao foi copiado"


def test_estrutura_que_o_site_le(dados):
    chaves = {"semana", "semanaRotulo", "dataInicio", "horizonte", "limiar",
              "totalMunicipios", "foco", "entorno", "serie", "comparacao",
              "municipios", "desempenho", "alarmes", "clima", "ras", "malha",
              "malhaRas", "dicionario", "geradoEm", "semanaMaisRecente",
              "verificadoEm"}
    assert chaves <= set(dados)
    assert dados["foco"]["cod"] == exportar_site.COD_FOCO
    assert dados["foco"]["nome"] == "Brasília"
    assert set(dados["comparacao"]) == {"Brasilia", "Entorno"}
    assert dados["entorno"]["municipios"] == dados["totalMunicipios"] - 1


def test_todos_os_municipios_do_territorio_entram(dados):
    painel = pd.read_csv(RAIZ / "dados/processado/painel.csv",
                         usecols=["cod_ibge"])
    assert dados["totalMunicipios"] == painel["cod_ibge"].nunique()
    malha = {f["properties"]["cod"] for f in dados["malha"]["features"]}
    assert {m["cod"] for m in dados["municipios"]} == malha, (
        "municipio sem poligono no mapa, ou poligono sem municipio")


def test_semana_do_panorama_cobre_o_territorio(dados):
    """A semana mostrada e a ultima com todos os municipios, nunca uma parcial."""
    assert all(len(m["semanas"]) >= 1 and m["semanas"][-1]["d"] == dados["dataInicio"]
               for m in dados["municipios"])


def test_serie_de_brasilia_e_a_historia_inteira(dados):
    """O site mostra de 1 ano a "tudo" e baixa a serie completa em CSV: a
    serie nao pode voltar a ser cortada em poucos anos sem ninguem notar."""
    painel = pd.read_csv(RAIZ / "dados/processado/painel.csv",
                         usecols=["cod_ibge", "se_codigo"])
    semanas = painel[(painel["cod_ibge"] == exportar_site.COD_FOCO)
                     & (painel["se_codigo"] <= dados["semana"])]["se_codigo"]
    assert [p["se"] for p in dados["serie"]] == sorted(semanas)
    assert len(dados["comparacao"]["Brasilia"]) == len(dados["serie"])
    campos = {"d", "se", "n", "e", "lo", "hi", "inc", "q3", "r", "p", "f", "pv", "c"}
    assert all(campos <= set(p) for p in dados["serie"])


def test_probabilidade_sem_arredondamento_duplo(dados):
    """A pagina arredonda para porcentagem inteira. Se o JSON ja vier
    arredondado a 3 casas, 0,1549 vira 0,155 e depois 16%, e o certo e 15%."""
    painel = pd.read_csv(RAIZ / "dados/processado/painel.csv",
                         usecols=["cod_ibge", "se_codigo", "probabilidade_alerta"])
    semana = painel[painel["se_codigo"] == dados["semana"]].set_index("cod_ibge")
    for m in dados["municipios"]:
        bruto = semana.loc[m["cod"], "probabilidade_alerta"]
        if pd.notna(bruto):
            assert round(m["prob"] * 100) == round(bruto * 100), m["nome"]


def test_dados_que_o_painel_antigo_mostrava_continuam_no_site(dados):
    """Itens que o redesign tinha deixado de fora e voltaram: tendencia
    recente, AUPRC, lift por municipio da regra aprovada e o detalhe de cada
    regra."""
    assert all("tend" in m for m in dados["municipios"])
    assert all(r.get("auprc") is not None for r in dados["desempenho"]["resumo"])
    aprovadas = {r["id"] for r in dados["alarmes"]["regras"] if r["aprovada"]}
    assert set(dados["alarmes"]["porMunicipio"]) == aprovadas
    assert all(i["n"] >= 8 for lista in dados["alarmes"]["porMunicipio"].values()
               for i in lista)
    assert all(r["condicao"] and r["acimaDoNormal"] is not None
               for r in dados["alarmes"]["regras"])


def test_cada_municipio_tem_serie_completa_e_endereco(tmp_path):
    """O panorama de Planaltina (GO) ou de qualquer outro municipio le a
    serie de dados/municipios/<codigo>.json, e o link #panorama/<apelido>
    precisa apontar para um municipio so."""
    exportar_site.salvar(tmp_path)
    painel = json.loads((tmp_path / "painel.json").read_text(encoding="utf-8"))
    apelidos = [m["slug"] for m in painel["municipios"]]
    assert len(set(apelidos)) == len(apelidos), "dois municipios com o mesmo link"
    assert all(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", a) for a in apelidos)
    for m in painel["municipios"]:
        arquivo = tmp_path / "municipios" / f"{m['cod']}.json"
        assert arquivo.exists(), m["nome"]
        serie = json.loads(arquivo.read_text(encoding="utf-8"))["serie"]
        # A serie termina na semana do boletim, a mesma da ficha do municipio.
        assert serie[-1]["d"] == painel["dataInicio"], m["nome"]
        assert serie[-1]["e"] == m["est"], m["nome"]
    brasilia = json.loads((tmp_path / "municipios" / f"{exportar_site.COD_FOCO}.json")
                          .read_text(encoding="utf-8"))["serie"]
    assert brasilia == painel["serie"]


def test_quadras_vao_em_arquivo_proprio(tmp_path):
    exportar_site.salvar(tmp_path)
    setores = json.loads((tmp_path / "setores.json").read_text(encoding="utf-8"))
    bruto = json.loads((RAIZ / "dados/externo/setores_df.geojson")
                       .read_text(encoding="utf-8"))
    urbanos = [f for f in bruto["features"]
               if f["properties"].get("SITUACAO") == "Urbana"
               and f["properties"].get("indice_criadouro") is not None]
    assert len(setores["features"]) == len(urbanos) > 0
    props = {"cod", "ra", "dom", "indice", "esgoto", "agua", "lixo", "bueiro",
             "pavimento"}
    assert all(set(f["properties"]) == props for f in setores["features"])
    assert "setores" not in json.loads(
        (tmp_path / "painel.json").read_text(encoding="utf-8")), (
        "as quadras sao pesadas; so devem baixar quando alguem abre a escala")


def test_limiar_e_o_mesmo_do_alerta_do_pipeline(dados):
    from vigia import alerta
    padrao = inspect.signature(alerta.avaliar).parameters["limiar"].default
    assert dados["limiar"] == padrao, (
        "o site e o ciclo diario usam limiares diferentes: o boletim diria "
        "'fora de alerta' enquanto o aviso dispara, ou o contrario")


def test_peso_do_combinado_bate_com_a_modelagem(dados):
    pytest.importorskip("lightgbm")
    from vigia.modelagem import PESO_BOOSTING
    assert dados["desempenho"]["pesoBoosting"] == PESO_BOOSTING


def test_nenhum_nome_de_coluna_cru_vaza_para_a_tela():
    painel = pd.read_csv(RAIZ / "dados/processado/painel.csv",
                         usecols=["fatores_alerta"])
    usados = {f.strip() for texto in painel["fatores_alerta"].dropna()
              for f in str(texto).split(",") if f.strip()}
    sem_traducao = usados - set(exportar_site.FATORES)
    assert not sem_traducao, (
        "fatores sem descricao legivel em exportar_site.FATORES: "
        f"{sorted(sem_traducao)}")


def test_toda_regra_de_alarme_tem_frase(dados):
    gravadas = json.loads((RAIZ / "saidas/alarmes.json").read_text(encoding="utf-8"))
    ids = {r["id"] for r in gravadas["regras"]["regras"]}
    assert ids <= set(exportar_site.REGRAS_TEXTO)
    assert dados["alarmes"]["criterio"] is not None, (
        "o criterio de aprovacao sumiu do 'metodo' em alarmes.json; o site "
        "omitiria a frase que explica como uma regra vira alarme")


def test_pagina_aponta_para_arquivos_que_existem():
    html = (RAIZ / "site/index.html").read_text(encoding="utf-8")
    for local in re.findall(r'(?:href|src)="([^":#]+\.(?:css|js))"', html):
        assert (RAIZ / "site" / local).exists(), local


def _copiados_pelo_dockerfile() -> set[str]:
    """Origens dos COPY do repositorio (ignora o COPY --from entre estagios)."""
    origens = set()
    for linha in (RAIZ / "Dockerfile").read_text(encoding="utf-8").splitlines():
        partes = linha.split()
        if not partes or partes[0] != "COPY" or any(p.startswith("--from") for p in partes):
            continue
        origens.update(partes[1:-1])
    return origens


def test_cada_arquivo_da_imagem_esta_nos_tres_lugares():
    copiados = _copiados_pelo_dockerfile()
    assert copiados, "nenhum COPY encontrado no Dockerfile"
    ignorar = (RAIZ / ".dockerignore").read_text(encoding="utf-8")
    reabertos = {l[1:].strip() for l in ignorar.splitlines() if l.startswith("!")}
    workflow = (RAIZ / ".github/workflows/publicar-painel.yml").read_text(encoding="utf-8")
    vigiados = set(re.findall(r'-\s+"([^"]+)"', workflow))
    na_raiz = {"requirements-site.txt", "nginx.conf"}   # nao estao em pasta ignorada
    for arquivo in copiados:
        assert (RAIZ / arquivo).exists(), f"o Dockerfile copia {arquivo}, que nao existe"
        if arquivo not in na_raiz:
            assert arquivo in reabertos, f"{arquivo} falta como excecao no .dockerignore"
        assert arquivo in vigiados, (
            f"{arquivo} falta nos paths de publicar-painel.yml: mudar esse "
            "arquivo nao republicaria o site")
