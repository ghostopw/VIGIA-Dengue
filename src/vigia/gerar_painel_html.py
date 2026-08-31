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
from math import isfinite
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
GABARITO = RAIZ / "app" / "artifact" / "corpo.html"
DADOS = RAIZ / "dados" / "processado" / "painel_dados.json"
DESTINO = RAIZ / "Painel VIGIA-Dengue (offline).html"


def sem_nan(valor):
    """Troca NaN e infinitos por None, recursivamente."""
    if isinstance(valor, float) and not isfinite(valor):
        return None
    if isinstance(valor, dict):
        return {c: sem_nan(v) for c, v in valor.items()}
    if isinstance(valor, list):
        return [sem_nan(v) for v in valor]
    return valor


def gerar(destino: Path = DESTINO) -> Path:
    dados = json.loads(DADOS.read_text(encoding="utf-8"))
    corpo = GABARITO.read_text(encoding="utf-8")

    # O JSON entra em <script type="application/json">, onde nao e preciso
    # escapar aspas -- apenas a sequencia que fecharia a tag antes da hora.
    # `allow_nan=False` barra a extensao NaN/Infinity do Python, que o
    # `JSON.parse` do navegador rejeita -- ausencia vira `null`.
    bruto = json.dumps(sem_nan(dados), ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False)
    destino.write_text(corpo.replace("/*__DADOS__*/", bruto.replace("</", "<\/")),
                       encoding="utf-8")
    return destino


if __name__ == "__main__":
    caminho = gerar()
    print(f"painel gerado: {caminho} ({caminho.stat().st_size / 1024:.0f} KB)")
