"""Canais por onde o alerta sai do computador.

A decisao de avisar esta em `alerta.py`; aqui esta so o transporte. A separacao
importa porque o criterio epidemiologico nao deve mudar quando se troca o meio
de aviso, e porque um canal que falha -- rede fora, webhook errado -- nao pode
derrubar os outros.

CANAIS
------
arquivo   sempre. Grava `saidas/alerta.json` e `saidas/alerta.txt`. E o unico
          que nao depende de nada e serve de registro do que foi avisado; o
          servidor local publica o JSON em /alerta.json.
windows   notificacao nativa do Windows, sem dependencia externa. Alcanca quem
          esta na maquina.
webhook   POST do JSON para a URL em VIGIA_WEBHOOK. E o caminho para alcancar
          alguem longe da maquina: Slack, Discord, Telegram via bot, n8n, o que
          houver do outro lado.

Nenhum canal recebe nada quando nao ha evento: um alerta que chega toda hora
dizendo que nada mudou deixa de ser lido, e ai deixa de ser alerta.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SAIDAS = RAIZ / "saidas"
ARQUIVO_JSON = SAIDAS / "alerta.json"
ARQUIVO_TEXTO = SAIDAS / "alerta.txt"

VARIAVEL_WEBHOOK = "VIGIA_WEBHOOK"


def _resumo(resultado: dict) -> str:
    """Uma linha, para o corpo da notificacao."""
    estado = resultado["estado"]
    rotulo = f"{estado['semana'] % 100:02d}/{estado['semana'] // 100}"
    return (
        f"SE {rotulo}: {estado['casos_est']:.0f} casos estimados, "
        f"risco {estado['risco']}, "
        f"{estado['probabilidade_alerta']:.0%} de probabilidade de alerta."
    )


def em_arquivo(resultado: dict) -> bool:
    """Grava o estado corrente, tenha havido evento ou nao.

    Diferente dos outros canais, este registra sempre: e a fonte que o painel e
    o servidor leem para dizer quando foi a ultima verificacao.
    """
    SAIDAS.mkdir(parents=True, exist_ok=True)
    ARQUIVO_JSON.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if resultado.get("mensagem"):
        ARQUIVO_TEXTO.write_text(resultado["mensagem"], encoding="utf-8")
    return True


def no_windows(resultado: dict) -> bool:
    """Notificacao nativa do Windows, via WinRT."""
    if os.name != "nt":
        return False

    titulo = "VIGIA-Dengue -- Brasilia"
    corpo = _resumo(resultado)
    if resultado["eventos"]:
        corpo = resultado["eventos"][0] + " " + corpo

    script = f"""
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$modelo = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
    [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textos = $modelo.GetElementsByTagName('text')
$textos.Item(0).AppendChild($modelo.CreateTextNode({titulo!r})) | Out-Null
$textos.Item(1).AppendChild($modelo.CreateTextNode({corpo!r})) | Out-Null
$aviso = [Windows.UI.Notifications.ToastNotification]::new($modelo)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(
    'Microsoft.WindowsTerminal_8wekyb3d8bbwe!App').Show($aviso)
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True, capture_output=True, timeout=60,
        )
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def por_webhook(resultado: dict) -> bool:
    """POST do resultado para a URL em VIGIA_WEBHOOK, se houver."""
    url = os.environ.get(VARIAVEL_WEBHOOK, "").strip()
    if not url:
        return False

    import requests

    corpo = {
        "texto": resultado.get("mensagem") or _resumo(resultado),
        "eventos": resultado["eventos"],
        "estado": resultado["estado"],
        "em_alerta": resultado["em_alerta"],
    }
    try:
        resposta = requests.post(url, json=corpo, timeout=30)
        return resposta.ok
    except requests.RequestException:
        return False


def emitir(resultado: dict) -> dict[str, bool]:
    """Manda o alerta por todos os canais disponiveis.

    O arquivo e escrito sempre; os canais que interrompem alguem so entram
    quando ha evento. Cada canal e tentado por si: um que falhe nao impede os
    outros, e o retorno diz quais funcionaram.
    """
    entregues = {"arquivo": em_arquivo(resultado)}

    if not resultado["eventos"]:
        return entregues

    entregues["windows"] = no_windows(resultado)
    entregues["webhook"] = por_webhook(resultado)
    return entregues
