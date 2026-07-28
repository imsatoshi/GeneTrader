"""Robustness validation for trading strategies.

This module provides tools to test strategy robustness under various
conditions to ensure strategies don't just work on historical data
but have a chance of working in live trading.

Robustness tests include:
1. Parameter sensitivity - Small changes shouldn't cause large fitness drops
2. Market regime testing - Test across bull/bear/sideways markets
3. Monte Carlo validation - Random perturbations to parameters
4. Slippage sensitivity - Test with different slippage assumptions
"""
import random
import math
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime

from utils.logging_config import logger


@dataclass
class RobustnessResult:
    """Results from robustness testing."""
    original_fitness: float
    mean_perturbed_fitness: float
    min_perturbed_fitness: float
    max_perturbed_fitness: float
    fitness_std: float
    robustness_score: float  # 0-1, higher is better
    sensitivity_scores: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)


class ParameterSensitivityAnalyzer:
    """Analyze how sensitive fitness is to parameter changes.

    A robust strategy should not be overly sensitive to small
    parameter changes. If changing a parameter by 5% causes
    fitness to drop 50%, the strategy is likely overfit.
    """

    def __init__(
        self,
        perturbation_range: float = 0.1,
        num_samples: int = 10
    ):
        """Initialize analyzer.

        Args:
            perturbation_range: Maximum perturbation as fraction (0.1 = 10%)
            num_samples: Number of samples per parameter
        """
        self.perturbation_range = perturbation_range
        self.num_samples = num_samples

    def analyze(
        self,
        genes: List[Any],
        param_types: List[Dict],
        fitness_func: callable,
        original_fitness: float
    ) -> Dict[str, float]:
        """Analyze parameter sensitivity.

        Args:
            genes: Original gene values
            param_types: Parameter type definitions
            fitness_func: Function to evaluate fitness
            original_fitness: Original strategy fitness

        Returns:
            Dict mapping parameter name to sensitivity score (0-1)
        """
        sensitivity_scores = {}

        for i, param_type in enumerate(param_types):
            if i >= len(genes):
                break

            param_name = param_type.get('name', f'param_{i}')
            gene_type = param_type.get('type', 'Decimal')

            if gene_type in ('Int', 'Decimal'):
                sensitivity = self._analyze_numeric_param(
                    genes, i, param_type, fitness_func, original_fitness
                )
            elif gene_type == 'Boolean':
                sensitivity = self._analyze_boolean_param(
                    genes, i, fitness_func, original_fitness
                )
            else:
                sensitivity = 0.5  # Default for categorical

            sensitivity_scores[param_name] = sensitivity

        return sensitivity_scores

    def _analyze_numeric_param(
        self,
        genes: List[Any],
        index: int,
        param_type: Dict,
        fitness_func: callable,
        original_fitness: float
    ) -> float:
        """Analyze sensitivity of numeric parameter."""
        start = param_type.get('start', 0)
        end = param_type.get('end', 100)
        original_value = genes[index]

        fitness_changes = []

        for _ in range(self.num_samples):
            # Create perturbed genes
            perturbed = genes.copy()

            # Add perturbation
            range_size = end - start
            perturbation = random.uniform(
                -self.perturbation_range * range_size,
                self.perturbation_range * range_size
            )
            new_value = max(start, min(end, original_value + perturbation))

            if param_type.get('type') == 'Int':
                new_value = int(round(new_value))

            perturbed[index] = new_value

            # Evaluate perturbed strategy
            try:
                perturbed_fitness = fitness_func(perturbed)
                if perturbed_fitness is not None and original_fitness > 0:
                    change = abs(perturbed_fitness - original_fitness) / original_fitness
                    fitness_changes.append(change)
            except Exception as e:
                logger.debug(f"Sensitivity eval failed for param index {index}: {e}")

        if not fitness_changes:
            return 0.5  # Unknown sensitivity

        # Higher average change = higher sensitivity
        avg_change = sum(fitness_changes) / len(fitness_changes)

        # Convert to 0-1 scale (1 = very sensitive)
        sensitivity = min(1.0, avg_change)

        return sensitivity

    def _analyze_boolean_param(
        self,
        genes: List[Any],
        index: int,
        fitness_func: callable,
        original_fitness: float
    ) -> float:
        """Analyze sensitivity of boolean parameter."""
        perturbed = genes.copy()
        perturbed[index] = not perturbed[index]

        try:
            perturbed_fitness = fitness_func(perturbed)
            if perturbed_fitness is not None and original_fitness > 0:
                change = abs(perturbed_fitness - original_fitness) / original_fitness
                return min(1.0, change)
        except Exception as e:
            logger.debug(f"Sensitivity eval failed for boolean param index {index}: {e}")

        return 0.5


class MonteCarloValidator:
    """Monte Carlo validation through random perturbations.

    This tests strategy robustness by running many evaluations
    with small random changes to parameters.
    """

    def __init__(
        self,
        num_simulations: int = 50,
        perturbation_range: float = 0.05
    ):
        """Initialize validator.

        Args:
            num_simulations: Number of Monte Carlo simulations
            perturbation_range: Maximum perturbation as fraction
        """
        self.num_simulations = num_simulations
        self.perturbation_range = perturbation_range

    def validate(
        self,
        genes: List[Any],
        param_types: List[Dict],
        fitness_func: callable,
        original_fitness: float
    ) -> RobustnessResult:
        """Run Monte Carlo validation.

        Args:
            genes: Original gene values
            param_types: Parameter type definitions
            fitness_func: Function to evaluate fitness
            original_fitness: Original strategy fitness

        Returns:
            RobustnessResult with statistics
        """
        perturbed_fitnesses = []

        for sim in range(self.num_simulations):
            perturbed = self._perturb_genes(genes, param_types)

            try:
                fitness = fitness_func(perturbed)
                if fitness is not None:
                    perturbed_fitnesses.append(fitness)
            except Exception as e:
                logger.debug(f"Simulation {sim} failed: {e}")

        if not perturbed_fitnesses:
            return RobustnessResult(
                original_fitness=original_fitness,
                mean_perturbed_fitness=0.0,
                min_perturbed_fitness=0.0,
                max_perturbed_fitness=0.0,
                fitness_std=0.0,
                robustness_score=0.0
            )

        # Calculate statistics
        mean_fitness = sum(perturbed_fitnesses) / len(perturbed_fitnesses)
        min_fitness = min(perturbed_fitnesses)
        max_fitness = max(perturbed_fitnesses)

        variance = sum((f - mean_fitness) ** 2 for f in perturbed_fitnesses) / len(perturbed_fitnesses)
        std = variance ** 0.5

        # Calculate robustness score
        # Good robustness: mean close to original, low variance, min not too low
        if original_fitness > 0:
            mean_ratio = mean_fitness / original_fitness
            min_ratio = min_fitness / original_fitness
            cv = std / mean_fitness if mean_fitness > 0 else 1.0

            robustness_score = (
                0.4 * max(0, min(1, mean_ratio)) +      # Mean should stay close
                0.3 * max(0, min(1, min_ratio)) +       # Min shouldn't drop too much
                0.3 * max(0, 1 - cv)                    # Low coefficient of variation
            )
        else:
            robustness_score = 0.0

        return RobustnessResult(
            original_fitness=original_fitness,
            mean_perturbed_fitness=mean_fitness,
            min_perturbed_fitness=min_fitness,
            max_perturbed_fitness=max_fitness,
            fitness_std=std,
            robustness_score=robustness_score,
            details={
                'num_simulations': len(perturbed_fitnesses),
                'perturbation_range': self.perturbation_range
            }
        )

    def _perturb_genes(
        self,
        genes: List[Any],
        param_types: List[Dict]
    ) -> List[Any]:
        """Create perturbed copy of genes."""
        perturbed = genes.copy()

        for i, gene in enumerate(perturbed):
            if i >= len(param_types):
                continue

            param_type = param_types[i]
            gene_type = param_type.get('type', 'Decimal')

            if gene_type in ('Int', 'Decimal'):
                start = param_type.get('start', 0)
                end = param_type.get('end', 100)
                range_size = end - start

                perturbation = random.gauss(0, self.perturbation_range * range_size)
                new_value = max(start, min(end, gene + perturbation))

                if gene_type == 'Int':
                    new_value = int(round(new_value))

                perturbed[i] = new_value

            elif gene_type == 'Boolean':
                # Small chance to flip
                if random.random() < self.perturbation_range:
                    perturbed[i] = not gene

        return perturbed


def calculate_robustness_score(
    original_fitness: float,
    walk_forward_results: Optional[Dict] = None,
    monte_carlo_result: Optional[RobustnessResult] = None,
    sensitivity_scores: Optional[Dict[str, float]] = None
) -> float:
    """Calculate overall robustness score.

    Combines multiple robustness metrics into a single score.

    Args:
        original_fitness: Original strategy fitness
        walk_forward_results: Results from walk-forward validation
        monte_carlo_result: Results from Monte Carlo validation
        sensitivity_scores: Parameter sensitivity scores

    Returns:
        Overall robustness score (0-1)
    """
    scores = []
    weights = []

    # Walk-forward component
    if walk_forward_results:
        wf_score = walk_forward_results.get('composite_fitness', 0)
        if original_fitness > 0:
            wf_score = wf_score / original_fitness
        scores.append(max(0, min(1, wf_score)))
        weights.append(0.4)

    # Monte Carlo component
    if monte_carlo_result:
        scores.append(monte_carlo_result.robustness_score)
        weights.append(0.35)

    # Sensitivity component (invert - low sensitivity is good)
    if sensitivity_scores:
        avg_sensitivity = sum(sensitivity_scores.values()) / len(sensitivity_scores)
        sensitivity_score = 1 - avg_sensitivity  # Invert
        scores.append(sensitivity_score)
        weights.append(0.25)

    if not scores:
        return 0.0

    # Weighted average
    total_weight = sum(weights)
    return sum(s * w for s, w in zip(scores, weights)) / total_weight


def log_robustness_report(
    strategy_name: str,
    robustness_score: float,
    monte_carlo_result: Optional[RobustnessResult] = None,
    sensitivity_scores: Optional[Dict[str, float]] = None,
    walk_forward_results: Optional[Dict] = None
) -> str:
    """Generate and log a robustness report.

    Args:
        strategy_name: Name of the strategy
        robustness_score: Overall robustness score
        monte_carlo_result: Monte Carlo validation results
        sensitivity_scores: Parameter sensitivity scores
        walk_forward_results: Walk-forward validation results

    Returns:
        Report as formatted string
    """
    report_lines = [
        f"\n{'='*60}",
        f"ROBUSTNESS REPORT: {strategy_name}",
        f"{'='*60}",
        f"Overall Robustness Score: {robustness_score:.2%}",
        ""
    ]

    # Risk assessment
    if robustness_score >= 0.7:
        risk_level = "LOW RISK - Strategy appears robust"
    elif robustness_score >= 0.5:
        risk_level = "MEDIUM RISK - Some robustness concerns"
    elif robustness_score >= 0.3:
        risk_level = "HIGH RISK - Strategy may be overfit"
    else:
        risk_level = "CRITICAL RISK - Strategy is likely overfit"

    report_lines.append(f"Risk Assessment: {risk_level}")
    report_lines.append("")

    # Monte Carlo details
    if monte_carlo_result:
        report_lines.extend([
            "Monte Carlo Validation:",
            f"  Original Fitness: {monte_carlo_result.original_fitness:.4f}",
            f"  Mean Perturbed:   {monte_carlo_result.mean_perturbed_fitness:.4f}",
            f"  Min Perturbed:    {monte_carlo_result.min_perturbed_fitness:.4f}",
            f"  Max Perturbed:    {monte_carlo_result.max_perturbed_fitness:.4f}",
            f"  Std Dev:          {monte_carlo_result.fitness_std:.4f}",
            f"  MC Score:         {monte_carlo_result.robustness_score:.2%}",
            ""
        ])

    # Sensitivity details
    if sensitivity_scores:
        report_lines.append("Parameter Sensitivity (lower is better):")
        sorted_params = sorted(sensitivity_scores.items(), key=lambda x: x[1], reverse=True)
        for param, score in sorted_params[:10]:  # Top 10 most sensitive
            bar = "█" * int(score * 20)
            report_lines.append(f"  {param:20s}: {score:.2f} {bar}")
        report_lines.append("")

    # Walk-forward details
    if walk_forward_results:
        report_lines.extend([
            "Walk-Forward Validation:",
            f"  Composite Fitness: {walk_forward_results.get('composite_fitness', 0):.4f}",
            f"  Number of Folds:   {walk_forward_results.get('num_folds', 0)}",
            f"  Method:            {walk_forward_results.get('method', 'unknown')}",
            ""
        ])

    report_lines.append("=" * 60)

    report = "\n".join(report_lines)
    logger.info(report)

    return report
