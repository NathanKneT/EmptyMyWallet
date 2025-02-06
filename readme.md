
# EmptyMyWallet 💸

Les taux des livrets diminuent tandis que l'inflation continue d'augmenter. C'est dans une volonté d'investir en minimisant les risque que j'ai développé cet outil. **EmptyMyWallet est un bot de trading** intelligent qui analyse les données DeFi via DexScreener, détecte les opportunités grâce au machine learning, et exécute des trades sécurisés sur Binance. Il intègre une protection anti-arnaque avec RugCheck et une analyse en temps réel des liquidités.

Disclaimer ⚠️ : Ce projet est à but éducatif et ne constitue pas un conseil financier. Investissez uniquement ce que vous pouvez vous permettre de perdre. Il est conseiller de ne le lancer uniquement en mode "Test" ou bien de le faire tourner sur un compte Binance dédié à cet usage.

![Architecture du bot](frontend/crypto-bot.jpg)

## Fonctionnalités Clés 🚀

- **🕵️ Analyse On-Chain Avancée**
  - Récupération des données de pairs depuis DexScreener
  - Détection du créateur du contrat via Etherscan/BscScan
  - Vérification de la réputation sur RugCheck.xyz
  - Détection de l'approvisionnement groupé (Bundled Supply)

- **🤖 Intelligence Artificielle**
  - Détection d'anomalies avec Isolation Forest
  - Modèle entraîné sur 100 000 points de données historiques
  - Analyse multivariée (prix, liquidité, volume)

- **🔒 Sécurité Renforcée**
  - Double liste noire (token + développeur)
  - Filtres dynamiques anti-honeypot
  - Mode test sans risque avec Binance Testnet

- **📊 Gestion des Données**
  - Stockage PostgreSQL sécurisé (SSL/TLS)
  - Mise à jour automatique des listes noires
  - Historique des trades accessible via SQL

## Prérequis 📋

- Python 3.10+
- Compte Binance [Obtenir](https://www.binance.com/)
- Clés API :
  - Binance (Production et TestNet)
  - Etherscan ([Obtenir](https://etherscan.io/apis))
  - BscScan ([Obtenir](https://bscscan.com/apis))
  - Polygon ([Obtenir](https://polygonscan.com/apis))

## Installation 🛠️

1. **Cloner le dépôt**
```bash
git clone https://github.com/yourusername/empty-my-wallet-bot.git
cd empty-my-wallet-bot
```

2. **Configurer l'environnement**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d'environnement (.env)**
```ini
# Binance
BINANCE_API_KEY="votre_cle_production"
BINANCE_API_SECRET="votre_secret_production"

# Database
POSTGRES_HOST="votre-host.com"
POSTGRES_PORT=12345
POSTGRES_DB="defaultdb"
POSTGRES_USER="admin"
POSTGRES_PASSWORD="votre-mot-de-passe"

# Explorers
ETHERSCAN_API="votre_cle_etherscan"
BSCSCAN_API="votre_cle_bscscan"
POLYGON_API="votre_cle_polygon"

TEST_MODE="true"  # Mode test (Pour éviter les trades mais tracking réel)
```

## Configuration ⚙️

`config/config.yaml`
```yaml
FILTERS:
  min_liquidity: 10000    # Liquidité minimum en USD
  max_age_days: 7         # Âge maximum des pairs
  chain_whitelist:        # Blockchains surveillées
    - "ethereum"
    - "bsc"
    - "polygon"

RISK_MANAGEMENT:
  max_trade_size: 100     # USD par trade
  daily_loss_limit: 500   # USD de perte max/jour
  slippage_tolerance: 1.5 # % de slippage accepté

ANALYSIS:
  model_refresh: 3600     # Intervalle de réentraînement (secondes)
  anomaly_threshold: -0.7 # Seuil de détection d'anomalie
```

## Utilisation 🚦

**Lancer en mode production**
```bash
python main.py
```

**Commandes optionnelles**
```bash
--interval 300       # Analyse toutes les 5 minutes
--liquidity 5000     # Modifie la liquidité minimum
--chains eth,bsc     # Filtre les blockchains
```

## Structure du Projet 📂
```
empty-my-wallet-bot/
├── main.py                 # Point d'entrée principal
├── config/
│   ├── __init__.py
│   ├── config.py          # Gestion de la configuration
├── log/
│   └── dex_screener_bot.log # Log du backend
│   └── logging_config.py  # Configuration des logs
├── db/
│   └── db.py        # Interactions PostgreSQL
├── empty_my_wallet/
│   └── empty_my_wallet.py       # Ici que la magie opère
├── utils/
│   ├── security.py        # Filtres et listes noires (A FAIRE)
│   └── analytics.py       # Modèles d'IA (A FAIRE)
├── frontend/
│   └── front.py        # Permet d'avoir des indicateurs de la DB
├── .env.example            # Template à prendre pour les .env
├── requirements.txt        # Fichier qui regroupe toutes les dépendances

```

## Workflow d'Analyse 🔄
1. Récupération des pairs depuis DexScreener
2. Validation des adresses et nettoyage des données
3. Vérification des listes noires (on-chain et locale)
4. Détection d'anomalies avec Isolation Forest
5. Exécution des trades sur Binance (si conditions remplies)
6. Mise à jour de la base de données et des listes noires

## Sécurité 🔐
- Toutes les communications chiffrées (HTTPS/SSL)
- Gestion sécurisée des clés API (dotenv)
- Audit automatique des contrats intelligents
- Isolation complète des environnements test/prod

## Contribution 🤝
Les contributions sont les bienvenues ! Veuillez :
1. Forker le projet
2. Créer une branche (`git checkout -b feature/newfeat`)
3. Commiter vos changements (`git commit -m 'Add some newfeat'`)
4. Pousser vers la branche (`git push origin feature/newfeat`)
5. Ouvrir une Pull Request

## Licence 📄
Distribué sous licence MIT. Voir `LICENSE` pour plus d'informations.

---

**Développé par [Nathan RIHET](https://www.linkedin.com/in/nathan-rihet/) | N'investissez que ce que vous pouvez perdre !**
