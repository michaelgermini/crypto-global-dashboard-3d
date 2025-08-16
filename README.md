## Crypto Global Dashboard 3D

Interface 3D immersive d'inspiration Tron/Cyberpunk pour visualiser l'activité crypto mondiale, intégrée dans Streamlit et propulsée par Three.js (embarqué via HTML).

### Lancer localement

1. Créez un environnement Python 3.10+ (recommandé)
2. Installez les dépendances:
```bash
pip install -r requirements.txt
```
3. Lancez l'app:
```bash
streamlit run streamlit_app.py
```

### Fonctionnalités
- Globe 3D rotatif avec points lumineux sur les hubs économiques (survol interactif)
- Liens animés entre hubs majeurs, particules et glow atmosphérique
- Panneaux latéraux:
  - Top 10 cryptos (avec sparklines 24h)
  - Courbes 24h BTC/ETH/SOL normalisées
  - Indicateurs globaux (market cap, volume 24h)

### Données
- Récupération via l'API publique CoinCap. En cas d'indisponibilité réseau, un mode dégradé génère des données de démonstration.

### Notes
- L'app embarque Three.js via un composant HTML, aucune config JS séparée requise.
- Ce projet est une base: libre à vous d'ajouter textures, shaders, et sources de données temps réel.
