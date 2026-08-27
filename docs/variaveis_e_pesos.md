# Variáveis, pesos e fontes — VIGIA-Dengue

Documento de referência do bloco de variáveis do projeto: o que a literatura
recomenda, o que foi implementado, quanto cada bloco pesa no modelo e o que
ficou de fora — com o motivo.

Território: Brasília (DF) e os 29 municípios goianos do Entorno.
Unidade de análise: município × semana epidemiológica.

---

## 1. O que a literatura recomenda

Revisões sistemáticas de modelos de alerta precoce de dengue convergem em um
conjunto de preditores. A frequência com que cada um aparece nos modelos
publicados:

| Preditor | Frequência na literatura | Temos? |
|---|---|---|
| Temperatura | ~99% | sim |
| Precipitação | ~83% | sim (adicionada) |
| Umidade relativa | ~80% | sim |
| Casos passados / autocorrelação | maioria | sim |
| Ajuste de atraso de notificação | ~59% | sim (nowcasting) |
| Índices entomológicos (LIRAa) | usado, com ressalvas | **não** |
| Velocidade e direção do vento | ~31% | não |
| Insolação | ~12% | não |

Duas observações da própria literatura orientaram decisões aqui:

- A **umidade** funciona mais como fator modificador do que como preditor
  independente — coerente com o peso baixo que ela recebe no nosso modelo.
- Há relatos de **ausência de correlação entre LIRAa e incidência** de
  arboviroses. O índice é útil para vigilância vetorial, mas não é preditor
  confiável de transmissão — o que reduz o custo de não dispormos dele.

---

## 2. Blocos de variáveis e seus pesos

Pesos medidos pelo ganho acumulado no LightGBM, treinado sobre a base completa
com validação temporal em janela expansiva.

Base final: **41 preditores**, 115 colunas, 30 municípios × 659 semanas.

| Bloco | Peso | Nº de variáveis | Papel |
|---|---|---|---|
| **Epidemiológico** | **52,3%** | 10 | histórico da própria dengue |
| Climático (temp./umidade) | 16,6% | 12 | condição ambiental para o vetor |
| Precipitação | 13,6% | 12 | criadouros, lavagem e armazenamento |
| Canal endêmico | 7,5% | 2 | padrão esperado da semana |
| Contextual | 6,0% | 2 | população e sazonalidade |
| Vulnerabilidade | 4,0% | 3 | saneamento (Censo 2022) |

### As dez variáveis de maior peso

| Peso | Variável | Direção | Descrição |
|---|---|---|---|
| 30,3% | `incidencia_100k` | ↑ | incidência da semana corrente |
| 4,9% | `incidencia_lag1` | ↑ | incidência da semana anterior |
| 3,9% | `canal_mediana` | ↓ | mediana histórica da semana |
| 3,8% | `incidencia_mm3` | ↑ | média móvel de 3 semanas |
| 3,6% | `log_pop` | ↑ | porte populacional |
| 3,6% | `canal_q3` | ↓ | limite esperado histórico |
| 3,2% | `incidencia_mm8` | ↓ | média móvel de 8 semanas |
| 2,8% | `incidencia_lag2` | ↑ | incidência de 2 semanas antes |
| 2,4% | `semana` | — | semana epidemiológica (sazonalidade) |
| 2,2% | `casos_est_mm3` | ↑ | casos estimados, média de 3 semanas |
| 2,1% | `chuva_acum4` | ↑ | chuva acumulada em 4 semanas |
| 2,1% | `chuva_semana_mm` | ↑ | chuva da semana |

A incidência corrente sozinha responde por 30,3% do ganho.

---

## 3. Achados de ablação

Testes removendo blocos inteiros, sempre com validação temporal:

| Conjunto | AUC |
|---|---|
| Todas as variáveis (41) | 0,818 |
| Sem clima | 0,838* |
| Só epidemiológicas | 0,796* |
| **Só clima** | **0,586*** |
| **Só precipitação (12)** | **0,550** |

\* medidos na base anterior, de 33 municípios.

**A precipitação repete o padrão.** Ganho médio de apenas +0,002 de AUC
(vencendo em 5 dos 7 anos), e isoladamente fica em 0,550 — quase o acaso.

**O clima quase não agrega poder preditivo neste território.** Isoladamente
fica em 0,586, próximo do acaso (0,50), e removê-lo não piora o modelo.

A causa não é erro de medição, e sim o recorte espacial: os municípios estão no
mesmo bioma e altitude, e a temperatura varia apenas **0,68 °C entre eles** na
mesma semana, contra **6,65 °C de amplitude sazonal** ao longo do ano.

> O clima explica **quando** a dengue sobe — a sazonalidade, que a variável
> `semana` já captura. Não explica **onde**, que é o que a estratificação
> espacial precisa distinguir.

Correlações com a incidência futura confirmam: temperatura defasada 0,21,
contra 0,72 da própria incidência atual.

O mesmo padrão se repetiu com a **vulnerabilidade socioambiental**: sem
associação significativa com a incidência (Spearman ρ = 0,119; p = 0,51), e
ganho de apenas +0,0007 de AUC. A explicação é da mesma natureza — o indicador
é municipal, mas a vulnerabilidade que importa para dengue é **intraurbana**.

### O padrão que se repete

Três blocos independentes — clima, precipitação e vulnerabilidade — produziram
o mesmo resultado: contribuição marginal, e desempenho próximo do acaso quando
isolados. A explicação é comum a todos: **eles variam no tempo, mas quase não
variam entre os municípios do território.** O modelo de estratificação espacial
precisa distinguir *onde*, e esses blocos só informam *quando*.

Os blocos foram mantidos: constam do projeto aprovado (item 4.4), descrevem o
território no painel, não prejudicam o desempenho e cada um vence na maioria dos
anos avaliados.

---

## 4. Fontes de dados — o que existe e o que foi testado

### Em uso

| Fonte | O que fornece | Acesso |
|---|---|---|
| InfoDengue (Fiocruz/FGV) | casos, nowcasting, incidência, Rt, temperatura, umidade | API pública `alertcity` |
| IBGE — localidades | validação dos códigos municipais | API pública |
| IBGE — malhas | cartografia municipal | API pública |
| IBGE — Censo 2022 | vulnerabilidade socioambiental | API de agregados |
| Open-Meteo (ERA5) | precipitação diária | API pública, sem chave |
| NASA POWER | precipitação (fonte de reserva) | API pública, sem chave |
| Shapefile das RAs | geometria das 31 Regiões Administrativas | repositório público |

### Testadas e indisponíveis

| Fonte | O que daria | Por que não |
|---|---|---|
| DATASUS / SINAN | microdados com bairro, idade, sexo, gravidade | FTP e espelho HTTPS sem resposta |
| Ipea / Atlas IVS | IVS municipal consolidado | não servido por API; só planilha no portal |
| SES-DF — painel de incidência | casos por Região Administrativa | aplicação Streamlit, sem endpoint REST |
| SES-DF — LIRAa | índice de infestação predial | relatório Power BI embutido |
| dados.df.gov.br | dados abertos distritais | API CKAN retorna 404 |
| GeoServiço DF (WFS) | camadas geográficas oficiais | host não responde |

---

## 5. Bloco de precipitação

Adicionado por ser a maior lacuna frente à literatura. A chuva atua sobre a
dengue por mecanismos opostos, e por isso entra em várias leituras em vez de um
único acumulado:

| Variável | Mecanismo |
|---|---|
| `chuva_semana_mm` | acumulado da semana |
| `chuva_lag2` … `chuva_lag12` | defasagem entre criadouro e caso notificado |
| `chuva_acum4` / `acum8` / `acum12` | formação sustentada de criadouros |
| `semanas_secas_8` | seca leva ao armazenamento domiciliar de água |
| `semanas_torrenciais_4` | chuva intensa lava criadouros |
| `chuva_anomalia` | desvio do padrão sazonal daquela semana |
| `chuva_dias_com_chuva` | distribuição da chuva na semana |
| `chuva_max_diaria_mm` | intensidade máxima |

---

## 6. Mapa intraurbano do DF

As 31 Regiões Administrativas com geometria disponível estão no painel, com
população (PDAD 2021), área e densidade — cobrindo 2.966.281 habitantes.

**O mapa não exibe casos por RA**, porque não existe fonte pública com essa
série (ver seção 4). Repartir os casos do DF entre as RAs na proporção da
população produziria um mapa apenas aparentemente informativo: ele reproduziria
o mapa populacional e esconderia justamente a desigualdade intraurbana que se
quer medir.

Obtida a série por RA junto à SES-DF, ela se acopla à malha existente pelo nome
da região, sem reescrita do pipeline.

---

## 7. Desdobramento prioritário

Dois achados independentes — clima e vulnerabilidade — apontam para a mesma
conclusão: **no recorte municipal, o que prevê dengue é o histórico da própria
dengue.** A variação que faria clima e vulnerabilidade importarem é intraurbana
e está agregada dentro do único município que é o DF.

Obter os casos por Região Administrativa junto à Secretaria de Saúde do DF é,
portanto, o desdobramento de maior valor do projeto: é onde essas variáveis
provavelmente recuperariam poder explicativo, e a infraestrutura para recebê-las
já está pronta.
