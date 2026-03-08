"""
Unit tests for the PortfolioAnalyzer class.
"""

import unittest
from decimal import Decimal

from src.portfolio.analyzer import PortfolioAnalyzer
from src.api.client import Account, Position, Instrument


class TestPortfolioAnalyzer(unittest.TestCase):
    """Test cases for PortfolioAnalyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = PortfolioAnalyzer()
        
        # Create sample positions
        self.positions = [
            Position(
                instrument=Instrument("AAPL", "EQUITY"),
                quantity=10.0,
                current_value=1500.0,
                cost_basis=1400.0,
                unrealized_pnl=100.0,
                unrealized_pnl_percent=7.14,
                last_price=150.0,
                percent_of_portfolio=50.0
            ),
            Position(
                instrument=Instrument("GOOGL", "EQUITY"),
                quantity=5.0,
                current_value=1500.0,
                cost_basis=1350.0,
                unrealized_pnl=150.0,
                unrealized_pnl_percent=11.11,
                last_price=300.0,
                percent_of_portfolio=50.0
            )
        ]
        
        self.account = Account(
            account_id="test_account",
            account_type="BROKERAGE",
            net_liquidation_value=3000.0,
            cash_balance=0.0,
            buying_power=1000.0,
            positions=self.positions
        )
    
    def test_calculate_current_allocations(self):
        """Test calculation of current allocations."""
        allocations = self.analyzer.calculate_current_allocations(self.account)
        
        # Should have 100% EQUITY allocation
        self.assertEqual(allocations['EQUITY'], 100.0)
        self.assertEqual(allocations['CASH'], 0.0)
        self.assertEqual(allocations['BOND'], 0.0)
    
    def test_calculate_current_allocations_with_cash(self):
        """Test allocation calculation with cash balance."""
        account_with_cash = Account(
            account_id="test_account",
            account_type="BROKERAGE",
            net_liquidation_value=4000.0,
            cash_balance=1000.0,
            buying_power=1000.0,
            positions=self.positions
        )
        
        allocations = self.analyzer.calculate_current_allocations(account_with_cash)
        
        self.assertEqual(allocations['EQUITY'], 75.0)  # 3000/4000
        self.assertEqual(allocations['CASH'], 25.0)    # 1000/4000
    
    def test_validate_target_allocations_valid(self):
        """Test validation of valid target allocations."""
        targets = {
            'EQUITY': 60.0,
            'BOND': 30.0,
            'CASH': 10.0
        }
        
        is_valid, error = self.analyzer.validate_target_allocations(targets)
        
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
    
    def test_validate_target_allocations_invalid_sum(self):
        """Test validation with invalid sum."""
        targets = {
            'EQUITY': 60.0,
            'BOND': 30.0,
            'CASH': 20.0  # Total = 110%
        }
        
        is_valid, error = self.analyzer.validate_target_allocations(targets)
        
        self.assertFalse(is_valid)
        self.assertIn("110.00%", error)
    
    def test_validate_target_allocations_negative(self):
        """Test validation with negative allocation."""
        targets = {
            'EQUITY': 70.0,
            'BOND': -10.0,  # Negative
            'CASH': 40.0
        }
        
        is_valid, error = self.analyzer.validate_target_allocations(targets)
        
        self.assertFalse(is_valid)
        self.assertIn("Negative allocation", error)
    
    def test_validate_target_allocations_invalid_class(self):
        """Test validation with invalid asset class."""
        targets = {
            'EQUITY': 50.0,
            'INVALID_CLASS': 30.0,
            'CASH': 20.0
        }
        
        is_valid, error = self.analyzer.validate_target_allocations(targets)
        
        self.assertFalse(is_valid)
        self.assertIn("Unknown asset class", error)
    
    def test_group_positions_by_asset_class(self):
        """Test grouping positions by asset class."""
        grouped = self.analyzer._group_positions_by_asset_class(self.positions)
        
        self.assertEqual(len(grouped['EQUITY']), 2)
        self.assertEqual(len(grouped['BOND']), 0)
        self.assertEqual(grouped['EQUITY'][0].instrument.symbol, 'AAPL')
        self.assertEqual(grouped['EQUITY'][1].instrument.symbol, 'GOOGL')


if __name__ == '__main__':
    unittest.main()
