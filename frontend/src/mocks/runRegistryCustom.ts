export type CustomExperimentRun = {
  run_id: string;
  created_at: string;
  source: string;
  seed: number;
  generations: number;
  population_size: number;
  best_fitness: number;
  artifact_dir: string;
  status: 'completed' | 'review' | 'failed';
  strategy_family: string;
  stability_score: number;
  failure_rate: number;
  portfolio_profit: number;
  portfolio_drawdown: number;
  best_genome_id: string;
  notes: string;
};

export const customRunRegistry: CustomExperimentRun[] = [
  {
    run_id: 'custom-ga-seed-42',
    created_at: '2026-06-06T12:10:00+00:00',
    source: 'custom-strategy-mock-ga',
    seed: 42,
    generations: 5,
    population_size: 30,
    best_fitness: 0.864,
    artifact_dir: 'artifacts/custom-ga-seed-42',
    status: 'completed',
    strategy_family: 'custom-bollinger-rsi',
    stability_score: 0.82,
    failure_rate: 0.06,
    portfolio_profit: 0.18,
    portfolio_drawdown: 0.09,
    best_genome_id: 'custom-gen004-ind017',
    notes: 'custom schema baseline with advisory risk governor',
  },
  {
    run_id: 'custom-walk-forward-017',
    created_at: '2026-06-06T13:30:00+00:00',
    source: 'custom-walk-forward',
    seed: 17,
    generations: 4,
    population_size: 24,
    best_fitness: 0.799,
    artifact_dir: 'artifacts/custom-walk-forward-017',
    status: 'review',
    strategy_family: 'custom-bollinger-rsi',
    stability_score: 0.76,
    failure_rate: 0.09,
    portfolio_profit: 0.14,
    portfolio_drawdown: 0.13,
    best_genome_id: 'custom-gen003-ind009',
    notes: 'walk-forward stability and overfit penalty review',
  },
  {
    run_id: 'custom-portfolio-088',
    created_at: '2026-06-06T14:05:00+00:00',
    source: 'custom-portfolio',
    seed: 88,
    generations: 6,
    population_size: 28,
    best_fitness: 0.812,
    artifact_dir: 'artifacts/custom-portfolio-088',
    status: 'completed',
    strategy_family: 'custom-bollinger-rsi',
    stability_score: 0.79,
    failure_rate: 0.05,
    portfolio_profit: 0.21,
    portfolio_drawdown: 0.08,
    best_genome_id: 'custom-gen006-ind021',
    notes: 'multi-pair portfolio mock validation',
  },
];
