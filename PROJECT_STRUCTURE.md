# Project Structure

```
Public.Com-Portfolio-Rebalance/
├── app.py                              # Streamlit entry point
├── requirements.txt                    # Python dependencies
├── scripts.py                          # Dev utility scripts
├── test_api.py                         # CLI API connection tester
├── README.md                           # Project documentation
├── PROJECT_STRUCTURE.md                # This file
├── DEPLOYMENT.md                       # Deployment guide
│
├── .streamlit/
│   ├── config.toml                     # Streamlit configuration
│   └── secrets.toml.example            # API key template
│
├── .github/
│   ├── TODO.md                         # Development tracking
│   ├── project-spec.md                 # Original spec
│   ├── copilot-instructions.md         # AI coding assistant context
│   └── docs/
│       └── public_api_docs.md          # Public.com API reference
│
├── config/
│   ├── __init__.py
│   └── settings.py                     # App configuration constants
│
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── client.py                   # Public.com API client
│   │       - Authentication & token management
│   │       - Account & portfolio fetching
│   │       - Instrument lookup & validation
│   │       - Quote retrieval
│   │       - Order preflight, placement, status, cancellation
│   │
│   ├── portfolio/
│   │   ├── __init__.py
│   │   └── analyzer.py                 # Rebalancing engine
│   │       - Current allocation calculation
│   │       - Target vs actual comparison
│   │       - Trade recommendation generation
│   │       - Cash-aware order sizing
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   └── main_app.py                 # Streamlit UI
│   │       - Sidebar: API key, mode toggle, allocation editor
│   │       - Bulk ticker upload (CSV + paste)
│   │       - Instrument validation
│   │       - Portfolio dashboard & charts
│   │       - Rebalance analysis display
│   │       - Order preflight preview
│   │       - Trade simulation & live execution
│   │       - Order status tracking
│   │
│   └── utils/
│       ├── __init__.py
│       ├── calculations.py             # Math helpers
│       └── logger.py                   # Logging setup
│
├── assets/
│   └── styles.py                       # (legacy) CSS styles
│
└── tests/
    ├── __init__.py
    ├── test_api_client.py
    └── test_portfolio_analyzer.py
```
