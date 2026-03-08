You are an expert Python developer building a portfolio rebalancing tool using Streamlit and the Public.com API. Create a professional, production-ready application with the following specifications:

## Core Requirements

### Authentication & Setup
- Use Public.com API with API key authentication
- Store API key securely in Streamlit secrets or user input
- Include proper error handling for API failures and rate limiting

### Main Features
1. **Account Dashboard**
   - Display net liquidation value and cash balance prominently
   - Show positions table with: symbol, quantity, market value, cost basis, unrealized P&L, P&L percentage
   - Real-time market prices from Public.com API
   - Auto-refresh capability for live data

2. **Asset Allocation Management**
   - Manual percentage input for target allocations across Public.com's asset categories:
     EQUITY, OPTION, CRYPTO, ALT, TREASURY, BOND, INDEX
   - Validation that percentages sum to 100%
   - Visual comparison of current vs target allocations using pie charts

3. **Rebalancing Engine**
   - Calculate required trades to achieve target allocations
   - Support fractional shares for all asset types
   - Invest maximum available cash without going negative
   - Generate market orders only
   - Show detailed transaction preview table with: action (buy/sell), symbol, quantity, estimated cost/proceeds

4. **Test Mode Toggle**
   - Prominent toggle switch for test vs live mode
   - Test mode: show all calculations and previews without executing trades
   - Live mode: include confirmation dialogs before executing
   - Clear visual indicators of current mode

### Technical Implementation

#### Code Structure
- Use object-oriented design with separate classes for:
  - PublicAPIClient (API interactions)
  - PortfolioAnalyzer (calculations and rebalancing logic)
  - StreamlitUI (interface components)
- Implement proper error handling and logging
- Use type hints throughout
- Follow PEP 8 style guidelines

#### Streamlit Layout
- Sidebar: API key input, test mode toggle, target allocation inputs
- Main area: Account overview, current positions table, allocation charts
- Rebalancing section: transaction preview, execute button
- Status messages and progress indicators

#### Data Management
- Use Streamlit session state for maintaining data between interactions
- Implement caching for API calls where appropriate
- Real-time price updates with configurable refresh intervals

#### Visualization Requirements
- Professional-looking pie charts comparing current vs target allocations
- Color-coded P&L in positions table (green for gains, red for losses)
- Clean, responsive design that works on desktop and mobile
- Loading spinners for API calls

#### Safety Features
- Confirmation dialogs for live trades
- Input validation for all user inputs
- Clear error messages for API failures or invalid operations
- Dry-run calculations showing exact trade impacts

#### API Integration
- Robust error handling for network issues
- Proper request rate limiting
- Secure credential management
- Comprehensive logging for debugging

## Code Quality Standards
- Write clean, maintainable, well-documented code
- Include docstrings for all functions and classes
- Use meaningful variable names and comments
- Implement proper exception handling
- Follow single responsibility principle
- Make code modular and testable

## User Experience
- Intuitive interface requiring minimal learning curve
- Clear visual feedback for all actions
- Professional styling with consistent color scheme
- Responsive design elements
- Helpful tooltips and explanations where needed

Generate complete, production-ready code that can be run immediately with `streamlit run app.py` after adding the Public.com API key. Include all necessary imports, error handling, and a professional UI that looks like a real financial application.