# Dicionário de Dados — VIGIA-Dengue

Documento da **Etapa 1** do projeto. Descreve a tabela analítica principal, no formato
**município–semana epidemiológica**, gerada por `src/vigia/base_analitica.py` e
`src/vigia/risco.py`.

| Item | Valor |
|---|---|
| Unidade de análise | Município × semana epidemiológica |
| Território piloto | Distrito Federal + RIDE-DF (33 municípios: 1 DF, 29 GO, 3 MG) |
| Período | 2014-SE01 a 2026-SE32 (659 semanas) |
| Dimensões | 21.747 linhas × 105 colunas |
| Chave primária | `cod_ibge` + `se_codigo` |
| Fonte epidemiológica e climática | InfoDengue (Fiocruz/FGV), API `alertcity` |
| Fonte de população e cartografia | IBGE (API de localidades e de malhas) |

---

## 1. Identificação

| Variável | Tipo | Descrição |
|---|---|---|
| `cod_ibge` | int | Código IBGE de 7 dígitos do município. Chave de integração entre todas as bases. |
| `municipio` | texto | Nome do município conforme o IBGE. |
| `uf` | texto | Unidade federativa (DF, GO ou MG). |
| `se_codigo` | int | Semana epidemiológica no formato AAAASS (ex.: 202432). |
| `ano` | int | Ano epidemiológico, derivado de `se_codigo`. |
| `semana` | int | Semana epidemiológica de 1 a 53. |
| `data_ini_se` | data | Data do domingo que inicia a semana epidemiológica. |

## 2. Bloco epidemiológico

| Variável | Tipo | Descrição |
|---|---|---|
| `casos` | int | Casos prováveis **notificados** e já digitados no sistema na semana. |
| `casos_est` | float | Casos estimados por *nowcasting*, **corrigidos pelo atraso de notificação**. É a variável de referência do projeto. |
| `casos_est_min` / `casos_est_max` | float | Limites do intervalo de credibilidade da estimativa. |
| `incidencia_100k` | float | Incidência semanal por 100 mil habitantes, calculada como `casos_est / pop × 100.000`. **Desfecho principal.** |
| `Rt` | float | Número reprodutivo efetivo estimado pelo InfoDengue. Acima de 1 indica transmissão em expansão. |
| `casos_est_lag{1,2,3,4,8}` | float | Casos estimados defasados em 1, 2, 3, 4 e 8 semanas. |
| `incidencia_lag{1,2,3,4,8}` | float | Incidência defasada nos mesmos intervalos. |
| `casos_est_mm{3,4,8}` | float | Médias móveis dos casos estimados. Calculadas **até a semana anterior** (`shift(1)`), nunca incluindo a semana corrente. |
| `incidencia_mm{3,4,8}` | float | Médias móveis da incidência, mesma regra. |
| `razao_mm3_mm8` | float | Razão entre a média móvel curta e a longa. Acima de 1 indica aceleração recente. |
| `variacao_semanal` | float | Variação relativa dos casos estimados frente à semana anterior. |

## 3. Bloco climático

| Variável | Tipo | Descrição |
|---|---|---|
| `tempmed`, `tempmin`, `tempmax` | float | Temperaturas média, mínima e máxima da semana (°C). |
| `umidmed`, `umidmin`, `umidmax` | float | Umidade relativa média, mínima e máxima (%). |
| `{tempmed,tempmin,tempmax,umidmed}_lag{1,2,3,4,6,8}` | float | Defasagens climáticas. A janela de 4 a 8 semanas cobre o intervalo entre condição favorável ao vetor e aparecimento de casos. |
| `tempmed_anomalia`, `umidmed_anomalia` | float | Desvio em relação à média histórica da **mesma semana do ano** no município. Isola o sinal anômalo da sazonalidade normal. |
| `semanas_favoraveis_8` | float | Nº de semanas, entre as 8 anteriores, com temperatura média na faixa favorável ao *Aedes aegypti* (21 a 32 °C). |
| `receptivo`, `transmissao` | int | Indicadores de receptividade e transmissão do InfoDengue. |

## 4. Bloco contextual

| Variável | Tipo | Descrição |
|---|---|---|
| `pop` | int | População residente estimada (denominador da incidência). |
| `log_pop` | float | Logaritmo decimal da população; estabiliza a escala na modelagem. |
| `porte_populacional` | categoria | `pequeno` (<20 mil), `medio` (20–100 mil), `grande` (100–500 mil), `metropole` (>500 mil). |

## 5. Bloco operacional e de qualidade

| Variável | Tipo | Descrição |
|---|---|---|
| `completude` | float | Razão `casos / casos_est`, limitada a 1. Mede o quanto da notificação já foi digitada. Semana sem nenhum caso estimado recebe valor 1 (dado legítimo, não incompleto). |
| `dado_provisorio` | 0/1 | Marca 1 quando `completude < 0,90`. Sinaliza semanas cujo número de casos ainda deve subir. |
| `incerteza_nowcast` | float | Largura relativa do intervalo de estimativa: `(max − min) / casos_est`. |
| `{variavel}_imputado` | 0/1 | Marca 1 quando o valor climático original estava ausente e foi imputado. |
| `clima_imputado` | 0/1 | Marca 1 se qualquer variável climática da linha foi imputada. |
| `historico_insuficiente` | 0/1 | Marca as 8 primeiras semanas de cada município, sem histórico para as janelas móveis. |
| `anos_historico` | int | Nº de anos anteriores disponíveis para o cálculo do canal endêmico. |

## 6. Bloco de risco

| Variável | Tipo | Descrição |
|---|---|---|
| `canal_q1`, `canal_mediana`, `canal_q3` | float | Quartis históricos da incidência **da mesma semana do ano** no município, usando apenas anos anteriores e janela de ±2 semanas. |
| `nivel_canal` | int | Nível pelo canal endêmico: 0 abaixo da mediana, 1 até o Q3, 2 acima do Q3, 3 acima do dobro do Q3. `-1` quando não há histórico suficiente. |
| `nivel_absoluto` | int | Nível pelos patamares absolutos de incidência: 0 (<10), 1 (10–30), 2 (30–60), 3 (>60) por 100 mil. |
| `risco_codigo` | int | Nível final: o **maior** entre `nivel_canal` e `nivel_absoluto`. |
| `risco` | categoria ordenada | `baixo`, `moderado`, `alto`, `muito alto`. |
| `risco_sem_canal` | 0/1 | Marca 1 quando a classificação não pôde usar o canal endêmico. |

## 7. Variáveis do painel

Geradas por `src/vigia/painel_dados.py`.

| Variável | Tipo | Descrição |
|---|---|---|
| `alvo` | 0/1 | Desfecho da modelagem: haverá risco alto ou muito alto daqui a `horizonte` semanas. |
| `probabilidade_alerta` | float | Probabilidade prevista pelo modelo de que o alvo ocorra. |
| `fatores_alerta` | texto | As três variáveis que mais elevaram a probabilidade naquela linha (explicação simplificada do alerta). |
| `horizonte_semanas` | int | Antecedência do alerta, em semanas (padrão: 4). |

---

## 8. Critérios operacionais

**Prevenção de vazamento temporal.** Nenhuma variável explicativa usa informação de
semana futura. Médias móveis são deslocadas por `shift(1)`; os quartis do canal endêmico
usam apenas anos anteriores ao da linha; a validação dos modelos é temporal em janela
expansiva (treina até o ano *t−1*, avalia em *t*).

**Tratamento de faltantes climáticos.** Falhas de até 3 semanas são interpoladas
linearmente dentro do município; o remanescente recebe a mediana da mesma semana
epidemiológica naquele município. Toda imputação fica registrada em `*_imputado`.

**Casos notificados × casos estimados.** As semanas mais recentes têm notificação
incompleta por atraso de digitação — na última semana da série, um município chegou a
exibir 92 casos notificados contra 184 estimados. Por isso a incidência e o risco são
calculados sobre `casos_est`, e `dado_provisorio` sinaliza a incompletude no painel.
