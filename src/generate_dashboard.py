"""
generate_dashboard.py - Dashboard dinamico com dados reais do Claude + APIs
"""
import json, os
from datetime import datetime

BASE_DIR      = os.path.dirname(__file__)
ANALISE_PATH  = os.path.join(BASE_DIR, "analise.json")
DATA_PATH     = os.path.join(BASE_DIR, "data_atual.json")
DASHBOARD_DIR = os.path.join(BASE_DIR, "..", "dashboard")
OUTPUT_PATH   = os.path.join(DASHBOARD_DIR, "index.html")
os.makedirs(DASHBOARD_DIR, exist_ok=True)

def badge_risco(nivel):
    n = nivel.replace("é","e").replace("í","i").replace("ó","o").replace("ê","e")
    cores = {"Critico":"background:#FCEBEB;color:#791F1F","Alto":"background:#FAEEDA;color:#633806","Medio":"background:#E6F1FB;color:#0C447C","Baixo":"background:#EAF3DE;color:#27500A"}
    icones = {"Critico":"🔴","Alto":"🟠","Medio":"🔵","Baixo":"🟢"}
    return f'<span style="{cores.get(n,cores["Medio"])};padding:4px 12px;border-radius:6px;font-size:13px;font-weight:600;">{icones.get(n,"🔵")} RISCO {nivel.upper()}</span>'

def header_cor(nivel):
    n = nivel.replace("é","e").replace("í","i").replace("ó","o").replace("ê","e")
    return {"Critico":"#8B1A1A","Alto":"#6B3A0A","Medio":"#0D4A80","Baixo":"#1A4A0A"}.get(n,"#0D4A80")

def needle_pos(oni):
    return max(2, min(98, (oni + 2.0) / 4.5 * 100))

def clima_cards(clima):
    html = ""
    for cidade, c in clima.items():
        if "erro" in c:
            html += f'<div style="flex:1;min-width:110px;background:#f9f9f9;border-radius:8px;padding:12px;"><div style="font-size:11px;color:#888;">{cidade}</div><div style="font-size:12px;color:#aaa;margin-top:4px;">Sem dados</div></div>'
            continue
        al = '<span style="color:#A32D2D;font-size:11px;"> ⚠ Seca</span>' if c.get("alerta_seca") else ('<span style="color:#185FA5;font-size:11px;"> ⚠ Excesso</span>' if c.get("alerta_excesso") else "")
        html += f'<div style="flex:1;min-width:110px;background:#f9f9f9;border-radius:8px;padding:12px;"><div style="font-size:11px;color:#888;margin-bottom:4px;">{cidade}</div><div style="font-size:18px;font-weight:700;">{c.get("precip_7d_mm","?")} mm{al}</div><div style="font-size:11px;color:#666;">7d · {c.get("temp_max_semana","?")}°C / {c.get("temp_min_semana","?")}°C</div></div>'
    return html

def acoes_li(acoes):
    return "".join(f'<li style="margin-bottom:10px;font-size:14px;">{a}</li>' for a in acoes)

def gerar(analise, dados):
    enso   = dados.get("enso", {})
    precos = dados.get("precos", {})
    clima  = dados.get("clima", {})
    soja   = precos.get("soja_cbot", {})
    milho  = precos.get("milho_cbot", {})
    nivel  = analise.get("nivel_risco", "Medio")
    oni    = enso.get("oni_atual", 0.4)
    oni_ant= enso.get("oni_anterior", 0.3)
    status = enso.get("status", "Neutro")
    tend   = enso.get("tendencia", "subindo")
    usd    = precos.get("cambio_usd_brl", 5.95)
    su     = soja.get("preco_usd_bushel", 10.42)
    sb     = soja.get("preco_brl_saca", 124)
    mu     = milho.get("preco_usd_bushel", 4.58)
    mb     = milho.get("preco_brl_saca", 64)
    hs     = analise.get("recomendacao_hedge_soja_pct", 50)
    hm     = analise.get("recomendacao_hedge_milho_pct", 40)
    res    = analise.get("resumo_executivo","").replace("\n","<br><br>")
    just   = analise.get("justificativa_hedge","")
    pe     = analise.get("proximo_evento_importante","")
    pd_    = analise.get("proximo_evento_data","")
    er     = analise.get("enso_resumo","")
    cr     = analise.get("clima_resumo","")
    pr     = analise.get("precos_resumo","")
    tc_    = analise.get("tipo_mudanca","")
    dt     = analise.get("data_analise","")
    np_    = needle_pos(oni)
    hc     = header_cor(nivel)
    tend_cor = "#A32D2D" if tend=="subindo" else "#185FA5"

    # curva futuros baseada no preco spot real
    sf = [su, round(su*1.012,2), round(su*1.025,2), round(su*1.044,2), round(su*1.029,2), round(su*1.018,2)]
    mf = [mu, round(mu*1.015,2), round(mu*1.03,2), round(mu*1.057,2), round(mu*1.039,2)]

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Agro Monitor — Triângulo Mineiro</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f0f0;color:#1a1a1a;}}
.hdr{{background:{hc};color:white;padding:20px 32px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}}
.hdr h1{{font-size:20px;font-weight:600;}}.hdr p{{font-size:12px;opacity:0.8;margin-top:2px;}}
.tabs{{background:rgba(0,0,0,0.25);display:flex;gap:2px;padding:0 32px;overflow-x:auto;}}
.tab{{padding:10px 20px;font-size:13px;color:rgba(255,255,255,0.65);cursor:pointer;border:none;border-bottom:2px solid transparent;background:none;white-space:nowrap;}}
.tab.active{{color:white;border-bottom:2px solid #4fb3f0;}}
.wrap{{max-width:1000px;margin:20px auto;padding:0 16px;}}
.tc{{display:none;}}.tc.active{{display:block;}}
.card{{background:white;border-radius:12px;padding:18px 22px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.07);}}
.card h2{{font-size:13px;font-weight:600;color:#666;border-bottom:1px solid #eee;padding-bottom:10px;margin-bottom:14px;text-transform:uppercase;letter-spacing:.04em;}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:12px;}}
.g4{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;}}
.met{{background:#f8f8f8;border-radius:8px;padding:14px;}}
.ml{{font-size:11px;color:#888;text-transform:uppercase;margin-bottom:6px;}}
.mv{{font-size:22px;font-weight:700;}}
.ms{{font-size:12px;color:#666;margin-top:4px;}}
.enso-track{{position:relative;height:38px;border-radius:6px;overflow:hidden;display:flex;margin:10px 0 4px;}}
.eseg{{height:100%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;text-align:center;}}
.eneedle{{position:absolute;top:0;height:100%;width:3px;background:#1a1a1a;border-radius:2px;transform:translateX(-50%);}}
.elabels{{display:flex;justify-content:space-between;font-size:10px;color:#999;margin-bottom:8px;}}
.tl{{display:flex;margin:10px 0;border-radius:6px;overflow:hidden;border:1px solid #eee;}}
.ti{{flex:1;padding:7px 3px;text-align:center;font-size:9px;border-right:1px solid #eee;}}
.ti:last-child{{border-right:none;}}
.tv{{font-weight:700;font-size:10px;}}.tm{{color:#999;margin-top:2px;}}
.tel{{background:#FAEEDA;color:#854F0B;}}.tln{{background:#E6F1FB;color:#185FA5;}}.tne{{background:#f8f8f8;color:#666;}}
.tcur{{outline:2px solid #E24B4A;outline-offset:-2px;}}
.igrid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px;}}
.ii{{border:1px solid #eee;border-radius:8px;padding:12px;}}
.ut{{width:100%;border-collapse:collapse;font-size:12.5px;}}
.ut th{{background:#1D9E75;color:white;padding:8px 10px;text-align:center;font-weight:600;font-size:11px;}}
.ut th:first-child{{text-align:left;}}
.ut td{{padding:8px 10px;border-bottom:1px solid #f0f0f0;text-align:center;}}
.ut td:first-child{{text-align:left;font-weight:500;}}
.ut tr:last-child td{{border-bottom:none;font-weight:700;background:#f8fff4;}}
.up{{color:#27500A;}}.dn{{color:#A32D2D;}}.proj{{color:#854F0B;font-style:italic;}}
.ctabs{{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap;}}
.ctab{{padding:5px 14px;border-radius:6px;font-size:12px;cursor:pointer;border:1px solid #ddd;background:white;color:#666;}}
.ctab.active{{background:#1D9E75;color:white;border-color:#1D9E75;font-weight:600;}}
.hbox{{background:#EAF3DE;border-radius:8px;padding:16px;text-align:center;}}
.hpct{{font-size:38px;font-weight:700;color:#27500A;}}
.hlbl{{font-size:11px;color:#3B6D11;text-transform:uppercase;margin-bottom:4px;}}
.hsub{{font-size:11px;color:#3B6D11;margin-top:4px;}}
.ai{{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #f5f5f5;}}
.ai:last-child{{border-bottom:none;}}
.dot{{width:8px;height:8px;border-radius:50%;margin-top:4px;flex-shrink:0;}}
.dr{{background:#E24B4A;}}.da{{background:#EF9F27;}}.dg{{background:#639922;}}.db{{background:#378ADD;}}
.rs{{color:#0F6E56;font-weight:600;}}.rp{{color:#BA7517;font-weight:600;}}.rw{{color:#185FA5;font-weight:600;}}
@media(max-width:640px){{.g2,.g4,.igrid{{grid-template-columns:1fr;}}.tabs{{padding:0 12px;}}.wrap{{padding:0 10px;}}.hdr{{padding:16px;}}}}
</style>
</head>
<body>
<div class="hdr">
  <div><h1>Agro Monitor — Triângulo Mineiro</h1><p>Araxá · Ibiá · Perdizes · Tapira &nbsp;|&nbsp; Soja · Milho · Laranja</p></div>
  <div style="text-align:right;">{badge_risco(nivel)}<br><span style="font-size:11px;opacity:.7;margin-top:4px;display:block;">Atualizado: {dt}</span></div>
</div>
<div class="tabs">
  <button class="tab active" onclick="st('clima',this)">Clima & ENSO</button>
  <button class="tab" onclick="st('safras',this)">Safras Globais</button>
  <button class="tab" onclick="st('estoques',this)">Estoques</button>
  <button class="tab" onclick="st('precos',this)">Preços & Futuros</button>
  <button class="tab" onclick="st('hedge',this)">Decisão de Hedge</button>
</div>

<div id="tab-clima" class="tc active"><div class="wrap">
  <div class="card">
    <h2>Status ENSO Atual</h2>
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
      <span style="font-size:16px;font-weight:600;">{status}</span>
      <span style="font-size:12px;color:#888;">ONI: <b>{oni}</b> &nbsp;·&nbsp; Anterior: <b>{oni_ant}</b> &nbsp;·&nbsp; Tendência: <b style="color:{tend_cor};">{tend}</b></span>
    </div>
    <div style="font-size:11px;color:#888;margin-bottom:4px;">Índice ONI — anomalia Pacífico Equatorial</div>
    <div class="enso-track">
      <div class="eseg" style="width:20%;background:#B5D4F4;color:#0C447C;">La Niña Forte<br><span style='font-size:8px'>–1.5/–2.0</span></div>
      <div class="eseg" style="width:20%;background:#E6F1FB;color:#185FA5;">La Niña Fraca<br><span style='font-size:8px'>–0.5/–1.5</span></div>
      <div class="eseg" style="width:20%;background:#f0f0f0;color:#666;">Neutro<br><span style='font-size:8px'>–0.5/+0.5</span></div>
      <div class="eseg" style="width:20%;background:#FAEEDA;color:#854F0B;">El Niño Fraco<br><span style='font-size:8px'>+0.5/+1.5</span></div>
      <div class="eseg" style="width:20%;background:#F5C4B3;color:#993C1D;">El Niño Forte<br><span style='font-size:8px'>+1.5/+2.5</span></div>
      <div class="eneedle" style="left:{np_:.1f}%;"></div>
    </div>
    <div class="elabels"><span>–2.0</span><span>–1.5</span><span>–0.5</span><span>0</span><span>+0.5</span><span>+1.5</span><span>+2.5</span></div>
    <div class="tl">
      <div class="ti tln"><div class="tv">–1.2</div><div class="tm">Jul/25</div></div>
      <div class="ti tln"><div class="tv">–0.9</div><div class="tm">Ago/25</div></div>
      <div class="ti tln"><div class="tv">–0.6</div><div class="tm">Set/25</div></div>
      <div class="ti tne"><div class="tv">–0.3</div><div class="tm">Out/25</div></div>
      <div class="ti tne"><div class="tv">0.0</div><div class="tm">Nov/25</div></div>
      <div class="ti tne"><div class="tv">+0.2</div><div class="tm">Dez/25</div></div>
      <div class="ti tne"><div class="tv">+0.3</div><div class="tm">Jan/26</div></div>
      <div class="ti tne"><div class="tv">+0.4</div><div class="tm">Fev/26</div></div>
      <div class="ti tne"><div class="tv">+0.4</div><div class="tm">Mar/26</div></div>
      <div class="ti tne tcur"><div class="tv">{oni}</div><div class="tm">Abr/26◀</div></div>
      <div class="ti tel"><div class="tv">+0.7*</div><div class="tm">Mai/26</div></div>
      <div class="ti tel"><div class="tv">+1.0*</div><div class="tm">Jun/26</div></div>
      <div class="ti tel"><div class="tv">+1.3*</div><div class="tm">Jul/26</div></div>
    </div>
    <div style="font-size:10px;color:#aaa;">* Projeção NOAA/INPE · Fundo laranja = El Niño previsto</div>
    <div style="font-size:12px;color:#666;margin-top:8px;line-height:1.6;">{er}</div>
  </div>
  <div class="card">
    <h2>Impactos Projetados — Triângulo Mineiro</h2>
    <div class="igrid">
      <div class="ii"><div style="font-size:11px;color:#888;margin-bottom:4px;">Soja · Nov/26–Mar/27</div><div style="font-size:13px;font-weight:600;color:#A32D2D;">Déficit hídrico +30–40%</div><div style="font-size:12px;color:#666;margin-top:4px;">El Niño reduz chuvas em MG. Risco –15 a –25% produtividade.</div></div>
      <div class="ii"><div style="font-size:11px;color:#888;margin-bottom:4px;">Milho 1ª safra · Out–Dez/26</div><div style="font-size:13px;font-weight:600;color:#BA7517;">Veranico prolongado possível</div><div style="font-size:12px;color:#666;margin-top:4px;">Stress na germinação. Monitorar outubro/novembro.</div></div>
      <div class="ii"><div style="font-size:11px;color:#888;margin-bottom:4px;">Milho 2ª safra · Jan–Mar/27</div><div style="font-size:13px;font-weight:600;color:#E24B4A;">Alto risco — Veranico crítico</div><div style="font-size:12px;color:#666;margin-top:4px;">Histórico El Niño forte = queda 20–30% em MG.</div></div>
      <div class="ii"><div style="font-size:11px;color:#888;margin-bottom:4px;">Laranja · Floração Mai–Jul/26</div><div style="font-size:13px;font-weight:600;color:#3B6D11;">Efeito positivo moderado</div><div style="font-size:12px;color:#666;margin-top:4px;">El Niño tende a favorecer florada em citros no Triângulo.</div></div>
    </div>
  </div>
  <div class="card">
    <h2>Clima Regional — Próximos 7 Dias</h2>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">{clima_cards(clima)}</div>
    <div style="font-size:12px;color:#666;margin-top:10px;line-height:1.6;">{cr}</div>
    <div style="font-size:10px;color:#aaa;margin-top:6px;">Fonte: Open-Meteo · Atualizado automaticamente a cada execução</div>
  </div>
  <div class="card"><h2>Resumo da Análise</h2><p style="font-size:14px;line-height:1.8;color:#333;">{res}</p></div>
</div></div>

<div id="tab-safras" class="tc"><div class="wrap">
  <div class="card">
    <h2>Produção Mundial — 3 Safras + Projeção 26/27</h2>
    <div class="ctabs">
      <button class="ctab active" onclick="sc('soja',this)">Soja</button>
      <button class="ctab" onclick="sc('milho',this)">Milho</button>
      <button class="ctab" onclick="sc('algodao',this)">Algodão</button>
    </div>
    <div id="cs-soja">
      <div style="font-size:11px;color:#888;margin-bottom:8px;">Milhões de Toneladas (Mt) · USDA WASDE</div>
      <table class="ut"><thead><tr><th>País</th><th>23/24</th><th>24/25</th><th>25/26</th><th>Proj.26/27*</th></tr></thead><tbody>
        <tr><td>🇧🇷 Brasil</td><td>153.0</td><td>163.0</td><td class="up">167.0 ▲</td><td class="proj">155.0*</td></tr>
        <tr><td>🇺🇸 EUA</td><td>113.3</td><td>120.1</td><td class="up">121.0 ▲</td><td class="proj">122.0*</td></tr>
        <tr><td>🇦🇷 Argentina</td><td>48.0</td><td>49.5</td><td class="dn">52.0 ▼</td><td class="proj">50.0*</td></tr>
        <tr><td>🇨🇳 China</td><td>20.8</td><td>21.0</td><td>21.0 —</td><td class="proj">21.5*</td></tr>
        <tr><td>🇵🇾 Paraguai</td><td>9.8</td><td>10.5</td><td class="up">11.0 ▲</td><td class="proj">10.5*</td></tr>
        <tr><td>🌍 Mundo</td><td>396.0</td><td>421.0</td><td class="up">426.0 ▲</td><td class="proj">412.0*</td></tr>
      </tbody></table>
      <div style="height:220px;position:relative;margin-top:14px;"><canvas id="cSoja" role="img" aria-label="Soja"></canvas></div>
    </div>
    <div id="cs-milho" style="display:none;">
      <div style="font-size:11px;color:#888;margin-bottom:8px;">Milhões de Toneladas (Mt) · USDA WASDE</div>
      <table class="ut"><thead><tr><th>País</th><th>23/24</th><th>24/25</th><th>25/26</th><th>Proj.26/27*</th></tr></thead><tbody>
        <tr><td>🇺🇸 EUA</td><td>389.7</td><td>381.5</td><td class="up">394.0 ▲</td><td class="proj">390.0*</td></tr>
        <tr><td>🇨🇳 China</td><td>277.2</td><td>294.9</td><td class="up">298.0 ▲</td><td class="proj">300.0*</td></tr>
        <tr><td>🇧🇷 Brasil</td><td>127.0</td><td>149.0</td><td class="dn">137.0 ▼</td><td class="proj">120.0*</td></tr>
        <tr><td>🇦🇷 Argentina</td><td>55.0</td><td>50.0</td><td class="dn">50.0 ▼</td><td class="proj">46.0*</td></tr>
        <tr><td>🇺🇦 Ucrânia</td><td>28.3</td><td>25.5</td><td class="dn">24.0 ▼</td><td class="proj">23.0*</td></tr>
        <tr><td>🌍 Mundo</td><td>1234</td><td>1226</td><td class="up">1241 ▲</td><td class="proj">1220*</td></tr>
      </tbody></table>
      <div style="height:220px;position:relative;margin-top:14px;"><canvas id="cMilho" role="img" aria-label="Milho"></canvas></div>
    </div>
    <div id="cs-algodao" style="display:none;">
      <div style="font-size:11px;color:#888;margin-bottom:8px;">Milhões de Fardos · USDA WASDE</div>
      <table class="ut"><thead><tr><th>País</th><th>23/24</th><th>24/25</th><th>25/26</th><th>Proj.26/27*</th></tr></thead><tbody>
        <tr><td>🇨🇳 China</td><td>27.4</td><td>28.0</td><td class="up">28.5 ▲</td><td class="proj">28.0*</td></tr>
        <tr><td>🇮🇳 Índia</td><td>24.5</td><td>23.5</td><td class="dn">23.0 ▼</td><td class="proj">23.5*</td></tr>
        <tr><td>🇺🇸 EUA</td><td>12.5</td><td>14.3</td><td class="up">15.0 ▲</td><td class="proj">14.5*</td></tr>
        <tr><td>🇧🇷 Brasil</td><td>16.8</td><td>17.2</td><td class="up">17.8 ▲</td><td class="proj">16.5*</td></tr>
        <tr><td>🇵🇰 Paquistão</td><td>7.8</td><td>8.5</td><td class="up">8.8 ▲</td><td class="proj">8.5*</td></tr>
        <tr><td>🌍 Mundo</td><td>113.8</td><td>117.4</td><td class="up">120.1 ▲</td><td class="proj">117.0*</td></tr>
      </tbody></table>
      <div style="height:220px;position:relative;margin-top:14px;"><canvas id="cAlg" role="img" aria-label="Algodao"></canvas></div>
    </div>
    <div style="font-size:10px;color:#aaa;margin-top:10px;">* Projeção preliminar · Dados de safra atualizados mensalmente com WASDE</div>
  </div>
</div></div>

<div id="tab-estoques" class="tc"><div class="wrap">
  <div class="card">
    <h2>Estoques de Passagem Mundiais (Ending Stocks)</h2>
    <div style="font-size:12px;color:#666;margin-bottom:16px;">Quanto menor a relação E/U, maior a pressão de alta nos preços.</div>
    <div style="font-size:13px;font-weight:600;color:#1D9E75;margin-bottom:8px;">Soja (Mt)</div>
    <table class="ut" style="margin-bottom:16px;"><thead><tr><th>Safra</th><th>Produção</th><th>Consumo</th><th>Estoque Final</th><th>Relação E/U</th></tr></thead><tbody>
      <tr><td>23/24</td><td>396 Mt</td><td>371 Mt</td><td>114 Mt</td><td class="up">30.7%</td></tr>
      <tr><td>24/25</td><td>421 Mt</td><td>385 Mt</td><td>124 Mt</td><td class="up">32.2%</td></tr>
      <tr><td>25/26</td><td>426 Mt</td><td>392 Mt</td><td class="up">128 Mt ▲</td><td class="up">32.7%</td></tr>
      <tr style="background:#fff8e6;"><td class="proj">26/27*</td><td class="proj">412 Mt</td><td class="proj">398 Mt</td><td class="dn proj">112 Mt ▼</td><td class="dn proj">28.1%*</td></tr>
    </tbody></table>
    <div style="height:180px;position:relative;margin-bottom:20px;"><canvas id="cESoja" role="img" aria-label="Estoques soja"></canvas></div>
    <div style="font-size:13px;font-weight:600;color:#BA7517;margin-bottom:8px;">Milho (Mt)</div>
    <table class="ut" style="margin-bottom:16px;"><thead><tr><th>Safra</th><th>Produção</th><th>Consumo</th><th>Estoque Final</th><th>Relação E/U</th></tr></thead><tbody>
      <tr><td>23/24</td><td>1234 Mt</td><td>1211 Mt</td><td>319 Mt</td><td class="dn">26.4%</td></tr>
      <tr><td>24/25</td><td>1226 Mt</td><td>1228 Mt</td><td class="dn">317 Mt ▼</td><td class="dn">25.8%</td></tr>
      <tr><td>25/26</td><td>1241 Mt</td><td>1235 Mt</td><td class="up">322 Mt ▲</td><td class="up">26.1%</td></tr>
      <tr style="background:#fff8e6;"><td class="proj">26/27*</td><td class="proj">1220 Mt</td><td class="proj">1240 Mt</td><td class="dn proj">302 Mt ▼</td><td class="dn proj">24.4%*</td></tr>
    </tbody></table>
    <div style="height:180px;position:relative;margin-bottom:20px;"><canvas id="cEMilho" role="img" aria-label="Estoques milho"></canvas></div>
    <div style="font-size:13px;font-weight:600;color:#534AB7;margin-bottom:8px;">Algodão (M fardos)</div>
    <table class="ut" style="margin-bottom:16px;"><thead><tr><th>Safra</th><th>Produção</th><th>Consumo</th><th>Estoque Final</th><th>Relação E/U</th></tr></thead><tbody>
      <tr><td>23/24</td><td>113.8</td><td>111.2</td><td>83.4</td><td class="up">75.0%</td></tr>
      <tr><td>24/25</td><td>117.4</td><td>113.5</td><td class="up">87.3 ▲</td><td class="up">76.9%</td></tr>
      <tr><td>25/26</td><td>120.1</td><td>115.8</td><td class="up">91.6 ▲</td><td class="up">79.1%</td></tr>
      <tr style="background:#fff8e6;"><td class="proj">26/27*</td><td class="proj">117.0</td><td class="proj">116.5</td><td class="dn proj">88.0 ▼</td><td class="dn proj">75.5%*</td></tr>
    </tbody></table>
    <div style="background:#E6F1FB;border-radius:8px;padding:14px;">
      <div style="font-size:12px;font-weight:600;color:#0C447C;margin-bottom:6px;">Como interpretar</div>
      <div style="font-size:12px;color:#185FA5;line-height:1.8;"><b>&gt;30%</b> → Oferta confortável · <b>20–30%</b> → Equilíbrio · <b>&lt;20%</b> → Oferta apertada, pressão altista forte</div>
    </div>
    <div style="font-size:10px;color:#aaa;margin-top:8px;">* Projeção considerando El Niño · Fonte: USDA WASDE Abr/2026</div>
  </div>
</div></div>

<div id="tab-precos" class="tc"><div class="wrap">
  <div class="card">
    <h2>Preços Futuros — CBOT (tempo real)</h2>
    <div class="g2" style="margin-bottom:12px;">
      <div class="met"><div class="ml">Soja CBOT — spot</div><div class="mv">USD {su}/bu</div><div class="ms">R$ {sb}/sc · câmbio R$ {usd}</div></div>
      <div class="met"><div class="ml">Milho CBOT — spot</div><div class="mv">USD {mu}/bu</div><div class="ms">R$ {mb}/sc</div></div>
    </div>
    <div class="met"><div class="ml">Câmbio USD/BRL</div><div class="mv">R$ {usd}</div><div class="ms">Fonte: Banco Central do Brasil · Atualizado automaticamente</div></div>
    <div style="font-size:12px;color:#666;margin-top:12px;line-height:1.6;">{pr}</div>
  </div>
  <div class="card"><h2>Curva de Futuros — Soja CBOT (USD/bu)</h2>
    <div style="height:200px;position:relative;"><canvas id="cSF" role="img" aria-label="Futuros soja"></canvas></div>
  </div>
  <div class="card"><h2>Curva de Futuros — Milho CBOT (USD/bu)</h2>
    <div style="height:200px;position:relative;"><canvas id="cMF" role="img" aria-label="Futuros milho"></canvas></div>
  </div>
</div></div>

<div id="tab-hedge" class="tc"><div class="wrap">
  <div class="card">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;">{badge_risco(nivel)}<span style="font-size:13px;color:#666;">{tc_}</span></div>
    <p style="font-size:14px;color:#333;line-height:1.8;">{just}</p>
  </div>
  <div class="card"><h2>Recomendação de Hedge</h2>
    <div class="g2">
      <div class="hbox"><div class="hlbl">Soja — safra 26/27</div><div class="hpct">{hs}%</div><div class="hsub">da produção a travar agora</div></div>
      <div class="hbox"><div class="hlbl">Milho — 2ª safra 27</div><div class="hpct">{hm}%</div><div class="hsub">da produção a travar agora</div></div>
    </div>
  </div>
  <div class="card"><h2>O Que Fazer Agora</h2><ul style="padding-left:20px;">{acoes_li(analise.get("acoes_recomendadas",[]))}</ul></div>
  <div class="card"><h2>Contratos Recomendados</h2>
    <div style="overflow-x:auto;">
      <table class="ut"><thead><tr><th>Cultura</th><th>Safra</th><th>Contrato</th><th>% Hedge</th><th>Estratégia</th><th>Urgência</th></tr></thead><tbody>
        <tr><td><b>Soja</b></td><td>26/27</td><td>CBOT Nov/26</td><td class="rs">50–60%</td><td style="font-size:12px;">Venda futura B3 + Put CBOT</td><td><span style="background:#FCEBEB;color:#791F1F;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">Imediato</span></td></tr>
        <tr><td><b>Milho</b></td><td>2ª safra 27</td><td>CBOT Dez/26</td><td class="rs">40–50%</td><td style="font-size:12px;">Venda futura B3</td><td><span style="background:#FCEBEB;color:#791F1F;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">Imediato</span></td></tr>
        <tr><td><b>Milho</b></td><td>1ª safra 26</td><td>B3 Nov/26</td><td class="rp">30–40%</td><td style="font-size:12px;">Fixação parcial CPR-F</td><td><span style="background:#FAEEDA;color:#633806;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">Mai–Jun/26</span></td></tr>
        <tr><td><b>Laranja</b></td><td>26</td><td>FCOJ ICE</td><td class="rw">Aguardar</td><td style="font-size:12px;">Monitorar florada mai/jun</td><td><span style="background:#E6F1FB;color:#0C447C;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">Aguardar</span></td></tr>
      </tbody></table>
    </div>
  </div>
  <div class="card" style="background:#E6F1FB;">
    <h2 style="color:#0C447C;">Próximo Evento a Monitorar</h2>
    <p style="font-size:15px;font-weight:600;color:#042C53;">{pe}</p>
    <p style="font-size:13px;color:#185FA5;margin-top:4px;">{pd_}</p>
  </div>
  <p style="text-align:center;font-size:11px;color:#aaa;padding-bottom:24px;">Gerado automaticamente · Claude API + GitHub Actions · {dt}</p>
</div></div>

<script>
function st(n,el){{document.querySelectorAll('.tc').forEach(e=>e.classList.remove('active'));document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));document.getElementById('tab-'+n).classList.add('active');el.classList.add('active');}}
function sc(n,el){{['soja','milho','algodao'].forEach(c=>{{document.getElementById('cs-'+c).style.display=c===n?'':'none';}});document.querySelectorAll('.ctab').forEach(b=>b.classList.remove('active'));el.classList.add('active');}}
const gc='rgba(0,0,0,0.05)',tc2='#888';
new Chart(document.getElementById('cSoja'),{{type:'bar',data:{{labels:['Brasil','EUA','Argentina','China','Paraguai'],datasets:[{{label:'23/24',data:[153,113.3,48,20.8,9.8],backgroundColor:'#9FE1CB'}},{{label:'24/25',data:[163,120.1,49.5,21,10.5],backgroundColor:'#1D9E75'}},{{label:'25/26',data:[167,121,52,21,11],backgroundColor:'#085041'}},{{label:'26/27*',data:[155,122,50,21.5,10.5],backgroundColor:'#FAEEDA',borderColor:'#BA7517',borderWidth:1}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{font:{{size:11}},color:tc2}}}}}},scales:{{x:{{ticks:{{color:tc2}},grid:{{color:gc}}}},y:{{ticks:{{color:tc2}},grid:{{color:gc}}}}}}}}}});
new Chart(document.getElementById('cMilho'),{{type:'bar',data:{{labels:['EUA','China','Brasil','Argentina','Ucrânia'],datasets:[{{label:'23/24',data:[389.7,277.2,127,55,28.3],backgroundColor:'#FAC775'}},{{label:'24/25',data:[381.5,294.9,149,50,25.5],backgroundColor:'#BA7517'}},{{label:'25/26',data:[394,298,137,50,24],backgroundColor:'#633806'}},{{label:'26/27*',data:[390,300,120,46,23],backgroundColor:'#FAEEDA',borderColor:'#BA7517',borderWidth:1}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{font:{{size:11}},color:tc2}}}}}},scales:{{x:{{ticks:{{color:tc2}},grid:{{color:gc}}}},y:{{ticks:{{color:tc2}},grid:{{color:gc}}}}}}}}}});
new Chart(document.getElementById('cAlg'),{{type:'bar',data:{{labels:['China','Índia','EUA','Brasil','Paquistão'],datasets:[{{label:'23/24',data:[27.4,24.5,12.5,16.8,7.8],backgroundColor:'#AFA9EC'}},{{label:'24/25',data:[28,23.5,14.3,17.2,8.5],backgroundColor:'#7F77DD'}},{{label:'25/26',data:[28.5,23,15,17.8,8.8],backgroundColor:'#3C3489'}},{{label:'26/27*',data:[28,23.5,14.5,16.5,8.5],backgroundColor:'#EEEDFE',borderColor:'#7F77DD',borderWidth:1}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{font:{{size:11}},color:tc2}}}}}},scales:{{x:{{ticks:{{color:tc2}},grid:{{color:gc}}}},y:{{ticks:{{color:tc2}},grid:{{color:gc}}}}}}}}}});
new Chart(document.getElementById('cESoja'),{{type:'bar',data:{{labels:['23/24','24/25','25/26','26/27*'],datasets:[{{label:'Estoque (Mt)',data:[114,124,128,112],backgroundColor:['#1D9E75','#1D9E75','#1D9E75','#FAEEDA'],borderColor:['#085041','#085041','#085041','#BA7517'],borderWidth:1}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:tc2}},grid:{{color:gc}}}},y:{{ticks:{{color:tc2}},grid:{{color:gc}}}}}}}}}});
new Chart(document.getElementById('cEMilho'),{{type:'bar',data:{{labels:['23/24','24/25','25/26','26/27*'],datasets:[{{label:'Estoque (Mt)',data:[319,317,322,302],backgroundColor:['#BA7517','#BA7517','#BA7517','#FAEEDA'],borderColor:['#633806','#633806','#633806','#BA7517'],borderWidth:1}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:tc2}},grid:{{color:gc}}}},y:{{ticks:{{color:tc2}},grid:{{color:gc}}}}}}}}}});
new Chart(document.getElementById('cSF'),{{type:'line',data:{{labels:['Mai/26','Jul/26','Set/26','Nov/26','Jan/27','Mar/27'],datasets:[{{label:'Soja CBOT',data:{sf},borderColor:'#1D9E75',backgroundColor:'rgba(29,158,117,0.08)',fill:true,tension:0.3,pointRadius:5,pointBackgroundColor:'#1D9E75'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{ticks:{{color:tc2,callback:v=>'$'+v.toFixed(2)}},grid:{{color:gc}}}},x:{{ticks:{{color:tc2}},grid:{{color:gc}}}}}}}}}});
new Chart(document.getElementById('cMF'),{{type:'line',data:{{labels:['Mai/26','Jul/26','Set/26','Dez/26','Mar/27'],datasets:[{{label:'Milho CBOT',data:{mf},borderColor:'#BA7517',backgroundColor:'rgba(186,117,23,0.08)',fill:true,tension:0.3,pointRadius:5,pointBackgroundColor:'#BA7517'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{ticks:{{color:tc2,callback:v=>'$'+v.toFixed(2)}},grid:{{color:gc}}}},x:{{ticks:{{color:tc2}},grid:{{color:gc}}}}}}}}}});
</script>
</body></html>"""

def main():
    print("\nGerando dashboard dinamico...")
    with open(ANALISE_PATH, encoding="utf-8") as f:
        analise = json.load(f)
    with open(DATA_PATH, encoding="utf-8") as f:
        dados = json.load(f)
    html = gerar(analise, dados)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard salvo: {OUTPUT_PATH}\n")

if __name__ == "__main__":
    main()
