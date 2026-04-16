"""
send_alert.py - Envia alertas por email usando Resend, com painel ENSO.
"""

import json
import os
from datetime import datetime
import requests

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_DESTINO  = os.environ.get("EMAIL_DESTINO", "")

BASE_DIR     = os.path.dirname(__file__)
ANALISE_PATH = os.path.join(BASE_DIR, "analise.json")
DATA_PATH    = os.path.join(BASE_DIR, "data_atual.json")

FORCAR_ENVIO = os.environ.get("FORCAR_ENVIO", "false").lower() == "true"

CORES = {
    "Critico": {"header": "#A32D2D", "badge": "#FCEBEB", "badge_text": "#791F1F"},
    "Alto":    {"header": "#854F0B", "badge": "#FAEEDA", "badge_text": "#633806"},
    "Medio":   {"header": "#185FA5", "badge": "#E6F1FB", "badge_text": "#0C447C"},
    "Baixo":   {"header": "#27500A", "badge": "#EAF3DE", "badge_text": "#3B6D11"},
}

def get_cores(nivel):
    n = nivel.replace("\u00e9","e").replace("\u00ed","i").replace("\u00f3","o").replace("\u00ea","e")
    return CORES.get(n, CORES["Medio"])

def enso_barra(oni):
    pos = max(2, min(96, round((oni + 2.0) / 4.5 * 100)))
    html  = "<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"margin:10px 0 4px;\">"
    html += "<tr>"
    html += "<td width=\"20%\" style=\"background:#B5D4F4;padding:8px 4px;text-align:center;font-size:10px;font-weight:bold;color:#0C447C;border-radius:6px 0 0 6px;\">La Nina<br>Forte</td>"
    html += "<td width=\"20%\" style=\"background:#E6F1FB;padding:8px 4px;text-align:center;font-size:10px;font-weight:bold;color:#185FA5;\">La Nina<br>Fraca</td>"
    html += "<td width=\"20%\" style=\"background:#f0f0f0;padding:8px 4px;text-align:center;font-size:10px;font-weight:bold;color:#666;\">Neutro</td>"
    html += "<td width=\"20%\" style=\"background:#FAEEDA;padding:8px 4px;text-align:center;font-size:10px;font-weight:bold;color:#854F0B;\">El Nino<br>Fraco</td>"
    html += "<td width=\"20%\" style=\"background:#F5C4B3;padding:8px 4px;text-align:center;font-size:10px;font-weight:bold;color:#993C1D;border-radius:0 6px 6px 0;\">El Nino<br>Forte</td>"
    html += "</tr></table>"
    html += "<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"margin-bottom:4px;\"><tr>"
    html += "<td width=\"" + str(pos) + "%\" style=\"text-align:right;\">"
    html += "<span style=\"display:inline-block;background:#1a1a1a;color:white;font-size:11px;font-weight:bold;padding:3px 8px;border-radius:4px;\">ONI: " + str(oni) + "</span>"
    html += "</td><td></td></tr></table>"
    html += "<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\"><tr>"
    html += "<td style=\"font-size:10px;color:#999;\">-2.0</td>"
    html += "<td style=\"text-align:center;font-size:10px;color:#999;\">-0.5</td>"
    html += "<td style=\"text-align:center;font-size:10px;color:#999;\">0</td>"
    html += "<td style=\"text-align:center;font-size:10px;color:#999;\">+0.5</td>"
    html += "<td style=\"text-align:right;font-size:10px;color:#999;\">+2.5</td>"
    html += "</tr></table>"
    return html

def timeline_enso(oni_atual):
    meses = [
        ("Jul/25", -1.2, "ln"), ("Ago/25", -0.9, "ln"), ("Set/25", -0.6, "ln"),
        ("Out/25", -0.3, "ne"), ("Nov/25",  0.0, "ne"), ("Dez/25",  0.2, "ne"),
        ("Jan/26",  0.3, "ne"), ("Fev/26",  0.4, "ne"), ("Mar/26",  0.4, "ne"),
        ("Abr/26", oni_atual, "cur"),
        ("Mai/26",  0.7, "el"), ("Jun/26",  1.0, "el"), ("Jul/26",  1.3, "el"),
    ]
    bgs  = {"ln":"#E6F1FB", "ne":"#f8f8f8", "el":"#FAEEDA", "cur":"#fff3cd"}
    txts = {"ln":"#185FA5", "ne":"#666",    "el":"#854F0B",  "cur":"#A32D2D"}
    cells = ""
    for mes, val, tipo in meses:
        brd = "border:2px solid #E24B4A;" if tipo == "cur" else ""
        proj = "*" if tipo == "el" else ""
        cells += "<td style=\"background:" + bgs[tipo] + ";" + brd + "padding:6px 2px;text-align:center;border-right:1px solid #eee;\">"
        cells += "<span style=\"font-size:10px;font-weight:bold;color:" + txts[tipo] + ";\">" + str(val) + proj + "</span>"
        cells += "<br><span style=\"font-size:9px;color:#999;\">" + mes + "</span></td>"
    html  = "<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border:1px solid #eee;border-radius:6px;overflow:hidden;margin:10px 0;\">"
    html += "<tr>" + cells + "</tr></table>"
    html += "<p style=\"font-size:10px;color:#aaa;margin:0;\">* Projecao NOAA/INPE - Fundo laranja = El Nino previsto - La Nina encerrada mar/2026</p>"
    return html

def gerar_html(analise, dados, tipo):
    risco    = analise.get("nivel_risco", "Medio")
    cores    = get_cores(risco)
    enso     = dados.get("enso", {})
    precos   = dados.get("precos", {})
    soja     = precos.get("soja_cbot", {})
    milho    = precos.get("milho_cbot", {})
    clima    = dados.get("clima", {})
    araxa    = clima.get("Arax\u00e1", clima.get("Araxa", {}))
    oni      = enso.get("oni_atual", 0.4)
    status   = enso.get("status", "Neutro")
    tend     = enso.get("tendencia", "subindo")
    usd      = precos.get("cambio_usd_brl", "?")
    hs       = analise.get("recomendacao_hedge_soja_pct", "?")
    hm       = analise.get("recomendacao_hedge_milho_pct", "?")
    dt       = analise.get("data_analise", "")
    resumo   = analise.get("resumo_executivo", "").replace("\n", "<br><br>")
    enso_res = analise.get("enso_resumo", "")
    justif   = analise.get("justificativa_hedge", "")
    pe       = analise.get("proximo_evento_importante", "")
    pd_      = analise.get("proximo_evento_data", "")
    acoes    = analise.get("acoes_recomendadas", [])
    acoes_li = "".join("<li style=\"margin-bottom:8px;\">" + a + "</li>" for a in acoes)

    if tipo == "alerta":
        titulo = "Alerta Imediato - Agro Monitor"
        subtit = analise.get("tipo_mudanca", "")
    else:
        titulo = "Relatorio Semanal - Agro Monitor"
        subtit = "Resumo semanal de clima, precos e hedge"

    tend_cor  = "#A32D2D" if tend == "subindo" else "#185FA5"
    tend_seta = "&#9650;" if tend == "subindo" else "&#9660;"

    h = "<!DOCTYPE html><html><head><meta charset=\"UTF-8\"></head>"
    h += "<body style=\"font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0;\">"
    h += "<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"background:#f4f4f4;padding:20px 0;\"><tr><td align=\"center\">"
    h += "<table width=\"600\" cellpadding=\"0\" cellspacing=\"0\" style=\"background:#fff;border-radius:12px;overflow:hidden;\">"

    # Header
    h += "<tr><td style=\"background:" + cores["header"] + ";padding:24px 32px;\">"
    h += "<h1 style=\"color:#fff;margin:0;font-size:22px;\">" + titulo + "</h1>"
    h += "<p style=\"color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;\">" + subtit + "</p>"
    h += "</td></tr>"

    # Risco
    h += "<tr><td style=\"padding:20px 32px 0;\">"
    h += "<span style=\"background:" + cores["badge"] + ";color:" + cores["badge_text"] + ";padding:6px 16px;border-radius:6px;font-size:13px;font-weight:bold;\">RISCO: " + risco.upper() + "</span>"
    h += "<span style=\"padding-left:12px;font-size:12px;color:#666;\">" + dt + " - Triangulo Mineiro, MG</span>"
    h += "</td></tr>"

    # ENSO
    h += "<tr><td style=\"padding:20px 32px;\">"
    h += "<h2 style=\"font-size:15px;color:#1a1a1a;margin:0 0 10px;border-bottom:1px solid #eee;padding-bottom:8px;\">Status ENSO Atual</h2>"
    h += "<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"margin-bottom:8px;\"><tr>"
    h += "<td style=\"font-size:15px;font-weight:bold;color:#1a1a1a;\">" + status + "</td>"
    h += "<td style=\"text-align:right;font-size:13px;font-weight:bold;color:" + tend_cor + ";\">" + tend_seta + " " + tend + "</td>"
    h += "</tr></table>"
    h += "<p style=\"font-size:11px;color:#888;margin:0 0 4px;\">Indice ONI - anomalia Pacifico Equatorial</p>"
    h += enso_barra(oni)
    h += "<p style=\"font-size:12px;color:#555;margin:8px 0 0;\">ONI atual: <strong>" + str(oni) + "</strong> &nbsp;&#183;&nbsp; Projecao jun/26: <strong style=\"color:#854F0B;\">+0.8 a +1.2</strong> &nbsp;&#183;&nbsp; Prob. Super El Nino: <strong style=\"color:#A32D2D;\">65-70%</strong></p>"
    h += "<p style=\"font-size:11px;color:#666;margin:8px 0 0;line-height:1.6;\">" + enso_res + "</p>"
    h += "<p style=\"font-size:11px;color:#888;margin:10px 0 4px;\">Historico e projecao 13 meses:</p>"
    h += timeline_enso(oni)
    h += "</td></tr>"

    # Resumo
    h += "<tr><td style=\"padding:0 32px 20px;\">"
    h += "<h2 style=\"font-size:15px;color:#1a1a1a;margin:0 0 10px;border-bottom:1px solid #eee;padding-bottom:8px;\">Situacao Atual</h2>"
    h += "<p style=\"font-size:14px;color:#333;line-height:1.7;margin:0;\">" + resumo + "</p>"
    h += "</td></tr>"

    # Cards dados
    h += "<tr><td style=\"padding:0 32px 20px;\">"
    h += "<table width=\"100%\" cellpadding=\"0\" cellspacing=\"8\"><tr>"
    h += "<td width=\"48%\" style=\"background:#f8f8f8;border-radius:8px;padding:14px;\"><p style=\"font-size:11px;color:#888;margin:0 0 4px;text-transform:uppercase;\">Chuva Araxa (7 dias)</p><p style=\"font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;\">" + str(araxa.get("precip_7d_mm","?")) + " mm</p><p style=\"font-size:12px;color:#666;margin:4px 0 0;\">Max " + str(araxa.get("temp_max_semana","?")) + "C - Min " + str(araxa.get("temp_min_semana","?")) + "C</p></td>"
    h += "<td width=\"4%\"></td>"
    h += "<td width=\"48%\" style=\"background:#f8f8f8;border-radius:8px;padding:14px;\"><p style=\"font-size:11px;color:#888;margin:0 0 4px;text-transform:uppercase;\">Cambio USD/BRL</p><p style=\"font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;\">R$ " + str(usd) + "</p><p style=\"font-size:12px;color:#666;margin:4px 0 0;\">Fonte: Banco Central</p></td>"
    h += "</tr><tr><td colspan=\"3\" style=\"padding:4px 0;\"></td></tr><tr>"
    h += "<td width=\"48%\" style=\"background:#f8f8f8;border-radius:8px;padding:14px;\"><p style=\"font-size:11px;color:#888;margin:0 0 4px;text-transform:uppercase;\">Soja CBOT</p><p style=\"font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;\">USD " + str(soja.get("preco_usd_bushel","?")) + "/bu</p><p style=\"font-size:12px;color:#666;margin:4px 0 0;\">R$ " + str(soja.get("preco_brl_saca","?")) + "/sc</p></td>"
    h += "<td width=\"4%\"></td>"
    h += "<td width=\"48%\" style=\"background:#f8f8f8;border-radius:8px;padding:14px;\"><p style=\"font-size:11px;color:#888;margin:0 0 4px;text-transform:uppercase;\">Milho CBOT</p><p style=\"font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;\">USD " + str(milho.get("preco_usd_bushel","?")) + "/bu</p><p style=\"font-size:12px;color:#666;margin:4px 0 0;\">R$ " + str(milho.get("preco_brl_saca","?")) + "/sc</p></td>"
    h += "</tr></table></td></tr>"

    # Hedge
    h += "<tr><td style=\"padding:0 32px 20px;\">"
    h += "<h2 style=\"font-size:15px;color:#1a1a1a;margin:0 0 10px;border-bottom:1px solid #eee;padding-bottom:8px;\">Recomendacao de Hedge</h2>"
    h += "<table width=\"100%\" cellpadding=\"0\" cellspacing=\"8\"><tr>"
    h += "<td width=\"48%\" style=\"background:#EAF3DE;border-radius:8px;padding:14px;text-align:center;\"><p style=\"font-size:11px;color:#3B6D11;margin:0 0 4px;text-transform:uppercase;\">Soja safra 26/27</p><p style=\"font-size:28px;font-weight:bold;color:#27500A;margin:0;\">" + str(hs) + "%</p><p style=\"font-size:11px;color:#3B6D11;margin:4px 0 0;\">da producao a travar agora</p></td>"
    h += "<td width=\"4%\"></td>"
    h += "<td width=\"48%\" style=\"background:#EAF3DE;border-radius:8px;padding:14px;text-align:center;\"><p style=\"font-size:11px;color:#3B6D11;margin:0 0 4px;text-transform:uppercase;\">Milho 2a safra 27</p><p style=\"font-size:28px;font-weight:bold;color:#27500A;margin:0;\">" + str(hm) + "%</p><p style=\"font-size:11px;color:#3B6D11;margin:4px 0 0;\">da producao a travar agora</p></td>"
    h += "</tr></table>"
    h += "<p style=\"font-size:13px;color:#555;margin:12px 0 0;line-height:1.6;\">" + justif + "</p>"
    h += "</td></tr>"

    # Acoes
    h += "<tr><td style=\"padding:0 32px 20px;\">"
    h += "<h2 style=\"font-size:15px;color:#1a1a1a;margin:0 0 10px;border-bottom:1px solid #eee;padding-bottom:8px;\">O Que Fazer Agora</h2>"
    h += "<ul style=\"font-size:14px;color:#333;line-height:1.7;margin:0;padding-left:20px;\">" + acoes_li + "</ul>"
    h += "</td></tr>"

    # Proximo evento
    h += "<tr><td style=\"padding:0 32px 20px;\">"
    h += "<div style=\"background:#E6F1FB;border-radius:8px;padding:14px;\">"
    h += "<p style=\"font-size:11px;color:#185FA5;margin:0 0 4px;text-transform:uppercase;\">Proximo evento a monitorar</p>"
    h += "<p style=\"font-size:14px;color:#0C447C;margin:0;font-weight:bold;\">" + pe + "</p>"
    h += "<p style=\"font-size:12px;color:#185FA5;margin:4px 0 0;\">" + pd_ + "</p>"
    h += "</div></td></tr>"

    # Footer
    h += "<tr><td style=\"background:#f8f8f8;padding:16px 32px;border-top:1px solid #eee;\">"
    h += "<p style=\"font-size:11px;color:#999;margin:0;text-align:center;\">Agro Monitor - Triangulo Mineiro - Gerado automaticamente via Claude API + GitHub Actions</p>"
    h += "</td></tr>"

    h += "</table></td></tr></table></body></html>"
    return h

def enviar_email(assunto, html_body):
    if not RESEND_API_KEY:
        print("[AVISO] RESEND_API_KEY nao configurada. Email nao enviado.")
        return False
    if not EMAIL_DESTINO:
        print("[AVISO] EMAIL_DESTINO nao configurado.")
        return False
    payload = {
        "from": "Agro Monitor <onboarding@resend.dev>",
        "to": [EMAIL_DESTINO],
        "subject": assunto,
        "html": html_body
    }
    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": "Bearer " + RESEND_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=15
    )
    if response.status_code in (200, 201):
        print("Email enviado com sucesso para " + EMAIL_DESTINO)
        return True
    else:
        print("[ERRO] Falha ao enviar email: " + str(response.status_code) + " - " + response.text)
        return False

def main():
    print("\n" + "="*50)
    print("AGRO MONITOR - Envio de alertas")
    print("Data/hora: " + datetime.now().strftime("%d/%m/%Y %H:%M"))
    print("="*50 + "\n")
    with open(ANALISE_PATH, encoding="utf-8") as f:
        analise = json.load(f)
    with open(DATA_PATH, encoding="utf-8") as f:
        dados = json.load(f)
    deve_enviar = FORCAR_ENVIO or analise.get("alerta_imediato", False)
    tipo = "relatorio" if FORCAR_ENVIO and not analise.get("alerta_imediato") else "alerta"
    if deve_enviar:
        print("Preparando email (" + tipo + ")...")
        assunto = analise.get("assunto_email", "Agro Monitor - Atualizacao")
        if FORCAR_ENVIO and tipo == "relatorio":
            assunto = "Relatorio Semanal Agro Monitor - " + datetime.now().strftime("%d/%m/%Y")
        html = gerar_html(analise, dados, tipo)
        enviar_email(assunto, html)
    else:
        print("Sem mudancas relevantes. Nenhum alerta enviado.")
    print("\nProcesso de alerta concluido.\n")

if __name__ == "__main__":
    main()
