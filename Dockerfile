# Painel VIGIA-Dengue servido como aplicativo Streamlit.
#
# O painel e autocontido: importa apenas pandas, plotly e streamlit. Nao
# precisa de geopandas nem lightgbm, que sao do pipeline de analise e pesam
# centenas de megabytes. Instalar so o necessario mantem a imagem pequena.
#
# Escuta na porta 80 de proposito: assim a rota do Cloudflare Tunnel continua
# apontando para vigia:80, como todos os outros sites, e nao ha nada a mudar
# no painel da Cloudflare.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=80 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Só o que o painel usa em tempo de execução.
COPY requirements-painel.txt .
RUN pip install --no-cache-dir -r requirements-painel.txt

# O código e os dados que o painel lê. A lista é explícita: copiar o
# repositório inteiro traria 600 MB de dados brutos e o histórico do git.
COPY .streamlit/ ./.streamlit/
COPY app/painel.py ./app/painel.py
COPY dados/externo/malha_ras_df.geojson      ./dados/externo/
COPY dados/externo/setores_df.geojson        ./dados/externo/
COPY dados/externo/vulnerabilidade_ras.csv   ./dados/externo/
COPY dados/processado/painel.csv             ./dados/processado/
COPY saidas/desempenho_modelos.csv           ./saidas/
COPY saidas/alerta.json                      ./saidas/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1/_stcore/health').read()" || exit 1

# enableCORS e enableXsrfProtection ficam desligados porque o acesso chega
# por um proxy (o tunel), e nao direto do navegador para este container.
CMD ["streamlit", "run", "app/painel.py", \
     "--server.port=80", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
