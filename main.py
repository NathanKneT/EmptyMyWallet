
import os
import sys
from dotenv import load_dotenv
from empty_my_wallet.empty_my_wallet import EmptyMyWallet

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()

    binance_api_key = os.getenv("BINANCE_API_KEY")
    binance_api_secret = os.getenv("BINANCE_API_SECRET")
    test_mode = os.getenv("TEST_MODE", "True").lower() == "true"  # Default to test mode

    if not binance_api_key or not binance_api_secret:
        print("❌ Binance API keys missing in .env file")
        sys.exit(1)

    # Initialize and run bot
    bot = EmptyMyWallet(
        binance_api_key=binance_api_key,
        binance_api_secret=binance_api_secret,
        test_mode=test_mode
    )
    
    bot.run()