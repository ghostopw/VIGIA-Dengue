# VIGIA-Dengue

Ferramenta digital de alerta precoce para estratificação espaço-temporal do risco de
dengue, com **foco em Brasília (Distrito Federal)** e os demais municípios da RIDE-DF
como território de comparação.

Projeto PIBITI 2026 — Iniciação em Desenvolvimento Tecnológico e Inovação
**Aluno:** João Gabriel Alves Guimarães (2512082047)
**Orientadora:** Natália Ribeiro de Souza Evangelista (201534)
**Instituição:** IESB — Ciências da Saúde / Saúde Coletiva / Epidemiologia

---

## O que já está pronto

| Etapa do projeto | Situação | Onde está |
|---|---|---|
| 1 — Revisão e planejamento | Dicionário de dados e critérios operacionais | [docs/dicionario_de_dados_completo.md](docs/dicionario_de_dados_completo.md) |
| 2 — Base analítica | 22.440 linhas município-semana, 2014–2026 | `src/vigia/ingestao_infodengue.py`, `src/vigia/base_analitica.py` |
| 3 — Análise espaço-temporal | Canal endêmico e estratificação em 4 níveis | `src/vigia/risco.py` |
| 4 — Modelagem de alerta | 4 modelos com validação temporal, mais uma rede neural avaliada e descartada | `src/vigia/modelagem.py`, `src/vigia/rede_neural.py` |
| 5 — Dashboard | Painel web com mapa 3D, séries e relatórios | `Painel VIGIA-Dengue (offline).html`, `app/servidor.py` |
| 6 — Avaliação e documentação | Métricas apuradas; manual e relatório pendentes | `saidas/desempenho_modelos.csv` |

## Território piloto

**Foco: Brasília.** O DF concentra **69% da população** e **63,5% dos casos** do
território — por isso o painel abre em Brasília, com bloco de indicadores próprio, e
o Entorno entra como contexto recolhido.

**34 municípios na base**: o Distrito Federal, os 29 municípios goianos do Entorno e os
4 mineiros da RIDE-DF — Arinos, Buritis, Cabeceira Grande e Unaí.

> **Regra do território — vale para toda coleta, presente e futura.** O território é a
> RIDE-DF completa, nos termos da LC 94/1998, ampliada pela LC 163/2018. Toda rotina de
> coleta — das APIs atuais ou de qualquer API que venha a ser criada — deve iterar sobre
> `TERRITORIO` e usar `filtrar_territorio()` para barrar municípios de fora.
> `validar_territorio()` recusa a base se alguma UF fora de DF/GO/MG aparecer, e dois
> testes automatizados cobrem a regra.


> O DF é um único município na malha do IBGE e o InfoDengue não o desagrega por Região
> Administrativa. A RIDE foi adotada para que a análise espacial, os mapas e a
> estratificação entre municípios — cinco dos objetivos específicos — tivessem base de
> dados real. A escolha também é epidemiologicamente defensável: a dengue circula pelo
> pendularismo diário entre o DF e o Entorno.

## Fontes de dados

| Fonte | Uso | Acesso |
|---|---|---|
| InfoDengue (Fiocruz/FGV) | Casos, casos estimados por *nowcasting*, incidência, Rt, clima semanal | API pública `alertcity` |
| IBGE | População, malhas cartográficas e indicadores do Censo 2022 | APIs de localidades, de malhas e SIDRA |
| Open-Meteo (reanálise ERA5/ECMWF) | Precipitação, temperatura e umidade diárias por município | API `archive-api`, com NASA POWER como reserva |

**Todas as URLs de origem** — as 136 requisições que geraram os dados brutos
(34 municípios × 3 arboviroses no InfoDengue, mais 34 do IBGE) — estão documentadas em
[docs/fontes_dos_dados.md](docs/fontes_dos_dados.md): cada link abre no navegador e
devolve exatamente o conteúdo que gerou o arquivo local correspondente. As contagens
esperadas em `src/vigia/verificar_fontes.py` agora saem de `len(TERRITORIO)`, para o
verificador acompanhar o território em vez de fossilizar.

> **Nota sobre o SINAN.** O projeto previa microdados do SINAN via DATASUS. Durante a
> montagem da base o acesso não respondeu — timeout nas portas 21, 80 e 443 do FTP —, e o
> InfoDengue foi adotado por processar o próprio SINAN e por já entregar a série em
> município-semana **com correção do atraso de notificação**, requisito central para
> alerta precoce. Essa continua sendo a fonte do painel.
>
> **O acesso foi restabelecido.** Em 09/09/2026 o FTP respondeu na porta 21, com login
> anônimo e download iniciado: `DENGBR20` a `DENGBR25` em
> `/dissemin/publicos/SINAN/DADOS/FINAIS` e o preliminar `DENGBR26` em `PRELIM`. Os
> microdados trazem bairro de residência, idade, sexo e gravidade — o que o InfoDengue
> não oferece, e o que abre caminho para a escala intraurbana. A incorporação está nos
> próximos passos.

## Como reproduzir

```bash
pip install -r requirements.txt

python src/vigia/executar_ingestao.py        # baixa a série 2014-2026 (~5 min)
python src/vigia/executar_malha.py           # baixa a malha cartográfica
python src/vigia/executar_analise.py         # base analítica, risco e validação
python src/vigia/executar_painel_dados.py    # gera os dados do painel
python src/vigia/executar_dicionario.py      # regenera o dicionário de dados

python app/servidor.py                       # abre o painel em localhost:8000
python src/vigia/executar_atualizacao.py     # busca, reavalia e avisa se mudou
python -m pytest testes -q                   # roda os testes
```

## O painel

O painel é inteiramente **Brasília e suas cidades satélites**. Os municípios vizinhos
não aparecem na tela: entram apenas como massa de treino do modelo, que precisa da
variação espacial para estratificar risco (ver *Modelagem*).

No topo, um bloco fixo com a situação de **Brasília**: casos estimados (com variação
frente à semana anterior), incidência, nível de risco e probabilidade de alerta.

- **Brasília por Região Administrativa** — as 31 RAs por população, densidade ou
  vulnerabilidade socioambiental do Censo 2022 (esgoto inadequado, sem água de rede,
  lixo sem coleta). Não há *casos* por RA — o InfoDengue opera no nível municipal e o
  DF é um único município —, mas há condição: 0,12% de esgotamento inadequado no Plano
  Piloto contra 30,5% na Fercal. A correlação entre o índice e a população é de −0,141
  (Spearman, p = 0,45): o mapa não é o mapa populacional repintado.
- **Séries temporais** — casos notificados × estimados com faixa de incerteza do
  *nowcasting*, e incidência contra o canal endêmico.
- **Relatório da semana** — os indicadores de Brasília na semana escolhida, com os
  fatores que pesaram na previsão, e a série completa em CSV.
- **Desempenho do modelo** — métricas da validação temporal, ano a ano.

Controles: semana epidemiológica, limiar de probabilidade do alerta e sinalização de
semanas com notificação incompleta.

## Alerta ao vivo

`executar_atualizacao.py` é o ciclo que faz o painel acompanhar a fonte sozinho: busca
as semanas recentes no InfoDengue, reconstrói a base, reavalia Brasília e avisa **só
quando algo muda** — semana nova, risco subindo, cruzamento do limiar de probabilidade
ou incidência acima do canal endêmico. Um alerta que chega toda hora dizendo que nada
mudou deixa de ser lido.

Canais: `saidas/alerta.json` (sempre, e publicado pelo servidor em `/alerta.json`),
notificação nativa do Windows, e um POST para a URL em `VIGIA_WEBHOOK`, se definida.

Para agendar uma vez por dia no Windows — a fonte publica uma vez por semana, em dia
que varia:

```
schtasks /create /tn "VIGIA-Dengue" ^
  /tr "python L:\Dengue\src\vigia\executar_atualizacao.py" /sc daily /st 08:00
```

**O que "ao vivo" não resolve.** O InfoDengue publica a semana epidemiológica cerca de
três semanas depois de ela começar: a notificação leva tempo para ser digitada e o
*nowcasting* só estabiliza depois. Rodar de hora em hora não adianta — o dado novo
aparece uma vez por semana. O que o ciclo garante é que, quando a semana sair, ela
esteja no painel em poucas horas, e não quando alguém lembrar de rodar o pipeline.

## Estratificação de risco

O nível final é o **maior** entre dois critérios, para que nem uma epidemia fora de época
nem um patamar alto sustentado passem despercebidos:

1. **Canal endêmico** — posição da incidência frente aos quartis históricos da mesma
   semana do ano no município (só anos anteriores, janela de ±2 semanas).
2. **Patamares absolutos** — incidência semanal por 100 mil: 10, 30 e 60.

Validação histórica: o pico de semanas em risco *muito alto* ocorre em **2024 (46,9%)**,
a grande epidemia do período, seguido de 2022 (32,7%) e 2019 (26,2%); o mínimo é 2018
(3,4%), ano reconhecidamente calmo.

## Desempenho dos modelos

Desfecho: risco alto ou muito alto **4 semanas à frente**. Validação temporal em janela
expansiva (treina até o ano *t−1*, avalia em *t*), média de 2019 a 2025:

| Modelo | Sensibilidade | Especificidade | VPP | AUC | AUPRC | Brier |
|---|---|---|---|---|---|---|
| Referência (persistência) | 0,726 | 0,788 | 0,725 | 0,757 | 0,645 | 0,233 |
| Interpretável (logística) | 0,707 | 0,781 | 0,710 | 0,814 | 0,778 | 0,173 |
| Aprendizado (LightGBM) | **0,765** | 0,786 | 0,732 | 0,849 | 0,819 | 0,157 |
| **Combinado** (0,8·LightGBM + 0,2·persistência) | 0,757 | **0,789** | **0,733** | **0,852** | **0,822** | **0,155** |

Médias calculadas de `saidas/desempenho_modelos.csv`, sobre os 34 municípios. O painel
opera com o **combinado**. Estes números são da rodada de experimentos de 27/09/2026
([docs/achados_modelagem.md](docs/achados_modelagem.md), seção 8): o modelo passou de
41 para 23 variáveis — o bloco climático saiu por medição, e entraram Rt, p_rt1 e os
indicadores de transmissão do InfoDengue — com hiperparâmetros reajustados para o
tamanho real da base.

Leitura honesta: a rodada de 27/09 fez o aprendizado superar a persistência também em
sensibilidade, o que antes não acontecia. O ganho veio de três mudanças medidas — poda
do bloco climático, entrada dos indicadores de transmissão do InfoDengue e corte de
capacidade do LightGBM — mais a combinação com o estado presente. No operacional de
Brasília, no limiar de 0,80 já em uso, a especificidade foi de 0,58 para **0,75**,
cruzando o piso de 0,74 da literatura de sistemas de alerta (EWARS), com sensibilidade
0,77 e VPP 0,90. Dois caminhos testados e **descartados** por medição: calibração
pós-hoc e pesos de recência — os números estão na seção 8 dos achados.

## Estrutura

```
Painel VIGIA-Dengue (offline).html  o painel: canvas do Claude Design,
                               autocontido (desenho, dados e fontes)
app/servidor.py                serve o painel em localhost
app/artifact/corpo.html        gabarito de uma versão anterior do painel
app/painel.py                  dashboard Streamlit (versão anterior)
src/vigia/territorio.py        os 34 municípios da RIDE-DF, com a regra validada
src/vigia/ingestao_infodengue.py  download da série município-semana
src/vigia/base_analitica.py    incidência, médias móveis, defasagens, flags
src/vigia/risco.py             canal endêmico e estratificação em 4 níveis
src/vigia/modelagem.py         3 modelos e validação temporal
src/vigia/rede_neural.py       a GRU avaliada, mantida como registro
src/vigia/setores_df.py        malha e indicadores por setor censitário
src/vigia/painel_dados.py      probabilidade de alerta e fatores explicativos
src/vigia/alerta.py            o ciclo que avisa só quando algo muda
src/vigia/verificar_fontes.py  reconfere os dados contra as fontes de origem
src/vigia/dicionario.py        gera o dicionário da própria base
docs/dicionario_de_dados_completo.md  todas as colunas, papel e fonte
docs/achados_modelagem.md      o que foi medido, inclusive o que não funcionou
testes/test_base.py            testes das regras críticas
```

## Cuidados metodológicos

**Vazamento temporal.** Nenhuma variável explicativa enxerga o futuro: médias móveis são
deslocadas por `shift(1)`, o canal endêmico usa só anos anteriores e a validação é
temporal. Três testes automatizados verificam isso a cada execução, porque é um erro
silencioso que inflaria as métricas.

**Atraso de notificação.** As semanas recentes vêm subnotificadas — na última semana da
série, um município exibia 92 casos notificados contra 184 estimados. Todo o cálculo de
incidência e risco usa `casos_est`, e o painel sinaliza as semanas provisórias.

## Próximos passos

- Incorporar os microdados do SINAN, cujo acesso foi restabelecido, para estratificar
  por idade, sexo e gravidade e testar a escala intraurbana pelo bairro de residência.
- Etapa 6: manual do usuário e relatório técnico final.
- Operação sombra: acompanhar os alertas em tempo real e ajustar o limiar.
- Avaliação de usabilidade com profissionais de vigilância (exige submissão ao CEP).
- Calibração das probabilidades e análise da antecedência efetiva do alerta.

---

Ferramenta de apoio à vigilância epidemiológica. Não substitui a análise da equipe de
vigilância local nem orienta conduta clínica individual.
