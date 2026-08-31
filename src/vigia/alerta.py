"""Alerta ao vivo de Brasilia: le o estado atual e decide se ha o que avisar.

O QUE "AO VIVO" PODE SIGNIFICAR AQUI
------------------------------------
Nenhum alerta pode ser mais fresco que a fonte. O InfoDengue publica a semana
epidemiologica com cerca de tres semanas de atraso -- em 31/08/2026 a ultima
semana disponivel era a 33, iniciada em 16/08. Esse atraso e da vigilancia, nao
do painel: a notificacao leva tempo para ser digitada, e o proprio InfoDengue
corrige o numero nas semanas seguintes.

Ao vivo, entao, quer dizer duas coisas que dependem so de nos:

  1. acompanhar a fonte sozinho, de modo que a semana nova entre no painel
     poucas horas depois de publicada, sem ninguem rodar nada a mao;
  2. procurar a pessoa quando o quadro muda, em vez de esperar que ela abra a
     pagina -- um painel que so avisa quem ja esta olhando nao e um alerta.

O QUE CONTA COMO EVENTO
-----------------------
Nem toda mudanca merece interromper alguem. Avisamos quando:

  - chega uma semana nova (o dado avancou);
  - o nivel de risco sobe (subida importa mais que descida: a descida pode ser
    apenas notificacao incompleta ainda subindo);
  - Brasilia cruza o limiar de probabilidade, nos dois sentidos;
  - a incidencia passa o limite do canal endemico.

O estado da ultima verificacao fica em `dados/processado/ultimo_alerta.json`.
Sem ele, a primeira execucao registra o estado e nao dispara nada -- ninguem
deve receber um alerta so porque o programa rodou pela primeira vez.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PAINEL = RAIZ / "dados" / "processado" / "painel.csv"
ESTADO = RAIZ / "dados" / "processado" / "ultimo_alerta.json"

COD_FOCO = 5300108
ORDEM_RISCO = ["baixo", "moderado", "alto", "muito alto"]


@dataclass
class Estado:
    """Retrato de Brasilia numa semana."""

    semana: int
    data_ini_se: str
    casos: int
    casos_est: float
    incidencia_100k: float
    risco: str
    probabilidade_alerta: float
    canal_q3: float
    fatores: str
    dado_provisorio: bool
    completude: float
    verificado_em: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @property
    def risco_codigo(self) -> int:
        return ORDEM_RISCO.index(self.risco) if self.risco in ORDEM_RISCO else -1

    def em_alerta(self, limiar: float) -> bool:
        return self.probabilidade_alerta >= limiar

    def acima_do_canal(self) -> bool:
        return bool(self.canal_q3) and self.incidencia_100k > self.canal_q3


def ler_estado_atual(painel: Path = PAINEL) -> Estado:
    """Ultima semana de Brasilia no painel."""
    dados = pd.read_csv(painel)
    brasilia = dados[dados["cod_ibge"] == COD_FOCO].sort_values("se_codigo")
    if brasilia.empty:
        raise RuntimeError("nao ha linha de Brasilia no painel")

    linha = brasilia.iloc[-1]
    return Estado(
        semana=int(linha["se_codigo"]),
        data_ini_se=str(linha["data_ini_se"])[:10],
        casos=int(linha["casos"]),
        casos_est=round(float(linha["casos_est"]), 1),
        incidencia_100k=round(float(linha["incidencia_100k"]), 2),
        risco=str(linha["risco"]),
        probabilidade_alerta=round(float(linha["probabilidade_alerta"]), 4),
        canal_q3=round(float(linha.get("canal_q3", 0) or 0), 2),
        fatores=str(linha.get("fatores_alerta", "")),
        dado_provisorio=bool(linha.get("dado_provisorio", 0)),
        completude=round(float(linha.get("completude", 1) or 1), 3),
    )


def carregar_anterior(caminho: Path = ESTADO) -> Estado | None:
    if not caminho.exists():
        return None
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    return Estado(**bruto)


def guardar(estado: Estado, caminho: Path = ESTADO) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(estado.__dict__, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def comparar(anterior: Estado | None, atual: Estado, limiar: float = 0.50) -> list[str]:
    """Eventos que justificam avisar alguem."""
    if anterior is None:
        return []

    eventos: list[str] = []

    if atual.semana > anterior.semana:
        eventos.append(
            f"Semana nova publicada: SE {atual.semana % 100:02d}/{atual.semana // 100} "
            f"(iniciada em {atual.data_ini_se})."
        )

    if atual.risco_codigo > anterior.risco_codigo:
        eventos.append(
            f"Risco subiu de {anterior.risco} para {atual.risco}."
        )

    antes, agora = anterior.em_alerta(limiar), atual.em_alerta(limiar)
    if agora and not antes:
        eventos.append(
            f"Brasilia entrou em alerta: probabilidade de "
            f"{atual.probabilidade_alerta:.0%}, acima do limiar de {limiar:.0%}."
        )
    elif antes and not agora:
        eventos.append(
            f"Brasilia saiu do alerta: probabilidade caiu para "
            f"{atual.probabilidade_alerta:.0%}."
        )

    if atual.acima_do_canal() and not anterior.acima_do_canal():
        eventos.append(
            f"Incidencia passou o limite esperado: {atual.incidencia_100k:.1f} "
            f"contra {atual.canal_q3:.1f} por 100 mil do canal endemico."
        )

    return eventos


def mensagem(eventos: list[str], estado: Estado) -> str:
    """Texto do aviso, curto o bastante para caber numa notificacao."""
    rotulo = f"SE {estado.semana % 100:02d}/{estado.semana // 100}"
    linhas = [f"VIGIA-Dengue -- Brasilia, {rotulo}", ""]
    linhas += [f"- {evento}" for evento in eventos]
    linhas += [
        "",
        f"Casos estimados: {estado.casos_est:,.0f}".replace(",", "."),
        f"Incidencia: {estado.incidencia_100k:.1f} por 100 mil",
        f"Risco: {estado.risco} | probabilidade de alerta: "
        f"{estado.probabilidade_alerta:.0%}",
    ]
    if estado.fatores:
        linhas.append(f"Fatores: {estado.fatores}")
    if estado.dado_provisorio:
        linhas.append(
            f"Atencao: notificacao ainda incompleta ({estado.completude:.0%} "
            "digitado). Os numeros tendem a subir."
        )
    return "\n".join(linhas)


def avaliar(limiar: float = 0.50, painel: Path = PAINEL,
            caminho_estado: Path = ESTADO) -> dict:
    """Le, compara, grava e devolve o que houve.

    Nao emite nada: quem emite e `notificar.py`, para que a decisao de avisar
    fique separada do canal por onde se avisa.
    """
    atual = ler_estado_atual(painel)
    anterior = carregar_anterior(caminho_estado)
    eventos = comparar(anterior, atual, limiar)

    primeira_vez = anterior is None
    guardar(atual, caminho_estado)

    return {
        "primeira_vez": primeira_vez,
        "eventos": eventos,
        "estado": atual.__dict__,
        "mensagem": mensagem(eventos, atual) if eventos else "",
        "em_alerta": atual.em_alerta(limiar),
        "limiar": limiar,
    }
