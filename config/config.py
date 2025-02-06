import logging
import os
import yaml

# Configuration par défaut
DEFAULT_CONFIG = {
    "DB": {
        "dbname": "dexscreener",
        "user": os.getenv("POSTGRES_USER", "admin"),
        "password": os.getenv("POSTGRES_PASSWORD", "your_password"),
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": 5432,
    },
    "FILTERS": {
        "min_liquidity": 5000,
        "min_age_days": 3,
        "coin_blacklist": [],
        "dev_blacklist": [],
        "chain_whitelist": ["ethereum", "bsc", "polygon"],
    }
}

# Dictionnaire des explorateurs de blockchain
EXPLORERS = {
    "ethereum": "https://api.etherscan.io/api",
    "bsc": "https://api.bscscan.com/api",
    "polygon": "https://api.polygonscan.com/api",
}

CHAIN_IDS = {
    'ethereum': 1,
    'bsc': 56,
    'polygon': 137
}

# Clés API des explorers
API_KEYS = {
    "ethereum": os.getenv("ETHERSCAN_API"),
    "bsc": os.getenv("BSC_API"),
    "polygon": os.getenv("POLYGON_API"),
}

# Fonction de chargement de la configuration
def load_config(config_path="config/config.yaml"):
    try:
        # Tentative de chargement du fichier YAML
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file)
        
        # Si la configuration est manquante ou invalide, retour à la configuration par défaut
        if not config:
            raise ValueError("Le fichier de configuration est vide.")
        
        logging.info("Configuration chargée avec succès.")
        return config
    except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
        logging.error(f"Erreur lors du chargement du fichier de configuration: {e}")
        logging.info("Chargement de la configuration par défaut.")
        return DEFAULT_CONFIG

# Chargement de la configuration
CONFIG = load_config()
