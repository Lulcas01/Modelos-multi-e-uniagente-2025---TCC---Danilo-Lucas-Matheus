import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import cohen_kappa_score, mean_absolute_error

df_uni = pd.read_excel(r"Código dos modelos e Resultados\Resultados\Redações Uni-agente.xlsx")
df_multi = pd.read_excel(r"Código dos modelos e Resultados\Resultados\Redações Multi-Agente.xlsx")

def calcular_metricas(y_true, y_pred, nome_modelo):
    y_true = pd.to_numeric(y_true, errors="coerce")
    y_pred = pd.to_numeric(y_pred, errors="coerce")
    dados = pd.concat([y_true, y_pred], axis=1).dropna()
    y_true, y_pred = dados.iloc[:, 0], dados.iloc[:, 1]
    qwk = cohen_kappa_score(y_true, y_pred, weights="quadratic")
    mae = mean_absolute_error(y_true, y_pred)
    pearson = np.corrcoef(y_true, y_pred)[0, 1]
    return {
        "Modelo": nome_modelo,
        "QWK (Kappa)": round(qwk, 4),
        "MAE": round(mae, 2),
        "Correlação (Pearson)": round(pearson, 4)
    }

res_uni = calcular_metricas(
    df_uni["nota_antiga"],
    df_uni["nota_nova"],
    "Uni-Agente"
)

res_multi = calcular_metricas(
    df_multi["nota_original_total"],
    df_multi["nota_agregador_validada_total"],
    "Multi-Agente"
)

df_resultados = pd.DataFrame([res_uni, res_multi])
print(df_resultados)

plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
sns.scatterplot(x=df_uni["nota_antiga"], y=df_uni["nota_nova"], alpha=0.6)
plt.plot([0, 1000], [0, 1000], "r--")
plt.title(f"Uni-Agente (QWK={res_uni['QWK (Kappa)']})")
plt.xlabel("Nota Humana")
plt.ylabel("Nota IA")
plt.grid(alpha=0.3)

plt.subplot(1, 2, 2)
sns.scatterplot(x=df_multi["nota_original_total"], y=df_multi["nota_agregador_validada_total"], alpha=0.6)
plt.plot([0, 1000], [0, 1000], "r--")
plt.title(f"Multi-Agente (QWK={res_multi['QWK (Kappa)']})")
plt.xlabel("Nota Humana")
plt.ylabel("Nota IA")
plt.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("comparacao_modelos.png", dpi=300)
plt.show()

competencias = ["C1", "C2", "C3", "C4", "C5"]
dados_comp = []

for c in competencias:
    k_uni = cohen_kappa_score(
        pd.to_numeric(df_uni[f"{c.lower()}_antiga"], errors="coerce"),
        pd.to_numeric(df_uni[f"{c.lower()}"], errors="coerce"),
        weights="quadratic"
    )
    k_multi = cohen_kappa_score(
        pd.to_numeric(df_multi[f"nota_original_{c}"], errors="coerce"),
        pd.to_numeric(df_multi[f"nota_agregador_validada_{c}"], errors="coerce"),
        weights="quadratic"
    )
    dados_comp.append({
        "Competência": c,
        "Kappa Uni": round(k_uni, 4),
        "Kappa Multi": round(k_multi, 4)
    })

df_comp = pd.DataFrame(dados_comp)
print(df_comp)

with pd.ExcelWriter("avaliacao_final_modelos.xlsx") as writer:
    df_resultados.to_excel(writer, sheet_name="Resumo Geral", index=False)
    df_comp.to_excel(writer, sheet_name="Por Competência", index=False)
