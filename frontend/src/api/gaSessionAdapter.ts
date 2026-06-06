export interface GaFitnessPoint {
  generation: number;
  bestFitness: number;
  averageFitness: number;
  diversity: number;
}

export interface GaLeaderboardEntry {
  rank: number;
  genomeId: string;
  fitness: number;
  profit: number;
  drawdown: number;
  sharpe: number;
  winRate: number;
  fitnessComponents: Record<string, number>;
  maxLossStreak: number | null;
  leverage: number | null;
  riskPerTrade: number | null;
  genome: Record<string, unknown>;
}

export interface GaSessionSummary {
  schemaVersion: string;
  source: string;
  runId: string;
  generation: number;
  populationSize: number;
  bestFitness: number;
  averageFitness: number;
  diversity: number;
  bestGenome: Record<string, unknown>;
  fitnessSeries: GaFitnessPoint[];
  leaderboard: GaLeaderboardEntry[];
}

type SnakeCaseGaArtifact = {
  schema_version?: string;
  source?: string;
  run_id?: string;
  generation?: number;
  population_size?: number;
  best_fitness?: number;
  average_fitness?: number;
  diversity?: number;
  best_genome?: Record<string, unknown>;
  fitness_series?: Array<{
    generation: number;
    best_fitness: number;
    average_fitness: number;
    diversity: number;
  }>;
  leaderboard?: Array<SnakeCaseLeaderboardEntry>;
  genomes?: Array<SnakeCaseLeaderboardEntry>;
  session_summary?: SnakeCaseGaArtifact;
};

type SnakeCaseLeaderboardEntry = {
  rank: number;
  genome_id?: string;
  genomeId?: string;
  fitness: number;
  profit?: number;
  drawdown?: number;
  max_drawdown?: number;
  sharpe?: number;
  win_rate?: number;
  winRate?: number;
  fitness_components?: unknown;
  fitnessComponents?: unknown;
  max_consecutive_losses?: unknown;
  maxLossStreak?: unknown;
  leverage?: unknown;
  risk_per_trade?: unknown;
  riskPerTrade?: unknown;
  genome: Record<string, unknown>;
};

const defaultGaArtifact: SnakeCaseGaArtifact = {
  schema_version: 'ga-session-summary/v1',
  source: 'mock-ga-execution',
  run_id: 'mock-ga-seed-2026',
  generation: 3,
  population_size: 8,
  best_fitness: 0.472481,
  average_fitness: 0.182214,
  diversity: 0.875,
  best_genome: {
    genome_id: 'gen003-ind002',
    parameters: {
      bb_window: 34,
      bb_stddev: 2.08,
      stop_loss_pct: 0.035,
      take_profit_pct: 0.14,
      leverage: 2.4,
      risk_per_trade: 0.014,
    },
  },
  fitness_series: [
    { generation: 1, best_fitness: 0.251044, average_fitness: 0.103117, diversity: 1 },
    { generation: 2, best_fitness: 0.392802, average_fitness: 0.151331, diversity: 0.875 },
    { generation: 3, best_fitness: 0.472481, average_fitness: 0.182214, diversity: 0.875 },
  ],
  leaderboard: [
    {
      rank: 1,
      genome_id: 'gen003-ind002',
      fitness: 0.472481,
      profit: 0.22,
      drawdown: 0.06,
      sharpe: 1.7,
      win_rate: 0.61,
      max_consecutive_losses: 2,
      leverage: 2.4,
      risk_per_trade: 0.014,
      fitness_components: {
        profit_component: 0.22,
        sharpe_component: 0.425,
        win_rate_component: 0.061,
        drawdown_penalty: 0.12,
        leverage_penalty: 0,
        risk_per_trade_penalty: 0,
        loss_streak_penalty: 0.3,
        final_fitness: 0.472481,
      },
      genome: {
        genome_id: 'gen003-ind002',
        parameters: {
          bb_window: 34,
          bb_stddev: 2.08,
          stop_loss_pct: 0.035,
          take_profit_pct: 0.14,
          leverage: 2.4,
          risk_per_trade: 0.014,
        },
      },
    },
    {
      rank: 2,
      genome_id: 'gen003-ind004',
      fitness: 0.331902,
      profit: 0.18,
      drawdown: 0.09,
      sharpe: 1.28,
      win_rate: 0.57,
      max_consecutive_losses: 3,
      leverage: 3.2,
      risk_per_trade: 0.018,
      fitness_components: {
        profit_component: 0.18,
        sharpe_component: 0.32,
        win_rate_component: 0.057,
        drawdown_penalty: 0.18,
        leverage_penalty: 0.07,
        risk_per_trade_penalty: 0,
        loss_streak_penalty: 0.45,
        final_fitness: 0.331902,
      },
      genome: {
        genome_id: 'gen003-ind004',
        parameters: {
          bb_window: 29,
          bb_stddev: 2.22,
          stop_loss_pct: 0.045,
          take_profit_pct: 0.12,
          leverage: 3.2,
          risk_per_trade: 0.018,
        },
      },
    },
    {
      rank: 3,
      genome_id: 'gen003-ind006',
      fitness: 0.118012,
      profit: 0.31,
      drawdown: 0.31,
      sharpe: 0.88,
      win_rate: 0.53,
      max_consecutive_losses: 7,
      leverage: 7.5,
      risk_per_trade: 0.041,
      fitness_components: {
        profit_component: 0.31,
        sharpe_component: 0.22,
        win_rate_component: 0.053,
        drawdown_penalty: 0.62,
        leverage_penalty: 1.575,
        risk_per_trade_penalty: 0.0105,
        loss_streak_penalty: 1.05,
        final_fitness: 0.118012,
      },
      genome: {
        genome_id: 'gen003-ind006',
        parameters: {
          bb_window: 48,
          bb_stddev: 2.9,
          stop_loss_pct: 0.11,
          take_profit_pct: 0.32,
          leverage: 7.5,
          risk_per_trade: 0.041,
        },
      },
    },
  ],
};

const alternateGaArtifact: SnakeCaseGaArtifact = {
  ...defaultGaArtifact,
  run_id: 'mock-ga-seed-88',
  generation: 2,
  population_size: 6,
  best_fitness: 0.361009,
  average_fitness: 0.144221,
  diversity: 0.833333,
  fitness_series: [
    { generation: 1, best_fitness: 0.243118, average_fitness: 0.097102, diversity: 1 },
    { generation: 2, best_fitness: 0.361009, average_fitness: 0.144221, diversity: 0.833333 },
  ],
};

const artifactsByRunId: Record<string, SnakeCaseGaArtifact> = {
  'mock-ga-seed-2026': defaultGaArtifact,
  'mock-ga-seed-88': alternateGaArtifact,
};

function toNullableNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function toFitnessComponents(value: unknown): Record<string, number> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).filter(
      ([, componentValue]) => typeof componentValue === 'number' && Number.isFinite(componentValue),
    ),
  ) as Record<string, number>;
}

function mapLeaderboardEntry(item: SnakeCaseLeaderboardEntry): GaLeaderboardEntry {
  return {
    rank: item.rank,
    genomeId: item.genome_id ?? item.genomeId ?? 'unknown',
    fitness: item.fitness,
    profit: item.profit ?? 0,
    drawdown: item.drawdown ?? item.max_drawdown ?? 0,
    sharpe: item.sharpe ?? 0,
    winRate: item.win_rate ?? item.winRate ?? 0,
    fitnessComponents: toFitnessComponents(item.fitness_components ?? item.fitnessComponents),
    maxLossStreak: toNullableNumber(item.max_consecutive_losses ?? item.maxLossStreak),
    leverage: toNullableNumber(item.leverage),
    riskPerTrade: toNullableNumber(item.risk_per_trade ?? item.riskPerTrade),
    genome: item.genome,
  };
}

export function adaptGaSessionArtifact(artifact: SnakeCaseGaArtifact): GaSessionSummary {
  const source = artifact.session_summary ?? artifact;
  const sourceLeaderboard = source.leaderboard ?? artifact.genomes ?? artifact.leaderboard ?? [];
  const fitnessSeries = source.fitness_series ?? artifact.fitness_series ?? [];
  return {
    schemaVersion: source.schema_version ?? 'ga-session-summary/v1',
    source: source.source ?? 'mock-ga-execution',
    runId: source.run_id ?? 'unknown-run',
    generation: source.generation ?? artifact.generation ?? 0,
    populationSize: source.population_size ?? artifact.population_size ?? 0,
    bestFitness: source.best_fitness ?? artifact.best_fitness ?? 0,
    averageFitness: source.average_fitness ?? artifact.average_fitness ?? 0,
    diversity: source.diversity ?? artifact.diversity ?? 0,
    bestGenome: source.best_genome ?? artifact.best_genome ?? {},
    fitnessSeries: fitnessSeries.map((item) => ({
      generation: item.generation,
      bestFitness: item.best_fitness,
      averageFitness: item.average_fitness,
      diversity: item.diversity,
    })),
    leaderboard: sourceLeaderboard.map(mapLeaderboardEntry),
  };
}

export async function fetchGaSessionSummary(runId?: string): Promise<GaSessionSummary> {
  const selectedArtifact = runId ? artifactsByRunId[runId] : defaultGaArtifact;
  return adaptGaSessionArtifact(selectedArtifact ?? defaultGaArtifact);
}
