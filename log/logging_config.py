import logging
import sys

def setup_logging():
    """Setup logging with UTF-8 encoding support"""
    logger = logging.getLogger("DexScreenerBot")
    logger.setLevel(logging.INFO)

    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler("log/dex_screener_bot.log", encoding='utf-8')
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)  # Use stdout instead of stderr
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s: %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger