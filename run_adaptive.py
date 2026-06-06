#!/usr/bin/env python3
"""
Adaptive Optimization Runner

This script runs the on-the-fly optimization system that:
1. Monitors live trading performance from Freqtrade
2. Detects strategy degradation
3. Triggers re-optimization when needed
4. Deploys optimized strategies safely

Usage:
    # Start the adaptive optimization daemon
    python run_adaptive.py --strategy MyStrategy

    # Start with Agent API for Claude integration
    python run_adaptive.py --strategy MyStrategy --api-port 8090

    # One-time performance check
    python run_adaptive.py --strategy MyStrategy --check-only

    # Force optimization
    python run_adaptive.py --strategy MyStrategy --force-optimize
"""

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from utils.logging_config import logger

# Import adaptive optimization components
from monitoring.freqtrade_client import FreqtradeClient
from monitoring.performance_db import PerformanceDB
from monitoring.performance_monitor import PerformanceMonitor
from monitoring.degradation_detector import DegradationDetector

from deployment.version_control import StrategyVersionControl
from deployment.strategy_deployer import StrategyDeployer
from deployment.rollback_manager import RollbackManager

from adaptive.adaptive_optimizer import AdaptiveOptimizer, AdaptiveConfig
from adaptive.scheduler import OptimizationScheduler, ScheduleConfig

from agent_api.api_server import AgentAPI


class AdaptiveRunner:
    """Main runner for the adaptive optimization system."""

    def __init__(self, settings: Settings, strategy_name: str):
        """Initialize the adaptive runner."""
        self.settings = settings
        self.strategy_name = strategy_name
        self.running = False

        # Initialize components
        self._init_components()

    def _init_components(self):
        """Initialize all system components."""
        logger.info("Initializing adaptive optimization system...")

        # Freqtrade client
        try:
            self.client = FreqtradeClient(
                api_url=self.settings.api_url,
                username=self.settings.freqtrade_username,
                password=self.settings.freqtrade_password,
            )
            if self.client.ping():
                logger.info("Connected to Freqtrade API")
            else:
                logger.warning("Freqtrade API not available, running in offline mode")
                self.client = None
        except Exception as e:
            logger.warning(f"Could not connect to Freqtrade: {e}")
            self.client = None

        # Performance database
        db_path = getattr(self.settings, 'performance_db_path', 'data/performance.db')
        self.db = PerformanceDB(db_path)
        logger.info(f"Performance database: {db_path}")

        # Performance monitor
        self.monitor = PerformanceMonitor(
            client=self.client,
            db=self.db,
            snapshot_interval_minutes=getattr(self.settings, 'performance_check_interval_minutes', 5),
            metrics_window_hours=getattr(self.settings, 'metrics_window_hours', 168),
        ) if self.client else None

        # Degradation detector
        self.detector = DegradationDetector(
            profit_threshold=1 - getattr(self.settings, 'reoptimization_trigger_threshold', 0.3),
            drawdown_threshold=getattr(self.settings, 'max_drawdown_limit', 0.35),
        )

        # Version control
        self.version_control = StrategyVersionControl('data/strategy_versions')

        # Strategy deployer
        self.deployer = StrategyDeployer(
            version_control=self.version_control,
            freqtrade_client=self.client,
            target_strategy_dir=self.settings.strategy_dir,
        )

        # Rollback manager
        self.rollback_manager = RollbackManager(
            version_control=self.version_control,
            performance_monitor=self.monitor,
            degradation_detector=self.detector,
        )

        # Adaptive optimizer
        adaptive_config = AdaptiveConfig(
            check_interval_minutes=getattr(self.settings, 'performance_check_interval_minutes', 5),
            metrics_window_hours=getattr(self.settings, 'metrics_window_hours', 168),
            min_trades_for_evaluation=getattr(self.settings, 'minimum_trades_for_evaluation', 20),
            min_hours_between_optimizations=getattr(self.settings, 'minimum_days_between_optimizations', 3) * 24,
            shadow_trading_hours=getattr(self.settings, 'shadow_trading_hours', 24),
            require_approval=getattr(self.settings, 'agent_approval_required_for_deployment', True),
        )

        self.adaptive_optimizer = AdaptiveOptimizer(
            strategy_name=self.strategy_name,
            freqtrade_client=self.client,
            version_control=self.version_control,
            performance_db=self.db,
            config=adaptive_config,
        )

        # Scheduler
        self.scheduler = OptimizationScheduler(
            config=ScheduleConfig(
                min_interval_hours=getattr(self.settings, 'minimum_days_between_optimizations', 3) * 24,
            )
        )

        # Agent API (optional)
        self.api = None

        logger.info("Adaptive optimization system initialized")

    def start_api(self, host: str = '127.0.0.1', port: int = 8090):
        """Start the Agent API server."""
        api_key = getattr(self.settings, 'agent_api_key', '') or os.environ.get('AGENT_API_KEY', '')
        if not api_key:
            raise ValueError("Agent API key required. Set agent_api_key or AGENT_API_KEY.")

        self.api = AgentAPI(
            host=host,
            port=port,
            api_key=api_key,
            performance_db=self.db,
            version_control=self.version_control,
            adaptive_optimizer=self.adaptive_optimizer,
            scheduler=self.scheduler,
        )
        self.api.start()
        logger.info(f"Agent API started on {host}:{port}")

    def check_performance(self) -> dict:
        """Perform a one-time performance check."""
        logger.info(f"Checking performance for {self.strategy_name}...")

        # Get recent snapshots
        snapshots = self.db.get_rolling_metrics(
            self.strategy_name,
            window_hours=getattr(self.settings, 'metrics_window_hours', 168)
        )

        if not snapshots:
            return {
                'status': 'no_data',
                'message': 'No performance data available',
            }

        # Get baseline
        baseline = self.db.get_latest_baseline(self.strategy_name)

        # Detect degradation
        result = self.detector.detect(snapshots, baseline)

        # Get current metrics
        latest = snapshots[0] if snapshots else None

        return {
            'status': 'degraded' if result.is_degraded else 'healthy',
            'degradation_score': result.degradation_score,
            'market_regime': result.market_regime.value,
            'alerts': [a.to_dict() for a in result.alerts],
            'recommendation': result.recommendation,
            'current_metrics': {
                'profit_pct': latest.total_profit_pct if latest else 0,
                'win_rate': latest.win_rate if latest else 0,
                'max_drawdown': latest.max_drawdown if latest else 0,
                'total_trades': latest.total_trades if latest else 0,
            } if latest else None,
            'baseline': baseline,
        }

    def force_optimize(self) -> dict:
        """Force an immediate optimization."""
        logger.info(f"Forcing optimization for {self.strategy_name}...")

        success = self.adaptive_optimizer.force_optimization("manual_trigger")

        return {
            'success': success,
            'message': 'Optimization triggered' if success else 'Optimization failed',
            'status': self.adaptive_optimizer.get_status(),
        }

    def run(self, interval_seconds: int = 60):
        """Run the adaptive optimization loop."""
        self.running = True
        self.adaptive_optimizer.start()

        logger.info(f"Starting adaptive optimization for {self.strategy_name}")
        logger.info(f"Check interval: {interval_seconds} seconds")

        try:
            while self.running:
                # Collect performance data
                if self.monitor:
                    snapshot = self.monitor.collect_and_store()
                    if snapshot:
                        logger.debug(f"Collected snapshot: {snapshot.total_trades} trades")

                # Check for degradation and act
                state = self.adaptive_optimizer.check_and_act()
                logger.debug(f"Adaptive state: {state.value}")

                # Process scheduler queue
                task = self.scheduler.process_queue()
                if task:
                    logger.info(f"Processed scheduled task: {task.id}")

                # Check for rollback
                if self.monitor:
                    metrics = self.monitor.get_current_metrics()
                    rollback_event = self.rollback_manager.check_and_rollback(
                        self.strategy_name, metrics
                    )
                    if rollback_event:
                        logger.warning(f"Rollback triggered: {rollback_event.reason.value}")

                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.stop()

    def stop(self):
        """Stop the adaptive optimization system."""
        self.running = False
        self.adaptive_optimizer.stop()

        if self.api:
            self.api.stop()

        logger.info("Adaptive optimization system stopped")


def main():
    parser = argparse.ArgumentParser(
        description='Adaptive Strategy Optimization System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start monitoring and adaptive optimization
  python run_adaptive.py --strategy MyStrategy

  # Start with Agent API for Claude integration
  python run_adaptive.py --strategy MyStrategy --api-port 8090

  # Check performance without starting daemon
  python run_adaptive.py --strategy MyStrategy --check-only

  # Force immediate optimization
  python run_adaptive.py --strategy MyStrategy --force-optimize

  # Use custom config
  python run_adaptive.py --config my_config.json --strategy MyStrategy
        """
    )

    parser.add_argument('--config', type=str, default='ga.json',
                        help='Configuration file path')
    parser.add_argument('--strategy', type=str, required=True,
                        help='Strategy name to monitor and optimize')
    parser.add_argument('--check-only', action='store_true',
                        help='Perform one-time performance check')
    parser.add_argument('--force-optimize', action='store_true',
                        help='Force immediate optimization')
    parser.add_argument('--api-port', type=int, default=0,
                        help='Start Agent API on this port (0 = disabled)')
    parser.add_argument('--api-host', type=str, default=None,
                        help='Host for Agent API (default: config agent_api_host or 127.0.0.1)')
    parser.add_argument('--interval', type=int, default=60,
                        help='Check interval in seconds (default: 60)')

    args = parser.parse_args()

    # Load settings
    try:
        settings = Settings(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Create runner
    runner = AdaptiveRunner(settings, args.strategy)

    # Handle signals
    def signal_handler(signum, frame):
        logger.info("Shutdown signal received")
        runner.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Execute requested action
    if args.check_only:
        result = runner.check_performance()
        print(json.dumps(result, indent=2))

    elif args.force_optimize:
        result = runner.force_optimize()
        print(json.dumps(result, indent=2))

    else:
        # Start API if requested
        if args.api_port > 0:
            api_host = args.api_host or getattr(settings, 'agent_api_host', '127.0.0.1')
            runner.start_api(host=api_host, port=args.api_port)

        # Run main loop
        runner.run(interval_seconds=args.interval)


if __name__ == '__main__':
    main()
