# VIGIA-Dengue

Ferramenta digital de alerta precoce para estratificação espaço-temporal do risco de
dengue, com **foco em Brasília (Distrito Federal)** e os 29 municípios goianos do
Entorno como território de comparação.

Projeto PIBITI 2026 — Iniciação em Desenvolvimento Tecnológico e Inovação
**Aluno:** João Gabriel Alves Guimarães (2512082047)
**Orientadora:** Natália Ribeiro de Souza Evangelista (201534)
**Instituição:** IESB — Ciências da Saúde / Saúde Coletiva / Epidemiologia

---

## O que já está pronto

| Etapa do projeto | Situação | Onde está |
|---|---|---|
| 1 — Revisão e planejamento | Dicionário de dados e critérios operacionais | [docs/dicionario_de_dados.md](docs/dicionario_de_dados.md) |
| 2 — Base analítica | 19.770 linhas município-semana, 2014–2026 | `src/vigia/ingestao_infodengue.py`, `src/vigia/base_analitica.py` |
| 3 — Análise espaço-temporal | Canal endêmico e estratificação em 4 níveis | `src/vigia/risco.py` |
| 4 — Modelagem de alerta | 3 modelos com validação temporal | `src/vigia/modelagem.py` |
| 5 — Dashboard | Painel web com mapa 3D, séries e relatórios | `Painel VIGIA-Dengue (offline).html`, `app/servidor.py` |
| 6 — Avaliação e documentação | Métricas apuradas; manual e relatório pendentes | `saidas/desempenho_modelos.csv` |

## Território piloto

**Foco: Brasília.** O DF concentra **69% da população** e **63,5% dos casos** do
território — por isso o painel abre em Brasília, com bloco de indicadores próprio, e
o Entorno entra como contexto recolhido.

**30 municípios na base**: o Distrito Federal e os 29 municípios goianos do Entorno.

> **Regra do território — vale para toda coleta, presente e futura.** Municípios de
> Minas Gerais estão **excluídos** por decisão do projeto, ainda que a RIDE-DF legal
> (LC 94/1998, ampliada pela LC 163/2018) os inclua. Toda rotina de coleta — das APIs
> atuais ou de qualquer API que venha a ser criada — deve iterar sobre `TERRITORIO` e
> usar `filtrar_territorio()` para barrar municípios de fora. `validar_territorio()`
> recusa a base se alguma UF fora de DF/GO aparecer, e dois testes automatizados
> cobrem a regra.

> O DF é um único município na malha do IBGE e o InfoDengue não o desagrega por Região
> Administrativa. A RIDE foi adotada para que a análise espacial, os mapas e a
> estratificação entre municípios — cinco dos objetivos específicos — tivessem base de
> dados real. A escolha também é epidemiologicamente defensável: a dengue circula pelo
> pendularismo diário entre o DF e o Entorno.

## Fontes de dados

| Fonte | Uso | Acesso |
|---|---|---|
| InfoDengue (Fiocruz/FGV) | Casos, casos estimados por *nowcasting*, incidência, Rt, clima semanal | API pública `alertcity` |
| IBGE | População e malha cartográfica municipal | APIs de localidades e de malhas |

**Todas as URLs de origem** — as 132 requisições que geraram os dados brutos — estão
documentadas em [docs/fontes_dos_dados.md](docs/fontes_dos_dados.md). Cada link abre no
navegador e devolve exatamente o conteúdo que gerou o arquivo local correspondente.

> **Nota sobre o SINAN.** O projeto previa microdados do SINAN via DATASUS. O acesso
> (FTP e espelho HTTPS) não respondeu neste ambiente. O InfoDengue foi adotado por
> processar o próprio SINAN e por já entregar a série em município-semana **com correção
> do atraso de notificação** — requisito central para alerta precoce. Se o acesso ao
> DATASUS for restabelecido, os microdados permitem estratificar por idade, sexo e
> gravidade, o que o InfoDengue não oferece.

## Como reproduzir

```bash
pip install -r requirements.txt

python src/vigia/executar_ingestao.py        # baixa a série 2014-2026 (~5 min)
python src/vigia/executar_malha.py           # baixa a malha cartográfica
python src/vigia/executar_analise.py         # base analítica, risco e validação
python src/vigia/executar_painel_dados.py    # gera os dados do painel

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

- **Brasília por Região Administrativa** — as 31 RAs com geometria disponível, por
  população ou densidade. Não há casos por RA: o InfoDengue opera no nível municipal,
  e o DF é um único município.
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
| Referência (persistência) | 0,708 | **0,784** | 0,709 | 0,746 | 0,626 | 0,240 |
| Interpretável (logística) | 0,700 | 0,699 | 0,636 | 0,779 | 0,740 | 0,195 |
| Aprendizado (LightGBM) | 0,702 | 0,775 | **0,713** | **0,815** | **0,776** | **0,181** |

Leitura honesta: a persistência tem sensibilidade ligeiramente maior, porque repetir o
estado atual já acerta bastante quando a prevalência é alta. O ganho dos modelos está na
**discriminação e na calibração** — o LightGBM supera a referência em AUC (0,815 contra
0,746) e reduz o erro de Brier em 25%, e a vantagem é maior nos anos epidêmicos, quando
o alerta precisa funcionar.

## Estrutura

```
Painel VIGIA-Dengue (offline).html  o painel: canvas do Claude Design,
                               autocontido (desenho, dados e fontes)
app/servidor.py                serve o painel em localhost
app/artifact/corpo.html        gabarito de uma versão anterior do painel
app/painel.py                  dashboard Streamlit (versão anterior)
src/vigia/territorio.py        os 30 municípios, com a regra DF+GO validada
src/vigia/ingestao_infodengue.py  download da série município-semana
src/vigia/base_analitica.py    incidência, médias móveis, defasagens, flags
src/vigia/risco.py             canal endêmico e estratificação em 4 níveis
src/vigia/modelagem.py         3 modelos e validação temporal
src/vigia/painel_dados.py      probabilidade de alerta e fatores explicativos
docs/dicionario_de_dados.md    dicionário completo das 105 variáveis
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

- Etapa 6: manual do usuário e relatório técnico final.
- Operação sombra: acompanhar os alertas em tempo real e ajustar o limiar.
- Avaliação de usabilidade com profissionais de vigilância (exige submissão ao CEP).
- Calibração das probabilidades e análise da antecedência efetiva do alerta.

---

Ferramenta de apoio à vigilância epidemiológica. Não substitui a análise da equipe de
vigilância local nem orienta conduta clínica individual.
