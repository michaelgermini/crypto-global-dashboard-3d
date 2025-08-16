## Crypto Global Dashboard 3D

An immersive, cyberpunk‑styled 3D crypto market dashboard. It blends a real‑time, interactive globe (Three.js) with live market insights (Streamlit + Altair) to give a high‑signal overview of global activity.

### Demo

- Live: https://crypto-global-dashboard-3d.streamlit.app/

### What it does
- 3D globe market view
  - Rotating globe with luminous city hubs (hover tooltips: volume, top coins, trend)
  - Animated links between major hubs, starfield, atmospheric glow
  - Extra configurable 3D points to visualize broader activity
- Live market panels
  - Top 10 traded cryptos with 24h sparklines and per‑asset details
  - Multi‑asset 24h lines for BTC/ETH/SOL, plus a Top‑5 comparison chart
  - Global KPIs: total market cap, 24h volume, BTC/ETH/ALT dominance, breadth, median change
  - Insights: stablecoin dominance, exchanges count, Fear & Greed, watchlist alerts, BTC volatility
  - Derivatives view (Binance): funding rate (BTCUSDT) and open interest approximation
  - Depth (Binance): simple order‑book area for BTC/ETH/SOL
- Tickers and UX
  - Top metrics + news RSS ticker below the header
  - Permanent bottom marquee ticker
  - Sidebar controls: globe auto‑rotation/speed, zoom distance, extra points, live auto‑refresh

### Tech stack
- App: Streamlit (Python)
- 3D: Three.js (embedded via Streamlit HTML component)
- Charts: Altair/Vega‑Lite
- Data sources:
  - CoinCap (assets, history, globals)
  - Binance (depth, funding, premium index, open interest)
  - Etherscan (optional; ETH gas via `ETHERSCAN_API_KEY`)
  - RSS (CoinDesk / CoinTelegraph) for headlines
- Fallbacks: graceful mock data when APIs are unavailable

### Run locally
1) Python 3.10+
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Quick deploy (Streamlit Community Cloud)
- Repo: michaelgermini/crypto-global-dashboard-3d
- Branch: main
- App file: `streamlit_app.py`
- Dependencies: `requirements.txt`
- Secrets (optional):
  - `ETHERSCAN_API_KEY` for live ETH gas

### Configuration
- Sidebar toggles allow auto‑rotation, rotation speed, camera distance (zoom), number of extra 3D points, and live update interval.
- When network/API access is restricted, the app falls back to demo data so the 3D and charts remain functional.

### Roadmap ideas
- WebSocket streaming for lower‑latency updates
- Additional categories (L2/AI/RWA) and sector heatmaps
- Portfolio/watchlist persistence and alert notifications
- Texture/shader enhancements for the globe
