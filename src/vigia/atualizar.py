"""Ciclo de atualizacao do alerta: busca a fonte, reconstroi e avalia.

E o passo que faz o painel acompanhar o InfoDengue sozinho. Roda inteiro em
alguns minutos e pode ser agendado -- uma vez por dia basta, porque a fonte
publica uma vez por semana e o dia da publicacao varia.

O QUE ELE NAO RESOLVE
---------------------
O atraso da fonte. O InfoDengue publica a semana epidemiologica cerca de tres
semanas depois de ela comecar, porque a notificacao leva tempo para ser
digitada e o nowcasting so estabiliza depois. Rodar de hora em hora nao
adianta: o dado novo aparece uma vez por semana, e o valor da semana recem
publicada ainda vai ser corrigido para cima nas semanas seguintes.

O que este ciclo garante e que, quando a semana sair, ela esteja no painel
poucas horas depois -- e nao quando alguem lembrar de rodar o pipeline.

POR QUE SO OS ANOS RECENTES
---------------------------
A serie completa vai de 2014 a hoje e leva minutos para baixar. O que muda de
uma execucao para outra sao as ultimas semanas, e o InfoDengue tambem revisa
retroativamente os meses recentes. Baixar os dois ultimos anos e o suficiente
para capturar as duas coisas; o restante da serie fica como esta.

Uso:  python src/vigia/executar_atualizacao.py
"""

from __future__ import annotations

import time
from datetime import date
from pathlib import Path

import pandas as pd

from . import alerta
from .base_analitica import construir
from .ingestao_infodengue import padronizar
from .painel_dados import salvar as salvar_painel
from .risco import classificar
from .territorio import TERRITORIO
from .vulnerabilidade import integrar

RAIZ = Path(__file__).resolve().parents[2]
PROCESSADO = RAIZ / "dados" / "processado"
EXTERNO = RAIZ / "dados" / "externo"
BRUTO = PROCESSADO / "infodengue_territorio.csv"

ANOS_RECENTES = 2
HORIZONTE = 4


def buscar_recente(anos: int = ANOS_RECENTES, doenca: str = "dengue") -> pd.DataFrame:
    """Baixa as ultimas semanas de todo o territorio."""
    from .ingestao_infodengue import baixar_municipio

    ano_fim = date.today().year
    ano_inicio = ano_fim - anos + 1
    partes: list[pd.DataFrame] = []

    for indice, (geocode, nome) in enumerate(sorted(TERRITORIO.items()), start=1):
        bruto = baixar_municipio(geocode, ano_inicio, ano_fim, doenca)
        if not bruto.empty:
            partes.append(padronizar(bruto, geocode))
        print(f"  [{indice:2d}/{len(TERRITORIO)}] {nome}")
        time.sleep(1)  # cortesia com a API publica

    if not partes:
        raise RuntimeError("o InfoDengue nao devolveu dado algum")
    return pd.concat(partes, ignore_index=True)


def mesclar(historico: pd.DataFrame, recente: pd.DataFrame) -> pd.DataFrame:
    """Sobrepoe as semanas recentes ao historico.

    A revisao vale mais que o registro antigo: o InfoDengue corrige o numero das
    semanas recentes a medida que a notificacao e digitada, entao em caso de
    empate fica o que acabou de chegar.
    """
    juntos = pd.concat([historico, recente], ignore_index=True)

    # O historico guarda a data como "2026-08-09 00:00:00" e o download novo
    # como "2026-08-09". Misturadas no mesmo CSV, a releitura quebra. Normalizar
    # aqui mantem o arquivo com um formato so, seja qual for a origem da linha.
    for coluna in ("data_ini_se", "data_iniSE"):
        if coluna in juntos.columns:
            juntos[coluna] = pd.to_datetime(
                juntos[coluna], format="mixed", errors="coerce"
            ).dt.strftime("%Y-%m-%d")

    return (
        juntos.drop_duplicates(subset=["cod_ibge", "se_codigo"], keep="last")
        .sort_values(["cod_ibge", "se_codigo"])
        .reset_index(drop=True)
    )


def reconstruir() -> pd.DataFrame:
    """Refaz a base analitica, o risco e a tabela do painel.

    Nao refaz a validacao temporal dos modelos: ela mede desempenho historico,
    leva minutos e nao muda o alerta desta semana. Fica para `executar_analise`.
    """
    bruto = pd.read_csv(BRUTO)

    arquivo_chuva = EXTERNO / "chuva_semanal.csv"
    chuva = pd.read_csv(arquivo_chuva) if arquivo_chuva.exists() else None
    base = construir(bruto, chuva=chuva)

    arquivo_vulnerabilidade = EXTERNO / "vulnerabilidade.csv"
    if arquivo_vulnerabilidade.exists():
        base = integrar(base, pd.read_csv(arquivo_vulnerabilidade))

    base.to_csv(PROCESSADO / "base_analitica.csv", index=False, encoding="utf-8")
    com_risco = classificar(base)
    com_risco.to_csv(PROCESSADO / "base_com_risco.csv", index=False, encoding="utf-8")

    return salvar_painel(com_risco, PROCESSADO / "painel.csv", horizonte=HORIZONTE)


def semana_no_painel() -> int | None:
    """Ultima semana de Brasilia hoje no painel, antes de qualquer atualizacao."""
    caminho = PROCESSADO / "painel.csv"
    if not caminho.exists():
        return None
    dados = pd.read_csv(caminho, usecols=["cod_ibge", "se_codigo"])
    brasilia = dados[dados["cod_ibge"] == alerta.COD_FOCO]
    return int(brasilia["se_codigo"].max()) if len(brasilia) else None


def atualizar(limiar: float = 0.50, buscar: bool = True) -> dict:
    """Executa o ciclo inteiro e devolve o que mudou."""
    antes = semana_no_painel()

    if buscar:
        print("buscando o InfoDengue...")
        recente = buscar_recente()
        historico = pd.read_csv(BRUTO)
        mesclado = mesclar(historico, recente)
        mesclado.to_csv(BRUTO, index=False, encoding="utf-8")
        print(f"  base bruta: {len(historico)} -> {len(mesclado)} linhas")

    print("reconstruindo...")
    painel = reconstruir()
    print(f"  painel: {len(painel)} linhas")

    resultado = alerta.avaliar(limiar=limiar)
    resultado["semana_anterior"] = antes
    resultado["semana_nova"] = resultado["estado"]["semana"] != antes
    return resultado
