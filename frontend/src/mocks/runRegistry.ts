export type MockExperimentRun = {
  run_id: string;
  created_at: string;
  source: string;
  seed: number;
  generations: number;
  population_size: number;
  best_fitness: number;
  artifact_dir: string;
  status: 'completed' | 'review' | 'failed';
  notes: string;
};

export const mockRunRegistry: MockExperimentRun[] = [
  {
    run_id: 'mock-ga-seed-42',
    created_at: '2026-06-06T08:10:00+00:00',
    source: 'mock-ga-cli',
    seed: 42,
    generations: 5,
    population_size: 30,
    best_fitness: 0.842,
    artifact_dir: 'artifacts/mock-ga-seed-42',
    status: 'completed',
    notes: 'baseline mock session with stable risk-aware fitness',
  },
  {
    run_id: 'portfolio-smoke-001',
    created_at: '2026-06-06T09:35:00+00:00',
    source: 'mock-portfolio-evaluator',
    seed: 88,
    generations: 4,
    population_size: 24,
    best_fitness: 0.776,
    artifact_dir: 'artifacts/portfolio-smoke-001',
    status: 'review',
    notes: 'multi-pair mock portfolio review pending',
  },
  {
    run_id: 'walk-forward-robustness-003',
    created_at: '2026-06-06T10:20:00+00:00',
    source: 'mock-walk-forward',
    seed: 103,
    generations: 6,
    population_size: 28,
    best_fitness: 0.731,
    artifact_dir: 'artifacts/walk-forward-robustness-003',
    status: 'completed',
    notes: 'walk-forward stability penalty enabled',
  },
];
