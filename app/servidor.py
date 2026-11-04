"""VIGIA-Dengue -- servidor local do site.

Gera os dados (src/vigia/exportar_site.py) e serve a pasta `site/` em
localhost, exatamente como o nginx da imagem publica. Para ver uma mudanca
no HTML, CSS ou JavaScript basta recarregar o navegador; para ver dados novos,
reinicie o servidor (ou rode o exportador).

Uso:  python app/servidor.py                (http://localhost:8000)
      python app/servidor.py --porta 8080
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SITE = RAIZ / "site"
sys.path.insert(0, str(RAIZ / "src"))

from vigia.exportar_site import salvar  # noqa: E402


class Servidor(HTTPServer):
    """HTTPServer que recusa uma porta ja ocupada.

    O padrao da biblioteca liga SO_REUSEADDR, e no Windows isso deixa dois
    servidores escutarem o mesmo endereco: as requisicoes se dividem entre
    eles sem aviso, e o navegador acaba mostrando a pagina do outro processo.
    """

    allow_reuse_address = False


class Manipulador(SimpleHTTPRequestHandler):
    """Arquivos estaticos sem cache, para o recarregar refletir a edicao."""

    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".js": "text/javascript; charset=utf-8",
                      ".json": "application/json; charset=utf-8",
                      ".css": "text/css; charset=utf-8",
                      ".csv": "text/csv; charset=utf-8"}

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, formato: str, *args) -> None:
        # So a pagina e os erros; o resto e ruido.
        if args and (str(args[0]).startswith("GET / ") or str(args[1])[:1] in "45"):
            super().log_message(formato, *args)


def principal() -> None:
    analisador = argparse.ArgumentParser(description="Servidor local do site VIGIA-Dengue.")
    analisador.add_argument("--porta", type=int, default=8000, help="porta HTTP (padrao: 8000)")
    analisador.add_argument("--host", default="127.0.0.1", help="endereco de escuta")
    analisador.add_argument("--sem-navegador", action="store_true",
                            help="nao abre o navegador automaticamente")
    argumentos = analisador.parse_args()

    dados = salvar(SITE / "dados")
    print(f"dados gerados: {dados} ({dados.stat().st_size / 1024:.0f} KB)")

    manipulador = partial(Manipulador, directory=str(SITE))
    try:
        servidor = Servidor((argumentos.host, argumentos.porta), manipulador)
    except OSError as erro:
        # Porta ocupada por outro processo: sem este aviso o navegador abriria
        # a pagina do outro servico, e o erro passaria por bug do site.
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
