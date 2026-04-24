"""
generate_dashboard_v3.py - Agro Monitor BR
Historico RT clicavel, safras total BR + paises, historico frete por corredor
JS sem acentos ou caracteres especiais para evitar SyntaxError
"""
import json, os
from datetime import datetime

BASE_DIR      = os.path.dirname(__file__)
ANALISE_PATH  = os.path.join(BASE_DIR, "analise.json")
DATA_PATH     = os.path.join(BASE_DIR, "data_atual.json")
DASHBOARD_DIR = os.path.join(BASE_DIR, "..", "dashboard")
OUTPUT_PATH   = os.path.join(DASHBOARD_DIR, "index.html")
os.makedirs(DASHBOARD_DIR, exist_ok=True)

HIST_RT = {
    "ureia":     {"soja":[1.65,2.82,2.21,2.35],"milho":[3.28,5.60,4.38,4.65],"algodao":[1.92,3.28,2.58,2.74]},
    "map":       {"soja":[2.10,3.95,3.28,3.08],"milho":[4.18,7.84,6.50,6.10],"algodao":[2.45,4.60,3.82,3.60]},
    "kcl":       {"soja":[1.42,2.38,1.95,1.91],"milho":[2.82,4.72,3.86,3.78],"algodao":[1.66,2.78,2.28,2.23]},
    "glifosato": {"soja":[0.18,0.22,0.16,0.15],"milho":[0.36,0.44,0.32,0.30],"algodao":[0.21,0.26,0.19,0.18]},
    "diesel":    {"soja":[0.038,0.051,0.046,0.044],"milho":[0.076,0.102,0.091,0.087],"algodao":[0.044,0.060,0.054,0.051]},
}
SAFRAS_RT = ["22/23","23/24","24/25","25/26"]

HIST_FRETE = {
    "Sorriso":      [198,218,240,248],
    "Rondonopolis": [174,192,211,218],
    "Rio Verde":    [112,124,139,144],
    "Uberlandia":   [72, 80, 91, 94],
    "Barreiras":    [138,153,172,178],
    "Cascavel":     [42, 47, 52, 54],
}
SAFRAS_FRETE = ["22/23","23/24","24/25","25/26"]

def s(v, d=2, suf=""):
    try: return str(round(float(v), d)) + suf
    except: return str(v)

def badge_risco(nivel):
    n = nivel.replace("\u00e9","e").replace("\u00ed","i").replace("\u00f3","o").replace("\u00ea","e")
    cores = {"Critico":"background:#FCEBEB;color:#791F1F","Alto":"background:#FAEEDA;color:#633806","Medio":"background:#E6F1FB;color:#0C447C","Baixo":"background:#EAF3DE;color:#27500A"}
    icones = {"Critico":"&#128308;","Alto":"&#128992;","Medio":"&#128309;","Baixo":"&#128994;"}
    return "<span style=\""+cores.get(n,cores["Medio"])+";padding:5px 14px;border-radius:6px;font-size:13px;font-weight:600;\">"+icones.get(n,"&#128309;")+" RISCO "+nivel.upper()+"</span>"

def header_cor(nivel):
    n = nivel.replace("\u00e9","e").replace("\u00ed","i").replace("\u00f3","o").replace("\u00ea","e")
    return {"Critico":"#8B1A1A","Alto":"#6B3A0A","Medio":"#0D4A80","Baixo":"#1A4A0A"}.get(n,"#1a3a1a")

def needle_pos(oni):
    return max(2, min(96, round((float(oni)+2.0)/4.5*100)))

def clima_cards(clima):
    rbg={"MT":"#FCEBEB","GO":"#FAEEDA","MS":"#FAEEDA","MG":"#FAEEDA","BA":"#FAEEDA","MA":"#FAEEDA","PR":"#E6F1FB","RS":"#E6F1FB","SP":"#FAEEDA","SC":"#EAF3DE","PA":"#EAF3DE","RO":"#E6F1FB"}
    rtc={"MT":"#791F1F","GO":"#633806","MS":"#633806","MG":"#633806","BA":"#633806","MA":"#633806","PR":"#0C447C","RS":"#0C447C","SP":"#633806","SC":"#27500A","PA":"#27500A","RO":"#0C447C"}
    rlb={"MT":"Critico","GO":"Alto","MS":"Alto","MG":"Alto","BA":"Alto","MA":"Alto","PR":"Medio","RS":"Medio","SP":"Medio","SC":"Baixo","PA":"Baixo","RO":"Medio"}
    h=""
    for sig,c in clima.items():
        if "erro" in c: continue
        bg=rbg.get(sig,"#f0f0f0"); tc=rtc.get(sig,"#333"); lb=rlb.get(sig,"Medio")
        al=""
        if c.get("alerta_seca"): al="<span style=\"color:#A32D2D;font-size:10px;\"> &#9888;Seca</span>"
        elif c.get("alerta_excesso"): al="<span style=\"color:#185FA5;font-size:10px;\"> &#9888;Exc.</span>"
        h+="<div style=\"background:"+bg+";border-radius:8px;padding:10px;text-align:center;\"><div style=\"font-size:16px;font-weight:700;color:"+tc+";\">"+sig+"</div><div style=\"font-size:10px;color:"+tc+";margin-bottom:4px;\">"+lb+"</div><div style=\"font-size:13px;font-weight:700;\">"+str(c.get("precip_7d_mm","?"))+"mm"+al+"</div><div style=\"font-size:10px;color:#666;\">"+str(c.get("temp_max","?"))+"/"+str(c.get("temp_min","?"))+"&#176;C</div></div>"
    return h

def tabela_pracas(pracas, ref):
    h=""
    for p,v in pracas.items():
        basis=round(float(v)-float(ref),2)
        bc="color:#A32D2D;" if basis<0 else "color:#27500A;"
        h+="<tr><td>"+p+"</td><td style=\"text-align:right;\"><b>"+s(v)+"</b></td><td style=\"text-align:right;"+bc+"\">"+str(basis)+"</td></tr>"
    return h

def tabela_futuros(fu):
    h=""
    for venc,v in fu.items():
        h+="<tr><td>"+venc+"</td><td style=\"text-align:right;\">"+s(v.get("usd_bu","?"))+"</td><td style=\"text-align:right;\"><b>"+s(v.get("brl_sc","?"))+"</b></td></tr>"
    return h

def tabela_estado_soja(d):
    h=""
    for est,v in d.items():
        vc="color:#27500A;" if v.get("var",0)>=0 else "color:#A32D2D;"
        sv=("&#9650;+" if v.get("var",0)>=0 else "&#9660;")+str(v.get("var","?"))+"%"
        h+="<tr><td>"+est+"</td><td style=\"text-align:right;\">"+s(v.get("area","?"),1)+"</td><td style=\"text-align:right;\">"+s(v.get("prod","?"),1)+"</td><td style=\"text-align:right;\">"+str(v.get("produt","?"))+"</td><td style=\"text-align:right;\">"+str(v.get("colheita","?"))+"%</td><td style=\"text-align:right;"+vc+"\">"+sv+"</td></tr>"
    return h

def tabela_estado_milho(d):
    h=""
    for est,v in d.items():
        vc="color:#27500A;" if v.get("var",0)>=0 else "color:#A32D2D;"
        sv=("&#9650;+" if v.get("var",0)>=0 else "&#9660;")+str(v.get("var","?"))+"%"
        h+="<tr><td>"+est+"</td><td style=\"text-align:right;\">"+s(v.get("prod_1a","?"),1)+"</td><td style=\"text-align:right;\">"+s(v.get("prod_2a","?"),1)+"</td><td style=\"text-align:right;\"><b>"+s(v.get("total","?"),1)+"</b></td><td style=\"text-align:right;\">"+str(v.get("colheita_2a","?"))+"%</td><td style=\"text-align:right;"+vc+"\">"+sv+"</td></tr>"
    return h

def tabela_estado_algodao(d):
    h=""
    for est,v in d.items():
        vc="color:#27500A;" if v.get("var",0)>=0 else "color:#A32D2D;"
        sv=("&#9650;+" if v.get("var",0)>=0 else "&#9660;")+str(v.get("var","?"))+"%"
        h+="<tr><td>"+est+"</td><td style=\"text-align:right;\">"+s(v.get("area","?"),2)+"</td><td style=\"text-align:right;\">"+s(v.get("prod","?"),2)+"</td><td style=\"text-align:right;\">"+str(v.get("produt","?"))+"</td><td style=\"text-align:right;\">"+str(v.get("colheita","?"))+"%</td><td style=\"text-align:right;"+vc+"\">"+sv+"</td></tr>"
    return h

def tabela_mundial(data, unidade):
    h="<table class=\"tbl\"><thead><tr><th>Pais</th><th style=\"text-align:right;\">23/24</th><th style=\"text-align:right;\">24/25</th><th style=\"text-align:right;\">25/26</th><th style=\"text-align:right;\">Proj.26/27*</th><th>Tend.</th></tr></thead><tbody>"
    tot={"a":0,"b":0,"c":0,"d":0}
    for pais,v in data.items():
        if pais=="Mundo": continue
        vc="color:#27500A;" if v.get("proj_2627",0)>=v.get("prod_2526",0) else "color:#A32D2D;"
        for k,kk in [("a","prod_2324"),("b","prod_2425"),("c","prod_2526"),("d","proj_2627")]: tot[k]+=v.get(kk,0)
        mx=max(v.get("prod_2324",0),v.get("prod_2425",0),v.get("prod_2526",0),v.get("proj_2627",0),1)
        bw=round(v.get("prod_2526",0)/mx*50); bw2=round(v.get("proj_2627",0)/mx*50)
        spark="<div style=\"display:flex;flex-direction:column;gap:2px;\"><div style=\"height:5px;width:"+str(bw)+"px;background:#1D9E75;border-radius:2px;\"></div><div style=\"height:5px;width:"+str(bw2)+"px;background:#FAEEDA;border:1px solid #BA7517;border-radius:2px;\"></div></div>"
        h+="<tr><td style=\"font-weight:500;\">"+pais+"</td><td style=\"text-align:right;\">"+s(v.get("prod_2324","?"),0)+"</td><td style=\"text-align:right;\">"+s(v.get("prod_2425","?"),0)+"</td><td style=\"text-align:right;font-weight:600;\">"+s(v.get("prod_2526","?"),0)+"</td><td style=\"text-align:right;"+vc+"font-style:italic;\">"+s(v.get("proj_2627","?"),0)+"*</td><td>"+spark+"</td></tr>"
    vc_t="color:#27500A;" if tot["d"]>=tot["c"] else "color:#A32D2D;"
    h+="<tr style=\"background:#f8fff4;font-weight:700;\"><td>Total mundo</td><td style=\"text-align:right;\">"+s(tot["a"],0)+"</td><td style=\"text-align:right;\">"+s(tot["b"],0)+"</td><td style=\"text-align:right;\">"+s(tot["c"],0)+"</td><td style=\"text-align:right;"+vc_t+"font-style:italic;\">"+s(tot["d"],0)+"*</td><td><div style=\"font-size:10px;color:#666;\">"+unidade+"</div></td></tr>"
    h+="</tbody></table>"
    return h

def tabela_estoques(lista):
    h=""
    for e in lista:
        proj="*" in str(e.get("safra",""))
        eu=float(e.get("eu",30))
        euc="color:#A32D2D;" if eu<25 else ("color:#BA7517;" if eu<30 else "color:#27500A;")
        bg="background:#fff8e6;" if proj else ""
        h+="<tr style=\""+bg+"\"><td>"+str(e.get("safra",""))+"</td><td style=\"text-align:right;\">"+str(e.get("prod",""))+"</td><td style=\"text-align:right;\">"+str(e.get("cons",""))+"</td><td style=\"text-align:right;font-weight:700;\">"+str(e.get("est",""))+"</td><td style=\"text-align:right;"+euc+"font-weight:600;\">"+s(eu,1)+"%</td></tr>"
    return h

def painel_enso(oni, status, tend, enso_res):
    np_=needle_pos(oni)
    tend_cor="#A32D2D" if tend=="subindo" else "#185FA5"
    tend_seta="&#9650;" if tend=="subindo" else "&#9660;"
    if oni>=1.5:   probs={"La Nina Forte":0,"La Nina Moderada":0,"La Nina Fraca":1,"Neutro":4,"El Nino Fraco":15,"El Nino Moderado":35,"El Nino Forte Super":45}
    elif oni>=0.5: probs={"La Nina Forte":0,"La Nina Moderada":1,"La Nina Fraca":2,"Neutro":12,"El Nino Fraco":30,"El Nino Moderado":35,"El Nino Forte Super":20}
    elif oni>=0.0: probs={"La Nina Forte":1,"La Nina Moderada":2,"La Nina Fraca":5,"Neutro":22,"El Nino Fraco":35,"El Nino Moderado":25,"El Nino Forte Super":10}
    elif oni>=-0.5:probs={"La Nina Forte":2,"La Nina Moderada":5,"La Nina Fraca":18,"Neutro":40,"El Nino Fraco":25,"El Nino Moderado":8,"El Nino Forte Super":2}
    elif oni>=-1.0:probs={"La Nina Forte":5,"La Nina Moderada":20,"La Nina Fraca":35,"Neutro":28,"El Nino Fraco":10,"El Nino Moderado":2,"El Nino Forte Super":0}
    else:          probs={"La Nina Forte":30,"La Nina Moderada":35,"La Nina Fraca":20,"Neutro":10,"El Nino Fraco":4,"El Nino Moderado":1,"El Nino Forte Super":0}
    cores_prob={"La Nina Forte":("color:#0C447C;","#0C447C","#E6F1FB"),"La Nina Moderada":("color:#185FA5;","#378ADD","#E6F1FB"),"La Nina Fraca":("color:#185FA5;","#85B7EB","#042C53"),"Neutro":("color:#444441;","#888780","#F1EFE8"),"El Nino Fraco":("color:#854F0B;","#EF9F27","#412402"),"El Nino Moderado":("color:#A32D2D;","#E24B4A","#FCEBEB"),"El Nino Forte Super":("color:#791F1F;","#791F1F","#FCEBEB")}
    barras=""
    for nome,pct in probs.items():
        lc,bc,tc2=cores_prob[nome]
        inner=str(pct)+"%" if pct>=8 else "&nbsp;"
        barras+="<div style=\"display:flex;align-items:center;gap:10px;margin-bottom:8px;\"><div style=\"font-size:12px;font-weight:500;width:150px;flex-shrink:0;"+lc+"\">"+nome+"</div><div style=\"flex:1;height:22px;background:#f0f0f0;border-radius:4px;overflow:hidden;\"><div style=\"width:"+str(max(pct,1))+"%;height:100%;background:"+bc+";border-radius:4px;display:flex;align-items:center;justify-content:flex-end;padding-right:6px;font-size:11px;font-weight:600;color:"+tc2+";min-width:24px;\">"+inner+"</div></div><div style=\"font-size:13px;font-weight:600;min-width:36px;text-align:right;"+lc+"\">"+str(pct)+"%</div></div>"
    if oni>=0.4:
        proj_meses=[("Mai/26",round(oni+0.3,1),"el"),("Jun/26",round(oni+0.6,1),"el"),("Jul/26",round(oni+0.9,1),"el"),("Ago/26",round(oni+1.1,1),"el"),("Set/26",round(oni+1.3,1),"el_crit"),("Out/26",round(oni+1.4,1),"el_crit"),("Nov/26",round(oni+1.4,1),"el"),("Dez/26",round(oni+1.3,1),"el"),("Jan/27",round(oni+1.1,1),"el")]
    elif oni>=0.0:
        proj_meses=[("Mai/26",round(oni+0.2,1),"ne"),("Jun/26",round(oni+0.4,1),"el"),("Jul/26",round(oni+0.6,1),"el"),("Ago/26",round(oni+0.8,1),"el"),("Set/26",round(oni+1.0,1),"el_crit"),("Out/26",round(oni+1.1,1),"el_crit"),("Nov/26",round(oni+1.1,1),"el"),("Dez/26",round(oni+1.0,1),"el"),("Jan/27",round(oni+0.8,1),"el")]
    else:
        proj_meses=[("Mai/26",round(oni+0.3,1),"ne"),("Jun/26",round(oni+0.5,1),"ne"),("Jul/26",round(oni+0.7,1),"ne"),("Ago/26",round(oni+0.9,1),"el"),("Set/26",round(oni+1.0,1),"el"),("Out/26",round(oni+1.1,1),"el_crit"),("Nov/26",round(oni+1.0,1),"el"),("Dez/26",round(oni+0.9,1),"el"),("Jan/27",round(oni+0.7,1),"el")]
    bgs_tl={"ln":"#E6F1FB","ne":"#f8f8f8","el":"#FAEEDA","el_crit":"#FCEBEB"}
    txs_tl={"ln":"#185FA5","ne":"#666","el":"#854F0B","el_crit":"#A32D2D"}
    tl_cells=""
    for mes,val,tipo in proj_meses:
        bg=bgs_tl.get(tipo,"#f0f0f0"); tx=txs_tl.get(tipo,"#333")
        brd="outline:2px solid #E24B4A;outline-offset:-2px;" if tipo=="el_crit" else ""
        tl_cells+="<td style=\"background:"+bg+";"+brd+"padding:7px 2px;text-align:center;border-right:0.5px solid #eee;\"><div style=\"font-size:10px;font-weight:700;color:"+tx+";\">"+str(val)+"*</div><div style=\"font-size:9px;color:#999;margin-top:2px;\">"+mes+"</div></td>"
    if oni>=0.3:
        md=[("Mai/26",3,18,35,27,14,False),("Jun/26",1,12,33,32,20,False),("Jul/26",1,8,28,35,26,False),("Ago/26",1,6,22,38,30,False),("Set/26",1,4,15,37,40,True),("Out/26",1,3,12,35,46,True),("Nov/26",1,4,14,33,44,False),("Dez/26",2,5,15,34,41,False),("Jan/27",3,8,18,35,32,False)]
    else:
        md=[("Mai/26",10,20,30,25,12,False),("Jun/26",5,15,30,30,18,False),("Jul/26",3,10,28,35,22,False),("Ago/26",2,8,20,38,30,False),("Set/26",1,5,15,38,38,True),("Out/26",1,4,12,35,44,True),("Nov/26",1,4,14,33,44,False),("Dez/26",2,5,15,34,41,False),("Jan/27",3,8,18,35,32,False)]
    colunas=""
    for mes,ln,ne,ef,em,efort,crit in md:
        brd2="outline:2px solid #E24B4A;outline-offset:-1px;border-radius:2px;" if crit else ""
        mc="#E24B4A" if crit else "#999"; mw="font-weight:700;" if crit else ""
        def seg(hh,bg,cor,val):
            inn=str(val) if hh>=14 else ""
            return "<div style=\"height:"+str(hh)+"px;background:"+bg+";width:100%;display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:700;color:"+cor+";\">"+inn+"</div>"
        colunas+="<div style=\"flex:1;display:flex;flex-direction:column;align-items:center;"+brd2+"\">"+seg(ln,"#85B7EB","#042C53",ln)+seg(ne,"#888780","#F1EFE8",ne)+seg(ef,"#EF9F27","#412402",ef)+seg(em,"#E24B4A","#FCEBEB",em)+seg(efort,"#791F1F","#FCEBEB",efort)+"<div style=\"font-size:8px;color:"+mc+";"+mw+"margin-top:3px;text-align:center;\">"+mes+("&#9650;" if crit else "")+"</div></div>"
    p_la=probs["La Nina Fraca"]+probs["La Nina Moderada"]+probs["La Nina Forte"]
    return (
        "<div style=\"margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;\">"
        "<div><div style=\"font-size:16px;font-weight:500;color:#1a1a1a;\">"+status+"</div>"
        "<div style=\"font-size:12px;color:#666;margin-top:2px;\">Avaliacao NOAA CPC</div></div>"
        "<span style=\"background:#FAEEDA;color:#633806;padding:5px 14px;border-radius:6px;font-size:13px;font-weight:600;\">ONI "+s(oni)+" "+tend_seta+" <span style=\"color:"+tend_cor+";\">"+tend+"</span></span></div>"
        "<div style=\"font-size:11px;font-weight:500;color:#888;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;\">Posicao no espectro ENSO</div>"
        "<div style=\"position:relative;height:48px;border-radius:8px;overflow:hidden;display:flex;margin:8px 0 3px;\">"
        "<div style=\"width:14%;height:100%;background:#0C447C;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#E6F1FB;text-align:center;\">La Nina<br>Forte<br><span style=\"font-size:8px;opacity:.8;\">&#8804;-1.5</span></div>"
        "<div style=\"width:15%;height:100%;background:#378ADD;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#E6F1FB;text-align:center;\">La Nina<br>Moder.<br><span style=\"font-size:8px;opacity:.8;\">-1.5/-1.0</span></div>"
        "<div style=\"width:15%;height:100%;background:#85B7EB;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#042C53;text-align:center;\">La Nina<br>Fraca<br><span style=\"font-size:8px;opacity:.8;\">-1.0/-0.5</span></div>"
        "<div style=\"width:15%;height:100%;background:#e8e8e0;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#444;text-align:center;\">Neutro<br><br><span style=\"font-size:8px;opacity:.8;\">-0.5/+0.5</span></div>"
        "<div style=\"width:15%;height:100%;background:#FAC775;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#412402;text-align:center;\">El Nino<br>Fraco<br><span style=\"font-size:8px;opacity:.8;\">+0.5/+1.5</span></div>"
        "<div style=\"width:13%;height:100%;background:#E24B4A;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#FCEBEB;text-align:center;\">El Nino<br>Forte<br><span style=\"font-size:8px;opacity:.8;\">+1.5/+2.0</span></div>"
        "<div style=\"width:13%;height:100%;background:#791F1F;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#FCEBEB;text-align:center;\">Super<br>El Nino<br><span style=\"font-size:8px;opacity:.8;\">&gt;+2.0</span></div>"
        "<div style=\"position:absolute;top:-4px;height:calc(100%% + 8px);width:3px;background:#1a1a1a;border-radius:2px;left:"+str(np_)+"%;transform:translateX(-50%%);z-index:10;\"></div></div>"
        "<div style=\"display:flex;justify-content:space-between;font-size:10px;color:#999;margin-bottom:6px;\"><span>-2.0</span><span>-1.5</span><span>-1.0</span><span>-0.5</span><span>0</span><span>+0.5</span><span>+1.5</span><span>+2.0</span><span>+2.5</span></div>"
        "<div style=\"font-size:11px;color:#555;margin-bottom:16px;\">ONI atual <strong>"+s(oni)+"</strong> &#183; Projecao jun/26: <strong style=\"color:#854F0B;\">+0.8 a +1.2</strong> &#183; Prob. Super El Nino: <strong style=\"color:#A32D2D;\">65-70%%</strong></div>"
        "<div style=\"height:0.5px;background:#eee;margin-bottom:16px;\"></div>"
        "<div style=\"font-size:11px;font-weight:500;color:#888;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;\">Probabilidades proximos 3 meses</div>"
        +barras+
        "<div style=\"height:0.5px;background:#eee;margin:16px 0;\"></div>"
        "<div style=\"font-size:11px;font-weight:500;color:#888;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;\">Projecao ONI mensal</div>"
        "<table style=\"width:100%;border-collapse:collapse;border:0.5px solid #eee;border-radius:8px;overflow:hidden;margin-bottom:4px;\"><tr>"+tl_cells+"</tr></table>"
        "<div style=\"font-size:10px;color:#999;margin-bottom:16px;\">* Projecao NOAA/INPE &#183; &#128308; Periodo critico plantio safra 26/27</div>"
        "<div style=\"height:0.5px;background:#eee;margin-bottom:16px;\"></div>"
        "<div style=\"font-size:11px;font-weight:500;color:#888;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;\">Evolucao das probabilidades mensais</div>"
        "<div style=\"display:flex;gap:2px;align-items:flex-end;height:100px;margin-bottom:4px;\">"+colunas+"</div>"
        "<div style=\"display:flex;flex-wrap:wrap;gap:12px;margin-bottom:4px;font-size:11px;\">"
        "<span style=\"display:flex;align-items:center;gap:4px;\"><span style=\"width:10px;height:10px;border-radius:2px;background:#85B7EB;display:inline-block;\"></span><span style=\"color:#666;\">La Nina</span></span>"
        "<span style=\"display:flex;align-items:center;gap:4px;\"><span style=\"width:10px;height:10px;border-radius:2px;background:#888780;display:inline-block;\"></span><span style=\"color:#666;\">Neutro</span></span>"
        "<span style=\"display:flex;align-items:center;gap:4px;\"><span style=\"width:10px;height:10px;border-radius:2px;background:#EF9F27;display:inline-block;\"></span><span style=\"color:#666;\">El Nino Fraco</span></span>"
        "<span style=\"display:flex;align-items:center;gap:4px;\"><span style=\"width:10px;height:10px;border-radius:2px;background:#E24B4A;display:inline-block;\"></span><span style=\"color:#666;\">El Nino Moderado</span></span>"
        "<span style=\"display:flex;align-items:center;gap:4px;\"><span style=\"width:10px;height:10px;border-radius:2px;background:#791F1F;display:inline-block;\"></span><span style=\"color:#666;\">El Nino Forte/Super</span></span>"
        "<span style=\"color:#E24B4A;font-weight:600;font-size:11px;\">&#9650; = periodo critico safra</span></div>"
        "<div style=\"font-size:10px;color:#aaa;margin-bottom:16px;\">Fonte: NOAA CPC IRI probabilistic ENSO forecast</div>"
        "<div style=\"height:0.5px;background:#eee;margin-bottom:16px;\"></div>"
        "<div style=\"font-size:11px;font-weight:500;color:#888;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;\">Impacto por cenario - Centro-Oeste e Triangulo Mineiro</div>"
        "<div style=\"display:grid;grid-template-columns:repeat(5,1fr);gap:8px;\">"
        "<div style=\"background:#E6F1FB;border:0.5px solid #85B7EB;border-radius:8px;padding:10px 8px;text-align:center;\"><div style=\"font-size:11px;font-weight:600;color:#0C447C;margin-bottom:4px;\">La Nina</div><div style=\"font-size:18px;font-weight:700;color:#0C447C;\">"+str(p_la)+"%</div><div style=\"font-size:10px;color:#185FA5;\">prob.</div><div style=\"font-size:10px;color:#27500A;margin-top:6px;\">Soja: +5/+10%%</div><div style=\"font-size:10px;color:#27500A;\">Milho: +5/+8%%</div><div style=\"font-size:10px;color:#27500A;\">Algodao: +3/+6%%</div></div>"
        "<div style=\"background:#f5f5f3;border:0.5px solid #B4B2A9;border-radius:8px;padding:10px 8px;text-align:center;\"><div style=\"font-size:11px;font-weight:600;color:#444;margin-bottom:4px;\">Neutro</div><div style=\"font-size:18px;font-weight:700;color:#444;\">"+str(probs["Neutro"])+"%</div><div style=\"font-size:10px;color:#666;\">prob.</div><div style=\"font-size:10px;color:#444;margin-top:6px;\">Soja: 0/+5%%</div><div style=\"font-size:10px;color:#444;\">Milho: 0/+5%%</div><div style=\"font-size:10px;color:#444;\">Algodao: 0/+3%%</div></div>"
        "<div style=\"background:#FAEEDA;border:0.5px solid #EF9F27;border-radius:8px;padding:10px 8px;text-align:center;\"><div style=\"font-size:11px;font-weight:600;color:#854F0B;margin-bottom:4px;\">El Nino Fraco</div><div style=\"font-size:18px;font-weight:700;color:#854F0B;\">"+str(probs["El Nino Fraco"])+"%</div><div style=\"font-size:10px;color:#BA7517;\">prob.</div><div style=\"font-size:10px;color:#A32D2D;margin-top:6px;\">Soja: -5/-15%%</div><div style=\"font-size:10px;color:#A32D2D;\">Milho: -10/-20%%</div><div style=\"font-size:10px;color:#A32D2D;\">Algodao: -5/-10%%</div></div>"
        "<div style=\"background:#FCEBEB;border:0.5px solid #E24B4A;border-radius:8px;padding:10px 8px;text-align:center;\"><div style=\"font-size:11px;font-weight:600;color:#A32D2D;margin-bottom:4px;\">El Nino Moder.</div><div style=\"font-size:18px;font-weight:700;color:#A32D2D;\">"+str(probs["El Nino Moderado"])+"%</div><div style=\"font-size:10px;color:#A32D2D;\">prob.</div><div style=\"font-size:10px;color:#A32D2D;margin-top:6px;\">Soja: -15/-25%%</div><div style=\"font-size:10px;color:#A32D2D;\">Milho: -20/-30%%</div><div style=\"font-size:10px;color:#A32D2D;\">Algodao: -10/-18%%</div></div>"
        "<div style=\"background:#FCEBEB;border:2px solid #791F1F;border-radius:8px;padding:10px 8px;text-align:center;\"><div style=\"font-size:11px;font-weight:600;color:#791F1F;margin-bottom:4px;\">Super El Nino</div><div style=\"font-size:18px;font-weight:700;color:#791F1F;\">"+str(probs["El Nino Forte Super"])+"%</div><div style=\"font-size:10px;color:#791F1F;\">prob.</div><div style=\"font-size:10px;color:#791F1F;margin-top:6px;\">Soja: -25/-35%%</div><div style=\"font-size:10px;color:#791F1F;\">Milho: -30/-40%%</div><div style=\"font-size:10px;color:#791F1F;\">Algodao: -18/-25%%</div></div>"
        "</div>"
        "<div style=\"font-size:10px;color:#aaa;margin-top:8px;\">Impacto na produtividade vs media historica</div>"
        "<div style=\"height:0.5px;background:#eee;margin:16px 0;\"></div>"
        "<div style=\"font-size:11px;color:#555;line-height:1.7;\">"+enso_res+"</div>"
    )

def js_rt_data(rt_js):
    """Gera bloco JS com todos os dados de RT como objeto global - sem acentos."""
    lines = ["var RT_DATA = {"]
    for key, crops in rt_js.items():
        soja_vals   = json.dumps([round(v,3) if v is not None else 0 for v in crops["soja"]])
        milho_vals  = json.dumps([round(v,3) if v is not None else 0 for v in crops["milho"]])
        alg_vals    = json.dumps([round(v,3) if v is not None else 0 for v in crops["algodao"]])
        lines.append('  "'+key+'": {soja:'+soja_vals+',milho:'+milho_vals+',algodao:'+alg_vals+'},')
    lines.append("};")
    lines.append('var RT_LABELS = '+json.dumps(SAFRAS_RT)+';')
    return "\n".join(lines)

def js_frete_data(frete_js):
    """Gera bloco JS com dados de frete como objeto global."""
    lines = ["var FR_DATA = {"]
    for key, vals in frete_js.items():
        cores = []
        for i,v in enumerate(vals):
            if i == len(vals)-1: cores.append("#1D9E75")
            elif v == max(vals): cores.append("#E24B4A")
            else: cores.append("#9FE1CB")
        safe_key = key.replace(" ","_")
        lines.append('  "'+safe_key+'": {values:'+json.dumps(vals)+',colors:'+json.dumps(cores)+',min:'+str(int(min(vals)*0.85))+'},')
    lines.append("};")
    lines.append('var FR_LABELS = '+json.dumps(SAFRAS_FRETE)+';')
    return "\n".join(lines)

def gerar(analise, dados):
    enso=dados.get("enso",{}); precos=dados.get("precos",{}); pracas=dados.get("pracas",{})
    cambio=dados.get("cambio",{}); clima=dados.get("clima_estados",{}); safras=dados.get("safras",{})
    frete=dados.get("frete",{}); rt=dados.get("relacao_troca",{})
    nivel=analise.get("nivel_risco","Medio"); oni=enso.get("oni_atual",0.4)
    status=enso.get("status","Neutro"); tend=enso.get("tendencia","subindo")
    usd=cambio.get("usd_brl",5.95); dt=analise.get("data_analise",dados.get("data_coleta",""))
    hcor=header_cor(nivel)
    soja_cbot=precos.get("soja_cbot",{}) or {}; milho_cbot=precos.get("milho_cbot",{}) or {}
    alg_ice=precos.get("algodao_ice",{}) or {}; soja_fu=precos.get("soja_futuros",{}) or {}
    milho_fu=precos.get("milho_futuros",{}) or {}
    prac_soja=pracas.get("soja",{}) or {}; prac_milho=pracas.get("milho",{}) or {}
    prac_alg=pracas.get("algodao",{}) or {}
    ref_pga=pracas.get("ref_soja_paranagua",135.0); ref_cpx=pracas.get("ref_milho_campinas",68.0)
    ref_alg=pracas.get("ref_algodao_br",115.0)
    rt_soja=rt.get("relacao_soja",{}) or {}; rt_milho=rt.get("relacao_milho",{}) or {}
    rt_alg=rt.get("relacao_algodao",{}) or {}; insumos=rt.get("precos_insumos",{}) or {}
    soja_br=safras.get("soja_br",{}) or {}; milho_br=safras.get("milho_br",{}) or {}
    alg_br=safras.get("algodao_br",{}) or {}; mundial=safras.get("mundial",{}) or {}
    estoques=mundial.get("estoques",{}) or {}
    resumo=analise.get("resumo_executivo","").replace("\n","<br><br>")
    enso_res=analise.get("enso_resumo",""); just=analise.get("justificativa_hedge","")
    acoes=analise.get("acoes_recomendadas",[]); pe=analise.get("proximo_evento_importante","")
    pd_=analise.get("proximo_evento_data",""); pr_res=analise.get("precos_resumo","")
    hs=analise.get("recomendacao_hedge_soja_pct",50); hm=analise.get("recomendacao_hedge_milho_pct",40)
    tc_=analise.get("tipo_mudanca","")
    acoes_li="".join("<li style=\"margin-bottom:10px;font-size:14px;\">"+a+"</li>" for a in acoes)
    hist_soja=precos.get("hist_soja",[]); hist_milho=precos.get("hist_milho",[]); hist_alg=precos.get("hist_algodao",[])
    def hl(h): return json.dumps([x["data"] for x in h]) if h else '["Out/25","Nov/25","Dez/25","Jan/26","Fev/26","Mar/26","Abr/26"]'
    def hds(h): return json.dumps([round(x["preco"]/100,2) for x in h]) if h else "[118,121,125,128,131,133,135.5]"
    def hdm(h): return json.dumps([round(x["preco"]/100,2) for x in h]) if h else "[72,70,68,69,70,69,68.4]"
    def hda(h): return json.dumps([round(x["preco"]/100,4) for x in h]) if h else "[0.62,0.64,0.65,0.66,0.67,0.67,0.68]"
    sfl=json.dumps(list(soja_fu.keys())) if soja_fu else '["Mai/26","Jul/26","Set/26","Nov/26","Jan/27"]'
    sfd=json.dumps([v["usd_bu"] for v in soja_fu.values()]) if soja_fu else "[10.42,10.55,10.68,10.88,10.72]"

    # Atualiza RT historico com valor atual
    rt_map={"ureia":"ureia_sc_ton","map":"map_sc_ton","kcl":"kcl_sc_ton","glifosato":"glifosato_sc_l","diesel":"diesel_sc_l"}
    for key,crops in HIST_RT.items():
        rk=rt_map.get(key,"")
        if rk and rk in rt_soja:
            crops["soja"][3]=round(float(rt_soja[rk]),3)
        if rk and key in ("ureia","map","kcl") and rk in rt_milho:
            crops["milho"][3]=round(float(rt_milho[rk]),3)
        rk2=rk.replace("sc_ton","arr_ton").replace("sc_l","arr_l")
        if rk2 in rt_alg:
            crops["algodao"][3]=round(float(rt_alg[rk2]),3)

    js_rt  = js_rt_data(HIST_RT)
    js_fr  = js_frete_data(HIST_FRETE)

    CSS="""*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f0f0;color:#1a1a1a;}
.hdr{background:"""+hcor+""";color:white;padding:16px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;}
.hdr h1{font-size:18px;font-weight:600;}.hdr p{font-size:11px;opacity:.75;margin-top:2px;}
.tabs{background:rgba(0,0,0,0.3);display:flex;overflow-x:auto;padding:0 28px;}
.tab{padding:10px 16px;font-size:12px;color:rgba(255,255,255,.55);cursor:pointer;border:none;border-bottom:2px solid transparent;background:none;white-space:nowrap;font-weight:500;}
.tab.active{color:white;border-bottom:2px solid #4caf50;}
.wrap{max-width:1100px;margin:16px auto;padding:0 14px;}
.tc{display:none;}.tc.active{display:block;}
.card{background:white;border-radius:10px;padding:16px 20px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.06);}
.ct{font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #f0f0f0;padding-bottom:8px;margin-bottom:12px;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;}
.met{background:#f8f8f8;border-radius:8px;padding:12px;}
.ml{font-size:10px;color:#888;text-transform:uppercase;margin-bottom:4px;}
.mv{font-size:20px;font-weight:700;}.ms{font-size:11px;color:#666;margin-top:3px;}
.tbl{width:100%;border-collapse:collapse;font-size:12px;}
.tbl th{background:#1a3a1a;color:white;padding:7px 10px;text-align:left;font-weight:600;font-size:11px;}
.tbl td{padding:8px 10px;border-bottom:1px solid #f5f5f5;vertical-align:top;}
.tbl tr:last-child td{border-bottom:none;}
.tbl tr:hover td{background:#fafafa;}
.rtabs{display:flex;gap:4px;margin-bottom:12px;flex-wrap:wrap;}
.rtab{padding:4px 12px;border-radius:5px;font-size:11px;cursor:pointer;border:1px solid #ddd;background:white;color:#666;font-weight:500;}
.rtab.active{background:#1a3a1a;color:white;border-color:#1a3a1a;}
.ai{display:flex;gap:8px;padding:8px 0;border-bottom:1px solid #f5f5f5;}
.ai:last-child{border-bottom:none;}
.dot{width:7px;height:7px;border-radius:50%;margin-top:4px;flex-shrink:0;}
.dr{background:#E24B4A;}.da{background:#EF9F27;}.dg{background:#639922;}.db{background:#378ADD;}
.hbox{background:#EAF3DE;border-radius:8px;padding:16px;text-align:center;}
.hpct{font-size:36px;font-weight:700;color:#27500A;}
.hlbl{font-size:10px;color:#3B6D11;text-transform:uppercase;margin-bottom:4px;}
.hsub{font-size:11px;color:#3B6D11;margin-top:4px;}
.rt-card{border:1px solid #eee;border-radius:8px;padding:12px;cursor:pointer;transition:box-shadow .15s;}
.rt-card:hover{box-shadow:0 2px 8px rgba(0,0,0,.10);}
.rt-hist{display:none;margin-top:12px;padding-top:12px;border-top:1px solid #f0f0f0;}
.fr-hist{display:none;background:#f8fff4;}
@media(max-width:700px){.g2,.g3,.g4{grid-template-columns:1fr 1fr;}.tabs{padding:0 10px;}.wrap{padding:0 8px;}.hdr{padding:14px 16px;}}
@media(max-width:480px){.g4{grid-template-columns:1fr 1fr;}}"""

    html="<!DOCTYPE html><html lang=\"pt-BR\"><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\"><title>Agro Monitor BR</title>"
    html+="<script src=\"https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js\"></script>"
    html+="<style>"+CSS+"</style></head><body>"
    html+="<div class=\"hdr\"><div><h1>Agro Monitor BR</h1><p>Monitor Agricola Nacional &#183; Soja &#183; Milho &#183; Algodao &#183; Clima &#183; Mercado</p></div><div style=\"text-align:right;\">"+badge_risco(nivel)+"<br><span style=\"font-size:11px;opacity:.75;margin-top:4px;display:block;\">Atualizado: "+dt+"</span></div></div>"
    html+="<div class=\"tabs\"><button class=\"tab active\" onclick=\"st('visao',this)\">Visao Geral</button><button class=\"tab\" onclick=\"st('clima',this)\">Clima e ENSO</button><button class=\"tab\" onclick=\"st('safras',this)\">Safras por Regiao</button><button class=\"tab\" onclick=\"st('precos',this)\">Precos CEPEA</button><button class=\"tab\" onclick=\"st('frete',this)\">Frete e Logistica</button><button class=\"tab\" onclick=\"st('insumos',this)\">Relacao de Troca</button><button class=\"tab\" onclick=\"st('algodao',this)\">Algodao</button><button class=\"tab\" onclick=\"st('hedge',this)\">Hedge e Decisao</button></div>"

    # VISAO GERAL
    html+="<div id=\"tab-visao\" class=\"tc active\"><div class=\"wrap\">"
    html+="<div class=\"g2\"><div class=\"card\"><div class=\"ct\">Cambio e Precos Spot</div><div class=\"g2\"><div class=\"met\"><div class=\"ml\">USD/BRL</div><div class=\"mv\">R$ "+s(usd)+"</div></div><div class=\"met\"><div class=\"ml\">Soja CBOT</div><div class=\"mv\">USD "+s(soja_cbot.get("preco_usd_bushel","?"))+"/bu</div><div class=\"ms\">R$ "+s(soja_cbot.get("preco_brl_saca","?"))+"/sc</div></div><div class=\"met\"><div class=\"ml\">Milho CBOT</div><div class=\"mv\">USD "+s(milho_cbot.get("preco_usd_bushel","?"))+"/bu</div><div class=\"ms\">R$ "+s(milho_cbot.get("preco_brl_saca","?"))+"/sc</div></div><div class=\"met\"><div class=\"ml\">Algodao ICE</div><div class=\"mv\">USD "+s(alg_ice.get("preco_usd_lb","?"),4)+"/lb</div><div class=\"ms\">R$ "+s(alg_ice.get("preco_brl_arroba","?"))+"/@</div></div></div></div>"
    html+="<div class=\"card\"><div class=\"ct\">Alertas do Dia</div><div class=\"ai\"><div class=\"dot dr\"></div><div style=\"font-size:13px;line-height:1.6;\"><strong>ENSO:</strong> "+analise.get("enso_resumo","")+"</div></div><div class=\"ai\"><div class=\"dot da\"></div><div style=\"font-size:13px;line-height:1.6;\"><strong>Mercado:</strong> "+pr_res+"</div></div><div class=\"ai\"><div class=\"dot db\"></div><div style=\"font-size:13px;line-height:1.6;\"><strong>Proximo evento:</strong> "+pe+" - "+pd_+"</div></div></div></div>"
    html+="<div class=\"card\"><div class=\"ct\">Precos por Praca</div><div class=\"g3\"><div><div style=\"font-size:12px;font-weight:700;color:#1D9E75;margin-bottom:8px;\">Soja (R$/sc)</div><table class=\"tbl\"><thead><tr><th>Praca</th><th style=\"text-align:right;\">R$/sc</th><th style=\"text-align:right;\">Basis</th></tr></thead><tbody>"+tabela_pracas(prac_soja,ref_pga)+"</tbody></table></div><div><div style=\"font-size:12px;font-weight:700;color:#BA7517;margin-bottom:8px;\">Milho (R$/sc)</div><table class=\"tbl\"><thead><tr><th>Praca</th><th style=\"text-align:right;\">R$/sc</th><th style=\"text-align:right;\">Basis</th></tr></thead><tbody>"+tabela_pracas(prac_milho,ref_cpx)+"</tbody></table></div><div><div style=\"font-size:12px;font-weight:700;color:#534AB7;margin-bottom:8px;\">Algodao (R$/@)</div><table class=\"tbl\"><thead><tr><th>Praca</th><th style=\"text-align:right;\">R$/@</th></tr></thead><tbody>"+"".join("<tr><td>"+p+"</td><td style=\"text-align:right;\"><b>"+s(v)+"</b></td></tr>" for p,v in prac_alg.items())+"</tbody></table></div></div></div>"
    html+="<div class=\"card\"><div class=\"ct\">Resumo da Analise</div><p style=\"font-size:14px;line-height:1.8;color:#333;\">"+resumo+"</p></div>"
    html+="</div></div>"

    # CLIMA
    html+="<div id=\"tab-clima\" class=\"tc\"><div class=\"wrap\">"
    html+="<div class=\"card\"><div class=\"ct\">Status ENSO e Probabilidades Climaticas</div>"+painel_enso(oni,status,tend,enso_res)+"</div>"
    html+="<div class=\"card\"><div class=\"ct\">Mapa de Risco por Estado - Safra 26/27</div><div style=\"display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:10px 0;\">"+clima_cards(clima)+"</div><div style=\"font-size:10px;color:#aaa;margin-top:4px;\">Previsao 7 dias Open-Meteo &#183; Risco baseado em projecoes ENSO/INPE</div></div>"
    html+="<div class=\"card\"><div class=\"ct\">Impactos por Macrorregiao</div><table class=\"tbl\"><tr><th>Regiao</th><th>Estados</th><th>Risco</th><th style=\"text-align:right;\">Soja</th><th style=\"text-align:right;\">Milho 2a</th><th style=\"text-align:right;\">Algodao</th></tr><tr><td><b>Centro-Oeste</b></td><td>MT, MS, GO</td><td><span style=\"background:#FCEBEB;color:#791F1F;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;\">Critico</span></td><td style=\"text-align:right;color:#A32D2D;\">-15/-25%%</td><td style=\"text-align:right;color:#A32D2D;\">-20/-30%%</td><td style=\"text-align:right;color:#A32D2D;\">-10/-18%%</td></tr><tr><td><b>MATOPIBA</b></td><td>MA, TO, PI, BA</td><td><span style=\"background:#FAEEDA;color:#633806;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;\">Alto</span></td><td style=\"text-align:right;color:#A32D2D;\">-10/-20%%</td><td style=\"text-align:right;color:#A32D2D;\">-15/-25%%</td><td style=\"text-align:right;color:#A32D2D;\">-8/-15%%</td></tr><tr><td><b>Triangulo/MG</b></td><td>MG, SP oeste</td><td><span style=\"background:#FAEEDA;color:#633806;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;\">Alto</span></td><td style=\"text-align:right;color:#A32D2D;\">-15/-25%%</td><td style=\"text-align:right;color:#A32D2D;\">-20/-30%%</td><td style=\"text-align:right;color:#888;\">-</td></tr><tr><td><b>Sul</b></td><td>PR, SC, RS</td><td><span style=\"background:#E6F1FB;color:#0C447C;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;\">Medio</span></td><td style=\"text-align:right;color:#BA7517;\">-5/+5%%</td><td style=\"text-align:right;color:#BA7517;\">-5/+5%%</td><td style=\"text-align:right;color:#888;\">-</td></tr><tr><td><b>Sul Para</b></td><td>PA, RO</td><td><span style=\"background:#EAF3DE;color:#27500A;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;\">Baixo</span></td><td style=\"text-align:right;color:#27500A;\">0/+5%%</td><td style=\"text-align:right;color:#27500A;\">0/+5%%</td><td style=\"text-align:right;color:#888;\">-</td></tr></table></div>"
    html+="</div></div>"

    # SAFRAS
    html+="<div id=\"tab-safras\" class=\"tc\"><div class=\"wrap\">"
    html+="<div class=\"card\"><div class=\"ct\">Andamento da Safra 25/26 - Brasil (CONAB/IMEA)</div><div class=\"rtabs\"><button class=\"rtab active\" onclick=\"sr('soja',this)\">Soja BR</button><button class=\"rtab\" onclick=\"sr('milho',this)\">Milho BR</button><button class=\"rtab\" onclick=\"sr('algodao',this)\">Algodao BR</button><button class=\"rtab\" onclick=\"sr('ms',this)\">Mundo Soja</button><button class=\"rtab\" onclick=\"sr('mm',this)\">Mundo Milho</button><button class=\"rtab\" onclick=\"sr('ma',this)\">Mundo Algodao</button></div>"
    html+="<div id=\"sr-soja\"><div class=\"g4\" style=\"margin-bottom:12px;\"><div class=\"met\"><div class=\"ml\">Area total BR</div><div class=\"mv\">"+s(soja_br.get("area_mha","?"),1)+" Mha</div></div><div class=\"met\"><div class=\"ml\">Producao total BR</div><div class=\"mv\" style=\"color:#1D9E75;\">"+s(soja_br.get("producao_mt","?"),0)+" Mt</div><div class=\"ms\" style=\"color:#27500A;\">+"+s(soja_br.get("vs_safra_anterior_pct","?"),1)+"%% vs 24/25</div></div><div class=\"met\"><div class=\"ml\">Produtividade</div><div class=\"mv\">"+str(soja_br.get("produtividade_kgha","?"))+" kg/ha</div></div><div class=\"met\"><div class=\"ml\">Colheita</div><div class=\"mv\" style=\"color:#1D9E75;\">"+str(soja_br.get("colheita_pct","?"))+"%</div></div></div><table class=\"tbl\"><thead><tr><th>Estado</th><th style=\"text-align:right;\">Area(Mha)</th><th style=\"text-align:right;\">Prod.(Mt)</th><th style=\"text-align:right;\">kg/ha</th><th style=\"text-align:right;\">Colheita</th><th style=\"text-align:right;\">vs 24/25</th></tr></thead><tbody>"+tabela_estado_soja(soja_br.get("por_estado",{}))+"</tbody></table></div>"
    html+="<div id=\"sr-milho\" style=\"display:none;\"><div class=\"g4\" style=\"margin-bottom:12px;\"><div class=\"met\"><div class=\"ml\">Area total BR</div><div class=\"mv\">"+s(milho_br.get("area_mha","?"),1)+" Mha</div></div><div class=\"met\"><div class=\"ml\">Producao total BR</div><div class=\"mv\" style=\"color:#BA7517;\">"+s(milho_br.get("producao_mt","?"),0)+" Mt</div><div class=\"ms\" style=\"color:#A32D2D;\">"+s(milho_br.get("vs_safra_anterior_pct","?"),1)+"%% vs 24/25</div></div><div class=\"met\"><div class=\"ml\">Produtividade</div><div class=\"mv\">"+str(milho_br.get("produtividade_kgha","?"))+" kg/ha</div></div><div class=\"met\"><div class=\"ml\">Colheita 2a safra</div><div class=\"mv\" style=\"color:#BA7517;\">"+str(milho_br.get("colheita_2a_pct","?"))+"%</div></div></div><table class=\"tbl\"><thead><tr><th>Estado</th><th style=\"text-align:right;\">1a Safra(Mt)</th><th style=\"text-align:right;\">2a Safra(Mt)</th><th style=\"text-align:right;\">Total(Mt)</th><th style=\"text-align:right;\">Colheita 2a</th><th style=\"text-align:right;\">vs 24/25</th></tr></thead><tbody>"+tabela_estado_milho(milho_br.get("por_estado",{}))+"</tbody></table></div>"
    html+="<div id=\"sr-algodao\" style=\"display:none;\"><div class=\"g4\" style=\"margin-bottom:12px;\"><div class=\"met\"><div class=\"ml\">Area total BR</div><div class=\"mv\">"+s(alg_br.get("area_mha","?"),2)+" Mha</div></div><div class=\"met\"><div class=\"ml\">Producao total BR</div><div class=\"mv\" style=\"color:#534AB7;\">"+s(alg_br.get("producao_mfardos","?"),1)+" Mf</div></div><div class=\"met\"><div class=\"ml\">Produtividade</div><div class=\"mv\">"+str(alg_br.get("produtividade_arrha","?"))+" @/ha</div></div><div class=\"met\"><div class=\"ml\">Colheita</div><div class=\"mv\" style=\"color:#1D9E75;\">"+str(alg_br.get("colheita_pct","?"))+"%</div></div></div><table class=\"tbl\"><thead><tr><th>Estado</th><th style=\"text-align:right;\">Area(Mha)</th><th style=\"text-align:right;\">Prod.(Mf)</th><th style=\"text-align:right;\">@/ha</th><th style=\"text-align:right;\">Colheita</th><th style=\"text-align:right;\">vs 24/25</th></tr></thead><tbody>"+tabela_estado_algodao(alg_br.get("por_estado",{}))+"</tbody></table></div>"
    html+="<div id=\"sr-ms\" style=\"display:none;\">"+tabela_mundial(mundial.get("soja_mt",{}),"Mt")+"</div>"
    html+="<div id=\"sr-mm\" style=\"display:none;\">"+tabela_mundial(mundial.get("milho_mt",{}),"Mt")+"</div>"
    html+="<div id=\"sr-ma\" style=\"display:none;\">"+tabela_mundial(mundial.get("algodao_mf",{}),"Mf")+"</div>"
    html+="<div style=\"font-size:10px;color:#aaa;margin-top:8px;\">* Projecao &#183; "+safras.get("referencia","CONAB")+"</div></div>"
    html+="<div class=\"card\"><div class=\"ct\">Estoques de Passagem Mundiais</div><div class=\"g3\"><div><div style=\"font-size:12px;font-weight:700;color:#1D9E75;margin-bottom:6px;\">Soja (Mt)</div><table class=\"tbl\"><thead><tr><th>Safra</th><th style=\"text-align:right;\">Prod.</th><th style=\"text-align:right;\">Cons.</th><th style=\"text-align:right;\">Est.</th><th style=\"text-align:right;\">E/U%%</th></tr></thead><tbody>"+tabela_estoques(estoques.get("soja",[]))+"</tbody></table></div><div><div style=\"font-size:12px;font-weight:700;color:#BA7517;margin-bottom:6px;\">Milho (Mt)</div><table class=\"tbl\"><thead><tr><th>Safra</th><th style=\"text-align:right;\">Prod.</th><th style=\"text-align:right;\">Cons.</th><th style=\"text-align:right;\">Est.</th><th style=\"text-align:right;\">E/U%%</th></tr></thead><tbody>"+tabela_estoques(estoques.get("milho",[]))+"</tbody></table></div><div><div style=\"font-size:12px;font-weight:700;color:#534AB7;margin-bottom:6px;\">Algodao (Mf)</div><table class=\"tbl\"><thead><tr><th>Safra</th><th style=\"text-align:right;\">Prod.</th><th style=\"text-align:right;\">Cons.</th><th style=\"text-align:right;\">Est.</th><th style=\"text-align:right;\">E/U%%</th></tr></thead><tbody>"+tabela_estoques(estoques.get("algodao",[]))+"</tbody></table></div></div></div>"
    html+="</div></div>"

    # PRECOS
    html+="<div id=\"tab-precos\" class=\"tc\"><div class=\"wrap\">"
    html+="<div class=\"card\"><div class=\"ct\">Soja - Historico CBOT (USD/bu)</div><div style=\"height:180px;position:relative;margin-bottom:14px;\"><canvas id=\"cSH\"></canvas></div><table class=\"tbl\"><thead><tr><th>Praca</th><th style=\"text-align:right;\">R$/sc</th><th style=\"text-align:right;\">Basis</th></tr></thead><tbody>"+tabela_pracas(prac_soja,ref_pga)+"</tbody></table></div>"
    html+="<div class=\"card\"><div class=\"ct\">Milho - Historico CBOT (USD/bu)</div><div style=\"height:180px;position:relative;margin-bottom:14px;\"><canvas id=\"cMH\"></canvas></div><table class=\"tbl\"><thead><tr><th>Praca</th><th style=\"text-align:right;\">R$/sc</th><th style=\"text-align:right;\">Basis</th></tr></thead><tbody>"+tabela_pracas(prac_milho,ref_cpx)+"</tbody></table></div>"
    html+="<div class=\"card\"><div class=\"ct\">Futuros CBOT</div><div class=\"g2\"><div><div style=\"font-size:12px;font-weight:700;color:#1D9E75;margin-bottom:8px;\">Soja</div><table class=\"tbl\"><thead><tr><th>Venc.</th><th style=\"text-align:right;\">USD/bu</th><th style=\"text-align:right;\">R$/sc</th></tr></thead><tbody>"+tabela_futuros(soja_fu)+"</tbody></table></div><div><div style=\"font-size:12px;font-weight:700;color:#BA7517;margin-bottom:8px;\">Milho</div><table class=\"tbl\"><thead><tr><th>Venc.</th><th style=\"text-align:right;\">USD/bu</th><th style=\"text-align:right;\">R$/sc</th></tr></thead><tbody>"+tabela_futuros(milho_fu)+"</tbody></table></div></div><div style=\"margin-top:14px;height:180px;position:relative;\"><canvas id=\"cSF\"></canvas></div></div>"
    html+="</div></div>"

    # FRETE
    html+="<div id=\"tab-frete\" class=\"tc\"><div class=\"wrap\">"
    html+="<div class=\"card\"><div class=\"ct\">Fretes - Principais Rotas (R$/ton) &#183; "+frete.get("data_ref","Abr/2026")+"</div>"
    html+="<div style=\"font-size:12px;color:#666;margin-bottom:6px;\">Diesel: R$ "+s(frete.get("diesel_rl",6.18))+"/L &#183; Reajuste ANTT: +"+s(frete.get("reajuste_antt_pct",3.2),1)+"%</div>"
    html+="<div style=\"font-size:12px;color:#27500A;margin-bottom:10px;\">&#9660; Clique em uma rota destacada para ver historico de 4 safras</div>"
    html+="<table class=\"tbl\"><thead><tr><th>Rota</th><th style=\"text-align:right;\">R$/ton</th><th style=\"text-align:right;\">Var.</th><th style=\"text-align:right;\">%% soja</th></tr></thead><tbody>"

    for r in frete.get("rotas",[]):
        # extrai chave da origem (primeira palavra antes do espaco)
        origem_parts = r["origem"].split(" ")
        origem_key = origem_parts[0]  # ex: "Sorriso", "Rondonopolis", etc
        pct_soja=round(r["valor"]/float(ref_pga)/16.67*100,1)
        vc="color:#A32D2D;" if r.get("var_pct",3)>3 else "color:#BA7517;"
        safe_key = origem_key.replace(" ","_")
        rid = "fr_"+safe_key

        if origem_key in HIST_FRETE:
            data_attr = " data-rid=\""+rid+"\""
            row_style = "cursor:pointer;"
            tip = "&#9660; historico"
        else:
            data_attr = ""
            row_style = ""
            tip = ""

        html+="<tr class=\"fr-row\" style=\""+row_style+"\""+data_attr+"><td style=\"font-size:12px;font-weight:500;\">"+r["origem"]+" &rarr; "+r["destino"]+"<br><span style=\"font-size:10px;color:#888;\">"+r["modal"]+" <span style=\"color:#3B6D11;\">"+tip+"</span></span></td><td style=\"text-align:right;font-size:14px;font-weight:700;\">R$ "+str(r["valor"])+"/ton</td><td style=\"text-align:right;font-size:11px;"+vc+"\">+"+s(r.get("var_pct","?"),1)+"%</td><td style=\"text-align:right;font-size:11px;color:#888;\">"+str(pct_soja)+"%% soja</td></tr>"

        if origem_key in HIST_FRETE:
            html+="<tr id=\""+rid+"\" class=\"fr-hist\"><td colspan=\"4\" style=\"padding:12px 16px;\"><div id=\""+rid+"_lbl\" style=\"font-size:12px;font-weight:600;color:#1a3a1a;margin-bottom:8px;\"></div><div style=\"position:relative;height:150px;\"><canvas id=\""+rid+"_c\"></canvas></div><div style=\"display:flex;gap:12px;margin-top:6px;font-size:10px;\"><span style=\"display:flex;align-items:center;gap:3px;\"><span style=\"width:10px;height:10px;background:#1D9E75;border-radius:2px;display:inline-block;\"></span>Safra atual</span><span style=\"display:flex;align-items:center;gap:3px;\"><span style=\"width:10px;height:10px;background:#E24B4A;border-radius:2px;display:inline-block;\"></span>Pico historico</span><span style=\"display:flex;align-items:center;gap:3px;\"><span style=\"width:10px;height:10px;background:#9FE1CB;border-radius:2px;display:inline-block;\"></span>Demais safras</span></div></td></tr>"

    html+="</tbody></table></div>"
    html+="<div class=\"card\"><div class=\"ct\">Frete como %% do Preco da Soja</div><div style=\"height:200px;position:relative;\"><canvas id=\"cFrete\"></canvas></div></div>"
    html+="</div></div>"

    # RELACAO DE TROCA
    html+="<div id=\"tab-insumos\" class=\"tc\"><div class=\"wrap\">"
    html+="<div class=\"card\"><div class=\"ct\">Relacao de Troca - Soja/Insumo &#183; Paranagua R$ "+s(ref_pga)+"/sc</div>"
    html+="<div style=\"font-size:12px;color:#27500A;margin-bottom:12px;\">&#9660; Clique em qualquer card para ver historico comparativo das ultimas 3 safras</div>"
    html+="<div class=\"g3\">"

    rt_cfg = [
        ("ureia",    "Ureia (sc/ton)",    rt_soja.get("ureia_sc_ton","?"),    "R$ "+s(insumos.get("ureia_ton",336),0)+"/ton", "#A32D2D"),
        ("map",      "MAP (sc/ton)",       rt_soja.get("map_sc_ton","?"),       "R$ "+s(insumos.get("map_ton",423),0)+"/ton",   "#BA7517"),
        ("kcl",      "KCl (sc/ton)",       rt_soja.get("kcl_sc_ton","?"),       "R$ "+s(insumos.get("kcl_ton",247),0)+"/ton",   "#27500A"),
        ("glifosato","Glifosato (sc/L)",   rt_soja.get("glifosato_sc_l","?"),   "R$ "+s(insumos.get("glifosato_l",18.9),2)+"/L","#27500A"),
        ("diesel",   "Diesel (sc/L)",      rt_soja.get("diesel_sc_l","?"),      "R$ "+s(insumos.get("diesel_l",6.18),2)+"/L",   "#BA7517"),
    ]
    for key,lbl,val,nota,cor in rt_cfg:
        rid2 = "rt_"+key
        html+="<div class=\"rt-card\" data-rid=\""+rid2+"\" data-key=\""+key+"\">"
        html+="<div style=\"font-size:10px;color:#888;text-transform:uppercase;margin-bottom:4px;\">"+lbl+"</div>"
        html+="<div style=\"font-size:22px;font-weight:700;color:"+cor+";\">"+s(val)+"</div>"
        html+="<div style=\"font-size:11px;color:#666;margin-top:3px;\">"+nota+"</div>"
        html+="<div style=\"font-size:10px;color:#888;margin-top:6px;\">&#9660; ver historico 3 safras</div>"
        html+="<div id=\""+rid2+"\" class=\"rt-hist\">"
        html+="<div id=\""+rid2+"_lbl\" style=\"font-size:12px;font-weight:600;color:#1a3a1a;margin-bottom:8px;\"></div>"
        html+="<div style=\"position:relative;height:160px;\"><canvas id=\""+rid2+"_c\"></canvas></div>"
        html+="<div style=\"display:flex;gap:10px;margin-top:6px;font-size:10px;\"><span style=\"display:flex;align-items:center;gap:3px;\"><span style=\"width:8px;height:8px;background:#1D9E75;border-radius:2px;display:inline-block;\"></span>Soja</span><span style=\"display:flex;align-items:center;gap:3px;\"><span style=\"width:8px;height:8px;background:#BA7517;border-radius:2px;display:inline-block;\"></span>Milho</span><span style=\"display:flex;align-items:center;gap:3px;\"><span style=\"width:8px;height:8px;background:#7F77DD;border-radius:2px;display:inline-block;\"></span>Algodao</span><span style=\"color:#aaa;\">* = safra atual</span></div>"
        html+="</div></div>"

    html+="<div style=\"border:1px solid #eee;border-radius:8px;padding:12px;\"><div style=\"font-size:10px;color:#888;text-transform:uppercase;margin-bottom:6px;\">Como interpretar</div><div style=\"font-size:12px;color:#555;line-height:1.7;\">Sacas de soja equivalentes a 1 unidade do insumo. <strong>Quanto menor, melhor</strong> para o produtor.</div><div style=\"font-size:11px;color:#888;margin-top:8px;\">Media historica ureia: 2.1 sc/ton &#183; Atual: "+s(rt_soja.get("ureia_sc_ton","?"))+" sc/ton</div></div>"
    html+="</div></div>"
    html+="<div class=\"card\"><div class=\"ct\">Custo de Producao - Soja Safra 26/27 (R$/ha)</div><table class=\"tbl\"><tr><th>Componente</th><th style=\"text-align:right;\">MT</th><th style=\"text-align:right;\">GO</th><th style=\"text-align:right;\">PR</th><th style=\"text-align:right;\">MG Tri.</th></tr><tr><td>Fertilizantes</td><td style=\"text-align:right;\">1.420</td><td style=\"text-align:right;\">1.380</td><td style=\"text-align:right;\">1.280</td><td style=\"text-align:right;\">1.350</td></tr><tr><td>Defensivos</td><td style=\"text-align:right;\">980</td><td style=\"text-align:right;\">920</td><td style=\"text-align:right;\">860</td><td style=\"text-align:right;\">900</td></tr><tr><td>Sementes</td><td style=\"text-align:right;\">420</td><td style=\"text-align:right;\">410</td><td style=\"text-align:right;\">390</td><td style=\"text-align:right;\">400</td></tr><tr><td>Operacoes</td><td style=\"text-align:right;\">680</td><td style=\"text-align:right;\">640</td><td style=\"text-align:right;\">580</td><td style=\"text-align:right;\">620</td></tr><tr><td>Frete interno</td><td style=\"text-align:right;\">340</td><td style=\"text-align:right;\">220</td><td style=\"text-align:right;\">90</td><td style=\"text-align:right;\">160</td></tr><tr><td>Outros</td><td style=\"text-align:right;\">580</td><td style=\"text-align:right;\">540</td><td style=\"text-align:right;\">490</td><td style=\"text-align:right;\">520</td></tr><tr style=\"background:#f8fff4;\"><td><b>TOTAL</b></td><td style=\"text-align:right;\"><b>4.420</b></td><td style=\"text-align:right;\"><b>4.110</b></td><td style=\"text-align:right;\"><b>3.690</b></td><td style=\"text-align:right;\"><b>3.950</b></td></tr><tr style=\"background:#fff8e6;\"><td><i>Break-even sc/ha</i></td><td style=\"text-align:right;color:#A32D2D;\"><b>"+s(4420/float(ref_pga),1)+"</b></td><td style=\"text-align:right;color:#BA7517;\"><b>"+s(4110/float(ref_pga),1)+"</b></td><td style=\"text-align:right;color:#27500A;\"><b>"+s(3690/float(ref_pga),1)+"</b></td><td style=\"text-align:right;color:#BA7517;\"><b>"+s(3950/float(ref_pga),1)+"</b></td></tr></table></div>"
    html+="</div></div>"

    # ALGODAO
    html+="<div id=\"tab-algodao\" class=\"tc\"><div class=\"wrap\">"
    html+="<div class=\"card\"><div class=\"ct\">Algodao - Visao Geral</div><div class=\"g4\"><div class=\"met\"><div class=\"ml\">CEPEA BR (R$/@)</div><div class=\"mv\">R$ "+s(ref_alg)+"</div></div><div class=\"met\"><div class=\"ml\">ICE (USD/lb)</div><div class=\"mv\">USD "+s(alg_ice.get("preco_usd_lb","?"),4)+"</div></div><div class=\"met\"><div class=\"ml\">Producao 25/26</div><div class=\"mv\">"+s(alg_br.get("producao_mfardos","?"),1)+" Mf</div></div><div class=\"met\"><div class=\"ml\">Colheita</div><div class=\"mv\" style=\"color:#1D9E75;\">"+str(alg_br.get("colheita_pct","?"))+"%</div></div></div></div>"
    html+="<div class=\"card\"><div class=\"ct\">Historico ICE (USD/lb)</div><div style=\"height:180px;position:relative;\"><canvas id=\"cAH\"></canvas></div></div>"
    html+="<div class=\"card\"><div class=\"ct\">Producao por Estado</div><table class=\"tbl\"><thead><tr><th>Estado</th><th style=\"text-align:right;\">Area(Mha)</th><th style=\"text-align:right;\">Prod.(Mf)</th><th style=\"text-align:right;\">@/ha</th><th style=\"text-align:right;\">Colheita</th><th style=\"text-align:right;\">vs 24/25</th></tr></thead><tbody>"+tabela_estado_algodao(alg_br.get("por_estado",{}))+"</tbody></table></div>"
    html+="</div></div>"

    # HEDGE
    html+="<div id=\"tab-hedge\" class=\"tc\"><div class=\"wrap\">"
    html+="<div class=\"card\"><div style=\"display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;\">"+badge_risco(nivel)+"<span style=\"font-size:13px;color:#666;\">"+tc_+"</span></div><p style=\"font-size:14px;color:#333;line-height:1.8;\">"+just+"</p></div>"
    html+="<div class=\"card\"><div class=\"ct\">Recomendacao de Hedge</div><div class=\"g3\"><div class=\"hbox\"><div class=\"hlbl\">Soja safra 26/27</div><div class=\"hpct\">"+str(hs)+"%</div><div class=\"hsub\">da producao estimada</div></div><div class=\"hbox\"><div class=\"hlbl\">Milho 2a safra 27</div><div class=\"hpct\">"+str(hm)+"%</div><div class=\"hsub\">da producao estimada</div></div><div class=\"hbox\"><div class=\"hlbl\">Algodao safra 26/27</div><div class=\"hpct\">35%</div><div class=\"hsub\">ICE Dez/26 + NDF cambio</div></div></div></div>"
    html+="<div class=\"card\"><div class=\"ct\">O Que Fazer Agora</div><ul style=\"padding-left:20px;\">"+acoes_li+"</ul></div>"
    html+="<div class=\"card\" style=\"background:#E6F1FB;\"><div class=\"ct\" style=\"color:#0C447C;\">Proximo Evento</div><p style=\"font-size:15px;font-weight:600;color:#042C53;\">"+pe+"</p><p style=\"font-size:13px;color:#185FA5;margin-top:4px;\">"+pd_+"</p></div>"
    html+="<p style=\"text-align:center;font-size:11px;color:#aaa;padding-bottom:24px;\">Gerado automaticamente &#183; Claude API + GitHub Actions &#183; "+dt+"</p>"
    html+="</div></div>"

    # SCRIPTS - todos os dados em variaveis JS globais, sem acentos em strings JS
    gc="rgba(0,0,0,0.05)"; tc2="#888"
    html+="<script>\n"
    html+=js_rt+"\n"
    html+=js_fr+"\n"
    html+="var _rtCharts={}, _frCharts={};\n"

    html+="function st(n,el){document.querySelectorAll('.tc').forEach(function(e){e.classList.remove('active');});document.querySelectorAll('.tab').forEach(function(e){e.classList.remove('active');});document.getElementById('tab-'+n).classList.add('active');el.classList.add('active');}\n"
    html+="function sr(n,el){var ids=['soja','milho','algodao','ms','mm','ma'];ids.forEach(function(c){var e=document.getElementById('sr-'+c);if(e)e.style.display=c===n?'':'none';});document.querySelectorAll('.rtab').forEach(function(b){b.classList.remove('active');});el.classList.add('active');}\n"


    # Graficos estaticos
    html+="new Chart(document.getElementById('cSH'),{type:'line',data:{labels:"+hl(hist_soja)+",datasets:[{label:'Soja CBOT',data:"+hds(hist_soja)+",borderColor:'#1D9E75',backgroundColor:'rgba(29,158,117,0.07)',fill:true,tension:0.3,pointRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'"+tc2+"',font:{size:10}},grid:{color:'"+gc+"'}},y:{ticks:{color:'"+tc2+"',callback:function(v){return '$'+v.toFixed(2);}},grid:{color:'"+gc+"'}}}}});\n"
    html+="new Chart(document.getElementById('cMH'),{type:'line',data:{labels:"+hl(hist_milho)+",datasets:[{label:'Milho CBOT',data:"+hdm(hist_milho)+",borderColor:'#BA7517',backgroundColor:'rgba(186,117,23,0.07)',fill:true,tension:0.3,pointRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'"+tc2+"',font:{size:10}},grid:{color:'"+gc+"'}},y:{ticks:{color:'"+tc2+"',callback:function(v){return '$'+v.toFixed(2);}},grid:{color:'"+gc+"'}}}}});\n"
    html+="new Chart(document.getElementById('cAH'),{type:'line',data:{labels:"+hl(hist_alg)+",datasets:[{label:'Algodao ICE',data:"+hda(hist_alg)+",borderColor:'#7F77DD',backgroundColor:'rgba(127,119,221,0.07)',fill:true,tension:0.3,pointRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'"+tc2+"',font:{size:10}},grid:{color:'"+gc+"'}},y:{ticks:{color:'"+tc2+"',callback:function(v){return '$'+v.toFixed(4);}},grid:{color:'"+gc+"'}}}}});\n"
    html+="new Chart(document.getElementById('cSF'),{type:'line',data:{labels:"+sfl+",datasets:[{label:'Soja futuros',data:"+sfd+",borderColor:'#1D9E75',backgroundColor:'rgba(29,158,117,0.08)',fill:true,tension:0.3,pointRadius:5,pointBackgroundColor:'#1D9E75'}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'"+tc2+"'},grid:{color:'"+gc+"'}},y:{ticks:{color:'"+tc2+"',callback:function(v){return '$'+v.toFixed(2);}},grid:{color:'"+gc+"'}}}}});\n"
    html+="new Chart(document.getElementById('cFrete'),{type:'bar',data:{labels:['Cascavel PR','Uberlandia MG','Rio Verde GO','Rondonopolis MT','Sorriso MT','Barreiras BA'],datasets:[{label:'Frete pct soja',data:[4.0,6.9,10.6,16.1,18.3,13.1],backgroundColor:['#9FE1CB','#9FE1CB','#FAC775','#E24B4A','#E24B4A','#EF9F27']}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'"+tc2+"',font:{size:10}},grid:{color:'"+gc+"'}},y:{ticks:{color:'"+tc2+"',callback:function(v){return v+'%';}},grid:{color:'"+gc+"'}}}}});\n"

    # Event delegation - zero inline onclick, works with any text content
    html+="""
document.addEventListener('click', function(e) {
  var rtCard = e.target.closest('.rt-card');
  if (rtCard) {
    var rid = rtCard.getAttribute('data-rid');
    var key = rtCard.getAttribute('data-key');
    if (!rid || !key) return;
    var box = document.getElementById(rid);
    if (!box) return;
    var showing = box.style.display === 'block';
    box.style.display = showing ? 'none' : 'block';
    if (!showing && !_rtCharts[rid]) {
      var d = RT_DATA[key];
      if (!d) return;
      var lbl = document.getElementById(rid+'_lbl');
      if (lbl) lbl.textContent = key + ' - historico 4 safras';
      var ctx = document.getElementById(rid+'_c');
      if (!ctx) return;
      _rtCharts[rid] = new Chart(ctx, {
        type: 'bar',
        data: { labels: RT_LABELS,
          datasets: [
            {label:'Soja',   data:d.soja,    backgroundColor:['#9FE1CB','#9FE1CB','#9FE1CB','#1D9E75']},
            {label:'Milho',  data:d.milho,   backgroundColor:['#FAC775','#FAC775','#FAC775','#BA7517']},
            {label:'Algodao',data:d.algodao, backgroundColor:['#AFA9EC','#AFA9EC','#AFA9EC','#7F77DD']}
          ]
        },
        options:{responsive:true,maintainAspectRatio:false,
          plugins:{legend:{position:'bottom',labels:{font:{size:10},color:'#888'}}},
          scales:{x:{ticks:{color:'#888',font:{size:10}},grid:{color:'rgba(0,0,0,0.05)'}},
                  y:{ticks:{color:'#888',font:{size:10}},grid:{color:'rgba(0,0,0,0.05)'}}}}
      });
    }
    return;
  }
  var frRow = e.target.closest('.fr-row');
  if (frRow) {
    var rid2 = frRow.getAttribute('data-rid');
    if (!rid2) return;
    var row = document.getElementById(rid2);
    if (!row) return;
    var showing2 = row.style.display === 'table-row';
    row.style.display = showing2 ? 'none' : 'table-row';
    if (!showing2 && !_frCharts[rid2]) {
      var key2 = rid2.replace('fr_','');
      var d2 = FR_DATA[key2];
      if (!d2) return;
      var lbl2 = document.getElementById(rid2+'_lbl');
      if (lbl2) lbl2.textContent = key2 + ' - historico R/ton por safra';
      var ctx2 = document.getElementById(rid2+'_c');
      if (!ctx2) return;
      _frCharts[rid2] = new Chart(ctx2, {
        type: 'bar',
        data: {labels: FR_LABELS, datasets:[{label:'R/ton',data:d2.values,backgroundColor:d2.colors}]},
        options:{responsive:true,maintainAspectRatio:false,
          plugins:{legend:{display:false}},
          scales:{x:{ticks:{color:'#888',font:{size:11}},grid:{color:'rgba(0,0,0,0.05)'}},
                  y:{ticks:{color:'#888',font:{size:11},callback:function(v){return 'R$'+v;}},
                     grid:{color:'rgba(0,0,0,0.05)'},suggestedMin:d2.min}}}
      });
    }
  }
});
"""
    html+="</script></body></html>"
    return html

def main():
    print("\nGerando dashboard v3 corrigido...")
    with open(ANALISE_PATH, encoding="utf-8") as f:
        analise=json.load(f)
    with open(DATA_PATH, encoding="utf-8") as f:
        dados=json.load(f)
    html=gerar(analise,dados)
    with open(OUTPUT_PATH,"w",encoding="utf-8") as f:
        f.write(html)
    print("Dashboard salvo: "+OUTPUT_PATH+"\nConcluido!\n")

if __name__=="__main__":
    main()
