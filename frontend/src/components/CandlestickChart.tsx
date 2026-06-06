import { createChart, type IChartApi } from 'lightweight-charts';
import { useEffect, useRef } from 'react';
import type { MockCandle } from '../mocks/candles';

export default function CandlestickChart({ candles }: { candles: MockCandle[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }
    const chart: IChartApi = createChart(containerRef.current, {
      height: 360,
      layout: { background: { color: '#fffaf0' }, textColor: '#10211c' },
      grid: { vertLines: { color: '#eadfc8' }, horzLines: { color: '#eadfc8' } },
    });
    const candleSeries = (chart as unknown as {
      addCandlestickSeries: (options: Record<string, unknown>) => {
        setData: (data: Array<Record<string, string | number>>) => void;
      };
    }).addCandlestickSeries({
      upColor: '#28745d',
      downColor: '#a6402d',
      borderVisible: false,
      wickUpColor: '#28745d',
      wickDownColor: '#a6402d',
    });
    candleSeries.setData(
      candles.map((item) => ({
        time: item.time,
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
      })),
    );
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [candles]);

  return <div className="chart-frame" ref={containerRef} aria-label="Candlestick chart" />;
}
