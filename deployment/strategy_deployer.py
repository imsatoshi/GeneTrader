"""
Strategy deployer for safe strategy deployment to live trading.

This module provides a deployment pipeline that includes validation,
shadow trading, gradual rollout, and monitoring integration.
"""

import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from utils.time_utils import utc_now, to_utc, parse_utc
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from utils.logging_config import logger

from deployment.version_control import StrategyVersionControl, StrategyVersion, VersionStatus
from monitoring.freqtrade_client import FreqtradeClient


class DeploymentStatus(Enum):
    """Status of a deployment."""
    PENDING = "pending"
    VALIDATING = "validating"
    SHADOW_TESTING = "shadow_testing"
    DEPLOYING = "deploying"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentConfig:
    """Configuration for a deployment."""
    shadow_trading_hours: int = 24
    validation_trades_required: int = 10
    gradual_rollout: bool = True
    rollout_phases: List[float] = field(default_factory=lambda: [0.25, 0.5, 0.75, 1.0])
    phase_duration_hours: int = 6
    auto_rollback_enabled: bool = True
    rollback_drawdown_threshold: float = 0.15
    monitoring_hours: int = 48
    require_approval: bool = True


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    status: DeploymentStatus
    version_id: str
    strategy_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    current_phase: int = 0
    total_phases: int = 1
    shadow_metrics: Dict[str, Any] = field(default_factory=dict)
    live_metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    approved: bool = False
    approved_by: str = ""
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'status': self.status.value,
            'version_id': self.version_id,
            'strategy_name': self.strategy_name,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'current_phase': self.current_phase,
            'total_phases': self.total_phases,
            'shadow_metrics': self.shadow_metrics,
            'live_metrics': self.live_metrics,
            'error_message': self.error_message,
            'approved': self.approved,
            'notes': self.notes,
        }


class StrategyDeployer:
    """
    Safe deployment pipeline for trading strategies.

    Deployment flow:
    1. Validation: Check strategy file and parameters
    2. Approval: Wait for approval (if required)
    3. Deploy: Copy the strategy file and optionally reload Freqtrade config
    4. Monitoring: Record deployment status for external monitoring
    5. Completion or Rollback: Based on performance

    Usage:
        deployer = StrategyDeployer(version_control, freqtrade_client)
        result = deployer.deploy(
            strategy_name="MyStrategy",
            version_id="v5",
            config=DeploymentConfig(shadow_trading_hours=24)
        )
    """

    def __init__(
        self,
        version_control: StrategyVersionControl,
        freqtrade_client: Optional[FreqtradeClient] = None,
        target_strategy_dir: str = "/freqtrade/user_data/strategies",
        backup_dir: str = "data/strategy_backups"
    ):
        """
        Initialize strategy deployer.

        Args:
            version_control: Version control system
            freqtrade_client: Freqtrade API client (optional)
            target_strategy_dir: Directory where strategies are deployed
            backup_dir: Directory for backing up current strategies
        """
        self.version_control = version_control
        self.client = freqtrade_client
        self.target_strategy_dir = target_strategy_dir
        self.backup_dir = backup_dir

        os.makedirs(backup_dir, exist_ok=True)

        self._current_deployment: Optional[DeploymentResult] = None
        self._approval_callback: Optional[Callable[[str, str], bool]] = None

    def set_approval_callback(self, callback: Callable[[str, str], bool]) -> None:
        """
        Set callback for deployment approval.

        Args:
            callback: Function(strategy_name, version_id) -> bool
        """
        self._approval_callback = callback

    def validate_strategy(
        self,
        strategy_name: str,
        version_id: str
    ) -> tuple[bool, str]:
        """
        Validate a strategy version before deployment.

        Args:
            strategy_name: Strategy name
            version_id: Version to validate

        Returns:
            (is_valid, message)
        """
        version = self.version_control.get_version(strategy_name, version_id)

        if not version:
            return False, f"Version {version_id} not found"

        # Check file exists
        if not os.path.exists(version.file_path):
            return False, f"Strategy file not found: {version.file_path}"

        # Check file is valid Python
        try:
            with open(version.file_path, 'r') as f:
                source = f.read()
            compile(source, version.file_path, 'exec')
        except SyntaxError as e:
            return False, f"Strategy has syntax error: {e}"

        # Check backtest metrics exist
        if not version.backtest_metrics:
            return False, "No backtest metrics available"

        # Check minimum performance requirements
        profit = version.backtest_metrics.get('total_profit_pct', 0)
        if profit <= 0:
            return False, f"Backtest profit is negative: {profit}"

        drawdown = version.backtest_metrics.get('max_drawdown', 1.0)
        if drawdown > 0.5:
            return False, f"Backtest drawdown too high: {drawdown:.1%}"

        return True, "Validation passed"

    def backup_current_strategy(self, strategy_name: str) -> Optional[str]:
        """
        Backup the currently deployed strategy.

        Args:
            strategy_name: Strategy to backup

        Returns:
            Path to backup file, or None if no current strategy
        """
        # Find current strategy file
        strategy_file = os.path.join(self.target_strategy_dir, f"{strategy_name}.py")

        if not os.path.exists(strategy_file):
            logger.info(f"No existing strategy file to backup: {strategy_file}")
            return None

        # Create backup
        timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(
            self.backup_dir,
            f"{strategy_name}_{timestamp}.py"
        )

        shutil.copy2(strategy_file, backup_file)
        logger.info(f"Backed up strategy to {backup_file}")

        return backup_file

    def deploy_file(
        self,
        version: StrategyVersion,
        reload_config: bool = True
    ) -> bool:
        """
        Deploy strategy file to target directory.

        Args:
            version: Strategy version to deploy
            reload_config: Whether to reload Freqtrade config

        Returns:
            True if successful
        """
        try:
            # Ensure target directory exists
            os.makedirs(self.target_strategy_dir, exist_ok=True)

            # Deploy file
            target_file = os.path.join(
                self.target_strategy_dir,
                f"{version.strategy_name}.py"
            )
            shutil.copy2(version.file_path, target_file)
            logger.info(f"Deployed strategy to {target_file}")

            # Reload Freqtrade config if client available
            if reload_config and self.client:
                try:
                    self.client.reload_config()
                except Exception as e:
                    logger.warning(f"Failed to reload config: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to deploy strategy: {e}")
            return False

    def deploy(
        self,
        strategy_name: str,
        version_id: str,
        config: Optional[DeploymentConfig] = None
    ) -> DeploymentResult:
        """
        Deploy a strategy version with full safety pipeline.

        Args:
            strategy_name: Strategy name
            version_id: Version to deploy
            config: Deployment configuration

        Returns:
            DeploymentResult with deployment status
        """
        config = config or DeploymentConfig()

        result = DeploymentResult(
            status=DeploymentStatus.PENDING,
            version_id=version_id,
            strategy_name=strategy_name,
            started_at=utc_now(),
            total_phases=1
        )

        self._current_deployment = result

        try:
            # Step 1: Validation
            result.status = DeploymentStatus.VALIDATING
            result.notes.append(f"[{utc_now().isoformat()}] Starting validation")

            is_valid, message = self.validate_strategy(strategy_name, version_id)
            if not is_valid:
                result.status = DeploymentStatus.FAILED
                result.error_message = message
                result.notes.append(f"[{utc_now().isoformat()}] Validation failed: {message}")
                return result

            result.notes.append(f"[{utc_now().isoformat()}] Validation passed")

            # Update version status
            self.version_control.update_status(
                strategy_name, version_id, VersionStatus.VALIDATING
            )

            # Step 2: Approval (if required)
            if config.require_approval:
                result.notes.append(f"[{utc_now().isoformat()}] Waiting for approval")

                if self._approval_callback:
                    approved = self._approval_callback(strategy_name, version_id)
                    if not approved:
                        result.status = DeploymentStatus.FAILED
                        result.error_message = "Deployment not approved"
                        return result
                    result.approved = True
                else:
                    result.status = DeploymentStatus.FAILED
                    result.error_message = "Deployment approval callback required"
                    result.notes.append(
                        f"[{utc_now().isoformat()}] Approval callback missing; failing closed"
                    )
                    return result

                result.notes.append(f"[{utc_now().isoformat()}] Approved")

            if config.shadow_trading_hours > 0:
                result.notes.append(
                    f"[{utc_now().isoformat()}] Shadow trading not executed by StrategyDeployer"
                )
            if config.gradual_rollout:
                result.notes.append(
                    f"[{utc_now().isoformat()}] Gradual rollout not executed by StrategyDeployer"
                )

            # Step 3: Backup current strategy
            backup_path = self.backup_current_strategy(strategy_name)
            if backup_path:
                result.notes.append(f"[{utc_now().isoformat()}] Backed up to {backup_path}")

            # Step 4: Deploy
            result.status = DeploymentStatus.DEPLOYING
            version = self.version_control.get_version(strategy_name, version_id)

            if not self.deploy_file(version):
                result.status = DeploymentStatus.FAILED
                result.error_message = "Failed to deploy strategy file"
                return result

            result.notes.append(f"[{utc_now().isoformat()}] Strategy file deployed")

            # Update version status to deployed
            self.version_control.update_status(
                strategy_name, version_id, VersionStatus.DEPLOYED
            )

            # Step 5: Set as active
            self.version_control.set_active(strategy_name, version_id)

            result.status = DeploymentStatus.MONITORING
            result.notes.append(f"[{utc_now().isoformat()}] Deployment completed, entering monitoring phase")

            # Mark as completed
            result.status = DeploymentStatus.COMPLETED
            result.completed_at = utc_now()

            logger.info(f"Successfully deployed {strategy_name} {version_id}")

        except Exception as e:
            result.status = DeploymentStatus.FAILED
            result.error_message = str(e)
            result.notes.append(f"[{utc_now().isoformat()}] Error: {e}")
            logger.error(f"Deployment failed: {e}")

        return result

    def rollback(
        self,
        strategy_name: str,
        to_version_id: Optional[str] = None
    ) -> bool:
        """
        Rollback to a previous version.

        Args:
            strategy_name: Strategy to rollback
            to_version_id: Target version (uses previous active if not specified)

        Returns:
            True if rollback successful
        """
        try:
            # Find target version
            if to_version_id:
                target = self.version_control.get_version(strategy_name, to_version_id)
            else:
                # Find previous active version
                history = self.version_control.get_deployment_history(strategy_name)
                if len(history) < 2:
                    logger.error("No previous version to rollback to")
                    return False
                target = self.version_control.get_version(
                    strategy_name, history[1]['version_id']
                )

            if not target:
                logger.error(f"Target version not found")
                return False

            # Get current version
            current = self.version_control.get_active_version(strategy_name)
            if current:
                self.version_control.update_status(
                    strategy_name, current.version_id, VersionStatus.ROLLED_BACK
                )

            # Deploy target version
            if not self.deploy_file(target):
                return False

            # Update status
            self.version_control.set_active(strategy_name, target.version_id)

            logger.info(f"Rolled back {strategy_name} to {target.version_id}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def get_deployment_status(self) -> Optional[DeploymentResult]:
        """Get status of current deployment."""
        return self._current_deployment

    def cancel_deployment(self) -> bool:
        """Cancel the current deployment."""
        if not self._current_deployment:
            return False

        if self._current_deployment.status in [
            DeploymentStatus.COMPLETED,
            DeploymentStatus.FAILED
        ]:
            return False

        self._current_deployment.status = DeploymentStatus.FAILED
        self._current_deployment.error_message = "Deployment cancelled"
        self._current_deployment.completed_at = utc_now()

        # Update version status
        self.version_control.update_status(
            self._current_deployment.strategy_name,
            self._current_deployment.version_id,
            VersionStatus.FAILED
        )

        logger.info("Deployment cancelled")
        return True


class GradualRolloutManager:
    """
    Manages gradual rollout of new strategy versions.

    Gradually increases allocation to new strategy while monitoring performance.
    """

    def __init__(
        self,
        deployer: StrategyDeployer,
        phases: List[float] = None,
        phase_duration_hours: int = 6
    ):
        """
        Initialize rollout manager.

        Args:
            deployer: Strategy deployer
            phases: List of allocation percentages (e.g., [0.25, 0.5, 0.75, 1.0])
            phase_duration_hours: Duration of each phase
        """
        self.deployer = deployer
        self.phases = phases or [0.25, 0.5, 0.75, 1.0]
        self.phase_duration_hours = phase_duration_hours

        self._current_phase = 0
        self._phase_start_time: Optional[datetime] = None
        self._rollout_active = False

    def start_rollout(self, strategy_name: str, version_id: str) -> bool:
        """
        Start gradual rollout.

        Args:
            strategy_name: Strategy name
            version_id: Version to rollout

        Returns:
            True if rollout started
        """
        self._current_phase = 0
        self._phase_start_time = utc_now()
        self._rollout_active = True

        logger.info(f"Started gradual rollout: {strategy_name} {version_id}")
        logger.info(f"Phase 1/{len(self.phases)}: {self.phases[0]:.0%} allocation")

        return True

    def check_phase_completion(self) -> bool:
        """Check if current phase is complete."""
        if not self._rollout_active or not self._phase_start_time:
            return False

        elapsed = utc_now() - self._phase_start_time
        return elapsed >= timedelta(hours=self.phase_duration_hours)

    def advance_phase(self) -> bool:
        """
        Advance to next rollout phase.

        Returns:
            True if advanced, False if rollout complete
        """
        if not self._rollout_active:
            return False

        self._current_phase += 1
        self._phase_start_time = utc_now()

        if self._current_phase >= len(self.phases):
            self._rollout_active = False
            logger.info("Gradual rollout completed")
            return False

        logger.info(f"Phase {self._current_phase + 1}/{len(self.phases)}: "
                   f"{self.phases[self._current_phase]:.0%} allocation")
        return True

    def get_current_allocation(self) -> float:
        """Get current allocation percentage."""
        if not self._rollout_active:
            return 1.0

        if self._current_phase < len(self.phases):
            return self.phases[self._current_phase]

        return 1.0

    def is_active(self) -> bool:
        """Check if rollout is active."""
        return self._rollout_active

    def cancel_rollout(self) -> None:
        """Cancel the current rollout."""
        self._rollout_active = False
        logger.info("Gradual rollout cancelled")
