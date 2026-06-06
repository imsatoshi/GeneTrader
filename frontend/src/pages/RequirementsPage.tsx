import { useMemo, useState } from 'react';
import { z } from 'zod';
import CoverageMatrix from '../components/CoverageMatrix';
import { mockCoverageMatrix } from '../mocks/offlineData';

const requirementsSchema = z.object({
  pairs: z.array(z.string().regex(/^[A-Z0-9]+\/[A-Z0-9]+$/)).min(1),
  timeframes: z.array(z.string().regex(/^\d+[mhdw]$/)).min(1),
});

export default function RequirementsPage() {
  const [pairs, setPairs] = useState('BTC/USDT');
  const [timeframes, setTimeframes] = useState('15m,1h,4h');
  const requirements = useMemo(
    () => ({
      pairs: pairs.split(',').map((item) => item.trim()).filter(Boolean),
      timeframes: timeframes.split(',').map((item) => item.trim()).filter(Boolean),
    }),
    [pairs, timeframes],
  );
  const validation = requirementsSchema.safeParse(requirements);

  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Requirements</p>
        <h2>Edit offline pair and timeframe requirements.</h2>
      </div>
      <div className="editor-grid">
        <label>
          Pairs
          <input value={pairs} onChange={(event) => setPairs(event.target.value.toUpperCase())} />
        </label>
        <label>
          Timeframes
          <input value={timeframes} onChange={(event) => setTimeframes(event.target.value)} />
        </label>
      </div>
      {!validation.success ? <p className="error-text">Requirements format is invalid.</p> : null}
      <pre className="json-preview">{JSON.stringify(requirements, null, 2)}</pre>
      <CoverageMatrix matrix={mockCoverageMatrix} />
    </section>
  );
}
