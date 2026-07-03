import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { MetricSeriesPoint } from '../services/analysisService';

interface TrendChartProps {
  serie: MetricSeriesPoint[];
}

function formatDate(value: string | null): string {
  if (!value) return '';
  return new Date(value).toLocaleDateString('pt-BR');
}

function TrendChart({ serie }: TrendChartProps) {
  const data = serie.map((point) => ({
    data: formatDate(point.concluida_em),
    valor: point.valor_medido,
  }));

  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <XAxis dataKey="data" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Line type="monotone" dataKey="valor" stroke="#0284c7" strokeWidth={2} dot />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default TrendChart;
