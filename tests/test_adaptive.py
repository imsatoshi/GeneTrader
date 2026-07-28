"""Unit tests for adaptive optimization module."""

import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from utils.time_utils import utc_now
from unittest.mock import MagicMock, patch

from adaptive.weighted_optimizer import (
    WeightedDataOptimizer, TimePeriod, OptimizationResult, AdaptiveFitnessFunction
)
from adaptive.adaptive_optimizer import (
    AdaptiveOptimizer, AdaptiveConfig, AdaptiveState
)
from adaptive.scheduler import (
    OptimizationScheduler, ScheduleConfig, SchedulePriority, ScheduledOptimization
)


class TestTimePeriod(unittest.TestCase):
    """Tests for TimePeriod dataclass."""

    def test_days_property(self):
        """Test days calculation."""
        period = TimePeriod(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            weight=1.0
        )

        self.assertEqual(period.days, 30)


class TestWeightedDataOptimizer(unittest.TestCase):
    """Tests for WeightedDataOptimizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.optimizer = WeightedDataOptimizer(
            recent_weight=0.7,
            historical_weight=0.3,
            recent_period_days=30,
            weighting_scheme="step"
        )

    def test_create_step_periods(self):
        """Test step weighting scheme."""
        periods = self.optimizer.create_time_periods(90)

        self.assertEqual(len(periods), 2)
        self.assertEqual(periods[0].name, "historical")
        self.assertEqual(periods[0].weight, 0.3)
        self.assertEqual(periods[1].name, "recent")
        self.assertEqual(periods[1].weight, 0.7)

    def test_create_linear_periods(self):
        """Test linear weighting scheme."""
        optimizer = WeightedDataOptimizer(weighting_scheme="linear")
        periods = optimizer.create_time_periods(120)

        self.assertEqual(len(periods), 4)
        # Weights should increase
        weights = [p.weight for p in periods]
        self.assertEqual(weights, sorted(weights))

    def test_create_exponential_periods(self):
        """Test exponential weighting scheme."""
        optimizer = WeightedDataOptimizer(
            weighting_scheme="exponential",
            decay_half_life_days=30
        )
        periods = optimizer.create_time_periods(120)

        self.assertEqual(len(periods), 4)
        # Most recent period should have highest weight
        self.assertEqual(max(periods, key=lambda p: p.weight), periods[-1])

    def test_calculate_weighted_fitness(self):
        """Test weighted fitness calculation."""
        # Set fitness function
        self.optimizer.set_fitness_function(
            lambda params, period: params.get('score', 0.0)
        )

        periods = self.optimizer.create_time_periods(90)

        weighted_score, period_scores = self.optimizer.calculate_weighted_fitness(
            {'score': 1.0},
            periods
        )

        # With both periods returning 1.0, weighted average should be 1.0
        self.assertEqual(weighted_score, 1.0)
        self.assertEqual(len(period_scores), 2)


class TestAdaptiveFitnessFunction(unittest.TestCase):
    """Tests for AdaptiveFitnessFunction."""

    def setUp(self):
        """Set up test fixtures."""
        self.fitness = AdaptiveFitnessFunction()

    def test_calculate_good_metrics(self):
        """Test fitness with good metrics."""
        metrics = {
            'total_profit_pct': 0.15,
            'sharpe_ratio': 2.0,
            'max_drawdown': 0.08,
            'win_rate': 0.65,
            'profit_factor': 2.0,
        }

        score = self.fitness.calculate(metrics)

        self.assertGreater(score, 0.5)

    def test_calculate_poor_metrics(self):
        """Test fitness with poor metrics."""
        metrics = {
            'total_profit_pct': -0.05,
            'sharpe_ratio': -0.5,
            'max_drawdown': 0.30,
            'win_rate': 0.35,
            'profit_factor': 0.5,
        }

        score = self.fitness.calculate(metrics)

        self.assertLess(score, 0.5)

    def test_volatility_adjustment(self):
        """Test volatility adjustment."""
        metrics = {
            'total_profit_pct': 0.10,
            'sharpe_ratio': 1.5,
            'max_drawdown': 0.10,
            'win_rate': 0.55,
            'profit_factor': 1.5,
        }

        # Normal volatility
        normal_score = self.fitness.calculate(metrics, market_volatility=1.0)

        # High volatility should favor stability
        high_vol_score = self.fitness.calculate(metrics, market_volatility=2.0)

        # Both should be positive
        self.assertGreater(normal_score, 0)
        self.assertGreater(high_vol_score, 0)


class TestAdaptiveOptimizer(unittest.TestCase):
    """Tests for AdaptiveOptimizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "adaptive_state.json")
        self.versions_dir = os.path.join(self.temp_dir, "versions")

        # Create mock components
        from deployment.version_control import StrategyVersionControl
        from monitoring.performance_db import PerformanceDB

        self.vc = StrategyVersionControl(self.versions_dir)
        self.db = PerformanceDB(os.path.join(self.temp_dir, "perf.db"))

        self.optimizer = AdaptiveOptimizer(
            strategy_name="TestStrategy",
            version_control=self.vc,
            performance_db=self.db,
            config=AdaptiveConfig(
                check_interval_minutes=1,
                min_trades_for_evaluation=5,
                min_hours_between_optimizations=0,
            ),
            state_file=self.state_file
        )

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_initial_state(self):
        """Test initial state is IDLE."""
        self.assertEqual(self.optimizer.state, AdaptiveState.IDLE)

    def test_start(self):
        """Test starting the optimizer."""
        self.optimizer.start()
        self.assertEqual(self.optimizer.state, AdaptiveState.MONITORING)

    def test_stop(self):
        """Test stopping the optimizer."""
        self.optimizer.start()
        self.optimizer.stop()
        self.assertEqual(self.optimizer.state, AdaptiveState.IDLE)

    def test_get_status(self):
        """Test getting status."""
        self.optimizer.start()
        status = self.optimizer.get_status()

        self.assertEqual(status['strategy_name'], "TestStrategy")
        self.assertEqual(status['state'], "monitoring")
        self.assertTrue(status['can_optimize'])

    def test_state_persistence(self):
        """Test state is saved and loaded."""
        self.optimizer.start()
        self.optimizer._last_optimization_time = utc_now()
        self.optimizer._save_state()

        # Create new instance
        new_optimizer = AdaptiveOptimizer(
            strategy_name="TestStrategy",
            version_control=self.vc,
            performance_db=self.db,
            state_file=self.state_file
        )

        self.assertIsNotNone(new_optimizer._last_optimization_time)


class TestOptimizationScheduler(unittest.TestCase):
    """Tests for OptimizationScheduler."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "scheduler_state.json")

        self.scheduler = OptimizationScheduler(
            config=ScheduleConfig(
                min_interval_hours=0,
                max_per_day=10,
                max_per_week=20,
            ),
            state_file=self.state_file
        )

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_schedule_task(self):
        """Test scheduling a task."""
        task = self.scheduler.schedule(
            "TestStrategy",
            "degradation_detected",
            SchedulePriority.NORMAL
        )

        self.assertIsNotNone(task)
        self.assertEqual(task.strategy_name, "TestStrategy")
        self.assertEqual(task.status, "pending")

    def test_schedule_critical_runs_immediately(self):
        """Test critical priority schedules immediately."""
        task = self.scheduler.schedule(
            "TestStrategy",
            "critical_alert",
            SchedulePriority.CRITICAL
        )

        # Critical tasks should be scheduled for now
        self.assertLessEqual(
            (task.scheduled_time - utc_now()).total_seconds(),
            60  # Within a minute
        )

    def test_duplicate_prevention(self):
        """Test that duplicate scheduling is prevented."""
        task1 = self.scheduler.schedule("TestStrategy", "reason1")
        task2 = self.scheduler.schedule("TestStrategy", "reason2")

        self.assertIsNotNone(task1)
        self.assertIsNone(task2)  # Should be rejected as duplicate

    def test_daily_limit(self):
        """Test daily limit enforcement."""
        scheduler = OptimizationScheduler(
            config=ScheduleConfig(max_per_day=2, queue_size=2),
            state_file=os.path.join(self.temp_dir, "limited.json")
        )

        # Fill the queue to capacity
        scheduler.schedule("Strategy1", "reason")
        scheduler.schedule("Strategy2", "reason")

        # This should be rejected due to queue size limit
        task3 = scheduler.schedule("Strategy3", "reason")
        self.assertIsNone(task3)

    def test_process_queue(self):
        """Test processing queue."""
        # Set up optimization function
        self.scheduler.set_optimization_func(
            lambda name: {'success': True}
        )

        # Schedule task for immediate execution
        task = self.scheduler.schedule(
            "TestStrategy",
            "test",
            SchedulePriority.CRITICAL
        )

        # Process
        processed = self.scheduler.process_queue()

        self.assertIsNotNone(processed)
        self.assertEqual(processed.status, "completed")

    def test_cancel_task(self):
        """Test cancelling a task."""
        task = self.scheduler.schedule("TestStrategy", "reason")
        success = self.scheduler.cancel(task.id)

        self.assertTrue(success)
        self.assertEqual(len(self.scheduler.get_queue()), 0)

    def test_get_stats(self):
        """Test getting statistics."""
        self.scheduler.schedule("Strategy1", "reason")

        stats = self.scheduler.get_stats()

        self.assertEqual(stats['queue_size'], 1)
        self.assertEqual(stats['running'], 0)

    def test_state_persistence(self):
        """Test state is saved and loaded."""
        self.scheduler.schedule("TestStrategy", "reason")

        # Create new instance
        new_scheduler = OptimizationScheduler(state_file=self.state_file)

        self.assertEqual(len(new_scheduler.get_queue()), 1)

    def test_preferred_hours_scheduling(self):
        """Test scheduling respects preferred hours."""
        scheduler = OptimizationScheduler(
            config=ScheduleConfig(
                preferred_hours=[2, 3, 4],
                avoid_hours=[8, 9, 16, 17],
            ),
            state_file=os.path.join(self.temp_dir, "hours.json")
        )

        # Schedule low priority task
        task = scheduler.schedule(
            "TestStrategy",
            "reason",
            SchedulePriority.LOW
        )

        # Should be scheduled for a preferred hour
        # (or avoided hours should be avoided)
        self.assertNotIn(task.scheduled_time.hour, [8, 9, 16, 17])


class TestScheduledOptimization(unittest.TestCase):
    """Tests for ScheduledOptimization dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        task = ScheduledOptimization(
            id="test_123",
            strategy_name="TestStrategy",
            scheduled_time=utc_now(),
            priority=SchedulePriority.HIGH,
            trigger_reason="degradation"
        )

        data = task.to_dict()

        self.assertEqual(data['id'], "test_123")
        self.assertEqual(data['strategy_name'], "TestStrategy")
        self.assertEqual(data['priority'], SchedulePriority.HIGH.value)


if __name__ == '__main__':
    unittest.main()
