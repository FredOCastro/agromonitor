"""
send_alert.py
Envia alertas por email usando SendGrid.
"""

import json
import os
from datetime import datetime
import requests

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
EMAIL_DESTINO    = os.environ.get("EMAIL_DESTINO", "")
EMAIL_REMETENTE  = os.environ.get("EMAIL_REMETENTE", "")

BASE_DIR     = os.path.dirname(__file__)
ANALISE_PATH = os.path.join(BASE_DIR, "analise.json")
DATA_PATH    = os.path.join(BASE_DIR, "data_atual.json")

FORCAR_ENVIO = os.environ.get("FORCAR_ENVIO", "false").lower() == "true"

CORES = {
    "Crítico": {"header": "#A32D2D", "badge": "#FCEBEB", "badge_text": "#791F1F"},
    "Alto":    {"header": "#854F0B", "badge": "#FAEEDA", "badge_text": "#633806"},
    "Médio":   {"header": "#185FA5", "badge": "#E6F1FB", "badge_text": "#0C447C"},
    "Baixo":   {"header": "#27500A", "badge": "#EAF3DE", "badge_text": "#3B6D11"},
}

def gerar_html_alerta(analise, dados, tipo="alerta"):
    risco  = analise.get("nivel_risco", "Médio")
    cores  = CORES.get(risco, CORES["Médio"])
    titulo = "🚨 Alerta Imediato — Agro Monitor" if tipo == "alerta" else "📊 Relatório Semanal — Agro Monitor"
    subtitulo = analise.get("tipo_mudanca", "") if tipo == "alerta" else "Resumo semanal de clima, preços e hedge"
    acoes  = analise.get("acoes_recomendadas", [])
    acoes_html = "".join(f"<li style='margin-bottom:8px;'>{a}</li>" for a in acoes)
    enso   = dados.get("enso", {})
    precos = dados.get("precos", {})
    soja   = precos.get("soja_cbot", {})
    milho  = precos.get("milho_cbot", {})
    clima_araxa = dados.get("clima", {}).get("Araxá", {})

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:20px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;">
        <tr><td style="background:{cores['header']};padding:24px 32px;">
          <h1 style="color:#ffffff;margin:0;font-size:22px;">{titulo}</h1>
          <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;">{subtitulo}</p>
        </td></tr>
        <tr><td style="padding:24px 32px 0;">
          <span style="background:{cores['badge']};color:{cores['badge_text']};padding:6px 16px;border-radius:6px;font-size:13px;font-weight:bold;">
            RISCO: {risco.upper()}
          </span>
          <span style="padding-left:12px;font-size:12px;color:#666;">{analise.get('data_analise','')} · Triângulo Mineiro, MG</span>
        </td></tr>
        <tr><td style="padding:20px 32px;">
          <h2 style="font-size:16px;color:#1a1a1a;margin:0 0 12px;border-bottom:1px solid #eee;padding-bottom:8px;">Situação Atual</h2>
          <p style="font-size:14px;color:#333;line-height:1.7;margin:0;">
            {analise.get('resumo_executivo','').replace(chr(10),'<br><br>')}
          </p>
        </td></tr>
        <tr><td style="padding:0 32px 20px;">
          <table width="100%" cellpadding="0" cellspacing="8">
            <tr>
              <td width="48%" style="background:#f8f8f8;border-radius:8px;padding:16px;">
                <p style="font-size:11px;color:#888;margin:0 0 6px;text-transform:uppercase;">ENSO / El Niño</p>
                <p style="font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;">{enso.get('oni_atual','?')}</p>
                <p style="font-size:12px;color:#666;margin:4px 0 0;">{enso.get('status','?')} · {enso.get('tendencia','?')}</p>
              </td>
              <td width="4%"></td>
              <td width="48%" style="background:#f8f8f8;border-radius:8px;padding:16px;">
                <p style="font-size:11px;color:#888;margin:0 0 6px;text-transform:uppercase;">Chuva em Araxá (7 dias)</p>
                <p style="font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;">{clima_araxa.get('precip_7d_mm','?')} mm</p>
                <p style="font-size:12px;color:#666;margin:4px 0 0;">Máx {clima_araxa.get('temp_max_semana','?')}°C · Mín {clima_araxa.get('temp_min_semana','?')}°C</p>
              </td>
            </tr>
            <tr><td colspan="3" style="padding:4px 0;"></td></tr>
            <tr>
              <td width="48%" style="background:#f8f8f8;border-radius:8px;padding:16px;">
                <p style="font-size:11px;color:#888;margin:0 0 6px;text-transform:uppercase;">Soja CBOT</p>
                <p style="font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;">USD {soja.get('preco_usd_bushel','?')}/bu</p>
                <p style="font-size:12px;color:#666;margin:4px 0 0;">R$ {soja.get('preco_brl_saca','?')}/sc · câmbio {precos.get('cambio_usd_brl','?')}</p>
              </td>
              <td width="4%"></td>
              <td width="48%" style="background:#f8f8f8;border-radius:8px;padding:16px;">
                <p style="font-size:11px;color:#888;margin:0 0 6px;text-transform:uppercase;">Milho CBOT</p>
                <p style="font-size:20px;font-weight:bold;color:#1a1a1a;margin:0;">USD {milho.get('preco_usd_bushel','?')}/bu</p>
                <p style="font-size:12px;color:#666;margin:4px 0 0;">R$ {milho.get('preco_brl_saca','?')}/sc</p>
              </td>
            </tr>
          </table>
        </td></tr>
        <tr><td style="padding:0 32px 20px;">
          <h2 style="font-size:16px;color:#1a1a1a;margin:0 0 12px;border-bottom:1px solid #eee;padding-bottom:8px;">Recomendação de Hedge</h2>
          <table width="100%" cellpadding="0" cellspacing="8">
            <tr>
              <td width="48%" style="background:#EAF3DE;border-radius:8px;padding:16px;text-align:center;">
                <p style="font-size:11px;color:#3B6D11;margin:0 0 4px;text-transform:uppercase;">Soja safra 26/27</p>
                <p style="font-size:28px;font-weight:bold;color:#27500A;margin:0;">{analise.get('recomendacao_hedge_soja_pct','?')}%</p>
                <p style="font-size:11px;color:#3B6D11;margin:4px 0 0;">da produção a travar agora</p>
              </td>
              <td width="4%"></td>
              <td width="48%" style="background:#EAF3DE;border-radius:8px;padding:16px;text-align:center;">
                <p style="font-size:11px;color:#3B6D11;margin:0 0 4px;text-transform:uppercase;">Milho 2ª safra 27</p>
                <p style="font-size:28px;font-weight:bold;color:#27500A;margin:0;">{analise.get('recomendacao_hedge_milho_pct','?')}%</p>
                <p style="font-size:11px;color:#3B6D11;margin:4px 0 0;">da produção a travar agora</p>
              </td>
            </tr>
          </table>
          <p style="font-size:13px;color:#555;margin:12px 0 0;line-height:1.6;">{analise.get('justificativa_hedge','')}</p>
        </td></tr>
        <tr><td style="padding:0 32px 20px;">
          <h2 style="font-size:16px;color:#1a1a1a;margin:0 0 12px;border-bottom:1px solid #eee;padding-bottom:8px;">O Que Fazer Agora</h2>
          <ul style="font-size:14px;color:#333;line-height:1.7;margin:0;padding-left:20px;">{acoes_html}</ul>
        </td></tr>
        <tr><td style="padding:0 32px 20px;">
          <div style="background:#E6F1FB;border-radius:8px;padding:16px;">
            <p style="font-size:11px;color:#185FA5;margin:0 0 4px;text-transform:uppercase;">Próximo evento a monitorar</p>
            <p style="font-size:14px;color:#0C447C;margin:0;font-weight:bold;">{analise.get('proximo_evento_importante','')}</p>
            <p style="font-size:12px;color:#185FA5;margin:4px 0 0;">{analise.get('proximo_evento_data','')}</p>
          </div>
        </td></tr>
        <tr><td style="background:#f8f8f8;padding:16px 32px;border-top:1px solid #eee;">
          <p style="font-size:11px;color:#999;margin:0;text-align:center;">
            Agro Monitor · Triângulo Mineiro · Gerado automaticamente via Claude API + GitHub Actions
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

def enviar_email(assunto, html_body):
    if not SENDGRID_API_KEY:
        print("[AVISO] SENDGRID_API_KEY não configurada. Email não enviado.")
        return False
    if not EMAIL_DESTINO or not EMAIL_REMETENTE:
        print("[AVISO] EMAIL_DESTINO ou EMAIL_REMETENTE não configurados.")
        return False
    payload = {
        "personalizations": [{"to": [{"email": EMAIL_DESTINO}]}],
        "from": {"email": EMAIL_REMETENTE, "name": "Agro Monitor"},
        "subject": assunto,
        "content": [{"type": "text/html", "value": html_body}]
    }
    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
        json=payload, timeout=15
    )
    if response.status_code in (200, 202):
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
        assunto = analise.get("assunto_email", "Agro Monitor — Atualização")
        if FORCAR_ENVIO and tipo == "relatorio":
            assunto = f"📊 Relatório Semanal Agro Monitor — {datetime.now().strftime('%d/%m/%Y')}"
        html = gerar_html_alerta(analise, dados, tipo=tipo)
        enviar_email(assunto, html)
    else:
        print("Sem mudanças relevantes. Nenhum alerta enviado.")
    print("\nProcesso de alerta concluído.\n")

if __name__ == "__main__":
    main()
