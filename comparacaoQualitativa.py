import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import re

df_uni = pd.read_excel(r"Resultados\Redações Uni-Agente.xlsx")
df_multi = pd.read_excel(r"Resultados\Redações Multi-Agente.xlsx")

stopwords_pt = set([
    'de','a','o','que','e','do','da','em','um','uma','para','com','não','os','as',
    'dos','das','se','na','no','como','mais','mas','foi','ao','ele','ela','por','seu',
    'sua','ter','ser','está','são','pela','pelo','ou','também','é','estão','entre','há',
    'muito','seja','isso','esse','essa','esses','essas','tem','têm','nos','nas','pode',
    'podem','será','sobre','nota','pois','apresenta','entanto','geral','alguns','algumas',
    'texto','redação','apenas','bem','bom','boa','candidato','demonstra','apresentar','deve',
    'uso','utilização','falta','necessidade','argumentos','ideias','forma','tema','proposta',
    'intervenção','competência','domínio','norma','culta','relação','melhor','pouco','ainda',
    'cada','pontos','análise','ponto','sendo','assim'
])

def limpar_e_tokenizar(texto):
    if pd.isna(texto):
        return []
    texto = re.sub(r"[^\w\s]", "", str(texto).lower())
    palavras = texto.split()
    return [p for p in palavras if p not in stopwords_pt and not p.isdigit() and len(p) > 2]

cols_uni = [
    "justificativa_c1",
    "justificativa_c2",
    "justificativa_c3",
    "justificativa_c4",
    "justificativa_c5"
]

texto_uni = " ".join(df_uni[cols_uni].fillna("").apply(lambda x: " ".join(x.astype(str)), axis=1))
tokens_uni = limpar_e_tokenizar(texto_uni)
contagem_uni = Counter(tokens_uni).most_common(10)

cols_multi = [c for c in df_multi.columns if "justificativa" in c.lower()]
texto_multi = " ".join(df_multi[cols_multi].fillna("").apply(lambda x: " ".join(x.astype(str)), axis=1))
tokens_multi = limpar_e_tokenizar(texto_multi)
contagem_multi = Counter(tokens_multi).most_common(10)

plt.figure(figsize=(8, 6))
sns.barplot(
    x=[x[1] for x in contagem_uni],
    y=[x[0] for x in contagem_uni]
)
plt.title("Vocabulário Mais Frequente: Uni-Agente")
plt.xlabel("Frequência")
plt.tight_layout()
plt.savefig("palavras_frequentes_uni.png", dpi=300)
plt.close()

plt.figure(figsize=(8, 6))
sns.barplot(
    x=[x[1] for x in contagem_multi],
    y=[x[0] for x in contagem_multi]
)
plt.title("Vocabulário Mais Frequente: Multi-Agente")
plt.xlabel("Frequência")
plt.tight_layout()
plt.savefig("palavras_frequentes_multi.png", dpi=300)
plt.close()

df_uni["tamanho"] = df_uni[cols_uni].fillna("").apply(lambda x: len(" ".join(x.astype(str)).split()), axis=1)
df_multi["tamanho"] = df_multi[cols_multi].fillna("").apply(lambda x: len(" ".join(x.astype(str)).split()), axis=1)

df_plot = pd.DataFrame({
    "Modelo": ["Uni-Agente"] * len(df_uni) + ["Multi-Agente"] * len(df_multi),
    "Contagem de Palavras": pd.concat([df_uni["tamanho"], df_multi["tamanho"]], ignore_index=True)
})

plt.figure(figsize=(9, 6))
sns.boxplot(x="Modelo", y="Contagem de Palavras", data=df_plot)
plt.tight_layout()
plt.savefig("comparacao_tamanho_texto.png", dpi=300)
plt.close()
