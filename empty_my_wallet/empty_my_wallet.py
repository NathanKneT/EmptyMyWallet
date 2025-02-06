import os
import logging
import sys
import requests
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from sqlalchemy import text
from typing import Dict, List
import time
from sklearn.ensemble import IsolationForest
from log.logging_config import setup_logging
from db.db import get_db_config
from binance.client import Client
import matplotlib
matplotlib.use('Agg')  # Required for headless environments
import matplotlib.pyplot as plt
from config.config import CONFIG, EXPLORERS, API_KEYS, CHAIN_IDS

class EmptyMyWallet:
    def __init__(self, binance_api_key: str, binance_api_secret: str, test_mode: bool = False):
        self.binance_api_key = binance_api_key
        self.binance_api_secret = binance_api_secret
        self.test_mode = test_mode
        self.logger = setup_logging()
        self.creator_cache = {}
        
        # Log initialization mode
        if self.test_mode:
            self.logger.info("🔬 Initializing bot in TEST MODE - No real trades will be executed")
        else:
            self.logger.info("🚀 Initializing bot in PRODUCTION MODE")

        # Database connection
        try:
            db_config = get_db_config()
            connection_string = (
                f'postgresql+psycopg2://{db_config["user"]}:{db_config["password"]}'
                f'@{db_config["host"]}:{db_config["port"]}/{db_config["dbname"]}'
            )
            
            self.engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600,
                connect_args={
                    'sslmode': 'require'  # Required for Aiven PostgreSQL
                }
            )
            self.logger.info("Database connection established successfully")
        except SQLAlchemyError as e:
            self.logger.error(f"❌ Database connection error: {e}")
            sys.exit(1)

        self._init_db()
        self.model = IsolationForest(n_estimators=100, contamination=0.01)
        self.historical_data = pd.DataFrame()
        
        # Initialize Binance client with test/prod mode
        self.binance_client = self._initialize_binance_client()

    def _initialize_binance_client(self):
        """Initialize Binance client with appropriate endpoint based on mode"""
        try:
            client = Client(self.binance_api_key, self.binance_api_secret)
            if self.test_mode:
                client.API_URL = 'https://testnet.binance.vision'
                self.logger.info("📡 Connected to Binance TestNet API")
            else:
                self.logger.info("📡 Connected to Binance Production API")
            return client
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Binance client: {e}")
            sys.exit(1)

    def _init_db(self):
        """Initialize database with tables for blacklists and pair data."""
        
        create_blacklist_table = text("""
            CREATE TABLE IF NOT EXISTS blacklist (
                address VARCHAR(128) PRIMARY KEY,
                type VARCHAR(20) CHECK (type IN ('coin', 'dev')) NOT NULL,
                reason TEXT NOT NULL,
                listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """)
        
        create_blacklist_index = text("""
            CREATE INDEX IF NOT EXISTS idx_blacklist_type ON blacklist(type);
        """)
        
        create_pairs_table = text("""
            CREATE TABLE IF NOT EXISTS pairs (
                pair_address VARCHAR(128) PRIMARY KEY,
                base_token_name TEXT NOT NULL,
                base_token_address VARCHAR(128) NOT NULL,
                quote_token_address VARCHAR(128) NOT NULL,
                price NUMERIC CHECK (price >= 0),
                liquidity NUMERIC CHECK (liquidity >= 0),
                volume_24h NUMERIC CHECK (volume_24h >= 0),
                chain TEXT NOT NULL,
                exchange TEXT NOT NULL,
                created_at TIMESTAMP,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                creator_address VARCHAR(128)
            );
        """)

        with self.engine.begin() as conn:
            try:
                # Execute each statement separately  
                conn.execute(create_blacklist_table)
                conn.execute(create_blacklist_index)
                conn.execute(create_pairs_table)
                self.logger.info("Database tables created successfully")
            except Exception as e:
                self.logger.error(f"Error creating database tables: {str(e)}")
                raise

        self._seed_initial_blacklists()

    def _seed_initial_blacklists(self):
        """Seed the database with initial blacklists from the config file."""
        
        insert_query = text("""
            INSERT INTO blacklist (address, type, reason)
            VALUES (:address, :type, :reason)
            ON CONFLICT (address) DO NOTHING
        """)

        with self.engine.begin() as conn:
            try:
                # Insert coin blacklist
                for address in CONFIG["FILTERS"]["coin_blacklist"]:
                    conn.execute(insert_query, {
                        "address": address,
                        "type": "coin",
                        "reason": "Predefined blacklist"
                    })

                # Insert dev blacklist
                for address in CONFIG["FILTERS"]["dev_blacklist"]:
                    conn.execute(insert_query, {
                        "address": address,
                        "type": "dev",
                        "reason": "Predefined blacklist"
                    })
                    
                self.logger.info("Initial blacklists seeded successfully")
            except Exception as e:
                self.logger.error(f"Error seeding blacklists: {str(e)}")
                raise

    def add_to_blacklist(self, address: str, blacklist_type: str, reason: str) -> bool:
        """Add an address to the blacklist with a reason."""
        insert_query = text("""
            INSERT INTO blacklist (address, type, reason)
            VALUES (:address, :type, :reason)
            ON CONFLICT (address) DO NOTHING
        """)
        
        with self.engine.begin() as conn:
            try:
                conn.execute(insert_query, {
                    "address": address,
                    "type": blacklist_type,
                    "reason": reason
                })
                self.logger.info(f"Added {address} to blacklist ({blacklist_type}): {reason}")
                return True
            except Exception as e:
                self.logger.error(f"Error adding to blacklist: {str(e)}")
                return False
            

    def apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhanced filtering with None handling."""
        if df.empty:
            return df

        # Créer une copie explicite du DataFrame
        df = df.copy()
        
        # Remplacer None par des valeurs par défaut
        df.loc[:, 'base_token_address'] = df['base_token_address'].fillna('')
        df.loc[:, 'pair_address'] = df['pair_address'].fillna('')
        df.loc[:, 'creator_address'] = df['creator_address'].fillna('')
        df.loc[:, 'base_token_name'] = df['base_token_name'].fillna('').str.lower()

        # Get fresh blacklist data
        with self.engine.begin() as conn:
            coin_blacklist = pd.read_sql(
                "SELECT address FROM blacklist WHERE type = 'coin'", 
                conn
            )['address'].tolist()
            
            dev_blacklist = pd.read_sql(
                "SELECT address FROM blacklist WHERE type = 'dev'", 
                conn
            )['address'].tolist()

        # Address-based filtering
        mask = (
            ~df['base_token_address'].isin(coin_blacklist) &
            ~df['pair_address'].isin(coin_blacklist) &
            ~df['creator_address'].isin(dev_blacklist)
        )
        df = df[mask]
        
        # Symbol-based filtering
        symbol_blacklist = [s.lower() for s in CONFIG["FILTERS"]["coin_blacklist"]]
        df = df[~df['base_token_name'].str.lower().isin(symbol_blacklist)]
        
        return df
    
    def get_contract_creator(self, chain: str, contract_address: str) -> str:
        """Retrieve contract creator with proper parsing"""
        contract_address = contract_address.strip("'\"")
        
        chain = chain.lower()
        if chain not in EXPLORERS:
            self.logger.warning(f"Unsupported chain for contract lookup: {chain}")
            return "Unknown"
        
        url = EXPLORERS[chain]
        api_key = API_KEYS[chain]
        params = {
            "module": "contract",
            "action": "getcontractcreation",
            "contractaddresses": contract_address,
            "apikey": api_key,
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data and data.get("status") == "1" and isinstance(data.get("result"), list):
                    creator = data["result"][0].get("contractCreator")
                    return creator if creator else "Unknown"
            
            return "Unknown"
        
        except Exception as e:
            self.logger.error(f"Creator fetch error for {contract_address}: {e}")
            return "Unknown"

    def process_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Vectorized data processing with address validation"""
        if not raw_data:
            return pd.DataFrame()
            
        try:
            df = pd.json_normalize(raw_data, sep='_')
            
            # Add address validation and trimming
            def validate_address(addr):
                if not isinstance(addr, str):
                    return None
                clean_addr = addr.strip()[:128]
                if len(clean_addr) not in (42, 44) or not clean_addr.startswith(('0x', 'osmo')):
                    return None
                return clean_addr
            
            # Column renaming and type conversion
            processed = pd.DataFrame({
                'pair_address': df['pairAddress'].apply(validate_address),
                'base_token_name': df['baseToken_name'],
                'base_token_address': df['baseToken_address'].apply(validate_address),
                'quote_token_address': df['quoteToken_address'].apply(validate_address),
                'price': pd.to_numeric(df['priceUsd'], errors='coerce'),
                'liquidity': pd.to_numeric(df['liquidity_usd'], errors='coerce'),
                'volume_24h': pd.to_numeric(df['volume_h24'], errors='coerce'),
                'chain': df['chainId'],
                'exchange': df['dexId'],
                'created_at': pd.to_datetime(df['pairCreatedAt'], unit='ms'),
                'timestamp': datetime.utcnow()
            })
            
            # Add creator address with validation
            processed['creator_address'] = processed.apply(
                lambda row: (self.get_contract_creator(row['chain'], row['base_token_address'])[:128] 
                            if pd.notnull(row['base_token_address']) else None), 
                axis=1
            )
            
            return self.apply_filters(processed.dropna())
            
        except Exception as e:
            self.logger.error(f"Error processing data: {str(e)}")
            return pd.DataFrame()
        
    # TODO : Fix les calls API (https://api.rugcheck.xyz/swagger/index.html)

    # def check_rugcheck(self, contract_address: str) -> bool:
    #     """Check if a contract is marked as 'Good' on RugCheck.xyz."""
    #     try:
    #         response = requests.get(f"http://rugcheck.xyz/api/contracts/{contract_address}")
    #         data = response.json()
    #         return data.get("status", "").lower() == "good"
    #     except Exception as e:
    #         print(f"Error checking RugCheck: {e}")
    #         return False
        
    # TODO : Verifier pourquoi cela ne fonctionne pas avec les contract adresse (pas les mêmes chains ?)
    # def check_honeypot(self, contract_address: str) -> bool:
    #     """Vérifie via l'API Honeypot.is avec plus de robustesse"""
    #     if not contract_address or not isinstance(contract_address, str):
    #         self.logger.warning(f"Invalid contract address: {contract_address}")
    #         return True  # Considérer les adresses invalides comme honeypots
        
    #     # Nettoyage de l'adresse (au cas où l'API ait des restrictions de format)
    #     contract_address = contract_address.strip()
        
    #     api_url = f"https://api.honeypot.is/v2/IsHoneypot?address={contract_address}"
    #     self.logger.debug(f"Checking honeypot for address: {contract_address} via {api_url}")

    #     try:
    #         response = requests.get(api_url, timeout=10)
    #         response.raise_for_status()  # Lève une exception si le statut n'est pas 2xx

    #         data = response.json()
    #         result = data.get("isHoneypot", True)  # Par défaut, considérer comme un honeypot si la clé est absente
    #         self.logger.debug(f"Honeypot result for {contract_address}: {result}")
    #         return result

    #     except requests.exceptions.HTTPError as http_err:
    #         self.logger.error(f"HTTP error: {http_err} (Status Code: {response.status_code})")
    #         if response.status_code == 404:
    #             self.logger.warning(f"Contract address {contract_address} not found on Honeypot.is")
    #         return True
    #     except requests.exceptions.Timeout:
    #         self.logger.error(f"Timeout checking honeypot for {contract_address}")
    #         return True
    #     except requests.exceptions.RequestException as e:
    #         self.logger.error(f"Request error checking honeypot: {e}")
    #         return True
    #     except ValueError:
    #         self.logger.error(f"Invalid JSON response from Honeypot API for {contract_address}")
    #         return True
    #     except Exception as e:
    #         self.logger.error(f"Unexpected error in check_honeypot: {str(e)}")
    #         return True

    def check_honeypot(self, chain, address):
        if chain.lower() not in EXPLORERS:
            return {'honeypot': False, 'error': 'Unsupported chain'}
        
        params = {
            'address': address,
            'chainId': CHAIN_IDS[chain.lower()]
        }
        
        try:
            response = requests.get(
                "https://api.honeypot.is/v2/IsHoneypot",
                params=params,
                timeout=10
            )
            return response.json()
        except Exception as e:
            self.logger.error(f"Honeypot check error: {str(e)}")
            return {'error': str(e)}

    def check_bundled_supply(self, contract_address: str, chain: str) -> bool:
        """Check if the token supply is bundled for a given blockchain."""
        if chain not in EXPLORERS or chain not in API_KEYS or not API_KEYS[chain]:
            print(f"Unsupported or missing API key for chain: {chain}")
            return False

        url = (
            f"{EXPLORERS[chain]}?module=account&action=tokenbalance"
            f"&contractaddress={contract_address}"
            f"&address=0x000000000000000000000000000000000000dead"
            f"&tag=latest&apikey={API_KEYS[chain]}"
        )

        try:
            response = requests.get(url)
            response.raise_for_status()  # Lève une exception si le statut HTTP est >= 400
            data = response.json()
            return int(data.get("result", 0)) > 0  # Vérifie si un solde est présent
        except requests.exceptions.RequestException as e:
            print(f"Error checking bundled supply on {chain}: {e}")
            return False

    def detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Détecte les anomalies dans les paires en analysant leurs caractéristiques financières."""
        
        if df.empty:
            logging.warning("Aucune donnée à analyser pour les anomalies.")
            return df

        features = ["price", "liquidity", "volume_24h"]

        # Remplacement des valeurs NaN par la médiane pour éviter les erreurs du modèle
        df[features] = df[features].fillna(df[features].median())

        # Détection des anomalies avec Isolation Forest
        predictions = self.model.fit_predict(df[features])

        # -1 = anomalie, on les filtre
        df_anomalies = df.loc[predictions == -1]

        logging.info(f"Nombre d'anomalies détectées : {len(df_anomalies)}")
        
        return df_anomalies

    def analyze_market_events(self, anomalous_data: pd.DataFrame):
        """Analyze market events and log suspicious activity."""
        for _, row in anomalous_data.iterrows():
            # Check RugCheck.xyz and bundled supply
            # if not self.check_rugcheck(row['base_token_address']):
            #     self.add_to_blacklist(row['base_token_address'], 'coin', 'Failed RugCheck')
            #     continue
            if self.check_bundled_supply(row['base_token_address']):
                self.add_to_blacklist(row['base_token_address'], 'coin', 'Bundled supply')
                self.add_to_blacklist(row['creator_address'], 'dev', 'Bundled supply')
                continue

            # If all checks pass, place a trade
            self.place_trade(row)

    def place_trade(self, row: pd.Series):
        """Place a trade with test mode awareness"""
        symbol = row['base_token_name'] + 'USDT'
        quantity = 10  # Adjust based on your budget

        try:
            if self.test_mode:
                self.logger.info(f"🔬 TEST MODE - Simulated trade for {symbol}: {quantity} units")
                return {"status": "success", "message": "Test trade simulated"}
            
            order = self.binance_client.create_order(
                symbol=symbol,
                side='BUY',
                type='MARKET',
                quantity=quantity
            )
            self.logger.info(f"✅ Trade executed: {symbol}, Quantity: {quantity}")
            return order
            
        except Exception as e:
            self.logger.error(f"❌ Trade failed for {symbol}: {str(e)}")
            return None
        
    def fetch_pair_data(self) -> List[Dict]:
        """Fetch trading pair data from DexScreener API using the /search endpoint."""
        base_url = "https://api.dexscreener.com/latest/dex/search"
        all_pairs = []

        try:
            for chain in CONFIG["FILTERS"]["chain_whitelist"]:
                self.logger.info(f"Fetching pairs for chain: {chain}")

                query = chain  #  A simple search for the chain name.  Improve as needed.
                params = {'q': query, 'limit': 500} # Added a limit, Dexscreener defaults to 25

                response = requests.get(
                    base_url,
                    params=params,
                    headers={'Accept': 'application/json'},
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    # Dexscreener API returns the pairs inside the "pairs" key
                    pairs = data.get('pairs', [])  # Make sure to access the 'pairs' key.
                    all_pairs.extend(pairs)
                    self.logger.info(f"Found {len(pairs)} pairs for {chain}") # Log how many we found
                elif response.status_code == 429:
                    self.logger.warning(f"Rate limit hit for {chain}. Waiting before retry...")
                    time.sleep(60)
                    continue # Retry the same chain after waiting
                else:
                    self.logger.error(f"Error fetching {chain} pairs: Status {response.status_code} - {response.text}") # Include response text for debugging
                    continue # Move onto the next chain

                time.sleep(1)  # Rate limiting
                
            self.logger.info(f"Total pairs fetched: {len(all_pairs)}")
            return all_pairs
            
        except requests.RequestException as e:
            self.logger.error(f"Network error while fetching pairs: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in fetch_pair_data: {str(e)}")
            return []

    def _filter_minimum_pairs(self, pairs: List[Dict]) -> List[Dict]:
        """Filter pairs based on minimum requirements"""
        filtered_pairs = []
        
        for pair in pairs:
            # Basic validation of required fields
            required_fields = ['pairAddress', 'baseToken', 'quoteToken', 
                            'priceUsd', 'liquidity', 'volume']
                            
            if all(field in pair for field in required_fields):
                # Check minimum liquidity
                try:
                    liquidity = float(pair.get('liquidity', 0))
                    if liquidity >= CONFIG["FILTERS"]["min_liquidity"]:
                        filtered_pairs.append(pair)
                except (ValueError, TypeError):
                    continue
                    
        return filtered_pairs
    
    def _refresh_blacklists(self):
        """Refresh blacklists using proper SQLAlchemy text() wrapper"""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    DELETE FROM blacklist 
                    WHERE listed_at < NOW() - INTERVAL '7 days'
                """))
            self.logger.info("Blacklists refreshed successfully")
        except Exception as e:
            self.logger.error(f"Error refreshing blacklists: {str(e)}")

    def run(self):
        """Enhanced main loop with saved plots."""
        import signal
        
        def signal_handler(signum, frame):
            """Gestionnaire de signal pour sauvegarder les graphiques avant de quitter"""
            self.logger.info("🛑 Arrêt du programme détecté, sauvegarde des graphiques...")
            try:
                if 'anomalies_history' in locals() and 'scores_history' in locals():
                    self.save_training_plots(anomalies_history, scores_history)
                self.logger.info("✅ Graphiques sauvegardés avec succès")
            except Exception as e:
                self.logger.error(f"❌ Erreur lors de la sauvegarde finale: {str(e)}")
            sys.exit(0)

        # Mise en place des gestionnaires de signaux
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # kill

        self.logger.info("🚀 Starting DexScreener Bot")
        self.logger.info(f"Mode: {'TEST' if self.test_mode else 'PRODUCTION'}")

        anomalies_history = []  # Historique des anomalies détectées
        scores_history = []  # Historique des scores du modèle

        while True:
            try:
                self.logger.info("🔄 Starting new analysis cycle")

                # Récupération des données
                raw_data = self.fetch_pair_data()
                self.logger.info(f"📊 Fetched {len(raw_data)} pairs")

                # Traitement des données
                processed_data = self.process_data(raw_data)
                self.logger.info(f"✨ Processed {len(processed_data)} valid pairs")

                if not processed_data.empty:
                    # Debug: Afficher les colonnes et échantillon des données
                    self.logger.debug(f"Columns in processed_data: {processed_data.columns.tolist()}")
                    self.logger.debug("Sample of base_token_addresses:")
                    self.logger.debug(processed_data["base_token_address"].head())

                    # Vérification Honeypot avec gestion d'erreur détaillée
                    try:
                        honeypot_results = []
                        for _, row in processed_data.iterrows():
                            chain = row['chain']
                            address = row['base_token_address']
                            
                            result = self.check_honeypot(chain, address)
                            
                            # Check if the result indicates a honeypot
                            is_honeypot = result.get('isHoneypot', True)  # Default to True if key is missing
                            honeypot_results.append(is_honeypot)
                        
                        # Filter out honeypots
                        processed_data = processed_data[~pd.Series(honeypot_results, index=processed_data.index)]
                        self.logger.info(f"🛡️ Filtered {len(processed_data)} pairs after Honeypot check")
                    except Exception as e:
                        self.logger.error(f"Honeypot check error: {str(e)}")
                        continue

                    # Détection des anomalies
                    anomalies = self.detect_anomalies(processed_data)
                    self.logger.info(f"🔍 Detected {len(anomalies)} anomalies")

                    # Stockage des données
                    processed_data.to_sql('pairs', self.engine, if_exists='append', index=False)
                    self.logger.info("💾 Data stored in database")

                    # Analyse et trading
                    self.analyze_market_events(anomalies)

                    # Mise à jour des données historiques
                    self.historical_data = pd.concat([self.historical_data, processed_data]).tail(100000)

                    # Re-training du modèle si suffisamment de données
                    if len(self.historical_data) >= 100_000:
                        self.logger.info("🤖 Re-training the model...")
                        self.model.fit(self.historical_data[["price", "liquidity", "volume_24h"]])
                        scores = self.model.decision_function(self.historical_data[["price", "liquidity", "volume_24h"]])
                        scores_history.append(scores.mean())

                    # Enregistrement des anomalies
                    anomalies_history.append(len(anomalies))

                    # Sauvegarde périodique des graphiques
                    try:
                        self.save_training_plots(anomalies_history, scores_history)
                    except Exception as e:
                        self.logger.error(f"❌ Error saving periodic graphs: {str(e)}")

                # Rafraîchissement des blacklists
                self._refresh_blacklists()
                self.logger.info("😴 Waiting for next cycle...")
                time.sleep(60)

            except Exception as e:
                self.logger.error(f"❌ Runtime error: {str(e)}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                time.sleep(60)

    def save_training_plots(self, anomalies_history, scores_history):
        """Méthode séparée pour sauvegarder les graphiques d'entraînement"""
        if not anomalies_history:  # Si pas de données, ne rien faire
            return

        fig, ax = plt.subplots(1, 2, figsize=(15, 5))
        fig.suptitle("Modèle IA - Évolution de l'Entraînement")
        
        # Premier graphique
        ax[0].set_title("Nombre d'Anomalies Détectées")
        ax[0].set_xlabel("Cycle")
        ax[0].set_ylabel("Anomalies")
        ax[0].plot(anomalies_history, label="Anomalies détectées", color="red")
        ax[0].legend()

        # Deuxième graphique
        if scores_history:  # Ne tracer que s'il y a des scores
            ax[1].set_title("Performance du Modèle (Score Moyen)")
            ax[1].set_xlabel("Cycle")
            ax[1].set_ylabel("Score")
            ax[1].plot(scores_history, label="Score moyen", color="blue")
            ax[1].legend()

        # Ajuster la mise en page
        plt.tight_layout()
        
        # Sauvegarde avec gestion d'erreur et chemin absolu
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "training_evolution.png")
        plt.savefig(save_path)
        plt.close(fig)
        self.logger.info(f"📊 Graphs saved to {save_path}")