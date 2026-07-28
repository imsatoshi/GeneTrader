"""
Freqtrade REST API client for live performance monitoring.

This module provides a client for interacting with Freqtrade's REST API
to collect live trading data, performance metrics, and system status.
"""

import os
import time
import requests
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from utils.time_utils import utc_now, to_utc, parse_utc
from typing import Any, Dict, List, Optional
from utils.logging_config import logger


@dataclass
class Trade:
    """Represents a single trade from Freqtrade."""
    trade_id: int
    pair: str
    is_open: bool
    open_date: datetime
    close_date: Optional[datetime]
    open_rate: float
    close_rate: Optional[float]
    profit_ratio: float
    profit_abs: float
    stake_amount: float
    amount: float
    fee_open: float
    fee_close: float
    is_short: bool = False
    leverage: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: str = ""
    timeframe: str = ""

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'Trade':
        """Create Trade from Freqtrade API response."""
        return cls(
            trade_id=data.get('trade_id', 0),
            pair=data.get('pair', ''),
            is_open=data.get('is_open', False),
            # Freqtrade returns UTC, but some versions omit the offset. Normalise
            # to aware UTC so these never get compared against a naive datetime.
            open_date=parse_utc(data.get('open_date')) or utc_now(),
            close_date=parse_utc(data.get('close_date')),
            open_rate=float(data.get('open_rate', 0)),
            close_rate=float(data.get('close_rate', 0)) if data.get('close_rate') else None,
            profit_ratio=float(data.get('profit_ratio', 0)),
            profit_abs=float(data.get('profit_abs', 0)),
            stake_amount=float(data.get('stake_amount', 0)),
            amount=float(data.get('amount', 0)),
            fee_open=float(data.get('fee_open', 0)),
            fee_close=float(data.get('fee_close', 0)),
            is_short=data.get('is_short', False),
            leverage=float(data.get('leverage', 1.0)),
            stop_loss=float(data.get('stop_loss')) if data.get('stop_loss') else None,
            take_profit=float(data.get('take_profit')) if data.get('take_profit') else None,
            strategy=data.get('strategy', ''),
            timeframe=data.get('timeframe', ''),
        )


@dataclass
class Balance:
    """Represents account balance."""
    currency: str
    free: float
    used: float
    total: float


@dataclass
class SystemStatus:
    """Represents Freqtrade system status."""
    status: str  # running, stopped, etc.
    running: bool
    max_open_trades: int
    open_trades: int
    trading_enabled: bool
    strategy: str
    timeframe: str
    exchange: str
    state: str


class FreqtradeClient:
    """
    REST API client for Freqtrade.

    Provides methods to fetch live trading data, performance metrics,
    and system status from a running Freqtrade instance.
    """

    def __init__(
        self,
        api_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        Initialize Freqtrade client.

        Args:
            api_url: Base URL of the Freqtrade API (e.g., "http://localhost:8080")
            username: API username (falls back to FREQTRADE_USERNAME env var)
            password: API password (falls back to FREQTRADE_PASSWORD env var)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.api_url = api_url.rstrip('/')
        self.username = username or os.environ.get('FREQTRADE_USERNAME')
        self.password = password or os.environ.get('FREQTRADE_PASSWORD')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def _get_token(self) -> str:
        """Get or refresh access token."""
        # Check if we have a valid token
        if self._access_token and self._token_expiry:
            if utc_now() < self._token_expiry - timedelta(minutes=5):
                return self._access_token

        # Get new token
        if not self.username or not self.password:
            raise ValueError(
                "Credentials not provided. Set FREQTRADE_USERNAME and FREQTRADE_PASSWORD "
                "environment variables, or pass username/password to constructor."
            )

        response = requests.post(
            f"{self.api_url}/api/v1/token/login",
            data={"username": self.username, "password": self.password},
            timeout=self.timeout
        )
        response.raise_for_status()

        self._access_token = response.json()['access_token']
        # Token typically expires in 15 minutes
        self._token_expiry = utc_now() + timedelta(minutes=15)

        logger.debug("Obtained new Freqtrade access token")
        return self._access_token

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Freqtrade API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/api/v1/status")
            data: Request body data
            params: Query parameters

        Returns:
            JSON response as dictionary
        """
        url = f"{self.api_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                token = self._get_token()
                headers = {'Authorization': f'Bearer {token}'}

                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    # Token expired, clear and retry
                    self._access_token = None
                    self._token_expiry = None
                    if attempt < self.max_retries - 1:
                        continue
                raise

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    raise

        return {}

    def ping(self) -> bool:
        """Test API connectivity."""
        try:
            response = requests.get(f"{self.api_url}/api/v1/ping", timeout=self.timeout)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_status(self) -> SystemStatus:
        """Get Freqtrade system status."""
        data = self._request('GET', '/api/v1/show_config')

        return SystemStatus(
            status=data.get('state', 'unknown'),
            running=data.get('state') == 'running',
            max_open_trades=data.get('max_open_trades', 0),
            open_trades=data.get('open_trades', 0),
            trading_enabled=data.get('trading_mode', '') != 'dry_run',
            strategy=data.get('strategy', ''),
            timeframe=data.get('timeframe', ''),
            exchange=data.get('exchange', ''),
            state=data.get('state', 'unknown')
        )

    def get_open_trades(self) -> List[Trade]:
        """Get list of currently open trades."""
        data = self._request('GET', '/api/v1/status')
        return [Trade.from_api_response(t) for t in data]

    def get_closed_trades(
        self,
        limit: int = 500,
        offset: int = 0
    ) -> List[Trade]:
        """
        Get list of closed trades.

        Args:
            limit: Maximum number of trades to return
            offset: Number of trades to skip

        Returns:
            List of closed Trade objects
        """
        data = self._request('GET', '/api/v1/trades', params={
            'limit': limit,
            'offset': offset
        })

        trades = data.get('trades', [])
        return [Trade.from_api_response(t) for t in trades if not t.get('is_open')]

    def get_all_trades(
        self,
        limit: int = 500,
        offset: int = 0
    ) -> List[Trade]:
        """Get all trades (open and closed)."""
        data = self._request('GET', '/api/v1/trades', params={
            'limit': limit,
            'offset': offset
        })

        trades = data.get('trades', [])
        return [Trade.from_api_response(t) for t in trades]

    def get_trades_since(self, since: datetime) -> List[Trade]:
        """
        Get all trades since a specific datetime.

        Args:
            since: Start datetime

        Returns:
            List of Trade objects closed after the given datetime
        """
        all_trades = []
        offset = 0
        limit = 500

        while True:
            trades = self.get_all_trades(limit=limit, offset=offset)
            if not trades:
                break

            # Filter trades after the since datetime
            for trade in trades:
                if trade.close_date and trade.close_date >= since:
                    all_trades.append(trade)
                elif trade.open_date >= since:
                    all_trades.append(trade)

            # Check if we've gone past the since date
            oldest_trade = min(trades, key=lambda t: t.open_date)
            if oldest_trade.open_date < since:
                break

            offset += limit

            # Safety limit
            if offset > 10000:
                logger.warning("Hit safety limit when fetching trades")
                break

        return all_trades

    def get_performance(self) -> Dict[str, Any]:
        """Get overall performance statistics."""
        return self._request('GET', '/api/v1/performance')

    def get_profit(self) -> Dict[str, Any]:
        """Get profit summary."""
        return self._request('GET', '/api/v1/profit')

    def get_balance(self) -> Dict[str, Balance]:
        """Get account balances."""
        data = self._request('GET', '/api/v1/balance')

        balances = {}
        for currency_data in data.get('currencies', []):
            currency = currency_data.get('currency', '')
            balances[currency] = Balance(
                currency=currency,
                free=float(currency_data.get('free', 0)),
                used=float(currency_data.get('used', 0)),
                total=float(currency_data.get('balance', 0))
            )

        return balances

    def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily profit statistics."""
        return self._request('GET', '/api/v1/daily', params={'timescale': days})

    def reload_config(self) -> bool:
        """Reload Freqtrade configuration (hot reload)."""
        try:
            self._request('POST', '/api/v1/reload_config')
            logger.info("Freqtrade config reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reload config: {e}")
            return False

    def start_trading(self) -> bool:
        """Start the trading bot."""
        try:
            self._request('POST', '/api/v1/start')
            logger.info("Freqtrade trading started")
            return True
        except Exception as e:
            logger.error(f"Failed to start trading: {e}")
            return False

    def stop_trading(self) -> bool:
        """Stop the trading bot."""
        try:
            self._request('POST', '/api/v1/stop')
            logger.info("Freqtrade trading stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop trading: {e}")
            return False

    def force_exit(self, trade_id: int) -> bool:
        """Force exit a specific trade."""
        try:
            self._request('POST', '/api/v1/forceexit', data={'tradeid': str(trade_id)})
            logger.info(f"Force exited trade {trade_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to force exit trade {trade_id}: {e}")
            return False
