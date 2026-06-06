import ReactECharts from 'echarts-for-react';
import type { GenerationMetric } from '../types/ga';

export default function FitnessChart({ data }: { data: GenerationMetric[] }) {
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Best', 'Average', 'Worst'] },
    xAxis: { type: 'category', data: data.map((item) => `Gen ${item.generation}`) },
    yAxis: { type: 'value' },
    series: [
      { name: 'Best', type: 'line', smooth: true, data: data.map((item) => item.bestFitness) },
      { name: 'Average', type: 'line', smooth: true, data: data.map((item) => item.avgFitness) },
      { name: 'Worst', type: 'line', smooth: true, data: data.map((item) => item.worstFitness) },
    ],
  };

  return <ReactECharts option={option} style={{ height: 320 }} />;
}
