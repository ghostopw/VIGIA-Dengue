"""Base analitica do Centro-Oeste: o conjunto de treino da rede neural.

Encadeia as mesmas etapas da base do painel -- derivacoes epidemiologicas e
climaticas, canal endemico, estratificacao de risco e vulnerabilidade --, so que
sobre os 468 municipios do Centro-Oeste em vez dos 34 da RIDE.

DUAS DIFERENCAS DELIBERADAS EM RELACAO A BASE DO PAINEL
--------------------------------------------------------
Sem o bloco de precipitacao. A chuva do painel vem do Open-Meteo, uma serie por
municipio, e coletar 468 delas esbarra na cota diaria do servico. A validacao do
proprio projeto ja mostrou que o bloco acrescenta quase nada ao modelo, e a
temperatura e a umidade -- que vem junto com o InfoDengue, sem custo extra --
carregam o sinal climatico principal. Quando a chuva do Centro-Oeste existir,
basta passa-la em `chuva`.

Vulnerabilidade dos 468, e nao dos 34. Vem de
`executar_vulnerabilidade_co.py`. Dois municipios ficam sem indicador --
Paraiso das Aguas e Boa Esperanca do Norte, criados depois da referencia do
Censo --, o que e ausencia por idade do municipio, e nao por pobreza: a falha
nao vicia o treino na direcao que importaria.

Uso:  python src/vigia/executar_base_centro_oeste.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from vigia.base_analitica import construir  # noqa: E402
from vigia.risco import classificar  # noqa: E402
from vigia.vulnerabilidade import integrar  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
PROCESSADO = RAIZ / "dados" / "processado"
EXTERNO = RAIZ / "dados" / "externo"

BRUTO = PROCESSADO / "infodengue_centro_oeste.csv"
DESTINO = PROCESSADO / "base_centro_oeste.csv"
VULNERABILIDADE = EXTERNO / "vulnerabilidade_centro_oeste.csv"


def principal() -> int:
    if not BRUTO.exists():
        raise SystemExit(
            f"{BRUTO.name} ausente. Rode antes: "
            "python src/vigia/executar_centro_oeste.py"
        )

    bruto = pd.read_csv(BRUTO)
    print(f"serie bruta: {len(bruto):,} linhas | "
          f"{bruto['cod_ibge'].nunique()} municipios".replace(",", "."))

    print("construindo a base analitica...")
    base = construir(bruto, chuva=None)

    if VULNERABILIDADE.exists():
        base = integrar(base, pd.read_csv(VULNERABILIDADE))
        cobertura = base["esgoto_inadequado_pct"].notna().mean() * 100
        print(f"  vulnerabilidade integrada ({cobertura:.1f}% das linhas)")
    else:
        print("  aviso: vulnerabilidade_centro_oeste.csv ausente; "
              "rode executar_vulnerabilidade_co.py")

    print("classificando o risco...")
    com_risco = classificar(base)
    com_risco.to_csv(DESTINO, index=False, encoding="utf-8")

    print(f"\n{len(com_risco):,} linhas x {com_risco.shape[1]} colunas"
          .replace(",", "."))
    distribuicao = com_risco["risco"].value_counts()
    print("  " + " | ".join(f"{nivel}: {n:,}".replace(",", ".")
                            for nivel, n in distribuicao.items()))
    print(f"gravado em {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
