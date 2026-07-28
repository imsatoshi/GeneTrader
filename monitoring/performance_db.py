"""
Performance database for storing time-series trading metrics.

This module provides SQLite-based storage for live trading performance data,
enabling historical analysis and degradation detection.
"""

import sqlite3
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from utils.time_utils import utc_now, to_utc, parse_utc, utc_iso
from typing import Any, Dict, List, Optional, Generator
from utils.logging_config import logger


@dataclass
class PerformanceSnapshot:
    """A point-in-time snapshot of trading performance."""
    timestamp: datetime
    strategy_name: str
    total_profit: float
    total_profit_pct: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_profit_per_trade: float
    avg_duration_minutes: float
    max_drawdown: float
    profit_factor: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    expectancy: Optional[float] = None
    open_trades: int = 0
    balance: float = 0.0
    extra_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['timestamp'] = utc_iso(self.timestamp)
        if self.extra_data:
            d['extra_data'] = json.dumps(self.extra_data)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceSnapshot':
        """Create from dictionary."""
        data = data.copy()
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = parse_utc(data['timestamp'])
        if isinstance(data.get('extra_data'), str):
            data['extra_data'] = json.loads(data['extra_data'])
        return cls(**data)


@dataclass
class TradeRecord:
    """Record of a single trade for storage."""
    trade_id: int
    pair: str
    open_date: datetime
    close_date: Optional[datetime]
    open_rate: float
    close_rate: Optional[float]
    profit_ratio: float
    profit_abs: float
    stake_amount: float
    duration_minutes: int
    strategy: str
    is_short: bool = False
    exit_reason: str = ""


class PerformanceDB:
    """
    SQLite database for storing trading performance metrics.

    Provides methods to store and query performance snapshots and trade records
    for historical analysis and degradation detection.
    """

    def __init__(self, db_path: str = "data/performance.db"):
        """
        Initialize performance database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Performance snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    total_profit REAL,
                    total_profit_pct REAL,
                    win_rate REAL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    avg_profit_per_trade REAL,
                    avg_duration_minutes REAL,
                    max_drawdown REAL,
                    profit_factor REAL,
                    sharpe_ratio REAL,
                    sortino_ratio REAL,
                    expectancy REAL,
                    open_trades INTEGER,
                    balance REAL,
                    extra_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes for efficient queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
                ON performance_snapshots(timestamp)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_snapshots_strategy
                ON performance_snapshots(strategy_name, timestamp)
            ''')

            # Trade records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER NOT NULL,
                    pair TEXT NOT NULL,
                    open_date TEXT NOT NULL,
                    close_date TEXT,
                    open_rate REAL,
                    close_rate REAL,
                    profit_ratio REAL,
                    profit_abs REAL,
                    stake_amount REAL,
                    duration_minutes INTEGER,
                    strategy TEXT,
                    is_short INTEGER DEFAULT 0,
                    exit_reason TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(trade_id, strategy)
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trades_close_date
                ON trade_records(close_date)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_trades_strategy
                ON trade_records(strategy, close_date)
            ''')

            # Backtest baselines table (for comparison)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backtest_baselines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    total_profit_pct REAL,
                    win_rate REAL,
                    avg_profit_per_trade REAL,
                    max_drawdown REAL,
                    profit_factor REAL,
                    sharpe_ratio REAL,
                    total_trades INTEGER,
                    avg_trades_per_day REAL,
                    timerange TEXT,
                    extra_data TEXT
                )
            ''')

            logger.info(f"Initialized performance database at {self.db_path}")

    def save_snapshot(self, snapshot: PerformanceSnapshot) -> int:
        """
        Save a performance snapshot.

        Args:
            snapshot: Performance snapshot to save

        Returns:
            ID of the inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO performance_snapshots (
                    timestamp, strategy_name, total_profit, total_profit_pct,
                    win_rate, total_trades, winning_trades, losing_trades,
                    avg_profit_per_trade, avg_duration_minutes, max_drawdown,
                    profit_factor, sharpe_ratio, sortino_ratio, expectancy,
                    open_trades, balance, extra_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                utc_iso(snapshot.timestamp),
                snapshot.strategy_name,
                snapshot.total_profit,
                snapshot.total_profit_pct,
                snapshot.win_rate,
                snapshot.total_trades,
                snapshot.winning_trades,
                snapshot.losing_trades,
                snapshot.avg_profit_per_trade,
                snapshot.avg_duration_minutes,
                snapshot.max_drawdown,
                snapshot.profit_factor,
                snapshot.sharpe_ratio,
                snapshot.sortino_ratio,
                snapshot.expectancy,
                snapshot.open_trades,
                snapshot.balance,
                json.dumps(snapshot.extra_data) if snapshot.extra_data else None
            ))
            return cursor.lastrowid

    def save_trade(self, trade: TradeRecord) -> bool:
        """
        Save or update a trade record.

        Args:
            trade: Trade record to save

        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO trade_records (
                    trade_id, pair, open_date, close_date, open_rate, close_rate,
                    profit_ratio, profit_abs, stake_amount, duration_minutes,
                    strategy, is_short, exit_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade.trade_id,
                trade.pair,
                utc_iso(trade.open_date),
                utc_iso(trade.close_date) if trade.close_date else None,
                trade.open_rate,
                trade.close_rate,
                trade.profit_ratio,
                trade.profit_abs,
                trade.stake_amount,
                trade.duration_minutes,
                trade.strategy,
                1 if trade.is_short else 0,
                trade.exit_reason
            ))
            return True

    def save_baseline(
        self,
        strategy_name: str,
        metrics: Dict[str, Any],
        timerange: str = ""
    ) -> int:
        """
        Save backtest baseline for comparison.

        Args:
            strategy_name: Name of the strategy
            metrics: Backtest metrics
            timerange: Timerange used for backtest

        Returns:
            ID of the inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO backtest_baselines (
                    strategy_name, total_profit_pct, win_rate, avg_profit_per_trade,
                    max_drawdown, profit_factor, sharpe_ratio, total_trades,
                    avg_trades_per_day, timerange, extra_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                strategy_name,
                metrics.get('total_profit_pct'),
                metrics.get('win_rate'),
                metrics.get('avg_profit_per_trade'),
                metrics.get('max_drawdown'),
                metrics.get('profit_factor'),
                metrics.get('sharpe_ratio'),
                metrics.get('total_trades'),
                metrics.get('avg_trades_per_day'),
                timerange,
                json.dumps(metrics)
            ))
            return cursor.lastrowid

    def get_latest_baseline(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get the most recent backtest baseline for a strategy."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM backtest_baselines
                WHERE strategy_name = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (strategy_name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def get_snapshots(
        self,
        strategy_name: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[PerformanceSnapshot]:
        """
        Get performance snapshots.

        Args:
            strategy_name: Filter by strategy name
            since: Start datetime
            until: End datetime
            limit: Maximum number of records

        Returns:
            List of PerformanceSnapshot objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = 'SELECT * FROM performance_snapshots WHERE 1=1'
            params = []

            if strategy_name:
                query += ' AND strategy_name = ?'
                params.append(strategy_name)
            if since:
                query += ' AND timestamp >= ?'
                params.append(utc_iso(since))
            if until:
                query += ' AND timestamp <= ?'
                params.append(utc_iso(until))

            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            snapshots = []
            for row in rows:
                data = dict(row)
                # Remove database-specific fields
                data.pop('id', None)
                data.pop('created_at', None)
                snapshots.append(PerformanceSnapshot.from_dict(data))

            return snapshots

    def get_trades(
        self,
        strategy: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[TradeRecord]:
        """
        Get trade records.

        Args:
            strategy: Filter by strategy name
            since: Start datetime (based on close_date)
            until: End datetime (based on close_date)
            limit: Maximum number of records

        Returns:
            List of TradeRecord objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = 'SELECT * FROM trade_records WHERE close_date IS NOT NULL'
            params = []

            if strategy:
                query += ' AND strategy = ?'
                params.append(strategy)
            if since:
                query += ' AND close_date >= ?'
                params.append(utc_iso(since))
            if until:
                query += ' AND close_date <= ?'
                params.append(utc_iso(until))

            query += ' ORDER BY close_date DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            trades = []
            for row in rows:
                trades.append(TradeRecord(
                    trade_id=row['trade_id'],
                    pair=row['pair'],
                    open_date=parse_utc(row['open_date']),
                    close_date=parse_utc(row['close_date']),
                    open_rate=row['open_rate'],
                    close_rate=row['close_rate'],
                    profit_ratio=row['profit_ratio'],
                    profit_abs=row['profit_abs'],
                    stake_amount=row['stake_amount'],
                    duration_minutes=row['duration_minutes'],
                    strategy=row['strategy'],
                    is_short=bool(row['is_short']),
                    exit_reason=row['exit_reason'] or ""
                ))

            return trades

    def get_rolling_metrics(
        self,
        strategy_name: str,
        window_hours: int = 168  # 7 days
    ) -> List[PerformanceSnapshot]:
        """
        Get snapshots within a rolling window.

        Args:
            strategy_name: Strategy to query
            window_hours: Window size in hours

        Returns:
            List of snapshots within the window
        """
        since = utc_now() - timedelta(hours=window_hours)
        return self.get_snapshots(
            strategy_name=strategy_name,
            since=since,
            limit=10000
        )

    def cleanup_old_data(self, retention_days: int = 365) -> int:
        """
        Remove data older than retention period.

        Args:
            retention_days: Number of days to retain

        Returns:
            Number of deleted records
        """
        cutoff = utc_now() - timedelta(days=retention_days)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Delete old snapshots
            cursor.execute(
                'DELETE FROM performance_snapshots WHERE timestamp < ?',
                (utc_iso(cutoff),)
            )
            snapshots_deleted = cursor.rowcount

            # Delete old trades
            cursor.execute(
                'DELETE FROM trade_records WHERE close_date < ?',
                (utc_iso(cutoff),)
            )
            trades_deleted = cursor.rowcount

            logger.info(f"Cleanup: deleted {snapshots_deleted} snapshots, {trades_deleted} trades")
            return snapshots_deleted + trades_deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM performance_snapshots')
            snapshot_count = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM trade_records')
            trade_count = cursor.fetchone()[0]

            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM performance_snapshots')
            row = cursor.fetchone()
            date_range = (row[0], row[1]) if row[0] else (None, None)

            return {
                'snapshot_count': snapshot_count,
                'trade_count': trade_count,
                'date_range': date_range,
                'db_path': self.db_path,
                'db_size_mb': os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0
            }
