"""Rede neural de alerta: GRU sobre a serie, treinada no Centro-Oeste.

POR QUE UMA REDE, E POR QUE ESTA
--------------------------------
O modelo atual e um LightGBM sobre variaveis defasadas escritas a mao --
incidencia_lag1, incidencia_mm3, chuva_acum12 e assim por diante. Ele funciona
(AUC 0,818), mas a defasagem util foi escolhida por nos: alguem decidiu que
importa a media de tres semanas e a de oito, e o modelo so pode olhar para o
que foi oferecido.

Uma rede recorrente recebe a serie bruta e aprende sozinha qual pedaco do
passado importa. Isso vale a pena aqui por causa de um fato medido neste
projeto: a chuva antecede os casos em cerca de oito semanas, mas essa
defasagem nao e a mesma em todo municipio nem em todo ano. Uma janela fixa
achata isso; a rede pode pesar cada semana da janela de forma diferente
conforme o contexto.

A ARQUITETURA
-------------
Duas entradas, porque os dados tem duas naturezas:

  ramo temporal   GRU de duas camadas sobre uma janela de 16 semanas com seis
                  canais por semana. Dezesseis semanas cobrem a defasagem de
                  oito da chuva com folga dos dois lados.
  ramo estatico   o que nao muda de semana para semana -- porte do municipio,
                  saneamento -- mais a posicao no ano em seno e cosseno, para
                  que dezembro e janeiro fiquem vizinhos em vez de opostos.

Os dois se juntam num cabecalho denso que devolve a probabilidade de risco alto
ou muito alto daqui a quatro semanas.

O QUE ESTE MODULO NAO FAZ
-------------------------
Nao substitui o LightGBM por decreto. `treinar()` avalia os dois na mesma
particao temporal e devolve as duas metricas: se a rede nao ganhar, o resultado
vai dizer isso, e o painel continua com o que for melhor. Um modelo mais
sofisticado que perde nao e um avanco.

Uso:  python src/vigia/executar_rede_neural.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

RAIZ = Path(__file__).resolve().parents[2]
BASE = RAIZ / "dados" / "processado" / "base_centro_oeste.csv"
DESTINO = RAIZ / "saidas" / "rede_neural.pt"
RELATORIO = RAIZ / "saidas" / "desempenho_rede.csv"

COD_FOCO = 5300108
JANELA = 16
HORIZONTE = 4

# Canais da serie. Sao sinais crus, sem defasagem escrita a mao: a rede tira do
# proprio historico o que a engenharia de variaveis fazia por ela.
CANAIS = [
    "incidencia_100k",   # o sinal principal
    "casos_est_log",     # o mesmo em nivel absoluto, comprimido
    "tempmed",
    "umidmed",
    "canal_q3",          # o patamar esperado para aquela semana do ano
    "excesso_canal",     # quanto a incidencia passa do esperado
]

# Nao mudam de semana para semana; descrevem o lugar.
ESTATICOS = [
    "log_pop",
    "esgoto_inadequado_pct",
    "sem_agua_rede_pct",
    "lixo_sem_coleta_pct",
]


@dataclass
class Particao:
    """Uma janela expansiva: treina no passado, avalia num ano fechado."""

    ano: int
    treino: tuple
    teste: tuple


class RedeAlerta(nn.Module):
    """GRU sobre a serie, concatenada aos atributos fixos do municipio."""

    def __init__(self, canais: int, estaticos: int, oculto: int = 96):
        super().__init__()
        self.gru = nn.GRU(canais, oculto, num_layers=2, batch_first=True,
                          dropout=0.2)
        self.estatico = nn.Sequential(
            nn.Linear(estaticos, 32), nn.ReLU(), nn.Dropout(0.2),
        )
        self.cabeca = nn.Sequential(
            nn.Linear(oculto + 32, 64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, 1),
        )

    def forward(self, serie: torch.Tensor, fixos: torch.Tensor) -> torch.Tensor:
        # Interessa o estado ao fim da janela: e o resumo do que a serie trouxe.
        _, oculto = self.gru(serie)
        return self.cabeca(torch.cat([oculto[-1], self.estatico(fixos)], dim=1)).squeeze(1)


def preparar(base: pd.DataFrame) -> pd.DataFrame:
    """Deriva os canais e o alvo, sem tocar no futuro."""
    dados = base.sort_values(["cod_ibge", "data_ini_se"]).copy()
    dados["data_ini_se"] = pd.to_datetime(dados["data_ini_se"])

    dados["casos_est_log"] = np.log1p(dados["casos_est"].clip(lower=0))
    # Quanto a incidencia passa do patamar historico daquela semana do ano. E a
    # leitura do canal endemico transformada em numero, e nao em rotulo.
    dados["excesso_canal"] = dados["incidencia_100k"] - dados["canal_q3"].fillna(0)

    risco_alto = (dados["risco_codigo"] >= 2).astype(float)
    dados["alvo"] = risco_alto.groupby(dados["cod_ibge"]).shift(-HORIZONTE)

    # A posicao no ano entra em seno e cosseno para que a semana 52 e a 1 fiquem
    # vizinhas; como numero cru, dezembro e janeiro seriam os extremos opostos.
    angulo = 2 * np.pi * dados["semana"] / 52.0
    dados["ano_sen"], dados["ano_cos"] = np.sin(angulo), np.cos(angulo)

    return dados


def montar_janelas(dados: pd.DataFrame) -> dict:
    """Empilha as janelas de cada municipio, sem atravessar a fronteira entre eles.

    Uma janela so existe quando ha `JANELA` semanas consecutivas antes dela e um
    alvo observavel depois. As bordas da serie ficam de fora, e nao preenchidas:
    preencher inventaria historico onde nao ha.
    """
    estaticos_mais = ESTATICOS + ["ano_sen", "ano_cos"]
    series, fixos, alvos, anos, codigos, datas = [], [], [], [], [], []

    for codigo, grupo in dados.groupby("cod_ibge", sort=False):
        grupo = grupo.reset_index(drop=True)
        canais = grupo[CANAIS].to_numpy(dtype=np.float32)
        estat = grupo[estaticos_mais].to_numpy(dtype=np.float32)
        alvo = grupo["alvo"].to_numpy(dtype=np.float32)
        ano = grupo["ano"].to_numpy()
        data = grupo["data_ini_se"].to_numpy()

        if np.isnan(canais).all() or len(grupo) < JANELA + HORIZONTE:
            continue

        for fim in range(JANELA, len(grupo)):
            if np.isnan(alvo[fim]):
                continue
            trecho = canais[fim - JANELA:fim]
            if np.isnan(trecho).any() or np.isnan(estat[fim]).any():
                continue
            series.append(trecho)
            fixos.append(estat[fim])
            alvos.append(alvo[fim])
            anos.append(ano[fim])
            codigos.append(codigo)
            datas.append(data[fim])

    return {
        "serie": np.stack(series),
        "fixo": np.stack(fixos),
        "alvo": np.array(alvos, dtype=np.float32),
        "ano": np.array(anos),
        "cod_ibge": np.array(codigos),
        "data": np.array(datas),
    }


def _normalizar(treino: np.ndarray, *outros: np.ndarray):
    """Padroniza pelos parametros do TREINO -- nunca pelos do conjunto todo.

    Calcular media e desvio sobre tudo vazaria informacao do periodo de teste
    para dentro do treino, e a metrica sairia otimista sem que se veja.
    """
    eixos = tuple(range(treino.ndim - 1))
    media = treino.mean(axis=eixos, keepdims=True)
    desvio = treino.std(axis=eixos, keepdims=True) + 1e-6
    return [(x - media) / desvio for x in (treino, *outros)]


def treinar_ano(dados: dict, ano: int, epocas: int = 30,
                dispositivo: str | None = None, semente: int = 42) -> dict:
    """Treina com tudo antes de `ano` e avalia dentro dele."""
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

    torch.manual_seed(semente)
    np.random.seed(semente)
    aparelho = torch.device(dispositivo or ("cuda" if torch.cuda.is_available() else "cpu"))

    treino = dados["ano"] < ano
    teste = dados["ano"] == ano
    if treino.sum() == 0 or teste.sum() == 0 or len(np.unique(dados["alvo"][treino])) < 2:
        return {}

    serie_tr, serie_te = _normalizar(dados["serie"][treino], dados["serie"][teste])
    fixo_tr, fixo_te = _normalizar(dados["fixo"][treino], dados["fixo"][teste])
    y_tr = dados["alvo"][treino]
    y_te = dados["alvo"][teste]

    t = lambda x: torch.tensor(x, dtype=torch.float32, device=aparelho)
    modelo = RedeAlerta(len(CANAIS), fixo_tr.shape[1]).to(aparelho)

    # O desbalanceamento vai para a funcao de perda, e nao para reamostragem:
    # reamostrar uma serie temporal quebraria a ordem que a GRU depende.
    positivos = max(float(y_tr.sum()), 1.0)
    peso = torch.tensor((len(y_tr) - positivos) / positivos, device=aparelho)
    criterio = nn.BCEWithLogitsLoss(pos_weight=peso)
    otimizador = torch.optim.AdamW(modelo.parameters(), lr=1e-3, weight_decay=1e-4)

    X, F, Y = t(serie_tr), t(fixo_tr), t(y_tr)
    lote = 512
    for _ in range(epocas):
        modelo.train()
        ordem = torch.randperm(len(Y), device=aparelho)
        for inicio in range(0, len(Y), lote):
            indice = ordem[inicio:inicio + lote]
            otimizador.zero_grad()
            perda = criterio(modelo(X[indice], F[indice]), Y[indice])
            perda.backward()
            nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            otimizador.step()

    modelo.eval()
    with torch.no_grad():
        logitos = modelo(t(serie_te), t(fixo_te))
        probabilidade = torch.sigmoid(logitos).cpu().numpy()

    return {
        "ano": ano,
        "n_treino": int(treino.sum()),
        "n_teste": int(teste.sum()),
        "auc": float(roc_auc_score(y_te, probabilidade)),
        "auprc": float(average_precision_score(y_te, probabilidade)),
        "brier": float(brier_score_loss(y_te, probabilidade)),
        "modelo": modelo,
        "probabilidade": probabilidade,
        "y": y_te,
    }
