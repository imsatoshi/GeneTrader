"""
Optimization scheduler for managing optimization timing and resources.

This module provides scheduling, rate limiting, and resource management
for the adaptive optimization system.
"""

import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from utils.time_utils import utc_now, to_utc, parse_utc
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from utils.logging_config import logger


class SchedulePriority(Enum):
    """Priority levels for scheduled optimizations."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ScheduleConfig:
    """Configuration for optimization scheduling."""
    # Rate limiting
    min_interval_hours: int = 24
    max_per_day: int = 2
    max_per_week: int = 5

    # Timing
    preferred_hours: List[int] = field(default_factory=lambda: [2, 3, 4])  # Early morning
    avoid_hours: List[int] = field(default_factory=lambda: [8, 9, 16, 17])  # Market opens
    timezone: str = "UTC"

    # Resource management
    max_concurrent: int = 1
    queue_size: int = 10

    # Timeout
    optimization_timeout_minutes: int = 120


@dataclass
class ScheduledOptimization:
    """Represents a scheduled optimization task."""
    id: str
    strategy_name: str
    scheduled_time: datetime
    priority: SchedulePriority
    trigger_reason: str
    status: str = "pending"  # pending, running, completed, failed, cancelled
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'strategy_name': self.strategy_name,
            'scheduled_time': self.scheduled_time.isoformat(),
            'priority': self.priority.value,
            'trigger_reason': self.trigger_reason,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class OptimizationScheduler:
    """
    Scheduler for optimization tasks.

    Features:
    - Rate limiting (per day, per week)
    - Priority-based queue
    - Preferred timing (avoid market hours)
    - Concurrent execution management
    - Persistence of scheduled tasks

    Usage:
        scheduler = OptimizationScheduler(config)
        scheduler.schedule("MyStrategy", "degradation_detected", SchedulePriority.HIGH)

        # In main loop:
        while True:
            scheduler.process_queue()
            time.sleep(60)
    """

    def __init__(
        self,
        config: Optional[ScheduleConfig] = None,
        state_file: str = "data/scheduler_state.json"
    ):
        """
        Initialize scheduler.

        Args:
            config: Scheduler configuration
            state_file: Path to state persistence file
        """
        self.config = config or ScheduleConfig()
        self.state_file = state_file

        self._queue: List[ScheduledOptimization] = []
        self._history: List[ScheduledOptimization] = []
        self._running: Dict[str, ScheduledOptimization] = {}
        self._lock = threading.Lock()

        # Callbacks
        self._optimization_func: Optional[Callable[[str], Dict[str, Any]]] = None
        self._on_complete_callback: Optional[Callable[[ScheduledOptimization], None]] = None

        self._load_state()

    def _load_state(self) -> None:
        """Load saved state from file."""
        if not os.path.exists(self.state_file):
            return

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            # Load pending tasks
            for task_data in data.get('queue', []):
                self._queue.append(ScheduledOptimization(
                    id=task_data['id'],
                    strategy_name=task_data['strategy_name'],
                    scheduled_time=parse_utc(task_data['scheduled_time']),
                    priority=SchedulePriority(task_data['priority']),
                    trigger_reason=task_data['trigger_reason'],
                    status=task_data['status'],
                    created_at=parse_utc(task_data['created_at']),
                ))

            # Load history
            for task_data in data.get('history', [])[-100:]:
                self._history.append(ScheduledOptimization(
                    id=task_data['id'],
                    strategy_name=task_data['strategy_name'],
                    scheduled_time=parse_utc(task_data['scheduled_time']),
                    priority=SchedulePriority(task_data['priority']),
                    trigger_reason=task_data['trigger_reason'],
                    status=task_data['status'],
                    created_at=parse_utc(task_data['created_at']),
                    started_at=parse_utc(task_data['started_at']),
                    completed_at=parse_utc(task_data['completed_at']),
                ))

        except Exception as e:
            logger.error(f"Error loading scheduler state: {e}")

    def _save_state(self) -> None:
        """Save state to file."""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

        data = {
            'queue': [t.to_dict() for t in self._queue],
            'history': [t.to_dict() for t in self._history[-100:]],
        }

        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)

    def set_optimization_func(
        self,
        func: Callable[[str], Dict[str, Any]]
    ) -> None:
        """
        Set the optimization function.

        Args:
            func: Function(strategy_name) -> result_dict
        """
        self._optimization_func = func

    def set_on_complete(
        self,
        callback: Callable[[ScheduledOptimization], None]
    ) -> None:
        """Set callback for task completion."""
        self._on_complete_callback = callback

    def _generate_id(self) -> str:
        """Generate unique task ID."""
        return f"opt_{utc_now().strftime('%Y%m%d_%H%M%S')}_{len(self._history)}"

    def _can_schedule(self, strategy_name: str) -> tuple[bool, str]:
        """
        Check if a new optimization can be scheduled.

        Returns:
            (can_schedule, reason)
        """
        now = utc_now()

        # Check daily limit
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = sum(
            1 for t in self._history
            if t.created_at >= today_start
        )

        if today_count >= self.config.max_per_day:
            return False, "Daily limit reached"

        # Check weekly limit
        week_ago = now - timedelta(days=7)
        week_count = sum(
            1 for t in self._history
            if t.created_at >= week_ago
        )

        if week_count >= self.config.max_per_week:
            return False, "Weekly limit reached"

        # Check minimum interval
        recent_for_strategy = [
            t for t in self._history
            if t.strategy_name == strategy_name and t.status == "completed"
        ]

        if recent_for_strategy:
            last_completed = max(t.completed_at for t in recent_for_strategy if t.completed_at)
            if last_completed:
                hours_since = (now - last_completed).total_seconds() / 3600
                if hours_since < self.config.min_interval_hours:
                    return False, f"Minimum interval not met ({hours_since:.1f}h < {self.config.min_interval_hours}h)"

        # Check queue size
        if len(self._queue) >= self.config.queue_size:
            return False, "Queue is full"

        # Check if already queued
        if any(t.strategy_name == strategy_name and t.status == "pending" for t in self._queue):
            return False, "Already queued"

        return True, "OK"

    def _calculate_schedule_time(
        self,
        priority: SchedulePriority
    ) -> datetime:
        """Calculate when to schedule based on priority and timing preferences."""
        now = utc_now()

        if priority == SchedulePriority.CRITICAL:
            # Run immediately
            return now

        if priority == SchedulePriority.HIGH:
            # Run within the hour
            return now + timedelta(minutes=15)

        # For normal/low priority, try to schedule during preferred hours
        target = now

        # If current hour is not preferred, find next preferred hour
        if now.hour not in self.config.preferred_hours:
            for hours_ahead in range(1, 25):
                candidate = now + timedelta(hours=hours_ahead)
                if candidate.hour in self.config.preferred_hours:
                    target = candidate.replace(minute=0, second=0, microsecond=0)
                    break

        # Avoid certain hours
        while target.hour in self.config.avoid_hours:
            target += timedelta(hours=1)

        return target

    def schedule(
        self,
        strategy_name: str,
        trigger_reason: str,
        priority: SchedulePriority = SchedulePriority.NORMAL,
        force: bool = False
    ) -> Optional[ScheduledOptimization]:
        """
        Schedule an optimization.

        Args:
            strategy_name: Strategy to optimize
            trigger_reason: Why optimization is being triggered
            priority: Priority level
            force: Bypass rate limiting

        Returns:
            ScheduledOptimization if scheduled, None if rejected
        """
        with self._lock:
            # Check if we can schedule
            if not force:
                can_schedule, reason = self._can_schedule(strategy_name)
                if not can_schedule:
                    logger.info(f"Cannot schedule optimization for {strategy_name}: {reason}")
                    return None

            # Create task
            scheduled_time = self._calculate_schedule_time(priority)

            task = ScheduledOptimization(
                id=self._generate_id(),
                strategy_name=strategy_name,
                scheduled_time=scheduled_time,
                priority=priority,
                trigger_reason=trigger_reason,
            )

            # Add to queue
            self._queue.append(task)

            # Sort by priority (higher first) then by scheduled time
            self._queue.sort(key=lambda t: (-t.priority.value, t.scheduled_time))

            self._save_state()

            logger.info(f"Scheduled optimization for {strategy_name} at {scheduled_time}")
            return task

    def process_queue(self) -> Optional[ScheduledOptimization]:
        """
        Process the next task in the queue if ready.

        Returns:
            The processed task, or None
        """
        with self._lock:
            if not self._queue:
                return None

            # Check concurrent limit
            if len(self._running) >= self.config.max_concurrent:
                return None

            now = utc_now()

            # Find next ready task
            ready_task = None
            for task in self._queue:
                if task.scheduled_time <= now:
                    ready_task = task
                    break

            if not ready_task:
                return None

            # Remove from queue
            self._queue.remove(ready_task)

            # Start execution
            ready_task.status = "running"
            ready_task.started_at = now
            self._running[ready_task.id] = ready_task

        # Execute outside lock
        try:
            result = self._execute_task(ready_task)
            ready_task.status = "completed"
            ready_task.result = result
        except Exception as e:
            logger.error(f"Optimization failed for {ready_task.strategy_name}: {e}")
            ready_task.status = "failed"
            ready_task.result = {'error': str(e)}

        # Cleanup
        with self._lock:
            ready_task.completed_at = utc_now()
            del self._running[ready_task.id]
            self._history.append(ready_task)
            self._save_state()

        # Callback
        if self._on_complete_callback:
            self._on_complete_callback(ready_task)

        return ready_task

    def _execute_task(self, task: ScheduledOptimization) -> Dict[str, Any]:
        """Execute an optimization task."""
        logger.info(f"Starting optimization for {task.strategy_name}")

        if not self._optimization_func:
            logger.warning("No optimization function set")
            return {'success': False, 'error': 'No optimization function'}

        result = self._optimization_func(task.strategy_name)

        logger.info(f"Completed optimization for {task.strategy_name}")
        return result

    def cancel(self, task_id: str) -> bool:
        """
        Cancel a scheduled optimization.

        Args:
            task_id: ID of task to cancel

        Returns:
            True if cancelled
        """
        with self._lock:
            for task in self._queue:
                if task.id == task_id:
                    task.status = "cancelled"
                    self._queue.remove(task)
                    self._history.append(task)
                    self._save_state()
                    logger.info(f"Cancelled optimization {task_id}")
                    return True

        return False

    def get_queue(self) -> List[Dict[str, Any]]:
        """Get current queue."""
        with self._lock:
            return [t.to_dict() for t in self._queue]

    def get_running(self) -> List[Dict[str, Any]]:
        """Get currently running tasks."""
        with self._lock:
            return [t.to_dict() for t in self._running.values()]

    def get_history(
        self,
        strategy_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get task history."""
        with self._lock:
            history = self._history

            if strategy_name:
                history = [t for t in history if t.strategy_name == strategy_name]

            return [t.to_dict() for t in history[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        now = utc_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        with self._lock:
            return {
                'queue_size': len(self._queue),
                'running': len(self._running),
                'completed_today': sum(
                    1 for t in self._history
                    if t.completed_at and t.completed_at >= today_start and t.status == "completed"
                ),
                'completed_this_week': sum(
                    1 for t in self._history
                    if t.completed_at and t.completed_at >= week_ago and t.status == "completed"
                ),
                'failed_this_week': sum(
                    1 for t in self._history
                    if t.completed_at and t.completed_at >= week_ago and t.status == "failed"
                ),
                'daily_limit': self.config.max_per_day,
                'weekly_limit': self.config.max_per_week,
            }

    def clear_queue(self) -> int:
        """Clear all pending tasks."""
        with self._lock:
            count = len(self._queue)
            for task in self._queue:
                task.status = "cancelled"
                self._history.append(task)
            self._queue.clear()
            self._save_state()
            return count
