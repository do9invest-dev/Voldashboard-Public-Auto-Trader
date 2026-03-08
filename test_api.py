"""
Test script to verify Public.com API authentication.

Usage:
    export PUBLIC_API_KEY='your_key_here'
    python test_api.py
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))

from src.api.client import PublicAPIClient
import logging

logging.basicConfig(level=logging.INFO)


def test_api():
    """Test the API connection with the configured key."""

    api_key = os.getenv("PUBLIC_API_KEY")

    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("PUBLIC_API_KEY", "")
        except Exception:
            pass

    if not api_key:
        print("❌ No API key found!")
        print("Set your API key: export PUBLIC_API_KEY='your_key_here'")
        return

    print(f"Testing API with key: {api_key[:8]}...{api_key[-4:]}")

    try:
        client = PublicAPIClient(api_key)
        print("✅ Client initialized and access token generated")

        print("📊 Getting accounts...")
        accounts = client.get_accounts()
        print(f"✅ Found {len(accounts)} account(s)")

        for account in accounts:
            print(f"\n  Account ID: {account.account_id}")
            print(f"  Type:       {account.account_type}")
            print(f"  Net Value:  ${account.net_liquidation_value:,.2f}")
            print(f"  Cash:       ${account.cash_balance:,.2f}")
            print(f"  Buying Pwr: ${account.buying_power:,.2f}")
            print(f"  Positions:  {len(account.positions)}")

            for pos in account.positions:
                print(f"    {pos.instrument.symbol:8s}  qty={pos.quantity:<10.4f}  "
                      f"value=${pos.current_value:>10,.2f}  "
                      f"P&L={pos.unrealized_pnl:>+10,.2f}")

        # Test instrument validation
        print("\n🔎 Validating sample instruments...")
        for sym in ["SPY", "AAPL", "BND", "QQQ"]:
            valid = client.validate_instrument(sym)
            print(f"  {sym}: {'✅ Tradable' if valid else '❌ Not found'}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_api()
