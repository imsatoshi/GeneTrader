import { useEffect, useState } from 'react';
import { fetchGaSessionSummary, type GaSessionSummary } from '../api/gaSessionAdapter';
import CoverageMatrix from '../components/CoverageMatrix';
import FitnessChart from '../components/FitnessChart';
import GateResultPanel from '../components/GateResultPanel';
import InventoryTable from '../components/InventoryTable';
import ResultsTable from '../components/ResultsTable';
import { sessionSummary } from '../mocks/sessionSummary';
import type { CoverageMatrix as ComponentCoverageMatrix, DataFormat, GateResult, InventoryFile } from '../types/offlineData';
import type { GenerationMetric, ResultCandidate } from '../types/ga';
import type { CoverageMatrix as SessionCoverageMatrix, GateIssue, InventoryFileSummary } from '../types/sessionSummary';

function toInventoryFiles(items: InventoryFileSummary[]): InventoryFile[] {
  return items.map((item) => ({
    ...item,
    format: item.format as DataFormat,
  }));
}

function toComponentCoverageMatrix(
  matrix: SessionCoverageMatrix,
  pairs: string[],
  timeframes: string[],
): ComponentCoverageMatrix {
  return {
    pairs,
    timeframes,
    matrix: pairs.map((pair) => ({
      pair,
      cells: timeframes.map((timeframe) => ({
        timeframe,
        status: matrix[pair]?.[timeframe] ?? 'missing',
      })),
    })),
  };
}

function formatCombination(item: { pair: string; timeframe: string }) {
  return `${item.pair} ${item.timeframe}`;
}

function formatIssue(item: GateIssue) {
  return item.message ?? item.code;
}

function formatNullableNumber(value: number | null) {
  return value ?? 'N/A';
}

function toFitnessChartData(summary: GaSessionSummary): GenerationMetric[] {
  return summary.fitnessSeries.map((item) => ({
    generation: item.generation,
    bestFitness: item.bestFitness,
    avgFitness: item.averageFitness,
    worstFitness: Math.max(0, item.averageFitness - 0.18),
  }));
}

function toResultCandidates(summary: GaSessionSummary): ResultCandidate[] {
  return summary.leaderboard.map((item) => ({
    rank: item.rank,
    fitness: item.fitness,
    profit: item.profit,
    sharpe: item.sharpe,
    drawdown: item.drawdown,
    parameters: item.genome as Record<string, string | number>,
  }));
}

export default function MockDashboardPage() {
  const { offlineData, requirementsGate, gaRunSummary } = sessionSummary;
  const [gaSession, setGaSession] = useState<GaSessionSummary | null>(null);

  useEffect(() => {
    let active = true;
    fetchGaSessionSummary().then((summary) => {
      if (active) {
        setGaSession(summary);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const inventoryForTable = toInventoryFiles(offlineData.inventory);
  const coverageMatrixForComponent = toComponentCoverageMatrix(
    offlineData.coverageMatrix,
    requirementsGate.requiredPairs,
    requirementsGate.requiredTimeframes,
  );
  const gateForPanel: GateResult = {
    ok: offlineData.status === 'pass',
    errors: offlineData.gateErrors.map(formatIssue),
    warnings: offlineData.gateWarnings.map(formatIssue),
    coverageMatrix: coverageMatrixForComponent,
  };
  const fitnessSeriesForChart: GenerationMetric[] = gaRunSummary.fitnessSeries.map((item) => ({
    generation: item.generation,
    bestFitness: item.bestFitness,
    avgFitness: item.averageFitness,
    worstFitness: Math.max(0, item.averageFitness - 18),
  }));
  const chartData = gaSession ? toFitnessChartData(gaSession) : fitnessSeriesForChart;
  const leaderboard = gaSession ? toResultCandidates(gaSession) : [];
  const topLeaderboardEntry = gaSession?.leaderboard[0] ?? null;

  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Mock Session</p>
        <h2>Session Summary Dashboard</h2>
        <p>
          Read-only mock data view for offline inventory, requirements gate status, and GA run health.
          No backend, exchange, or real backtest is called from this page.
        </p>
      </div>

      <div className="panel">
        <h3>Session Contract</h3>
        <div className="summary-grid">
          <span>Schema version: {sessionSummary.schemaVersion}</span>
          <span>Source: {sessionSummary.source}</span>
          <span>Generated at: {sessionSummary.generatedAt}</span>
          <span>GA source: {gaSession?.source ?? 'loading'}</span>
        </div>
      </div>

      <div className="status-grid">
        <div className="status-card status-card-warning">
          <span>Generation</span>
          <strong>{gaSession?.generation ?? gaRunSummary.generation}</strong>
          <small>latest mock generation</small>
        </div>
        <div className="status-card status-card-success">
          <span>Best fitness</span>
          <strong>{gaSession?.bestFitness ?? gaRunSummary.bestFitness}</strong>
          <small>mock session score</small>
        </div>
        <div className="status-card">
          <span>Population</span>
          <strong>{gaSession?.populationSize ?? gaRunSummary.populationSize}</strong>
          <small>individuals per generation</small>
        </div>
        <div className="status-card status-card-danger">
          <span>Missing datasets</span>
          <strong>{requirementsGate.missingCombinations.length}</strong>
          <small>required pair/timeframe gaps</small>
        </div>
      </div>

      <div className="status-grid">
        <GateResultPanel gate={gateForPanel} />
        <div className="panel">
          <h3>Requirements Gate</h3>
          <p>Status: {requirementsGate.status}</p>
          <p>Required pairs: {requirementsGate.requiredPairs.join(', ')}</p>
          <p>Required timeframes: {requirementsGate.requiredTimeframes.join(', ')}</p>
          <p>
            Missing combinations:{' '}
            {requirementsGate.missingCombinations.map(formatCombination).join(', ') || 'None'}
          </p>
        </div>
      </div>

      <div className="panel">
        <h3>GA Run Summary</h3>
        <div className="summary-grid">
          <span>Run ID: {gaRunSummary.runId}</span>
          <span>Artifact run ID: {gaSession?.runId ?? 'loading'}</span>
          <span>Status: {gaSession ? 'artifact-loaded' : gaRunSummary.status}</span>
          <span>Average fitness: {gaSession?.averageFitness ?? gaRunSummary.averageFitness}</span>
          <span>Diversity: {gaSession?.diversity ?? 'loading'}</span>
          <span>Mutation rate: {gaRunSummary.mutationRate}</span>
          <span>Crossover rate: {gaRunSummary.crossoverRate}</span>
          <span>Best genome: {gaRunSummary.bestGenomeId ?? 'unknown'}</span>
        </div>
      </div>

      <div className="panel">
        <FitnessChart data={chartData} />
      </div>

      <div className="panel">
        <h3>GA Leaderboard</h3>
        <p>Top genomes are loaded through the GA session adapter.</p>
      </div>
      {leaderboard.length > 0 ? <ResultsTable results={leaderboard} /> : <div className="panel">Loading leaderboard...</div>}

      <div className="panel">
        <h3>Risk Components</h3>
        <div className="summary-grid">
          <span>Max loss streak: {formatNullableNumber(topLeaderboardEntry?.maxLossStreak ?? null)}</span>
          <span>Leverage: {formatNullableNumber(topLeaderboardEntry?.leverage ?? null)}</span>
          <span>Risk per trade: {formatNullableNumber(topLeaderboardEntry?.riskPerTrade ?? null)}</span>
        </div>
        {topLeaderboardEntry && Object.keys(topLeaderboardEntry.fitnessComponents).length > 0 ? (
          <dl className="summary-grid">
            {Object.entries(topLeaderboardEntry.fitnessComponents).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p>Risk-aware fitness components are not available for this artifact.</p>
        )}
      </div>

      <div className="panel">
        <h3>Best Genome Detail</h3>
        <pre>{JSON.stringify(gaSession?.bestGenome ?? {}, null, 2)}</pre>
      </div>

      <div className="panel">
        <h3>Offline Data Inventory</h3>
        <div className="summary-grid">
          <span>Offline status: {offlineData.status}</span>
          <span>Inventory count: {offlineData.inventoryCount}</span>
          <span>Manifest dataset count: {offlineData.manifestDatasetCount}</span>
          <span>Gate error count: {offlineData.gateErrorCount}</span>
          <span>Gate warning count: {offlineData.gateWarningCount}</span>
        </div>
      </div>
      <InventoryTable files={inventoryForTable} />
      <CoverageMatrix matrix={coverageMatrixForComponent} />

      <div className="panel">
        <h3>Gate Errors</h3>
        <pre>{JSON.stringify(offlineData.gateErrors, null, 2)}</pre>
      </div>
    </section>
  );
}
