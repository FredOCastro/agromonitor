"""
analyze.py
Chama a Claude API para analisar os dados coletados,
detectar mudanças de status e gerar recomendações de hedge.
"""

import json
import os
import anthropic
from datetime import datetime

BASE_DIR     = os.path.dirname(__file__)
DATA_PATH    = os.path.join(BASE_DIR, "data_atual.json")
STATE_PATH   = os.path.join(BASE_DIR, "state.json")
ANALISE_PATH = os.path.join(BASE_DIR, "analise.json")

def carregar_dados():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)

def carregar_estado_anterior():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_novo_estado(analise, dados):
    estado = {
        "timestamp": datetime.now().isoformat(),
        "oni": dados["enso"]["oni_atual"],
        "status_enso": dados["enso"]["status"],
        "soja_usd": dados["precos"]["soja_cbot"]["preco_usd_bushel"],
        "milho_usd": dados["precos"]["milho_cbot"]["preco_usd_bushel"],
        "cambio": dados["precos"]["cambio_usd_brl"],
        "nivel_risco": analise.get("nivel_risco", "Desconhecido"),
        "recomendacao_hedge_soja_pct": analise.get("recomendacao_hedge_soja_pct", 0),
        "recomendacao_hedge_milho_pct": analise.get("recomendacao_hedge_milho_pct", 0),
    }
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
    return estado

def analisar_com_claude(dados, estado_anterior):
    print("Enviando dados para Claude API...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resumo_anterior = "Nenhum estado anterior disponível (primeiro monitoramento)."
    if estado_anterior:
        resumo_anterior = f"""
Estado anterior ({estado_anterior.get('timestamp', 'data desconhecida')}):
- ONI: {estado_anterior.get('oni', 'N/A')} — Status: {estado_anterior.get('status_enso', 'N/A')}
- Soja: USD {estado_anterior.get('soja_usd', 'N/A')}/bu
- Milho: USD {estado_anterior.get('milho_usd', 'N/A')}/bu
- Câmbio: R$ {estado_anterior.get('cambio', 'N/A')}
- Nível de risco anterior: {estado_anterior.get('nivel_risco', 'N/A')}
"""
    prompt = f"""
Você é um analista agroclimático sênior especializado em soja e milho no Brasil Central.
Seu cliente é um produtor rural com fazendas em Araxá, Ibiá, Perdizes e Tapira (Triângulo Mineiro, MG).
As culturas principais são Soja, Milho (1ª e 2ª safra) e Laranja.
Ele precisa de análise para decisão de hedge (travamento de preço de venda antecipado).

=== DADOS COLETADOS AGORA ===
{json.dumps(dados, ensure_ascii=False, indent=2)}

=== ESTADO ANTERIOR ===
{resumo_anterior}

=== SUA TAREFA ===
Analise os dados e responda APENAS com um objeto JSON válido (sem markdown, sem texto fora do JSON).

O JSON deve ter EX
