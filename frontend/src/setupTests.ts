import '@testing-library/jest-dom/vitest';
import React from 'react';
import { vi } from 'vitest';

vi.mock('echarts-for-react', () => ({
  default: ({ option }: { option?: { series?: unknown[] } }) =>
    React.createElement(
      'div',
      {
        'data-testid': 'fitness-chart',
        'data-series-count': option?.series?.length ?? 0,
      },
      'Fitness chart mock',
    ),
}));

HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
  clearRect: vi.fn(),
  fillRect: vi.fn(),
  measureText: vi.fn(() => ({ width: 80 })),
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  closePath: vi.fn(),
  stroke: vi.fn(),
  fill: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  translate: vi.fn(),
  scale: vi.fn(),
  rotate: vi.fn(),
  rect: vi.fn(),
  arc: vi.fn(),
  fillText: vi.fn(),
  strokeText: vi.fn(),
  setLineDash: vi.fn(),
  getLineDash: vi.fn(() => []),
  createLinearGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
  createRadialGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
  drawImage: vi.fn(),
})) as unknown as typeof HTMLCanvasElement.prototype.getContext;
