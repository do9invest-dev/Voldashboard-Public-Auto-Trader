"""
Public.com API Client

Handles all interactions with the Public.com API including authentication,
account management, market data, and trading operations.

Fully compatible with the Public.com Personal API:
https://public.com/developer
"""

import requests
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Instrument:
    """Represents a financial instrument."""
    symbol: str
    type: str = "EQUITY"


@dataclass
class InstrumentDetail:
    """Full instrument details from the /instruments endpoint."""
    instrument: Instrument
    trading: str = "NONE"
    fractional_trading: str = "NONE"
    option_trading: str = "NONE"
    option_spread_trading: str = "NONE"


@dataclass
class Quote:
    """Represents a market quote for an instrument."""
    instrument: Instrument
    last: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    timestamp: Optional[datetime] = None


@dataclass
class Position:
    """Represents a portfolio position."""
    instrument: Instrument
    quantity: float
    current_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    last_price: float
    percent_of_portfolio: float


@dataclass
class Account:
    """Represents a brokerage account."""
    account_id: str
    account_type: str
    net_liquidation_value: float
    cash_balance: float
    buying_power: float
    positions: List[Position]


@dataclass
class OrderResult:
    """Represents the result of placing an order."""
    order_id: str
    symbol: str
    side: str
    status: str = "SUBMITTED"
    filled_quantity: Optional[str] = None
    average_price: Optional[str] = None
    error: Optional[str] = None


class PublicAPIClient:
    """
    Client for interacting with the Public.com API.

    Provides methods for authentication, account management, market data,
    and trading operations with proper error handling and rate limiting.
    """

    BASE_URL = "https://api.public.com"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.access_token = None
        self.token_expiry = None
        self.session = requests.Session()
        self.last_request_time = 0
        self.read_delay = 0.15   # 150ms between read requests
        self.order_delay = 1.0   # 1s between order placements
        self._instruments_cache: Dict[str, InstrumentDetail] = {}

        if api_key:
            self._generate_access_token()

    # -------------------------------------------------------------------------
    # Auth
    # -------------------------------------------------------------------------

    def _generate_access_token(self) -> None:
        """Exchange the API secret for a short-lived access token."""
        if not self.api_key:
            raise ValueError("API key (secret) not set")

        try:
            token_session = requests.Session()
            token_session.headers.update({"Content-Type": "application/json"})

            response = token_session.post(
                f"{self.BASE_URL}/userapiauthservice/personal/access-tokens",
                json={"validityInMinutes": 60, "secret": self.api_key},
                timeout=30,
            )
            response.raise_for_status()
            token_response = response.json()

            self.access_token = token_response.get("accessToken")
            if not self.access_token:
                raise ValueError("No access token received from API")

            self.token_expiry = time.time() + (55 * 60)

            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            })
            logger.info("Access token generated successfully")

        except requests.RequestException as e:
            logger.error(f"Failed to generate access token: {e}")
            raise ValueError(f"Authentication failed: {e}")

    def _ensure_valid_token(self) -> None:
        if not self.api_key:
            raise ValueError("API key (secret) not set")
        if (
            not self.access_token
            or not self.token_expiry
            or time.time() >= self.token_expiry
        ):
            self._generate_access_token()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        max_retries: int = 4,
        slow: bool = False,
    ) -> Dict[str, Any]:
        """
        Make a rate-limited request to the Public.com API.
        slow=True uses order_delay (1s), slow=False uses read_delay (150ms).
        """
        self._ensure_valid_token()

        url = f"{self.BASE_URL}{endpoint}"
        delay = self.order_delay if slow else self.read_delay

        for attempt in range(max_retries + 1):
            elapsed = time.time() - self.last_request_time
            if elapsed < delay:
                time.sleep(delay - elapsed)

            try:
                if method.upper() == "GET":
                    response = self.session.get(url, params=params, timeout=30)
                elif method.upper() == "POST":
                    response = self.session.post(url, json=data, timeout=30)
                elif method.upper() == "DELETE":
                    response = self.session.delete(url, timeout=30)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                self.last_request_time = time.time()

                # Retry on rate limit (429) or server errors (5xx)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) * 1.0
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                wait_time = max(float(retry_after), wait_time)
                            except ValueError:
                                pass
                        logger.warning(
                            f"Rate limited ({response.status_code}) on "
                            f"{method} {endpoint}, retrying in {wait_time:.1f}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue

                # For ANY non-2xx response, log the full details BEFORE raising
                if not response.ok:
                    resp_body = "(empty)"
                    try:
                        resp_body = response.text[:2000]
                    except Exception:
                        pass
                    logger.error(
                        f"API ERROR [{method} {endpoint}] "
                        f"status={response.status_code}\n"
                        f"  Request payload: {data}\n"
                        f"  Response body: {resp_body}"
                    )
                    response.raise_for_status()

                if response.status_code == 204 or not response.content:
                    return {}
                return response.json()

            except requests.ConnectionError as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 1.0
                    logger.warning(
                        f"Connection error on {method} {endpoint}: {e}, "
                        f"retrying in {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)
                    continue
                logger.error(f"API request failed [{method} {endpoint}]: {e}")
                raise

            except requests.RequestException as e:
                logger.error(f"API request failed [{method} {endpoint}]: {e}")
                raise

        raise requests.RequestException(
            f"Failed after {max_retries} retries: {method} {endpoint}"
        )

    def set_api_key(self, api_key: str) -> None:
        self.api_key = api_key
        self.access_token = None
        self.token_expiry = None
        self._instruments_cache.clear()
        if api_key:
            self._generate_access_token()

    def test_connection(self) -> bool:
        try:
            self.get_accounts()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    # -------------------------------------------------------------------------
    # Account & Portfolio
    # -------------------------------------------------------------------------

    def get_accounts(self) -> List[Account]:
        if not self.api_key:
            raise ValueError("API key not set")

        response = self._make_request("GET", "/userapigateway/trading/account")
        accounts = []
        for account_data in response.get("accounts", []):
            portfolio = self.get_portfolio(account_data["accountId"])
            accounts.append(portfolio)
        return accounts

    def get_portfolio(self, account_id: str) -> Account:
        endpoint = f"/userapigateway/trading/{account_id}/portfolio/v2"
        response = self._make_request("GET", endpoint)

        # Log raw response keys for debugging
        logger.info(f"Portfolio response keys: {list(response.keys())}")

        # Parse positions
        positions = []
        for pos_data in response.get("positions", []):
            try:
                instrument = Instrument(
                    symbol=pos_data["instrument"]["symbol"],
                    type=pos_data["instrument"].get("type", "EQUITY"),
                )
                position = Position(
                    instrument=instrument,
                    quantity=float(pos_data.get("quantity", 0)),
                    current_value=float(pos_data.get("currentValue", 0)),
                    cost_basis=float(
                        pos_data.get("costBasis", {}).get("totalCost", 0)
                    ),
                    unrealized_pnl=float(
                        pos_data.get("instrumentGain", {}).get("gainValue", 0)
                    ),
                    unrealized_pnl_percent=float(
                        pos_data.get("instrumentGain", {}).get("gainPercentage", 0)
                    ),
                    last_price=float(
                        pos_data.get("lastPrice", {}).get("lastPrice", 0)
                    ),
                    percent_of_portfolio=float(
                        pos_data.get("percentOfPortfolio", 0)
                    ),
                )
                positions.append(position)
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Skipping position due to parse error: {e} — raw: {pos_data}")

        # Parse equity array — extract cash and total net value
        # The equity array can contain entries like:
        #   {"type": "CASH", "value": "1234.56", ...}
        #   {"type": "LONG_EQUITY", "value": "5678.90", ...}
        #   {"type": "TOTAL", "value": "6913.46", ...}
        cash_value = 0.0
        api_total_value = None
        equity_entries = response.get("equity", [])
        logger.info(f"Equity entries from API: {equity_entries}")

        for equity in equity_entries:
            eq_type = equity.get("type", "")
            eq_value = equity.get("value", "0")
            try:
                val = float(eq_value)
            except (ValueError, TypeError):
                val = 0.0

            if eq_type == "CASH":
                cash_value = val
            elif eq_type in ("TOTAL", "NET_LIQUIDATION", "TOTAL_EQUITY"):
                api_total_value = val

        # Calculate total value: prefer the API's own total if available,
        # otherwise fall back to summing positions + cash
        positions_value = sum(pos.current_value for pos in positions)
        if api_total_value is not None and api_total_value > 0:
            total_value = api_total_value
        else:
            total_value = positions_value + cash_value

        logger.info(
            f"Portfolio values — API total: {api_total_value}, "
            f"positions: {positions_value}, cash: {cash_value}, "
            f"using total: {total_value}"
        )

        buying_power = 0.0
        bp_data = response.get("buyingPower", {})
        if isinstance(bp_data, dict):
            try:
                buying_power = float(bp_data.get("buyingPower", "0"))
            except (ValueError, TypeError):
                buying_power = 0.0
        logger.info(f"Buying power data: {bp_data} → {buying_power}")

        return Account(
            account_id=account_id,
            account_type=response.get("accountType", "BROKERAGE"),
            net_liquidation_value=total_value,
            cash_balance=cash_value,
            buying_power=buying_power,
            positions=positions,
        )

    # -------------------------------------------------------------------------
    # Instruments
    # -------------------------------------------------------------------------

    def get_all_instruments(self) -> List[InstrumentDetail]:
        """Fetch all tradable instruments from Public.com."""
        response = self._make_request("GET", "/userapigateway/trading/instruments")
        details = []
        for item in response.get("instruments", []):
            inst = Instrument(
                symbol=item["instrument"]["symbol"],
                type=item["instrument"].get("type", "EQUITY"),
            )
            detail = InstrumentDetail(
                instrument=inst,
                trading=item.get("trading", "NONE"),
                fractional_trading=item.get("fractionalTrading", "NONE"),
                option_trading=item.get("optionTrading", "NONE"),
                option_spread_trading=item.get("optionSpreadTrading", "NONE"),
            )
            details.append(detail)
            self._instruments_cache[inst.symbol.upper()] = detail
        return details

    def get_instrument(
        self, symbol: str, inst_type: str = "EQUITY"
    ) -> Optional[InstrumentDetail]:
        """Look up a single instrument by symbol via the API."""
        cache_key = symbol.upper()
        if cache_key in self._instruments_cache:
            return self._instruments_cache[cache_key]

        try:
            response = self._make_request(
                "GET",
                f"/userapigateway/trading/instruments/{symbol.upper()}/{inst_type}",
            )
            inst = Instrument(
                symbol=response["instrument"]["symbol"],
                type=response["instrument"].get("type", inst_type),
            )
            detail = InstrumentDetail(
                instrument=inst,
                trading=response.get("trading", "NONE"),
                fractional_trading=response.get("fractionalTrading", "NONE"),
                option_trading=response.get("optionTrading", "NONE"),
                option_spread_trading=response.get("optionSpreadTrading", "NONE"),
            )
            self._instruments_cache[cache_key] = detail
            return detail
        except Exception as e:
            logger.warning(f"Could not look up instrument {symbol}/{inst_type}: {e}")
            return None

    def validate_instrument(self, symbol: str, inst_type: str = "EQUITY") -> bool:
        """Check whether a symbol is tradable on Public.com."""
        detail = self.get_instrument(symbol, inst_type)
        if detail is None:
            return False
        return detail.trading in ("BUY_AND_SELL", "BUY_ONLY", "SELL_ONLY")

    def search_instruments(self, symbol: str) -> List[Instrument]:
        """Search for instruments by symbol using the single-instrument lookup."""
        detail = self.get_instrument(symbol.upper(), "EQUITY")
        if detail:
            return [detail.instrument]
        return []

    def validate_tickers(self, symbols: List[str]) -> Dict[str, bool]:
        """Batch-validate multiple ticker symbols. Returns {symbol: is_valid}."""
        results = {}
        for sym in symbols:
            sym = sym.strip().upper()
            if not sym or sym == "CASH":
                results[sym] = True
                continue
            results[sym] = self.validate_instrument(sym)
        return results

    def validate_tickers_detailed(self, symbols: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Batch-validate with full detail. Returns:
        {symbol: {"tradable": bool, "trading": str, "fractional": str}}

        fractional tells you if dollar-amount orders work.
        If fractional is DISABLED, you must use quantity-based orders.
        """
        results = {}
        for sym in symbols:
            sym = sym.strip().upper()
            if not sym or sym == "CASH":
                results[sym] = {"tradable": True, "trading": "N/A", "fractional": "N/A"}
                continue
            detail = self.get_instrument(sym)
            if detail is None:
                results[sym] = {"tradable": False, "trading": "NOT FOUND", "fractional": "N/A"}
            else:
                results[sym] = {
                    "tradable": detail.trading in ("BUY_AND_SELL", "BUY_ONLY", "SELL_ONLY"),
                    "trading": detail.trading,
                    "fractional": detail.fractional_trading,
                }
        return results

    # -------------------------------------------------------------------------
    # Market Data
    # -------------------------------------------------------------------------

    def get_quotes(
        self, account_id: str, instruments: List[Instrument]
    ) -> List[Quote]:
        if not instruments:
            return []

        endpoint = f"/userapigateway/marketdata/{account_id}/quotes"
        data = {
            "instruments": [
                {"symbol": inst.symbol, "type": inst.type} for inst in instruments
            ]
        }

        response = self._make_request("POST", endpoint, data=data)
        quotes = []

        for quote_data in response.get("quotes", []):
            if quote_data.get("outcome") == "SUCCESS":
                instrument = Instrument(
                    symbol=quote_data["instrument"]["symbol"],
                    type=quote_data["instrument"].get("type", "EQUITY"),
                )
                quote = Quote(
                    instrument=instrument,
                    last=float(quote_data["last"]),
                    bid=(
                        float(quote_data["bid"]) if quote_data.get("bid") else None
                    ),
                    ask=(
                        float(quote_data["ask"]) if quote_data.get("ask") else None
                    ),
                    volume=quote_data.get("volume"),
                    timestamp=(
                        datetime.fromisoformat(
                            quote_data["lastTimestamp"].replace("Z", "+00:00")
                        )
                        if quote_data.get("lastTimestamp")
                        else None
                    ),
                )
                quotes.append(quote)

        return quotes

    # -------------------------------------------------------------------------
    # Trading
    # -------------------------------------------------------------------------

    def preview_order(
        self,
        account_id: str,
        instrument: Instrument,
        side: str,
        quantity: Optional[str] = None,
        amount: Optional[str] = None,
        order_type: str = "MARKET",
        limit_price: Optional[str] = None,
        stop_price: Optional[str] = None,
        time_in_force: str = "DAY",
    ) -> Dict[str, Any]:
        """Preview an order before placing it (preflight), matching SDK format."""
        endpoint = f"/userapigateway/trading/{account_id}/preflight/single-leg"

        data: Dict[str, Any] = {
            "instrument": {"symbol": instrument.symbol, "type": instrument.type},
            "orderSide": side.upper(),
            "orderType": order_type.upper(),
            "expiration": {"timeInForce": time_in_force},
        }

        # Only for options
        if instrument.type == "OPTION":
            data["openCloseIndicator"] = "OPEN" if side.upper() == "BUY" else "CLOSE"

        if quantity:
            try:
                from decimal import Decimal, ROUND_HALF_UP
                qty = Decimal(str(quantity)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
                data["quantity"] = str(qty)
            except Exception:
                data["quantity"] = str(quantity)
        if amount:
            try:
                from decimal import Decimal, ROUND_HALF_UP
                amt = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                data["amount"] = str(amt)
            except Exception:
                data["amount"] = str(amount)
        if limit_price:
            data["limitPrice"] = str(limit_price)
        if stop_price:
            data["stopPrice"] = str(stop_price)

        logger.info(f"Preflight request: {data}")
        return self._make_request("POST", endpoint, data=data, slow=True)

    def place_order(
        self,
        account_id: str,
        instrument: Instrument,
        side: str,
        quantity: Optional[str] = None,
        amount: Optional[str] = None,
        order_type: str = "MARKET",
        limit_price: Optional[str] = None,
        stop_price: Optional[str] = None,
        time_in_force: str = "DAY",
    ) -> OrderResult:
        """
        Place a trade order matching the official Public.com SDK format.

        Key rules from the SDK:
        - openCloseIndicator is ONLY for options, omit for equities
        - quantity uses 5 decimal places (0.00001 precision)
        - amount uses 2 decimal places
        - None fields must be omitted entirely, not sent as null
        - Either quantity OR amount, never both
        """
        endpoint = f"/userapigateway/trading/{account_id}/order"
        order_id = str(uuid.uuid4())

        # Build payload matching SDK's model_dump(by_alias=True, exclude_none=True)
        data: Dict[str, Any] = {
            "orderId": order_id,
            "instrument": {"symbol": instrument.symbol, "type": instrument.type},
            "orderSide": side.upper(),
            "orderType": order_type.upper(),
            "expiration": {"timeInForce": time_in_force},
        }

        # Only add openCloseIndicator for options, NOT for equities
        if instrument.type == "OPTION":
            data["openCloseIndicator"] = "OPEN" if side.upper() == "BUY" else "CLOSE"

        # Quantity: 5 decimal places to match SDK's Decimal("0.00001") precision
        if quantity:
            try:
                from decimal import Decimal, ROUND_HALF_UP
                qty = Decimal(str(quantity)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
                data["quantity"] = str(qty)
            except Exception:
                data["quantity"] = str(quantity)

        # Amount: 2 decimal places
        if amount:
            try:
                from decimal import Decimal, ROUND_HALF_UP
                amt = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                data["amount"] = str(amt)
            except Exception:
                data["amount"] = str(amount)

        # Only include price fields if actually set (exclude_none behavior)
        if limit_price:
            data["limitPrice"] = str(limit_price)
        if stop_price:
            data["stopPrice"] = str(stop_price)

        logger.info(f"Placing order: {data}")

        try:
            response = self._make_request("POST", endpoint, data=data, slow=True)
            logger.info(f"Order response: {response}")
            return OrderResult(
                order_id=response.get("orderId", order_id),
                symbol=instrument.symbol,
                side=side.upper(),
                status="SUBMITTED",
            )
        except requests.RequestException as e:
            # Extract the actual error message from the API response body
            error_detail = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_body = e.response.json()
                    error_detail = (
                        f"HTTP {e.response.status_code}: "
                        f"{error_body}"
                    )
                except Exception:
                    error_detail = (
                        f"HTTP {e.response.status_code}: "
                        f"{e.response.text[:500]}"
                    )
            logger.error(
                f"Order failed for {side} {instrument.symbol} "
                f"(qty={quantity}, amt={amount}): {error_detail}"
            )
            logger.error(f"Order payload was: {data}")
            return OrderResult(
                order_id=order_id,
                symbol=instrument.symbol,
                side=side.upper(),
                status="FAILED",
                error=error_detail,
            )

    def get_order(self, account_id: str, order_id: str) -> Dict[str, Any]:
        endpoint = f"/userapigateway/trading/{account_id}/order/{order_id}"
        return self._make_request("GET", endpoint)

    def cancel_order(self, account_id: str, order_id: str) -> bool:
        endpoint = f"/userapigateway/trading/{account_id}/order/{order_id}"
        try:
            self._make_request("DELETE", endpoint)
            return True
        except requests.RequestException:
            return False

    def get_account_history(
        self,
        account_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        endpoint = f"/userapigateway/trading/{account_id}/history"
        params: Dict[str, Any] = {"pageSize": page_size}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self._make_request("GET", endpoint, params=params)
