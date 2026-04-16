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
    n = nivel.replace("é","e").replace("í","i").replace("ó","o").replace("ê","e").replace("í","i")
    return CORES.get(n, CORES["Medio"])

def enso_barra_html(oni):
    pos = max(2, min(96, (oni + 2.0) / 4.5 * 100))
    return (
        "<table width='100%' cellpadding='0' cellspacing='0' style='margin:10px 0 4px;'>"
        "<tr>"
        "<td width='20%' style='background:#B5D4F4;padding:8px 4px;text-align:center;font-size:10px;font-weight:bold;color:#0C447C;border-radius:6px 0 0 6px;'>La Nina<br>Forte</td>"
        "<td width='20%' style='background:#E6F1FB;padding:8px 4px;text-align:center;font-size:10px;font-weight:bold;color:#185FA5;'>La Nina<br>Fraca</td>"
        "<td width='20%' style='background:#f0f0f0;padding:8px 4px;text-align:center;font-size:10px;font-weight:bold;color:#666;'>Neutro</td>"
        "<td width='20%' style='background:#FAEEDA;padding:8px 4px;text-align:center;font-size:10px;font-weight:bold;color:#854F0B;'>El Nino<br>Fraco</td>"
        "<td width='20%' style='background:#F5C4B3;padding:8px 4px;text-align:center;font-size:10px;font-weight:bold;color:#993C1D;border-radius:0 6px 6px 0;'>El Nino<br>Forte</td>"
        "</tr></table>"
        "<table width='100%' cellpadding='0' cellspacing='0' style='margin-bottom:4px;'>"
        "<tr>"
        "<td width='" + str(round(pos)) + "%' style='text-align:right;'>"
        "<span style='display:inline-block;background:#1a1a1a;color:white;font-size:11px;font-weight:bold;padding:3px 8px;border-radius:4px;'>ONI: " + str(oni) + "</span>"
        "</td><td></td></tr></table>"
        "<table width='100%' cellpadding='0' cellspacing='0'><tr>"
        "<td style='font-size:10px;color:#999;'>-2.0</td>"
        "<td style='text-align:center;font-size:10px;color:#999;'>-0.5</td>"
        "<td style='text-align:center;font-size:10px;color:#999;'>0</td>"
        "<td style='text-align:center;font-size:10px;color:#999;'>+0.5</td>"
        "<td style='text-align:right;font-size:10px;color:#999;'>+2.5</td>"
        "</tr></table>"
    )

def timeline_enso_html(oni_atual):
    meses = [
        ("Jul/25", -1.2, "ln"), ("Ago/25", -0.9, "ln"), ("Set/25", -0.6, "ln"),
        ("Out/25", -0.3, "ne"), ("Nov/25",  0.0, "ne"), ("Dez/25",  0.2, "ne"),
        ("Jan/26",  0.3, "ne"), ("Fev/26",  0.4, "ne"), ("Mar/26",  0.4, "ne"),
        ("Abr/26", oni_atual, "cur"),
        ("Mai/26",  0.7, "el"), ("Jun/26",  1.0, "el"), ("Jul/26",  1.3, "el"),
    ]
    bgs  = {"ln":"#E6F1FB","ne":"#f8f8f8","el":"#FAEEDA","cur":"#fff3cd"}
    txts = {"ln":"#185FA5","ne":"#666","el":"#854F0B","cur":"#A32D2D"}
    cells = ""
    for mes, val, tipo in meses:
        brd = "border:2px solid #E24B4A;" if tipo == "cur" else ""
        proj = "*" if tipo == "el" else ""
        cells += (
            "<td style='background:" + bgs[tipo] + ";" + brd + "padding:6px 2px;"
            "text-align:center;border-right:1px solid #eee;'>"
            "<span style='font-size:10px;font-weight:bold;color:" + txts[tipo] + ";'>" + str(val) + proj + "</span>"
            "<br><span style='font-size:9px;color:#999;'>" + mes + "</span></td>"
        )
    return (
        "<table width='100%' cellpadding='0' cellspacing='0' "
        "style='border:1px solid #eee;border-radius:6px;overflow:hidden;margin:10px 0;'>"
        "<tr>" + cells + "</tr></table>"
        "<p style='font-size:10px;color:#aaa;margin:0;'>"
        "* Projecao NOAA/INPE · Fundo laranja = El Nino previsto · La Nina encerrada mar/2026</p>"
    )

def gerar_html(analise, dados, tipo):
    risco  = analise.get("nivel_risco", "Medio")
    cores  = get_cores(risco)
    titulo = "Alerta Imediato - Agro Monitor" if tipo == "alerta" else "Relatorio Semanal - Agro Monitor"
    subtit = analise.get("tipo_mudanca","") if tipo == "alerta" else "Resumo semanal de clima, precos e hedge"
    acoes  = analise.get("acoes_recomendadas", [])
    acoes_li = "".join("<li style='margin-bottom:8px;'>" + a + "</li>" for a in acoes)
    enso   = dados.get("enso", {})
    precos = dados.get("precos", {})
    soja   = precos.get("soja_cbot", {})
    milho  = precos.get("milho_cbot", {})
    araxa  = dados.get("clima", {}).get("Araxa", dados.get("clima", {}).get("Araxá", {}))
    oni    = enso.get("oni_atual", 0.4)
    status = enso.get("status", "Neutro")
    tend   = enso.get("tendencia", "subindo")
    tend_cor = "#A32D2D" if tend == "subindo" else "#185FA5"
    tend_seta = "▲" if tend == "subindo" else "▼"
    resumo = analise.get("resumo_executivo","").replace("\n","<br><br>")
    enso_res = analise.get("enso_resumo","")
    justif = analise.get("justificativa_hedge","")
    hs = analise.get("recomendacao_hedge_soja_pct","?")
    hm = analise.get("recomendacao_hedge_milho_pct","?")
    pe = analise.get("proximo_evento_importante","")
    pd = analise.get("proximo_evento_data","")
    dt = analise.get("data_analise","")
    usd = precos.get("cambio_usd_brl","?")

    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1.0'></head>"
        "<body style='font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0;'>"
        "<table width='100%' cellpadding='0' cellspacing='0' style='background:#f4f4f4;padding:20px 0;'>"
        "<tr><td align='center'>"
        "<table width='600' cellpadding='0' cellspacing='0' style='background:#ffffff;border-radius:12px;overflow:hidden;'>"

        # Header
        "<tr><td style='background:" + cores["header"] + ";padding:24px 32px;'>"
        "<h1 style='color:#fff;margin:0;font-size:22px;'>" + titulo + "</h1>"
        "<p style='color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;'>" + subtit + "</p>"
        "</td></tr>"

        # Badge risco
        "<tr><td style='padding:20px 32px 0;'>"
        "<span style='background:" + cores["badge"] + ";color:" + cores["badge_text"] + ";"
        "padding:6px 16px;border-radius:6px;font-size:13px;font-weight:bold;'>RISCO: " + risco.upper() + "</span>"
        "<span style='padding-left:12px;font-size:12px;color:#666;'>" + dt + " · Triangulo Mineiro, MG</span>"
        "</td></tr>"

        # ENSO
        "<tr><td style='padding:20px 32px;'>"
        "<h2 style='font-size:15px;color:#1a1a1a;margin:0 0 10px;border-bottom:1px solid #eee;padding-bottom:8px;'>Status ENSO Atual</h2>"
        "<table width='100%' cellpadding='0' cellspacing='0' style='margin-bottom:8px;'><tr>"
        "<td style='font-size:15px;font-weight:bold;color:#1a1a1a;'>" + status + "</td>"
        "<td style='text-align:right;font-size:13px;font-weight:bold;color:" + tend_cor + ";'>" + tend_seta + " " + tend + "</td>"
        "</tr></table>"
        "<p style='font-size:11px;color:#888;margin:0 0 4px;'>Indice ONI — anomalia Pacifico Equatorial</p>"
        + enso_barra_html(oni) +
        "<p style='font-size:12px;color:#555;margin:8px 0 0;'>"
        "ONI atual: <strong>" + str(oni) + "</strong> &nbsp;·&nbsp; "
        "Projecao jun/26: <strong style='color:#854F0B;'>+0.8 a +1.2</strong> &nbsp;·&nbsp; "
        "Prob. Super El Nino: <strong style='color:#A32D2D;'>65-70%</strong></p>"
        "<p style='font-size:11px;color:#666;margin:8px 0 0;line-height:1.6;'>" + enso_res + "</p>"
        "<p style='font-size:11px;color:#888;margin:10px 0 4px;'>Historico e projecao 13 meses:</p>"
        + timeline_enso_html(oni) +
        "</td></tr>"

        # Resumo
        "<tr><td style='padding:0 32px 20px;'>"
        "<h2 style='font-size:15px;color:#1a1a1a;margin:0 0 10px;border-bottom:1px solid #eee;padding-bottom:8px;'>Situacao Atual</h2>"
        "<p style='font-size:14px;color:#333;line-height:1.7;margin:0;'>" + resumo + "</p>"
        "</td></tr>"

        # Dados
        "<tr><td style='padding:0 32px 20px;'>"
        "<table width='100%' cellpadding='0' cellspacing='8'><tr>"
        "<td width='48%' style='background:#f8f8f8;border-radius:8px;padding:14px;'>"
        "<p style='font-size:11px;color:#888;margin:0 0 4px;text-transform:uppercase;'>Chuva Araxa (7 dias)</p>"
        "<p style='font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;'>" + str(araxa.get("precip_7d_mm","?")) + " mm</p>"
        "<p style='font-size:12px;color:#666;margin:4px 0 0;'>Max " + str(araxa.get("temp_max_semana","?")) + "C · Min " + str(araxa.get("temp_min_semana","?")) + "C</p>"
        "</td><td width='4%'></td>"
        "<td width='48%' style='background:#f8f8f8;border-radius:8px;padding:14px;'>"
        "<p style='font-size:11px;color:#888;margin:0 0 4px;text-transform:uppercase;'>Cambio USD/BRL</p>"
        "<p style='font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;'>R$ " + str(usd) + "</p>"
        "<p style='font-size:12px;color:#666;margin:4px 0 0;'>Fonte: Banco Central</p>"
        "</td></tr><tr><td colspan='3' style='padding:4px 0;'></td></tr><tr>"
        "<td width='48%' style='background:#f8f8f8;border-radius:8px;padding:14px;'>"
        "<p style='font-size:11px;color:#888;margin:0 0 4px;text-transform:uppercase;'>Soja CBOT</p>"
        "<p style='font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;'>USD " + str(soja.get("preco_usd_bushel","?")) + "/bu</p>"
        "<p style='font-size:12px;color:#666;margin:4px 0 0;'>R$ " + str(soja.get("preco_brl_saca","?")) + "/sc</p>"
        "</td><td width='4%'></td>"
        "<td width='48%' style='background:#f8f8f8;border-radius:8px;padding:14px;'>"
        "<p style='font-size:11px;color:#888;margin:0 0 4px;text-transform:uppercase;'>Milho CBOT</p>"
        "<p style='font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;'>USD " + str(milho.get("preco_usd_bushel","?")) + "/bu</p>"
        "<p style='font-size:12px;color:#666;margin:4px 0 0;'>R$ " + str(milho.get("preco_brl_saca","?")) + "/sc</p>"
        "</td></tr></table></td></tr>"

        # Hedge
        "<tr><td style='padding:0 32px 20px;'>"
        "<h2 style='font-size:15px;color:#1a1a1a;margin:0 0 10px;border-bottom:1px solid #eee;padding-bottom:8px;'>Recomendacao de Hedge</h2>"
        "<table width='100%' cellpadding='0' cellspacing='8'><tr>"
        "<td width='48%' style='background:#EAF3DE;border-radius:8px;padding:14px;text-align:center;'>"
        "<p style='font-size:11px;color:#3B6D11;margin:0 0 4px;text-transform:uppercase;'>Soja safra 26/27</p>"
        "<p style='font-size:28px;font-weight:bold;color:#27500A;margin:0;'>" + str(hs) + "%</p>"
        "<p style='font-size:11px;color:#3B6D11;margin:4px 0 0;'>da producao a travar agora</p>"
        "</td><td width='4%'></td>"
        "<td width='48%' style='background:#EAF3DE;border-radius:8px;padding:14px;text-align:center;'>"
        "<p style='font-size:11px;color:#3B6D11;margin:0 0 4px;text-transform:uppercase;'>Milho 2a safra 27</p>"
        "<p style='font-size:28px;font-weight:bold;color:#27500A;margin:0;'>" + str(hm) + "%</p>"
        "<p style='font-size:11px;color:#3B6D11;margin:4px 0 0;'>da producao a travar agora</p>"
        "</td></tr></table>"
        "<p style='font-size:13px;color:#555;margin:12px 0 0;line-height:1.6;'>" + justif + "</p>"
        "</td></tr>"

        # Acoes
        "<tr><td style='padding:0 32px 20px;'>"
        "<h2 style='font-size:15px;color:#1a1a1a;margin:0 0 10px;border-bottom:1px solid #eee;padding-bottom:8px;'>O Que Fazer Agora</h2>"
        "<ul style='font-size:14px;color:#333;line-height:1.7;margin:0;padding-left:20px;'>" + acoes_li + "</ul>"
        "</td></tr>"

        # Proximo evento
        "<tr><td style='padding:0 32px 20px;'>"
        "<div style='background:#E6F1FB;border-radius:8px;padding:14px;'>"
        "<p style='font-size:11px;color:#185FA5;margin:0 0 4px;text-transform:uppercase;'>Proximo evento a monitorar</p>"
        "<p style='font-size:14px;color:#0C447C;margin:0;font-weight:bold;'>" + pe + "</p>"
        "<p style='font-size:12px;color:#185FA5;margin:4px 0 0;'>" + pd + "</p>"
        "</div></td></tr>"

        # Footer
        "<tr><td style='background:#f8f8f8;padding:16px 32px;border-top:1px solid #eee;'>"
        "<p style='font-size:11px;color:#999;margin:0;text-align:center;'>"
        "Agro Monitor · Triangulo Mineiro · Gerado automaticamente via Claude API + GitHub Actions"
        "</p></td></tr>"

        "</table></td></tr></table></body></html>"
    )

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
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        json=payload, timeout=15
    )
    if response.status_code in (200, 201):
        print(f"Email enviado com sucesso para {EMAIL_DESTINO}")
        return True
    else:
        print(f"[ERRO] Falha ao enviar email: {response.status_code} — {response.text}")
        return False

def main():
    print("\n" + "="*50)
    print("AGRO MONITOR — Envio de alertas")
    print(f"Data/hora: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*50 + "\n")
    with open(ANALISE_PATH, encoding="utf-8") as f:
        analise = json.load(f)
    with open(DATA_PATH, encoding="utf-8") as f:
        dados = json.load(f)
    deve_enviar = FORCAR_ENVIO or analise.get("alerta_imediato", False)
    tipo = "relatorio" if FORCAR_ENVIO and not analise.get("alerta_imediato") else "alerta"
    if deve_enviar:
        print(f"Preparando email ({tipo})...")
        assunto = analise.get("assunto_email", "Agro Monitor — Atualizacao")
        if FORCAR_ENVIO and tipo == "relatorio":
            assunto = f"Relatorio Semanal Agro Monitor — {datetime.now().strftime('%d/%m/%Y')}"
        html = gerar_html(analise, dados, tipo)
        enviar_email(assunto, html)
    else:
        print("Sem mudancas relevantes. Nenhum alerta enviado.")
    print("\nProcesso de alerta concluido.\n")

if __name__ == "__main__":
    main()
