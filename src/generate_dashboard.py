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
          <td sty
