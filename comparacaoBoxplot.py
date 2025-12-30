import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Caminhos dos arquivos (mantenha os seus)
ARQUIVO_UNI = r'Resultados\Redações Uni-agente.xlsx'
ARQUIVO_MULTI = r'Resultados\Redações Multi-Agente.xlsx'

df_uni = pd.read_excel(ARQUIVO_UNI)
df_multi = pd.read_excel(ARQUIVO_MULTI)

dados_boxplot = []

# --- Processamento de Dados (Mantido igual) ---
for i in range(1, 6):
    col_name = f'c{i}'
    if col_name in df_uni.columns:
        temp = df_uni[[col_name]].copy()
        temp.columns = ['Nota']
        temp['Competencia'] = f'C{i}'
        temp['Modelo'] = 'Uni-Agente'
        dados_boxplot.append(temp)

for i in range(1, 6):
    possiveis_nomes = [f'nota_agregador_validada_C{i}', f'nota_agregador_C{i}']
    col_encontrada = None
    for nome in possiveis_nomes:
        if nome in df_multi.columns:
            col_encontrada = nome
            break
    if col_encontrada:
        temp = df_multi[[col_encontrada]].copy()
        temp.columns = ['Nota']
        temp['Competencia'] = f'C{i}'
        temp['Modelo'] = 'Multi-Agente'
        dados_boxplot.append(temp)

for i in range(1, 6):
    col_name = f'c{i}_antiga'
    if col_name in df_uni.columns:
        temp = df_uni[[col_name]].copy()
        temp.columns = ['Nota']
        temp['Competencia'] = f'C{i}'
        temp['Modelo'] = 'Humano (Ref.)'
        dados_boxplot.append(temp)

df_long = pd.concat(dados_boxplot, ignore_index=True)

# --- ALTERAÇÕES PARA CORRIGIR A MARGEM ---

# 1. Ajuste o tamanho da figura para ser mais alto que largo (Retrato)
# Largura 8, Altura 10 (proporção melhor para página A4)
plt.figure(figsize=(8, 10)) 

sns.boxplot(
    data=df_long,
    y='Competencia', # 2. Competência vai para o Eixo Y
    x='Nota',        # 3. Nota vai para o Eixo X
    hue='Modelo',
    palette=['skyblue', 'salmon', 'lightgreen'],
    orient='h'       # 4. Força a orientação horizontal das caixas
)

# Ajustes estéticos para o novo layout
plt.xlabel('Pontuação (0–200)') # Rótulo muda para baixo
plt.ylabel('Competência')       # Rótulo muda para a esquerda
plt.grid(True, axis='x', linestyle='--', alpha=0.3) # Grid agora é no eixo X

# Move a legenda para o topo ou base para economizar largura
plt.legend(title='Avaliador', loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3)

plt.tight_layout() # Garante que nada fique cortado
plt.savefig('boxplot_comparativo_competencias.png', dpi=300)
plt.close()

nota_humano = df_uni['nota_antiga']
nota_uni = df_uni['nota_nova']

col_total_multi = 'nota_agregador_validada_total'
if col_total_multi not in df_multi.columns:
    col_total_multi = 'nota_agregador_total'

nota_multi = df_multi[col_total_multi]

bins = [0, 200, 400, 500, 600, 700, 800, 900, 1000]
labels = ['0-200', '201-400', '401-500', '501-600', '601-700', '701-800', '801-900', '901-1000']

freq_humano = pd.cut(nota_humano, bins=bins, labels=labels, include_lowest=True).value_counts().sort_index()
freq_uni = pd.cut(nota_uni, bins=bins, labels=labels, include_lowest=True).value_counts().sort_index()
freq_multi = pd.cut(nota_multi, bins=bins, labels=labels, include_lowest=True).value_counts().sort_index()

df_tabela = pd.DataFrame({
    'Faixa de Nota': labels,
    'Humano': freq_humano.values,
    'Uni-Agente': freq_uni.values,
    'Multi-Agente': freq_multi.values
})

print(df_tabela.to_latex(
    index=False,
    caption='Distribuição de Frequência das Notas Totais',
    label='tab:freq_notas_comparativa'
))

df_tabela.to_csv('tabela_frequencia_notas.csv', index=False)
