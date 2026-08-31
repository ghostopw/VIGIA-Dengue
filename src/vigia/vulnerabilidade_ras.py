"""Vulnerabilidade socioambiental por Regiao Administrativa (Censo 2022).

O QUE ISTO RESOLVE
------------------
`vulnerabilidade.py` mede saneamento no nivel municipal e diz, no proprio
texto, por que aquilo rende pouco: "o indicador e municipal e agregado,
enquanto a vulnerabilidade relevante para dengue e intraurbana -- dentro de
Brasilia, a diferenca entre o Plano Piloto e a periferia e enorme e nenhum
indicador municipal a captura".

Este modulo captura. O Censo 2022 publica os agregados tambem por SUBDISTRITO,
e no Distrito Federal o subdistrito e a Regiao Administrativa -- os mesmos
codigos que `territorio.RAS_DF` ja registrava. A diferenca medida e enorme
mesmo: 0,12% de esgotamento inadequado no Plano Piloto contra 30,5% na Fercal.

Nao sai pela API de agregados do IBGE, que serve esses temas apenas ate o nivel
municipal (N1, N2, N3 e N6 -- conferido nos metadados dos agregados 10053, 6751
e 9839). Sai dos arquivos do FTP, que e de onde este modulo le.

OS INDICADORES, E POR QUE ESTES
-------------------------------
Sao as tres dimensoes que a literatura liga a proliferacao do Aedes aegypti, as
mesmas que `vulnerabilidade.py` usa no municipio:

  esgoto_inadequado_pct  fossa rudimentar, vala ou outra forma -- agua parada
                         exposta;
  sem_agua_rede_pct      domicilio sem ligacao a rede geral, o que leva ao
                         armazenamento domiciliar em caixas e toneis, criadouro
                         classico do vetor;
  lixo_sem_coleta_pct    lixo queimado, enterrado ou com outro destino, que
                         acumula recipientes com agua parada;
  sem_bueiro_pct         domicilios em face de rua sem boca de lobo -- e a
                         drenagem que decide se a chuva escoa ou empoca, e o
                         Aedes se cria em agua parada, nao corrente;
  sem_pavimento_pct      domicilios em face de rua sem pavimento, onde a agua
                         empoca mesmo com drenagem.

Ficou de fora "utiliza agua da chuva armazenada" (V00116), que seria o
indicador mais direto de todos: no DF ele e praticamente zero em todas as RAs e
nao distingue nenhuma delas. Registrar isso importa mais do que exibir uma
coluna vazia.

O TESTE QUE ESTE MAPA PRECISAVA PASSAR
--------------------------------------
`ras_df.py` adverte contra publicar um mapa por RA que apenas repinte o mapa
populacional. Medido: a correlacao de Spearman entre o indice e a populacao da
RA e de -0,152 (p = 0,42) -- ou seja, nenhuma. A drenagem, sozinha, da -0,154. As cinco RAs mais populosas tem
vulnerabilidade baixa (Ceilandia 4,9; Taguatinga 1,0), e as mais vulneraveis
sao pequenas ou medias (Fercal, com 8.801 habitantes, marca 63,6). O mapa
carrega informacao que o denominador nao tinha, que era a condicao para
existir.

Uso:  python src/vigia/executar_vulnerabilidade_ras.py
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "dados" / "externo" / "vulnerabilidade_ras.csv"

FTP = ("https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
       "Agregados_por_Setores_Censitarios/Agregados_por_SubDistrito_csv/")
FTP_ENTORNO = ("https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
               "Agregados_por_Setores_Censitarios_Caracteristicas_urbanisticas_"
               "do_entorno_dos_domicilios/Agregados_por_SubDistrito_csv/")
ARQUIVO_ENTORNO = "Agregados_por_subdistritos_entorno_domic%c3%adlios_BR.zip"
# A versao de 2025 e a revisao mais recente da Parte 2; a Parte 1 entra so pelo
# total de domicilios, que serve de denominador.
ARQUIVO_PARTE2 = "Agregados_por_subdistritos_caracteristicas_domicilio2_BR_20250417.zip"
ARQUIVO_PARTE1 = "Agregados_por_subdistritos_caracteristicas_domicilio1_BR.zip"

PREFIXO_DF = "5300108"  # subdistritos do municipio de Brasilia

TOTAL = "V00001"  # domicilios particulares permanentes ocupados
ESGOTO_INADEQUADO = ["V00312", "V00313", "V00315"]  # fossa rudimentar, vala, outra
SEM_AGUA_REDE = ["V00464"]
LIXO_SEM_COLETA = ["V00399", "V00400", "V00402"]  # queimado, enterrado, outro
AGUA_DA_CHUVA = ["V00116"]

# Entorno do domicilio -- o fluxo das aguas na escala da rua. O Aedes se cria em
# agua PARADA, e o que decide se a agua fica parada na rua e a drenagem: sem
# boca de lobo a chuva empoca, e em via de terra empoca ainda mais.
COM_BUEIRO, SEM_BUEIRO = "V05009", "V05010"
COM_PAVIMENTO, SEM_PAVIMENTO = "V05006", "V05007"


def _baixar_csv(arquivo: str) -> pd.DataFrame:
    resposta = requests.get(FTP + arquivo, timeout=600)
    resposta.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resposta.content)) as pacote:
        nome = pacote.namelist()[0]
        # O IBGE distribui em latin-1 e usa ";" como separador.
        return pd.read_csv(pacote.open(nome), sep=";", dtype=str, encoding="latin-1")


def _numero(coluna: pd.Series) -> pd.Series:
    """Converte para numero tratando os codigos de ausencia do IBGE.

    O Censo usa "X" onde o valor foi suprimido por sigilo estatistico e vazio
    onde nao se aplica. Os dois viram zero: sao contagens de domicilios, e a
    supressao ocorre justamente onde a contagem e minima.
    """
    return pd.to_numeric(coluna.replace({"X": None, "": None}), errors="coerce").fillna(0)


def _baixar_entorno() -> pd.DataFrame:
    """Caracteristicas urbanisticas do entorno, por subdistrito."""
    resposta = requests.get(FTP_ENTORNO + ARQUIVO_ENTORNO, timeout=600)
    resposta.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resposta.content)) as pacote:
        nome = pacote.namelist()[0]
        return pd.read_csv(pacote.open(nome), sep=";", dtype=str, encoding="latin-1")


def coletar(destino: Path | None = DESTINO) -> pd.DataFrame:
    """Baixa o Censo 2022 por subdistrito e devolve os indicadores das RAs."""
    print("baixando o Censo 2022 por subdistrito...")
    parte2 = _baixar_csv(ARQUIVO_PARTE2)
    parte1 = _baixar_csv(ARQUIVO_PARTE1)
    entorno = _baixar_entorno()

    dados = parte2.merge(parte1[["CD_SUBDIST", TOTAL]], on="CD_SUBDIST", how="left")
    # `reset_index` e necessario: o bloco do entorno vem de outro arquivo e e
    # realinhado por posicao. Sem indices iguais, o pandas alinha por rotulo e
    # devolve NaN em todas as colunas combinadas.
    dados = (dados[dados["CD_SUBDIST"].str.startswith(PREFIXO_DF)]
             .reset_index(drop=True).copy())

    total = _numero(dados[TOTAL])
    def proporcao(variaveis: list[str]) -> pd.Series:
        soma = sum(_numero(dados[v]) for v in variaveis if v in dados.columns)
        return (soma / total * 100).round(2)

    # O entorno tem denominador proprio: foi levantado numa amostra de setores,
    # entao a proporcao se calcula sobre o total do proprio bloco, e nao sobre o
    # total de domicilios do subdistrito.
    ent = entorno[entorno["CD_SUBDIST"].str.startswith(PREFIXO_DF)].set_index("CD_SUBDIST")
    ent = ent.reindex(dados["CD_SUBDIST"]).reset_index(drop=True)
    bueiro_total = _numero(ent[COM_BUEIRO]) + _numero(ent[SEM_BUEIRO])
    pavimento_total = _numero(ent[COM_PAVIMENTO]) + _numero(ent[SEM_PAVIMENTO])

    resultado = pd.DataFrame({
        "cod_subdistrito": dados["CD_SUBDIST"].astype("int64"),
        "ra_nome": dados["NM_SUBDIST"].str.strip(),
        "domicilios": total.astype("int64"),
        "esgoto_inadequado_pct": proporcao(ESGOTO_INADEQUADO),
        "sem_agua_rede_pct": proporcao(SEM_AGUA_REDE),
        "lixo_sem_coleta_pct": proporcao(LIXO_SEM_COLETA),
        "agua_da_chuva_pct": proporcao(AGUA_DA_CHUVA),
        "sem_bueiro_pct": (_numero(ent[SEM_BUEIRO]) / bueiro_total.replace(0, pd.NA)
                           * 100).round(2),
        "sem_pavimento_pct": (_numero(ent[SEM_PAVIMENTO]) / pavimento_total.replace(0, pd.NA)
                              * 100).round(2),
    })

    # Indice sintetico: a media das quatro dimensoes, cada uma como distancia
    # relativa dentro do proprio DF. Serve para ordenar as RAs numa leitura so,
    # sem sugerir que as quatro pesem igual na transmissao -- nao ha estudo local
    # que sustente pesos diferentes, e inventa-los seria pior.
    dimensoes = ["esgoto_inadequado_pct", "sem_agua_rede_pct", "lixo_sem_coleta_pct",
                 "sem_bueiro_pct"]
    normalizadas = []
    for coluna in dimensoes:
        faixa = resultado[coluna].max() - resultado[coluna].min()
        normalizadas.append(
            (resultado[coluna] - resultado[coluna].min()) / faixa if faixa else 0.0
        )
    resultado["indice_vulnerabilidade"] = (
        sum(normalizadas) / len(normalizadas) * 100
    ).round(1)

    resultado = resultado.sort_values("indice_vulnerabilidade", ascending=False)
    print(f"  {len(resultado)} Regioes Administrativas")
    print(f"  esgotamento inadequado: de {resultado['esgoto_inadequado_pct'].min():.2f}% "
          f"a {resultado['esgoto_inadequado_pct'].max():.2f}%")

    if destino is not None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        resultado.to_csv(destino, index=False, encoding="utf-8")
        print(f"gravado em {destino}")
    return resultado


if __name__ == "__main__":
    coletar()
