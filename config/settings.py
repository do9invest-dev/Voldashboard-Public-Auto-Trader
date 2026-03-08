"""
Configuration settings for the portfolio rebalancing application.
"""

import os
from typing import Dict, Any


class Config:
    """Application configuration settings."""
    
    # API Configuration
    API_BASE_URL = "https://api.public.com"
    REQUEST_TIMEOUT = 30  # seconds
    RATE_LIMIT_DELAY = 0.1  # seconds between requests
    
    # Trading Configuration
    MINIMUM_TRADE_VALUE = 1.00  # Minimum $1 trade
    FRACTIONAL_PRECISION = 6  # 6 decimal places for fractional shares
    
    # UI Configuration
    AUTO_REFRESH_INTERVAL = 30  # seconds
    DEFAULT_TEST_MODE = True
    
    # Supported Asset Classes
    ASSET_CLASSES = {
        'EQUITY': 'Stocks and ETFs',
        'OPTION': 'Options Contracts', 
        'CRYPTO': 'Cryptocurrency',
        'ALT': 'Alternative Investments',
        'TREASURY': 'Treasury Securities',
        'BOND': 'Bonds',
        'INDEX': 'Index Funds'
    }
    
    # Default Allocation Presets
    ALLOCATION_PRESETS = {
        'conservative': {
            'EQUITY': 40.0,
            'BOND': 35.0,
            'TREASURY': 15.0,
            'CASH': 10.0,
            'OPTION': 0.0,
            'CRYPTO': 0.0,
            'ALT': 0.0,
            'INDEX': 0.0
        },
        'moderate': {
            'EQUITY': 60.0,
            'BOND': 25.0,
            'TREASURY': 10.0,
            'CASH': 5.0,
            'OPTION': 0.0,
            'CRYPTO': 0.0,
            'ALT': 0.0,
            'INDEX': 0.0
        },
        'aggressive': {
            'EQUITY': 80.0,
            'BOND': 15.0,
            'CASH': 5.0,
            'OPTION': 0.0,
            'CRYPTO': 0.0,
            'ALT': 0.0,
            'INDEX': 0.0,
            'TREASURY': 0.0
        },
        'balanced': {
            'EQUITY': 50.0,
            'BOND': 30.0,
            'TREASURY': 15.0,
            'CASH': 5.0,
            'OPTION': 0.0,
            'CRYPTO': 0.0,
            'ALT': 0.0,
            'INDEX': 0.0
        }
    }
    
    @classmethod
    def get_api_key(cls) -> str:
        """Get API key from environment or Streamlit secrets."""
        # Try environment variable first
        api_key = os.getenv('PUBLIC_API_KEY')
        
        if not api_key:
            # Try Streamlit secrets
            try:
                import streamlit as st
                api_key = st.secrets.get('PUBLIC_API_KEY', '')
            except:
                api_key = ''
        
        return api_key
    
    @classmethod
    def get_logging_config(cls) -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'default': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'INFO',
                    'formatter': 'default'
                }
            },
            'loggers': {
                'portfolio_rebalancer': {
                    'level': 'INFO',
                    'handlers': ['console'],
                    'propagate': False
                }
            }
        }
