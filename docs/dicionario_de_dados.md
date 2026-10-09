# Dicionário de Dados — VIGIA-Dengue

Este arquivo foi substituído pelo dicionário **gerado da própria base**, que
cobre todas as colunas e não envelhece:

- **[dicionario_de_dados_completo.md](dicionario_de_dados_completo.md)** — a
  versão de leitura, com todas as colunas por bloco, papel na previsão,
  preenchimento e fonte, mais as variáveis do painel e os critérios
  operacionais que viviam aqui.
- **[dicionario_de_dados.csv](dicionario_de_dados.csv)** — a versão de máquina,
  que a aba *Dicionário de dados* do painel consome.

Para regenerar depois de mudar a base:

```bash
python src/vigia/executar_dicionario.py
```

`testes/test_dicionario.py` falha quando os artefatos ficam para trás da base
ou quando uma coluna nova aparece sem descrição — a descrição se acrescenta em
`src/vigia/dicionario.py`.

> Por que este arquivo não foi apagado: links antigos (README de commits
> passados, relatório parcial) apontam para cá. O conteúdo, esse mudou de casa.
