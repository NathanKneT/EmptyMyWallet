# Development Environment Setup

## Prerequisites

- **Python 3.10+**: Ensure Python is installed on your system.
- **Binance Account**: Create an account at [Binance](https://www.binance.com).
- **API Keys**:
  - Binance (Production and TestNet)
  - Etherscan ([Get Here](https://etherscan.io/register))
  - BscScan ([Get Here](https://bscscan.com/register))
  - Polygon ([Get Here](https://polygonscan.com/register))

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/empty-my-wallet-bot.git
   cd empty-my-wallet-bot
   ```

2. **Set Up a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the root directory and add the following:
   ```env
   # Binance
   BINANCE_API_KEY="your_production_key"
   BINANCE_API_SECRET="your_production_secret"

   # Database
   POSTGRES_HOST="your-host.com"
   POSTGRES_PORT=12345
   POSTGRES_DB="defaultdb"
   POSTGRES_USER="admin"
   POSTGRES_PASSWORD="your-password"

   # Explorers
   ETHERSCAN_API="your_etherscan_key"
   BSCSCAN_API="your_bscscan_key"
   POLYGON_API="your_polygon_key"

   TEST_MODE="true"  # Test mode (For tracking without real trades)
   ```

5. **Database Setup**:
   - Ensure PostgreSQL is installed and running.
   - Update the `.env` file with your database credentials.
   - Run the bot to initialize the database tables.

## Running the Bot

1. **Production Mode**:
   ```bash
   python main.py
   ```

2. **Optional Commands**:
   ```bash
   --interval 300       # Runs analysis every 5 minutes
   --liquidity 5000     # Adjusts minimum liquidity
   --chains eth,bsc     # Filters blockchains
   ```

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the project.
2. Create a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. Commit your changes:
   ```bash
   git commit -m 'Add amazing feature'
   ```
4. Push to the branch:
   ```bash
   git push origin feature/amazing-feature
   ```
5. Open a Pull Request.

## Testing

- Run unit tests:
  ```bash
  pytest tests/
  ```
- Ensure all tests pass before submitting a PR.