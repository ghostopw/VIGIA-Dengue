"""Pipeline da base analitica ate a validacao dos modelos (Etapas 2 a 4).

Le a serie bruta do InfoDengue, constroi a tabela analitica, classifica o risco
e executa a validacao temporal dos tres modelos de alerta.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from vigia.base_analitica import construir  # noqa: E402
from vigia.modelagem import preparar, validacao_temporal  # noqa: E402
from vigia.risco import classificar  # noqa: E402
from vigia.vulnerabilidade import integrar  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
ANOS_AVALIACAO = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
HORIZONTE = 4

if __name__ == "__main__":
    processado = RAIZ / "dados" / "processado"
    bruto = pd.read_csv(processado / "infodengue_territorio.csv")

    # Precipitacao: bloco opcional, coletado por executar_chuva.py.
    arquivo_chuva = RAIZ / "dados" / "externo" / "chuva_semanal.csv"
    chuva = pd.read_csv(arquivo_chuva) if arquivo_chuva.exists() else None

    print("construindo a base analitica...")
    base = construir(bruto, chuva=chuva)
    if chuva is not None:
        cobertura = base["chuva_semana_mm"].notna().mean() * 100
        print(f"  bloco de precipitacao integrado ({cobertura:.0f}% das linhas)")
    else:
        print("  aviso: chuva_semanal.csv ausente; execute executar_chuva.py")

    # Vulnerabilidade socioambiental: indicadores municipais fixos no tempo,
    # coletados por executar_vulnerabilidade.py. Se o arquivo ainda nao existir,
    # a base segue sem o bloco em vez de interromper o pipeline.
    arquivo_vulnerabilidade = RAIZ / "dados" / "externo" / "vulnerabilidade.csv"
    if arquivo_vulnerabilidade.exists():
        base = integrar(base, pd.read_csv(arquivo_vulnerabilidade))
        print("  bloco de vulnerabilidade socioambiental integrado")
    else:
        print("  aviso: vulnerabilidade.csv ausente; execute executar_vulnerabilidade.py")

    base.to_csv(processado / "base_analitica.csv", index=False, encoding="utf-8")
    print(f"  {len(base)} linhas x {base.shape[1]} colunas")

    print("classificando o risco...")
    com_risco = classificar(base)
    com_risco.to_csv(processado / "base_com_risco.csv", index=False, encoding="utf-8")
    distribuicao = com_risco["risco"].value_counts()
    print("  " + " | ".join(f"{nivel}: {n}" for nivel, n in distribuicao.items()))

    print(f"validando os modelos (horizonte de {HORIZONTE} semanas)...")
    dados = preparar(com_risco, horizonte=HORIZONTE)
    desempenho = validacao_temporal(dados, anos_avaliacao=ANOS_AVALIACAO)

    saidas = RAIZ / "saidas"
    saidas.mkdir(parents=True, exist_ok=True)
    desempenho.to_csv(saidas / "desempenho_modelos.csv", index=False)

    resumo = desempenho.groupby("modelo")[
        ["sensibilidade", "especificidade", "vpp", "auc", "auprc", "brier"]
    ].mean().round(3)
    print()
    print(resumo.to_string())
