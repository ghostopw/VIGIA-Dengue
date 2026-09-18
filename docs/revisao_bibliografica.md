# Revisão bibliográfica — alerta precoce de dengue

Levantamento feito em 18/09/2026 para situar o VIGIA-Dengue frente ao que já
existe: quem faz previsão de dengue, com que dado, em que escala, e com que
desempenho. A pergunta de fundo é se o projeto repete o que já foi feito ou se
ocupa uma lacuna.

---

## 1. Perguntas da revisão

**P1.** Que desempenho um sistema de alerta precoce de dengue costuma alcançar,
e em que horizonte? Serve para saber se 0,830 de AUC e 71% de sensibilidade
são bons, medianos ou fracos.

**P2.** O bloco climático melhora a previsão? O projeto mediu ganho
praticamente nulo, o que contraria a intuição e boa parte da literatura.

**P3.** Redes neurais recorrentes superam ensembles de árvore em dengue? O
projeto mediu que não, com a GRU perdendo nos cinco anos avaliados.

**P4.** Como a literatura define o limiar de disparo do alerta, e que
sensibilidade e especificidade são consideradas aceitáveis na operação?

**P5.** Existe sistema operando em escala intraurbana — bairro ou setor
censitário — e como ele contorna a agregação municipal da notificação?

---

## 2. Estratégia de busca

Buscas em inglês e português no PubMed/PMC, Springer, ScienceDirect, PLOS,
Lancet Planetary Health, PNAS e arXiv, combinando os termos *dengue*,
*early warning*, *forecasting*, *machine learning*, *LSTM*, *gradient
boosting*, *intra-urban*, *census tract*, *alarm threshold* e *Brazil*.
Priorizados estudos brasileiros, por comparabilidade de fonte e de território.

Dos nove estudos selecionados, dois foram lidos na íntegra e os demais pelo
resumo e pelos trechos indexados — a coluna **Leitura** da tabela registra
isso, para que ninguém cite de segunda mão sem saber.

---

## 3. Tabela comparativa

| # | Estudo | Território e escala | Horizonte | Preditores | Modelos | Desempenho relatado | Leitura |
|---|---|---|---|---|---|---|---|
| 1 | Comparative evaluation of ML strategies for short-term dengue forecasting in Brazilian capital municipalities (Int J Biometeorol, 2026) | 27 capitais, municipal, 1999–2021 | 1 a 4 semanas | Epidemiológicos, climáticos e socioeconômicos, com defasagens, janelas móveis e codificação sazonal | GRU × CatBoost | CatBoost superior em mais de 20 capitais; R² até 0,92 contra 0,51 da GRU, que teve R² negativo na maioria | íntegra |
| 2 | Assessing dengue forecasting methods: statistical models and ML in Rio de Janeiro (2025) | Rio de Janeiro, município único, 2016–2023 | 1 a 12 semanas | Casos, temperatura e umidade | ARIMA, ETS, VAR, SARIMAX, SVM, RF, XGBoost, LSTM, Prophet, ensembles | 1 semana: LSTM com covariáveis MAE 71,4; ARIMA só com casos MAE 78,3. Clima melhorou a acurácia | íntegra |
| 3 | 2024 Dengue Forecasting Sprint in Brazil (PNAS, 2025) | Brasil, estadual/municipal | temporada | Casos, clima, mobilidade, conforme a equipe | Múltiplas equipes, modelos diversos | Exercício de previsão probabilística com avaliação padronizada entre equipes | resumo |
| 4 | Dengue Early Warning System as Outbreak Prediction Tool: revisão sistemática (RMHP, 2022) | Multipaís, distrital | 1 a 3 meses | Meteorológicos, entomológicos e epidemiológicos | EWARS/TDR e variantes | Sensibilidade 50–100%, especificidade 74–94,7%, VPP 43–86%, acurácia 70–96,3% | resumo |
| 5 | EWARS em implementação operacional no México (PLOS Glob Public Health, 2023) | México, distrital | semanas | Indicadores de alarme meteorológicos e epidemiológicos | Modelo de probabilidade de surto com limiar de alarme | Distritos com resposta guiada por alarme registraram prevenção de surto | resumo |
| 6 | Combined effects of hydrometeorological hazards and urbanisation on dengue risk in Brazil (Lancet Planet Health, 2021) | Brasil, microrregiões | defasagens até 12 meses | Seca, chuva extrema, urbanização, abastecimento de água | Modelo espaço-temporal bayesiano | Risco após seca extrema maior onde há mais falta de abastecimento de água | resumo |
| 7 | Spatial Distribution of Dengue in a Brazilian Urban Slum Setting (PLOS NTD, 2015) | Salvador, intraurbano | transversal | Gradiente socioeconômico de vizinhança | Modelos espaciais | Menor nível socioeconômico associado a maior risco, mesmo dentro da favela | resumo |
| 8 | Hierarchical Bayesian Modeling of Dengue in Recife, 2015–2024 (2025) | Recife, bairro e setor | mensal | Casos, granularidade espacial, qualidade do dado | Bayesiano hierárquico | Discute o custo da granularidade espacial fina sobre a qualidade do dado | resumo |
| 9 | Neural networks for dengue forecasting: systematic review (2021) | Multipaís | variado | Clima e casos | Redes neurais diversas | Sem superioridade consistente das redes sobre alternativas mais simples | resumo |
| — | **VIGIA-Dengue** | **RIDE-DF, 34 municípios, semanal, 2014–2026** | **4 semanas** | **41 variáveis: epidemiológicas, climáticas, precipitação, porte e vulnerabilidade do Censo 2022** | **Persistência, logística, LightGBM, GRU** | **AUC 0,830; no limiar operacional de 0,80 em Brasília: sensibilidade 71,1%, especificidade 67,0%, VPP 74,8%** | — |

---

## 4. Respostas às perguntas

**P1 — O desempenho está dentro da faixa, com uma ressalva.** A revisão
sistemática de EWARS (#4) situa os sistemas operacionais entre 50% e 100% de
sensibilidade e entre 74% e 94,7% de especificidade, com VPP de 43% a 86%. O
VIGIA-Dengue, no limiar de 0,80, entrega sensibilidade de 71,1% e VPP de
74,8% — ambos confortavelmente dentro da faixa, o VPP inclusive na metade
superior. A especificidade de 67,0% fica **abaixo do piso** de 74%. Isso é
coerente com o que o projeto já registrou: a taxa base de Brasília é alta, com
risco alto em 58% das semanas, e um desfecho tão frequente limita a
especificidade alcançável qualquer que seja o limiar. É o argumento mais forte
para rever o critério de risco em Brasília, e agora ele tem referência externa.

**P2 — A divergência sobre o clima é de escala, não de contradição.** O estudo
do Rio (#2) concluiu que temperatura e umidade melhoram a previsão; o
VIGIA-Dengue mediu ganho nulo. As duas coisas podem ser verdadeiras porque as
perguntas são diferentes. O Rio é *um* município ao longo do tempo: ali o clima
explica **quando** a dengue sobe. O VIGIA-Dengue estratifica **entre**
municípios que estão no mesmo bioma e na mesma faixa de altitude, com 0,68 grau
de variação entre eles na mesma semana — e a sazonalidade comum já é capturada
pela variável `semana`. O comentário metodológico em `modelagem.py` já dizia
isso; a literatura agora o sustenta em vez de contradizê-lo. Vale citar #2
explicitamente no relatório, como contraste explicado.

**P3 — A literatura recente concorda com o achado do projeto.** O estudo #1 é o
paralelo mais próximo que existe: mesma fonte de dados, território brasileiro,
horizonte de até 4 semanas, e exatamente a comparação que o projeto fez — uma
GRU contra um ensemble de árvore. O CatBoost venceu em mais de 20 das 27
capitais, com R² negativo da GRU na maioria delas, e os autores atribuem a
vantagem justamente à engenharia de variáveis: defasagens, janelas móveis e
codificação sazonal explícitas. É a mesma leitura que o projeto registrou em
`achados_modelagem.md`. A revisão sistemática #9 reforça que redes neurais não
mostram superioridade consistente em dengue.

**P4 — O limiar é decisão operacional, e há precedente.** O EWARS (#4, #5)
opera exatamente com o mecanismo do projeto: um modelo devolve probabilidade de
surto e o alarme dispara quando ela cruza um limiar definido. A mudança de 0,50
para 0,80 feita pelo projeto tem, portanto, respaldo metodológico — a escolha do
ponto de corte é parte do desenho, não improviso.

**P5 — É aqui que está a lacuna.** Os estudos intraurbanos que encontrei (#7,
#8) são **análises retrospectivas de distribuição espacial**, não sistemas de
alerta rodando nessa escala. E #8 discute justamente o custo da granularidade
fina sobre a qualidade do dado. Não localizei sistema de alerta precoce
operando em escala de setor censitário com atualização semanal. O VIGIA-Dengue
chega perto por um caminho próprio: mantém a **previsão** no nível municipal,
onde o dado existe, e usa a escala de quadra como **camada de direcionamento** —
4.022 setores com índice de criadouro. Separar previsão de direcionamento é
defensável e, pelo que levantei, pouco explorado.

---

## 5. O que isso muda no projeto

1. **Citar #1 ao justificar o LightGBM.** O achado da rede neural deixa de ser
   resultado isolado e passa a ser convergente com a literatura brasileira
   recente.
2. **Citar #2 como contraste, não como refutação**, e explicar a diferença de
   escala. É o tipo de discussão que uma banca cobra.
3. **Usar a faixa do EWARS (#4) como referência de desempenho** no relatório, e
   assumir a especificidade abaixo do piso como limitação medida, com a causa
   já identificada.
4. **Tratar #6 como sustentação do achado da água encanada.** A associação
   medida no projeto (ρ = +0,397; p = 0,020 para domicílios sem rede de água)
   deixa de ser curiosidade local e ganha mecanismo descrito na literatura.
5. **Posicionar a camada por setor censitário como contribuição**, e não como
   detalhe do painel: é o que diferencia o projeto dos sistemas existentes.

---

## 6. Referências

1. Comparative evaluation of machine learning strategies for short-term dengue
   forecasting in Brazilian capital municipalities. *International Journal of
   Biometeorology*, 2026. https://link.springer.com/article/10.1007/s00484-026-03300-7
2. Assessing dengue forecasting methods: a comparative study of statistical
   models and machine learning techniques in Rio de Janeiro, Brazil.
   https://pmc.ncbi.nlm.nih.gov/articles/PMC11984044/
3. Leveraging probabilistic forecasts for dengue preparedness and control: the
   2024 Dengue Forecasting Sprint in Brazil. *PNAS*, 2025.
   https://www.pnas.org/doi/full/10.1073/pnas.2508989123
4. Dengue Early Warning System as Outbreak Prediction Tool: A Systematic
   Review. *Risk Management and Healthcare Policy*, 2022.
   https://www.tandfonline.com/doi/full/10.2147/RMHP.S361106
5. Early warning and response system for dengue outbreaks: moving from research
   to operational implementation in Mexico. *PLOS Global Public Health*, 2023.
   https://journals.plos.org/globalpublichealth/article?id=10.1371%2Fjournal.pgph.0001691
6. Combined effects of hydrometeorological hazards and urbanisation on dengue
   risk in Brazil: a spatiotemporal modelling study. *Lancet Planetary Health*,
   2021. https://www.thelancet.com/journals/lanplh/article/PIIS2542-5196(20)30292-8/fulltext
7. Spatial Distribution of Dengue in a Brazilian Urban Slum Setting: Role of
   Socioeconomic Gradient in Disease Risk. *PLOS NTD*, 2015.
   https://journals.plos.org/plosntds/article?id=10.1371%2Fjournal.pntd.0003937
8. Hierarchical Bayesian Modeling of Dengue in Recife, Brazil (2015–2024): The
   Role of Spatial Granularity and Data Quality for Epidemiological Risk
   Mapping. https://arxiv.org/html/2510.13672
9. Neural networks for dengue forecasting: a systematic review.
   https://arxiv.org/pdf/2106.12905
10. Early warning and response system (EWARS) for dengue outbreaks: recent
    advancements towards widespread applications in critical settings.
    *PLOS One*, 2018.
    https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0196811
