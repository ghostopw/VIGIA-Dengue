# -*- coding: utf-8 -*-
"""Dicionario de dados gerado da propria base analitica.

O dicionario anterior era mantido a mao e envelheceu: descrevia 44 colunas
quando a base tinha 124. Este modulo gera a documentacao a partir das colunas
que existem de verdade, cruzando com as listas de preditoras de `modelagem`,
de modo que a documentacao nunca descreva uma base que deixou de existir.
O teste em testes/test_dicionario.py falha quando alguem acrescenta coluna
sem descricao ou esquece de regenerar os artefatos.

Saidas: docs/dicionario_de_dados_completo.md (leitura) e
docs/dicionario_de_dados.csv (a aba Dicionario do painel le este).
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from vigia.modelagem import VARIAVEIS, VARIAVEIS_ESSENCIAIS

RAIZ = Path(__file__).resolve().parents[2]
SAIDA_MD = RAIZ / "docs" / "dicionario_de_dados_completo.md"
SAIDA_CSV = RAIZ / "docs" / "dicionario_de_dados.csv"
SAIDA_GLOSSARIO = RAIZ / "docs" / "glossario.csv"

# --------------------------------------------------------------- descricoes
# Colunas de nome fixo. Defasagens, medias moveis e acumulados sao descritos
# por regra em PADROES, para nao repetir sessenta linhas quase iguais.

DESCRICOES = {
    # Identificacao
    "cod_ibge": ("Identificação", "Código IBGE de 7 dígitos do município. Chave de integração entre todas as bases.", "IBGE"),
    "municipio": ("Identificação", "Nome do município conforme o IBGE.", "IBGE"),
    "municipio_nome": ("Identificação", "Nome do município conforme o InfoDengue. Mantido para conferência da junção.", "InfoDengue"),
    "uf": ("Identificação", "Unidade federativa: DF, GO ou MG.", "IBGE"),
    "data_ini_se": ("Identificação", "Data do primeiro dia da semana epidemiológica (domingo). Chave temporal.", "InfoDengue"),
    "data_iniSE": ("Identificação", "Mesma data, no nome original do InfoDengue. Mantida para rastreio.", "InfoDengue"),
    "semana": ("Identificação", "Semana epidemiológica no ano, de 1 a 53. Entra no modelo como marcador de sazonalidade.", "Derivada"),
    "se_codigo": ("Identificação", "Semana epidemiológica no formato AAAASS, ex. 202633.", "InfoDengue"),
    "ano": ("Identificação", "Ano epidemiológico. Define as dobras da validação temporal.", "Derivada"),
    "id": ("Identificação", "Identificador da linha no InfoDengue.", "InfoDengue"),
    "Localidade_id": ("Identificação", "Identificador interno de localidade do InfoDengue.", "InfoDengue"),
    "versao_modelo": ("Identificação", "Versão do modelo de nowcasting que gerou os casos estimados.", "InfoDengue"),

    # Epidemiologicas
    "casos": ("Epidemiológico", "Casos notificados de dengue na semana. Subnotificado nas semanas recentes.", "InfoDengue/SINAN"),
    "casos_est": ("Epidemiológico", "Casos estimados por nowcasting, corrigindo o atraso de notificação. É a base de todo o cálculo de risco.", "InfoDengue"),
    "casos_est_min": ("Epidemiológico", "Limite inferior do intervalo de credibilidade dos casos estimados.", "InfoDengue"),
    "casos_est_max": ("Epidemiológico", "Limite superior do intervalo de credibilidade dos casos estimados.", "InfoDengue"),
    "incidencia_100k": ("Epidemiológico", "Casos estimados por 100 mil habitantes na semana. Variável mais importante do modelo.", "Derivada"),
    "p_inc100k": ("Epidemiológico", "Incidência por 100 mil calculada pelo próprio InfoDengue. Mantida para conferência.", "InfoDengue"),
    "razao_mm3_mm8": ("Epidemiológico", "Razão entre a média móvel de 3 e a de 8 semanas. Mede aceleração: acima de 1 a curva sobe.", "Derivada"),
    "variacao_semanal": ("Epidemiológico", "Variação relativa da incidência frente à semana anterior.", "Derivada"),
    "Rt": ("Epidemiológico", "Número reprodutivo efetivo estimado pelo InfoDengue.", "InfoDengue"),
    "p_rt1": ("Epidemiológico", "Probabilidade de o Rt ser maior que 1, isto é, de a transmissão estar crescendo.", "InfoDengue"),
    "nivel": ("Epidemiológico", "Nível de alerta do próprio InfoDengue (1 verde a 4 vermelho). Não é o risco do projeto.", "InfoDengue"),
    "nivel_inc": ("Epidemiológico", "Nível de incidência segundo o InfoDengue.", "InfoDengue"),
    "receptivo": ("Epidemiológico", "Indicador do InfoDengue de receptividade climática ao vetor.", "InfoDengue"),
    "transmissao": ("Epidemiológico", "Indicador do InfoDengue de evidência de transmissão sustentada.", "InfoDengue"),
    "tweet": ("Epidemiológico", "Menções a dengue no Twitter/X captadas pelo InfoDengue. Não usada pelo projeto.", "InfoDengue"),
    "notif_accum_year": ("Epidemiológico", "Notificações acumuladas no ano até a semana.", "InfoDengue"),
    "casprov": ("Epidemiológico", "Casos prováveis notificados.", "InfoDengue"),
    "casprov_est": ("Epidemiológico", "Casos prováveis estimados por nowcasting. Vem 100% vazia da fonte para este território.", "InfoDengue"),
    "casprov_est_min": ("Epidemiológico", "Limite inferior dos casos prováveis estimados. Vem 100% vazia da fonte.", "InfoDengue"),
    "casprov_est_max": ("Epidemiológico", "Limite superior dos casos prováveis estimados. Vem 100% vazia da fonte.", "InfoDengue"),
    "casconf": ("Epidemiológico", "Casos confirmados em laboratório. Vem 100% vazia da fonte para este território.", "InfoDengue"),

    # Climaticas
    "tempmed": ("Climático", "Temperatura média da semana, em graus Celsius. Reanálise, não medição de estação.", "ERA5/Open-Meteo"),
    "tempmin": ("Climático", "Temperatura mínima da semana.", "ERA5/Open-Meteo"),
    "tempmax": ("Climático", "Temperatura máxima da semana.", "ERA5/Open-Meteo"),
    "umidmed": ("Climático", "Umidade relativa média da semana, em porcentagem.", "ERA5/Open-Meteo"),
    "umidmin": ("Climático", "Umidade relativa mínima da semana.", "ERA5/Open-Meteo"),
    "umidmax": ("Climático", "Umidade relativa máxima da semana.", "ERA5/Open-Meteo"),
    "tempmed_anomalia": ("Climático", "Desvio da temperatura média frente à média histórica da mesma semana do ano, calculada só com anos anteriores.", "Derivada"),
    "umidmed_anomalia": ("Climático", "Desvio da umidade média frente à média histórica da mesma semana do ano, só com anos anteriores.", "Derivada"),
    "semanas_favoraveis_8": ("Climático", "Quantas das últimas 8 semanas tiveram temperatura na faixa favorável ao Aedes aegypti.", "Derivada"),

    # Chuva
    "chuva_semana_mm": ("Precipitação", "Precipitação acumulada na semana, em milímetros.", "ERA5/Open-Meteo"),
    "chuva_max_diaria_mm": ("Precipitação", "Maior precipitação diária da semana. Distingue chuva torrencial de chuva distribuída.", "ERA5/Open-Meteo"),
    "chuva_dias_com_chuva": ("Precipitação", "Número de dias com chuva na semana.", "Derivada"),
    "chuva_anomalia": ("Precipitação", "Desvio da chuva frente à média histórica da mesma semana, só com anos anteriores.", "Derivada"),
    "semanas_secas_8": ("Precipitação", "Quantas das últimas 8 semanas foram secas. Seca leva a armazenar água em casa, o que cria criadouro.", "Derivada"),
    "semanas_torrenciais_4": ("Precipitação", "Quantas das últimas 4 semanas tiveram chuva torrencial. Chuva forte lava criadouros em vez de criá-los.", "Derivada"),
    "chuva_ausente": ("Qualidade", "Marca 1 quando a série de chuva não estava disponível para a semana.", "Derivada"),

    # Contextuais e vulnerabilidade
    "pop": ("Contextual", "População residente do município. Entre censos, é projeção do IBGE.", "IBGE"),
    "log_pop": ("Contextual", "Logaritmo da população. Entra no modelo porque o efeito do porte não é linear.", "Derivada"),
    "porte_populacional": ("Contextual", "Faixa de porte do município.", "Derivada"),
    "esgoto_inadequado_pct": ("Vulnerabilidade", "Domicílios sem esgotamento sanitário adequado, em porcentagem.", "IBGE Censo 2022"),
    "sem_agua_rede_pct": ("Vulnerabilidade", "Domicílios sem ligação à rede de água. Único indicador com associação significativa à incidência no território (ρ = +0,397; p = 0,020).", "IBGE Censo 2022"),
    "lixo_sem_coleta_pct": ("Vulnerabilidade", "Domicílios sem coleta de lixo, em porcentagem.", "IBGE Censo 2022"),
    "vulnerabilidade_socioambiental": ("Vulnerabilidade", "Índice que resume os três indicadores acima.", "Derivada"),

    # Canal endemico e risco
    "canal_q1": ("Risco", "Primeiro quartil histórico da incidência na mesma semana do ano, só com anos anteriores.", "Derivada"),
    "canal_mediana": ("Risco", "Mediana histórica da incidência na mesma semana do ano. Piso da faixa de alerta do canal endêmico.", "Derivada"),
    "canal_q3": ("Risco", "Terceiro quartil histórico. Acima dele a incidência entra em zona epidêmica.", "Derivada"),
    "anos_historico": ("Risco", "Quantos anos anteriores sustentam o canal endêmico daquela semana.", "Derivada"),
    "historico_insuficiente": ("Qualidade", "Marca 1 quando não há anos anteriores bastantes para o canal endêmico ser válido.", "Derivada"),
    "nivel_canal": ("Risco", "Nível de risco pela posição no canal endêmico, de 0 a 3.", "Derivada"),
    "nivel_absoluto": ("Risco", "Nível de risco pelos patamares absolutos de incidência: 10, 30 e 60 por 100 mil.", "Derivada"),
    "risco_codigo": ("Risco", "Nível final, o maior entre canal e patamar: 0 baixo, 1 moderado, 2 alto, 3 muito alto. É a base do alvo do modelo.", "Derivada"),
    "risco": ("Risco", "Nome do nível final: baixo, moderado, alto ou muito alto.", "Derivada"),
    "risco_sem_canal": ("Risco", "Nível calculado só pelos patamares absolutos, para medir o quanto o canal acrescenta.", "Derivada"),

    # Qualidade
    "completude": ("Qualidade", "Proporção estimada de notificação já digitada na semana. Abaixo de 1 a semana ainda vai crescer.", "Derivada"),
    "dado_provisorio": ("Qualidade", "Marca 1 quando a semana ainda está sujeita a revisão pelo atraso de notificação.", "Derivada"),
    "incerteza_nowcast": ("Qualidade", "Largura relativa do intervalo de credibilidade do nowcasting.", "Derivada"),
    "clima_imputado": ("Qualidade", "Marca 1 quando alguma variável climática da linha foi imputada.", "Derivada"),
}

PADROES = [
    (re.compile(r"^(.*)_lag(\d+)$"), "{base} com defasagem de {n} semanas."),
    (re.compile(r"^(.*)_mm(\d+)$"), "Média móvel de {n} semanas de {base}, deslocada em uma semana para não enxergar o presente."),
    (re.compile(r"^chuva_acum(\d+)$"), "Precipitação acumulada nas últimas {n} semanas."),
    (re.compile(r"^(.*)_imputado$"), "Marca 1 quando {base} foi imputada naquela linha."),
]

LEGIVEL = {
    "incidencia": "a incidência por 100 mil", "casos_est": "os casos estimados",
    "tempmed": "a temperatura média", "tempmin": "a temperatura mínima",
    "tempmax": "a temperatura máxima", "umidmed": "a umidade média",
    "umidmin": "a umidade mínima", "umidmax": "a umidade máxima",
    "chuva": "a precipitação semanal", "Rt": "o número reprodutivo efetivo",
    "p_rt1": "a probabilidade de Rt acima de 1",
}

BLOCO_POR_PREFIXO = [
    ("incidencia", "Epidemiológico"), ("casos", "Epidemiológico"),
    ("Rt", "Epidemiológico"), ("p_rt1", "Epidemiológico"),
    ("temp", "Climático"), ("umid", "Climático"), ("chuva", "Precipitação"),
]

ORDEM_BLOCOS = ["Identificação", "Epidemiológico", "Climático", "Precipitação",
                "Contextual", "Vulnerabilidade", "Risco", "Qualidade", "Outro"]

SEM_DESCRICAO = "—"

# Secoes que nao saem das colunas da base: as variaveis que painel_dados.py
# acrescenta ao artefato do painel, e os criterios operacionais do projeto.
APENDICE = """
## Variáveis do painel

Geradas por `src/vigia/painel_dados.py` sobre a base — existem em
`dados/processado/painel.csv`, não na base analítica.

| Variável | Tipo | Descrição |
|---|---|---|
| `alvo` | 0/1 | Desfecho da modelagem: haverá risco alto ou muito alto daqui a `horizonte` semanas. |
| `probabilidade_alerta` | float | Probabilidade prevista pelo modelo de que o alvo ocorra. |
| `fatores_alerta` | texto | As três variáveis que mais elevaram a probabilidade naquela linha. |
| `horizonte_semanas` | int | Antecedência do alerta, em semanas (padrão: 4). |

## Critérios operacionais

**Prevenção de vazamento temporal.** Nenhuma variável explicativa usa informação de
semana futura. Médias móveis são deslocadas por `shift(1)`; os quartis do canal endêmico
usam apenas anos anteriores ao da linha; a validação dos modelos é temporal em janela
expansiva, com o treino cortado pela data que o alvo observa.

**Tratamento de faltantes climáticos.** Falhas de até 3 semanas são interpoladas dentro
do município, só para a frente; o remanescente recebe a mediana da mesma semana
epidemiológica com anos anteriores. Toda imputação fica registrada em `*_imputado`.

**Casos notificados × casos estimados.** As semanas recentes vêm subnotificadas pelo
atraso de digitação. Incidência e risco são calculados sobre `casos_est`, e
`dado_provisorio` sinaliza a incompletude no painel. Na série histórica fechada os dois
praticamente coincidem — a correção age nas semanas recentes, onde é decisiva.
"""


# Glossario: o que cada termo da tabela significa, para quem nao e da area.
# Mora aqui, junto do gerador, para que a explicacao acompanhe a tabela. O
# teste em testes/test_dicionario.py falha se aparecer na tabela um tipo, um
# papel ou uma fonte que o glossario nao explica.
GLOSSARIO = [
    # (grupo, termo, significado)
    ("Como ler a tabela", "Coluna",
     "O nome de uma informação guardada na base. Cada linha da base é um "
     "município numa semana; cada coluna é um dado sobre essa linha, como os "
     "casos ou a chuva."),
    ("Como ler a tabela", "Bloco",
     "O tema a que a coluna pertence: identificação, epidemiológico, "
     "climático, precipitação, contextual, vulnerabilidade, risco ou qualidade "
     "do dado."),
    ("Como ler a tabela", "Tipo",
     "A espécie de dado que a coluna guarda: número inteiro, número com casas "
     "decimais ou texto."),
    ("Como ler a tabela", "Papel",
     "Como a coluna entra na previsão: se o modelo a usa para calcular o "
     "risco ou se ela só sustenta cálculos e o painel."),
    ("Como ler a tabela", "Preenchida (%)",
     "De cada 100 linhas da base, em quantas a coluna tem valor. Abaixo de "
     "100% falta valor em parte das linhas, em geral por construção: o "
     "primeiro ano da série, por exemplo, não tem anos anteriores para "
     "comparar."),
    ("Como ler a tabela", "Fonte",
     "De onde o dado vem: de um sistema público ou de um cálculo do próprio "
     "projeto."),

    ("Tipos de dado", "int64",
     "Número inteiro, sem casas decimais. Exemplo: casos notificados."),
    ("Tipos de dado", "float64",
     "Número com casas decimais. Exemplo: incidência. Aparece também em "
     "colunas de contagem quando falta valor em alguma linha, porque o valor "
     "vazio só existe entre os números decimais."),
    ("Tipos de dado", "object",
     "Texto. Exemplos: nome do município, nível de risco."),

    ("Papéis na previsão", "preditor essencial",
     "Variável sem a qual a previsão não se sustenta. Está sempre disponível "
     "na semana mais recente, o que permite ao alerta funcionar sem esperar "
     "outras fontes."),
    ("Papéis na previsão", "preditor",
     "Variável que o modelo usa para calcular a probabilidade de risco. "
     "Inclui as essenciais."),
    ("Papéis na previsão", "origem do alvo",
     "Coluna da qual sai o que o modelo tenta prever: o risco alto ou muito "
     "alto quatro semanas à frente."),
    ("Papéis na previsão", "apoio",
     "Coluna que sustenta cálculos, conferências ou o painel, mas não entra "
     "no treino do modelo."),

    ("Fontes", "InfoDengue",
     "Sistema da Fiocruz e da FGV que processa as notificações do SINAN e "
     "publica, por município e semana, os casos, as estimativas e os "
     "indicadores de transmissão."),
    ("Fontes", "SINAN",
     "Sistema de Informação de Agravos de Notificação, do Ministério da "
     "Saúde, onde os casos de dengue são registrados."),
    ("Fontes", "IBGE",
     "Instituto Brasileiro de Geografia e Estatística. Fornece a população, "
     "os mapas e os indicadores do Censo 2022."),
    ("Fontes", "ERA5/Open-Meteo",
     "Reanálise climática do centro europeu ECMWF, acessada pela plataforma "
     "Open-Meteo. Reanálise é um modelo que combina observações para estimar "
     "o clima em cada ponto, inclusive onde não há estação meteorológica."),
    ("Fontes", "Derivada",
     "Calculada pelo próprio projeto a partir de outras colunas."),

    ("Termos das descrições", "Semana epidemiológica",
     "Semana padronizada da vigilância em saúde, de domingo a sábado, "
     "numerada de 1 a 52 ou 53 ao longo do ano."),
    ("Termos das descrições", "Incidência por 100 mil",
     "Casos estimados divididos pela população e multiplicados por 100 mil. "
     "Permite comparar municípios de tamanhos diferentes."),
    ("Termos das descrições", "Nowcasting",
     "Técnica que estima quantos casos de uma semana ainda vão ser "
     "registrados, corrigindo o atraso de notificação. Os casos estimados "
     "vêm dela."),
    ("Termos das descrições", "Casos notificados e casos estimados",
     "Notificados são os registrados até agora; estimados incluem os que "
     "ainda vão entrar no sistema. Nas semanas recentes, os estimados são "
     "maiores."),
    ("Termos das descrições", "Dado provisório",
     "Semana cuja notificação ainda não terminou de ser registrada. Os "
     "números tendem a subir."),
    ("Termos das descrições", "Defasagem",
     "O valor de semanas anteriores. Com defasagem de 4 semanas significa o "
     "valor de quatro semanas atrás."),
    ("Termos das descrições", "Média móvel",
     "Média das últimas semanas, que suaviza a oscilação de uma semana para "
     "outra. É calculada até a semana anterior, para não usar o próprio dado "
     "que se quer prever."),
    ("Termos das descrições", "Anomalia",
     "Diferença entre o valor da semana e a média histórica da mesma época "
     "do ano."),
    ("Termos das descrições", "Canal endêmico",
     "Faixa de incidência esperada para cada semana do ano, construída com "
     "os anos anteriores do próprio município. Acima do limite superior, a "
     "incidência está em zona epidêmica."),
    ("Termos das descrições", "Quartil",
     "Ponto que divide os valores históricos em quatro partes iguais. O "
     "terceiro quartil (Q3) é o valor abaixo do qual ficaram 75% das semanas "
     "anteriores; a mediana é o do meio."),
    ("Termos das descrições", "Rt",
     "Número reprodutivo efetivo: quantas pessoas, em média, cada caso "
     "infecta. Acima de 1 a transmissão cresce; abaixo de 1, diminui."),
    ("Termos das descrições", "Probabilidade de Rt acima de 1",
     "Chance de a transmissão estar crescendo na semana. É a variável do "
     "único alarme que se sustentou no histórico do território."),
    ("Termos das descrições", "Vazamento temporal",
     "Erro em que o modelo usa, sem perceber, informação do futuro. Infla o "
     "desempenho medido e falha em operação real; o projeto testa sua "
     "ausência a cada execução."),
]


def _descrever(coluna: str):
    if coluna in DESCRICOES:
        return DESCRICOES[coluna]
    for padrao, molde in PADROES:
        m = padrao.match(coluna)
        if not m:
            continue
        raiz = m.group(1)
        n = m.group(2) if m.lastindex and m.lastindex > 1 else m.group(1)
        legivel = LEGIVEL.get(raiz, raiz.replace("_", " "))
        texto = molde.format(base=legivel, n=n)
        bloco = next((b for p, b in BLOCO_POR_PREFIXO if coluna.startswith(p)),
                     "Qualidade")
        return (bloco, texto[0].upper() + texto[1:], "Derivada")
    return ("Outro", SEM_DESCRICAO, SEM_DESCRICAO)


def _papel(coluna: str) -> str:
    if coluna in VARIAVEIS_ESSENCIAIS:
        return "preditor essencial"
    if coluna in VARIAVEIS:
        return "preditor"
    if coluna == "risco_codigo":
        return "origem do alvo"
    return "apoio"


def gerar(base: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por coluna da base: bloco, tipo, papel, preenchimento, fonte."""
    linhas = []
    for coluna in base.columns:
        bloco, texto, fonte = _descrever(coluna)
        linhas.append({
            "coluna": coluna,
            "bloco": bloco,
            "tipo": str(base[coluna].dtype),
            "descricao": texto,
            "fonte": fonte,
            "papel": _papel(coluna),
            "preenchida_pct": round(100.0 * base[coluna].notna().mean(), 1),
        })
    tabela = pd.DataFrame(linhas)
    ordem = {b: i for i, b in enumerate(ORDEM_BLOCOS)}
    return (tabela.sort_values(["bloco", "coluna"],
                               key=lambda s: s.map(ordem).fillna(99)
                               if s.name == "bloco" else s)
                  .reset_index(drop=True))


def sem_descricao(tabela: pd.DataFrame) -> list[str]:
    """Colunas que o dicionario ainda nao sabe explicar -- o teste as acusa."""
    return tabela.loc[tabela["descricao"] == SEM_DESCRICAO, "coluna"].tolist()


def glossario() -> pd.DataFrame:
    """O glossario como tabela: grupo, termo, significado."""
    return pd.DataFrame(GLOSSARIO, columns=["grupo", "termo", "significado"])


def salvar(base: pd.DataFrame, caminho_md: Path = SAIDA_MD,
           caminho_csv: Path = SAIDA_CSV,
           caminho_glossario: Path = SAIDA_GLOSSARIO) -> pd.DataFrame:
    """Grava o markdown de leitura e os CSVs que a aba do painel consome."""
    tabela = gerar(base)
    glossario().to_csv(caminho_glossario, index=False, encoding="utf-8",
                       lineterminator="\n")

    tabela.to_csv(caminho_csv, index=False, encoding="utf-8",
                  lineterminator="\n")

    partes = ["# Dicionário de Dados — VIGIA-Dengue\n"]
    partes.append(
        "Gerado da base analítica por `src/vigia/executar_dicionario.py`: "
        f"{len(base.columns)} colunas, {len(base):,} linhas, "
        f"{base['cod_ibge'].nunique()} municípios da RIDE-DF."
        .replace(",", "."))
    partes.append(
        f"\n**Papel** diz como a coluna entra na previsão: *preditor essencial* "
        f"são as {len(VARIAVEIS_ESSENCIAIS)} sem as quais uma previsão não se "
        f"sustenta; *preditor* são as {len(VARIAVEIS)} que o modelo usa ao todo; "
        "*origem do alvo* é de onde sai o desfecho; *apoio* sustenta cálculo, "
        "conferência e painel sem entrar no treino.\n")

    for bloco in ORDEM_BLOCOS:
        sub = tabela[tabela["bloco"] == bloco]
        if sub.empty:
            continue
        partes.append(f"\n## {bloco} — {len(sub)} colunas\n")
        partes.append("| Coluna | Tipo | Papel | Preenchida | Fonte | Descrição |")
        partes.append("|---|---|---|---|---|---|")
        for _, r in sub.iterrows():
            partes.append(
                f"| `{r['coluna']}` | {r['tipo']} | {r['papel']} | "
                f"{r['preenchida_pct']:.1f}% | {r['fonte']} | {r['descricao']} |")

    partes.append(APENDICE)

    partes.append("\n## Glossário\n")
    partes.append("O que cada termo da tabela significa, para quem não é da área.\n")
    for grupo, linhas in glossario().groupby("grupo", sort=False):
        partes.append(f"\n### {grupo}\n")
        for _, linha in linhas.iterrows():
            partes.append(f"- **{linha['termo']}** — {linha['significado']}")
    caminho_md.write_text("\n".join(partes) + "\n", encoding="utf-8",
                          newline="\n")
    return tabela
