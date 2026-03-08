# Public.com Portfolio Rebalancing Tool

A Streamlit application that connects to the **Public.com API** to monitor your brokerage portfolio and execute rebalancing trades in real-time.

## Features

- **Live Portfolio Dashboard** — View positions, P&L, and account balances pulled directly from Public.com
- **Target Allocation Management** — Set per-ticker target allocations with validation
- **Bulk Ticker Upload** — Import tickers via CSV file or paste multiple tickers at once
- **Instrument Validation** — Verify that tickers are actually tradable on Public.com before placing orders
- **Smart Rebalancing Engine** — Calculates optimal buy/sell trades to reach your target allocations
- **Order Preflight** — Preview estimated costs and buying power requirements before execution
- **Live Order Execution** — Place real market orders on Public.com with confirmation safeguards
- **Test Mode** — Simulate everything without touching your account
- **Order Status Tracking** — Monitor submitted orders and check fill status

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Your API Key

Get your API key from the [Public.com Developer Portal](https://public.com/developer).

**Option A — Streamlit secrets (recommended for local use):**

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml and add your key
```

**Option B — Environment variable:**

```bash
export PUBLIC_API_KEY="your_api_key_here"
```

**Option C — Enter it in the sidebar** when the app launches.

### 3. Run the App

```bash
streamlit run app.py
```

## Bulk Ticker Upload

You can import tickers in two ways:

### CSV Upload

Upload a `.csv` file with columns `symbol` and `percentage`:

```csv
symbol,percentage
AAPL,25
MSFT,25
GOOGL,20
AMZN,15
TSLA,15
```

### Paste Text

Paste tickers directly, one per line. Supported formats:

```
AAPL 25
MSFT,25
GOOGL:20
AMZN=15
TSLA 15%
```

If you omit percentages, use the **Auto-distribute evenly** button to split allocation equally.

## How It Works

1. **Connect** — The app exchanges your API secret for a short-lived access token
2. **Fetch** — Pulls your account info, positions, and live quotes from Public.com
3. **Analyze** — Compares your current allocation to your targets
4. **Calculate** — Determines the optimal trades (buys and sells) to rebalance
5. **Execute** — Places market orders via the Public.com trading API (or simulates in test mode)

## Project Structure

```
├── app.py                          # Streamlit entry point
├── requirements.txt                # Python dependencies
├── .streamlit/
│   ├── config.toml                 # Streamlit config
│   └── secrets.toml.example        # API key template
├── src/
│   ├── api/
│   │   └── client.py               # Public.com API client
│   ├── portfolio/
│   │   └── analyzer.py             # Rebalancing engine
│   ├── ui/
│   │   └── main_app.py             # Streamlit UI
│   └── utils/
│       ├── calculations.py         # Helper math functions
│       └── logger.py               # Logging setup
├── config/
│   └── settings.py                 # App configuration
├── tests/
│   ├── test_api_client.py
│   └── test_portfolio_analyzer.py
└── scripts.py                      # Dev utility scripts
```

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/userapiauthservice/personal/access-tokens` | POST | Generate access token |
| `/userapigateway/trading/account` | GET | List accounts |
| `/userapigateway/trading/{id}/portfolio/v2` | GET | Get portfolio & positions |
| `/userapigateway/trading/instruments/{sym}/{type}` | GET | Validate instrument |
| `/userapigateway/marketdata/{id}/quotes` | POST | Get live quotes |
| `/userapigateway/trading/{id}/preflight/single-leg` | POST | Order preview |
| `/userapigateway/trading/{id}/order` | POST | Place order |
| `/userapigateway/trading/{id}/order/{oid}` | GET | Check order status |
| `/userapigateway/trading/{id}/order/{oid}` | DELETE | Cancel order |

## Safety

- **Test Mode** is on by default — no real orders are placed
- **Instrument Validation** checks that tickers exist on Public.com before trading
- **Order Preflight** shows estimated costs and requirements
- **Confirmation Checkbox** required before live execution
- **Zero commissions** on Public.com (no hidden fees)

## Requirements

- Python 3.9+
- A funded Public.com brokerage account
- A Public.com API key (secret)

## License

MIT
