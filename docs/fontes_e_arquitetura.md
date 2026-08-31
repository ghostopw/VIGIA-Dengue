# Levantamento de fontes e arquitetura — Centro-Oeste e captura ao vivo

> **Procedência.** Este documento saiu de um levantamento em cinco frentes
> (hidrografia, rede neural, captura ao vivo, vulnerabilidade e vetor), em que
> cada fonte proposta teve de ser chamada de verdade e teve o codigo HTTP e um
> trecho da resposta registrados, e depois passou por um verificador
> independente que reexecutou as chamadas para refutar o que nao se sustentasse.
>
> Os cinco pontos de vazamento temporal apontados na secao 0 foram **conferidos
> linha a linha e corrigidos** — ver  para o efeito
> medido de cada correcao. As demais afirmacoes carregam a evidencia HTTP que as
> acompanha, mas nao foram todas reexecutadas por mim.

# PLANO DE IMPLEMENTAÇÃO — VIGIA-Dengue / Centro-Oeste → Brasília e RAs

Base factual: painel já em disco (`dados/processado/base_centro_oeste.csv`, 304 MB, 307.198 linhas, 467 municípios, mediana 660 semanas) e comparação rede×LightGBM já rodada em `saidas/comparacao_modelos.csv`. Tudo abaixo parte disso.

---

## 0. CORREÇÕES OBRIGATÓRIAS ANTES DE QUALQUER TREINO

Não se treina nos 467 com o código como está. Cinco pontos, com arquivo e linha:

| Arquivo:linha | Problema | Correção |
|---|---|---|
| `src/vigia/base_analitica.py:156-157` | `transform("mean")` da chuva sobre a série inteira → anomalia de 2019 calculada contra média que contém 2025 | média sazonal expansiva: só anos anteriores da mesma semana no mesmo município |
| `src/vigia/base_analitica.py:174-175` | idem para `tempmed_anomalia` e `umidmed_anomalia` | idem |
| `src/vigia/base_analitica.py:56` | `transform("median")` global para imputar clima | mediana expansiva ou último valor conhecido |
| `src/vigia/base_analitica.py:54` | `interpolate(limit=3, limit_direction="both")` — preenche buraco com valor futuro | `limit_direction="forward"` |
| `src/vigia/modelagem.py:190` | `treino = dados[dados["ano"] < ano]` — as últimas 4 semanas de dezembro têm alvo dentro do ano de teste | `data_alvo = dados.groupby("cod_ibge")["data_ini_se"].shift(-4)`; `treino = data_alvo < inicio_do_teste`. Nos 467 são 1.868 linhas vazando por dobra |

`src/vigia/risco.py` está correto (`anos < anos[i]`, mínimo de 3 anos) — não vetorizar com groupby global ao reescrever.

Medição já feita: corrigir o vazamento **não derruba** o desempenho na RIDE (0,8300 → 0,8326). Isso muda no Centro-Oeste, onde o clima varia de verdade entre municípios.

Correções no registro de fontes (`docs/fontes_dos_dados.csv`, `docs/fontes_dos_dados.md`):
- TabArena: apagar `openreview.net/forum?id=jZqCqpCLdU` (captcha, API 403) → `https://arxiv.org/abs/2506.16791`.
- PNAS Sprint 2024, npj mobilidade, DengueGNN: registrar **só por DOI** (`10.1073/pnas.2508989123`, `10.1038/s44482-026-00015-9`, `10.1038/s41598-026-43073-y`) com nota "corpo nunca lido". Sprint 2024 e as 790 cidades são recuperáveis por `https://api.biorxiv.org/details/medrxiv/{DOI}` — citação liberada pelo resumo.
- ANA HidroInventario: a URL com 2 parâmetros devolve 500. Exige os 12 (`codEstDE, codEstATE, tpEst, nmEst, nmRio, codSubBacia, codBacia, nmMunicipio, nmEstado, sgResp, sgOper, telemetrica`), ainda que vazios. `nmEstado` exige acento (`GOIÁS`=509, `GOIAS`=0).
- ContaOvos: URL canônica é `https://contaovos.com/en-us/api/lastcountingpublic` — sem o `/en-us/` devolve 307 com HTML.
- Nota do LIRAa está incompleta em 4 pontos, não 2: `src/vigia/ras_df.py:20`, `app/painel.py:646` (não 525), `app/artifact/corpo.html:446`, `docs/variaveis_e_pesos.md:147`.

---

## 1. FONTES: QUEM ENTRA, EM QUE ORDEM, QUEM FICA DE FORA

### P0 — núcleo, já em disco, sem substituto

| Fonte | Endpoint / arquivo | Granularidade | Uso |
|---|---|---|---|
| InfoDengue alertcity | `https://info.dengue.mat.br/api/alertcity?geocode={7d}&disease=dengue&format=csv&ew_start=1&ew_end=52&ey_start={a}&ey_end={a}` | município × SE | desfecho e histórico. **467**, não 468 |
| IBGE Localidades | `/api/v1/localidades/regioes/5/municipios` | município | território. Extrair UF por `microrregiao.mesorregiao.UF.sigla` **com fallback** `regiao-imediata.regiao-intermediaria.UF.sigla` — 5101837 tem `microrregiao` nulo e quebra com TypeError |
| Censo 2022 esgoto | agregados `9397` var `1000382`, `localidades=N6[all]` | município | `esgoto_inadequado_pct` |
| Censo 2022 lixo | agregados `9541` var `1000382`, `N6[all]` | município | `lixo_sem_coleta_pct` |
| Censo 2022 água | FTP `Agregados_por_municipios_caracteristicas_domicilio2_BR_20250417.zip`, `V00111`–`V00118` | município | `sem_agua_rede_pct` (não existe na API para população geral) |
| Censo 2022 entorno | FTP `.../Caracteristicas_urbanisticas_do_entorno_dos_domicilios/Agregados_por_Municipio_csv/Agregados_por_municipios_entorno_faces_BR.zip`, `V05400/V05406/V05409` | município (467/467, mín. 140 faces) | `pct_pavimento`, `pct_bueiro` |
| Censo 2022 subdistrito | os três irmãos `Agregados_por_SubDistrito_csv/` (domicilio2, renda_responsavel, e **entorno_faces sob o diretório de Características urbanísticas**, não sob `Agregados_por_Setores_Censitarios/`) | subdistrito = RA (33 no DF) | mesmas variáveis para a camada de aplicação |
| Censo básico | FTP `Agregados_por_municipios_basico_BR_20260520.zip` | município | `pop`, `AREA_KM2` — denominador de tudo |

Armadilhas já medidas e que precisam estar no código: `localidades=N6[in N3 50|51|52|53]` devolve **500**, só `N6[all]` funciona; o caractere `-` na API é **zero absoluto** (somas das 8 categorias de esgotamento ficam entre 99,98 e 100,02 nos 467), lê-lo como NaN cria 312 buracos falsos; o `X` no arquivo **por setor** é supressão (739 de 33.410 no CO, sempre nas 6 variáveis de uma vez) e nunca vira zero — ao agregar setor→RA, ponderar por `V06001`.

### P1 — entram agora, exigem coleta nova

1. **Clima histórico para os 467.** É o buraco maior: `dados/externo/chuva_semanal.csv` só cobre os 34 da RIDE, e `base_centro_oeste.csv` não tem nenhuma coluna `chuva_*`. Fonte: **NASA POWER** `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,T2M_MIN,T2M_MAX,PRECTOTCORR,RH2M&community=AG&latitude={lat}&longitude={lon}&start=20140101&end={hoje-4d}&format=JSON`, um ponto por centroide de município. Open-Meteo archive **não é opção**: 429 reproduzido às 05:33 UTC, 5h30 depois do reset da cota, com pedido mínimo de 2 dias.
2. **ContaOvos retrospectivo.** `https://contaovos.com/en-us/api/lastcountingpublic?state={UF}&date_start=YYYY-MM-DD&date_end=YYYY-MM-DD&page=N`. Os dois parâmetros de data **juntos** devolvem janelas históricas arbitrárias (jan. março/2024 no DF: 3.000 `counting_id` únicos em 3 semanas, 867/1.133/1.000 armadilhas em 10-12 RAs). Há série semanal de ~2023 até hoje. Cobertura real medida: GO ≥90 municípios cadastrados, MT ≥60, MS 79 — não os 24/8/8 anotados.
3. **SES-DF Power BI — casos prováveis por RA × semana.** É o único rótulo sub-municipal que existe. `GET https://wabi-brazil-south-api.analysis.windows.net/public/reports/55cb4137-0bf2-4774-9f60-fa57fecd50f4/modelsAndExploration?preferReadOnlySession=true` + `POST .../public/reports/querydata?synchronous=true`, header `X-PowerBI-ResourceKey` = o próprio GUID. Consulta: `dRA.ra_ses_desc` × `fDengue.i_semana_prim_sintomas` × `Medidas['Caso Provavel Geral']`. Reconcilia com InfoDengue em 0,4% (10.817 vs 10.862 em 2026).
4. **Sorotipo GO.** Pacote `dengue` (id `44a9594c-42c1-4204-aca6-a07c347dd4bd`) do `dadosabertos.go.gov.br`, recurso `sorotipo-dengue.csv` — 5.584 linhas, `codigo_ibge;sorotipo;quantidade_testes;ano_epid;semana_epid`, semanal desde 2011. **Não** está no pacote `aedes` (esse só tem Zika/Chikungunya, zero colunas entomológicas apesar do que a descrição promete).

### P2 — bloco de água (detalhe na seção 2)

JRC Global Surface Water (4 tiles), MapBiomas climate_risk (série anual 1985-2025), Atlas de Desastres/S2iD, PNSB 2008 t/1764, PNSB 2000 t/2253. Só entram no treino as que existem nos 467.

### P3 — só camada de aplicação (DF), nunca no treino

SGB suscet_inundacao (5.178 feições no DF), GeoPortal-DF curvas de nível de 1 m de 2016, SGB risco_geologico (22 setores no DF), ContaOvos por RA, LIRAa-PDF por RA.

### FORA, com motivo medido

| Fonte | Motivo |
|---|---|
| SGB suscet_inundacao **como feature de treino** | 21 de 468 municípios setorizados (GO 4, MT 11, MS 5, DF 1) = 4,5%. 96% das linhas ficariam nulas |
| MapBiomas climate_risk normalizado pela área do município | 62,5 ha em 576.076 ha em Brasília = 0,0109%; 0,007% em Anápolis. Constante quase nula, sem poder discriminante. Só entra normalizado pela **área urbana mapeada** |
| MapBiomas água mensal | `water_water_surface_monthly` = 404; a chave real `water_monthly` dá ReadTimeout a 90s, 96s e 280s. Só a anual responde (1,8s) |
| Copernicus DEM para os 467 | ~290 tiles × 40 MB = ~12 GB, e é DSM (copa e telhado), ruidoso na mancha urbana |
| Open-Meteo archive | 429 persistente após reset de cota |
| INMET série horária | 204 No Content em toda estação e toda data, inclusive 2025 — rota desativada, não falta de dado. `/token/` responde `CHAVE INVALIDA!` |
| CEMADEN histórico | CAPTCHA (`securimage_show.php`). Só prospectivo |
| ANA HidroWeb consistida | 1-2 anos de atraso (estação 1547004: 12 meses para 2018-2023, **zero** para 2025 e 2026) |
| ANA telemetria no DF | de 20 estações testadas, 5 devolvem registro e 4 têm campo Chuva; as 4 ficam no DF rural leste, nenhuma na mancha urbana das RAs |
| BC250 `terreno_sujeito_inundacao` | 232 polígonos no Brasil inteiro, 0 no DF, 0 no Pantanal. Armadilha de nome |
| SIDRA MUNIC 2020 t/8536 | 100% dos valores `..`. A t/8535 devolve 500 — não registrar como testada |
| SNIS-AP / drenagem urbana recente | CKAN fora do ar, app Yii sem API, `/informacoesAguasPluviais/index` em 500 |
| TabNet como rótulo | DF 2026: 3.700 casos contra 10.817 (SES) e 10.862 (InfoDengue). Subnotifica ~3x. Serve só como referência de latência |
| FTP DATASUS microdados | timeout nas portas 21, 80 e 443 (o TabNet, outro host, responde) |
| Google Trends / Health Trends / RSS | 429, 403 e — no RSS — 10 manchetes sem série por palavra-chave, sem menção a dengue |
| dados.gov.br, OpenDataSUS, dados.df.gov.br, CGDF, painel MS | 401, 500, migrou para Liferay sem API, chave Power BI não resolve, host sem DNS |
| Atlas Brasil / IDHM | inacessível (certificado autoassinado + 404 do nginx) **e** anacrônico: IDHM municipal mais recente é do Censo 2010 |
| Gini municipal (SIDRA 10301) | níveis N1/N2/N3 apenas; com 4 UFs no CO seria constante por estado. Substituto: desvio-padrão via `V06005` |
| Portal da Transparência PBF | 401, e o SAGI entrega o mesmo sem credencial e com série mais longa |
| LIRAa como preditor semanal | 19 boletins trimestrais 2018-2024, **2020 inteiro ausente**, 2021 só Nov/Dez, série termina mai/2024, painel Power BI 403 em 4 rotas |
| GNN | teste barato já rodado: incidência média dos vizinhos nas defasagens 0/2/4 rendeu +0,0011 de AUC geral, dentro do ruído |
| Assets GEE do MapBiomas | não aparecem em nenhum payload ao vivo (`/themes` 257.902 bytes, 14 páginas de `/legends`): nenhuma ocorrência de `projects/`, `mapbiomas-public`, `asset` ou `earthengine`. Não registrar sem autenticar e listar |

---

## 2. COMO O FLUXO DAS ÁGUAS VIRA VARIÁVEL

Três blocos, porque são três mecanismos diferentes. Regra de ouro do bloco: **nenhuma variável de água entra no treino se não existir nos 467 municípios.** O que só existe no DF entra na camada de aplicação, como reponderação por RA.

### 2.1 Água que cai (chuva) — entra no treino, é a única com variação semanal

- **O que se mede:** precipitação diária acumulada.
- **Fonte:** NASA POWER, parâmetro `PRECTOTCORR` (grade ~0,5°), no centroide de cada município. Complemento corrente: Open-Meteo `forecast` com `past_days=92&forecast_days=16`, variáveis `precipitation_sum,temperature_2m_mean,relative_humidity_2m_mean`.
- **Granularidade:** ponto → dia → agregado à semana epidemiológica pela `data_ini_se` do InfoDengue.
- **Colunas (replicar `clima_chuva.py` para os 467, novo `src/vigia/clima_centro_oeste.py` → `dados/externo/chuva_centro_oeste.csv`):** `chuva_semana_mm, chuva_dias_com_chuva, chuva_max_diaria_mm, chuva_lag2, chuva_lag4, chuva_lag6, chuva_lag8, chuva_lag12, chuva_acum4, chuva_acum8, chuva_acum12, semanas_secas_8, semanas_torrenciais_4, chuva_anomalia, chuva_ausente`.
- **`chuva_anomalia` obrigatoriamente expansiva** (só anos anteriores da mesma semana no mesmo município).
- **A defasagem que justifica o bloco já está medida neste projeto:** máximo da correlação cruzada chuva→incidência em 8 semanas, r=+0,270; estação chuvosa com 1,77× a incidência da seca.
- **Chegada à RA:** a grade do POWER (~55 km) cobre o DF com 1-2 células. **Declarar no painel:** a chuva praticamente não discrimina entre RAs. A diferenciação intraurbana vem da infraestrutura, não da precipitação. `-999.0` do POWER é ausência, nunca zero.

### 2.2 Água que fica (paisagem) — entra no treino só onde cobre os 467

- **JRC Global Surface Water v1.4** — `https://storage.googleapis.com/global-surface-water/downloads2021/seasonality/seasonality_{50W_10S|60W_10S|50W_20S|60W_20S}v1_4_2021.tif`. Quatro tiles cobrem o CO inteiro. Métrica por polígono: `frac_agua_sazonal` = fração de pixels com `1 ≤ seasonality ≤ 11`, e `frac_agua_permanente` (=12). Lida com `rasterio` (1.5.1, já instalado). Referência de reprodutibilidade no DF: 94.486 px com água ≥1 mês (1,0545%), dos quais 13.154 sazonais e 81.332 permanentes. Aplica-se igualmente a município e a RA — é a única variável de paisagem hídrica com a mesma definição nas duas granularidades.
- **MapBiomas Climate Risk col.2** — `https://plataforma.agua.mapbiomas.org/api/v1/brazil/statistics/area?subthemeKey=climate_risk__urban_areas_susceptible_to_flooding_inundation_or_flash_floods&legendKey=..._mapbiomas_urban_flood_risk&pixelValue=1&pixelValue=2&pixelValue=3&year={ano}&territoryId={id}`, header **obrigatório** `tenant-id: mapbiomas`. Chamada nova devolve `{"taskID":...,"strategy":"batch"}` — repetir a **mesma** query após ~1 min. Município via `/territories/search/{nome}` filtrando `categoryId==230` (cuidado: "Brasilia" também devolve `categoryId 93` = Concentração Urbana, 1.720.396 ha, que **não** é o município). Duas correções sobre o registro atual: (a) **é série anual 1985-2025**, não camada estática — 1985: 6,37/3,96/9,13 ha → 2025: 21,35/15,15/26,00 ha, portanto entra como tendência temporal (`area_suscet_2025`, `delta_1985_2025`); (b) normalizar pela **área urbana mapeada**, nunca pela área do município. Para as RAs, `geometry=[[[lon,lat],…]]` com o polígono da RA (testado: bbox de Ceilândia dev