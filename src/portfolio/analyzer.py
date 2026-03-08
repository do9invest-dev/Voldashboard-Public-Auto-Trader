"""
Portfolio Analysis and Rebalancing Engine

Handles portfolio analysis, target allocation management, and rebalancing
calculations with support for fractional shares and cash optimization.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
import logging

from src.api.client import Account, Position, Instrument

logger = logging.getLogger(__name__)


@dataclass
class AllocationTarget:
    """Represents a target allocation for a specific ticker."""
    ticker: str
    target_percentage: float
    asset_class: Optional[str] = None  # Will be determined from API


@dataclass
class TradeRecommendation:
    """Represents a recommended trade to achieve target allocation."""
    action: str  # BUY or SELL
    instrument: Instrument
    quantity: Decimal
    estimated_value: Decimal
    current_quantity: Decimal
    reason: str


@dataclass
class RebalanceAnalysis:
    """Complete analysis of a portfolio rebalance."""
    current_allocations: Dict[str, float]  # ticker -> percentage
    target_allocations: Dict[str, float]   # ticker -> percentage
    allocation_differences: Dict[str, float]  # ticker -> difference
    recommended_trades: List[TradeRecommendation]
    cash_to_invest: Decimal
    total_portfolio_value: Decimal
    estimated_transaction_costs: Decimal
    asset_class_summary: Dict[str, float]  # asset_class -> total percentage


class PortfolioAnalyzer:
    """
    Analyzes portfolios and calculates optimal rebalancing trades.
    
    Now supports ticker-based allocations with asset class detection
    from Public.com API responses.
    """
    
    # Supported asset classes from Public.com API
    ASSET_CLASSES = {
        'EQUITY': 'Stocks and ETFs',
        'OPTION': 'Options Contracts', 
        'CRYPTO': 'Cryptocurrency',
        'ALT': 'Alternative Investments',
        'TREASURY': 'Treasury Securities',
        'BOND': 'Bonds',
        'INDEX': 'Index Funds'
    }
    
    def __init__(self, rebalance_threshold_pct: float = 1.0):
        """
        Initialize the portfolio analyzer.

        Args:
            rebalance_threshold_pct: Minimum allocation difference (in percentage
                points) required to trigger a rebalance trade. For example, 1.0
                means a ticker must be at least 1% off its target before a trade
                is generated. Set to 0 to disable.
        """
        self.minimum_trade_value = Decimal('1.00')  # Minimum $1 trade
        self.precision = Decimal('0.000001')  # 6 decimal places for fractional shares
        self.rebalance_threshold_pct = rebalance_threshold_pct
    
    def calculate_current_allocations(self, account: Account) -> Dict[str, float]:
        """
        Calculate current allocation percentages by ticker.
        
        Args:
            account: Account with positions to analyze
            
        Returns:
            Dictionary mapping ticker symbol to current percentage
        """
        if account.net_liquidation_value <= 0:
            return {}
        
        allocations = {}
        
        # Add cash allocation
        if account.cash_balance > 0:
            cash_percentage = (account.cash_balance / account.net_liquidation_value) * 100
            allocations['CASH'] = cash_percentage
        
        # Calculate allocation for each position by ticker
        for position in account.positions:
            ticker = position.instrument.symbol
            allocation_percent = (position.current_value / account.net_liquidation_value) * 100
            allocations[ticker] = allocation_percent
        
        return allocations
    
    def get_asset_class_summary(
        self, 
        ticker_allocations: Dict[str, float],
        positions: List[Position]
    ) -> Dict[str, float]:
        """
        Summarize allocations by asset class based on position data.
        
        Args:
            ticker_allocations: Dictionary of ticker -> percentage
            positions: List of positions with asset class info
            
        Returns:
            Dictionary of asset_class -> total percentage
        """
        asset_class_summary = {}
        
        # Create ticker to asset class mapping from positions
        ticker_to_asset_class = {}
        for position in positions:
            ticker_to_asset_class[position.instrument.symbol] = position.instrument.type
        
        # Add cash
        if 'CASH' in ticker_allocations:
            asset_class_summary['CASH'] = ticker_allocations['CASH']
        
        # Sum up by asset class
        for ticker, percentage in ticker_allocations.items():
            if ticker == 'CASH':
                continue
            
            asset_class = ticker_to_asset_class.get(ticker, 'UNKNOWN')
            if asset_class in asset_class_summary:
                asset_class_summary[asset_class] += percentage
            else:
                asset_class_summary[asset_class] = percentage
        
        return asset_class_summary
    
    def validate_target_allocations(self, targets: Dict[str, float]) -> Tuple[bool, str]:
        """
        Validate that target allocations are valid.
        
        Args:
            targets: Dictionary of ticker to target percentage
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        total_percentage = sum(targets.values())
        
        # Check if total equals 100% (with small tolerance for floating point)
        if abs(total_percentage - 100.0) > 0.01:
            return False, f"Allocations sum to {total_percentage:.2f}%, must equal 100%"
        
        # Check for negative percentages
        for ticker, percentage in targets.items():
            if percentage < 0:
                return False, f"Negative allocation not allowed for {ticker}"
            if percentage > 100:
                return False, f"Allocation cannot exceed 100% for {ticker}"
        
        # Check for valid ticker format (basic validation)
        for ticker in targets.keys():
            if not ticker or not isinstance(ticker, str):
                return False, f"Invalid ticker format: {ticker}"
            if ticker != 'CASH' and (len(ticker) > 10 or not ticker.replace('.', '').replace('-', '').isalnum()):
                return False, f"Invalid ticker format: {ticker}"
        
        return True, ""
    
    def calculate_rebalance_trades(
        self,
        account: Account,
        target_allocations: Dict[str, float],
        current_quotes: Dict[str, Decimal]
    ) -> RebalanceAnalysis:
        """
        Calculate the trades needed to achieve target ticker allocations.
        
        Args:
            account: Current account state
            target_allocations: Target percentages by ticker symbol
            current_quotes: Current prices for all symbols
            
        Returns:
            Complete rebalance analysis with recommended trades
        """
        logger.info(f"Calculating rebalance for {len(account.positions)} positions, {len(target_allocations)} targets")
        
        # Validate inputs
        is_valid, error_msg = self.validate_target_allocations(target_allocations)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Calculate current allocations by ticker
        current_allocations = self.calculate_current_allocations(account)
        
        # Calculate target values based on total portfolio
        total_value = Decimal(str(account.net_liquidation_value))
        target_values = {}
        
        logger.info(f"Total portfolio value: ${total_value}")
        logger.info(f"Target allocations: {target_allocations}")
        
        for ticker, percentage in target_allocations.items():
            target_values[ticker] = total_value * Decimal(str(percentage)) / Decimal('100')
            logger.info(f"Target value for {ticker}: ${target_values[ticker]}")
        
        # Add current positions that aren't in target allocations (target = 0%, sell all)
        for position in account.positions:
            sym = position.instrument.symbol
            if sym not in target_values:
                target_values[sym] = Decimal('0')
                logger.info(f"Position {sym} not in targets — will be sold to 0%")
        
        # Calculate allocation differences (include both targets and held positions)
        allocation_differences = {}
        for ticker in set(target_allocations.keys()) | set(target_values.keys()):
            current_pct = current_allocations.get(ticker, 0.0)
            target_pct = target_allocations.get(ticker, 0.0)
            allocation_differences[ticker] = target_pct - current_pct
        
        # Create position lookup by ticker
        positions_by_ticker = {}
        for position in account.positions:
            positions_by_ticker[position.instrument.symbol] = position
        
        # Calculate current values by ticker
        current_values = {}
        for ticker, position in positions_by_ticker.items():
            current_values[ticker] = Decimal(str(position.current_value))
        
        # Add cash to current values
        current_values['CASH'] = Decimal(str(account.cash_balance))
        
        # Build fallback prices from portfolio positions (for when quotes are unavailable)
        fallback_prices = {}
        for pos in account.positions:
            if pos.last_price > 0:
                fallback_prices[pos.instrument.symbol] = Decimal(str(pos.last_price))
        
        # Calculate recommended trades
        recommended_trades = []
        cash_available = Decimal(str(account.cash_balance))
        
        # Two-pass approach: calculate sells first to free up cash, then buys
        # This ensures that when you change allocations (e.g. drop old tickers,
        # add new ones), the sell proceeds fund the new buys.
        
        # Helper to get price for a ticker
        def _get_price(ticker):
            if ticker in current_quotes:
                return current_quotes[ticker]
            if ticker in fallback_prices:
                return fallback_prices[ticker]
            return None
        
        # Helper to check if ticker should be traded
        def _should_trade(ticker, value_diff):
            if ticker == 'CASH':
                return False
            # Always trade if target is 0% (full sell) regardless of threshold
            target_pct = target_allocations.get(ticker, 0.0)
            if target_pct == 0.0 and value_diff < 0:
                return abs(value_diff) >= self.minimum_trade_value
            pct_diff = abs(allocation_differences.get(ticker, 0.0))
            if pct_diff < self.rebalance_threshold_pct:
                return False
            if abs(value_diff) < self.minimum_trade_value:
                return False
            return True
        
        # --- Pass 1: SELLS (frees up cash) ---
        recommended_trades = []
        for ticker, target_value in target_values.items():
            current_value = current_values.get(ticker, Decimal('0'))
            value_difference = target_value - current_value
            
            if not _should_trade(ticker, value_difference):
                continue
            if value_difference >= 0:
                continue  # Skip buys in this pass
            
            current_price = _get_price(ticker)
            if not current_price:
                logger.warning(f"No price for {ticker}, skipping sell")
                continue
            
            if ticker in positions_by_ticker:
                position = positions_by_ticker[ticker]
                
                # If target is 0%, sell ALL shares (full liquidation)
                if target_value == 0:
                    sell_quantity = Decimal(str(position.quantity))
                    actual_proceeds = sell_quantity * current_price
                    trade = TradeRecommendation(
                        action="SELL",
                        instrument=position.instrument,
                        quantity=sell_quantity,
                        estimated_value=actual_proceeds,
                        current_quantity=sell_quantity,
                        reason=f"Sell all {ticker} (target 0%)"
                    )
                    recommended_trades.append(trade)
                    cash_available += actual_proceeds
                else:
                    sell_value = abs(value_difference)
                    sell_quantity = min(
                        (sell_value / current_price).quantize(self.precision, rounding=ROUND_DOWN),
                        Decimal(str(position.quantity))
                    )
                    
                    if sell_quantity > 0:
                        actual_proceeds = sell_quantity * current_price
                        trade = TradeRecommendation(
                            action="SELL",
                            instrument=position.instrument,
                            quantity=sell_quantity,
                            estimated_value=actual_proceeds,
                            current_quantity=Decimal(str(position.quantity)),
                            reason=f"Reduce {ticker} allocation to {target_allocations.get(ticker, 0.0):.1f}%"
                        )
                        recommended_trades.append(trade)
                        cash_available += actual_proceeds
        
        # --- Pass 2: BUYS (uses original cash + sell proceeds) ---
        for ticker, target_value in target_values.items():
            current_value = current_values.get(ticker, Decimal('0'))
            value_difference = target_value - current_value
            
            if not _should_trade(ticker, value_difference):
                continue
            if value_difference <= 0:
                continue  # Skip sells in this pass
            
            current_price = _get_price(ticker)
            if not current_price:
                logger.warning(f"No price for {ticker}, skipping buy")
                continue
            
            buy_amount = min(value_difference, cash_available)
            if buy_amount >= self.minimum_trade_value:
                quantity = (buy_amount / current_price).quantize(self.precision, rounding=ROUND_DOWN)
                
                if quantity > 0:
                    actual_cost = quantity * current_price
                    current_quantity = Decimal(str(positions_by_ticker.get(ticker, Position(
                        instrument=Instrument(ticker, "EQUITY"), 
                        quantity=0, current_value=0, cost_basis=0, 
                        unrealized_pnl=0, unrealized_pnl_percent=0, 
                        last_price=0, percent_of_portfolio=0
                    )).quantity))
                    
                    trade = TradeRecommendation(
                        action="BUY",
                        instrument=Instrument(ticker, "EQUITY"),
                        quantity=quantity,
                        estimated_value=actual_cost,
                        current_quantity=current_quantity,
                        reason=f"Increase {ticker} allocation to {target_allocations.get(ticker, 0.0):.1f}%"
                    )
                    recommended_trades.append(trade)
                    cash_available -= actual_cost
        
        # Generate asset class summary
        asset_class_summary = self.get_asset_class_summary(current_allocations, account.positions)
        
        return RebalanceAnalysis(
            current_allocations=current_allocations,
            target_allocations=target_allocations,
            allocation_differences=allocation_differences,
            recommended_trades=recommended_trades,
            cash_to_invest=cash_available,
            total_portfolio_value=total_value,
            estimated_transaction_costs=Decimal('0'),  # Public.com has zero commissions
            asset_class_summary=asset_class_summary
        )
    
    def _group_positions_by_asset_class(
        self, 
        positions: List[Position],
        symbol_to_asset_class: Optional[Dict[str, str]] = None
    ) -> Dict[str, List[Position]]:
        """Group positions by their asset class."""
        grouped = {asset_class: [] for asset_class in self.ASSET_CLASSES}
        
        for position in positions:
            # Use provided mapping or fall back to instrument type
            if symbol_to_asset_class and position.instrument.symbol in symbol_to_asset_class:
                asset_class = symbol_to_asset_class[position.instrument.symbol]
            else:
                asset_class = position.instrument.type
            
            if asset_class in grouped:
                grouped[asset_class].append(position)
        
        return grouped
    
    def _calculate_buy_trades(
        self,
        asset_class: str,
        target_amount: Decimal,
        current_quotes: Dict[str, Decimal],
        existing_positions: List[Position]
    ) -> List[TradeRecommendation]:
        """Calculate buy trades for an asset class."""
        trades = []
        
        if not existing_positions:
            # No existing positions, need to suggest representative symbols
            # This is a simplified implementation - in practice, you'd want
            # user input for specific symbols to buy
            logger.warning(f"No existing positions for {asset_class}, cannot generate buy trades")
            return trades
        
        # For simplicity, add to existing positions proportionally
        total_existing_value = sum(Decimal(str(pos.current_value)) for pos in existing_positions)
        
        for position in existing_positions:
            symbol = position.instrument.symbol
            if symbol not in current_quotes:
                continue
            
            current_price = current_quotes[symbol]
            position_weight = Decimal(str(position.current_value)) / total_existing_value
            buy_amount = target_amount * position_weight
            
            if buy_amount >= self.minimum_trade_value:
                quantity = (buy_amount / current_price).quantize(self.precision, rounding=ROUND_DOWN)
                
                if quantity > 0:
                    trade = TradeRecommendation(
                        action="BUY",
                        instrument=position.instrument,
                        quantity=quantity,
                        estimated_value=quantity * current_price,
                        current_quantity=Decimal(str(position.quantity)),
                        reason=f"Increase {asset_class} allocation to target"
                    )
                    trades.append(trade)
        
        return trades
    
    def _calculate_sell_trades(
        self,
        positions: List[Position],
        target_amount: Decimal,
        current_quotes: Dict[str, Decimal]
    ) -> List[TradeRecommendation]:
        """Calculate sell trades for positions."""
        trades = []
        remaining_to_sell = target_amount
        
        # Sort positions by unrealized P&L (sell losers first for tax efficiency)
        sorted_positions = sorted(
            positions, 
            key=lambda p: p.unrealized_pnl_percent
        )
        
        for position in sorted_positions:
            if remaining_to_sell <= 0:
                break
            
            symbol = position.instrument.symbol
            if symbol not in current_quotes:
                continue
            
            current_price = current_quotes[symbol]
            position_value = Decimal(str(position.current_value))
            
            # Calculate how much to sell from this position
            sell_amount = min(remaining_to_sell, position_value)
            sell_quantity = (sell_amount / current_price).quantize(self.precision, rounding=ROUND_DOWN)
            
            # Don't sell more than we have
            max_quantity = Decimal(str(position.quantity))
            sell_quantity = min(sell_quantity, max_quantity)
            
            if sell_quantity > 0:
                actual_sell_value = sell_quantity * current_price
                
                trade = TradeRecommendation(
                    action="SELL",
                    instrument=position.instrument,
                    quantity=sell_quantity,
                    estimated_value=actual_sell_value,
                    current_quantity=max_quantity,
                    reason="Reduce allocation to target"
                )
                trades.append(trade)
                remaining_to_sell -= actual_sell_value
        
        return trades
    
    def calculate_efficient_frontier(
        self, 
        account: Account,
        allocation_constraints: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> List[Dict[str, float]]:
        """
        Calculate efficient allocation options (simplified implementation).
        
        Args:
            account: Account to analyze
            allocation_constraints: Min/max constraints for each asset class
            
        Returns:
            List of allocation dictionaries representing efficient options
        """
        # This is a simplified implementation
        # In practice, you'd use modern portfolio theory with historical returns
        
        efficient_allocations = [
            # Conservative
            {'EQUITY': 40.0, 'BOND': 35.0, 'TREASURY': 15.0, 'CASH': 10.0},
            # Moderate
            {'EQUITY': 60.0, 'BOND': 25.0, 'TREASURY': 10.0, 'CASH': 5.0},
            # Aggressive
            {'EQUITY': 80.0, 'BOND': 15.0, 'CASH': 5.0},
            # Balanced
            {'EQUITY': 50.0, 'BOND': 30.0, 'TREASURY': 15.0, 'CASH': 5.0}
        ]
        
        # Apply constraints if provided
        if allocation_constraints:
            filtered_allocations = []
            for allocation in efficient_allocations:
                valid = True
                for asset_class, (min_pct, max_pct) in allocation_constraints.items():
                    current_pct = allocation.get(asset_class, 0.0)
                    if current_pct < min_pct or current_pct > max_pct:
                        valid = False
                        break
                if valid:
                    filtered_allocations.append(allocation)
            return filtered_allocations
        
        return efficient_allocations
