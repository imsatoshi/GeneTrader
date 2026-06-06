export type SessionStatus = 'pass' | 'fail' | 'warning' | 'unknown';

export type SessionSummary = {
  schemaVersion: 'session-summary/v1';
  generatedAt: string;
  source: 'mock' | 'preflight-json' | 'api';
  offlineData: OfflineDataSessionSummary;
  requirementsGate: RequirementsGateSummary;
  gaRunSummary: GaRunSummary;
};

export type OfflineDataSessionSummary = {
  status: SessionStatus;
  inventoryCount: number;
  manifestDatasetCount: number;
  gateErrorCount: number;
  gateWarningCount: number;
  inventory: InventoryFileSummary[];
  manifestDatasets: ManifestDatasetSummary[];
  coverageMatrix: CoverageMatrix;
  gateErrors: GateIssue[];
  gateWarnings: GateIssue[];
  ignoredFiles?: IgnoredFileSummary[];
};

export type RequirementsGateSummary = {
  status: SessionStatus;
  requiredPairs: string[];
  requiredTimeframes: string[];
  missingCombinations: PairTimeframeCombination[];
  presentCombinations: PairTimeframeCombination[];
};

export type GaRunSummary = {
  status: 'mock' | 'idle' | 'running' | 'completed' | 'failed';
  runId: string;
  generation: number;
  populationSize: number;
  bestFitness: number;
  averageFitness: number;
  mutationRate: number;
  crossoverRate: number;
  bestGenomeId?: string;
  fitnessSeries: FitnessPoint[];
};

export type InventoryFileSummary = {
  path: string;
  format: string;
  sizeBytes: number;
  pair: string | null;
  timeframe: string | null;
};

export type ManifestDatasetSummary = InventoryFileSummary;

export type GateIssue = {
  code: string;
  message?: string;
  path?: string;
  pair?: string;
  timeframe?: string;
};

export type IgnoredFileSummary = {
  path: string;
  reason: string;
};

export type PairTimeframeCombination = {
  pair: string;
  timeframe: string;
};

export type CoverageMatrix = Record<string, Record<string, 'present' | 'missing'>>;

export type FitnessPoint = {
  generation: number;
  bestFitness: number;
  averageFitness: number;
};
