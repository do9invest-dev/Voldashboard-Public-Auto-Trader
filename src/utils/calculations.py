"""
Utility functions for portfolio calculations and data processing.
"""

from typing import Dict, List, Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP
import logging

logger = logging.getLogger(__name__)


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else float('inf')
    
    return ((new_value - old_value) / old_value) * 100


def format_currency(amount: float, precision: int = 2) -> str:
    """
    Format a number as currency.
    
    Args:
        amount: Amount to format
        precision: Decimal places
        
    Returns:
        Formatted currency string
    """
    return f"${amount:,.{precision}f}"


def format_percentage(percentage: float, precision: int = 2) -> str:
    """
    Format a number as percentage.
    
    Args:
        percentage: Percentage to format
        precision: Decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{percentage:.{precision}f}%"


def round_to_precision(value: Decimal, precision: int = 6) -> Decimal:
    """
    Round a decimal value to specified precision.
    
    Args:
        value: Value to round
        precision: Number of decimal places
        
    Returns:
        Rounded decimal value
    """
    quantizer = Decimal('0.1') ** precision
    return value.quantize(quantizer, rounding=ROUND_HALF_UP)


def validate_allocation_sum(allocations: Dict[str, float], tolerance: float = 0.01) -> bool:
    """
    Validate that allocations sum to 100%.
    
    Args:
        allocations: Dictionary of asset class to percentage
        tolerance: Acceptable deviation from 100%
        
    Returns:
        True if allocations are valid
    """
    total = sum(allocations.values())
    return abs(total - 100.0) <= tolerance


def normalize_allocations(allocations: Dict[str, float]) -> Dict[str, float]:
    """
    Normalize allocations to sum to 100%.
    
    Args:
        allocations: Dictionary of asset class to percentage
        
    Returns:
        Normalized allocations
    """
    total = sum(allocations.values())
    
    if total == 0:
        return allocations
    
    return {
        asset_class: (percentage / total) * 100
        for asset_class, percentage in allocations.items()
    }


def calculate_portfolio_diversity_score(allocations: Dict[str, float]) -> float:
    """
    Calculate a simple diversity score for portfolio allocations.
    Higher scores indicate more diversified portfolios.
    
    Args:
        allocations: Dictionary of asset class to percentage
        
    Returns:
        Diversity score between 0 and 1
    """
    # Filter out zero allocations
    non_zero_allocations = [pct for pct in allocations.values() if pct > 0]
    
    if not non_zero_allocations:
        return 0.0
    
    # Calculate entropy-based diversity
    total = sum(non_zero_allocations)
    if total == 0:
        return 0.0
    
    # Normalize to probabilities
    probabilities = [pct / total for pct in non_zero_allocations]
    
    # Calculate Shannon entropy
    import math
    entropy = -sum(p * math.log(p) for p in probabilities if p > 0)
    
    # Normalize to 0-1 scale
    max_entropy = math.log(len(non_zero_allocations))
    return entropy / max_entropy if max_entropy > 0 else 0.0


def get_risk_level(allocations: Dict[str, float]) -> str:
    """
    Determine risk level based on allocations.
    
    Args:
        allocations: Dictionary of asset class to percentage
        
    Returns:
        Risk level string
    """
    equity_pct = allocations.get('EQUITY', 0.0)
    crypto_pct = allocations.get('CRYPTO', 0.0)
    option_pct = allocations.get('OPTION', 0.0)
    
    # Calculate risk score
    risk_score = (
        equity_pct * 1.0 +
        crypto_pct * 2.0 +
        option_pct * 3.0
    )
    
    if risk_score < 30:
        return "Conservative"
    elif risk_score < 60:
        return "Moderate"
    elif risk_score < 85:
        return "Aggressive"
    else:
        return "Very Aggressive"


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe ratio for a series of returns.
    
    Args:
        returns: List of periodic returns
        risk_free_rate: Risk-free rate of return
        
    Returns:
        Sharpe ratio
    """
    if not returns or len(returns) < 2:
        return 0.0
    
    import statistics
    
    mean_return = statistics.mean(returns)
    std_return = statistics.stdev(returns)
    
    if std_return == 0:
        return 0.0
    
    return (mean_return - risk_free_rate) / std_return
