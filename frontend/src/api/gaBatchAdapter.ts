export type GaBatchJobStatus = 'success' | 'failed' | 'skipped' | 'timeout' | 'policy_rejected';
export type GaBatchStatus = 'all_success' | 'partial_success' | 'all_failed' | 'skipped' | 'policy_rejected';

export interface GaBatchNormalizedMetrics {
  profit: number;
  sharpe: number;
  winRate: number;
  maxDrawdown: number;
  totalTrades: number;
  maxConsecutiveLosses: number;
  leverage: number;
  riskPerTrade: number;
}

export interface GaBatchLeaderboardEntry {
  jobId: string;
  genomeHash: string;
  status: GaBatchJobStatus;
  normalizedMetrics?: GaBatchNormalizedMetrics;
  fitnessComponents?: Record<string, number>;
  errorType?: string;
  errorMessage?: string;
}

export interface GaBatchSummary {
  batchId: string;
  status: GaBatchStatus;
  totalJobs: number;
  succeeded: number;
  failed: number;
  skipped: number;
  timedOut: number;
  policyRejected: number;
  leaderboard: GaBatchLeaderboardEntry[];
  metadata?: Record<string, unknown>;
}

type SmallBatchArtifact = {
  batch_id?: unknown;
  batchId?: unknown;
  status?: unknown;
  total_jobs?: unknown;
  totalJobs?: unknown;
  succeeded?: unknown;
  failed?: unknown;
  skipped?: unknown;
  timed_out?: unknown;
  timedOut?: unknown;
  policy_rejected?: unknown;
  policyRejected?: unknown;
  results?: SmallBatchJobArtifact[];
  metadata?: unknown;
};

type SmallBatchJobArtifact = {
  job_id?: unknown;
  jobId?: unknown;
  genome_hash?: unknown;
  genomeHash?: unknown;
  status?: unknown;
  normalized_result?: unknown;
  normalizedResult?: unknown;
  error_type?: unknown;
  errorType?: unknown;
  error_message?: unknown;
  errorMessage?: unknown;
  metadata?: unknown;
};

const batchStatuses = new Set<GaBatchStatus>([
  'all_success',
  'partial_success',
  'all_failed',
  'skipped',
  'policy_rejected',
]);

const jobStatuses = new Set<GaBatchJobStatus>(['success', 'failed', 'skipped', 'timeout', 'policy_rejected']);

const secretPattern = /(api[_-]?key|secret|password|private[_-]?key|token|webhook|jwt)/gi;
const secretKeyPattern = /(api[_-]?key|secret|password|private[_-]?key|token|webhook|jwt)/i;
const pathPattern = /([A-Za-z]:[\\/][^\s"']+|\/(?:home|Users)\/[^\s"']+)/g;

function redactText(value: unknown): string {
  const redactedTokens: string[] = [];
  const protectedText = String(value ?? '').replace(/<redacted:[^>]+>/g, (token) => {
    redactedTokens.push(token);
    return `__RDX${redactedTokens.length - 1}__`;
  });
  return protectedText
    .replace(secretPattern, '<redacted:secret-key>')
    .replace(pathPattern, '<redacted:path>')
    .replaceAll('.env', '<redacted:env>')
    .replace(/__RDX(\d+)__/g, (_, index: string) => redactedTokens[Number(index)] ?? '<redacted>');
}

function finiteNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function safeString(value: unknown, fallback: string): string {
  return typeof value === 'string' && value.length > 0 ? redactText(value) : fallback;
}

function normalizeBatchStatus(value: unknown): GaBatchStatus {
  return typeof value === 'string' && batchStatuses.has(value as GaBatchStatus) ? (value as GaBatchStatus) : 'all_failed';
}

function normalizeJobStatus(value: unknown): GaBatchJobStatus {
  return typeof value === 'string' && jobStatuses.has(value as GaBatchJobStatus) ? (value as GaBatchJobStatus) : 'failed';
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function redactJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(redactJsonValue);
  }
  if (isRecord(value)) {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        redactText(key),
        secretKeyPattern.test(key) ? '<redacted:secret>' : redactJsonValue(item),
      ]),
    );
  }
  if (typeof value === 'string') {
    return redactText(value);
  }
  return value;
}

function safeMetadata(value: unknown): Record<string, unknown> | undefined {
  if (!isRecord(value)) {
    return undefined;
  }
  return redactJsonValue(value) as Record<string, unknown>;
}

function numericRecord(value: unknown): Record<string, number> {
  if (!isRecord(value)) {
    return {};
  }
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => typeof item === 'number' && Number.isFinite(item)),
  ) as Record<string, number>;
}

function extractFitnessComponents(normalized: unknown, jobMetadata: unknown): Record<string, number> | undefined {
  const normalizedRecord = isRecord(normalized) ? normalized : {};
  const metadataRecord = isRecord(normalizedRecord.metadata) ? normalizedRecord.metadata : {};
  const jobMetadataRecord = isRecord(jobMetadata) ? jobMetadata : {};
  const candidates = [
    normalizedRecord.fitness_components,
    normalizedRecord.fitnessComponents,
    metadataRecord.fitness_components,
    metadataRecord.fitnessComponents,
    jobMetadataRecord.fitness_components,
    jobMetadataRecord.fitnessComponents,
  ];
  for (const candidate of candidates) {
    const components = numericRecord(candidate);
    if (Object.keys(components).length > 0) {
      return components;
    }
  }
  return undefined;
}

function mapNormalizedMetrics(normalized: unknown): GaBatchNormalizedMetrics | undefined {
  if (!isRecord(normalized)) {
    return undefined;
  }
  return {
    profit: finiteNumber(normalized.profit),
    sharpe: finiteNumber(normalized.sharpe),
    winRate: finiteNumber(normalized.win_rate ?? normalized.winRate),
    maxDrawdown: finiteNumber(normalized.max_drawdown ?? normalized.maxDrawdown),
    totalTrades: finiteNumber(normalized.total_trades ?? normalized.totalTrades),
    maxConsecutiveLosses: finiteNumber(normalized.max_consecutive_losses ?? normalized.maxConsecutiveLosses),
    leverage: finiteNumber(normalized.leverage),
    riskPerTrade: finiteNumber(normalized.risk_per_trade ?? normalized.riskPerTrade),
  };
}

function mapJob(item: SmallBatchJobArtifact, index: number): GaBatchLeaderboardEntry {
  const normalized = item.normalized_result ?? item.normalizedResult;
  const metrics = mapNormalizedMetrics(normalized);
  const errorType = item.error_type ?? item.errorType;
  const errorMessage = item.error_message ?? item.errorMessage;
  return {
    jobId: safeString(item.job_id ?? item.jobId, `job-${index + 1}`),
    genomeHash: safeString(item.genome_hash ?? item.genomeHash, 'unknown-genome'),
    status: normalizeJobStatus(item.status),
    normalizedMetrics: metrics,
    fitnessComponents: extractFitnessComponents(normalized, item.metadata),
    errorType: typeof errorType === 'string' ? redactText(errorType) : undefined,
    errorMessage: typeof errorMessage === 'string' ? redactText(errorMessage) : undefined,
  };
}

export function adaptSmallBatchArtifactToDashboard(artifact: SmallBatchArtifact): GaBatchSummary {
  const results = Array.isArray(artifact.results) ? artifact.results : [];
  return {
    batchId: safeString(artifact.batch_id ?? artifact.batchId, 'unknown-batch'),
    status: normalizeBatchStatus(artifact.status),
    totalJobs: finiteNumber(artifact.total_jobs ?? artifact.totalJobs, results.length),
    succeeded: finiteNumber(artifact.succeeded),
    failed: finiteNumber(artifact.failed),
    skipped: finiteNumber(artifact.skipped),
    timedOut: finiteNumber(artifact.timed_out ?? artifact.timedOut),
    policyRejected: finiteNumber(artifact.policy_rejected ?? artifact.policyRejected),
    leaderboard: results.map(mapJob),
    metadata: safeMetadata(artifact.metadata),
  };
}

export async function fetchGaBatchSummary(): Promise<GaBatchSummary> {
  return adaptSmallBatchArtifactToDashboard(defaultBatchArtifact as SmallBatchArtifact);
}
import defaultBatchArtifact from './__fixtures__/gaBatchArtifact.json';
