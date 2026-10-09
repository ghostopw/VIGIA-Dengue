# Pacote de dados -- VIGIA-Dengue

Gerado em 2026-09-27.

Territorio: a RIDE-DF completa -- Distrito Federal, Entorno goiano e os
4 municipios mineiros (34 ao todo).
Unidade de analise: municipio x semana epidemiologica.

Fontes:
- InfoDengue (Fiocruz/FGV) -- API alertcity: casos, casos estimados por
  nowcasting, incidencia, Rt e clima semanal.
- IBGE -- APIs de localidades e de malhas: populacao e cartografia.

| Arquivo | Linhas | Colunas | Conteudo |
|---|---|---|---|
| `dengue_municipio_semana.csv` | 22.440 | 37 | Dengue: serie municipio-semana bruta do InfoDengue, 2014-2026. |
| `chikungunya_municipio_semana.csv` | 22.440 | 37 | Chikungunya: serie municipio-semana bruta do InfoDengue, 2016-2026. |
| `zika_municipio_semana.csv` | 17.986 | 37 | Zika: serie municipio-semana bruta do InfoDengue, 2016-2026. |
| `base_analitica.csv` | 22.440 | 119 | Tabela analitica: incidencia, medias moveis, defasagens e flags. |
| `base_com_risco.csv` | 22.440 | 128 | Base analitica acrescida do canal endemico e da estratificacao de risco. |
| `painel.csv` | 20.638 | 39 | Base do painel: probabilidade de alerta e fatores explicativos. |
| `malha_municipios.geojson` | - | - | Malha cartografica dos municipios da RIDE-DF (IBGE). |
| `desempenho_modelos.csv` | 28 | 12 | Metricas da validacao temporal dos tres modelos, por ano. |
| `brutos_por_municipio/` | - | - | 102 CSVs: retorno original da API, um por municipio e arbovirose. |

## Dicionario das variaveis

A descricao completa de todas as colunas da base analitica esta em
`docs/dicionario_de_dados_completo.md` no repositorio do projeto,
gerada da propria base por `src/vigia/executar_dicionario.py`.

## Observacoes de uso

- **Use `casos_est`, nao `casos`, para semanas recentes.** As ultimas semanas
  vem subnotificadas por atraso de digitacao; `casos_est` corrige isso por
  nowcasting. A coluna `dado_provisorio` sinaliza as linhas afetadas.
- **`casos` x `casprov`.** `casos` conta todas as notificacoes; `casprov` conta
  casos provaveis (descartados excluidos), que e o conceito usado nos boletins
  do Ministerio da Saude.
- **Chave de integracao:** `cod_ibge` + `se_codigo`.