export default function SettingsPage() {
  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Settings</p>
        <h2>Runtime boundaries</h2>
      </div>
      <div className="panel">
        <p>This frontend is mock-first and offline by default.</p>
        <ul>
          <li>No exchange connection.</li>
          <li>No API keys or secrets.</li>
          <li>No real backtest execution from the browser.</li>
        </ul>
      </div>
    </section>
  );
}
