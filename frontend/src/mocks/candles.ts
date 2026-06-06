export interface MockCandle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  upper: number;
  middle: number;
  lower: number;
}

export const mockCandles: MockCandle[] = [
  { time: '2026-05-01', open: 62000, high: 63300, low: 61200, close: 62800, upper: 64200, middle: 62100, lower: 60000 },
  { time: '2026-05-02', open: 62800, high: 65100, low: 62400, close: 64600, upper: 65400, middle: 62800, lower: 60200 },
  { time: '2026-05-03', open: 64600, high: 65200, low: 63100, close: 63800, upper: 66000, middle: 63300, lower: 60600 },
  { time: '2026-05-04', open: 63800, high: 66900, low: 63600, close: 66200, upper: 67200, middle: 64200, lower: 61200 },
  { time: '2026-05-05', open: 66200, high: 68100, low: 65500, close: 67400, upper: 68700, middle: 65100, lower: 61500 },
];
