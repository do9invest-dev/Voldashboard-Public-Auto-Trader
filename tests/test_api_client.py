"""
Unit tests for the PublicAPIClient class.
"""

import unittest
from unittest.mock import Mock, patch
from decimal import Decimal

from src.api.client import PublicAPIClient, Instrument, Quote, Position, Account


class TestPublicAPIClient(unittest.TestCase):
    """Test cases for PublicAPIClient."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = PublicAPIClient("test_api_key")
    
    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        self.assertEqual(self.client.api_key, "test_api_key")
        self.assertIn("Authorization", self.client.session.headers)
    
    def test_init_without_api_key(self):
        """Test client initialization without API key."""
        client = PublicAPIClient()
        self.assertIsNone(client.api_key)
    
    def test_set_api_key(self):
        """Test setting API key after initialization."""
        self.client.set_api_key("new_key")
        self.assertEqual(self.client.api_key, "new_key")
        self.assertEqual(
            self.client.session.headers["Authorization"],
            "Bearer new_key"
        )
    
    @patch('src.api.client.requests.Session.get')
    def test_make_request_get(self, mock_get):
        """Test making GET requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_get.return_value = mock_response
        
        result = self.client._make_request('GET', '/test')
        
        self.assertEqual(result, {"test": "data"})
        mock_get.assert_called_once()
    
    @patch('src.api.client.requests.Session.post')
    def test_make_request_post(self, mock_post):
        """Test making POST requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response
        
        result = self.client._make_request('POST', '/test', {"data": "value"})
        
        self.assertEqual(result, {"success": True})
        mock_post.assert_called_once()
    
    def test_instrument_creation(self):
        """Test Instrument dataclass creation."""
        instrument = Instrument("AAPL", "EQUITY")
        self.assertEqual(instrument.symbol, "AAPL")
        self.assertEqual(instrument.type, "EQUITY")
    
    def test_quote_creation(self):
        """Test Quote dataclass creation."""
        instrument = Instrument("AAPL", "EQUITY")
        quote = Quote(instrument, 150.00, 149.95, 150.05)
        
        self.assertEqual(quote.instrument.symbol, "AAPL")
        self.assertEqual(quote.last, 150.00)
        self.assertEqual(quote.bid, 149.95)
        self.assertEqual(quote.ask, 150.05)


if __name__ == '__main__':
    unittest.main()
