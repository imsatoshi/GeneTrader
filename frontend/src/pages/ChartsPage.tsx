import CandlestickChart from '../components/CandlestickChart';
import { mockCandles } from '../mocks/candles';

export default function ChartsPage() {
  return (
    <section className="page-stack">
      <div className="section-heading">
        <p className="eyebrow">Charts</p>
        <h2>BTC/USDT OHLCV mock view with Bollinger context.</h2>
      </div>
      <CandlestickChart candles={mockCandles} />
    </section>
  );
}
