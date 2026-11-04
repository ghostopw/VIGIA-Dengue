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
              "malhaRas", "dicionario", "geradoEm", "semanaMaisRecente"}
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
