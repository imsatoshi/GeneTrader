export type DataFormat = 'csv' | 'json' | 'json.gz' | 'feather' | 'parquet';

export interface OfflineDatasetProbe {
  columns: string[];
  hasTimestampColumn: boolean;
  hasOhlcvColumns: boolean;
  rowCountEstimate: number | null;
}

export interface InventoryFile {
  path: string;
  format: DataFormat;
  sizeBytes: number;
  pair: string | null;
  timeframe: string | null;
  probe?: OfflineDatasetProbe;
}

export interface InventorySummary {
  fileCount: number;
  parsedFileCount: number;
  unparsedFileCount: number;
  totalSizeBytes: number;
  pairs: string[];
  timeframes: string[];
}

export interface CoverageCell {
  timeframe: string;
  status: 'present' | 'missing';
}

export interface CoverageRow {
  pair: string;
  cells: CoverageCell[];
}

export interface CoverageMatrix {
  pairs: string[];
  timeframes: string[];
  matrix: CoverageRow[];
}

export interface GateResult {
  ok: boolean;
  errors: string[];
  warnings: string[];
  coverageMatrix: CoverageMatrix;
}
