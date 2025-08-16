## Crypto Global Dashboard 3D

Immersive 3D interface inspired by Tron/Cyberpunk to visualize global crypto activity, built with Streamlit and powered by embedded Three.js.

### Demo

- Live: https://crypto-global-dashboard-3d.streamlit.app/

### Run locally

1. Create a Python 3.10+ environment (recommended)
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Start the app:
```bash
streamlit run streamlit_app.py
```

### Features
- Rotating 3D globe with glowing city hubs (interactive hover)
- Animated links between major hubs, particles and atmospheric glow
- Side panels:
  - Top 10 cryptos (with 24h sparklines)
  - 24h lines for BTC/ETH/SOL
  - Global indicators (market cap, 24h volume)

### Data
- Sourced from the public CoinCap API. If the network is unavailable, a degraded mode generates demo data.

### Notes
- The app embeds Three.js via an HTML component; no separate JS build required.
- This is a base you can extend with textures, shaders, and real-time data sources.
