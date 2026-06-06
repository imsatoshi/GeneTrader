import type { CoverageMatrix, GateResult, InventoryFile, InventorySummary } from '../types/offlineData';

export const mockInventoryFiles: InventoryFile[] = [
  {
    path: 'binance/BTC_USDT-15m.csv',
    format: 'csv',
    sizeBytes: 482_100,
    pair: 'BTC/USDT',
    timeframe: '15m',
    probe: {
      columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume'],
      hasTimestampColumn: true,
      hasOhlcvColumns: true,
      rowCountEstimate: 1800,
    },
  },
  {
    path: 'binance/BTC_USDT-1h.json',
    format: 'json',
    sizeBytes: 188_540,
    pair: 'BTC/USDT',
    timeframe: '1h',
    probe: {
      columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume'],
      hasTimestampColumn: true,
      hasOhlcvColumns: true,
      rowCountEstimate: 520,
    },
  },
  {
    path: 'binance/BTC_USDT-4h.json',
    format: 'json',
    sizeBytes: 58_230,
    pair: 'BTC/USDT',
    timeframe: '4h',
    probe: {
      columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume'],
      hasTimestampColumn: true,
      hasOhlcvColumns: true,
      rowCountEstimate: 140,
    },
  },
];

export const mockInventorySummary: InventorySummary = {
  fileCount: 3,
  parsedFileCount: 3,
  unparsedFileCount: 0,
  totalSizeBytes: mockInventoryFiles.reduce((total, item) => total + item.sizeBytes, 0),
  pairs: ['BTC/USDT'],
  timeframes: ['15m', '1h', '4h'],
};

export const mockCoverageMatrix: CoverageMatrix = {
  pairs: ['BTC/USDT'],
  timeframes: ['15m', '1h', '4h'],
  matrix: [
    {
      pair: 'BTC/USDT',
      cells: [
        { timeframe: '15m', status: 'present' },
        { timeframe: '1h', status: 'present' },
        { timeframe: '4h', status: 'present' },
      ],
    },
  ],
};

export const mockGateResult: GateResult = {
  ok: true,
  errors: [],
  warnings: ['duplicate coverage is checked in permissive mode'],
  coverageMatrix: mockCoverageMatrix,
};
