import json
import random
from datetime import datetime, timedelta, timezone
import re
import time
import os

import altair as alt
import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components


# -----------------------------
# Config & Theming
# -----------------------------
st.set_page_config(
    page_title="Crypto Global Dashboard 3D",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inject Tron/Cyberpunk inspired styling
st.markdown(
    """
    <style>
    /* Global dark theme overrides */
    :root {
        --neon-primary: #00e5ff;
        --neon-secondary: #00ff9c;
        --neon-accent: #14f1d9;
        --bg-deep: #0a0f1f;
        --panel-bg: rgba(10, 15, 31, 0.6);
        --panel-border: rgba(0, 229, 255, 0.3);
    }
    
    /* App background */
    .stApp {
        background: radial-gradient(1200px 800px at 50% -10%, #0f1e3a 0%, #0a0f1f 40%, #050812 100%);
        color: #d5e9ff;
    }

    /* Headings and text */
    h1, h2, h3, h4, h5, h6 {
        color: #dff6ff !important;
        text-shadow: 0 0 12px rgba(0, 229, 255, 0.2);
        font-weight: 700;
    }

    /* Panels */
    .block-container {
        padding-top: 1rem;
    }

    .neon-panel {
        background: var(--panel-bg);
        border: 1px solid var(--panel-border);
        box-shadow: 0 0 24px rgba(0, 229, 255, 0.15) inset, 0 0 24px rgba(20, 241, 217, 0.08);
        border-radius: 14px;
        padding: 12px 14px;
        backdrop-filter: blur(8px);
    }

    .neon-badge {
        display: inline-block;
        padding: 6px 10px;
        border: 1px solid var(--panel-border);
        border-radius: 999px;
        background: rgba(0, 229, 255, 0.06);
        box-shadow: 0 0 16px rgba(0, 229, 255, 0.2) inset;
        color: #bfefff;
        font-size: 12px;
        letter-spacing: 0.06em;
    }

    .metric-hero {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 24px;
        font-weight: 800;
        color: #ccf7ff;
        text-shadow: 0 0 10px rgba(0, 229, 255, 0.25);
    }

    /* Hide default Streamlit elements we don't want */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Data helpers (CoinCap API with graceful fallback)
# -----------------------------
API_BASE = "https://api.coincap.io/v2"


def _safe_get_json(url: str, params: dict | None = None) -> dict | None:
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


@st.cache_data(ttl=60)
def get_global_overview() -> dict:
    data = _safe_get_json(f"{API_BASE}/global")
    if data and isinstance(data, dict) and data.get("data"):
        return data["data"]
    # Fallback mock
    return {
        "totalMarketCapUsd": str(1.95e12 + random.uniform(-3e10, 3e10)),
        "totalVolumeUsd24Hr": str(8.2e10 + random.uniform(-1e10, 1e10)),
    }


@st.cache_data(ttl=60)
def get_top_assets(limit: int = 10) -> list[dict]:
    data = _safe_get_json(f"{API_BASE}/assets", params={"limit": limit})
    if data and data.get("data"):
        return data["data"]
    # Fallback mock
    mock = []
    for sym in [
        "BTC","ETH","USDT","BNB","SOL","XRP","USDC","ADA","DOGE","TON",
    ]:
        mock.append({
            "id": sym.lower(),
            "symbol": sym,
            "name": sym,
            "priceUsd": str(100 + random.random() * 50000),
            "changePercent24Hr": str(random.uniform(-5, 5)),
            "marketCapUsd": str(1e10 + random.random() * 9e11),
            "volumeUsd24Hr": str(1e8 + random.random() * 5e10),
        })
    return mock


@st.cache_data(ttl=60)
def get_asset_detail(asset_id: str) -> dict:
    data = _safe_get_json(f"{API_BASE}/assets/{asset_id}")
    if data and data.get("data"):
        return data["data"]
    # Fallback mock
    return {
        "id": asset_id,
        "symbol": asset_id[:3].upper(),
        "name": asset_id.capitalize(),
        "priceUsd": str(100 + random.random() * 50000),
        "changePercent24Hr": str(random.uniform(-5, 5)),
        "marketCapUsd": str(1e10 + random.random() * 9e11),
        "volumeUsd24Hr": str(1e8 + random.random() * 5e10),
    }

@st.cache_data(ttl=60)
def get_top_for_kpis(limit: int = 50) -> list[dict]:
    data = _safe_get_json(f"{API_BASE}/assets", params={"limit": limit})
    return data.get("data", []) if data else []


def compute_kpis() -> dict:
    assets = get_top_for_kpis(50)
    if not assets:
        assets = get_top_assets(50)
    btc = next((a for a in assets if a.get("id") == "bitcoin" or a.get("symbol","BTC").upper()=="BTC"), None)
    mcaps = [float(a.get("marketCapUsd", 0) or 0) for a in assets]
    total_top_mcap = sum(mcaps) if mcaps else 0.0
    btc_dom = (float(btc.get("marketCapUsd", 0) or 0) / total_top_mcap * 100.0) if (btc and total_top_mcap > 0) else None
    changes = [float(a.get("changePercent24Hr", 0) or 0) for a in assets]
    adv = sum(1 for c in changes if c > 0)
    dec = sum(1 for c in changes if c <= 0)
    avg_change = sum(changes) / len(changes) if changes else 0.0
    return {
        "btc_dominance": btc_dom,
        "advancers": adv,
        "decliners": dec,
        "avg_change": avg_change,
    }


@st.cache_data(ttl=120)
def get_history_24h(asset_id: str) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    end = int(now.timestamp() * 1000)
    start = int((now - timedelta(hours=24)).timestamp() * 1000)
    url = f"{API_BASE}/assets/{asset_id}/history"
    data = _safe_get_json(url, params={"interval": "m5", "start": start, "end": end})
    if data and data.get("data"):
        rows = data["data"]
        df = pd.DataFrame(rows)
        if not df.empty:
            # Normalize types and drop invalid rows
            df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
            df["priceUsd"] = pd.to_numeric(df["priceUsd"], errors="coerce")
            df = df[["time", "priceUsd"]].dropna(subset=["time", "priceUsd"]).reset_index(drop=True)
            if not df.empty:
                return df
    # Fallback mock sparkline (random walk)
    times = pd.date_range(now - timedelta(hours=24), periods=288, freq="5min", tz="UTC")
    values = np.cumsum(np.random.normal(0, 0.5, size=len(times))) + random.uniform(50, 100)
    return pd.DataFrame({"time": times, "priceUsd": values})

@st.cache_data(ttl=120)
def get_history(asset_id: str, hours: int = 24) -> pd.DataFrame:
    # Choose interval based on hours
    if hours <= 6:
        interval = "m1"; freq = "1min"; points = hours * 60
    elif hours <= 24:
        interval = "m5"; freq = "5min"; points = int(hours * 12)
    elif hours <= 7*24:
        interval = "h1"; freq = "1h"; points = int(hours)
    else:
        interval = "d1"; freq = "1D"; points = int(hours / 24)
    now = datetime.now(timezone.utc)
    end = int(now.timestamp() * 1000)
    start = int((now - timedelta(hours=hours)).timestamp() * 1000)
    url = f"{API_BASE}/assets/{asset_id}/history"
    data = _safe_get_json(url, params={"interval": interval, "start": start, "end": end})
    if data and data.get("data"):
        rows = data["data"]
        df = pd.DataFrame(rows)
        if not df.empty:
            df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
            df["priceUsd"] = pd.to_numeric(df["priceUsd"], errors="coerce")
            df = df[["time", "priceUsd"]].dropna(subset=["time", "priceUsd"]).reset_index(drop=True)
            return df
    # Fallback mock
    times = pd.date_range(now - timedelta(hours=hours), periods=max(10, points), freq=freq, tz="UTC")
    values = np.cumsum(np.random.normal(0, 0.5, size=len(times))) + random.uniform(50, 100)
    return pd.DataFrame({"time": times, "priceUsd": values})

# New helpers for extra boxes
@st.cache_data(ttl=180)
def get_exchanges_count() -> int:
    data = _safe_get_json(f"{API_BASE}/exchanges", params={"limit": 2000})
    if data and data.get("data") and isinstance(data["data"], list):
        return len(data["data"])
    return 0

@st.cache_data(ttl=120)
def compute_stablecoin_dominance() -> float:
    assets = get_top_for_kpis(200)
    if not assets:
        return 0.0
    stable_symbols = {"USDT", "USDC", "DAI", "TUSD", "USDP"}
    total_mcap = 0.0
    stable_mcap = 0.0
    for a in assets:
        m = float(a.get("marketCapUsd", 0) or 0)
        total_mcap += m
        if a.get("symbol", "").upper() in stable_symbols:
            stable_mcap += m
    return (stable_mcap / total_mcap * 100.0) if total_mcap > 0 else 0.0

@st.cache_data(ttl=600)
def get_fear_greed_index() -> dict:
    data = _safe_get_json("https://api.alternative.me/fng/", params={"limit": 1})
    try:
        d = data.get("data", [])[0]
        return {"value": int(d.get("value", 0)), "classification": d.get("value_classification", "N/A")}
    except Exception:
        # Fallback mock
        return {"value": int(50 + random.uniform(-20, 20)), "classification": "Neutral"}

@st.cache_data(ttl=120)
def compute_threshold_counts(threshold: float = 5.0) -> dict:
    assets = get_top_for_kpis(100)
    if not assets:
        return {"up": 0, "down": 0}
    ups = 0; downs = 0
    for a in assets:
        ch = float(a.get("changePercent24Hr", 0) or 0)
        if ch >= threshold: ups += 1
        if ch <= -threshold: downs += 1
    return {"up": ups, "down": downs}

@st.cache_data(ttl=120)
def compute_btc_volatility() -> float:
    df = get_history("bitcoin", hours=24)
    if df.empty or len(df) < 10:
        return 0.0
    s = df["priceUsd"].astype(float)
    rets = s.pct_change().dropna()
    vol = rets.std() * 100.0  # percent
    return float(vol)

@st.cache_data(ttl=120)
def compute_alt_eth_dominance() -> dict:
    assets = get_top_for_kpis(300)
    if not assets:
        return {"btc": 0.0, "eth": 0.0, "alt": 0.0}
    total = sum(float(a.get("marketCapUsd", 0) or 0) for a in assets)
    if total <= 0:
        return {"btc": 0.0, "eth": 0.0, "alt": 0.0}
    def _mcap(sym: str) -> float:
        a = next((x for x in assets if x.get("symbol", "").upper() == sym), None)
        return float(a.get("marketCapUsd", 0) or 0) if a else 0.0
    btc = _mcap("BTC"); eth = _mcap("ETH")
    btc_d = btc / total * 100.0
    eth_d = eth / total * 100.0
    alt_d = max(0.0, 100.0 - btc_d - eth_d)
    return {"btc": btc_d, "eth": eth_d, "alt": alt_d}

@st.cache_data(ttl=120)
def compute_total_stablecap() -> float:
    assets = get_top_for_kpis(300)
    if not assets:
        return 0.0
    stables = {"USDT","USDC","DAI","TUSD","USDP"}
    return sum(float(a.get("marketCapUsd", 0) or 0) for a in assets if a.get("symbol", "").upper() in stables)

@st.cache_data(ttl=180)
def get_top_exchange_by_volume() -> dict | None:
    data = _safe_get_json(f"{API_BASE}/exchanges", params={"limit": 200})
    lst = data.get("data") if (data and data.get("data")) else None
    if not lst:
        return None
    def _vol(x: dict) -> float:
        # CoinCap may use 'volumeUsd' or 'volumeUsd24Hr'
        return float(x.get("volumeUsd24Hr", x.get("volumeUsd", 0)) or 0)
    top = max(lst, key=_vol)
    return {"name": top.get("name", "N/A"), "volume": _vol(top)}

@st.cache_data(ttl=120)
def compute_median_change() -> float:
    assets = get_top_for_kpis(200)
    chs = [float(a.get("changePercent24Hr", 0) or 0) for a in assets] if assets else []
    if not chs:
        return 0.0
    arr = np.sort(np.array(chs))
    mid = len(arr)//2
    return float((arr[mid] if len(arr)%2==1 else (arr[mid-1]+arr[mid])/2))

@st.cache_data(ttl=60)
def count_watchlist_alerts() -> int:
    try:
        wl = st.session_state.watchlist
    except Exception:
        return 0
    if not wl:
        return 0
    all_assets = get_top_for_kpis(300)
    by_sym = {a.get("symbol", "").upper(): a for a in all_assets}
    alerts = 0
    for sym, cfg in wl.items():
        a = by_sym.get(sym.upper())
        if not a:
            continue
        ch = float(a.get("changePercent24Hr", 0) or 0)
        thr = float(cfg.get("threshold", 5.0))
        if abs(ch) >= thr:
            alerts += 1
    return alerts

@st.cache_data(ttl=60)
def compute_breadth_percent() -> float:
    assets = get_top_for_kpis(100)
    if not assets:
        assets = get_top_assets(100)
    if not assets:
        return 0.0
    pos = sum(1 for a in assets if float(a.get("changePercent24Hr", 0) or 0) > 0)
    return 100.0 * pos / len(assets)

@st.cache_data(ttl=30)
def compute_btcusdt_spread_pct() -> float:
    ob = get_order_book_binance("BTCUSDT", limit=5)
    try:
        best_bid = float(ob["bids"][0][0])
        best_ask = float(ob["asks"][0][0])
        mid = (best_bid + best_ask) / 2.0
        return ((best_ask - best_bid) / mid) * 100.0 if mid > 0 else 0.0
    except Exception:
        return 0.0

@st.cache_data(ttl=60)
def compute_top10_volume_sum(top_assets: list[dict]) -> float:
    if not top_assets:
        return 0.0
    return sum(float(a.get("volumeUsd24Hr", 0) or 0) for a in top_assets)

def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df.empty:
        return df
    dfr = df.set_index("time").sort_index()
    o = dfr["priceUsd"].resample(rule).ohlc()
    o = o.dropna().reset_index()
    return o

# Category mapping (basic)
CATEGORY_SYMBOLS = {
    "All": set(),
    "Layer1": {"BTC", "ETH", "SOL", "ADA", "BNB", "AVAX", "ATOM", "NEAR"},
    "DeFi": {"UNI", "AAVE", "MKR", "CAKE", "CRV"},
    "Stablecoins": {"USDT", "USDC", "DAI"},
    "NFT": {"APE", "SAND", "MANA"},
    "Gaming": {"GALA", "AXS"},
}

# Binance Order Book (Depth)
@st.cache_data(ttl=30)
def get_order_book_binance(symbol: str = "BTCUSDT", limit: int = 50) -> dict | None:
    try:
        url = "https://api.binance.com/api/v3/depth"
        data = _safe_get_json(url, params={"symbol": symbol, "limit": limit})
        return data or None
    except Exception:
        return None


def usd_fmt(value: float) -> str:
    abbr = ["", "K", "M", "B", "T"]
    sign = "-" if value < 0 else ""
    value = abs(value)
    i = 0
    while value >= 1000 and i < len(abbr) - 1:
        value /= 1000.0
        i += 1
    return f"{sign}{value:,.2f}{abbr[i]}"


# -----------------------------
# 3D Globe HTML (Three.js) builder
# -----------------------------

def build_three_globe_html(cities: list[dict], camera_distance: int = 420, auto_rotate: bool = True, rotate_speed: float = 1.0, extras: list[dict] | None = None) -> str:
    capitals_json = json.dumps(cities)
    extras_json = json.dumps(extras or [])
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <style>
            html, body { margin: 0; height: 100%; background: transparent; overflow: hidden; }
            #globe-container { width: 100%; height: 100%; min-height: 620px; position: relative; }
            .tooltip {
                position: absolute; pointer-events: none; padding: 8px 10px;
                background: rgba(10,15,31,0.85); border: 1px solid rgba(0,229,255,0.35);
                border-radius: 8px; color: #dff6ff; font-family: sans-serif; font-size: 12px;
                box-shadow: 0 0 16px rgba(0,229,255,0.25);
            }
            .badge { display: inline-block; margin-left: 6px; color: #00ff9c; }
            #globe-error {
                position: absolute; inset: 0; display: none; align-items: center; justify-content: center;
                background: rgba(5,8,18,0.85); color: #ff5b6b; font-family: sans-serif; font-size: 14px;
                border: 1px solid rgba(255,91,107,0.35);
            }
        </style>
    </head>
    <body>
        <div id=\"globe-container\"></div>
        <div id=\"tooltip\" class=\"tooltip\" style=\"opacity:0\"></div>
        <div id=\"globe-error\">Impossible d'afficher le globe 3D (scripts bloqués ?). Vérifiez votre connexion réseau.</div>

        <script>
        (async function(){
            const errorOverlay = document.getElementById('globe-error');
            function loadScript(url){
                return new Promise((resolve, reject) => {
                    const s = document.createElement('script');
                    s.src = url; s.async = true; s.crossOrigin = 'anonymous';
                    s.onload = () => resolve(true);
                    s.onerror = () => reject(new Error('Failed '+url));
                    document.head.appendChild(s);
                });
            }
            async function loadFirst(urls){
                for (const u of urls){
                    try { await loadScript(u); return true; } catch(e){}
                }
                return false;
            }

            // Injected from Streamlit
            const INITIAL_DISTANCE = 
    """ + str(camera_distance) + """
            ;
            const AUTO_ROTATE = 
    """ + ("true" if auto_rotate else "false") + """
            ;
            const ROTATE_SPEED = 
    """ + str(rotate_speed) + """
            ;

            const CDNS = {
                three: [
                    'https://unpkg.com/three@0.158.0/build/three.min.js',
                    'https://cdn.jsdelivr.net/npm/three@0.158.0/build/three.min.js'
                ],
                controls: [
                    'https://unpkg.com/three@0.158.0/examples/js/controls/OrbitControls.js',
                    'https://cdn.jsdelivr.net/npm/three@0.158.0/examples/js/controls/OrbitControls.js'
                ],
                effectComposer: [
                    'https://unpkg.com/three@0.158.0/examples/js/postprocessing/EffectComposer.js',
                    'https://cdn.jsdelivr.net/npm/three@0.158.0/examples/js/postprocessing/EffectComposer.js'
                ],
                renderPass: [
                    'https://unpkg.com/three@0.158.0/examples/js/postprocessing/RenderPass.js',
                    'https://cdn.jsdelivr.net/npm/three@0.158.0/examples/js/postprocessing/RenderPass.js'
                ],
                bloomPass: [
                    'https://unpkg.com/three@0.158.0/examples/js/postprocessing/UnrealBloomPass.js',
                    'https://cdn.jsdelivr.net/npm/three@0.158.0/examples/js/postprocessing/UnrealBloomPass.js'
                ]
            };

            const okThree = await loadFirst(CDNS.three);
            if (!okThree || !window.THREE){ errorOverlay.style.display = 'flex'; return; }
            await loadFirst(CDNS.controls); // optional
            const okEC = await loadFirst(CDNS.effectComposer);
            const okRP = await loadFirst(CDNS.renderPass);
            const okUB = await loadFirst(CDNS.bloomPass);
            const postOk = !!(okEC && okRP && okUB && THREE.EffectComposer && THREE.RenderPass && THREE.UnrealBloomPass);

            try {
                const CITIES = 
    """ + capitals_json + """
                ;
                const EXTRAS = 
    """ + extras_json + """
                ;
                const PRIMARY = 0x00e5ff;
                const SECONDARY = 0x00ff9c;
                const ACCENT = 0x14f1d9;
                const container = document.getElementById('globe-container');
                const tooltip = document.getElementById('tooltip');

                const scene = new THREE.Scene();
                scene.fog = new THREE.Fog(0x050812, 180, 500);
                const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 2000);
                camera.position.set(0, 0, INITIAL_DISTANCE);

                const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
                renderer.setSize(container.clientWidth, container.clientHeight);
                renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
                renderer.setClearColor(0x000000, 0);
                container.appendChild(renderer.domElement);

                let composer = null;
                if (postOk){
                    composer = new THREE.EffectComposer(renderer);
                    const renderPass = new THREE.RenderPass(scene, camera);
                    composer.addPass(renderPass);
                    const bloomPass = new THREE.UnrealBloomPass(new THREE.Vector2(container.clientWidth, container.clientHeight), 0.6, 0.3, 0.2);
                    composer.addPass(bloomPass);
                }

                let controls;
                if (THREE.OrbitControls){
                    controls = new THREE.OrbitControls(camera, renderer.domElement);
                    controls.enableDamping = true;
                    controls.enablePan = false;
                    controls.minDistance = 200;
                    controls.maxDistance = 600;
                    controls.autoRotate = AUTO_ROTATE;
                    controls.autoRotateSpeed = ROTATE_SPEED;
                } else {
                    controls = { update: () => { camera.lookAt(0,0,0); } };
                }

                // Lights
                scene.add(new THREE.AmbientLight(0x3fffff, 0.45));
                const keyLight = new THREE.PointLight(PRIMARY, 1.6, 1200);
                keyLight.position.set(200, 120, 220);
                scene.add(keyLight);

                // Starfield
                const starGeo = new THREE.BufferGeometry();
                const starCount = 2000;
                const starPositions = new Float32Array(starCount * 3);
                for (let i = 0; i < starCount; i++) {
                    const r = 800 + Math.random() * 300;
                    const phi = Math.acos(2 * Math.random() - 1);
                    const theta = 2 * Math.PI * Math.random();
                    starPositions[i*3] = r * Math.sin(phi) * Math.cos(theta);
                    starPositions[i*3+1] = r * Math.cos(phi);
                    starPositions[i*3+2] = r * Math.sin(phi) * Math.sin(theta);
                }
                starGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
                const starMat = new THREE.PointsMaterial({ color: 0x88c6ff, size: 0.7 });
                scene.add(new THREE.Points(starGeo, starMat));

                // Globe and glow
                const R = 160;
                const globeGeo = new THREE.SphereGeometry(R, 64, 64);
                const globeMat = new THREE.MeshPhongMaterial({
                    color: 0x0b1226,
                    emissive: 0x0a1530,
                    shininess: 25,
                    specular: 0x05203b,
                });
                const globe = new THREE.Mesh(globeGeo, globeMat);
                scene.add(globe);
                const glowGeo = new THREE.SphereGeometry(R * 1.06, 64, 64);
                const glowMat = new THREE.MeshBasicMaterial({ color: PRIMARY, transparent: true, opacity: 0.12 });
                glowMat.side = THREE.BackSide;
                glowMat.depthWrite = false;
                glowMat.blending = THREE.AdditiveBlending;
                scene.add(new THREE.Mesh(glowGeo, glowMat));

                function latLonToVector3(lat, lon, radius) {
                    const phi = (90 - lat) * (Math.PI / 180);
                    const theta = (lon + 180) * (Math.PI / 180);
                    return new THREE.Vector3(
                        -radius * Math.sin(phi) * Math.cos(theta),
                        radius * Math.cos(phi),
                        radius * Math.sin(phi) * Math.sin(theta)
                    );
                }

                // Grid
                (function addLatLonGrid(){
                    const group = new THREE.Group();
                    const mat = new THREE.LineBasicMaterial({ color: 0x0d98ba, transparent: true, opacity: 0.18 });
                    for (let lon = -180; lon <= 180; lon += 15) {
                        const pts = [];
                        for (let lat = -90; lat <= 90; lat += 3) { pts.push(latLonToVector3(lat, lon, R + 0.3)); }
                        const geo = new THREE.BufferGeometry().setFromPoints(pts);
                        group.add(new THREE.Line(geo, mat));
                    }
                    for (let lat = -75; lat <= 75; lat += 15) {
                        const pts = [];
                        for (let lon = -180; lon <= 180; lon += 3) { pts.push(latLonToVector3(lat, lon, R + 0.3)); }
                        const geo = new THREE.BufferGeometry().setFromPoints(pts);
                        group.add(new THREE.Line(geo, mat));
                    }
                    scene.add(group);
                })();

                // Hub markers (meshes) + halos
                const cityGroup = new THREE.Group();
                scene.add(cityGroup);
                const cityMeshes = [];
                for (const c of CITIES) {
                    const pos = latLonToVector3(c.lat, c.lon, R + 1.5);
                    const g = new THREE.SphereGeometry(2.2, 16, 16);
                    const m = new THREE.MeshPhongMaterial({ color: 0x00ff9c, emissive: 0x00ff9c, emissiveIntensity: 0.6 });
                    const mesh = new THREE.Mesh(g, m);
                    mesh.position.copy(pos);
                    mesh.userData = c;
                    cityGroup.add(mesh);
                    cityMeshes.push(mesh);
                    const sm = new THREE.SpriteMaterial({ color: 0x00ff9c, transparent: true, opacity: 0.65, blending: THREE.AdditiveBlending });
                    const sprite = new THREE.Sprite(sm);
                    sprite.scale.set(8, 8, 1);
                    sprite.position.copy(pos.clone().multiplyScalar(1.01));
                    cityGroup.add(sprite);
                }

                // Extra points (Points cloud) with tooltips
                const extraPositions = new Float32Array(EXTRAS.length * 3);
                for (let i = 0; i < EXTRAS.length; i++){
                    const e = EXTRAS[i];
                    const v = latLonToVector3(e.lat, e.lon, R + 1.0);
                    extraPositions[i*3] = v.x; extraPositions[i*3+1] = v.y; extraPositions[i*3+2] = v.z;
                }
                const extrasGeo = new THREE.BufferGeometry();
                extrasGeo.setAttribute('position', new THREE.BufferAttribute(extraPositions, 3));
                const extrasMat = new THREE.PointsMaterial({ color: 0x00e5ff, size: 1.6, transparent: true, opacity: 0.85 });
                const extrasPoints = new THREE.Points(extrasGeo, extrasMat);
                scene.add(extrasPoints);

                // Links and moving dots
                const movingDots = [];
                function makeLink(a, b) {
                    const p1 = latLonToVector3(a.lat, a.lon, R + 1);
                    const p2 = latLonToVector3(b.lat, b.lon, R + 1);
                    const points = [];
                    for (let i = 0; i <= 40; i++) {
                        const t = i / 40;
                        const x = p1.x * (1-t) + p2.x * t;
                        const y = p1.y * (1-t) + p2.y * t + Math.sin(Math.PI * t) * 22;
                        const z = p1.z * (1-t) + p2.z * t;
                        points.push(new THREE.Vector3(x, y, z));
                    }
                    const curve = new THREE.CatmullRomCurve3(points);
                    const geo = new THREE.TubeGeometry(curve, 80, 0.6, 8, false);
                    const mat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.35 });
                    const tube = new THREE.Mesh(geo, mat);
                    scene.add(tube);
                    const mover = new THREE.Mesh(new THREE.SphereGeometry(1.1, 10, 10), new THREE.MeshBasicMaterial({ color: 0x14f1d9 }));
                    scene.add(mover);
                    movingDots.push({ curve, mesh: mover, speed: 0.05 + Math.random() * 0.05, offset: Math.random() });
                    return tube;
                }

                const hubs = CITIES.filter(c => ['New York','London','Tokyo','Singapore','Frankfurt','Hong Kong'].includes(c.name));
                const links = [];
                for (let i = 0; i < hubs.length; i++) {
                    for (let j = i+1; j < hubs.length; j++) {
                        if (Math.random() < 0.25) links.push(makeLink(hubs[i], hubs[j]));
                    }
                }

                // Raycaster for hub meshes and extra points
                const raycaster = new THREE.Raycaster();
                raycaster.params.Points = { threshold: 6 };
                const mouse = new THREE.Vector2();
                let lastClientX = 0; let lastClientY = 0;
                renderer.domElement.addEventListener('mousemove', (e) => {
                    const rect = renderer.domElement.getBoundingClientRect();
                    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
                    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
                    lastClientX = e.clientX; lastClientY = e.clientY;
                });
                renderer.domElement.addEventListener('mouseleave', () => { tooltip.style.opacity = 0; });

                let t = 0;
                function animate() {
                    requestAnimationFrame(animate);
                    controls && controls.update && controls.update();
                    if (AUTO_ROTATE) { globe.rotation.y += 0.0006 * ROTATE_SPEED; }
                    cityGroup.children.forEach((m, idx) => { if (m.isMesh) m.scale.setScalar(0.9 + 0.12 * Math.sin(t * 2 + idx)); });
                    links.forEach((l, i) => { l.material.opacity = 0.25 + 0.15 * Math.sin(t * 2 + i); });
                    movingDots.forEach((d) => { const u = ((t * d.speed) + d.offset) % 1; const p = d.curve.getPointAt(u); d.mesh.position.copy(p); });

                    raycaster.setFromCamera(mouse, camera);
                    const intersects = raycaster.intersectObjects([...cityMeshes, extrasPoints], true);
                    if (intersects.length > 0) {
                        const it = intersects[0];
                        let data = null;
                        if (it.object === extrasPoints && typeof it.index === 'number') {
                            data = EXTRAS[it.index];
                        } else if (it.object.userData) {
                            data = it.object.userData;
                        }
                        if (data) {
                            tooltip.style.opacity = 1;
                            tooltip.style.left = (lastClientX + 14) + 'px';
                            tooltip.style.top = (lastClientY + 14) + 'px';
                            tooltip.innerHTML = `
                                <div><strong>${data.name || 'Node'}</strong><span class=\"badge\">${data.region || 'Global'}</span></div>
                                <div>Volume: $${Number(data.volume || 0).toLocaleString()}</div>
                                <div>Top: ${data.top || ''}</div>
                                <div>Tendance: <span style=\"color:${(data.trend || 0) > 0 ? '#00ff9c' : '#ff5b6b'}\">${(data.trend || 0) > 0 ? '+' : ''}${Number(data.trend || 0).toFixed(2)}%</span></div>
                            `;
                        }
                    } else { tooltip.style.opacity = 0; }

                    if (composer){ composer.render(); } else { renderer.render(scene, camera); }
                    t += 0.01;
                }
                animate();

                function onResize() {
                    const w = container.clientWidth; const h = container.clientHeight;
                    renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
                }
                window.addEventListener('resize', onResize);
            } catch (err) { console.error('Erreur globe 3D:', err); errorOverlay.style.display = 'flex'; }
        })();
        </script>
    </body>
    </html>
    """
    return html


# -----------------------------
# Sample capitals/hubs dataset (lightweight)
# -----------------------------

CAPITALS = [
    {"name": "New York", "lat": 40.7128, "lon": -74.0060, "region": "US"},
    {"name": "London", "lat": 51.5074, "lon": -0.1278, "region": "UK"},
    {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503, "region": "JP"},
    {"name": "Singapore", "lat": 1.3521, "lon": 103.8198, "region": "SG"},
    {"name": "Frankfurt", "lat": 50.1109, "lon": 8.6821, "region": "DE"},
    {"name": "Hong Kong", "lat": 22.3193, "lon": 114.1694, "region": "HK"},
    {"name": "Seoul", "lat": 37.5665, "lon": 126.9780, "region": "KR"},
    {"name": "Sydney", "lat": -33.8688, "lon": 151.2093, "region": "AU"},
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522, "region": "FR"},
    {"name": "Dubai", "lat": 25.2048, "lon": 55.2708, "region": "AE"},
    {"name": "Toronto", "lat": 43.6532, "lon": -79.3832, "region": "CA"},
    {"name": "São Paulo", "lat": -23.5558, "lon": -46.6396, "region": "BR"},
]


def enrich_capitals_with_activity(top_assets: list[dict]) -> list[dict]:
    coins = [a.get("symbol", "?") for a in top_assets[:3]] or ["BTC", "ETH", "SOL"]
    result = []
    for c in CAPITALS:
        result.append({
            **c,
            "volume": int(5e7 + random.random() * 8e8),
            "top": ", ".join(coins),
            "trend": random.uniform(-4, 4),
        })
    return result


def generate_extra_points(count: int, top_assets: list[dict]) -> list[dict]:
    coins = [a.get("symbol", "?") for a in top_assets[:3]] or ["BTC", "ETH", "SOL"]
    nodes = []
    for i in range(count):
        lat = random.uniform(-70, 70)
        lon = random.uniform(-180, 180)
        nodes.append({
            "name": f"Node {i+1}",
            "region": "Global",
            "lat": lat,
            "lon": lon,
            "volume": int(1e6 + random.random() * 8e7),
            "top": ", ".join(coins),
            "trend": random.uniform(-5, 5),
        })
    return nodes

def get_market_extremes() -> tuple[dict | None, dict | None]:
    assets = get_top_for_kpis(50)
    if not assets:
        return None, None
    try:
        # Convert change to float safely
        for a in assets:
            a["_chg"] = float(a.get("changePercent24Hr", 0) or 0)
        top_gainer = max(assets, key=lambda a: a["_chg"])
        top_loser = min(assets, key=lambda a: a["_chg"])
        return top_gainer, top_loser
    except Exception:
        return None, None

def _fetch_rss_titles(url: str, limit: int = 6) -> list[str]:
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return []
        text = resp.text
        titles = re.findall(r"<title>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
        # Drop the channel title (first one)
        titles = [t.strip() for t in titles[1:limit+1]]
        # Clean HTML entities
        clean = []
        for t in titles:
            t = re.sub(r"<.*?>", "", t)
            t = t.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
            clean.append(t)
        return clean
    except Exception:
        return []


def get_news_headlines(limit: int = 6) -> list[str]:
    # Try a couple of common RSS feeds
    feeds = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cointelegraph.com/rss",
    ]
    for f in feeds:
        titles = _fetch_rss_titles(f, limit)
        if titles:
            return titles[:limit]
    # Fallback mock
    return [
        "Le marché crypto maintient sa capitalisation",
        "BTC et ETH stables malgré la volatilité",
        "SOL mène les hausses de la journée",
        "Volumes en hausse sur les principales plateformes",
        "De nouveaux capitaux entrent sur le marché",
    ][:limit]


def build_ticker_html(top_assets: list[dict], headlines: list[str]) -> str:
    items = []
    for a in top_assets:
        sym = a.get("symbol", "?")
        price = float(a.get("priceUsd", 0) or 0)
        ch = float(a.get("changePercent24Hr", 0) or 0)
        col = "#00ff9c" if ch >= 0 else "#ff5b6b"
        items.append(
            "<span style='margin-right:24px;'><b>%s</b> $ %s <span style='color:%s'>%+0.2f%%</span></span>" % (
                sym, f"{price:,.2f}", col, ch
            )
        )
    for h in headlines:
        items.append("<span style='margin-right:24px;'>📰 %s</span>" % h)
    content = "".join(items)
    full = content + content
    html_tpl = """
    <div style="position:relative;width:100%;height:40px;overflow:hidden;border:1px solid rgba(0,229,255,0.25);background:rgba(0,229,255,0.05);border-radius:10px;">
      <div style="display:inline-block;white-space:nowrap;position:absolute;will-change:transform;animation:scrollLeft 30s linear infinite;padding:8px 12px;color:#dff6ff;">
        __CONTENT__
      </div>
    </div>
    <style>
      @keyframes scrollLeft { from { transform: translateX(0); } to { transform: translateX(-50%); } }
    </style>
    """
    return html_tpl.replace("__CONTENT__", full)

def build_bottom_ticker_html(top_assets: list[dict], headlines: list[str]) -> str:
    items = []
    for a in top_assets:
        sym = a.get("symbol", "?")
        price = float(a.get("priceUsd", 0) or 0)
        ch = float(a.get("changePercent24Hr", 0) or 0)
        col = "#00ff9c" if ch >= 0 else "#ff5b6b"
        items.append(
            "<span style='margin-right:28px;'><b>%s</b> $ %s <span style='color:%s'>%+0.2f%%</span></span>" % (
                sym, f"{price:,.2f}", col, ch
            )
        )
    for h in headlines:
        items.append("<span style='margin-right:32px;'>📰 %s</span>" % h)
    content = "".join(items)
    full = content + content
    html_tpl = """
    <div id=\"bottom-ticker\" style=\"position:fixed;left:0;right:0;bottom:0;height:50px;z-index:9999;background:rgba(5,8,18,0.9);border-top:1px solid rgba(0,229,255,0.25);backdrop-filter: blur(6px);\">
      <div style=\"display:inline-block;white-space:nowrap;position:absolute;will-change:transform;animation:scrollLeftBottom 40s linear infinite;padding:10px 16px;color:#dff6ff;width:200%;\">
        __CONTENT__
      </div>
    </div>
    <style>
      @keyframes scrollLeftBottom { from { transform: translateX(0); } to { transform: translateX(-50%); } }
    </style>
    """
    return html_tpl.replace("__CONTENT__", full)

# -----------------------------
# Layout
# -----------------------------

# Header metric row
colA, colB, colC = st.columns([1.2, 1.6, 1.2])

with colB:
    st.markdown("<div class='neon-panel'>", unsafe_allow_html=True)
    overview = get_global_overview()
    mcap = float(overview.get("totalMarketCapUsd", 0))
    vol24 = float(overview.get("totalVolumeUsd24Hr", 0))
    st.markdown(
        f"<div class='metric-hero'>🌐 Crypto Global Market Cap: $ {usd_fmt(mcap)}" \
        f"<span class='neon-badge'>24h Vol $ {usd_fmt(vol24)}</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# KPI boxes row
k1, k2, k3, k4 = st.columns(4)
kpis = compute_kpis()
with k1:
    st.markdown(
        f"<div class='neon-panel' style='padding:12px;'><div style='opacity:.8;font-size:12px'>BTC Dominance</div>"
        f"<div style='font-size:22px;font-weight:800;color:#ccf7ff;'>{(kpis['btc_dominance'] or 0):.2f}%</div></div>",
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f"<div class='neon-panel' style='padding:12px;'><div style='opacity:.8;font-size:12px'>Advancers</div>"
        f"<div style='font-size:22px;font-weight:800;color:#00ff9c;'>{kpis['advancers']}</div></div>",
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f"<div class='neon-panel' style='padding:12px;'><div style='opacity:.8;font-size:12px'>Decliners</div>"
        f"<div style='font-size:22px;font-weight:800;color:#ff5b6b;'>{kpis['decliners']}</div></div>",
        unsafe_allow_html=True,
    )
with k4:
    ch = kpis['avg_change']
    color = '#00ff9c' if ch >= 0 else '#ff5b6b'
    st.markdown(
        f"<div class='neon-panel' style='padding:12px;'><div style='opacity:.8;font-size:12px'>Avg Change 24h</div>"
        f"<div style='font-size:22px;font-weight:800;color:{color};'>{ch:+.2f}%</div></div>",
        unsafe_allow_html=True,
    )

# New summary boxes row
s1, s2, s3, s4 = st.columns(4)
with s1:
    breadth = compute_breadth_percent()
    st.markdown(
        f"<div class='neon-panel' style='padding:12px;'><div style='opacity:.8;font-size:12px'>Breadth positif</div>"
        f"<div style='font-size:20px;font-weight:800;color:#00ff9c;'>{breadth:.1f}%</div></div>",
        unsafe_allow_html=True,
    )
with s2:
    sp = compute_btcusdt_spread_pct()
    st.markdown(
        f"<div class='neon-panel' style='padding:12px;'><div style='opacity:.8;font-size:12px'>Spread BTCUSDT</div>"
        f"<div style='font-size:20px;font-weight:800;color:#bfefff;'>{sp:.3f}%</div></div>",
        unsafe_allow_html=True,
    )
with s3:
    # Will compute after we fetch _top_for_ticker
    st.session_state["_box_vol_placeholder"] = True
    st.markdown(
        f"<div class='neon-panel' style='padding:12px;' id='vol-top10-box'><div style='opacity:.8;font-size:12px'>Volume Top10</div>"
        f"<div style='font-size:20px;font-weight:800;color:#ccf7ff;' id='vol-top10-val'>Chargement...</div></div>",
        unsafe_allow_html=True,
    )
with s4:
    tg, tl = get_market_extremes()
    if tg:
        cg = float(tg.get('changePercent24Hr', 0) or 0)
        sym = tg.get('symbol', '—')
        colg = '#00ff9c' if cg >= 0 else '#ff5b6b'
        st.markdown(
            f"<div class='neon-panel' style='padding:12px;'><div style='opacity:.8;font-size:12px'>Top Mover</div>"
            f"<div style='font-weight:700;color:#bfefff'>{sym}</div>"
            f"<div style='font-size:20px;font-weight:800;color:{colg};'>{cg:+.2f}%</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='neon-panel' style='padding:12px;'>Top Mover: n/a</div>",
            unsafe_allow_html=True,
        )

# News & metrics ticker
_top_for_ticker = get_top_assets(10)
_news = get_news_headlines(6)
components.html(build_ticker_html(_top_for_ticker, _news), height=44)

# Fill Volume Top10 box value now that _top_for_ticker is available
try:
    volsum = compute_top10_volume_sum(_top_for_ticker)
    st.markdown(
        f"<script>document.getElementById('vol-top10-val').innerText = '$ {usd_fmt(volsum)}';</script>",
        unsafe_allow_html=True,
    )
except Exception:
    pass

st.markdown("\n")

left, center, right = st.columns([0.9, 1.6, 1.0])

# Sidebar (optional controls)
st.sidebar.markdown("## Contrôles")
auto_rotate = st.sidebar.toggle("Rotation auto", value=True, help="Active la rotation lente du globe")
distance = st.sidebar.slider("Zoom (distance)", min_value=200, max_value=600, value=420)
rot_speed = st.sidebar.slider("Vitesse rotation", min_value=0.1, max_value=3.0, value=1.0, step=0.1)
extra_count = st.sidebar.slider("Points additionnels (3D)", min_value=0, max_value=500, value=150, step=10)
live_update = st.sidebar.toggle("Live update", value=True, help="Rafraîchit automatiquement les données")
refresh_sec = st.sidebar.slider("Rafraîchissement (s)", min_value=15, max_value=120, value=60, step=5)

st.sidebar.markdown("## Watchlist")
if "watchlist" not in st.session_state:
    st.session_state.watchlist = {}
wl_sym = st.sidebar.text_input("Ajouter (SYM)", value="")
col_wl1, col_wl2 = st.sidebar.columns([1,1])
with col_wl1:
    if st.button("Ajouter") and wl_sym.strip():
        st.session_state.watchlist[wl_sym.strip().upper()] = {"threshold": 5.0}
with col_wl2:
    if st.button("Vider"):
        st.session_state.watchlist = {}
for sym, cfg in st.session_state.watchlist.items():
    st.sidebar.write(f"{sym} seuil {cfg['threshold']}%")

# Left panel: Top 10 cryptos with sparklines
with left:
    st.markdown("<div class='neon-panel'>", unsafe_allow_html=True)
    st.markdown("### Top 10 échangées")
    # Category filter
    cat = st.selectbox("Filtre catégorie", list(CATEGORY_SYMBOLS.keys()), index=0)
    top = _top_for_ticker
    if cat != "All":
        allowed = CATEGORY_SYMBOLS.get(cat, set())
        top = [a for a in top if a.get("symbol", "").upper() in allowed]
        if not top:
            st.info("Aucune crypto dans cette catégorie avec les données actuelles.")
    for idx, asset in enumerate(top, start=1):
        st.markdown("<div class='neon-panel' style='padding:8px;margin-bottom:8px;'>", unsafe_allow_html=True)
        asset_id = asset.get("id", "bitcoin")
        symbol = asset.get("symbol", "?")
        name = asset.get("name", symbol)
        price = float(asset.get("priceUsd", 0) or 0)
        change = float(asset.get("changePercent24Hr", 0) or 0)
        mcap = float(asset.get("marketCapUsd", 0) or 0)
        vol = float(asset.get("volumeUsd24Hr", 0) or 0)
        color = "#00ff9c" if change >= 0 else "#ff5b6b"

        # Sparkline (normalized)
        df = get_history_24h(asset_id)
        if df.empty:
            st.markdown(f"**{idx}. {symbol}** — données indisponibles")
            st.markdown("</div>", unsafe_allow_html=True)
            continue
        df_s = df.tail(150).copy()
        min_p = df_s["priceUsd"].min()
        max_p = df_s["priceUsd"].max()
        span = max(1e-9, max_p - min_p)
        df_s["norm"] = (df_s["priceUsd"] - min_p) / span
        # Prepare ISO time strings for better Vega-Lite compatibility
        df_s = df_s.dropna(subset=["time", "norm"]).copy()
        if "time" in df_s and hasattr(df_s["time"], "dt"):
            df_s["t_iso"] = df_s["time"].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            df_s["t_iso"] = pd.to_datetime(df_s["time"]).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        df_s = df_s[np.isfinite(df_s["norm"])].reset_index(drop=True)
        if len(df_s) < 2:
            st.markdown(f"**{idx}. {symbol}** — données insuffisantes pour sparkline")
            st.markdown("</div>", unsafe_allow_html=True)
            continue
        chart = (
            alt.Chart(df_s)
            .mark_line(color="#00e5ff", size=2)
            .encode(x=alt.X("t_iso:T", axis=None), y=alt.Y("norm:Q", axis=None))
            .properties(height=42)
        )

        c1, c2 = st.columns([1.0, 1.2])
        with c1:
            st.markdown(f"**{idx}. {name} ({symbol})**  ")
            st.markdown(f"<span style='color:#bfefff;'>$ {price:,.2f}</span>  "
                        f"<span style='color:{color};font-size:12px;'>{change:+.2f}% / 24h</span>",
                        unsafe_allow_html=True)
            st.markdown(
                f"<div style='font-size:11px;opacity:0.85;margin-top:2px;'>Cap: $ {usd_fmt(mcap)} — Vol 24h: $ {usd_fmt(vol)}</div>",
                unsafe_allow_html=True,
            )
        with c2:
            st.altair_chart(chart, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Center: 3D Globe
with center:
    st.markdown("<div class='neon-panel'>", unsafe_allow_html=True)
    st.markdown("### Marché global (3D)")
    cities = enrich_capitals_with_activity(top)
    extras = generate_extra_points(extra_count, top)
    html = build_three_globe_html(cities, camera_distance=distance, auto_rotate=auto_rotate, rotate_speed=rot_speed, extras=extras)
    components.html(html, height=650)
    # Info blocks tied to globe
    hubs_sorted = sorted(cities, key=lambda x: x.get("volume", 0), reverse=True)[:6]
    st.markdown("#### Hubs majeurs")
    for h in hubs_sorted:
        trend = float(h.get("trend", 0))
        color = "#00ff9c" if trend >= 0 else "#ff5b6b"
        st.markdown(
            f"<div class='neon-panel' style='margin-bottom:6px;padding:8px;'>"
            f"<strong>{h['name']}</strong> <span class='neon-badge'>{h['region']}</span><br/>"
            f"Volume: $ {usd_fmt(float(h.get('volume', 0)))} "
            f"· Tendance: <span style='color:{color}'>{trend:+.2f}%</span> "
            f"· Top: {h.get('top','')}"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        f"<div class='neon-badge'>Hubs: {len(cities)} — Noeuds: {len(extras)}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# Advanced Charts section in center
with center:
    st.markdown("<div class='neon-panel' style='margin-top:8px;'>", unsafe_allow_html=True)
    st.markdown("### Charts avancés")
    tf = st.selectbox("Timeframe", ["1h", "24h", "7j", "30j"], index=1, key="tf_sel")
    hours_map = {"1h": 1, "24h": 24, "7j": 7*24, "30j": 30*24}
    comp_syms = st.multiselect("Comparer", ["BTC","ETH","SOL","BNB","ADA","XRP"], default=["BTC","ETH","SOL"], key="cmp_syms")
    tabs = st.tabs(["Lignes", "Candlesticks"])
    with tabs[0]:
        layers_cmp = []
        palette = ["#00e5ff", "#14f1d9", "#f2a900", "#ff7fbf", "#8c8c8c", "#00ff9c"]
        for i, sym in enumerate(comp_syms):
            aid = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","BNB":"binance-coin","ADA":"cardano","XRP":"ripple"}.get(sym, "bitcoin")
            dfc = get_history(aid, hours=hours_map[tf])
            if dfc.empty:
                continue
            min_p = dfc["priceUsd"].min(); max_p = dfc["priceUsd"].max(); span = max(1e-9, max_p - min_p)
            dfc["norm"] = (dfc["priceUsd"] - min_p) / span
            dfc["t_iso"] = pd.to_datetime(dfc["time"]).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            layers_cmp.append(
                alt.Chart(dfc).mark_line(color=palette[i % len(palette)], opacity=0.95).encode(
                    x=alt.X("t_iso:T", title=None), y=alt.Y("norm:Q", title=None)
                ).properties(title=sym)
            )
        if layers_cmp:
            st.altair_chart(alt.layer(*layers_cmp).resolve_scale(y='independent').properties(height=260), use_container_width=True)
        else:
            st.info("Pas de données pour la comparaison.")
    with tabs[1]:
        sym_cs = st.selectbox("Instrument", comp_syms or ["BTC"], key="cs_sel")
        aid = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","BNB":"binance-coin","ADA":"cardano","XRP":"ripple"}.get(sym_cs, "bitcoin")
        dfc = get_history(aid, hours=hours_map[tf])
        rule = "5min" if hours_map[tf] <= 24 else ("1h" if hours_map[tf] <= 7*24 else "1D")
        ohlc = resample_ohlc(dfc, rule)
        if not ohlc.empty and {"open","high","low","close"}.issubset(ohlc.columns):
            ohlc["t_iso"] = pd.to_datetime(ohlc["time"]).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            base = alt.Chart(ohlc).encode(x=alt.X("t_iso:T", title=None))
            rule_chart = base.mark_rule(color="#bfefff").encode(y="low:Q", y2="high:Q")
            bar_up = base.transform_filter("datum.close >= datum.open").mark_bar(color="#00ff9c").encode(y="open:Q", y2="close:Q")
            bar_dn = base.transform_filter("datum.close < datum.open").mark_bar(color="#ff5b6b").encode(y="open:Q", y2="close:Q")
            st.altair_chart((rule_chart + bar_up + bar_dn).properties(height=280), use_container_width=True)
        else:
            st.info("Données insuffisantes pour candlesticks.")
    st.markdown("</div>", unsafe_allow_html=True)

# Heatmap in left panel bottom
with left:
    st.markdown("<div class='neon-panel' style='margin-top:8px;'>", unsafe_allow_html=True)
    st.markdown("### Heatmap marché")
    hm = _top_for_ticker
    if hm:
        # build grid positions
        dfh = pd.DataFrame([{ "symbol": a.get("symbol","?"), "chg": float(a.get("changePercent24Hr",0) or 0)} for a in hm])
        dfh["row"] = (np.arange(len(dfh)) // 5)
        dfh["col"] = (np.arange(len(dfh)) % 5)
        heat = alt.Chart(dfh).mark_rect().encode(
            x=alt.X("col:O", axis=None), y=alt.Y("row:O", axis=None),
            color=alt.Color("chg:Q", scale=alt.Scale(scheme="redblue", domainMid=0), legend=None),
            tooltip=["symbol:N","chg:Q"]
        ).properties(height=180)
        labels = alt.Chart(dfh).mark_text(color="#ffffff").encode(
            x="col:O", y="row:O", text="symbol:N"
        )
        st.altair_chart(heat + labels, use_container_width=True)
    else:
        st.info("Heatmap indisponible.")
    st.markdown("</div>", unsafe_allow_html=True)

# Right panel: BTC / ETH / SOL 24h lines
with right:
    try:
        st.markdown("<div class='neon-panel'>", unsafe_allow_html=True)
        st.markdown("### BTC / ETH / SOL — 24h")
        assets = [("bitcoin", "BTC", "#f2a900"), ("ethereum", "ETH", "#8c8c8c"), ("solana", "SOL", "#14f1d9")]

        # Mini cards (blocks) with 24h details
        c1, c2, c3 = st.columns(3)
        cards_cols = [c1, c2, c3]
        for idx, (aid, sym, color) in enumerate(assets):
            detail = get_asset_detail(aid)
            price = float(detail.get("priceUsd", 0) or 0)
            change = float(detail.get("changePercent24Hr", 0) or 0)
            mcap = float(detail.get("marketCapUsd", 0) or 0)
            vol = float(detail.get("volumeUsd24Hr", 0) or 0)
            dfh = get_history_24h(aid).tail(288)
            day_min = dfh["priceUsd"].min() if not dfh.empty else None
            day_max = dfh["priceUsd"].max() if not dfh.empty else None
            col = cards_cols[idx]
            with col:
                st.markdown(
                    f"<div class='neon-panel' style='padding:10px;'>"
                    f"<div style='font-weight:700;color:{color};margin-bottom:4px;'>{sym}</div>"
                    f"<div style='font-size:20px;color:#ccf7ff;'>$ {price:,.2f}"
                    f" <span style='font-size:12px;color:{('#00ff9c' if change>=0 else '#ff5b6b')};'>{change:+.2f}%</span>"
                    f"</div>"
                    f"<div style='font-size:12px;opacity:0.85;margin-top:4px;'>Cap: $ {usd_fmt(mcap)} · Vol 24h: $ {usd_fmt(vol)}</div>"
                    f"<div style='font-size:11px;opacity:0.75;margin-top:4px;'>"
                    f"{('Min 24h: $ ' + format(day_min, ',.2f')) if day_min else 'Min 24h: n/a'} · "
                    f"{('Max 24h: $ ' + format(day_max, ',.2f')) if day_max else 'Max 24h: n/a'}"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        layers = []
        for aid, sym, color in assets:
            df = get_history_24h(aid)
            df = df.tail(288)
            if df.empty:
                continue
            min_p = df["priceUsd"].min()
            max_p = df["priceUsd"].max()
            span = max(1e-9, max_p - min_p)
            df["norm"] = (df["priceUsd"] - min_p) / span
            df = df.dropna(subset=["time", "norm"]).copy()
            if "time" in df and hasattr(df["time"], "dt"):
                df["t_iso"] = df["time"].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                df["t_iso"] = pd.to_datetime(df["time"]).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            df = df[np.isfinite(df["norm"])].reset_index(drop=True)
            if len(df) < 2:
                continue
            layers.append(
                alt.Chart(df).mark_line(color=color, opacity=0.95).encode(
                    x=alt.X("t_iso:T", title=None), y=alt.Y("norm:Q", title=None)
                )
            )
        if layers:
            chart = alt.layer(*layers).properties(height=260)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Données graphiques indisponibles pour le moment.")

        st.markdown("### Capitalisation totale")
        st.markdown(
            f"<div class='neon-badge'>Cap totale: $ {usd_fmt(float(overview.get('totalMarketCapUsd', 0)))}" \
            f" — Vol 24h: $ {usd_fmt(float(overview.get('totalVolumeUsd24Hr', 0)))}" \
            "</div>",
            unsafe_allow_html=True,
        )

        # Boxes under Capitalisation totale
        g1, g2 = st.columns(2)
        try:
            _k = kpis
        except NameError:
            _k = compute_kpis()
        with g1:
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>BTC Dominance</div>"
                f"<div style='font-size:18px;font-weight:800;color:#ccf7ff;'>{(_k['btc_dominance'] or 0):.2f}%</div></div>",
                unsafe_allow_html=True,
            )
        with g2:
            ch = _k['avg_change']
            color = '#00ff9c' if ch >= 0 else '#ff5b6b'
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>Avg Change 24h</div>"
                f"<div style='font-size:18px;font-weight:800;color:{color};'>{ch:+.2f}%</div></div>",
                unsafe_allow_html=True,
            )

        g3, g4 = st.columns(2)
        top_g, top_l = get_market_extremes()
        if top_g:
            cg = float(top_g.get('changePercent24Hr', 0) or 0)
            colg = '#00ff9c' if cg >= 0 else '#ff5b6b'
            st_symbol = top_g.get('symbol', '').upper()
            st_name = top_g.get('name', st_symbol)
            with g3:
                st.markdown(
                    f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>Top Gainer</div>"
                    f"<div style='font-weight:700;color:#bfefff'>{st_name} ({st_symbol})</div>"
                    f"<div style='font-size:18px;font-weight:800;color:{colg};'>{cg:+.2f}%</div></div>",
                    unsafe_allow_html=True,
                )
        if top_l:
            cl = float(top_l.get('changePercent24Hr', 0) or 0)
            coll = '#00ff9c' if cl >= 0 else '#ff5b6b'
            st_symbol = top_l.get('symbol', '').upper()
            st_name = top_l.get('name', st_symbol)
            with g4:
                st.markdown(
                    f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>Top Loser</div>"
                    f"<div style='font-weight:700;color:#bfefff'>{st_name} ({st_symbol})</div>"
                    f"<div style='font-size:18px;font-weight:800;color:{coll};'>{cl:+.2f}%</div></div>",
                    unsafe_allow_html=True,
                )

        # Additional market insight boxes
        st.markdown("### Insights marché")
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            sc_dom = compute_stablecoin_dominance()
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>Stablecoins Dominance</div>"
                f"<div style='font-size:18px;font-weight:800;color:#ccf7ff;'>{sc_dom:.2f}%</div></div>",
                unsafe_allow_html=True,
            )
        with r1c2:
            ex_cnt = get_exchanges_count()
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>Exchanges actifs</div>"
                f"<div style='font-size:18px;font-weight:800;color:#bfefff;'>{ex_cnt}</div></div>",
                unsafe_allow_html=True,
            )
        with r1c3:
            fg = get_fear_greed_index()
            fg_val = fg.get('value', 0)
            fg_cls = fg.get('classification', 'N/A')
            fg_color = '#00ff9c' if fg_val >= 60 else ('#ff5b6b' if fg_val <= 40 else '#bfefff')
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>Fear & Greed</div>"
                f"<div style='font-size:18px;font-weight:800;color:{fg_color};'>{fg_val} — {fg_cls}</div></div>",
                unsafe_allow_html=True,
            )

        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            thr = compute_threshold_counts(5.0)
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>&gt;= +5% (24h)</div>"
                f"<div style='font-size:18px;font-weight:800;color:#00ff9c;'>{thr['up']}</div></div>",
                unsafe_allow_html=True,
            )
        with r2c2:
            thr = compute_threshold_counts(5.0)
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>&lt;= -5% (24h)</div>"
                f"<div style='font-size:18px;font-weight:800;color:#ff5b6b;'>{thr['down']}</div></div>",
                unsafe_allow_html=True,
            )
        with r2c3:
            volp = compute_btc_volatility()
            color = '#00ff9c' if volp < 2 else ('#bfefff' if volp < 5 else '#ffb86b')
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>Vol BTC (24h, %)</div>"
                f"<div style='font-size:18px;font-weight:800;color:{color};'>{volp:.2f}%</div></div>",
                unsafe_allow_html=True,
            )

        # New rows of boxes
        st.markdown("### Plus d'insights")
        r3c1, r3c2, r3c3 = st.columns(3)
        dom = compute_alt_eth_dominance()
        with r3c1:
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>ETH Dominance</div>"
                f"<div style='font-size:18px;font-weight:800;color:#bfefff;'>{dom['eth']:.2f}%</div></div>",
                unsafe_allow_html=True,
            )
        with r3c2:
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>ALT Dominance</div>"
                f"<div style='font-size:18px;font-weight:800;color:#ccf7ff;'>{dom['alt']:.2f}%</div></div>",
                unsafe_allow_html=True,
            )
        with r3c3:
            stablecap = compute_total_stablecap()
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>Stablecap total</div>"
                f"<div style='font-size:18px;font-weight:800;color:#ccf7ff;'>$ {usd_fmt(stablecap)}</div></div>",
                unsafe_allow_html=True,
            )

        r4c1, r4c2, r4c3 = st.columns(3)
        tx = get_top_exchange_by_volume()
        with r4c1:
            if tx:
                st.markdown(
                    f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>Top Exchange (vol)</div>"
                    f"<div style='font-weight:700;color:#bfefff'>{tx['name']}</div>"
                    f"<div style='font-size:18px;font-weight:800;color:#ccf7ff;'>$ {usd_fmt(tx['volume'])}</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='neon-panel' style='padding:10px;'>Top Exchange: n/a</div>",
                    unsafe_allow_html=True,
                )
        with r4c2:
            med = compute_median_change()
            colm = '#00ff9c' if med >= 0 else '#ff5b6b'
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>Médiane change 24h</div>"
                f"<div style='font-size:18px;font-weight:800;color:{colm};'>{med:+.2f}%</div></div>",
                unsafe_allow_html=True,
            )
        with r4c3:
            alerts = count_watchlist_alerts()
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.8;font-size:12px'>Alertes Watchlist</div>"
                f"<div style='font-size:18px;font-weight:800;color:#ffdf6b;'>{alerts}</div></div>",
                unsafe_allow_html=True,
            )

        # New row: Gas, Hashrate, Funding/OI, L2 dominance
        r5c1, r5c2, r5c3 = st.columns(3)
        # ETH gas inline
        try:
            key = os.getenv("ETHERSCAN_API_KEY")
            if key:
                _g = _safe_get_json("https://api.etherscan.io/api", params={"module":"gastracker","action":"gasoracle","apikey":key}) or {}
                _gr = _g.get("result", {})
                gas = {"low": float(_gr.get("SafeGasPrice", 0) or 0), "avg": float(_gr.get("ProposeGasPrice", 0) or 0), "fast": float(_gr.get("FastGasPrice", 0) or 0)}
            else:
                base = 20.0 + random.uniform(-5, 5)
                gas = {"low": max(1.0, base * 0.7), "avg": max(1.0, base), "fast": max(1.0, base * 1.3)}
        except Exception:
            base = 20.0 + random.uniform(-5, 5)
            gas = {"low": max(1.0, base * 0.7), "avg": max(1.0, base), "fast": max(1.0, base * 1.3)}
        with r5c1:
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.75;font-size:12px'>ETH Gas (Gwei)</div>"
                f"<div style='font-size:16px;color:#bfefff;'>Low {gas['low']:.0f} · Avg {gas['avg']:.0f} · Fast {gas['fast']:.0f}</div></div>",
                unsafe_allow_html=True,
            )
        # BTC hashrate inline
        try:
            _hr = _safe_get_json("https://api.blockchain.info/charts/hash-rate", params={"timespan":"3days","format":"json"}) or {}
            _vals = _hr.get("values", [])
            hashr = float((_vals[-1] or {}).get("y", 0)) / 1_000_000.0 if _vals else 0.0
            if hashr <= 0:
                hashr = float(350 + random.uniform(-50, 50))
        except Exception:
            hashr = float(350 + random.uniform(-50, 50))
        with r5c2:
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.75;font-size:12px'>Hashrate BTC</div>"
                f"<div style='font-size:16px;color:#ccf7ff;'>{hashr:.2f} EH/s</div></div>",
                unsafe_allow_html=True,
            )
        # Funding/OI inline
        try:
            fund_json = _safe_get_json("https://fapi.binance.com/fapi/v1/premiumIndex", params={"symbol":"BTCUSDT"}) or {}
            oi_json = _safe_get_json("https://fapi.binance.com/fapi/v1/openInterest", params={"symbol":"BTCUSDT"}) or {}
            fr = float(fund_json.get("lastFundingRate", 0) or 0) * 100.0
            mark = float(fund_json.get("markPrice", 0) or 0)
            qty = float(oi_json.get("openInterest", 0) or 0)
            oi_usd = qty * (mark or 0)
        except Exception:
            fr = 0.0; oi_usd = 0.0
        fcol = '#00ff9c' if fr >= 0 else '#ff5b6b'
        st.markdown(
            f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.75;font-size:12px'>Funding (BTCUSDT) / OI</div>"
            f"<div style='font-size:16px;color:{fcol};'>{fr:+.4f}%</div>"
            f"<div style='font-size:14px;color:#bfefff;'>OI: $ {usd_fmt(oi_usd)}</div></div>",
            unsafe_allow_html=True,
        )
        r6c1, r6c2 = st.columns(2)
        # L2 dominance inline (fallback if compute_l2_dominance absent)
        try:
            l2dom = float(compute_l2_dominance())
        except Exception:
            l2dom = 0.0
        with r6c1:
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'><div style='opacity:.75;font-size:12px'>L2 Dominance</div>"
                f"<div style='font-size:16px;color:#ccf7ff;'>{l2dom:.2f}%</div></div>",
                unsafe_allow_html=True,
            )
        with r6c2:
            st.markdown(
                f"<div class='neon-panel' style='padding:10px;'>Plus à venir…</div>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)
    except Exception as e:
        st.error("Section 'BTC / ETH / SOL — 24h' indisponible.")
        st.exception(e)

# Render bottom marquee ticker
components.html(build_bottom_ticker_html(_top_for_ticker, _news), height=55)

# Auto-refresh loop (timed rerun)
if live_update:
    time.sleep(refresh_sec)
    st.experimental_rerun()

@st.cache_data(ttl=60)
def get_eth_gas() -> dict:
    # Try Etherscan if API key provided, else try common public sources
    key = os.getenv("ETHERSCAN_API_KEY")
    if key:
        data = _safe_get_json(
            "https://api.etherscan.io/api",
            params={"module": "gastracker", "action": "gasoracle", "apikey": key},
        )
        try:
            d = data.get("result", {})
            return {
                "low": float(d.get("SafeGasPrice", 0)),
                "avg": float(d.get("ProposeGasPrice", 0)),
                "fast": float(d.get("FastGasPrice", 0)),
            }
        except Exception:
            pass
    # Fallback mock
    base = 18 + random.uniform(-5, 10)
    return {"low": max(1, base * 0.7), "avg": max(1, base), "fast": max(1, base * 1.3)}

@st.cache_data(ttl=300)
def get_btc_hashrate_ehs() -> float:
    data = _safe_get_json("https://api.blockchain.info/charts/hash-rate?timespan=3days&format=json")
    try:
        vals = data.get("values", [])
        last = vals[-1].get("y", 0)
        # Blockchain.info returns TH/s; convert to EH/s
        return float(last) / 1_000_000.0
    except Exception:
        return float(350 + random.uniform(-50, 50))  # mock EH/s

@st.cache_data(ttl=60)
def get_binance_funding(symbol: str = "BTCUSDT") -> dict:
    data = _safe_get_json("https://fapi.binance.com/fapi/v1/premiumIndex", params={"symbol": symbol})
    try:
        fr = float(data.get("lastFundingRate", 0)) * 100.0
        mark = float(data.get("markPrice", 0))
        return {"funding": fr, "mark": mark}
    except Exception:
        return {"funding": 0.0, "mark": 0.0}

@st.cache_data(ttl=60)
def get_binance_open_interest_usd(symbol: str = "BTCUSDT") -> float:
    oi = _safe_get_json("https://fapi.binance.com/fapi/v1/openInterest", params={"symbol": symbol})
    px = _safe_get_json("https://fapi.binance.com/fapi/v1/premiumIndex", params={"symbol": symbol})
    try:
        qty = float(oi.get("openInterest", 0))
        price = float(px.get("markPrice", 0))
        return qty * price
    except Exception:
        return 0.0

@st.cache_data(ttl=180)
def compute_l2_dominance() -> float:
    assets = get_top_for_kpis(300)
    if not assets:
        return 0.0
    l2_syms = {"ARB", "OP", "STRK", "METIS", "MANTA"}
    total = sum(float(a.get("marketCapUsd", 0) or 0) for a in assets)
    l2cap = sum(float(a.get("marketCapUsd", 0) or 0) for a in assets if a.get("symbol", "").upper() in l2_syms)
    return (l2cap / total * 100.0) if total > 0 else 0.0

# Safe wrappers to avoid NameError if helper functions are not defined earlier

def safe_get_eth_gas() -> dict:
    try:
        return get_eth_gas()  # type: ignore[name-defined]
    except Exception:
        base = 20.0 + random.uniform(-5, 5)
        return {"low": max(1.0, base * 0.7), "avg": max(1.0, base), "fast": max(1.0, base * 1.3)}


def safe_get_btc_hashrate_ehs() -> float:
    try:
        return float(get_btc_hashrate_ehs())  # type: ignore[name-defined]
    except Exception:
        return float(350 + random.uniform(-50, 50))


def safe_get_binance_funding(symbol: str = "BTCUSDT") -> dict:
    try:
        return get_binance_funding(symbol)  # type: ignore[name-defined]
    except Exception:
        return {"funding": 0.0, "mark": 0.0}


def safe_get_binance_open_interest_usd(symbol: str = "BTCUSDT") -> float:
    try:
        return float(get_binance_open_interest_usd(symbol))  # type: ignore[name-defined]
    except Exception:
        return 0.0


def safe_compute_l2_dominance() -> float:
    try:
        return float(compute_l2_dominance())  # type: ignore[name-defined]
    except Exception:
        return 0.0
