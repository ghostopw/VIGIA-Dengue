# Dicionário de Dados — VIGIA-Dengue

Gerado da base analítica por `src/vigia/executar_dicionario.py`: 128 colunas. 22.440 linhas. 34 municípios da RIDE-DF.

**Papel** diz como a coluna entra na previsão: *preditor essencial* são as 16 sem as quais uma previsão não se sustenta; *preditor* são as 23 que o modelo usa ao todo; *origem do alvo* é de onde sai o desfecho; *apoio* sustenta cálculo, conferência e painel sem entrar no treino.


## Identificação — 12 colunas

| Coluna | Tipo | Papel | Preenchida | Fonte | Descrição |
|---|---|---|---|---|---|
| `Localidade_id` | int64 | apoio | 100.0% | InfoDengue | Identificador interno de localidade do InfoDengue. |
| `ano` | int64 | apoio | 100.0% | Derivada | Ano epidemiológico. Define as dobras da validação temporal. |
| `cod_ibge` | int64 | apoio | 100.0% | IBGE | Código IBGE de 7 dígitos do município. Chave de integração entre todas as bases. |
| `data_iniSE` | object | apoio | 100.0% | InfoDengue | Mesma data, no nome original do InfoDengue. Mantida para rastreio. |
| `data_ini_se` | object | apoio | 100.0% | InfoDengue | Data do primeiro dia da semana epidemiológica (domingo). Chave temporal. |
| `id` | int64 | apoio | 100.0% | InfoDengue | Identificador da linha no InfoDengue. |
| `municipio` | object | apoio | 100.0% | IBGE | Nome do município conforme o IBGE. |
| `municipio_nome` | object | apoio | 100.0% | InfoDengue | Nome do município conforme o InfoDengue. Mantido para conferência da junção. |
| `se_codigo` | int64 | apoio | 100.0% | InfoDengue | Semana epidemiológica no formato AAAASS, ex. 202633. |
| `semana` | int64 | preditor essencial | 100.0% | Derivada | Semana epidemiológica no ano, de 1 a 53. Entra no modelo como marcador de sazonalidade. |
| `uf` | object | apoio | 100.0% | IBGE | Unidade federativa: DF, GO ou MG. |
| `versao_modelo` | object | apoio | 100.0% | InfoDengue | Versão do modelo de nowcasting que gerou os casos estimados. |

## Epidemiológico — 41 colunas

| Coluna | Tipo | Papel | Preenchida | Fonte | Descrição |
|---|---|---|---|---|---|
| `Rt` | float64 | preditor essencial | 100.0% | InfoDengue | Número reprodutivo efetivo estimado pelo InfoDengue. |
| `Rt_lag1` | float64 | preditor | 99.8% | Derivada | O número reprodutivo efetivo com defasagem de 1 semanas. |
| `Rt_lag2` | float64 | preditor | 99.7% | Derivada | O número reprodutivo efetivo com defasagem de 2 semanas. |
| `casconf` | float64 | apoio | 0.0% | InfoDengue | Casos confirmados em laboratório. Vem 100% vazia da fonte para este território. |
| `casos` | int64 | apoio | 100.0% | InfoDengue/SINAN | Casos notificados de dengue na semana. Subnotificado nas semanas recentes. |
| `casos_est` | float64 | apoio | 100.0% | InfoDengue | Casos estimados por nowcasting, corrigindo o atraso de notificação. É a base de todo o cálculo de risco. |
| `casos_est_lag1` | float64 | apoio | 99.8% | Derivada | Os casos estimados com defasagem de 1 semanas. |
| `casos_est_lag2` | float64 | apoio | 99.7% | Derivada | Os casos estimados com defasagem de 2 semanas. |
| `casos_est_lag3` | float64 | apoio | 99.5% | Derivada | Os casos estimados com defasagem de 3 semanas. |
| `casos_est_lag4` | float64 | apoio | 99.4% | Derivada | Os casos estimados com defasagem de 4 semanas. |
| `casos_est_lag8` | float64 | apoio | 98.8% | Derivada | Os casos estimados com defasagem de 8 semanas. |
| `casos_est_max` | float64 | apoio | 99.9% | InfoDengue | Limite superior do intervalo de credibilidade dos casos estimados. |
| `casos_est_min` | int64 | apoio | 100.0% | InfoDengue | Limite inferior do intervalo de credibilidade dos casos estimados. |
| `casos_est_mm3` | float64 | preditor essencial | 99.7% | Derivada | Média móvel de 3 semanas de os casos estimados, deslocada em uma semana para não enxergar o presente. |
| `casos_est_mm4` | float64 | apoio | 99.7% | Derivada | Média móvel de 4 semanas de os casos estimados, deslocada em uma semana para não enxergar o presente. |
| `casos_est_mm8` | float64 | preditor essencial | 99.7% | Derivada | Média móvel de 8 semanas de os casos estimados, deslocada em uma semana para não enxergar o presente. |
| `casprov` | int64 | apoio | 100.0% | InfoDengue | Casos prováveis notificados. |
| `casprov_est` | float64 | apoio | 0.0% | InfoDengue | Casos prováveis estimados por nowcasting. Vem 100% vazia da fonte para este território. |
| `casprov_est_max` | float64 | apoio | 0.0% | InfoDengue | Limite superior dos casos prováveis estimados. Vem 100% vazia da fonte. |
| `casprov_est_min` | float64 | apoio | 0.0% | InfoDengue | Limite inferior dos casos prováveis estimados. Vem 100% vazia da fonte. |
| `incidencia_100k` | float64 | preditor essencial | 100.0% | Derivada | Casos estimados por 100 mil habitantes na semana. Variável mais importante do modelo. |
| `incidencia_lag1` | float64 | preditor essencial | 99.8% | Derivada | A incidência por 100 mil com defasagem de 1 semanas. |
| `incidencia_lag2` | float64 | preditor essencial | 99.7% | Derivada | A incidência por 100 mil com defasagem de 2 semanas. |
| `incidencia_lag3` | float64 | apoio | 99.5% | Derivada | A incidência por 100 mil com defasagem de 3 semanas. |
| `incidencia_lag4` | float64 | preditor essencial | 99.4% | Derivada | A incidência por 100 mil com defasagem de 4 semanas. |
| `incidencia_lag8` | float64 | apoio | 98.8% | Derivada | A incidência por 100 mil com defasagem de 8 semanas. |
| `incidencia_mm3` | float64 | preditor essencial | 99.7% | Derivada | Média móvel de 3 semanas de a incidência por 100 mil, deslocada em uma semana para não enxergar o presente. |
| `incidencia_mm4` | float64 | apoio | 99.7% | Derivada | Média móvel de 4 semanas de a incidência por 100 mil, deslocada em uma semana para não enxergar o presente. |
| `incidencia_mm8` | float64 | preditor essencial | 99.7% | Derivada | Média móvel de 8 semanas de a incidência por 100 mil, deslocada em uma semana para não enxergar o presente. |
| `nivel` | int64 | apoio | 100.0% | InfoDengue | Nível de alerta do próprio InfoDengue (1 verde a 4 vermelho). Não é o risco do projeto. |
| `nivel_inc` | int64 | preditor | 100.0% | InfoDengue | Nível de incidência segundo o InfoDengue. |
| `notif_accum_year` | int64 | apoio | 100.0% | InfoDengue | Notificações acumuladas no ano até a semana. |
| `p_inc100k` | float64 | apoio | 100.0% | InfoDengue | Incidência por 100 mil calculada pelo próprio InfoDengue. Mantida para conferência. |
| `p_rt1` | float64 | preditor essencial | 100.0% | InfoDengue | Probabilidade de o Rt ser maior que 1, isto é, de a transmissão estar crescendo. |
| `p_rt1_lag1` | float64 | preditor | 99.8% | Derivada | A probabilidade de Rt acima de 1 com defasagem de 1 semanas. |
| `p_rt1_lag2` | float64 | preditor | 99.7% | Derivada | A probabilidade de Rt acima de 1 com defasagem de 2 semanas. |
| `razao_mm3_mm8` | float64 | preditor essencial | 100.0% | Derivada | Razão entre a média móvel de 3 e a de 8 semanas. Mede aceleração: acima de 1 a curva sobe. |
| `receptivo` | int64 | preditor | 100.0% | InfoDengue | Indicador do InfoDengue de receptividade climática ao vetor. |
| `transmissao` | int64 | preditor | 100.0% | InfoDengue | Indicador do InfoDengue de evidência de transmissão sustentada. |
| `tweet` | float64 | apoio | 75.0% | InfoDengue | Menções a dengue no Twitter/X captadas pelo InfoDengue. Não usada pelo projeto. |
| `variacao_semanal` | float64 | preditor essencial | 100.0% | Derivada | Variação relativa da incidência frente à semana anterior. |

## Climático — 39 colunas

| Coluna | Tipo | Papel | Preenchida | Fonte | Descrição |
|---|---|---|---|---|---|
| `semanas_favoraveis_8` | float64 | apoio | 99.4% | Derivada | Quantas das últimas 8 semanas tiveram temperatura na faixa favorável ao Aedes aegypti. |
| `tempmax` | float64 | apoio | 100.0% | ERA5/Open-Meteo | Temperatura máxima da semana. |
| `tempmax_imputado` | int64 | apoio | 100.0% | Derivada | Marca 1 quando a temperatura máxima foi imputada naquela linha. |
| `tempmax_lag1` | float64 | apoio | 99.8% | Derivada | A temperatura máxima com defasagem de 1 semanas. |
| `tempmax_lag2` | float64 | apoio | 99.7% | Derivada | A temperatura máxima com defasagem de 2 semanas. |
| `tempmax_lag3` | float64 | apoio | 99.5% | Derivada | A temperatura máxima com defasagem de 3 semanas. |
| `tempmax_lag4` | float64 | apoio | 99.4% | Derivada | A temperatura máxima com defasagem de 4 semanas. |
| `tempmax_lag6` | float64 | apoio | 99.1% | Derivada | A temperatura máxima com defasagem de 6 semanas. |
| `tempmax_lag8` | float64 | apoio | 98.8% | Derivada | A temperatura máxima com defasagem de 8 semanas. |
| `tempmed` | float64 | apoio | 100.0% | ERA5/Open-Meteo | Temperatura média da semana, em graus Celsius. Reanálise, não medição de estação. |
| `tempmed_anomalia` | float64 | apoio | 92.0% | Derivada | Desvio da temperatura média frente à média histórica da mesma semana do ano, calculada só com anos anteriores. |
| `tempmed_imputado` | int64 | apoio | 100.0% | Derivada | Marca 1 quando a temperatura média foi imputada naquela linha. |
| `tempmed_lag1` | float64 | apoio | 99.8% | Derivada | A temperatura média com defasagem de 1 semanas. |
| `tempmed_lag2` | float64 | apoio | 99.7% | Derivada | A temperatura média com defasagem de 2 semanas. |
| `tempmed_lag3` | float64 | apoio | 99.5% | Derivada | A temperatura média com defasagem de 3 semanas. |
| `tempmed_lag4` | float64 | apoio | 99.4% | Derivada | A temperatura média com defasagem de 4 semanas. |
| `tempmed_lag6` | float64 | apoio | 99.1% | Derivada | A temperatura média com defasagem de 6 semanas. |
| `tempmed_lag8` | float64 | apoio | 98.8% | Derivada | A temperatura média com defasagem de 8 semanas. |
| `tempmin` | float64 | apoio | 100.0% | ERA5/Open-Meteo | Temperatura mínima da semana. |
| `tempmin_imputado` | int64 | apoio | 100.0% | Derivada | Marca 1 quando a temperatura mínima foi imputada naquela linha. |
| `tempmin_lag1` | float64 | apoio | 99.8% | Derivada | A temperatura mínima com defasagem de 1 semanas. |
| `tempmin_lag2` | float64 | apoio | 99.7% | Derivada | A temperatura mínima com defasagem de 2 semanas. |
| `tempmin_lag3` | float64 | apoio | 99.5% | Derivada | A temperatura mínima com defasagem de 3 semanas. |
| `tempmin_lag4` | float64 | apoio | 99.4% | Derivada | A temperatura mínima com defasagem de 4 semanas. |
| `tempmin_lag6` | float64 | apoio | 99.1% | Derivada | A temperatura mínima com defasagem de 6 semanas. |
| `tempmin_lag8` | float64 | apoio | 98.8% | Derivada | A temperatura mínima com defasagem de 8 semanas. |
| `umidmax` | float64 | apoio | 100.0% | ERA5/Open-Meteo | Umidade relativa máxima da semana. |
| `umidmax_imputado` | int64 | apoio | 100.0% | Derivada | Marca 1 quando a umidade máxima foi imputada naquela linha. |
| `umidmed` | float64 | apoio | 100.0% | ERA5/Open-Meteo | Umidade relativa média da semana, em porcentagem. |
| `umidmed_anomalia` | float64 | apoio | 92.0% | Derivada | Desvio da umidade média frente à média histórica da mesma semana do ano, só com anos anteriores. |
| `umidmed_imputado` | int64 | apoio | 100.0% | Derivada | Marca 1 quando a umidade média foi imputada naquela linha. |
| `umidmed_lag1` | float64 | apoio | 99.8% | Derivada | A umidade média com defasagem de 1 semanas. |
| `umidmed_lag2` | float64 | apoio | 99.7% | Derivada | A umidade média com defasagem de 2 semanas. |
| `umidmed_lag3` | float64 | apoio | 99.5% | Derivada | A umidade média com defasagem de 3 semanas. |
| `umidmed_lag4` | float64 | apoio | 99.4% | Derivada | A umidade média com defasagem de 4 semanas. |
| `umidmed_lag6` | float64 | apoio | 99.1% | Derivada | A umidade média com defasagem de 6 semanas. |
| `umidmed_lag8` | float64 | apoio | 98.8% | Derivada | A umidade média com defasagem de 8 semanas. |
| `umidmin` | float64 | apoio | 100.0% | ERA5/Open-Meteo | Umidade relativa mínima da semana. |
| `umidmin_imputado` | int64 | apoio | 100.0% | Derivada | Marca 1 quando a umidade mínima foi imputada naquela linha. |

## Precipitação — 14 colunas

| Coluna | Tipo | Papel | Preenchida | Fonte | Descrição |
|---|---|---|---|---|---|
| `chuva_acum12` | float64 | apoio | 99.5% | Derivada | Precipitação acumulada nas últimas 12 semanas. |
| `chuva_acum4` | float64 | apoio | 99.5% | Derivada | Precipitação acumulada nas últimas 4 semanas. |
| `chuva_acum8` | float64 | apoio | 99.5% | Derivada | Precipitação acumulada nas últimas 8 semanas. |
| `chuva_anomalia` | float64 | apoio | 91.7% | Derivada | Desvio da chuva frente à média histórica da mesma semana, só com anos anteriores. |
| `chuva_dias_com_chuva` | float64 | apoio | 99.7% | Derivada | Número de dias com chuva na semana. |
| `chuva_lag12` | float64 | apoio | 98.0% | Derivada | A precipitação semanal com defasagem de 12 semanas. |
| `chuva_lag2` | float64 | apoio | 99.5% | Derivada | A precipitação semanal com defasagem de 2 semanas. |
| `chuva_lag4` | float64 | apoio | 99.2% | Derivada | A precipitação semanal com defasagem de 4 semanas. |
| `chuva_lag6` | float64 | apoio | 98.9% | Derivada | A precipitação semanal com defasagem de 6 semanas. |
| `chuva_lag8` | float64 | apoio | 98.6% | Derivada | A precipitação semanal com defasagem de 8 semanas. |
| `chuva_max_diaria_mm` | float64 | apoio | 99.7% | ERA5/Open-Meteo | Maior precipitação diária da semana. Distingue chuva torrencial de chuva distribuída. |
| `chuva_semana_mm` | float64 | apoio | 99.7% | ERA5/Open-Meteo | Precipitação acumulada na semana, em milímetros. |
| `semanas_secas_8` | float64 | apoio | 99.4% | Derivada | Quantas das últimas 8 semanas foram secas. Seca leva a armazenar água em casa, o que cria criadouro. |
| `semanas_torrenciais_4` | float64 | apoio | 99.7% | Derivada | Quantas das últimas 4 semanas tiveram chuva torrencial. Chuva forte lava criadouros em vez de criá-los. |

## Contextual — 3 colunas

| Coluna | Tipo | Papel | Preenchida | Fonte | Descrição |
|---|---|---|---|---|---|
| `log_pop` | float64 | preditor essencial | 100.0% | Derivada | Logaritmo da população. Entra no modelo porque o efeito do porte não é linear. |
| `pop` | int64 | apoio | 100.0% | IBGE | População residente do município. Entre censos, é projeção do IBGE. |
| `porte_populacional` | object | apoio | 100.0% | Derivada | Faixa de porte do município. |

## Vulnerabilidade — 4 colunas

| Coluna | Tipo | Papel | Preenchida | Fonte | Descrição |
|---|---|---|---|---|---|
| `esgoto_inadequado_pct` | float64 | apoio | 100.0% | IBGE Censo 2022 | Domicílios sem esgotamento sanitário adequado, em porcentagem. |
| `lixo_sem_coleta_pct` | float64 | apoio | 100.0% | IBGE Censo 2022 | Domicílios sem coleta de lixo, em porcentagem. |
| `sem_agua_rede_pct` | float64 | apoio | 100.0% | IBGE Censo 2022 | Domicílios sem ligação à rede de água. Único indicador com associação significativa à incidência no território (ρ = +0,397; p = 0,020). |
| `vulnerabilidade_socioambiental` | float64 | apoio | 100.0% | Derivada | Índice que resume os três indicadores acima. |

## Risco — 9 colunas

| Coluna | Tipo | Papel | Preenchida | Fonte | Descrição |
|---|---|---|---|---|---|
| `anos_historico` | int64 | apoio | 100.0% | Derivada | Quantos anos anteriores sustentam o canal endêmico daquela semana. |
| `canal_mediana` | float64 | preditor essencial | 92.0% | Derivada | Mediana histórica da incidência na mesma semana do ano. Piso da faixa de alerta do canal endêmico. |
| `canal_q1` | float64 | apoio | 92.0% | Derivada | Primeiro quartil histórico da incidência na mesma semana do ano, só com anos anteriores. |
| `canal_q3` | float64 | preditor essencial | 92.0% | Derivada | Terceiro quartil histórico. Acima dele a incidência entra em zona epidêmica. |
| `nivel_absoluto` | int64 | apoio | 100.0% | Derivada | Nível de risco pelos patamares absolutos de incidência: 10, 30 e 60 por 100 mil. |
| `nivel_canal` | int64 | apoio | 100.0% | Derivada | Nível de risco pela posição no canal endêmico, de 0 a 3. |
| `risco` | object | apoio | 100.0% | Derivada | Nome do nível final: baixo, moderado, alto ou muito alto. |
| `risco_codigo` | int64 | origem do alvo | 100.0% | Derivada | Nível final, o maior entre canal e patamar: 0 baixo, 1 moderado, 2 alto, 3 muito alto. É a base do alvo do modelo. |
| `risco_sem_canal` | int64 | apoio | 100.0% | Derivada | Nível calculado só pelos patamares absolutos, para medir o quanto o canal acrescenta. |

## Qualidade — 6 colunas

| Coluna | Tipo | Papel | Preenchida | Fonte | Descrição |
|---|---|---|---|---|---|
| `chuva_ausente` | int64 | apoio | 100.0% | Derivada | Marca 1 quando a série de chuva não estava disponível para a semana. |
| `clima_imputado` | int64 | apoio | 100.0% | Derivada | Marca 1 quando alguma variável climática da linha foi imputada. |
| `completude` | float64 | apoio | 100.0% | Derivada | Proporção estimada de notificação já digitada na semana. Abaixo de 1 a semana ainda vai crescer. |
| `dado_provisorio` | int64 | apoio | 100.0% | Derivada | Marca 1 quando a semana ainda está sujeita a revisão pelo atraso de notificação. |
| `historico_insuficiente` | int64 | apoio | 100.0% | Derivada | Marca 1 quando não há anos anteriores bastantes para o canal endêmico ser válido. |
| `incerteza_nowcast` | float64 | apoio | 100.0% | Derivada | Largura relativa do intervalo de credibilidade do nowcasting. |

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


## Glossário

O que cada termo da tabela significa, para quem não é da área.


### Como ler a tabela

- **Coluna** — O nome de uma informação guardada na base. Cada linha da base é um município numa semana; cada coluna é um dado sobre essa linha, como os casos ou a chuva.
- **Bloco** — O tema a que a coluna pertence: identificação, epidemiológico, climático, precipitação, contextual, vulnerabilidade, risco ou qualidade do dado.
- **Tipo** — A espécie de dado que a coluna guarda: número inteiro, número com casas decimais ou texto.
- **Papel** — Como a coluna entra na previsão: se o modelo a usa para calcular o risco ou se ela só sustenta cálculos e o painel.
- **Preenchida (%)** — De cada 100 linhas da base, em quantas a coluna tem valor. Abaixo de 100% falta valor em parte das linhas, em geral por construção: o primeiro ano da série, por exemplo, não tem anos anteriores para comparar.
- **Fonte** — De onde o dado vem: de um sistema público ou de um cálculo do próprio projeto.

### Tipos de dado

- **int64** — Número inteiro, sem casas decimais. Exemplo: casos notificados.
- **float64** — Número com casas decimais. Exemplo: incidência. Aparece também em colunas de contagem quando falta valor em alguma linha, porque o valor vazio só existe entre os números decimais.
- **object** — Texto. Exemplos: nome do município, nível de risco.

### Papéis na previsão

- **preditor essencial** — Variável sem a qual a previsão não se sustenta. Está sempre disponível na semana mais recente, o que permite ao alerta funcionar sem esperar outras fontes.
- **preditor** — Variável que o modelo usa para calcular a probabilidade de risco. Inclui as essenciais.
- **origem do alvo** — Coluna da qual sai o que o modelo tenta prever: o risco alto ou muito alto quatro semanas à frente.
- **apoio** — Coluna que sustenta cálculos, conferências ou o painel, mas não entra no treino do modelo.

### Fontes

- **InfoDengue** — Sistema da Fiocruz e da FGV que processa as notificações do SINAN e publica, por município e semana, os casos, as estimativas e os indicadores de transmissão.
- **SINAN** — Sistema de Informação de Agravos de Notificação, do Ministério da Saúde, onde os casos de dengue são registrados.
- **IBGE** — Instituto Brasileiro de Geografia e Estatística. Fornece a população, os mapas e os indicadores do Censo 2022.
- **ERA5/Open-Meteo** — Reanálise climática do centro europeu ECMWF, acessada pela plataforma Open-Meteo. Reanálise é um modelo que combina observações para estimar o clima em cada ponto, inclusive onde não há estação meteorológica.
- **Derivada** — Calculada pelo próprio projeto a partir de outras colunas.

### Termos das descrições

- **Semana epidemiológica** — Semana padronizada da vigilância em saúde, de domingo a sábado, numerada de 1 a 52 ou 53 ao longo do ano.
- **Incidência por 100 mil** — Casos estimados divididos pela população e multiplicados por 100 mil. Permite comparar municípios de tamanhos diferentes.
- **Nowcasting** — Técnica que estima quantos casos de uma semana ainda vão ser registrados, corrigindo o atraso de notificação. Os casos estimados vêm dela.
- **Casos notificados e casos estimados** — Notificados são os registrados até agora; estimados incluem os que ainda vão entrar no sistema. Nas semanas recentes, os estimados são maiores.
- **Dado provisório** — Semana cuja notificação ainda não terminou de ser registrada. Os números tendem a subir.
- **Defasagem** — O valor de semanas anteriores. Com defasagem de 4 semanas significa o valor de quatro semanas atrás.
- **Média móvel** — Média das últimas semanas, que suaviza a oscilação de uma semana para outra. É calculada até a semana anterior, para não usar o próprio dado que se quer prever.
- **Anomalia** — Diferença entre o valor da semana e a média histórica da mesma época do ano.
- **Canal endêmico** — Faixa de incidência esperada para cada semana do ano, construída com os anos anteriores do próprio município. Acima do limite superior, a incidência está em zona epidêmica.
- **Quartil** — Ponto que divide os valores históricos em quatro partes iguais. O terceiro quartil (Q3) é o valor abaixo do qual ficaram 75% das semanas anteriores; a mediana é o do meio.
- **Rt** — Número reprodutivo efetivo: quantas pessoas, em média, cada caso infecta. Acima de 1 a transmissão cresce; abaixo de 1, diminui.
- **Probabilidade de Rt acima de 1** — Chance de a transmissão estar crescendo na semana. É a variável do único alarme que se sustentou no histórico do território.
- **Vazamento temporal** — Erro em que o modelo usa, sem perceber, informação do futuro. Infla o desempenho medido e falha em operação real; o projeto testa sua ausência a cada execução.
