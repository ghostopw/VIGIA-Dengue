# Achados da modelagem — o que foi medido

Tudo aqui saiu de medição no dado do projeto, com a partição temporal em janela
expansiva: treina no passado, avalia num ano fechado, nunca ao contrário. Onde o
resultado contraria o que se esperava, ele está registrado assim mesmo.

---

## 1. Chuva ou seca? A chuva, com dois meses de atraso

Os casos se concentram na estação chuvosa, mas **o pico de casos não coincide com
o pico de chuva**.

| | Pico | Vale |
|---|---|---|
| Chuva | nov–dez (43 mm/semana) | jul–ago (0,1 mm) |
| Casos | **mar–abr (81 / 100 mil)** | **ago–set (7 / 100 mil)** |

A correlação cruzada dá o mecanismo: a chuva antecede a incidência com **máximo
em 8 semanas** (r = +0,270). A umidade antecede em 4 semanas (r = +0,234).

A estação chuvosa tem **1,77×** a incidência da seca (39,9 contra 22,5 por 100 mil).

Abril é o mês mais revelador: incidência quase no máximo (81,1) com chuva já baixa
(17 mm). É o efeito acumulado do que choveu dois meses antes.

---

## 2. Cidades carentes: só a falta de água encanada aparece

Correlação de Spearman entre indicador municipal e incidência média, nos 34
municípios do território do painel:

| Indicador | ρ | p |
|---|---|---|
| **Sem água de rede** | **+0,397** | **0,020** |
| Esgoto inadequado | +0,117 | 0,51 |
| Lixo sem coleta | −0,287 | 0,10 |

Só a falta de ligação à rede de água mostra associação — e é justamente a do
mecanismo direto: sem rede, o domicílio armazena em caixa e tonel, que é criadouro
clássico do *Aedes aegypti*.

A sazonalidade quase não muda com a vulnerabilidade: a razão chuvosa/seca é 1,89,
1,88 e 1,54 nos tercis de menor a maior vulnerabilidade.

---

## 3. Fluxo das águas: mede-se, mas não prevê

O *Aedes* se cria em água **parada**, não corrente. O que decide se a chuva escoa
ou empoça é a drenagem, e o Censo 2022 mede isso por face de rua.

**Por Região Administrativa** — 18% dos domicílios em rua sem boca de lobo no
Plano Piloto, contra 76% na Fercal.

**Por setor censitário** — 653 dos 4.913 setores do DF com dado têm **100% das
faces sem bueiro**. O pior deles fica no Sol Nascente/Pôr do Sol: 100% sem bueiro,
88% sem pavimento, 89% dos domicílios com esgotamento inadequado.

**Por município no Centro-Oeste** — mediana de 82,6% sem bueiro; Brasília em 47%.

### Mas como preditor, não acrescenta nada

Acrescentar `sem_bueiro_pct` e `sem_pavimento_pct` ao modelo:

| | AUC | AUPRC | Brier |
|---|---|---|---|
| Sem drenagem | 0,8349 | 0,7914 | 0,1679 |
| Com drenagem | 0,8350 | 0,7913 | 0,1676 |

Diferença de 0,0001 — nula. Avaliado só em Brasília, +0,0012, igualmente nulo.

**Por quê.** A drenagem é estática no tempo: descreve o lugar, não a semana. Ela
pode deslocar o patamar de risco de um município, mas não tem como informar
*quando* o surto vem — e o alerta pergunta exatamente isso, com quatro semanas de
antecedência. O modelo já tem `log_pop` e o bloco de vulnerabilidade, que carregam
informação estática parecida.

**O que isso não significa.** Não significa que a drenagem seja irrelevante para
dengue. Significa que ela serve para **direcionar**, não para **antecipar**: diz
onde mandar a equipe, o mutirão e a remoção de criadouro. É por isso que ela está
no mapa por quadra e fora do modelo.

---

## 4. Rede neural: perdeu para o LightGBM

Treinada nos 467 municípios do Centro-Oeste, 307.198 linhas. GRU de duas camadas
sobre janela de 16 semanas com seis canais crus, mais ramo estático.

Os três correndo no **mesmo dado, mesma partição e mesma informação**:

| Modelo | AUC | AUPRC | Brier |
|---|---|---|---|
| **LightGBM + variáveis à mão** | **0,8349** | **0,7914** | **0,1679** |
| LightGBM + janela achatada | 0,8199 | 0,7716 | 0,1775 |
| Rede neural (GRU) | 0,7815 | 0,7281 | 0,1951 |

Perdeu nos cinco anos avaliados, sem exceção. E o ensemble também não salva:

| Combinação | AUC |
|---|---|
| LightGBM sozinho | 0,8248 |
| 30% rede + 70% LightGBM | 0,8225 |
| Média simples | 0,8164 |
| Rede sozinha | 0,7892 |

### As duas leituras

**A estrutura temporal não ajudou.** Com a janela achatada em colunas planas, o
LightGBM (0,820) supera a rede (0,782) tendo exatamente a mesma informação. Saber
que aquelas colunas formam uma sequência não valeu nada aqui.

**A engenharia de variáveis venceu o aprendizado da defasagem.** As variáveis
escritas à mão (0,835) superam a janela crua (0,820). As médias móveis e o canal
endêmico que alguém escolheu carregam mais do que a rede conseguiu extrair
sozinha.

Isso é coerente com o que se observa em dado tabular em painel, onde ensembles de
árvore costumam dominar. **O painel segue com o LightGBM.** Trocar um modelo que
funciona por outro mais sofisticado que erra mais não é avanço.

---

## 5. Treinar no Centro-Oeste ajuda Brasília? Pouco

Mesmas variáveis, mesma partição, avaliado **só nas semanas de Brasília**:

| Treino | AUC | AUPRC | Brier |
|---|---|---|---|
| Centro-Oeste (467 municípios) | **0,7461** | **0,7127** | **0,2215** |
| RIDE (34 municípios) | 0,7391 | 0,6939 | 0,2273

Melhor nas três métricas, mas por +0,007 de AUC, com quatro anos avaliáveis e
cerca de 52 semanas por ano. Dois anos melhores, dois piores. É ganho real na
direção esperada, mas dentro do ruído — não a transformação que 15× mais dado
poderia sugerir.

Uma explicação provável: Brasília é atípica no Centro-Oeste. Tem 3,8% de
esgotamento inadequado contra mediana regional de 50%, e 47% de ruas sem bueiro
contra 82,6%. O modelo aprende sobretudo com municípios muito mais precários, e
aplicar isso ao DF é extrapolar para fora do que se viu.

---

## O que fazer com isto

1. **O modelo do painel continua o LightGBM** com as variáveis do projeto.
2. **A drenagem fica no mapa, não no modelo** — é camada de direcionamento.
3. **O treino no Centro-Oeste vale a pena**, pelo ganho pequeno e consistente em
   direção certa, e porque dá massa para futuras variantes.
4. **A rede neural fica registrada como tentativa que não venceu.** Se algum dia
   houver série por Região Administrativa, o quadro muda: aí a estrutura espacial
   passa a existir e uma rede com componente espacial volta a fazer sentido.

---

## 6. Vazamento temporal: existia, foi corrigido, mas não inflava o número

Um levantamento independente apontou cinco pontos em que informação do futuro
entrava no treino. Conferi os cinco linha a linha e todos existiam:

| Arquivo | O que fazia |
|---|---|
| `base_analitica.py:53` | `interpolate(limit_direction="both")` — tapava buraco do passado com valor futuro |
| `base_analitica.py:56` | mediana sazonal sobre a série inteira, para imputar clima |
| `base_analitica.py:156` | `chuva_anomalia` medida contra média que inclui anos posteriores |
| `base_analitica.py:175` | idem para `tempmed_anomalia` e `umidmed_anomalia` |
| `modelagem.py:190` | `treino = ano < ano` deixava passar dezembro, cujo alvo cai no ano de teste |

O quinto é o mais direto: uma linha da semana 50 de 2020 tem alvo na semana 2 de
2021. Medido no Centro-Oeste: **1.860 linhas por dobra**, 8.382 nas cinco.

Todos foram corrigidos — a anomalia sazonal passou a usar janela expansiva (só
anos anteriores), a interpolação só preenche para a frente, e a dobra corta pela
data que o alvo observa, não pela data da linha.

### O efeito medido foi nulo

| Correção | AUC antes | AUC depois |
|---|---|---|
| Corte da dobra | 0,8349 | 0,8350 |
| Anomalia sazonal expansiva | 0,8350 | 0,8348 |

Isto é uma boa notícia, e vale dizer com clareza: **o desempenho relatado pelo
projeto não estava inflado por vazamento.** As 1.860 linhas eram 1% do treino, e
as anomalias sazonais têm importância baixa perto do bloco epidemiológico, que
responde por ~60% do ganho.

As correções ficam de pé por serem corretas, não por mudarem o número. Se algum
dia o bloco climático ganhar peso — com chuva por município no Centro-Oeste, por
exemplo —, o vazamento passaria a doer, e aí já estará resolvido.

---

## 7. Em quantos por cento o modelo acerta

AUC não é percentual de acerto. As medidas que são, ao limiar em uso, com
horizonte de 4 semanas:

### No Centro-Oeste, 467 municípios

| Medida | Valor | Leitura |
|---|---|---|
| Sensibilidade | **77,9%** | pega 78 de cada 100 surtos |
| Especificidade | 71,7% | reconhece 72% das semanas calmas |
| VPP | 65,7% | quando alerta, acerta 2 de cada 3 vezes |
| Acurácia | 75,3% | |

### Só em Brasília, e aqui havia um defeito

A taxa base de Brasília é alta: em **121 das 209 semanas** avaliadas (58%) havia
risco alto no horizonte. E o modelo prevê mediana de 0,84. Com o limiar em 0,50,
o resultado era:

| Limiar | Sensib. | Especif. | VPP | Alertas/ano |
|---|---|---|---|---|
| 0,50 (antigo padrão) | 96,7% | **19,3%** | 62,2% | 47 |
| 0,70 | 85,1% | 43,2% | 67,3% | 38 |
| **0,80 (novo padrão)** | **71,1%** | **67,0%** | **74,8%** | **29** |
| 0,85 | 64,5% | 78,4% | 80,4% | 24 |
| 0,90 | 47,1% | 88,6% | 85,1% | 17 |

Especificidade de 19% significa alertar em quase toda semana. **Alerta que
dispara sempre não é alerta** — vira ruído, e depois de um mês ninguém abre.

O padrão passou para **0,80**, onde o alerta acerta 3 de cada 4 disparos e cai
para 29 por ano. O custo é perder os surtos mais fracos: a sensibilidade vai de
97% para 71%. É a troca certa para um alerta operacional, e o controle continua
na barra lateral para quem quiser outro ponto.

### A limitação de fundo

Um alerta que dispara em 58% das semanas tem pouco a informar, qualquer que seja
o limiar. Isso não é defeito do modelo, e sim da estratificação: o critério de
risco marca Brasília como alto ou muito alto em metade das semanas do ano. Para
o alerta ganhar poder de discriminação, o desfecho precisaria ser mais raro —
por exemplo, exigir crescimento acelerado além do patamar, ou usar percentil
específico de Brasília em vez do corte regional.
