"""
Main Streamlit UI Application

Provides the complete user interface for the portfolio rebalancing tool
with professional styling, multiple ticker upload, instrument validation,
and live order execution via the Public.com API.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional, Any
from decimal import Decimal
import time
import logging
import io
import csv
import re

from src.api.client import PublicAPIClient, Instrument, OrderResult
from src.portfolio.analyzer import PortfolioAnalyzer, RebalanceAnalysis
from src.utils.logger import setup_logger

try:
    import yfinance as yf
    import numpy as np
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

logger = setup_logger()


def _parse_tickers_text(text: str) -> Dict[str, float]:
    """
    Parse tickers and allocations from free-form text.

    Accepted formats:
      AAPL 25
      AAPL, 25
      AAPL 25%
      AAPL:25
      AAPL=25
      AAPL   (no percentage → 0, user must fill in)

    One ticker per line.
    """
    results: Dict[str, float] = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Normalize separators
        line = line.replace(":", " ").replace("=", " ").replace(",", " ").replace("\t", " ")
        line = line.replace("%", "")
        parts = line.split()
        if not parts:
            continue
        ticker = parts[0].upper().strip()
        # Basic ticker validation (1-10 alphanumeric chars, dots, dashes)
        if not re.match(r"^[A-Z0-9.\-]{1,10}$", ticker):
            continue
        pct = 0.0
        if len(parts) >= 2:
            try:
                pct = float(parts[1])
            except ValueError:
                pct = 0.0
        results[ticker] = pct
    return results


def _parse_tickers_csv(file_bytes: bytes) -> Dict[str, float]:
    """
    Parse tickers from an uploaded CSV file.

    Expected columns (case-insensitive): symbol/ticker, percentage/allocation/weight
    Falls back to first two columns if headers don't match.
    """
    results: Dict[str, float] = {}
    text = file_bytes.decode("utf-8", errors="ignore")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return results

    # Detect header
    header = [h.strip().lower() for h in rows[0]]
    sym_col = None
    pct_col = None

    for i, h in enumerate(header):
        if h in ("symbol", "ticker", "sym", "stock"):
            sym_col = i
        elif h in ("percentage", "allocation", "weight", "pct", "%", "target"):
            pct_col = i

    data_start = 0
    if sym_col is not None:
        data_start = 1
    else:
        # No recognized header; assume col 0 = ticker, col 1 = pct
        sym_col = 0
        pct_col = 1 if len(rows[0]) > 1 else None
        # Check if first row looks like data (first cell is alpha)
        if rows[0][0].strip().replace(".", "").replace("-", "").isalpha():
            data_start = 0
        else:
            data_start = 1

    for row in rows[data_start:]:
        if sym_col is not None and sym_col < len(row):
            ticker = row[sym_col].strip().upper()
            if not re.match(r"^[A-Z0-9.\-]{1,10}$", ticker):
                continue
            pct = 0.0
            if pct_col is not None and pct_col < len(row):
                try:
                    pct = float(row[pct_col].strip().replace("%", ""))
                except ValueError:
                    pct = 0.0
            results[ticker] = pct

    return results


class StreamlitUI:
    """
    Main Streamlit application interface for portfolio rebalancing.
    """

    def __init__(self):
        self.api_client = PublicAPIClient()
        self.analyzer = PortfolioAnalyzer()
        self._init_session_state()
        self._apply_custom_styling()

    def _init_session_state(self):
        if "api_key" not in st.session_state:
            try:
                api_key = st.secrets.get("PUBLIC_API_KEY", "")
                st.session_state.api_key = api_key
                if api_key:
                    self.api_client.set_api_key(api_key)
            except Exception:
                st.session_state.api_key = ""

        if "test_mode" not in st.session_state:
            st.session_state.test_mode = True

        if "portfolio_data" not in st.session_state:
            st.session_state.portfolio_data = None

        if "all_accounts" not in st.session_state:
            st.session_state.all_accounts = []

        if "selected_account_id" not in st.session_state:
            st.session_state.selected_account_id = None

        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = 0

        if "target_allocations" not in st.session_state:
            st.session_state.target_allocations = {
                "SPY": 60.0,
                "BND": 30.0,
                "CASH": 10.0,
            }

        if "order_results" not in st.session_state:
            st.session_state.order_results = []

        if "validated_tickers" not in st.session_state:
            st.session_state.validated_tickers = {}

        if "rebalance_threshold_pct" not in st.session_state:
            st.session_state.rebalance_threshold_pct = 1.0

    def _apply_custom_styling(self):
        st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-container {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
        }
        .positive { color: #28a745; font-weight: bold; }
        .negative { color: #dc3545; font-weight: bold; }
        .test-mode {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        .live-mode {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
        }
        .trade-action-buy {
            background-color: #d4edda;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            color: #155724;
            font-weight: bold;
        }
        .trade-action-sell {
            background-color: #f8d7da;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            color: #721c24;
            font-weight: bold;
        }
        .upload-section {
            background-color: #e8f4fd;
            border: 2px dashed #1f77b4;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 0.5rem 0;
        }
        </style>
        """, unsafe_allow_html=True)

    # =========================================================================
    # Main entry
    # =========================================================================

    def run(self):
        st.markdown(
            '<h1 class="main-header">📊 Portfolio Rebalancing Tool</h1>',
            unsafe_allow_html=True,
        )

        self._render_sidebar()

        if not st.session_state.api_key:
            self._render_welcome_screen()
        else:
            self._render_main_interface()

    # =========================================================================
    # Sidebar
    # =========================================================================

    def _render_sidebar(self):
        with st.sidebar:
            st.header("⚙️ Configuration")

            # --- API Key ---
            st.subheader("API Authentication")
            if st.session_state.api_key:
                masked = st.session_state.api_key[:8] + "..." + st.session_state.api_key[-4:]
                st.success(f"✅ API Key Set: {masked}")

                if st.button("🔍 Test Connection", use_container_width=True):
                    with st.spinner("Testing API connection..."):
                        if self.api_client.test_connection():
                            st.success("✅ Connection successful!")
                        else:
                            st.error("❌ Connection failed. Check your API key.")

            api_key = st.text_input(
                "Public.com API Key",
                type="password",
                value=st.session_state.api_key,
                help="Enter your Public.com API key (secret) for authentication",
            )

            if api_key != st.session_state.api_key:
                st.session_state.api_key = api_key
                if api_key:
                    self.api_client.set_api_key(api_key)
                    st.success("API key updated")
                st.rerun()

            # --- Trading Mode ---
            st.subheader("Trading Mode")
            test_mode = st.toggle(
                "Test Mode",
                value=st.session_state.test_mode,
                help="Enable to preview trades without executing them",
            )

            if test_mode != st.session_state.test_mode:
                st.session_state.test_mode = test_mode
                st.rerun()

            if st.session_state.test_mode:
                st.markdown(
                    '<div class="test-mode">🧪 <strong>TEST MODE</strong><br>Trades will be previewed only</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="live-mode">🔴 <strong>LIVE MODE</strong><br>Orders will be sent to Public.com</div>',
                    unsafe_allow_html=True,
                )

            # --- Rebalance Threshold ---
            if st.session_state.api_key:
                st.subheader("🎚️ Rebalance Threshold")
                threshold = st.slider(
                    "Skip if within % of target",
                    min_value=0.0,
                    max_value=10.0,
                    value=st.session_state.rebalance_threshold_pct,
                    step=0.25,
                    help=(
                        "If a ticker's current allocation is within this many "
                        "percentage points of its target, no trade will be generated. "
                        "For example, 1.0% means AAPL at 24.3% with a 25% target "
                        "won't trigger a trade."
                    ),
                    key="threshold_slider",
                )
                if threshold != st.session_state.rebalance_threshold_pct:
                    st.session_state.rebalance_threshold_pct = threshold
                st.caption(f"Currently skipping trades within **±{threshold:.2f}%** of target")

                # --- Order Pacing ---
                st.subheader("⏱️ Order Pacing")
                pace = st.slider(
                    "Seconds between orders",
                    min_value=3.0,
                    max_value=30.0,
                    value=st.session_state.get("order_pace_seconds", 1.0),
                    step=0.5,
                    help=(
                        "Time to wait between each order submission. "
                        "Public.com rate-limits API calls — if orders are failing, "
                        "increase this. 3s works for most accounts, try 5s for 30+ trades."
                    ),
                    key="pace_slider",
                )
                st.session_state.order_pace_seconds = pace
                trades_est = len(st.session_state.target_allocations)
                st.caption(
                    f"~{trades_est} trades × {pace:.0f}s = "
                    f"~{(trades_est * pace) / 60:.1f} min estimated"
                )

            # --- Account Selector ---
            if st.session_state.api_key and st.session_state.all_accounts:
                st.subheader("🏦 Account")
                accounts = st.session_state.all_accounts

                # Build display labels like "BROKERAGE (abc123)" or "ROTH_IRA (def456)"
                account_labels = {}
                for acc in accounts:
                    label = f"{acc.account_type} — ${acc.net_liquidation_value:,.2f}"
                    account_labels[acc.account_id] = label

                account_ids = list(account_labels.keys())
                current_idx = 0
                if st.session_state.selected_account_id in account_ids:
                    current_idx = account_ids.index(st.session_state.selected_account_id)

                selected_id = st.selectbox(
                    "Select Account",
                    options=account_ids,
                    index=current_idx,
                    format_func=lambda aid: account_labels.get(aid, aid),
                    key="account_selector",
                )

                if selected_id != st.session_state.selected_account_id:
                    st.session_state.selected_account_id = selected_id
                    # Update portfolio_data to the selected account
                    for acc in accounts:
                        if acc.account_id == selected_id:
                            st.session_state.portfolio_data = acc
                            break
                    st.session_state.order_results = []  # Clear orders on switch
                    st.rerun()

            # --- Allocations ---
            if st.session_state.api_key:
                self._render_allocation_settings()

    # =========================================================================
    # Multiple Ticker Upload + Allocation Editor
    # =========================================================================

    def _render_allocation_settings(self):
        st.subheader("🎯 Target Allocations")

        # ---- Bulk Ticker Upload ----
        with st.expander("📥 Bulk Upload Tickers", expanded=False):
            st.markdown(
                '<div class="upload-section">', unsafe_allow_html=True
            )

            upload_tab, paste_tab = st.tabs(["Upload CSV", "Paste Tickers"])

            with upload_tab:
                uploaded_file = st.file_uploader(
                    "Upload CSV with tickers",
                    type=["csv", "txt"],
                    help="CSV with columns: symbol, percentage. Or just a list of tickers.",
                    key="ticker_csv_upload",
                )
                if uploaded_file is not None:
                    parsed = _parse_tickers_csv(uploaded_file.getvalue())
                    if parsed:
                        st.write(f"Found **{len(parsed)}** tickers")
                        preview_df = pd.DataFrame(
                            [{"Ticker": k, "Allocation %": v} for k, v in parsed.items()]
                        )
                        st.dataframe(preview_df, hide_index=True, use_container_width=True)

                        col_a, col_b = st.columns(2)
                        with col_a:
                            merge_mode = st.radio(
                                "Import mode",
                                ["Replace all", "Merge with existing"],
                                horizontal=True,
                                key="csv_merge_mode",
                            )
                        with col_b:
                            if st.button("✅ Import Tickers", key="import_csv_btn"):
                                if merge_mode == "Replace all":
                                    st.session_state.target_allocations = parsed
                                else:
                                    merged = st.session_state.target_allocations.copy()
                                    merged.update(parsed)
                                    st.session_state.target_allocations = merged
                                st.success(f"Imported {len(parsed)} tickers!")
                                st.rerun()
                    else:
                        st.warning("Could not parse any tickers from the file.")

            with paste_tab:
                ticker_text = st.text_area(
                    "Paste tickers (one per line)",
                    placeholder="AAPL 25\nMSFT 25\nGOOGL 20\nAMZN 15\nTSLA 15",
                    height=150,
                    key="ticker_paste_area",
                    help="Format: TICKER PERCENTAGE (one per line). Percentage is optional.",
                )
                if ticker_text.strip():
                    parsed = _parse_tickers_text(ticker_text)
                    if parsed:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            paste_merge = st.radio(
                                "Import mode",
                                ["Replace all", "Merge with existing"],
                                horizontal=True,
                                key="paste_merge_mode",
                            )
                        with col_b:
                            if st.button("✅ Import Tickers", key="import_paste_btn"):
                                if paste_merge == "Replace all":
                                    st.session_state.target_allocations = parsed
                                else:
                                    merged = st.session_state.target_allocations.copy()
                                    merged.update(parsed)
                                    st.session_state.target_allocations = merged
                                st.success(f"Imported {len(parsed)} tickers!")
                                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        # ---- Validate Tickers Button ----
        non_cash = [t for t in st.session_state.target_allocations if t != "CASH"]
        if non_cash and self.api_client.api_key:
            if st.button("🔎 Validate Tickers on Public.com", use_container_width=True):
                with st.spinner("Checking instruments..."):
                    try:
                        results = self.api_client.validate_tickers(non_cash)
                        st.session_state.validated_tickers = results
                        valid_count = sum(1 for v in results.values() if v)
                        total = len(results)
                        if valid_count == total:
                            st.success(f"✅ All {total} tickers are tradable on Public.com")
                        else:
                            invalid = [k for k, v in results.items() if not v]
                            st.warning(
                                f"⚠️ {valid_count}/{total} valid. "
                                f"Not tradable: {', '.join(invalid)}"
                            )
                    except Exception as e:
                        st.error(f"Validation error: {e}")

        # ---- Per-Ticker Allocation Editor ----
        allocations = st.session_state.target_allocations.copy()

        st.write("**Current Target Allocations:**")

        # Handle removals
        for ticker in list(allocations.keys()):
            if ticker != "CASH" and st.session_state.get(f"remove_{ticker}", False):
                del allocations[ticker]
                st.session_state[f"remove_{ticker}"] = False
                st.session_state.target_allocations = allocations
                st.rerun()

        for ticker in list(allocations.keys()):
            col1, col2, col3 = st.columns([3, 2, 1])

            # Show validation status
            validation = st.session_state.validated_tickers
            icon = ""
            if ticker == "CASH":
                icon = "💵"
            elif ticker in validation:
                icon = "✅" if validation[ticker] else "❌"

            with col1:
                st.write(f"{icon} **{ticker}**")

            with col2:
                new_value = st.number_input(
                    f"{ticker} %",
                    min_value=0.0,
                    max_value=100.0,
                    value=allocations[ticker],
                    step=0.5,
                    key=f"allocation_{ticker}",
                    label_visibility="collapsed",
                )
                allocations[ticker] = new_value

            with col3:
                if ticker != "CASH":
                    st.button("❌", key=f"remove_{ticker}", help=f"Remove {ticker}")

        # --- Add new ticker ---
        st.write("**Add New Ticker:**")
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            new_ticker = st.text_input(
                "Ticker Symbol",
                placeholder="e.g., AAPL, TSLA, VTI",
                help="Enter a valid ticker symbol",
            ).upper().strip()

        with col2:
            new_percentage = st.number_input(
                "Percentage",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=0.5,
                key="new_ticker_percentage",
            )

        with col3:
            if st.button("➕ Add", disabled=not new_ticker or new_percentage <= 0):
                if new_ticker and new_ticker not in allocations and new_percentage > 0:
                    allocations[new_ticker] = new_percentage
                    st.session_state.target_allocations = allocations
                    st.rerun()

        # --- Total validation ---
        total_allocation = sum(allocations.values())
        if abs(total_allocation - 100.0) > 0.01:
            st.error(f"Total allocation: {total_allocation:.1f}% (must equal 100%)")

            # Auto-distribute button
            if st.button("⚖️ Auto-distribute evenly"):
                count = len(allocations)
                if count > 0:
                    even_pct = round(100.0 / count, 2)
                    remainder = 100.0 - (even_pct * count)
                    for i, ticker in enumerate(allocations):
                        allocations[ticker] = even_pct + (remainder if i == 0 else 0)
                    st.session_state.target_allocations = allocations
                    st.rerun()
        else:
            st.success(f"Total allocation: {total_allocation:.1f}% ✓")
            st.session_state.target_allocations = allocations

        # --- Presets ---
        st.subheader("📋 Preset Portfolios")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("60/40 Portfolio", use_container_width=True):
                st.session_state.target_allocations = {"SPY": 60.0, "BND": 40.0}
                st.rerun()
            if st.button("Three Fund", use_container_width=True):
                st.session_state.target_allocations = {
                    "VTI": 60.0,
                    "VXUS": 20.0,
                    "BND": 20.0,
                }
                st.rerun()

        with col2:
            if st.button("Conservative", use_container_width=True):
                st.session_state.target_allocations = {
                    "SPY": 30.0,
                    "BND": 50.0,
                    "CASH": 20.0,
                }
                st.rerun()
            if st.button("Tech Heavy", use_container_width=True):
                st.session_state.target_allocations = {
                    "QQQ": 40.0,
                    "SPY": 30.0,
                    "VGT": 20.0,
                    "CASH": 10.0,
                }
                st.rerun()

    # =========================================================================
    # Welcome
    # =========================================================================

    def _render_welcome_screen(self):
        st.markdown("""
        ## Welcome to the Portfolio Rebalancing Tool

        This application helps you rebalance your **Public.com** brokerage account:

        - 📊 **Monitor** your portfolio in real-time via the Public.com API
        - 🎯 **Set** target allocations for any ticker
        - 📥 **Bulk upload** tickers via CSV or paste
        - ⚖️ **Rebalance** with calculated buy/sell orders
        - 🧪 **Test** strategies before placing live orders
        - 🔴 **Execute** real market orders on Public.com

        ### Getting Started

        1. Get your API key from [Public.com Developer Portal](https://public.com/developer)
        2. Enter your API key in the sidebar
        3. Set your target allocations (manually or bulk upload)
        4. Review and execute rebalancing trades

        ### Bulk Ticker Upload

        You can upload multiple tickers at once:
        - **CSV file**: columns `symbol` and `percentage`
        - **Paste text**: one ticker per line, e.g. `AAPL 25`
        - **Auto-distribute**: evenly split allocation across all tickers

        ### Safety Features

        - 🧪 **Test Mode**: Preview all calculations without executing trades
        - 🔎 **Instrument Validation**: Verify tickers are tradable on Public.com
        - ✅ **Order Preview**: See preflight details before execution
        - 🔒 **Confirmation Dialogs**: Required for live trading
        """)

    # =========================================================================
    # Main Interface
    # =========================================================================

    def _render_main_interface(self):
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            if st.button("🔄 Refresh Data", use_container_width=True):
                self._refresh_portfolio_data()

        with col2:
            auto_refresh = st.checkbox("Auto-refresh", value=False)

        with col3:
            if auto_refresh and time.time() - st.session_state.last_refresh > 30:
                self._refresh_portfolio_data()
                st.rerun()

        if st.session_state.portfolio_data is None:
            self._refresh_portfolio_data()

        if st.session_state.portfolio_data:
            self._render_dashboard()
            self._render_rebalancing_section()

            # Show recent order results
            if st.session_state.order_results:
                self._render_order_history()
        else:
            st.error("Failed to load portfolio data. Please check your API key.")

    def _refresh_portfolio_data(self):
        if not st.session_state.api_key:
            st.error("Please enter your Public.com API key in the sidebar")
            return

        if not self.api_client.api_key or self.api_client.api_key != st.session_state.api_key:
            self.api_client.set_api_key(st.session_state.api_key)

        try:
            with st.spinner("Loading portfolio data..."):
                accounts = self.api_client.get_accounts()
                if not accounts:
                    st.error("No accounts found")
                    return

                # Store all accounts for the switcher
                st.session_state.all_accounts = accounts

                # If no account selected yet, or the selected one is gone, pick first
                selected_id = st.session_state.selected_account_id
                account_ids = [a.account_id for a in accounts]

                if selected_id not in account_ids:
                    selected_id = account_ids[0]
                    st.session_state.selected_account_id = selected_id

                # Set portfolio_data to the selected account
                for acc in accounts:
                    if acc.account_id == selected_id:
                        st.session_state.portfolio_data = acc
                        break

                st.session_state.last_refresh = time.time()

                if len(accounts) > 1:
                    st.success(
                        f"Loaded {len(accounts)} accounts — "
                        f"use the Account selector in the sidebar to switch."
                    )
                else:
                    st.success("Portfolio data loaded successfully!")

        except Exception as e:
            st.error(f"Error loading portfolio data: {e}")
            st.session_state.portfolio_data = None

    # =========================================================================
    # Dashboard
    # =========================================================================

    def _render_dashboard(self):
        account = st.session_state.portfolio_data

        st.header("💼 Portfolio Overview")

        # Debug toggle to see raw values
        if st.checkbox("🐛 Show Debug Info", value=False):
            st.write("**Account Object:**")
            st.json({
                "account_id": account.account_id,
                "account_type": account.account_type,
                "net_liquidation_value": account.net_liquidation_value,
                "cash_balance": account.cash_balance,
                "buying_power": account.buying_power,
                "positions_count": len(account.positions),
                "positions": [
                    {
                        "symbol": p.instrument.symbol,
                        "type": p.instrument.type,
                        "quantity": p.quantity,
                        "current_value": p.current_value,
                        "last_price": p.last_price,
                        "percent_of_portfolio": p.percent_of_portfolio,
                    }
                    for p in account.positions
                ],
            })
            st.info(
                "Check the Streamlit Cloud logs (Manage app → Logs) for the raw "
                "API equity array to see exactly what Public.com returned."
            )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Net Liquidation Value", f"${account.net_liquidation_value:,.2f}")
        with col2:
            st.metric("Cash Balance", f"${account.cash_balance:,.2f}")
        with col3:
            st.metric("Buying Power", f"${account.buying_power:,.2f}")
        with col4:
            total_pnl = sum(pos.unrealized_pnl for pos in account.positions)
            st.metric("Unrealized P&L", f"${total_pnl:,.2f}")

        if account.positions:
            self._render_positions_table(account.positions)

        self._render_allocation_charts(account)

        if account.positions:
            self._render_volatility(account)

    def _render_positions_table(self, positions):
        st.subheader("📋 Current Positions")

        positions_data = []
        for pos in positions:
            positions_data.append({
                "Symbol": pos.instrument.symbol,
                "Type": pos.instrument.type,
                "Quantity": f"{pos.quantity:,.6f}".rstrip("0").rstrip("."),
                "Market Value": f"${pos.current_value:,.2f}",
                "Cost Basis": f"${pos.cost_basis:,.2f}",
                "Unrealized P&L": f"${pos.unrealized_pnl:,.2f}",
                "P&L %": f"{pos.unrealized_pnl_percent:,.2f}%",
                "Last Price": f"${pos.last_price:,.2f}",
                "Portfolio %": f"{pos.percent_of_portfolio:,.2f}%",
            })

        df = pd.DataFrame(positions_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    def _render_allocation_charts(self, account):
        st.subheader("📊 Allocation Analysis")

        current_allocations = self.analyzer.calculate_current_allocations(account)
        target_allocations = st.session_state.target_allocations

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Current Allocations**")
            current_filtered = {k: v for k, v in current_allocations.items() if v > 0.1}
            if current_filtered:
                fig = px.pie(
                    values=list(current_filtered.values()),
                    names=list(current_filtered.keys()),
                    title="Current Portfolio Allocation",
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No significant positions to display")

        with col2:
            st.write("**Target Allocations**")
            target_filtered = {k: v for k, v in target_allocations.items() if v > 0.1}
            if target_filtered:
                fig = px.pie(
                    values=list(target_filtered.values()),
                    names=list(target_filtered.keys()),
                    title="Target Portfolio Allocation",
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)

        self._render_allocation_comparison(current_allocations, target_allocations)

    def _render_allocation_comparison(self, current, target):
        threshold = st.session_state.rebalance_threshold_pct
        st.write(f"**Ticker Allocation Comparison** _(threshold: ±{threshold:.2f}%)_")

        comparison_data = []
        for ticker in set(current.keys()) | set(target.keys()):
            current_pct = current.get(ticker, 0.0)
            target_pct = target.get(ticker, 0.0)
            diff = target_pct - current_pct

            if abs(diff) < threshold:
                status = "✅ skip"
            elif diff > 0:
                status = "📈 buy"
            else:
                status = "📉 sell"

            comparison_data.append({
                "Status": status,
                "Ticker": ticker,
                "Current %": f"{current_pct:.2f}%",
                "Target %": f"{target_pct:.2f}%",
                "Difference": f"{diff:+.2f}%",
            })

        comparison_data.sort(
            key=lambda x: abs(float(x["Difference"].replace("%", "").replace("+", ""))),
            reverse=True,
        )
        st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

    # =========================================================================
    # Portfolio Volatility
    # =========================================================================

    def _render_volatility(self, account):
        st.subheader("📉 Portfolio Volatility")

        if not HAS_YFINANCE:
            st.warning("Install `yfinance` to enable volatility analysis: `pip install yfinance`")
            return

        # Toggle between current holdings and target allocations
        col_toggle, col_period = st.columns([2, 1])

        with col_toggle:
            view_mode = st.radio(
                "Analyze",
                ["📊 Current Holdings", "🎯 Target Allocations"],
                horizontal=True,
                key="vol_view_mode",
            )

        # Build symbols and weights based on selected mode
        symbols = []
        weights = []

        if view_mode == "📊 Current Holdings":
            total_value = account.net_liquidation_value
            if total_value <= 0:
                st.info("No portfolio value to analyze.")
                return
            for pos in account.positions:
                if pos.instrument.type == "EQUITY" and pos.current_value > 0:
                    symbols.append(pos.instrument.symbol)
                    weights.append(pos.current_value / total_value)
            mode_label = "Current Holdings"
        else:
            target = st.session_state.target_allocations
            for ticker, pct in target.items():
                if ticker != "CASH" and pct > 0:
                    symbols.append(ticker)
                    weights.append(pct / 100.0)
            mode_label = "Target Allocations"

        if not symbols:
            st.info(f"No equity tickers in {mode_label.lower()} to analyze.")
            return

        # Re-normalize weights to sum to 1 (in case CASH was excluded)
        import numpy as np
        w_total = sum(weights)
        if w_total > 0:
            weights = [w / w_total for w in weights]

        # Period selector
        period_map = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y"}
        with col_period:
            period_label = st.selectbox("Period", list(period_map.keys()), index=0, key="vol_period")
        yf_period = period_map[period_label]

        # Cache key includes mode so switching doesn't reuse wrong data
        mode_key = "current" if "Current" in view_mode else "target"
        cache_key = f"vol_data_{mode_key}_{period_label}_{'_'.join(sorted(symbols))}"
        if cache_key not in st.session_state:
            st.session_state[cache_key] = None

        if st.button("📊 Calculate Volatility", use_container_width=True) or st.session_state[cache_key] is not None:
            try:
                if st.session_state[cache_key] is None:
                    with st.spinner(f"Downloading {period_label} price history for {len(symbols)} tickers..."):
                        data = yf.download(symbols, period=yf_period, interval="1d", progress=False)

                        if data.empty:
                            st.warning("Could not download price data.")
                            return

                        if len(symbols) == 1:
                            closes = data["Close"].to_frame(name=symbols[0])
                        else:
                            closes = data["Close"]

                        closes = closes.dropna(axis=1, how="all")
                        st.session_state[cache_key] = closes
                else:
                    closes = st.session_state[cache_key]

                if closes.empty or len(closes) < 2:
                    st.warning("Not enough price data to calculate volatility.")
                    return

                returns = closes.pct_change().dropna()

                available = [s for s in symbols if s in returns.columns]
                missing = [s for s in symbols if s not in returns.columns]
                if missing:
                    st.warning(f"No price data for: {', '.join(missing)}")
                if not available:
                    st.warning("No price data available for any tickers.")
                    return

                w = np.array([weights[symbols.index(s)] for s in available])
                w = w / w.sum()

                portfolio_returns = (returns[available] * w).sum(axis=1)

                daily_vol = portfolio_returns.std()
                annual_vol = daily_vol * np.sqrt(252)
                annual_return = portfolio_returns.mean() * 252
                sharpe = annual_return / annual_vol if annual_vol > 0 else 0

                cumulative = (1 + portfolio_returns).cumprod()
                peak = cumulative.cummax()
                drawdown = (cumulative - peak) / peak
                max_dd = drawdown.min() * 100

                stock_vols = returns[available].std() * np.sqrt(252)

                # --- Display ---
                st.caption(f"Analyzing: **{mode_label}** ({len(available)} tickers)")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Portfolio Vol (ann.)", f"{annual_vol * 100:.1f}%")
                col2.metric("Daily Vol", f"{daily_vol * 100:.2f}%")
                col3.metric("Sharpe Ratio", f"{sharpe:.2f}")
                col4.metric("Max Drawdown", f"{max_dd:.1f}%")

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=cumulative.index,
                    y=(cumulative - 1) * 100,
                    mode="lines",
                    name=mode_label,
                    line=dict(color="#1f77b4", width=2),
                ))

                if "SPY" not in available:
                    try:
                        spy_data = yf.download("SPY", period=yf_period, interval="1d", progress=False)
                        if not spy_data.empty:
                            spy_ret = spy_data["Close"].pct_change().dropna()
                            spy_cum = (1 + spy_ret).cumprod()
                            fig.add_trace(go.Scatter(
                                x=spy_cum.index,
                                y=(spy_cum - 1) * 100,
                                mode="lines",
                                name="SPY",
                                line=dict(color="#ff7f0e", width=2, dash="dash"),
                            ))
                    except Exception:
                        pass

                fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
                fig.update_layout(
                    title=f"{mode_label} vs SPY — {period_label}",
                    yaxis_title="Return (%)", yaxis_ticksuffix="%",
                    hovermode="x unified", height=350,
                )
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("📋 Per-Stock Volatility"):
                    vol_rows = []
                    for s in available:
                        vol_rows.append({
                            "Symbol": s,
                            "Weight": f"{weights[symbols.index(s)] * 100:.1f}%",
                            "Annual Vol": f"{stock_vols[s] * 100:.1f}%",
                            "Contribution": f"{(weights[symbols.index(s)] * stock_vols[s]) * 100:.2f}%",
                        })
                    vol_rows.sort(key=lambda x: float(x["Annual Vol"].replace("%", "")), reverse=True)
                    st.dataframe(pd.DataFrame(vol_rows), use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"Volatility calculation error: {e}")
                logger.error(f"Volatility error: {e}")

    # =========================================================================
    # Rebalancing
    # =========================================================================

    def _render_rebalancing_section(self):
        st.header("⚖️ Portfolio Rebalancing")

        account = st.session_state.portfolio_data

        # =================================================================
        # Ticker Validation — always visible
        # =================================================================
        st.subheader("🔎 Ticker Validation")

        non_cash_targets = [t for t in st.session_state.target_allocations if t != "CASH"]

        if non_cash_targets and st.session_state.api_key:
            if st.button("🔎 Validate Target Tickers on Public.com", use_container_width=True):
                if not self.api_client.api_key:
                    self.api_client.set_api_key(st.session_state.api_key)
                with st.spinner(f"Validating {len(non_cash_targets)} tickers..."):
                    try:
                        detailed = self.api_client.validate_tickers_detailed(non_cash_targets)
                        st.session_state.validated_tickers_detail = detailed
                        # Also update the simple validated_tickers for other parts of the UI
                        st.session_state.validated_tickers = {
                            t: d["tradable"] for t, d in detailed.items()
                        }
                    except Exception as e:
                        st.error(f"Validation error: {e}")

            # Always show results if we have them
            detail = st.session_state.get("validated_tickers_detail", {})
            if detail:
                valid_rows = []
                for ticker in non_cash_targets:
                    d = detail.get(ticker)
                    if d is None:
                        valid_rows.append({
                            "Ticker": ticker,
                            "Target %": f"{st.session_state.target_allocations.get(ticker, 0):.1f}%",
                            "Tradable": "⏳ Not checked",
                            "Trading": "—",
                            "Fractional": "—",
                        })
                    else:
                        tradable_icon = "✅" if d["tradable"] else "❌"
                        frac = d["fractional"]
                        if frac == "BUY_AND_SELL":
                            frac_display = "✅ Yes"
                        elif frac == "DISABLED":
                            frac_display = "❌ No (qty only)"
                        elif frac == "LIQUIDATION_ONLY":
                            frac_display = "⚠️ Sell only"
                        else:
                            frac_display = frac
                        valid_rows.append({
                            "Ticker": ticker,
                            "Target %": f"{st.session_state.target_allocations.get(ticker, 0):.1f}%",
                            "Tradable": f"{tradable_icon} {d['trading']}",
                            "Fractional": frac_display,
                        })

                tradable_count = sum(1 for t in non_cash_targets if detail.get(t, {}).get("tradable"))
                invalid = [t for t in non_cash_targets if t in detail and not detail[t]["tradable"]]
                no_fractional = [t for t in non_cash_targets if t in detail and detail[t].get("fractional") == "DISABLED"]

                if invalid:
                    st.error(f"❌ {len(invalid)} not tradable: **{', '.join(invalid)}**")
                elif no_fractional:
                    st.warning(
                        f"✅ All {tradable_count} tradable · "
                        f"⚠️ {len(no_fractional)} don't support fractional/dollar orders: "
                        f"**{', '.join(no_fractional)}** (will use quantity orders)"
                    )
                else:
                    st.success(f"✅ All {tradable_count} tickers tradable with fractional support")

                st.dataframe(pd.DataFrame(valid_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Add target tickers in the sidebar to validate them.")

        st.divider()

        # =================================================================
        # Rebalance calculation
        # =================================================================

        is_valid, error_msg = self.analyzer.validate_target_allocations(
            st.session_state.target_allocations
        )
        if not is_valid:
            st.error(f"Invalid target allocations: {error_msg}")
            return

        try:
            with st.spinner("Calculating rebalancing trades..."):
                target_allocations = st.session_state.target_allocations

                if not self.api_client.api_key or self.api_client.api_key != st.session_state.api_key:
                    self.api_client.set_api_key(st.session_state.api_key)

                # Gather quotes for all relevant symbols
                current_symbols = {pos.instrument.symbol for pos in account.positions}
                target_symbols = set(target_allocations.keys())
                all_symbols = current_symbols.union(target_symbols)

                quotes = {}
                if all_symbols:
                    instruments_needed = []

                    for pos in account.positions:
                        instruments_needed.append(pos.instrument)

                    missing_symbols = target_symbols - current_symbols - {"CASH"}
                    for symbol in missing_symbols:
                        search_results = self.api_client.search_instruments(symbol)
                        if search_results:
                            instruments_needed.append(search_results[0])
                        else:
                            st.warning(f"Could not find instrument: {symbol}")

                    if instruments_needed:
                        try:
                            quote_objects = self.api_client.get_quotes(
                                account.account_id, instruments_needed
                            )
                            quotes = {
                                q.instrument.symbol: Decimal(str(q.last))
                                for q in quote_objects
                            }
                        except Exception as e:
                            st.warning(f"Could not fetch live quotes: {e}. Using last known prices.")

                if not quotes:
                    st.info("📊 No live quotes available. Using last known prices from portfolio.")

                # Apply the rebalance threshold from sidebar setting
                self.analyzer.rebalance_threshold_pct = st.session_state.rebalance_threshold_pct

                analysis = self.analyzer.calculate_rebalance_trades(
                    account, target_allocations, quotes
                )
                self._render_rebalance_analysis(analysis)

        except Exception as e:
            st.error(f"Error calculating rebalancing trades: {e}")
            logger.error(f"Rebalancing calculation failed: {e}")

    def _render_rebalance_analysis(self, analysis: RebalanceAnalysis):
        if not analysis.recommended_trades:
            st.info("🎯 Your portfolio is already well-balanced! No trades needed.")
            return

        st.subheader("📋 Recommended Trades")

        trades_data = []
        total_buy = Decimal("0")
        total_sell = Decimal("0")

        for trade in analysis.recommended_trades:
            trades_data.append({
                "Action": trade.action,
                "Symbol": trade.instrument.symbol,
                "Type": trade.instrument.type,
                "Quantity": f"{trade.quantity:,.6f}".rstrip("0").rstrip("."),
                "Estimated Value": f"${trade.estimated_value:,.2f}",
                "Current Qty": f"{trade.current_quantity:,.6f}".rstrip("0").rstrip("."),
                "Reason": trade.reason,
            })

            if trade.action == "BUY":
                total_buy += trade.estimated_value
            else:
                total_sell += trade.estimated_value

        st.dataframe(pd.DataFrame(trades_data), use_container_width=True, hide_index=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Buys", f"${total_buy:,.2f}")
        with col2:
            st.metric("Total Sells", f"${total_sell:,.2f}")
        with col3:
            st.metric("Net Cash Change", f"${total_sell - total_buy:,.2f}")

        self._render_execution_controls(analysis)

    # =========================================================================
    # Execution
    # =========================================================================

    def _render_execution_controls(self, analysis: RebalanceAnalysis):
        st.subheader("🚀 Execute Trades")

        if st.session_state.test_mode:
            st.info("🧪 Test mode — trades will be simulated only")

            if st.button("▶️ Simulate All Trades", type="primary", use_container_width=True):
                self._simulate_trades(analysis.recommended_trades)
        else:
            st.warning("🔴 **LIVE MODE** — Orders will be submitted to Public.com!")

            # Preflight preview
            if st.button("🔎 Preview Orders (Preflight)", use_container_width=True):
                self._preflight_all(analysis.recommended_trades)

            st.divider()

            confirm = st.checkbox(
                "I understand these orders will be sent to my live Public.com account"
            )

            if confirm:
                if st.button(
                    "⚠️ EXECUTE ALL ORDERS",
                    type="primary",
                    use_container_width=True,
                ):
                    self._execute_trades(analysis.recommended_trades)
            else:
                st.button("Execute All Orders", disabled=True, use_container_width=True)

    def _simulate_trades(self, trades):
        if not trades:
            st.warning("No trades to simulate")
            return

        st.success("🧪 Starting Trade Simulation...")

        simulation_results = []
        total_value = 0

        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, trade in enumerate(trades):
            progress_bar.progress((i + 1) / len(trades))
            status_text.text(
                f"Simulating {trade.action} {trade.quantity} shares of {trade.instrument.symbol}"
            )
            time.sleep(0.3)

            price_per_share = (
                trade.estimated_value / trade.quantity if trade.quantity > 0 else 0
            )
            total_value += float(trade.estimated_value)

            simulation_results.append({
                "Order": f"#{i + 1}",
                "Action": trade.action,
                "Ticker": trade.instrument.symbol,
                "Quantity": f"{trade.quantity:.6f}".rstrip("0").rstrip("."),
                "Est. Price": f"${price_per_share:.2f}",
                "Est. Value": f"${trade.estimated_value:.2f}",
                "Status": "✅ Simulated",
            })

        status_text.text("✅ All trades simulated successfully!")
        progress_bar.empty()

        st.subheader("📊 Simulation Results")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Trades", len(trades))
        with col2:
            st.metric("Total Value", f"${total_value:.2f}")
        with col3:
            buys = len([t for t in trades if t.action == "BUY"])
            sells = len(trades) - buys
            st.metric("Buy / Sell", f"{buys} / {sells}")

        st.dataframe(pd.DataFrame(simulation_results), use_container_width=True, hide_index=True)
        st.success(f"✅ Simulated {len(trades)} trades worth ${total_value:,.2f}")

    def _preflight_all(self, trades):
        """Run preflight (order preview) for all trades."""
        account = st.session_state.portfolio_data
        st.write("**Order Preflight Preview:**")

        preflight_results = []
        for trade in trades:
            trade_amount = f"{float(trade.estimated_value):.2f}"
            try:
                # For sells, use quantity (amount may not work for sell preflights)
                # For buys, use amount (dollar-based)
                if trade.action == "SELL":
                    preview = self.api_client.preview_order(
                        account.account_id,
                        trade.instrument,
                        trade.action,
                        quantity=str(trade.quantity),
                    )
                else:
                    preview = self.api_client.preview_order(
                        account.account_id,
                        trade.instrument,
                        trade.action,
                        amount=trade_amount,
                    )
                preflight_results.append({
                    "Symbol": trade.instrument.symbol,
                    "Side": trade.action,
                    "Amount": f"${trade_amount}",
                    "Est. Cost": preview.get("estimatedCost", "N/A"),
                    "Est. Proceeds": preview.get("estimatedProceeds", "N/A"),
                    "BP Required": preview.get("buyingPowerRequirement", "N/A"),
                    "Commission": preview.get("estimatedCommission", "$0.00"),
                    "Status": "✅ OK",
                })
            except Exception as e:
                preflight_results.append({
                    "Symbol": trade.instrument.symbol,
                    "Side": trade.action,
                    "Amount": f"${trade_amount}",
                    "Est. Cost": "N/A",
                    "Est. Proceeds": "N/A",
                    "BP Required": "N/A",
                    "Commission": "N/A",
                    "Status": f"❌ {e}",
                })

        st.dataframe(pd.DataFrame(preflight_results), use_container_width=True, hide_index=True)

    def _execute_trades(self, trades):
        """
        Execute real trades via the Public.com API.

        SELLS use quantity (share count) — Public.com rejects dollar-amount
        sells when the amount is close to the full position value.
        BUYS use dollar amounts (notional) — simpler and avoids precision issues.

        Strategy:
          Phase 1 — Sell overweight positions by quantity
          Phase 2 — Buy underweight positions by dollar amount
        """
        st.warning("🔴 Executing live orders...")

        account = st.session_state.portfolio_data
        account_id = account.account_id
        pace = st.session_state.get("order_pace_seconds", 1.0)

        sell_trades = [t for t in trades if t.action == "SELL"]
        buy_trades = [t for t in trades if t.action == "BUY"]
        total = len(trades)

        est_seconds = total * pace + (20 if sell_trades and buy_trades else 0)
        est_minutes = est_seconds / 60

        progress_bar = st.progress(0)
        status_text = st.empty()
        phase_text = st.empty()
        all_results: List[tuple] = []
        completed = 0

        st.info(
            f"⏱️ Estimated time: ~{est_minutes:.1f} min "
            f"({total} orders × {pace:.0f}s pacing)"
        )

        # =================================================================
        # Phase 1: SELLS — use quantity (not dollar amount)
        # =================================================================
        if sell_trades:
            phase_text.markdown(
                f"### 📉 Phase 1: Selling {len(sell_trades)} positions"
            )

        for i, trade in enumerate(sell_trades):
            completed += 1
            progress_bar.progress(completed / total)
            qty = str(trade.quantity)
            status_text.text(
                f"[{completed}/{total}] SELL {qty} shares of "
                f"{trade.instrument.symbol}..."
            )

            result = self.api_client.place_order(
                account_id,
                trade.instrument,
                "SELL",
                quantity=qty,
            )
            all_results.append((trade, result))

            if result.status == "FAILED":
                time.sleep(5.0)
                status_text.text(
                    f"[{completed}/{total}] 🔄 Retrying SELL "
                    f"{trade.instrument.symbol}..."
                )
                result = self.api_client.place_order(
                    account_id,
                    trade.instrument,
                    "SELL",
                    quantity=qty,
                )
                all_results[-1] = (trade, result)

            if i < len(sell_trades) - 1:
                time.sleep(pace)

        # Pause between phases
        if sell_trades and buy_trades:
            status_text.text("⏳ Waiting for sells to settle before buying...")
            time.sleep(5.0)

        # =================================================================
        # Phase 2: BUYS
        # =================================================================
        if buy_trades:
            phase_text.markdown(
                f"### 📈 Phase 2: Buying {len(buy_trades)} positions"
            )

        for i, trade in enumerate(buy_trades):
            completed += 1
            progress_bar.progress(completed / total)
            buy_amount = f"{float(trade.estimated_value):.2f}"
            status_text.text(
                f"[{completed}/{total}] BUY ${buy_amount} of "
                f"{trade.instrument.symbol}..."
            )

            result = self.api_client.place_order(
                account_id,
                trade.instrument,
                "BUY",
                amount=buy_amount,
            )
            all_results.append((trade, result))

            if result.status == "FAILED":
                time.sleep(5.0)
                status_text.text(
                    f"[{completed}/{total}] 🔄 Retrying BUY "
                    f"{trade.instrument.symbol}..."
                )
                result = self.api_client.place_order(
                    account_id,
                    trade.instrument,
                    "BUY",
                    amount=buy_amount,
                )
                all_results[-1] = (trade, result)

            if i < len(buy_trades) - 1:
                time.sleep(pace)

        # =================================================================
        # Retry pass
        # =================================================================
        failed_indices = [
            i for i, (_, r) in enumerate(all_results) if r.status == "FAILED"
        ]

        if failed_indices:
            phase_text.markdown("### 🔄 Retrying Failed Orders")
            for retry_round in range(1, 3):
                if not failed_indices:
                    break

                status_text.text(
                    f"⏳ Retry round {retry_round}/2 — waiting 20s "
                    f"before retrying {len(failed_indices)} orders..."
                )
                time.sleep(5.0)

                still_failed = []
                for idx in failed_indices:
                    trade, _ = all_results[idx]
                    retry_amount = f"{float(trade.estimated_value):.2f}"
                    status_text.text(
                        f"🔄 Retrying {trade.action} ${retry_amount} "
                        f"{trade.instrument.symbol} (round {retry_round})..."
                    )

                    result = self.api_client.place_order(
                        account_id,
                        trade.instrument,
                        trade.action,
                        amount=retry_amount,
                    )
                    all_results[idx] = (trade, result)

                    if result.status == "FAILED":
                        still_failed.append(idx)

                    time.sleep(pace)

                failed_indices = still_failed

        # =================================================================
        # Results
        # =================================================================
        progress_bar.empty()
        status_text.empty()
        phase_text.empty()

        order_results = [r for _, r in all_results]
        st.session_state.order_results = order_results

        successful = [r for r in order_results if r.status != "FAILED"]
        failed = [r for r in order_results if r.status == "FAILED"]

        sell_ok = sum(1 for _, r in all_results[:len(sell_trades)] if r.status != "FAILED")
        buy_ok = sum(1 for _, r in all_results[len(sell_trades):] if r.status != "FAILED")

        if successful:
            st.success(
                f"✅ {len(successful)}/{total} orders submitted — "
                f"{sell_ok} sells, {buy_ok} buys"
            )

        if failed:
            st.error(f"❌ {len(failed)}/{total} orders failed after retries:")
            with st.expander("🔍 Click to see full error details", expanded=True):
                for r in failed:
                    st.markdown(f"**{r.side} {r.symbol}:**")
                    st.code(r.error or "No error message captured", language=None)
                st.info(
                    "💡 Common causes: market closed, insufficient buying power, "
                    "fractional shares not supported for this symbol, "
                    "dollar amount below minimum, or instrument not tradable. "
                    "Check Streamlit Cloud logs for the full API response."
                )

        # Refresh portfolio
        self._refresh_portfolio_data()

    # =========================================================================
    # Order History
    # =========================================================================

    def _render_order_history(self):
        st.subheader("📜 Recent Order Results")

        order_data = []
        for r in st.session_state.order_results:
            order_data.append({
                "Order ID": r.order_id[:12] + "...",
                "Symbol": r.symbol,
                "Side": r.side,
                "Status": r.status,
                "Error": r.error or "",
            })

        st.dataframe(pd.DataFrame(order_data), use_container_width=True, hide_index=True)

        # Check order statuses
        account = st.session_state.portfolio_data
        if account and st.button("🔄 Check Order Statuses"):
            updated = []
            for r in st.session_state.order_results:
                if r.status == "FAILED":
                    updated.append(r)
                    continue
                try:
                    order_info = self.api_client.get_order(
                        account.account_id, r.order_id
                    )
                    r.status = order_info.get("status", r.status)
                    r.filled_quantity = order_info.get("filledQuantity")
                    r.average_price = order_info.get("averagePrice")
                except Exception:
                    pass
                updated.append(r)
            st.session_state.order_results = updated
            st.rerun()

        if st.button("🗑️ Clear Order History"):
            st.session_state.order_results = []
            st.rerun()
