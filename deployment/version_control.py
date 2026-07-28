"""
Strategy version control for managing strategy deployments.

This module provides version tracking, rollback capability, and
deployment history for trading strategies.
"""

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from utils.time_utils import utc_now, to_utc, parse_utc
from enum import Enum
from typing import Any, Dict, List, Optional
from utils.logging_config import logger


class VersionStatus(Enum):
    """Status of a strategy version."""
    CREATED = "created"
    SHADOW_TESTING = "shadow_testing"
    VALIDATING = "validating"
    DEPLOYED = "deployed"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"
    DEPRECATED = "deprecated"
    FAILED = "failed"


@dataclass
class StrategyVersion:
    """Represents a single version of a strategy."""
    version_id: str
    strategy_name: str
    created_at: datetime
    status: VersionStatus
    file_path: str
    file_hash: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    backtest_metrics: Dict[str, Any] = field(default_factory=dict)
    live_metrics: Dict[str, Any] = field(default_factory=dict)
    parent_version: Optional[str] = None
    notes: str = ""
    deployed_at: Optional[datetime] = None
    deactivated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d['created_at'] = self.created_at.isoformat()
        d['status'] = self.status.value
        if self.deployed_at:
            d['deployed_at'] = self.deployed_at.isoformat()
        if self.deactivated_at:
            d['deactivated_at'] = self.deactivated_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyVersion':
        """Create from dictionary."""
        data = data.copy()
        data['created_at'] = parse_utc(data['created_at'])
        data['status'] = VersionStatus(data['status'])
        if data.get('deployed_at'):
            data['deployed_at'] = parse_utc(data['deployed_at'])
        if data.get('deactivated_at'):
            data['deactivated_at'] = parse_utc(data['deactivated_at'])
        return cls(**data)


class StrategyVersionControl:
    """
    Version control system for trading strategies.

    Manages strategy versions, tracks deployment history, and provides
    rollback capability. Stores strategies and metadata in a structured
    directory.

    Directory structure:
    versions_dir/
      strategy_name/
        versions.json        # Version metadata
        v1/
          strategy.py       # Strategy file
          parameters.json   # Parameters
          metrics.json      # Backtest metrics
        v2/
          ...
    """

    def __init__(self, versions_dir: str = "data/strategy_versions"):
        """
        Initialize version control.

        Args:
            versions_dir: Directory for storing strategy versions
        """
        self.versions_dir = versions_dir
        os.makedirs(versions_dir, exist_ok=True)

    def _get_strategy_dir(self, strategy_name: str) -> str:
        """Get directory for a strategy."""
        return os.path.join(self.versions_dir, strategy_name)

    def _get_version_dir(self, strategy_name: str, version_id: str) -> str:
        """Get directory for a specific version."""
        return os.path.join(self._get_strategy_dir(strategy_name), version_id)

    def _get_versions_file(self, strategy_name: str) -> str:
        """Get path to versions metadata file."""
        return os.path.join(self._get_strategy_dir(strategy_name), "versions.json")

    def _load_versions(self, strategy_name: str) -> List[StrategyVersion]:
        """Load all versions for a strategy."""
        versions_file = self._get_versions_file(strategy_name)
        if not os.path.exists(versions_file):
            return []

        try:
            with open(versions_file, 'r') as f:
                data = json.load(f)
            return [StrategyVersion.from_dict(v) for v in data.get('versions', [])]
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading versions for {strategy_name}: {e}")
            return []

    def _save_versions(self, strategy_name: str, versions: List[StrategyVersion]) -> None:
        """Save versions metadata."""
        versions_file = self._get_versions_file(strategy_name)
        os.makedirs(os.path.dirname(versions_file), exist_ok=True)

        data = {
            'strategy_name': strategy_name,
            'versions': [v.to_dict() for v in versions]
        }

        with open(versions_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _generate_version_id(self, strategy_name: str) -> str:
        """Generate a new version ID."""
        versions = self._load_versions(strategy_name)
        if not versions:
            return "v1"

        # Find highest version number
        max_num = 0
        for v in versions:
            if v.version_id.startswith('v'):
                try:
                    num = int(v.version_id[1:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass

        return f"v{max_num + 1}"

    def create_version(
        self,
        strategy_name: str,
        source_file: str,
        parameters: Optional[Dict[str, Any]] = None,
        backtest_metrics: Optional[Dict[str, Any]] = None,
        parent_version: Optional[str] = None,
        notes: str = ""
    ) -> StrategyVersion:
        """
        Create a new version of a strategy.

        Args:
            strategy_name: Name of the strategy
            source_file: Path to the strategy source file
            parameters: Strategy parameters
            backtest_metrics: Backtest performance metrics
            parent_version: ID of the parent version (if evolving)
            notes: Version notes

        Returns:
            Created StrategyVersion
        """
        if not os.path.exists(source_file):
            raise FileNotFoundError(f"Source file not found: {source_file}")

        # Generate version ID
        version_id = self._generate_version_id(strategy_name)

        # Create version directory
        version_dir = self._get_version_dir(strategy_name, version_id)
        os.makedirs(version_dir, exist_ok=True)

        # Copy strategy file
        dest_file = os.path.join(version_dir, "strategy.py")
        shutil.copy2(source_file, dest_file)

        # Calculate file hash
        file_hash = self._calculate_file_hash(dest_file)

        # Save parameters
        if parameters:
            params_file = os.path.join(version_dir, "parameters.json")
            with open(params_file, 'w') as f:
                json.dump(parameters, f, indent=2)

        # Save backtest metrics
        if backtest_metrics:
            metrics_file = os.path.join(version_dir, "metrics.json")
            with open(metrics_file, 'w') as f:
                json.dump(backtest_metrics, f, indent=2)

        # Create version object
        version = StrategyVersion(
            version_id=version_id,
            strategy_name=strategy_name,
            created_at=utc_now(),
            status=VersionStatus.CREATED,
            file_path=dest_file,
            file_hash=file_hash,
            parameters=parameters or {},
            backtest_metrics=backtest_metrics or {},
            parent_version=parent_version,
            notes=notes
        )

        # Save to versions list
        versions = self._load_versions(strategy_name)
        versions.append(version)
        self._save_versions(strategy_name, versions)

        logger.info(f"Created version {version_id} for strategy {strategy_name}")
        return version

    def get_version(self, strategy_name: str, version_id: str) -> Optional[StrategyVersion]:
        """Get a specific version."""
        versions = self._load_versions(strategy_name)
        for v in versions:
            if v.version_id == version_id:
                return v
        return None

    def get_all_versions(self, strategy_name: str) -> List[StrategyVersion]:
        """Get all versions of a strategy."""
        return self._load_versions(strategy_name)

    def get_active_version(self, strategy_name: str) -> Optional[StrategyVersion]:
        """Get the currently active version."""
        versions = self._load_versions(strategy_name)
        for v in versions:
            if v.status == VersionStatus.ACTIVE:
                return v
        return None

    def get_latest_version(self, strategy_name: str) -> Optional[StrategyVersion]:
        """Get the most recently created version."""
        versions = self._load_versions(strategy_name)
        if not versions:
            return None
        return max(versions, key=lambda v: v.created_at)

    def update_status(
        self,
        strategy_name: str,
        version_id: str,
        status: VersionStatus
    ) -> bool:
        """
        Update the status of a version.

        Args:
            strategy_name: Strategy name
            version_id: Version ID
            status: New status

        Returns:
            True if successful
        """
        versions = self._load_versions(strategy_name)

        for v in versions:
            if v.version_id == version_id:
                old_status = v.status
                v.status = status

                # Track deployment/deactivation times
                if status == VersionStatus.DEPLOYED or status == VersionStatus.ACTIVE:
                    v.deployed_at = utc_now()
                elif status in [VersionStatus.ROLLED_BACK, VersionStatus.DEPRECATED]:
                    v.deactivated_at = utc_now()

                self._save_versions(strategy_name, versions)
                logger.info(f"Updated {strategy_name} {version_id}: {old_status.value} -> {status.value}")
                return True

        return False

    def set_active(self, strategy_name: str, version_id: str) -> bool:
        """
        Set a version as the active version.

        Deactivates any currently active version.

        Args:
            strategy_name: Strategy name
            version_id: Version to activate

        Returns:
            True if successful
        """
        versions = self._load_versions(strategy_name)

        # Find target version
        target = None
        for v in versions:
            if v.version_id == version_id:
                target = v
                break

        if not target:
            logger.error(f"Version {version_id} not found for {strategy_name}")
            return False

        # Deactivate current active version
        for v in versions:
            if v.status == VersionStatus.ACTIVE and v.version_id != version_id:
                v.status = VersionStatus.DEPLOYED
                v.deactivated_at = utc_now()

        # Activate target
        target.status = VersionStatus.ACTIVE
        target.deployed_at = utc_now()

        self._save_versions(strategy_name, versions)
        logger.info(f"Set {strategy_name} {version_id} as active")
        return True

    def update_live_metrics(
        self,
        strategy_name: str,
        version_id: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """
        Update live trading metrics for a version.

        Args:
            strategy_name: Strategy name
            version_id: Version ID
            metrics: Live trading metrics

        Returns:
            True if successful
        """
        versions = self._load_versions(strategy_name)

        for v in versions:
            if v.version_id == version_id:
                v.live_metrics = metrics
                self._save_versions(strategy_name, versions)
                return True

        return False

    def get_deployment_history(self, strategy_name: str) -> List[Dict[str, Any]]:
        """
        Get deployment history for a strategy.

        Returns:
            List of deployment events with timestamps
        """
        versions = self._load_versions(strategy_name)
        history = []

        for v in versions:
            if v.deployed_at:
                history.append({
                    'version_id': v.version_id,
                    'deployed_at': v.deployed_at.isoformat(),
                    'status': v.status.value,
                    'deactivated_at': v.deactivated_at.isoformat() if v.deactivated_at else None,
                    'backtest_profit': v.backtest_metrics.get('total_profit_pct'),
                    'live_profit': v.live_metrics.get('total_profit_pct'),
                })

        # Sort by deployment time
        history.sort(key=lambda x: x['deployed_at'], reverse=True)
        return history

    def compare_versions(
        self,
        strategy_name: str,
        version_id_1: str,
        version_id_2: str
    ) -> Dict[str, Any]:
        """
        Compare two versions of a strategy.

        Returns:
            Comparison of backtest and live metrics
        """
        v1 = self.get_version(strategy_name, version_id_1)
        v2 = self.get_version(strategy_name, version_id_2)

        if not v1 or not v2:
            return {'error': 'Version not found'}

        def compare_metrics(m1: Dict, m2: Dict) -> Dict[str, Any]:
            """Compare two metric dictionaries."""
            result = {}
            all_keys = set(m1.keys()) | set(m2.keys())
            for key in all_keys:
                val1 = m1.get(key)
                val2 = m2.get(key)
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    result[key] = {
                        'v1': val1,
                        'v2': val2,
                        'diff': val2 - val1,
                        'pct_change': ((val2 - val1) / val1 * 100) if val1 else 0
                    }
            return result

        return {
            'version_1': version_id_1,
            'version_2': version_id_2,
            'backtest_comparison': compare_metrics(v1.backtest_metrics, v2.backtest_metrics),
            'live_comparison': compare_metrics(v1.live_metrics, v2.live_metrics),
        }

    def get_version_file(self, strategy_name: str, version_id: str) -> Optional[str]:
        """Get path to the strategy file for a version."""
        version = self.get_version(strategy_name, version_id)
        if version and os.path.exists(version.file_path):
            return version.file_path
        return None

    def cleanup_old_versions(
        self,
        strategy_name: str,
        keep_count: int = 10,
        keep_active: bool = True
    ) -> int:
        """
        Clean up old versions, keeping the most recent ones.

        Args:
            strategy_name: Strategy name
            keep_count: Number of versions to keep
            keep_active: Whether to always keep active/deployed versions

        Returns:
            Number of versions deleted
        """
        versions = self._load_versions(strategy_name)

        if len(versions) <= keep_count:
            return 0

        # Sort by creation time (oldest first)
        versions.sort(key=lambda v: v.created_at)

        # Identify versions to delete
        to_delete = []
        protected_statuses = {VersionStatus.ACTIVE, VersionStatus.DEPLOYED}

        for v in versions[:-keep_count]:
            if keep_active and v.status in protected_statuses:
                continue
            to_delete.append(v)

        # Delete versions
        for v in to_delete:
            version_dir = self._get_version_dir(strategy_name, v.version_id)
            if os.path.exists(version_dir):
                shutil.rmtree(version_dir)
            versions.remove(v)
            logger.info(f"Deleted old version {v.version_id} of {strategy_name}")

        self._save_versions(strategy_name, versions)
        return len(to_delete)

    def list_strategies(self) -> List[str]:
        """List all strategies with versions."""
        if not os.path.exists(self.versions_dir):
            return []

        strategies = []
        for name in os.listdir(self.versions_dir):
            path = os.path.join(self.versions_dir, name)
            if os.path.isdir(path) and os.path.exists(os.path.join(path, "versions.json")):
                strategies.append(name)

        return strategies
