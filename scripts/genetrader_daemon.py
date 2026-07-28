#!/usr/bin/env python3
"""
GeneTrader Daemon - Continuous Adaptive Optimization Service

This daemon runs 24/7 and automatically:
1. Monitors live trading performance
2. Detects strategy degradation
3. Triggers re-optimization when needed
4. Deploys optimized strategies safely
5. Sends notifications via Bark/Webhook

Usage:
    # Run in foreground
    python scripts/genetrader_daemon.py --strategy MyStrategy

    # Run with config
    python scripts/genetrader_daemon.py --config ga.json --strategy MyStrategy

    # Run with custom intervals
    python scripts/genetrader_daemon.py --strategy MyStrategy \
        --check-interval 300 \
        --optimize-interval 86400
"""

import argparse
import json
import os
import signal
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from utils.logging_config import logger

# Import components
from monitoring.freqtrade_client import FreqtradeClient
from monitoring.performance_db import PerformanceDB
from monitoring.performance_monitor import PerformanceMonitor
from monitoring.degradation_detector import DegradationDetector, DetectionResult

from deployment.version_control import StrategyVersionControl
from deployment.strategy_deployer import StrategyDeployer, DeploymentConfig
from deployment.rollback_manager import RollbackManager, RollbackConfig

from adaptive.adaptive_optimizer import AdaptiveOptimizer, AdaptiveConfig, AdaptiveState
from adaptive.scheduler import OptimizationScheduler, ScheduleConfig, SchedulePriority

from agent_api.api_server import AgentAPI


def send_notification(settings: Settings, title: str, message: str, group: str = "genetrader"):
    """Send notification via Bark."""
    try:
        import urllib.request
        import urllib.parse

        bark_endpoint = getattr(settings, 'bark_endpoint', '')
        bark_key = getattr(settings, 'bark_key', '')

        if not bark_endpoint or not bark_key:
            logger.debug("Bark not configured, skipping notification")
            return

        url = f"{bark_endpoint}/{bark_key}/{urllib.parse.quote(title)}/{urllib.parse.quote(message)}?group={group}"

        urllib.request.urlopen(url, timeout=10)
        logger.info(f"Notification sent: {title}")

    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


class GeneTraderDaemon:
    """
    Main daemon for continuous adaptive optimization.

    Responsibilities:
    - Monitor Freqtrade performance continuously
    - Detect strategy degradation
    - Schedule and run optimizations
    - Deploy optimized strategies
    - Auto-rollback on poor performance
    - Send notifications
    """

    def __init__(
        self,
        settings: Settings,
        strategy_name: str,
        check_interval: int = 300,  # 5 minutes
        optimize_interval: int = 86400,  # 24 hours minimum between optimizations
    ):
        self.settings = settings
        self.strategy_name = strategy_name
        self.check_interval = check_interval
        self.optimize_interval = optimize_interval

        self.running = False
        self._shutdown_event = threading.Event()

        # Initialize components
        self._init_components()

        # State tracking
        self._last_check_time: Optional[datetime] = None
        self._last_optimization_time: Optional[datetime] = None
        self._consecutive_failures = 0
        self._alerts_sent_today = 0
        self._alerts_date = datetime.now().date()

    def _init_components(self):
        """Initialize all system components."""
        logger.info("=" * 60)
        logger.info("Initializing GeneTrader Daemon")
        logger.info("=" * 60)

        # Freqtrade client
        try:
            self.client = FreqtradeClient(
                api_url=self.settings.api_url,
                username=self.settings.freqtrade_username,
                password=self.settings.freqtrade_password,
            )
            if self.client.ping():
                status = self.client.get_status()
                logger.info(f"✅ Connected to Freqtrade: {status.strategy} on {status.exchange}")
            else:
                raise ConnectionError("Ping failed")
        except Exception as e:
            logger.warning(f"⚠️ Freqtrade not available: {e}")
            logger.warning("   Running in offline mode (monitoring from database only)")
            self.client = None

        # Performance database
        db_path = getattr(self.settings, 'performance_db_path', 'data/performance.db')
        self.db = PerformanceDB(db_path)
        logger.info(f"✅ Performance database: {db_path}")

        # Performance monitor
        if self.client:
            self.monitor = PerformanceMonitor(
                client=self.client,
                db=self.db,
                snapshot_interval_minutes=self.check_interval // 60,
            )
        else:
            self.monitor = None

        # Degradation detector
        self.detector = DegradationDetector(
            profit_threshold=1 - getattr(self.settings, 'reoptimization_trigger_threshold', 0.3),
            drawdown_threshold=getattr(self.settings, 'max_drawdown_limit', 0.35),
        )
        logger.info("✅ Degradation detector initialized")

        # Version control
        self.version_control = StrategyVersionControl('data/strategy_versions')
        logger.info("✅ Version control initialized")

        # Deployer
        self.deployer = StrategyDeployer(
            version_control=self.version_control,
            freqtrade_client=self.client,
            target_strategy_dir=self.settings.strategy_dir,
        )

        # Rollback manager
        self.rollback_manager = RollbackManager(
            version_control=self.version_control,
            config=RollbackConfig(
                enabled=getattr(self.settings, 'auto_rollback_enabled', True),
                max_drawdown=getattr(self.settings, 'rollback_drawdown_threshold', 0.15),
                require_confirmation=getattr(self.settings, 'rollback_require_confirmation', False),
            )
        )
        logger.info("✅ Rollback manager initialized")

        # Scheduler
        self.scheduler = OptimizationScheduler(
            config=ScheduleConfig(
                min_interval_hours=self.optimize_interval // 3600,
                preferred_hours=[2, 3, 4, 5],  # Optimize during low-activity hours
            )
        )
        logger.info("✅ Scheduler initialized")

        # Adaptive optimizer
        self.adaptive = AdaptiveOptimizer(
            strategy_name=self.strategy_name,
            freqtrade_client=self.client,
            version_control=self.version_control,
            performance_db=self.db,
            config=AdaptiveConfig(
                check_interval_minutes=self.check_interval // 60,
                min_hours_between_optimizations=self.optimize_interval // 3600,
                require_approval=getattr(self.settings, 'agent_approval_required_for_deployment', False),
            ),
            strategy_deployer=self.deployer,
            rollback_manager=self.rollback_manager,
        )
        logger.info("✅ Adaptive optimizer initialized")

        # Agent API (optional)
        self.api = None
        if getattr(self.settings, 'agent_api_enabled', False):
            api_port = getattr(self.settings, 'agent_api_port', 8090)
            api_host = getattr(self.settings, 'agent_api_host', '127.0.0.1')
            api_key = getattr(self.settings, 'agent_api_key', '') or os.environ.get('AGENT_API_KEY', '')
            try:
                self.api = AgentAPI(
                    host=api_host,
                    port=api_port,
                    api_key=api_key,
                    performance_db=self.db,
                    version_control=self.version_control,
                    adaptive_optimizer=self.adaptive,
                    scheduler=self.scheduler,
                )
                logger.info(f"✅ Agent API will start on {api_host}:{api_port}")
            except ValueError as e:
                # A weak or missing master key must not silently expose the API.
                self.api = None
                logger.error(f"❌ Agent API disabled: {e}")

        logger.info("=" * 60)
        logger.info("Initialization complete")
        logger.info("=" * 60)

    def start(self):
        """Start the daemon."""
        self.running = True
        self._shutdown_event.clear()

        # Start Agent API if configured
        if self.api:
            self.api.start()

        # Start adaptive optimizer
        self.adaptive.start()

        # Send startup notification
        send_notification(
            self.settings,
            "🚀 GeneTrader Started",
            f"Monitoring strategy: {self.strategy_name}\nCheck interval: {self.check_interval}s"
        )

        logger.info(f"Daemon started for strategy: {self.strategy_name}")
        logger.info(f"Check interval: {self.check_interval} seconds")
        logger.info(f"Optimize interval: {self.optimize_interval} seconds")

    def stop(self):
        """Stop the daemon."""
        logger.info("Stopping daemon...")
        self.running = False
        self._shutdown_event.set()

        self.adaptive.stop()

        if self.api:
            self.api.stop()

        send_notification(
            self.settings,
            "🛑 GeneTrader Stopped",
            f"Daemon stopped for: {self.strategy_name}"
        )

        logger.info("Daemon stopped")

    def run(self):
        """Main daemon loop."""
        logger.info("Starting main loop...")

        while self.running:
            try:
                self._check_cycle()
            except Exception as e:
                logger.error(f"Error in check cycle: {e}")
                self._consecutive_failures += 1

                if self._consecutive_failures >= 5:
                    send_notification(
                        self.settings,
                        "⚠️ GeneTrader Errors",
                        f"5 consecutive failures: {str(e)[:100]}"
                    )
                    self._consecutive_failures = 0

            # Wait for next cycle
            self._shutdown_event.wait(timeout=self.check_interval)

            if self._shutdown_event.is_set():
                break

    def _check_cycle(self):
        """Perform one check cycle."""
        now = datetime.now()
        self._last_check_time = now

        logger.debug(f"Check cycle at {now.isoformat()}")

        # 1. Collect performance data
        if self.monitor:
            snapshot = self.monitor.collect_and_store()
            if snapshot:
                logger.info(f"Snapshot: {snapshot.total_trades} trades, "
                           f"profit: {snapshot.total_profit_pct:.2%}, "
                           f"win rate: {snapshot.win_rate:.2%}")

        # 2. Get recent snapshots for analysis
        snapshots = self.db.get_rolling_metrics(
            self.strategy_name,
            window_hours=getattr(self.settings, 'metrics_window_hours', 168)
        )

        if len(snapshots) < 3:
            logger.debug("Not enough data for analysis yet")
            return

        # 3. Detect degradation
        baseline = self.db.get_latest_baseline(self.strategy_name)
        result = self.detector.detect(snapshots, baseline)

        if result.is_degraded:
            self._handle_degradation(result)
        else:
            self._consecutive_failures = 0
            logger.debug(f"Strategy healthy: score={result.degradation_score:.2f}")

        # 4. Check adaptive optimizer state
        state = self.adaptive.check_and_act()

        if state == AdaptiveState.OPTIMIZING:
            logger.info("Optimization in progress...")

        # 5. Process scheduler queue
        task = self.scheduler.process_queue()
        if task:
            logger.info(f"Processed scheduled task: {task.id} - {task.status}")

        # 6. Check for rollback conditions
        if self.monitor:
            metrics = self.monitor.get_current_metrics()
            rollback = self.rollback_manager.check_and_rollback(self.strategy_name, metrics)
            if rollback:
                send_notification(
                    self.settings,
                    "🔙 Strategy Rolled Back",
                    f"Reason: {rollback.reason.value}\n"
                    f"From: {rollback.from_version} → {rollback.to_version}"
                )

    def _handle_degradation(self, result: DetectionResult):
        """Handle detected degradation."""
        logger.warning(f"⚠️ Degradation detected: score={result.degradation_score:.2f}")

        # Log alerts
        for alert in result.alerts:
            logger.warning(f"  Alert: {alert.alert_type.value} - {alert.message}")

        # Send notification (limit to 24 per day)
        today = datetime.now().date()
        if today != self._alerts_date:
            self._alerts_date = today
            self._alerts_sent_today = 0
        if self._alerts_sent_today < 24:
            send_notification(
                self.settings,
                f"⚠️ Strategy Degradation",
                f"Score: {result.degradation_score:.2f}\n"
                f"Alerts: {len(result.alerts)}\n"
                f"Regime: {result.market_regime.value}\n"
                f"Recommendation: {result.recommendation[:100]}"
            )
            self._alerts_sent_today += 1

        # Check if we should trigger optimization
        can_optimize = True

        if self._last_optimization_time:
            elapsed = (datetime.now() - self._last_optimization_time).total_seconds()
            if elapsed < self.optimize_interval:
                can_optimize = False
                logger.info(f"Skipping optimization: {elapsed/3600:.1f}h since last run")

        if can_optimize and result.degradation_score >= 0.5:
            logger.info("Scheduling re-optimization...")
            task = self.scheduler.schedule(
                self.strategy_name,
                f"degradation_score={result.degradation_score:.2f}",
                SchedulePriority.HIGH
            )

            if task:
                self._last_optimization_time = datetime.now()
                send_notification(
                    self.settings,
                    "🔧 Optimization Scheduled",
                    f"Strategy: {self.strategy_name}\n"
                    f"Scheduled: {task.scheduled_time.isoformat()}\n"
                    f"Reason: {task.trigger_reason}"
                )


def main():
    parser = argparse.ArgumentParser(
        description='GeneTrader Daemon - Continuous Adaptive Optimization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--config', type=str, default='ga.json',
                        help='Configuration file')
    parser.add_argument('--strategy', type=str, required=True,
                        help='Strategy name to monitor')
    parser.add_argument('--check-interval', type=int, default=300,
                        help='Check interval in seconds (default: 300)')
    parser.add_argument('--optimize-interval', type=int, default=86400,
                        help='Minimum interval between optimizations in seconds (default: 86400)')

    args = parser.parse_args()

    # Load settings
    try:
        settings = Settings(args.config)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    # Create daemon
    daemon = GeneTraderDaemon(
        settings=settings,
        strategy_name=args.strategy,
        check_interval=args.check_interval,
        optimize_interval=args.optimize_interval,
    )

    # Handle signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        daemon.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run
    daemon.start()
    daemon.run()


if __name__ == '__main__':
    main()
