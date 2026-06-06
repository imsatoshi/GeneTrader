import type { SessionSummary } from '../types/sessionSummary';

const missingCombinations = [
  { pair: 'BTC/USDT', timeframe: '4h' },
  { pair: 'ETH/USDT', timeframe: '1h' },
];

const presentCombinations = [
  { pair: 'BTC/USDT', timeframe: '1h' },
  { pair: 'ETH/USDT', timeframe: '4h' },
];

const inventory = [
  {
    path: 'binance/BTC_USDT-1h.json',
    format: 'json',
    sizeBytes: 12_345,
    pair: 'BTC/USDT',
    timeframe: '1h',
  },
  {
    path: 'binance/ETH_USDT-4h.csv',
    format: 'csv',
    sizeBytes: 23_456,
    pair: 'ETH/USDT',
    timeframe: '4h',
  },
];

const gateErrors = missingCombinations.map((item) => ({
  code: 'missing_pair_timeframe',
  message: `No dataset found for ${item.pair} ${item.timeframe}`,
  pair: item.pair,
  timeframe: item.timeframe,
}));

const gateWarnings = [
  {
    code: 'mock_only',
    message: 'Mock session summary is read-only and does not trigger backtests.',
  },
];

const fitnessSeries = [
  { generation: 1, bestFitness: 42, averageFitness: 31 },
  { generation: 4, bestFitness: 68, averageFitness: 52 },
  { generation: 7, bestFitness: 84, averageFitness: 63 },
  { generation: 10, bestFitness: 95, averageFitness: 72 },
];

export const sessionSummary: SessionSummary = {
  schemaVersion: 'session-summary/v1',
  generatedAt: '2026-06-02T00:00:00Z',
  source: 'mock',
  offlineData: {
    status: 'fail',
    inventoryCount: inventory.length,
    manifestDatasetCount: inventory.length,
    gateErrorCount: gateErrors.length,
    gateWarningCount: gateWarnings.length,
    inventory,
    manifestDatasets: inventory,
    coverageMatrix: {
      'BTC/USDT': { '1h': 'present', '4h': 'missing' },
      'ETH/USDT': { '1h': 'missing', '4h': 'present' },
    },
    gateErrors,
    gateWarnings,
    ignoredFiles: [
      {
        path: '.DS_Store',
        reason: 'hidden_file',
      },
    ],
  },
  requirementsGate: {
    status: 'fail',
    requiredPairs: ['BTC/USDT', 'ETH/USDT'],
    requiredTimeframes: ['1h', '4h'],
    missingCombinations,
    presentCombinations,
  },
  gaRunSummary: {
    status: 'mock',
    runId: 'mock-run-001',
    generation: 10,
    populationSize: 20,
    bestFitness: 95,
    averageFitness: 72,
    mutationRate: 0.2,
    crossoverRate: 0.5,
    bestGenomeId: 'mock-genome-010-best',
    fitnessSeries,
  },
};
