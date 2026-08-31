"""VIGIA-Dengue -- servidor local do painel.

Serve o painel de `app/artifact/corpo.html` como pagina web em localhost,
montando o desenho com os dados de `dados/processado/painel_dados.json` a
cada requisicao. Editar o gabarito ou reexportar os dados e recarregar o
navegador basta -- nao ha etapa de build.

Uso:  python app/servidor.py                (http://localhost:8000)
      python app/servidor.py --porta 8080
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from functools import partial
from math import isfinite
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
GABARITO = RAIZ / "app" / "artifact" / "corpo.html"
DADOS = RAIZ / "dados" / "processado" / "painel_dados.json"

# O gabarito e um fragmento -- carrega <title>, <style> e o corpo, mas nao a
# moldura do documento. Aqui ela e fechada com o mesmo reset minimo que a
# pagina ja pressupoe.
MOLDURA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{ margin: 0; font: 14px/1.5 system-ui, sans-serif; }}
  img {{ max-width: 100%; }}
  [hidden] {{ display: none !important; }}
</style>
{corpo}
</body>
</html>
"""


def sem_nan(valor):
    """Troca NaN e infinitos por None, recursivamente.

    O nowcasting deixa o limite superior do intervalo vazio nas semanas mais
    recentes, e esse vazio chega aqui como NaN.
    """
    if isinstance(valor, float) and not isfinite(valor):
        return None
    if isinstance(valor, dict):
        return {c: sem_nan(v) for c, v in valor.items()}
    if isinstance(valor, list):
        return [sem_nan(v) for v in valor]
    return valor


def montar_pagina() -> bytes:
    """Injeta os dados atuais no gabarito e devolve a pagina pronta."""
    corpo = GABARITO.read_text(encoding="utf-8")
    dados = json.loads(DADOS.read_text(encoding="utf-8"))

    # `json.dumps` emite NaN por padrao -- uma extensao que o Python le de
    # volta, mas que o `JSON.parse` do navegador rejeita, derrubando a pagina
    # inteira. `allow_nan=False` obriga a converter antes: valor ausente vira
    # `null`, que o gabarito ja trata como "sem dado".
    bruto = json.dumps(sem_nan(dados), ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False)

    # O JSON entra em <script type="application/json">, onde nao e preciso
    # escapar aspas -- apenas a sequencia que fecharia a tag antes da hora.
    corpo = corpo.replace("/*__DADOS__*/", bruto.replace("</", r"<\/"))

    # O <title> e o <link> das fontes precisam ficar no <head>; o restante do
    # gabarito e conteudo de <body>. A quebra acontece na primeira linha que
    # nao pertence mais ao cabecalho.
    cabecalho, resto = separar_cabecalho(corpo)
    return MOLDURA.format(corpo=cabecalho + "</head>\n<body>\n" + resto).encode("utf-8")


def separar_cabecalho(corpo: str) -> tuple[str, str]:
    """Divide o gabarito entre o que vai no <head> e o que vai no <body>.

    O <title>, o <link> das fontes e o <style> global abrem o arquivo; a
    pagina propriamente dita comeca no primeiro elemento depois deles.
    """
    marca = corpo.find("<script type=\"application/json\"")
    if marca == -1:
        return "", corpo
    return corpo[:marca], corpo[marca:]


class Servidor(HTTPServer):
    """HTTPServer que recusa uma porta ja ocupada.

    O padrao da biblioteca liga SO_REUSEADDR, e no Windows isso deixa dois
    servidores escutarem o mesmo endereco: as requisicoes se dividem entre
    eles sem aviso, e o navegador acaba mostrando a pagina do outro processo.
    """

    allow_reuse_address = False


class Manipulador(SimpleHTTPRequestHandler):
    """Serve o painel na raiz e os arquivos do projeto no restante."""

    def do_GET(self) -> None:  # noqa: N802 (assinatura da biblioteca padrao)
        if self.path in ("/", "/index.html", "/painel"):
            self.responder_painel()
        else:
            super().do_GET()

    def responder_painel(self) -> None:
        try:
            pagina = montar_pagina()
        except FileNotFoundError as erro:
            self.send_error(500, "Arquivo ausente", str(erro))
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(pagina)))
        # Sem cache: recarregar o navegador reflete a edicao mais recente.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(pagina)

    def log_message(self, formato: str, *args) -> None:
        # Silencia o ruido de favicon e afins; erros continuam visiveis.
        if args and str(args[0]).startswith(("GET / ", "GET /painel")):
            super().log_message(formato, *args)


def principal() -> None:
    analisador = argparse.ArgumentParser(description="Servidor local do painel VIGIA-Dengue.")
    analisador.add_argument("--porta", type=int, default=8000, help="porta HTTP (padrao: 8000)")
    analisador.add_argument("--host", default="127.0.0.1", help="endereco de escuta")
    analisador.add_argument("--sem-navegador", action="store_true",
                            help="nao abre o navegador automaticamente")
    argumentos = analisador.parse_args()

    manipulador = partial(Manipulador, directory=str(RAIZ))
    try:
        servidor = Servidor((argumentos.host, argumentos.porta), manipulador)
    except OSError as erro:
        # Porta ocupada por outro processo: sem este aviso o navegador abriria
        # a pagina do outro servico, e o erro passaria por bug do painel.
        raise SystemExit(
            f"porta {argumentos.porta} indisponivel ({erro.strerror or erro}).\n"
            f"Use outra:  python app/servidor.py --porta {argumentos.porta + 1}"
        ) from erro
    endereco = f"http://{argumentos.host}:{argumentos.porta}"

    print(f"VIGIA-Dengue no ar: {endereco}")
    print("Ctrl+C para encerrar.")

    if not argumentos.sem_navegador:
        webbrowser.open(endereco)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nservidor encerrado.")
        servidor.server_close()


if __name__ == "__main__":
    principal()
