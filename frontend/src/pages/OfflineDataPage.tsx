import CoverageMatrix from '../components/CoverageMatrix';
import GateResultPanel from '../components/GateResultPanel';
import InventoryTable from '../components/InventoryTable';
import ManifestTable from '../components/ManifestTable';
import { mockCoverageMatrix, mockGateResult, mockInventoryFiles, mockInventorySummary } from '../mocks/offlineData';

export default function OfflineDataPage() {
  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Offline Data</p>
        <h2>Inventory, manifest, coverage, and gate state.</h2>
      </div>
      <div className="status-grid">
        <GateResultPanel gate={mockGateResult} />
        <div className="panel">
          <h3>Inventory summary</h3>
          <p>{mockInventorySummary.fileCount} files, {mockInventorySummary.totalSizeBytes.toLocaleString()} bytes</p>
          <p>{mockInventorySummary.pairs.join(', ')} across {mockInventorySummary.timeframes.join(', ')}</p>
        </div>
      </div>
      <InventoryTable files={mockInventoryFiles} />
      <ManifestTable files={mockInventoryFiles} />
      <CoverageMatrix matrix={mockCoverageMatrix} />
    </section>
  );
}
