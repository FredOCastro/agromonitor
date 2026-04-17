"""
fetch_data.py - Coleta todos os dados dinamicos do Agro Monitor BR v2
APIs: NOAA (ENSO), Open-Meteo (clima), Bacen (cambio),
      Yahoo Finance (precos graos + algodao + futuros CBOT)
"""

import json
import os
import requests
from datetime import datetime, date, timedelta

BASE_DIR = os.path.dirname(__file__)

def get(url, params=None, headers=None, timeout=15):
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("  [ERRO] " + url[:60] + ": " + str(e))
        return None


# ── 1. ENSO / ONI ─────────────────────────────────────────────

def fetch_enso():
    print("Buscando ENSO (NOAA)...")
    try:
        r = requests.get("https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt", timeout=15)
        dados = []
        for linha in r.text.strip().split("\n"):
            p = linha.split()
            if len(p) >= 3:
                try:
                    dados.append({"periodo": p[0], "ano": int(p[1]), "oni": float(p[2])})
                except:
                    continue
        if not dados:
            raise ValueError("Sem dados")
        atual = dados[-1]
        anterior = dados[-2] if len(dados) > 1 else atual
        oni = atual["oni"]
        if oni >= 1.5:   status = "El Nino Forte"
        elif oni >= 0.5: status = "El Nino Fraco/Moderado"
        elif oni <= -1.5: status = "La Nina Forte"
        elif oni <= -0.5: status = "La Nina Fraca/Moderada"
        else:             status = "Neutro"
        return {
            "oni_atual": oni,
            "oni_anterior": anterior["oni"],
            "periodo": atual["periodo"],
            "status": status,
            "tendencia": "subindo" if oni > anterior["oni"] else "caindo",
            "fonte": "NOAA CPC"
        }
    except Exception as e:
        print("  [FALLBACK] ENSO: " + str(e))
        return {"oni_atual": 0.4, "oni_anterior": 0.3, "periodo": "MAM 2026",
                "status": "Neutro", "tendencia": "subindo", "fonte": "NOAA CPC (fallback)"}


# ── 2. CAMBIO ─────────────────────────────────────────────────

def fetch_cambio():
    print("Buscando cambio (Bacen)...")
    for delta in [0, 1, 2, 3]:
        d = (date.today() - timedelta(days=delta)).strftime("%m-%d-%Y")
        url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
               "CotacaoDolarDia(dataCotacao=@d)?@d='" + d + "'&$format=json")
        data = get(url)
        if data and data.get("value"):
            c = data["value"][-1]
            return {"usd_brl": round(c["cotacaoVenda"], 4), "data": d, "fonte": "BCB"}
    return {"usd_brl": 5.95, "data": str(date.today()), "fonte": "BCB (fallback)"}


# ── 3. PRECOS VIA YAHOO FINANCE ───────────────────────────────

def yahoo_preco(ticker):
    """Busca preco atual de um ticker no Yahoo Finance."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        meta = data["chart"]["result"][0]["meta"]
        return meta.get("regularMarketPrice", None)
    except:
        return None

def yahoo_historico(ticker, dias=180):
    """Busca historico de precos para graficos."""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker
    headers = {"User-Agent": "Mozilla/5.0"}
    periodo_fim = int(datetime.now().timestamp())
    periodo_ini = int((datetime.now() - timedelta(days=dias)).timestamp())
    try:
        r = requests.get(url, headers=headers, timeout=15,
                        params={"period1": periodo_ini, "period2": periodo_fim,
                                "interval": "1wk"})
        data = r.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        hist = []
        for t, c in zip(timestamps, closes):
            if c is not None:
                hist.append({
                    "data": datetime.fromtimestamp(t).strftime("%b/%y"),
                    "preco": round(c, 2)
                })
        return hist[-12:] if len(hist) > 12 else hist
    except:
        return []

def fetch_precos_futuros(usd_brl):
    print("Buscando precos futuros (Yahoo Finance)...")

    # Tickers CBOT
    tickers_soja = {
        "Mai/26": "ZSK26.CBT", "Jul/26": "ZSN26.CBT",
        "Set/26": "ZSU26.CBT", "Nov/26": "ZSX26.CBT", "Jan/27": "ZSF27.CBT"
    }
    tickers_milho = {
        "Mai/26": "ZCK26.CBT", "Jul/26": "ZCN26.CBT",
        "Set/26": "ZCU26.CBT", "Dez/26": "ZCZ26.CBT", "Mar/27": "ZCH27.CBT"
    }

    # Futuros soja
    soja_futuros = {}
    soja_spot = None
    for venc, ticker in tickers_soja.items():
        p = yahoo_preco(ticker)
        if p:
            p_usd = round(p / 100, 2)  # cents -> USD/bu
            p_brl = round(p_usd * 2.2 * usd_brl, 2)  # USD/bu -> R$/sc 60kg
            soja_futuros[venc] = {"usd_bu": p_usd, "brl_sc": p_brl}
            if soja_spot is None:
                soja_spot = {"preco_usd_bushel": p_usd, "preco_brl_saca": p_brl, "ticker": ticker}

    # Fallback soja
    if not soja_futuros:
        base = 10.42
        for i, venc in enumerate(tickers_soja.keys()):
            p_usd = round(base + i * 0.13, 2)
            soja_futuros[venc] = {"usd_bu": p_usd, "brl_sc": round(p_usd * 2.2 * usd_brl, 2)}
        soja_spot = {"preco_usd_bushel": base, "preco_brl_saca": round(base * 2.2 * usd_brl, 2), "ticker": "ZS=F"}

    # Futuros milho
    milho_futuros = {}
    milho_spot = None
    for venc, ticker in tickers_milho.items():
        p = yahoo_preco(ticker)
        if p:
            p_usd = round(p / 100, 2)
            p_brl = round(p_usd * 2.36 * usd_brl, 2)
            milho_futuros[venc] = {"usd_bu": p_usd, "brl_sc": p_brl}
            if milho_spot is None:
                milho_spot = {"preco_usd_bushel": p_usd, "preco_brl_saca": p_brl, "ticker": ticker}

    if not milho_futuros:
        base = 4.58
        for i, venc in enumerate(tickers_milho.keys()):
            p_usd = round(base + i * 0.065, 2)
            milho_futuros[venc] = {"usd_bu": p_usd, "brl_sc": round(p_usd * 2.36 * usd_brl, 2)}
        milho_spot = {"preco_usd_bushel": base, "preco_brl_saca": round(base * 2.36 * usd_brl, 2), "ticker": "ZC=F"}

    # Algodao ICE
    algodao_spot = None
    p_alg = yahoo_preco("CT=F")
    if p_alg:
        # ICE em cents/lb -> R$/@  (1@ = 15kg, 1lb = 0.453kg -> 1@ = 33.07lb)
        p_usd_lb = round(p_alg / 100, 4)
        p_brl_arr = round(p_usd_lb * 33.07 * usd_brl, 2)
        algodao_spot = {"preco_usd_lb": p_usd_lb, "preco_brl_arroba": p_brl_arr, "ticker": "CT=F"}
    else:
        algodao_spot = {"preco_usd_lb": 0.68, "preco_brl_arroba": round(0.68 * 33.07 * usd_brl, 2), "ticker": "CT=F (fallback)"}

    # Historico para graficos
    print("  Buscando historico soja...")
    hist_soja = yahoo_historico("ZS=F", dias=200)
    print("  Buscando historico milho...")
    hist_milho = yahoo_historico("ZC=F", dias=200)
    print("  Buscando historico algodao...")
    hist_algodao = yahoo_historico("CT=F", dias=200)

    return {
        "soja_cbot": soja_spot,
        "milho_cbot": milho_spot,
        "algodao_ice": algodao_spot,
        "soja_futuros": soja_futuros,
        "milho_futuros": milho_futuros,
        "cambio_usd_brl": usd_brl,
        "hist_soja": hist_soja,
        "hist_milho": hist_milho,
        "hist_algodao": hist_algodao
    }


# ── 4. PRECOS PRAÇAS — ESTIMATIVA POR BASIS ───────────────────

def fetch_precos_pracas(soja_cbot_brl, milho_cbot_brl, algodao_brl_arr):
    """
    Estima precos nas principais pracas usando basis historico.
    Basis = diferenca media entre preco local e referencia CBOT/CEPEA.
    Atualizado mensalmente com dados CEPEA/ESALQ.
    """
    print("Calculando precos por praca (basis)...")

    # Basis soja vs Paranagua (R$/sc) - media historica
    basis_soja = {
        "Paranagua":     0.00,
        "Rondonopolis": -7.10,
        "Rio Verde":    -8.70,
        "Cascavel":     -4.30,
        "Uberlandia":  -11.00,
        "Passo Fundo":  -2.70,
        "Barreiras":    -9.50,
        "Sorriso":      -8.20,
    }

    # Basis milho vs Campinas (R$/sc)
    basis_milho = {
        "Campinas":      0.00,
        "Rondonopolis": -7.20,
        "Rio Verde":    -8.60,
        "Cascavel":     -4.90,
        "Uberlandia":   -6.40,
        "Maringa":      -3.80,
    }

    # Basis algodao vs CEPEA BR (R$/@)
    basis_algodao = {
        "CEPEA BR":    0.00,
        "Cuiaba":     -2.40,
        "Barreiras":  -1.70,
        "Primavera":  -3.80,
    }

    # Referencia: Paranagua = CBOT convertido + premio exportacao (~R$8/sc)
    ref_soja_pga = round(soja_cbot_brl + 8.0, 2)
    ref_milho_cpx = round(milho_cbot_brl * 1.05, 2)  # premio consumo interno
    ref_alg_br = round(algodao_brl_arr, 2)

    pracas_soja = {}
    for praca, basis in basis_soja.items():
        pracas_soja[praca] = round(ref_soja_pga + basis, 2)

    pracas_milho = {}
    for praca, basis in basis_milho.items():
        pracas_milho[praca] = round(ref_milho_cpx + basis, 2)

    pracas_algodao = {}
    for praca, basis in basis_algodao.items():
        pracas_algodao[praca] = round(ref_alg_br + basis, 2)

    return {
        "soja": pracas_soja,
        "milho": pracas_milho,
        "algodao": pracas_algodao,
        "ref_soja_paranagua": ref_soja_pga,
        "ref_milho_campinas": ref_milho_cpx,
        "ref_algodao_br": ref_alg_br
    }


# ── 5. CLIMA REGIONAL POR ESTADO ──────────────────────────────

def fetch_clima_estados():
    print("Buscando clima por estado (Open-Meteo)...")

    estados = {
        "MT": {"lat": -12.64, "lon": -55.42, "nome": "Mato Grosso (Sorriso)"},
        "GO": {"lat": -17.80, "lon": -50.92, "nome": "Goias (Rio Verde)"},
        "MS": {"lat": -20.46, "lon": -54.61, "nome": "Mato Grosso do Sul"},
        "MG": {"lat": -19.59, "lon": -46.94, "nome": "Minas Gerais (Araxa)"},
        "PR": {"lat": -24.89, "lon": -53.46, "nome": "Parana (Cascavel)"},
        "RS": {"lat": -28.26, "lon": -52.41, "nome": "Rio Grande do Sul"},
        "BA": {"lat": -12.15, "lon": -44.99, "nome": "Bahia (Barreiras)"},
        "MA": {"lat": -5.80,  "lon": -47.40, "nome": "Maranhao (Balsas)"},
    }

    resultado = {}
    for sigla, info in estados.items():
        data = get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": info["lat"], "longitude": info["lon"],
            "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
            "timezone": "America/Sao_Paulo", "forecast_days": 14,
        })
        if data and "daily" in data:
            p7  = sum(p or 0 for p in data["daily"]["precipitation_sum"][:7])
            p14 = sum(p or 0 for p in data["daily"]["precipitation_sum"][:14])
            tmax = max((t for t in data["daily"]["temperature_2m_max"][:7] if t), default=0)
            tmin = min((t for t in data["daily"]["temperature_2m_min"][:7] if t), default=0)
            resultado[sigla] = {
                "nome": info["nome"],
                "precip_7d_mm": round(p7, 1),
                "precip_14d_mm": round(p14, 1),
                "temp_max": round(tmax, 1),
                "temp_min": round(tmin, 1),
                "alerta_seca": p7 < 8,
                "alerta_excesso": p7 > 100,
            }
        else:
            resultado[sigla] = {"nome": info["nome"], "erro": "sem dados"}
    return resultado


# ── 6. RELACAO DE TROCA ────────────────────────────────────────

def fetch_relacao_troca(soja_pga, milho_cpx, algodao_br):
    """
    Calcula relacao de troca insumos.
    Precos de insumos atualizados mensalmente (ANDA/CEPEA).
    """
    print("Calculando relacao de troca...")

    insumos = {
        "ureia_ton":    336.0,   # R$/ton (45% N)
        "map_ton":      423.0,   # R$/ton (11-52-0)
        "kcl_ton":      247.0,   # R$/ton (60% K2O)
        "ssp_ton":      374.0,   # R$/ton
        "glifosato_l":   18.9,   # R$/L
        "diesel_l":       6.18,  # R$/L
    }

    def rt(preco_insumo, preco_grao):
        return round(preco_insumo / preco_grao, 2) if preco_grao > 0 else 0

    return {
        "precos_insumos": insumos,
        "soja_paranagua": soja_pga,
        "milho_campinas": milho_cpx,
        "algodao_br": algodao_br,
        "relacao_soja": {
            "ureia_sc_ton":     rt(insumos["ureia_ton"], soja_pga),
            "map_sc_ton":       rt(insumos["map_ton"], soja_pga),
            "kcl_sc_ton":       rt(insumos["kcl_ton"], soja_pga),
            "ssp_sc_ton":       rt(insumos["ssp_ton"], soja_pga),
            "glifosato_sc_l":   rt(insumos["glifosato_l"], soja_pga),
            "diesel_sc_l":      rt(insumos["diesel_l"], soja_pga),
        },
        "relacao_milho": {
            "ureia_sc_ton":     rt(insumos["ureia_ton"], milho_cpx),
            "map_sc_ton":       rt(insumos["map_ton"], milho_cpx),
            "kcl_sc_ton":       rt(insumos["kcl_ton"], milho_cpx),
        },
        "relacao_algodao": {
            "ureia_arr_ton":    rt(insumos["ureia_ton"], algodao_br),
            "map_arr_ton":      rt(insumos["map_ton"], algodao_br),
            "kcl_arr_ton":      rt(insumos["kcl_ton"], algodao_br),
        },
        "fonte": "ANDA/CEPEA - Atualizar mensalmente",
        "data_ref": datetime.now().strftime("%m/%Y")
    }


# ── 7. SAFRAS ─────────────────────────────────────────────────

def fetch_safras():
    """Dados CONAB/IMEA - atualizados mensalmente."""
    print("Carregando dados de safra (CONAB/IMEA)...")
    return {
        "referencia": "CONAB Abril/2026 + IMEA",
        "proxima_atualizacao": "Maio/2026",
        "soja_br": {
            "area_mha": 45.8, "producao_mt": 167.0,
            "produtividade_kgha": 3647, "colheita_pct": 94,
            "vs_safra_anterior_pct": 2.0,
            "por_estado": {
                "MT": {"area": 12.1, "prod": 43.8, "produt": 3620, "colheita": 98, "var": 3},
                "PR": {"area": 5.8,  "prod": 22.1, "produt": 3810, "colheita": 97, "var": 2},
                "RS": {"area": 6.7,  "prod": 22.4, "produt": 3343, "colheita": 92, "var": -3},
                "GO": {"area": 4.2,  "prod": 15.2, "produt": 3619, "colheita": 95, "var": 1},
                "MS": {"area": 3.2,  "prod": 11.1, "produt": 3469, "colheita": 99, "var": 2},
                "MG": {"area": 1.7,  "prod": 5.8,  "produt": 3412, "colheita": 88, "var": -2},
                "MATOPIBA": {"area": 6.8, "prod": 24.6, "produt": 3618, "colheita": 89, "var": 4},
            }
        },
        "milho_br": {
            "area_mha": 22.4, "producao_mt": 137.0,
            "produtividade_kgha": 6116, "colheita_2a_pct": 68,
            "vs_safra_anterior_pct": -8.0,
            "por_estado": {
                "MT": {"prod_1a": 2.8, "prod_2a": 33.2, "total": 36.0, "colheita_2a": 72, "var": -9},
                "PR": {"prod_1a": 8.4, "prod_2a": 11.2, "total": 19.6, "colheita_2a": 61, "var": -4},
                "GO": {"prod_1a": 1.2, "prod_2a": 13.8, "total": 15.0, "colheita_2a": 65, "var": -7},
                "MS": {"prod_1a": 0.8, "prod_2a": 9.4,  "total": 10.2, "colheita_2a": 70, "var": -5},
                "MG": {"prod_1a": 3.2, "prod_2a": 7.1,  "total": 10.3, "colheita_2a": 58, "var": -8},
            }
        },
        "algodao_br": {
            "area_mha": 2.54, "producao_mfardos": 17.78,
            "produtividade_arrha": 210, "colheita_pct": 72,
            "vs_safra_anterior_pct": 3.0,
            "por_estado": {
                "MT": {"area": 1.18, "prod": 8.92, "produt": 228, "colheita": 78, "var": 3},
                "BA": {"area": 0.82, "prod": 5.12, "produt": 187, "colheita": 65, "var": 2},
                "GO": {"area": 0.28, "prod": 1.98, "produt": 212, "colheita": 71, "var": 4},
                "MS": {"area": 0.18, "prod": 1.24, "produt": 207, "colheita": 82, "var": 0},
                "MA": {"area": 0.08, "prod": 0.52, "produt": 195, "colheita": 58, "var": 5},
            }
        },
        "mundial": {
            "soja_mt": {
                "Brasil":    {"prod_2324": 153, "prod_2425": 163, "prod_2526": 167, "proj_2627": 155},
                "EUA":       {"prod_2324": 113, "prod_2425": 120, "prod_2526": 121, "proj_2627": 122},
                "Argentina": {"prod_2324": 48,  "prod_2425": 50,  "prod_2526": 52,  "proj_2627": 50},
                "China":     {"prod_2324": 21,  "prod_2425": 21,  "prod_2526": 21,  "proj_2627": 22},
                "Mundo":     {"prod_2324": 396, "prod_2425": 421, "prod_2526": 426, "proj_2627": 412},
            },
            "milho_mt": {
                "EUA":       {"prod_2324": 390, "prod_2425": 382, "prod_2526": 394, "proj_2627": 390},
                "China":     {"prod_2324": 277, "prod_2425": 295, "prod_2526": 298, "proj_2627": 300},
                "Brasil":    {"prod_2324": 127, "prod_2425": 149, "prod_2526": 137, "proj_2627": 120},
                "Argentina": {"prod_2324": 55,  "prod_2425": 50,  "prod_2526": 50,  "proj_2627": 46},
                "Mundo":     {"prod_2324": 1234,"prod_2425": 1226,"prod_2526": 1241,"proj_2627": 1220},
            },
            "algodao_mf": {
                "China":     {"prod_2324": 27.4,"prod_2425": 28.0,"prod_2526": 28.5,"proj_2627": 28.0},
                "India":     {"prod_2324": 24.5,"prod_2425": 23.5,"prod_2526": 23.0,"proj_2627": 23.5},
                "EUA":       {"prod_2324": 12.5,"prod_2425": 14.3,"prod_2526": 15.0,"proj_2627": 14.5},
                "Brasil":    {"prod_2324": 16.8,"prod_2425": 17.2,"prod_2526": 17.8,"proj_2627": 16.5},
                "Mundo":     {"prod_2324": 114, "prod_2425": 117, "prod_2526": 120, "proj_2627": 117},
            },
            "estoques": {
                "soja":    [{"safra":"23/24","prod":396,"cons":371,"est":114,"eu":30.7},
                            {"safra":"24/25","prod":421,"cons":385,"est":124,"eu":32.2},
                            {"safra":"25/26","prod":426,"cons":392,"est":128,"eu":32.7},
                            {"safra":"26/27*","prod":412,"cons":398,"est":112,"eu":28.1}],
                "milho":   [{"safra":"23/24","prod":1234,"cons":1211,"est":319,"eu":26.4},
                            {"safra":"24/25","prod":1226,"cons":1228,"est":317,"eu":25.8},
                            {"safra":"25/26","prod":1241,"cons":1235,"est":322,"eu":26.1},
                            {"safra":"26/27*","prod":1220,"cons":1240,"est":302,"eu":24.4}],
                "algodao": [{"safra":"23/24","prod":113.8,"cons":111.2,"est":83.4,"eu":75.0},
                            {"safra":"24/25","prod":117.4,"cons":113.5,"est":87.3,"eu":76.9},
                            {"safra":"25/26","prod":120.1,"cons":115.8,"est":91.6,"eu":79.1},
                            {"safra":"26/27*","prod":117.0,"cons":116.5,"est":88.0,"eu":75.5}],
            }
        }
    }


# ── 8. FRETE ──────────────────────────────────────────────────

def fetch_frete(usd_brl):
    """Tabela ANTT - atualizar mensalmente."""
    print("Carregando tabela de fretes (ANTT)...")
    rotas = [
        {"origem": "Sorriso MT",     "destino": "Paranagua PR", "modal": "rodoviario", "valor": 248, "var_pct": 3.2},
        {"origem": "Rondonopolis MT","destino": "Santos SP",    "modal": "rodoviario", "valor": 218, "var_pct": 3.2},
        {"origem": "Rio Verde GO",   "destino": "Santos SP",    "modal": "rodoviario", "valor": 144, "var_pct": 2.8},
        {"origem": "Rio Verde GO",   "destino": "Paranagua PR", "modal": "rodoviario", "valor": 154, "var_pct": 3.0},
        {"origem": "Uberlandia MG",  "destino": "Santos SP",    "modal": "rodoviario", "valor": 94,  "var_pct": 2.5},
        {"origem": "Barreiras BA",   "destino": "Santos SP",    "modal": "rodoviario", "valor": 178, "var_pct": 3.5},
        {"origem": "Cascavel PR",    "destino": "Paranagua PR", "modal": "rodoviario", "valor": 54,  "var_pct": 2.1},
        {"origem": "MT/GO",          "destino": "Santos SP",    "modal": "ferrovia VLI","valor": 124, "var_pct": 1.8},
        {"origem": "Rondonopolis MT","destino": "Santos SP",    "modal": "ferrovia Rumo","valor": 108,"var_pct": 1.5},
    ]
    return {
        "rotas": rotas,
        "diesel_rl": 6.18,
        "reajuste_antt_pct": 3.2,
        "data_ref": "Abril/2026",
        "fonte": "ANTT/IMEA"
    }


# ── MAIN ──────────────────────────────────────────────────────

def main():
    print("\n" + "="*55)
    print("AGRO MONITOR BR v2 - Coleta de dados")
    print("Data/hora: " + datetime.now().strftime("%d/%m/%Y %H:%M"))
    print("="*55 + "\n")

    cambio  = fetch_cambio()
    usd_brl = cambio["usd_brl"]

    enso    = fetch_enso()
    precos  = fetch_precos_futuros(usd_brl)
    clima   = fetch_clima_estados()
    safras  = fetch_safras()
    frete   = fetch_frete(usd_brl)

    soja_pga  = precos["soja_cbot"]["preco_brl_saca"] + 8.0 if precos["soja_cbot"] else 135.0
    milho_cpx = precos["milho_cbot"]["preco_brl_saca"] * 1.05 if precos["milho_cbot"] else 68.0
    alg_br    = precos["algodao_ice"]["preco_brl_arroba"] if precos["algodao_ice"] else 115.0

    pracas   = fetch_precos_pracas(soja_pga, milho_cpx, alg_br)
    rt       = fetch_relacao_troca(soja_pga, milho_cpx, alg_br)

    dados = {
        "timestamp": datetime.now().isoformat(),
        "data_coleta": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "cambio": cambio,
        "enso": enso,
        "precos": precos,
        "pracas": pracas,
        "clima_estados": clima,
        "safras": safras,
        "frete": frete,
        "relacao_troca": rt,
    }

    output = os.path.join(BASE_DIR, "data_atual.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    print("\nColeta concluida!")
    print("ONI: " + str(enso["oni_atual"]) + " (" + enso["status"] + ")")
    print("Cambio: R$ " + str(usd_brl))
    soja_u = precos["soja_cbot"]["preco_usd_bushel"] if precos["soja_cbot"] else "?"
    soja_b = precos["soja_cbot"]["preco_brl_saca"] if precos["soja_cbot"] else "?"
    milho_u = precos["milho_cbot"]["preco_usd_bushel"] if precos["milho_cbot"] else "?"
    milho_b = precos["milho_cbot"]["preco_brl_saca"] if precos["milho_cbot"] else "?"
    print("Soja: USD " + str(soja_u) + "/bu = R$ " + str(soja_b) + "/sc")
    print("Milho: USD " + str(milho_u) + "/bu = R$ " + str(milho_b) + "/sc")
    print("Soja Paranagua: R$ " + str(round(soja_pga, 2)) + "/sc")
    print("Dados salvos em data_atual.json\n")

if __name__ == "__main__":
    main()
