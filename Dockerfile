# Site VIGIA-Dengue (vigia.guimm.site): pagina estatica servida pelo nginx.
#
# Dois estagios. O primeiro gera os dados do site (site/dados/painel.json) a
# partir do que o repositorio versiona, com src/vigia/exportar_site.py; so ele
# precisa de Python e pandas. O segundo e um nginx puro com a pagina e os
# dados prontos: sem Python em tempo de execucao, a imagem final tem poucos MB
# e sobe em menos de um segundo.
#
# Escuta na porta 80 de proposito: a rota do Cloudflare Tunnel continua
# apontando para vigia:80, como todos os outros sites, e nao ha nada a mudar
# no painel da Cloudflare.

FROM python:3.12-slim AS dados

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /build

COPY requirements-site.txt .
RUN pip install --no-cache-dir -r requirements-site.txt

# A lista e explicita: copiar o repositorio inteiro traria 600 MB de dados
# brutos e o historico do git.
COPY src/vigia/exportar_site.py              src/vigia/
COPY dados/processado/painel.csv             dados/processado/
COPY dados/externo/malha_ride_df.geojson     dados/externo/
COPY dados/externo/malha_ras_df.geojson      dados/externo/
COPY dados/externo/vulnerabilidade_ras.csv   dados/externo/
COPY saidas/desempenho_modelos.csv           saidas/
COPY saidas/alarmes.json                     saidas/
COPY saidas/clima_futuro.json                saidas/
COPY saidas/alerta.json                      saidas/
COPY docs/dicionario_de_dados.csv            docs/
COPY docs/glossario.csv                      docs/

RUN python src/vigia/exportar_site.py --destino /build/site-dados


FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY site/index.html site/estilo.css site/app.js /usr/share/nginx/html/
COPY --from=dados /build/site-dados/ /usr/share/nginx/html/dados/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/saude || exit 1
