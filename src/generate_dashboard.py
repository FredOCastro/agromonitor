"""
generate_dashboard.py
Gera o dashboard HTML atualizado a partir dos dados coletados e da análise do Claude.
"""

import json
import os
from datetime import datetime

BASE_DIR      = os.path.dirname(__file__)
ANALISE_PATH  = os.path.join(BASE_DIR, "analise.json")
DATA_PATH     = os.path.join(BASE_DIR, "data_atual.json")
DASHBOARD_DIR = os.path.join(BASE_DIR, "..", "dashboard")
OUTPUT_PATH   = os.path.join(DASHBOARD_DIR, "index.html")

os.makedirs(DASHBOARD_DIR, exist_ok=True)

def badge_risco(nivel):
    cores = {
        "Crítico": ("background:#FCEBEB;color:#791F1F", "🔴"),
        "Alto":    ("background:#FAEEDA;color:#633806", "🟠"),
        "Médio":   ("background:#E6F1FB;color:#0C447C", "🔵"),
        "Baixo":   ("background:#EAF3DE;color:#27500A", "🟢"),
    }
    estilo, icone = cores.get(nivel, cores["Médio"])
    return f'<span style="{estilo};padding:4px 12px;border-radius:6px;font-size:13px;font-weight:bold;">{icone} RISCO {nivel.upper()}</span>'

def gerar_dashboard(analise, dados):
    enso   = dados.get("enso", {})
    precos = dados.get("precos", {})
    clima  = dados.get("clima", {})
    soja   = precos.get("soja_cbot", {})
    milho  = precos.get("milho_cbot", {})
    safras = dados.get("safras", {})
    nivel  = analise.get("nivel_risco", "Médio")

    header_cores = {
        "Crítico": "#8B1A1A", "Alto": "#6B3A0A",
        "Médio": "#0D4A80", "Baixo": "#1A4A0A",
    }
    header_cor = header_cores.get(nivel, "#0D4A80")

    acoes_html = "".join(
        f'<li style="margin-bottom:10px;font-size:14px;">{a}</li>'
        for a in analise.get("acoes_recomendadas", [])
    )

    clima_cards = ""
    for cidade, c in clima.items():
        if "erro" not in c:
            alerta = ""
            if c.get("alerta_seca"):
                alerta = '<span style="color:#A32D2D;font-size:11px;"> ⚠ Seca</span>'
            elif c.get("alerta_excesso"):
                alerta = '<span style="color:#185FA5;font-size:11px;"> ⚠ Excesso</span>'
            clima_cards += f"""
            <div style="flex:1;min-width:120px;background:#f9f9f9;border-radius:8px;padding:12px;">
              <div style="font-size:11px;color:#888;margin-bottom:4px;">{cidade}</div>
              <div style="font-size:18px;font-weight:bold;color:#1a1a1a;">{c.get('precip_7d_mm','?')} mm{alerta}</div>
              <div style="font-size:11px;color:#666;">7 dias · {c.get('temp_max_semana','?')}°C / {c.get('temp_min_semana','?')}°C</div>
            </div>"""

    safras_soja_html = ""
    for pais, info in safras.get("soja_mundial_mt", {}).items():
        var = info['variacao_pct']
        cor = "#27500A" if var > 0 else "#A32D2D"
        sinal = "▲" if var > 0 else "▼"
        safras_soja_html += f"""
        <tr>
          <td style="padding:8px 0;font-size:13px;">{pais}</td>
          <td style="padding:8px 0;font-size:13px;text-align:right;">{info['producao']} Mt</td>
          <td style="padding:8px 0;font-size:13px;text-align:right;color:{cor};">{sinal} {abs(var)}%</td>
        </tr>"""

    safras_milho_html = ""
    for pais, info in safras.get("milho_mundial_mt", {}).items():
        var = info['variacao_pct']
        cor = "#27500A" if var > 0 else "#A32D2D"
        sinal = "▲" if var > 0 else "▼"
        safras_milho_html += f"""
        <tr>
          <td style="padding:8px 0;font-size:13px;">{pais}</td>
          <td style="padding:8px 0;font-size:13px;text-align:right;">{info['producao']} Mt</td>
          <td style="padding:8px 0;font-size:13px;text-align:right;color:{cor};">{sinal} {abs(var)}%</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agro Monitor — Triângulo Mineiro</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f0f0; color: #1a1a1a; }}
    .header {{ background: {header_cor}; color: white; padding: 24px 32px; }}
    .header h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
    .header p {{ font-size: 13px; opacity: 0.8; }}
    .container {{ max-width: 900px; margin: 24px auto; padding: 0 16px; }}
    .card {{ background: white; border-radius: 12px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.07); }}
    .card h2 {{ font-size: 15px; font-weight: 600; margin-bottom: 14px; color: #333; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .metric {{ background: #f8f8f8; border-radius: 8px; padding: 14px; }}
    .metric-label {{ font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 6px; }}
    .metric-value {{ font-size: 24px; font-weight: 700; color: #1a1a1a; }}
    .metric-sub {{ font-size: 12px; color: #666; margin-top: 4px; }}
    .hedge-box {{ background: #EAF3DE; border-radius: 8px; padding: 16px; text-align: center; }}
    .hedge-pct {{ font-size: 36px; font-weight: 700; color: #27500A; }}
    .hedge-label {{ font-size: 11px; color: #3B6D11; text-transform: uppercase; margin-bottom: 4px; }}
    .hedge-sub {{ font-size: 11px; color: #3B6D11; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td {{ border-bottom: 1px solid #f0f0f0; }}
    tr:last-child td {{ border-bottom: none; }}
    .update-bar {{ text-align: center; font-size: 11px; color: #999; margin-bottom: 20px; }}
    @media (max-width: 600px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<div class="header">
  <h1>Agro Monitor — Triângulo Mineiro</h1>
  <p>Araxá · Ibiá · Perdizes · Tapira &nbsp;|&nbsp; Soja · Milho · Laranja</p>
</div>
<div class="container">
  <div class="update-bar">
    Última atualização: {analise.get('data_analise', '')} &nbsp;·&nbsp; {badge_risco(nivel)}
  </div>
  <div class="card">
    <h2>Situação Atual</h2>
    <p style="font-size:14px;line-height:1.8;color:#333;">
      {analise.get('resumo_executivo','').replace(chr(10), '<br><br>')}
    </p>
  </div>
  <div class="card">
    <h2>ENSO & Preços</h2>
    <div class="grid-2">
      <div class="metric">
        <div class="metric-label">Índice ONI (El Niño/La Niña)</div>
        <div class="metric-value">{enso.get('oni_atual','?')}</div>
        <div class="metric-sub">{enso.get('status','?')} · {enso.get('tendencia','?')}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Câmbio USD/BRL</div>
        <div class="metric-value">R$ {precos.get('cambio_usd_brl','?')}</div>
        <div class="metric-sub">Fonte: Banco Central do Brasil</div>
      </div>
      <div class="metric">
        <div class="metric-label">Soja CBOT</div>
        <div class="metric-value">USD {soja.get('preco_usd_bushel','?')}/bu</div>
        <div class="metric-sub">R$ {soja.get('preco_brl_saca','?')}/saca</div>
      </div>
      <div class="metric">
        <div class="metric-label">Milho CBOT</div>
        <div class="metric-value">USD {milho.get('preco_usd_bushel','?')}/bu</div>
        <div class="metric-sub">R$ {milho.get('preco_brl_saca','?')}/saca</div>
      </div>
    </div>
  </div>
  <div class="card">
    <h2>Clima Regional — Próximos 7 Dias</h2>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">{clima_cards}</div>
  </div>
  <div class="card">
    <h2>Recomendação de Hedge</h2>
    <div class="grid-2">
      <div class="hedge-box">
        <div class="hedge-label">Soja — safra 26/27</div>
        <div class="hedge-pct">{analise.get('recomendacao_hedge_soja_pct','?')}%</div>
        <div class="hedge-sub">da produção a travar agora</div>
      </div>
      <div class="hedge-box">
        <div class="hedge-label">Milho — 2ª safra 27</div>
        <div class="hedge-pct">{analise.get('recomendacao_hedge_milho_pct','?')}%</div>
        <div class="hedge-sub">da produção a travar agora</div>
      </div>
    </div>
    <p style="font-size:13px;color:#555;margin-top:14px;line-height:1.6;">
      {analise.get('justificativa_hedge','')}
    </p>
  </div>
  <div class="card">
    <h2>O Que Fazer Agora</h2>
    <ul style="padding-left:20px;">{acoes_html}</ul>
  </div>
  <div class="grid-2" style="margin-bottom:16px;">
    <div class="card" style="margin-bottom:0;">
      <h2>Soja Global (Mi ton)</h2>
      <table>
        <thead><tr>
          <th style="text-align:left;font-size:11px;color:#888;padding-bottom:6px;">País</th>
          <th style="text-align:right;font-size:11px;color:#888;padding-bottom:6px;">Prod.</th>
          <th style="text-align:right;font-size:11px;color:#888;padding-bottom:6px;">Var.</th>
        </tr></thead>
        <tbody>{safras_soja_html}</tbody>
      </table>
    </div>
    <div class="card" style="margin-bottom:0;">
      <h2>Milho Global (Mi ton)</h2>
      <table>
        <thead><tr>
          <th style="text-align:left;font-size:11px;color:#888;padding-bottom:6px;">País</th>
          <th style="text-align:right;font-size:11px;color:#888;padding-bottom:6px;">Prod.</th>
          <th style="text-align:right;font-size:11px;color:#888;padding-bottom:6px;">Var.</th>
        </tr></thead>
        <tbody>{safras_milho_html}</tbody>
      </table>
    </div>
  </div>
  <div class="card" style="background:#E6F1FB;">
    <h2 style="color:#0C447C;">Próximo Evento a Monitorar</h2>
    <p style="font-size:15px;font-weight:600;color:#042C53;">{analise.get('proximo_evento_importante','')}</p>
    <p style="font-size:13px;color:#185FA5;margin-top:4px;">{analise.get('proximo_evento_data','')}</p>
  </div>
  <p style="text-align:center;font-size:11px;color:#aaa;margin-top:8px;padding-bottom:24px;">
    Gerado automaticamente · Claude API + GitHub Actions · {analise.get('data_analise','')}
  </p>
</div>
</body>
</html>"""

def main():
    print("\nGerando dashboard HTML...")
    with open(ANALISE_PATH, encoding="utf-8") as f:
        analise = json.load(f)
    with open(DATA_PATH, encoding="utf-8") as f:
        dados = json.load(f)
    html = gerar_dashboard(analise, dados)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard salvo em: {OUTPUT_PATH}")
    print("Dashboard gerado com sucesso!\n")

if __name__ == "__main__":
    main()
