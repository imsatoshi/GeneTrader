import type { GateResult } from '../types/offlineData';

export default function GateResultPanel({ gate }: { gate: GateResult }) {
  return (
    <section className={`gate-panel ${gate.ok ? 'gate-ok' : 'gate-fail'}`}>
      <h3>Gate Result</h3>
      <strong>{gate.ok ? 'READY' : 'BLOCKED'}</strong>
      <p>{gate.ok ? 'Offline data can be used for mock-first readiness flows.' : 'Fix blocking data issues before evaluation.'}</p>
      <div className="gate-lists">
        <span>Errors: {gate.errors.length}</span>
        <span>Warnings: {gate.warnings.length}</span>
      </div>
    </section>
  );
}
