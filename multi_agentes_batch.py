import json
import asyncio
import httpx
import csv
from pathlib import Path
from datetime import datetime
import random

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:12b"

REGRA_VERIFICACAO = '''REGRA DE VERIFICAÇÃO OBRIGATÓRIA

Antes de finalizar sua resposta, verifique rigorosamente:

1) FORMATO
- A saída DEVE ser um JSON válido.
- Não escreva nenhum texto fora do JSON.
- Não use markdown, comentários ou explicações adicionais.

2) NOTA
- O campo "nota" DEVE existir.
- O valor DEVE ser um número inteiro.
- O valor DEVE estar no intervalo 0 ≤ nota ≤ 200.
- Se a nota estiver fora do intervalo, ajuste para o limite válido mais próximo.

3) JUSTIFICATIVA
- O campo "justificativa" DEVE existir.
- O valor DEVE ser uma string objetiva, técnica e impessoal.
- Não inclua sugestões de correção nem comentários pedagógicos.

4) COERÊNCIA INTERNA
- A justificativa deve ser compatível com a nota atribuída.
- Evite contradições (ex: elogio máximo com nota baixa).

5) FORMATO FINAL OBRIGATÓRIO
Retorne EXCLUSIVAMENTE no seguinte formato:

{
  "nota": 0-200,
  "justificativa": "Justificativa técnica, clara e objetiva, indicando elementos ausentes ou bem definidos."
}
'''

SYSTEM_PROMPTS = {
    "C1": f'''Você é o Avaliador da Competência 1 do ENEM (Domínio da Norma Culta da Língua Portuguesa).

Avalie exclusivamente:
- Ortografia
- Acentuação
- Morfossintaxe
- Regência e concordância
- Pontuação
- Clareza sintática

Desconsidere conteúdo, argumentos ou tema.

Atribua uma nota inteira entre 0 e 200, obrigatoriamente baseada nos níveis oficiais do ENEM.

{REGRA_VERIFICACAO}
''',
    "C2": f'''Você é o Avaliador da Competência 2 do ENEM (Compreensão da Proposta e Desenvolvimento do Tema).

Avalie exclusivamente:
- Atendimento ao tema proposto
- Adequação ao tipo dissertativo-argumentativo
- Progressão temática
- Presença de introdução, desenvolvimento e conclusão
- Ausência de tangenciamento ou fuga ao tema

Não avalie gramática nem proposta de intervenção.

Atribua uma nota inteira entre 0 e 200, conforme os níveis oficiais do ENEM.

{REGRA_VERIFICACAO}
''',
    "C3": f'''Você é o Avaliador da Competência 3 do ENEM (Seleção, Organização e Desenvolvimento de Argumentos).

Avalie exclusivamente:
- Clareza da tese
- Relevância e consistência dos argumentos
- Relação lógica entre ideias
- Uso de repertório sociocultural produtivo (quando presente)
- Profundidade argumentativa

Desconsidere erros gramaticais e coesão superficial.

Atribua uma nota inteira entre 0 e 200, conforme os níveis oficiais do ENEM.

{REGRA_VERIFICACAO}
''',
    "C4": f'''Você é o Avaliador da Competência 4 do ENEM (Mecanismos Linguísticos de Coesão).

Avalie exclusivamente:
- Uso adequado de conectivos
- Referenciação (anáfora e catáfora)
- Encadeamento lógico entre frases e parágrafos
- Progressão textual fluida

Não avalie ortografia nem argumentação em si.

Atribua uma nota inteira entre 0 e 200, conforme os níveis oficiais do ENEM.

{REGRA_VERIFICACAO}
''',
    "C5": f'''Você é o Avaliador da Competência 5 do ENEM (Proposta de Intervenção).

Avalie exclusivamente a presença e adequação dos 5 elementos obrigatórios:
1. Agente
2. Ação
3. Modo/meio
4. Finalidade
5. Detalhamento

Verifique também:
- Relação direta com o problema discutido
- Respeito aos direitos humanos

Desconsidere gramática e argumentação geral.

Atribua uma nota inteira entre 0 e 200, conforme os níveis oficiais do ENEM.

{REGRA_VERIFICACAO}
''',
    "AGREGADOR": '''Você é o Avaliador Chefe do ENEM.

Sua função é:
- Ler a redação original
- Analisar as avaliações das Competências C1 a C5
- Validar coerência entre notas e justificativas
- Calcular a nota final (soma direta das cinco competências)

Gere o boletim final contendo:
- Nota total (0–1000)
- Quadro-resumo com notas C1–C5
- Diagnóstico geral do desempenho
- Dicas práticas e objetivas de melhoria (uma por competência)

REGRA DE VERIFICAÇÃO OBRIGATÓRIA

Antes de finalizar o boletim, verifique rigorosamente:

1) FORMATO
- A saída DEVE ser um JSON válido.
- Não escreva nenhum texto fora do JSON.
- Não utilize markdown, listas ou explicações externas.

2) NOTAS DAS COMPETÊNCIAS
- Verifique se C1, C2, C3, C4 e C5 existem.
- Cada nota DEVE ser um número inteiro entre 0 e 200.
- Caso alguma nota esteja fora do intervalo, normalize para o limite válido mais próximo.

3) NOTA FINAL
- Calcule a soma das notas das cinco competências.
- A "nota_final" NÃO PODE ser maior que essa soma.
- A "nota_final" NÃO PODE ser maior que 1000.
- Se houver divergência, a nota final DEVE ser igual à soma calculada.
- Você deve calcular a nota_final exclusivamente como a soma dos valores numéricos que você verificou nos campos de competência.

4) CONSISTÊNCIA GERAL
- O diagnóstico geral deve ser coerente com a nota final.
- As dicas práticas devem corresponder às competências com menor pontuação.

5) FORMATO FINAL OBRIGATÓRIO
Retorne EXCLUSIVAMENTE no seguinte formato:

{
  "C1": { "nota": number, "justificativa": string },
  "C2": { "nota": number, "justificativa": string },
  "C3": { "nota": number, "justificativa": string },
  "C4": { "nota": number, "justificativa": string },
  "C5": { "nota": number, "justificativa": string },
  "nota_final": number,
  "diagnostico_geral": "texto",
  "dicas_praticas": {
    "C1": "texto",
    "C2": "texto",
    "C3": "texto",
    "C4": "texto",
    "C5": "texto"
  }
}

'''
}


async def call_ollama_simple(prompt: str, system_prompt: str) -> tuple:
    """Chama Ollama e retorna (sucesso, resposta_texto)"""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system_prompt,
        "stream": True,
        "temperature": 0.1
    }

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            result = ""

            async with client.stream(
                "POST",
                OLLAMA_URL,
                json=payload
            ) as response:

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    if line.startswith("data: "):
                        line = line[6:]

                    try:
                        obj = json.loads(line)
                    except:
                        continue

                    token = obj.get("response")
                    if token:
                        result += token

                    if obj.get("done"):
                        break

        return True, result.strip()

    except Exception as e:
        return False, f"Erro de conexão: {e}"


def extrair_nota_justificativa(resposta_json_str: str) -> dict:
    """Extrai nota e justificativa da resposta JSON"""
    try:
        # Remove markdown se houver
        resposta_json_str = resposta_json_str.strip()
        if resposta_json_str.startswith("```"):
            lines = resposta_json_str.split("\n")
            resposta_json_str = "\n".join(lines[1:-1])
        
        dados = json.loads(resposta_json_str)
        return {
            "nota": int(dados.get("nota", 0)),
            "justificativa": dados.get("justificativa", "")
        }
    except Exception as e:
        return {"nota": 0, "justificativa": f"Erro ao processar: {str(e)}"}


def extrair_resultado_agregador(resposta_json_str: str) -> dict:
    """Extrai resultado completo do agregador"""
    try:
        resposta_json_str = resposta_json_str.strip()
        if resposta_json_str.startswith("```"):
            lines = resposta_json_str.split("\n")
            resposta_json_str = "\n".join(lines[1:-1])
        
        dados = json.loads(resposta_json_str)
        return {
            "nota_final": int(dados.get("nota_final", 0)),
            "diagnostico_geral": dados.get("diagnostico_geral", ""),
            "dicas_praticas": dados.get("dicas_praticas", {})
        }
    except Exception as e:
        return {
            "nota_final": 0,
            "diagnostico_geral": f"Erro ao processar agregador: {str(e)}",
            "dicas_praticas": {}
        }


async def avaliar_redacao(redacao_texto: str, tema: str, redacao_id: str) -> dict:
    """Avalia uma redação completa usando os 5 agentes + agregador"""
    print(f"\n Avaliando redação ID: {redacao_id}")
    
    resultados = {}
    
    # Avalia cada competência
    for i, key in enumerate(["C1", "C2", "C3", "C4", "C5"], start=1):
        print(f"    Competência {i}...", end=" ", flush=True)
        
        prompt = f"Avalie tecnicamente a redação abaixo e responda nota e justificativa.\n\nREDAÇÃO:\n{redacao_texto}"
        ok, resp_text = await call_ollama_simple(prompt, SYSTEM_PROMPTS[key])
        
        if not ok:
            resultados[key] = {"nota": 0, "justificativa": f"Erro: {resp_text}"}
        else:
            resultado = extrair_nota_justificativa(resp_text)
            resultados[key] = resultado
            print(f" (Nota: {resultado['nota']})")
    
    # Prepara consolidado para o agregador
    consolidado = "\n\n".join([
        f"--- Competência {i} ---\nNota: {resultados[f'C{i}']['nota']}\nJustificativa: {resultados[f'C{i}']['justificativa']}"
        for i in range(1, 6)
    ])
    
    # Chama o agregador
    print(f"   Agregador...", end=" ", flush=True)
    prompt_agregador = f"""REDAÇÃO ORIGINAL:
{redacao_texto}

AVALIAÇÕES (C1 a C5):
{consolidado}

Gere o boletim final com nota total e dicas práticas.
"""
    ok, resp_agregador = await call_ollama_simple(prompt_agregador, SYSTEM_PROMPTS["AGREGADOR"])
    
    # Salva as notas originais dos agentes individuais
    resultados["agentes_individuais"] = {}
    for i in range(1, 6):
        comp_key = f"C{i}"
        resultados["agentes_individuais"][comp_key] = {
            "nota": resultados[comp_key]["nota"],
            "justificativa": resultados[comp_key]["justificativa"]
        }
    
    if ok:
        resultado_agregador = extrair_resultado_agregador(resp_agregador)
        
        # Sobrescreve as notas e justificativas dos agentes com as validadas pelo agregador
        for i in range(1, 6):
            comp_key = f"C{i}"
            if comp_key in resultado_agregador:
                # Usa nota e justificativa validadas pelo agregador
                resultados[comp_key]["nota"] = resultado_agregador[comp_key].get("nota", resultados[comp_key]["nota"])
                resultados[comp_key]["justificativa"] = resultado_agregador[comp_key].get("justificativa", resultados[comp_key]["justificativa"])
        
        resultados["nota_final"] = resultado_agregador.get("nota_final", sum(resultados[f"C{i}"]["nota"] for i in range(1, 6)))
        resultados["diagnostico_geral"] = resultado_agregador.get("diagnostico_geral", "")
        resultados["dicas_praticas"] = resultado_agregador.get("dicas_praticas", {})
    else:
        # Se agregador falhar, calcula nota final manualmente
        resultados["nota_final"] = sum(resultados[f"C{i}"]["nota"] for i in range(1, 6))
        resultados["diagnostico_geral"] = "Erro ao gerar diagnóstico"
        resultados["dicas_praticas"] = {f"C{i}": "" for i in range(1, 6)}

    
    print(f" Nota Final dos Agentes: {resultados['nota_final']}/1000\n")
    
    return resultados


def carregar_redacoes(pasta_conjunto: Path, num_redacoes: int = 200) -> list:
    """Carrega todas as redações de todos os arquivos JSON e retorna uma amostra"""
    todas_redacoes = []
    
    # Lista todos os arquivos JSON
    arquivos_json = sorted(pasta_conjunto.glob("tema-*.json"))
    
    print(f"Encontrados {len(arquivos_json)} arquivos JSON")
    
    for arquivo in arquivos_json:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                redacoes = json.load(f)
                for redacao in redacoes:
                    redacao['arquivo_origem'] = arquivo.name
                    todas_redacoes.append(redacao)
        except Exception as e:
            print(f"Erro ao carregar {arquivo.name}: {e}")
    
    print(f"Total de redações carregadas: {len(todas_redacoes)}")
    
    # Seleciona amostra aleatória (limitada ao número solicitado)
    tamanho_amostra = min(num_redacoes, len(todas_redacoes))
    amostra = random.sample(todas_redacoes, tamanho_amostra)
    
    percentual = (tamanho_amostra / len(todas_redacoes)) * 100
    print(f"Selecionadas {len(amostra)} redações ({percentual:.1f}% do total)\n")
    
    return amostra


def extrair_notas_originais(redacao: dict) -> dict:
    """Extrai notas originais das competências"""
    notas = {}
    
    for comp in redacao['competencias']:
        comp_nome = comp['competencia'].lower()
        nota_str = comp['nota']
        
        if 'modalidade escrita formal' in comp_nome or 'domínio da modalidade' in comp_nome:
            notas['C1'] = int(nota_str)
        elif 'compreender a proposta' in comp_nome:
            notas['C2'] = int(nota_str)
        elif 'selecionar, relacionar' in comp_nome:
            notas['C3'] = int(nota_str)
        elif 'mecanismos linguísticos' in comp_nome or 'conhecimento dos mecanismos' in comp_nome:
            notas['C4'] = int(nota_str)
        elif 'proposta de intervenção' in comp_nome or 'proposta de intervenÃ§Ã£o' in comp_nome:
            notas['C5'] = int(nota_str)
    
    return notas


async def main():
    print("="*80)
    print("SISTEMA DE AVALIAÇÃO AUTOMATIZADA DE REDAÇÕES - MULTI-AGENTES")
    print("="*80)
    print()
    
    # Configurações
    pasta_conjunto = Path("codigo/conjunto_1/conjunto_1")
    num_redacoes_processar = 400  # Número fixo de redações
    
    if not pasta_conjunto.exists():
        print(f" Pasta não encontrada: {pasta_conjunto}")
        return
    
    # Carrega redações
    redacoes = carregar_redacoes(pasta_conjunto, num_redacoes_processar)
    
    # Prepara arquivo CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"resultados_avaliacao_{timestamp}.csv"
    
    # Cabeçalhos do CSV
    fieldnames = [
        'redacao_id',
        'arquivo_origem',
        'tema',
        # Notas originais (do dataset)
        'nota_original_C1',
        'nota_original_C2',
        'nota_original_C3',
        'nota_original_C4',
        'nota_original_C5',
        'nota_original_total',
        # Notas dos agentes INDIVIDUAIS (primeira avaliação)
        'nota_agente_individual_C1',
        'nota_agente_individual_C2',
        'nota_agente_individual_C3',
        'nota_agente_individual_C4',
        'nota_agente_individual_C5',
        'nota_agente_individual_total',
        # Notas VALIDADAS pelo AGREGADOR
        'nota_agregador_validada_C1',
        'nota_agregador_validada_C2',
        'nota_agregador_validada_C3',
        'nota_agregador_validada_C4',
        'nota_agregador_validada_C5',
        'nota_agregador_validada_total',
        # Diferenças (Original vs Agregador Validado)
        'diferenca_C1',
        'diferenca_C2',
        'diferenca_C3',
        'diferenca_C4',
        'diferenca_C5',
        'diferenca_total',
        # Justificativas dos agentes INDIVIDUAIS
        'justificativa_individual_C1',
        'justificativa_individual_C2',
        'justificativa_individual_C3',
        'justificativa_individual_C4',
        'justificativa_individual_C5',
        # Justificativas VALIDADAS pelo AGREGADOR
        'justificativa_agregador_C1',
        'justificativa_agregador_C2',
        'justificativa_agregador_C3',
        'justificativa_agregador_C4',
        'justificativa_agregador_C5',
        # Diagnóstico e dicas do AGREGADOR
        'diagnostico_geral',
        'dica_pratica_C1',
        'dica_pratica_C2',
        'dica_pratica_C3',
        'dica_pratica_C4',
        'dica_pratica_C5',
    ]
    
    print(f"💾 Salvando resultados em: {csv_filename}\n")
    print("="*80)
    print("INICIANDO PROCESSAMENTO")
    print("="*80)
    
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Processa cada redação
        for idx, redacao in enumerate(redacoes, 1):
            print(f"\n[{idx}/{len(redacoes)}] Processando...")
            
            # Extrai dados originais
            redacao_id = redacao.get('id', 'N/A')
            arquivo_origem = redacao.get('arquivo_origem', 'N/A')
            tema = redacao['tema']
            texto = redacao['texto']
            nota_original_total = float(redacao['nota'])
            notas_originais = extrair_notas_originais(redacao)
            
            # Avalia com os agentes
            resultado_agentes = await avaliar_redacao(texto, tema, redacao_id)
            
            # Calcula diferenças
            row = {
                'redacao_id': redacao_id,
                'arquivo_origem': arquivo_origem,
                'tema': tema[:100],  # Limita tamanho
            }
            
            # Notas originais (do dataset)
            for i in range(1, 6):
                comp_key = f"C{i}"
                row[f'nota_original_{comp_key}'] = notas_originais.get(comp_key, 0)
            row['nota_original_total'] = nota_original_total
            
            # Notas dos agentes INDIVIDUAIS
            agentes_individuais = resultado_agentes.get('agentes_individuais', {})
            nota_individual_total = 0
            for i in range(1, 6):
                comp_key = f"C{i}"
                nota_individual = agentes_individuais.get(comp_key, {}).get('nota', 0)
                row[f'nota_agente_individual_{comp_key}'] = nota_individual
                nota_individual_total += nota_individual
            row['nota_agente_individual_total'] = nota_individual_total
            
            # Notas VALIDADAS pelo AGREGADOR
            for i in range(1, 6):
                comp_key = f"C{i}"
                row[f'nota_agregador_validada_{comp_key}'] = resultado_agentes[comp_key]['nota']
            row['nota_agregador_validada_total'] = resultado_agentes['nota_final']
            
            # Diferenças (Original vs Agregador Validado)
            for i in range(1, 6):
                comp_key = f"C{i}"
                diff = resultado_agentes[comp_key]['nota'] - notas_originais.get(comp_key, 0)
                row[f'diferenca_{comp_key}'] = diff
            row['diferenca_total'] = resultado_agentes['nota_final'] - nota_original_total
            
            # Justificativas dos agentes INDIVIDUAIS
            for i in range(1, 6):
                comp_key = f"C{i}"
                row[f'justificativa_individual_{comp_key}'] = agentes_individuais.get(comp_key, {}).get('justificativa', '')
            
            # Justificativas VALIDADAS pelo AGREGADOR
            for i in range(1, 6):
                comp_key = f"C{i}"
                row[f'justificativa_agregador_{comp_key}'] = resultado_agentes[comp_key]['justificativa']
            
            # Diagnóstico e dicas do AGREGADOR
            row['diagnostico_geral'] = resultado_agentes.get('diagnostico_geral', '')
            dicas = resultado_agentes.get('dicas_praticas', {})
            for i in range(1, 6):
                comp_key = f"C{i}"
                row[f'dica_pratica_{comp_key}'] = dicas.get(comp_key, '')
            
            # Escreve no CSV
            writer.writerow(row)
            csvfile.flush()  # Garante que os dados sejam escritos imediatamente
            
            print(f"   💾 Salvo no CSV")
    
    print("\n" + "="*80)
    print("PROCESSAMENTO CONCLUÍDO!")
    print("="*80)
    print(f"\n✅ Total de redações processadas: {len(redacoes)}")
    print(f"📄 Resultados salvos em: {csv_filename}")
    print("\nO arquivo CSV contém:")
    print("  - Notas ORIGINAIS (prefixo: nota_original_)")
    print("  - Notas dos AGENTES (prefixo: nota_agente_)")
    print("  - DIFERENÇAS entre agentes e originais (prefixo: diferenca_)")
    print("  - Justificativas completas dos agentes")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
