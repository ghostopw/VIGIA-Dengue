"""Gera o painel VIGIA-Dengue como pagina HTML autocontida.

Combina o gabarito de `app/artifact/corpo.html` -- que carrega o desenho da
pagina, o CSS e o JavaScript -- com os dados atuais exportados por
`exportar_dados_painel.py`. O resultado e um arquivo unico, que abre no
navegador sem servidor e pode ser enviado a quem nao vai instalar Python.

Uso:  python src/vigia/exportar_dados_painel.py   (atualiza os dados)
      python src/vigia/gerar_painel_html.py       (monta a pagina)
"""

from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
GABARITO = RAIZ / "app" / "artifact" / "corpo.html"
DADOS = RAIZ / "dados" / "processado" / "painel_dados.json"
DESTINO = RAIZ / "Painel VIGIA-Dengue (offline).html"


def gerar(destino: Path = DESTINO) -> Path:
    dados = json.loads(DADOS.read_text(encoding="utf-8"))
    corpo = GABARITO.read_text(encoding="utf-8")

    # O JSON entra em <script type="application/json">, onde nao e preciso
    # escapar aspas -- apenas a sequencia que fecharia a tag antes da hora.
    bruto = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    destino.write_text(corpo.replace("/*__DADOS__*/", bruto.replace("</", "<\/")),
                       encoding="utf-8")
    return destino


if __name__ == "__main__":
    caminho = gerar()
    print(f"painel gerado: {caminho} ({caminho.stat().st_size / 1024:.0f} KB)")
