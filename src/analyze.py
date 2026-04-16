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

def montar_prompt(dados, estado_anterior):
    resumo_anterior = "Primeiro monitoramento, sem estado anterior."
    if estado_anterior:
        resumo_anterior = (
            "Estado anterior: ONI=" + str(estado_anterior.get("oni")) +
            " status=" + str(estado_anterior.get("status_enso")) +
            " soja=USD" + str(estado_anterior.get("soja_usd")) +
            " milho=USD" + str(estado_anterior.get("milho_usd")) +
            " cambio=R$" + str(estado_anterior.get("cambio")) +
            " risco=" + str(estado_anterior.get("nivel_risco"))
        )

    dados_str = json.dumps(dados, ensure_ascii=False, indent=2)

    instrucao = (
        "Voce e um analista agroclimatico senior especializado em soja e milho no Brasil Central. "
        "Seu cliente e um produtor rural com fazendas em Araxa, Ibia, Perdizes e Tapira (Triangulo Mineiro, MG). "
        "As culturas principais sao Soja, Milho (1a e 2a safra) e Laranja. "
        "Ele precisa de analise para decisao de hedge.\n\n"
        "DADOS ATUAIS:\n" + dados_str + "\n\n"
        "ESTADO ANTERIOR:\n" + resumo_anterior + "\n\n"
        "Responda APENAS com JSON valido, sem markdown, sem texto fora do JSON.\n"
        "Estrutura obrigatoria:\n"
        '{"data_analise":"DD/MM/AAAA HH:MM",'
        '"nivel_risco":"Baixo ou Medio ou Alto ou Critico",'
        '"mudanca_detectada":true,'
        '"tipo_mudanca":"descricao",'
        '"alerta_imediato":false,'
        '"motivo_alerta":"",'
        '"assunto_email":"assunto curto",'
        '"enso_resumo":"1-2 frases",'
        '"clima_resumo":"1-2 frases",'
        '"precos_resumo":"1-2 frases",'
        '"safras_resumo":"1-2 frases",'
        '"recomendacao_hedge_soja_pct":50,'
        '"recomendacao_hedge_milho_pct":40,'
        '"justificativa_hedge":"2-3 frases",'
        '"resumo_executivo":"3 paragrafos para o produtor",'
        '"acoes_recomendadas":["acao 1","acao 2","acao 3"],'
        '"proximo_evento_importante":"descricao",'
        '"proximo_evento_data":"Mes/Ano"}'
    )
    return instrucao

def analisar_com_claude(dados, estado_anterior):
    print("Enviando dados para Claude API...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = montar_prompt(dados, estado_anterior)
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    texto = response.content[0].text.strip()
    if texto.startswith("```"):
        linhas = texto.split("\n")
        texto = "\n".join(linhas[1:-1])
    analise = json.loads(texto)
    analise["data_analise"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    return analise

def main():
    print("\n" + "="*50)
    print("AGRO MONITOR - Analise Claude")
    print("Data/hora: " + datetime.now().strftime("%d/%m/%Y %H:%M"))
    print("="*50 + "\n")
    dados = carregar_dados()
    estado_anterior = carregar_estado_anterior()
    analise = analisar_com_claude(dados, estado_anterior)
    with open(ANALISE_PATH, "w", encoding="utf-8") as f:
        json.dump(analise, f, ensure_ascii=False, indent=2)
    salvar_novo_estado(analise, dados)
    print("Analise concluida!")
    print("Nivel de risco: " + analise["nivel_risco"])
    print("Alerta imediato: " + str(analise["alerta_imediato"]))
    print("Hedge soja: " + str(analise["recomendacao_hedge_soja_pct"]) + "%")
    print("Hedge milho: " + str(analise["recomendacao_hedge_milho_pct"]) + "%\n")

if __name__ == "__main__":
    main()
