"""
Shadow trading for strategy validation before live deployment.

This module provides shadow (paper) trading capabilities to validate
strategy performance before deploying to live trading.
"""

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from utils.time_utils import utc_now, to_utc, parse_utc
from enum import Enum
from typing import Any, Dict, List, Optional
from utils.logging_config import logger


class ShadowStatus(Enum):
    """Status of shadow trading session."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ShadowTrade:
    """A simulated trade from shadow trading."""
    trade_id: int
    pair: str
    open_time: datetime
    close_time: Optional[datetime]
    open_rate: float
    close_rate: Optional[float]
    profit_ratio: float
    profit_abs: float
    stake_amount: float
    is_open: bool
    exit_reason: str = ""


@dataclass
class ShadowTradeResult:
    """Result of a shadow trading session."""
    session_id: str
    strategy_name: str
    version_id: str
    status: ShadowStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_hours: float = 0.0
    trades: List[ShadowTrade] = field(default_factory=list)
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_profit: float = 0.0
    total_profit_pct: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    avg_trade_duration_minutes: float = 0.0
    validation_passed: bool = False
    validation_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'session_id': self.session_id,
            'strategy_name': self.strategy_name,
            'version_id': self.version_id,
            'status': self.status.value,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_hours': self.duration_hours,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_profit': self.total_profit,
            'total_profit_pct': self.total_profit_pct,
            'max_drawdown': self.max_drawdown,
            'profit_factor': self.profit_factor,
            'avg_trade_duration_minutes': self.avg_trade_duration_minutes,
            'validation_passed': self.validation_passed,
            'validation_notes': self.validation_notes,
        }


@dataclass
class ShadowConfig:
    """Configuration for shadow trading."""
    duration_hours: int = 24
    min_trades_required: int = 5
    min_win_rate: float = 0.4
    max_drawdown: float = 0.20
    min_profit_pct: float = 0.0
    stake_amount: float = 100.0
    pairs: List[str] = field(default_factory=list)
    timeframe: str = "5m"


class ShadowTrader:
    """
    Shadow trading system for strategy validation.

    Runs a strategy in paper trading mode to validate performance
    before live deployment. Uses Freqtrade's dry-run mode.
    """

    def __init__(
        self,
        freqtrade_path: str,
        config_file: str,
        user_data_dir: str = "/freqtrade/user_data",
        results_dir: str = "data/shadow_results"
    ):
        """
        Initialize shadow trader.

        Args:
            freqtrade_path: Path to freqtrade executable
            config_file: Path to Freqtrade config file
            user_data_dir: Freqtrade user data directory
            results_dir: Directory to store shadow trading results
        """
        self.freqtrade_path = freqtrade_path
        self.config_file = config_file
        self.user_data_dir = user_data_dir
        self.results_dir = results_dir

        os.makedirs(results_dir, exist_ok=True)

        self._active_session: Optional[ShadowTradeResult] = None
        self._process: Optional[subprocess.Popen] = None

    def _generate_session_id(self, strategy_name: str, version_id: str) -> str:
        """Generate unique session ID."""
        timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
        return f"shadow_{strategy_name}_{version_id}_{timestamp}"

    def start_shadow_trading(
        self,
        strategy_name: str,
        version_id: str,
        strategy_file: str,
        config: Optional[ShadowConfig] = None
    ) -> ShadowTradeResult:
        """
        Start a shadow trading session.

        Note: This creates a backtest simulation rather than running
        a live dry-run process, as real dry-run requires a long-running
        process.

        Args:
            strategy_name: Strategy name
            version_id: Version being tested
            strategy_file: Path to strategy file
            config: Shadow trading configuration

        Returns:
            ShadowTradeResult with initial status
        """
        config = config or ShadowConfig()
        session_id = self._generate_session_id(strategy_name, version_id)

        result = ShadowTradeResult(
            session_id=session_id,
            strategy_name=strategy_name,
            version_id=version_id,
            status=ShadowStatus.PENDING,
            started_at=utc_now()
        )

        self._active_session = result

        # Verify strategy file exists
        if not os.path.exists(strategy_file):
            result.status = ShadowStatus.FAILED
            result.validation_notes.append(f"Strategy file not found: {strategy_file}")
            return result

        result.status = ShadowStatus.RUNNING
        logger.info(f"Started shadow trading session: {session_id}")

        return result

    def run_backtest_validation(
        self,
        strategy_file: str,
        config: Optional[ShadowConfig] = None,
        timerange_days: int = 7
    ) -> Dict[str, Any]:
        """
        Run a short backtest as shadow validation.

        This is a practical alternative to real-time shadow trading,
        using recent historical data to validate the strategy.

        Args:
            strategy_file: Path to strategy file
            config: Shadow trading configuration
            timerange_days: Number of days to backtest

        Returns:
            Backtest results
        """
        config = config or ShadowConfig()

        # Calculate timerange for recent data
        end_date = utc_now()
        start_date = end_date - timedelta(days=timerange_days)
        timerange = f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"

        # Build backtest command
        cmd = [
            self.freqtrade_path, "backtesting",
            "--config", self.config_file,
            "--strategy-path", os.path.dirname(strategy_file),
            "--strategy", os.path.basename(strategy_file).replace('.py', ''),
            "--timerange", timerange,
            "--timeframe", config.timeframe,
            "--export", "none",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"Backtest failed: {result.stderr}")
                return {'error': result.stderr}

            # Parse backtest output
            # This would need to parse the actual backtest output
            return {'success': True, 'output': result.stdout}

        except subprocess.TimeoutExpired:
            logger.error("Backtest timed out")
            return {'error': 'Backtest timed out'}
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return {'error': str(e)}

    def validate_results(
        self,
        result: ShadowTradeResult,
        config: ShadowConfig
    ) -> bool:
        """
        Validate shadow trading results against criteria.

        Args:
            result: Shadow trading result
            config: Validation configuration

        Returns:
            True if validation passed
        """
        notes = []
        passed = True

        # Check minimum trades
        if result.total_trades < config.min_trades_required:
            notes.append(f"Insufficient trades: {result.total_trades} < {config.min_trades_required}")
            passed = False

        # Check win rate
        if result.win_rate < config.min_win_rate:
            notes.append(f"Win rate too low: {result.win_rate:.1%} < {config.min_win_rate:.1%}")
            passed = False

        # Check drawdown
        if result.max_drawdown > config.max_drawdown:
            notes.append(f"Drawdown too high: {result.max_drawdown:.1%} > {config.max_drawdown:.1%}")
            passed = False

        # Check profit
        if result.total_profit_pct < config.min_profit_pct:
            notes.append(f"Profit too low: {result.total_profit_pct:.1%} < {config.min_profit_pct:.1%}")
            passed = False

        if passed:
            notes.append("All validation criteria passed")

        result.validation_notes.extend(notes)
        result.validation_passed = passed

        return passed

    def simulate_shadow_session(
        self,
        strategy_name: str,
        version_id: str,
        backtest_metrics: Dict[str, Any]
    ) -> ShadowTradeResult:
        """
        Simulate a shadow trading session from backtest metrics.

        This is used when actual shadow trading is not available,
        using backtest results as a proxy for shadow validation.

        Args:
            strategy_name: Strategy name
            version_id: Version ID
            backtest_metrics: Metrics from backtest

        Returns:
            Simulated ShadowTradeResult
        """
        session_id = self._generate_session_id(strategy_name, version_id)

        result = ShadowTradeResult(
            session_id=session_id,
            strategy_name=strategy_name,
            version_id=version_id,
            status=ShadowStatus.COMPLETED,
            started_at=utc_now(),
            ended_at=utc_now(),
            duration_hours=0.0,
            total_trades=backtest_metrics.get('total_trades', 0),
            winning_trades=backtest_metrics.get('wins', 0),
            losing_trades=backtest_metrics.get('losses', 0),
            win_rate=backtest_metrics.get('win_rate', 0.0),
            total_profit=backtest_metrics.get('profit_total', 0.0),
            total_profit_pct=backtest_metrics.get('total_profit_pct', 0.0),
            max_drawdown=abs(backtest_metrics.get('max_drawdown', 0.0)),
            profit_factor=backtest_metrics.get('profit_factor', 0.0),
        )

        # Auto-validate
        config = ShadowConfig()
        self.validate_results(result, config)

        return result

    def stop_shadow_trading(self) -> Optional[ShadowTradeResult]:
        """
        Stop the current shadow trading session.

        Returns:
            Final ShadowTradeResult
        """
        if not self._active_session:
            return None

        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()

        self._active_session.status = ShadowStatus.CANCELLED
        self._active_session.ended_at = utc_now()

        result = self._active_session
        self._active_session = None
        self._process = None

        return result

    def get_session_status(self) -> Optional[ShadowTradeResult]:
        """Get current session status."""
        return self._active_session

    def save_result(self, result: ShadowTradeResult) -> str:
        """
        Save shadow trading result to file.

        Args:
            result: Result to save

        Returns:
            Path to saved file
        """
        file_path = os.path.join(
            self.results_dir,
            f"{result.session_id}.json"
        )

        with open(file_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        return file_path

    def load_result(self, session_id: str) -> Optional[ShadowTradeResult]:
        """
        Load a previous shadow trading result.

        Args:
            session_id: Session ID to load

        Returns:
            ShadowTradeResult or None
        """
        file_path = os.path.join(self.results_dir, f"{session_id}.json")

        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            return ShadowTradeResult(
                session_id=data['session_id'],
                strategy_name=data['strategy_name'],
                version_id=data['version_id'],
                status=ShadowStatus(data['status']),
                started_at=parse_utc(data['started_at']),
                ended_at=parse_utc(data['ended_at']),
                duration_hours=data.get('duration_hours', 0),
                total_trades=data.get('total_trades', 0),
                winning_trades=data.get('winning_trades', 0),
                losing_trades=data.get('losing_trades', 0),
                win_rate=data.get('win_rate', 0),
                total_profit=data.get('total_profit', 0),
                total_profit_pct=data.get('total_profit_pct', 0),
                max_drawdown=data.get('max_drawdown', 0),
                profit_factor=data.get('profit_factor', 0),
                validation_passed=data.get('validation_passed', False),
                validation_notes=data.get('validation_notes', []),
            )
        except Exception as e:
            logger.error(f"Error loading shadow result: {e}")
            return None

    def list_sessions(self, strategy_name: Optional[str] = None) -> List[str]:
        """
        List shadow trading sessions.

        Args:
            strategy_name: Filter by strategy name

        Returns:
            List of session IDs
        """
        sessions = []

        for filename in os.listdir(self.results_dir):
            if filename.endswith('.json') and filename.startswith('shadow_'):
                session_id = filename[:-5]  # Remove .json

                if strategy_name:
                    if strategy_name in session_id:
                        sessions.append(session_id)
                else:
                    sessions.append(session_id)

        return sorted(sessions, reverse=True)
