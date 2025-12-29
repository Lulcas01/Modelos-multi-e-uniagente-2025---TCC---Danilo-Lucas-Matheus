import asyncio
import json
import httpx
import os
import csv
import re

# --- CONFIGURAÇÕES ---
PASTA_REDACOES = "Redações"
PASTA_RESULTADOS = "resultados_json_OFICIAL"
CSV_SAIDA = "resultado_completo.csv"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:latest"

os.makedirs(PASTA_RESULTADOS, exist_ok=True)

system_prompt = """
Você é um avaliador especialista do ENEM, capaz de analisar redações e atribuir notas às cinco competências oficiais.
Seu papel é ler a redação enviada e produzir notas individuais (0 a 200) para cada competência e uma nota final (0 a 1000), além de um breve diagnóstico.

Competências que você deve avaliar

Competência 1 – Domínio da norma culta.
Competência 2 – Compreensão da proposta e desenvolvimento do tema.
Competência 3 – Seleção e organização de argumentos.
Competência 4 – Coesão e coerência.
Competência 5 – Proposta de intervenção.

Regras de Avaliação
Siga estritamente os critérios da TRI do ENEM.
Não atribua notas intermediárias fracionadas.
As notas devem ser coerentes entre si.
Explique as notas com base em evidências do texto.

Formato Obrigatório (JSON):
{
  "competencia_1": { "nota": 0-200, "justificativa": "..." },
  "competencia_2": { "nota": 0-200, "justificativa": "..." },
  "competencia_3": { "nota": 0-200, "justificativa": "..." },
  "competencia_4": { "nota": 0-200, "justificativa": "..." },
  "competencia_5": { "nota": 0-200, "justificativa": "..." },
  "nota_final": 0-1000,
  "diagnostico_geral": "Texto resumido com os pontos fortes e fracos da redação."
}
"""

def extrair_json(texto):
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except:
        return None

async def avaliar_redacao(texto):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": texto,
        "system": system_prompt,
        "temperature": 0.1,
        "stream": True
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            resp = await client.post(OLLAMA_URL, json=payload)
            return resp.json().get("response", "").strip()
        except:
            return None

async def main():
    arquivo_temas = f"{PASTA_REDACOES}/todos_os_temas.json"

    with open(arquivo_temas, "r", encoding="utf-8") as f:
        lista_redacoes = json.load(f)

    contador = 0

    colunas = [
        "id", "nota_antiga", "nota_nova",
        "c1", "c2", "c3", "c4", "c5",
        "justificativa_c1", "justificativa_c2", "justificativa_c3",
        "justificativa_c4", "justificativa_c5",
        "diagnostico_geral", "tema",
        "c1_antiga", "c2_antiga", "c3_antiga", "c4_antiga", "c5_antiga"
    ]

    print(f"Iniciando processamento. Saída: {CSV_SAIDA}")

    with open(CSV_SAIDA, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=colunas)
        writer.writeheader()

        for bloco in lista_redacoes:
            iteravel = bloco if isinstance(bloco, list) else [bloco]

            for entrada in iteravel:
                try:
                    redacao_id = int(entrada.get("id", -1))
                except:
                    continue

                texto = entrada.get("texto", "")
                tema = entrada.get("tema", "")

                try:
                    nota_antiga = int(float(entrada.get("nota", 0)))
                except:
                    nota_antiga = 0

                comps_antigas = entrada.get("competencias", [])
                c_antigas = [0, 0, 0, 0, 0]
                if isinstance(comps_antigas, list) and len(comps_antigas) >= 5:
                    for i in range(5):
                        try:
                            c_antigas[i] = int(float(comps_antigas[i].get("nota", 0)))
                        except:
                            pass

                MAX_TENTATIVAS = 2
                resultado = None
                resposta_bruta = ""

                for tentativa in range(MAX_TENTATIVAS):
                    print(f"Avaliando ID {redacao_id} (Tentativa {tentativa+1}/{MAX_TENTATIVAS})...")
                    resposta_bruta = await avaliar_redacao(texto)

                    if resposta_bruta:
                        resultado = extrair_json(resposta_bruta)
                        if resultado:
                            break

                    print(" -> Falha ou JSON inválido")
                    await asyncio.sleep(1)

                if resultado is None:
                    print(f" -> ERRO: Falha ao avaliar ID {redacao_id}")
                    continue

                linha = {
                    "id": redacao_id,
                    "nota_antiga": nota_antiga,
                    "nota_nova": resultado.get("nota_final", 0),

                    "c1": resultado.get("competencia_1", {}).get("nota", 0),
                    "c2": resultado.get("competencia_2", {}).get("nota", 0),
                    "c3": resultado.get("competencia_3", {}).get("nota", 0),
                    "c4": resultado.get("competencia_4", {}).get("nota", 0),
                    "c5": resultado.get("competencia_5", {}).get("nota", 0),

                    "justificativa_c1": resultado.get("competencia_1", {}).get("justificativa", ""),
                    "justificativa_c2": resultado.get("competencia_2", {}).get("justificativa", ""),
                    "justificativa_c3": resultado.get("competencia_3", {}).get("justificativa", ""),
                    "justificativa_c4": resultado.get("competencia_4", {}).get("justificativa", ""),
                    "justificativa_c5": resultado.get("competencia_5", {}).get("justificativa", ""),

                    "diagnostico_geral": resultado.get("diagnostico_geral", ""),
                    "tema": tema,

                    "c1_antiga": c_antigas[0],
                    "c2_antiga": c_antigas[1],
                    "c3_antiga": c_antigas[2],
                    "c4_antiga": c_antigas[3],
                    "c5_antiga": c_antigas[4]
                }

                writer.writerow(linha)
                csvfile.flush()

                with open(f"{PASTA_RESULTADOS}/{redacao_id}.json", "w", encoding="utf-8") as f:
                    json.dump({
                        "id": redacao_id,
                        "nota_antiga": nota_antiga,
                        "nota_nova": resultado.get("nota_final", 0),
                        "avaliacao_llm": resultado,
                        "resposta_bruta": resposta_bruta
                    }, f, ensure_ascii=False, indent=2)

                contador += 1

    print(f"({contador} redações processadas)")

if __name__ == "__main__":
    asyncio.run(main())
