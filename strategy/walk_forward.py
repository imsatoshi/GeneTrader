"""Walk-Forward Analysis for preventing overfitting in strategy optimization.

Walk-forward analysis is the gold standard for validating trading strategies.
It ensures that strategies are tested on out-of-sample data, which is critical
for estimating real-world performance.

Three validation methods are provided:
1. Rolling Window: Train on N weeks, test on M weeks, roll forward
2. Expanding Window: Train on all data up to test period
3. Anchored: Train from fixed start, expand test window
"""
import os
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass

from utils.logging_config import logger


@dataclass
class ValidationPeriod:
    """Represents a single train/test period for walk-forward analysis."""
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    fold_number: int

    @property
    def train_timerange(self) -> str:
        """Return Freqtrade-compatible timerange string for training."""
        return f"{self.train_start.strftime('%Y%m%d')}-{self.train_end.strftime('%Y%m%d')}"

    @property
    def test_timerange(self) -> str:
        """Return Freqtrade-compatible timerange string for testing."""
        return f"{self.test_start.strftime('%Y%m%d')}-{self.test_end.strftime('%Y%m%d')}"

    @property
    def train_weeks(self) -> int:
        """Return number of weeks in training period."""
        return int((self.train_end - self.train_start).days / 7)

    @property
    def test_weeks(self) -> int:
        """Return number of weeks in test period."""
        return int((self.test_end - self.test_start).days / 7)


class WalkForwardValidator:
    """Walk-forward validation framework for trading strategies.

    This class generates train/test splits for walk-forward analysis,
    which is essential for preventing overfitting in trading strategies.

    Attributes:
        total_weeks: Total number of weeks of historical data
        train_weeks: Number of weeks for each training period
        test_weeks: Number of weeks for each test period
        min_train_weeks: Minimum weeks required for training
        method: Validation method ('rolling', 'expanding', 'anchored')
    """

    def __init__(
        self,
        total_weeks: int = 52,
        train_weeks: int = 26,
        test_weeks: int = 4,
        min_train_weeks: int = 12,
        method: str = 'rolling'
    ):
        """Initialize walk-forward validator.

        Args:
            total_weeks: Total weeks of data available
            train_weeks: Weeks to use for training in each fold
            test_weeks: Weeks to use for testing in each fold
            min_train_weeks: Minimum training weeks required
            method: 'rolling', 'expanding', or 'anchored'
        """
        self.total_weeks = total_weeks
        self.train_weeks = train_weeks
        self.test_weeks = test_weeks
        self.min_train_weeks = min_train_weeks
        self.method = method.lower()

        if self.method not in ('rolling', 'expanding', 'anchored'):
            raise ValueError(f"Unknown method: {method}. Use 'rolling', 'expanding', or 'anchored'")

        if train_weeks < min_train_weeks:
            raise ValueError(f"train_weeks ({train_weeks}) must be >= min_train_weeks ({min_train_weeks})")

        if train_weeks + test_weeks > total_weeks:
            raise ValueError(f"train_weeks + test_weeks ({train_weeks + test_weeks}) exceeds total_weeks ({total_weeks})")

    def generate_periods(self, end_date: Optional[datetime] = None) -> List[ValidationPeriod]:
        """Generate train/test periods for walk-forward analysis.

        Args:
            end_date: End date for the analysis (defaults to today)

        Returns:
            List of ValidationPeriod objects for each fold
        """
        if end_date is None:
            end_date = datetime.now()

        start_date = end_date - timedelta(weeks=self.total_weeks)
        periods: List[ValidationPeriod] = []

        if self.method == 'rolling':
            periods = self._generate_rolling_periods(start_date, end_date)
        elif self.method == 'expanding':
            periods = self._generate_expanding_periods(start_date, end_date)
        elif self.method == 'anchored':
            periods = self._generate_anchored_periods(start_date, end_date)

        logger.info(f"Generated {len(periods)} walk-forward validation periods using {self.method} method")
        return periods

    def _generate_rolling_periods(self, start_date: datetime, end_date: datetime) -> List[ValidationPeriod]:
        """Generate rolling window validation periods.

        In rolling window validation:
        - Training window is fixed size (train_weeks)
        - Test window is fixed size (test_weeks)
        - Both windows roll forward by test_weeks each fold
        """
        periods = []
        fold = 0
        current_train_start = start_date

        while True:
            train_end = current_train_start + timedelta(weeks=self.train_weeks)
            test_start = train_end
            test_end = test_start + timedelta(weeks=self.test_weeks)

            if test_end > end_date:
                break

            periods.append(ValidationPeriod(
                train_start=current_train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                fold_number=fold
            ))

            fold += 1
            current_train_start = current_train_start + timedelta(weeks=self.test_weeks)

        return periods

    def _generate_expanding_periods(self, start_date: datetime, end_date: datetime) -> List[ValidationPeriod]:
        """Generate expanding window validation periods.

        In expanding window validation:
        - Training always starts from start_date
        - Training window expands each fold
        - Test window is fixed size
        """
        periods = []
        fold = 0
        current_train_end = start_date + timedelta(weeks=self.min_train_weeks)

        while True:
            test_start = current_train_end
            test_end = test_start + timedelta(weeks=self.test_weeks)

            if test_end > end_date:
                break

            periods.append(ValidationPeriod(
                train_start=start_date,
                train_end=current_train_end,
                test_start=test_start,
                test_end=test_end,
                fold_number=fold
            ))

            fold += 1
            current_train_end = current_train_end + timedelta(weeks=self.test_weeks)

        return periods

    def _generate_anchored_periods(self, start_date: datetime, end_date: datetime) -> List[ValidationPeriod]:
        """Generate anchored validation periods.

        In anchored validation:
        - Training always starts from start_date
        - Test period is fixed at the end
        - Multiple training periods are tested against same test set
        """
        periods = []

        # Reserve last test_weeks for testing
        test_start = end_date - timedelta(weeks=self.test_weeks)
        test_end = end_date

        # Generate multiple training windows of different sizes
        fold = 0
        current_train_weeks = self.min_train_weeks

        while current_train_weeks <= self.train_weeks:
            train_end = test_start
            train_start = train_end - timedelta(weeks=current_train_weeks)

            if train_start < start_date:
                train_start = start_date

            periods.append(ValidationPeriod(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                fold_number=fold
            ))

            fold += 1
            current_train_weeks += self.test_weeks

        return periods

    def calculate_composite_fitness(
        self,
        fold_results: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """Calculate composite fitness from multiple fold results.

        This combines training and test fitness with emphasis on:
        1. Out-of-sample (test) performance
        2. Consistency across folds
        3. Penalty for overfitting (train >> test)

        Args:
            fold_results: List of dicts with 'train_fitness' and 'test_fitness'
            weights: Optional custom weights for components

        Returns:
            Composite fitness score
        """
        if not fold_results:
            return float('-inf')

        default_weights = {
            'test_mean': 0.40,      # Average test performance
            'test_min': 0.20,       # Worst-case test performance
            'consistency': 0.20,    # Low variance across folds
            'overfit_penalty': 0.20 # Penalty for train >> test
        }
        weights = weights or default_weights

        train_scores = [r['train_fitness'] for r in fold_results if r['train_fitness'] is not None]
        test_scores = [r['test_fitness'] for r in fold_results if r['test_fitness'] is not None]

        if not test_scores:
            return float('-inf')

        # 1. Average test performance
        test_mean = sum(test_scores) / len(test_scores)

        # 2. Worst-case test performance (robustness)
        test_min = min(test_scores)

        # 3. Consistency (inverse of standard deviation)
        if len(test_scores) > 1:
            test_variance = sum((x - test_mean) ** 2 for x in test_scores) / len(test_scores)
            consistency = 1.0 / (1.0 + test_variance ** 0.5)
        else:
            consistency = 1.0

        # 4. Overfitting penalty (if train >> test)
        if train_scores and test_scores:
            train_mean = sum(train_scores) / len(train_scores)
            if train_mean > 0 and test_mean > 0:
                overfit_ratio = train_mean / test_mean
                # Penalty increases exponentially when train is much better than test
                overfit_penalty = 1.0 / (1.0 + max(0, overfit_ratio - 1.5) ** 2)
            else:
                overfit_penalty = 0.5
        else:
            overfit_penalty = 1.0

        # Combine components
        composite = (
            weights['test_mean'] * test_mean +
            weights['test_min'] * test_min +
            weights['consistency'] * consistency +
            weights['overfit_penalty'] * overfit_penalty
        )

        logger.info(
            f"Walk-forward composite fitness: {composite:.4f} "
            f"(test_mean={test_mean:.4f}, test_min={test_min:.4f}, "
            f"consistency={consistency:.4f}, overfit_penalty={overfit_penalty:.4f})"
        )

        return composite


def create_validator_from_settings(settings: Any) -> WalkForwardValidator:
    """Create WalkForwardValidator from settings object.

    Args:
        settings: Settings object with walk-forward configuration

    Returns:
        Configured WalkForwardValidator instance
    """
    # Default values if not in settings
    total_weeks = getattr(settings, 'total_data_weeks', 52)
    train_weeks = getattr(settings, 'walk_forward_train_weeks', 26)
    test_weeks = getattr(settings, 'walk_forward_test_weeks', 4)
    # Settings and ga.json name this walk_forward_min_train_weeks; reading the
    # shorter name meant the configured value was silently ignored.
    min_train = getattr(settings, 'walk_forward_min_train_weeks', 12)
    method = getattr(settings, 'walk_forward_method', 'rolling')

    return WalkForwardValidator(
        total_weeks=total_weeks,
        train_weeks=train_weeks,
        test_weeks=test_weeks,
        min_train_weeks=min_train,
        method=method
    )


# Example usage
if __name__ == "__main__":
    # Create validator with 52 weeks of data
    validator = WalkForwardValidator(
        total_weeks=52,
        train_weeks=26,
        test_weeks=4,
        method='rolling'
    )

    # Generate periods
    periods = validator.generate_periods()

    print(f"\nGenerated {len(periods)} validation periods:\n")
    for p in periods:
        print(f"Fold {p.fold_number}:")
        print(f"  Train: {p.train_timerange} ({p.train_weeks} weeks)")
        print(f"  Test:  {p.test_timerange} ({p.test_weeks} weeks)")
        print()
