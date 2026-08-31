"""VIGIA-Dengue -- servidor local do painel.

Serve o painel `Painel VIGIA-Dengue (offline).html` -- o canvas exportado do
Claude Design, que carrega o desenho, os dados e as fontes num arquivo so --
como site em localhost. O arquivo e lido a cada requisicao: reexportar o
canvas e recarregar o navegador basta, nao ha etapa de build.

Uso:  python app/servidor.py                (http://localhost:8000)
      python app/servidor.py --porta 8080
"""

from __future__ import annotations

import argparse
import webbrowser
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PAINEL = RAIZ / "Painel VIGIA-Dengue (offline).html"


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
            pagina = PAINEL.read_bytes()
        except FileNotFoundError:
            self.send_error(
                500, "Painel ausente",
                f"{PAINEL.name} nao encontrado. Exporte o canvas do Claude "
                "Design para a raiz do projeto com esse nome.",
            )
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(pagina)))
        # Sem cache: recarregar o navegador reflete a exportacao mais recente.
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

    if not PAINEL.exists():
        raise SystemExit(f"painel nao encontrado: {PAINEL}")

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
    print(f"servindo: {PAINEL.name} ({PAINEL.stat().st_size / 1024:.0f} KB)")
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
