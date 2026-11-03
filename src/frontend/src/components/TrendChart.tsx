import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { MetricSeriesPoint } from '../services/analysisService';

interface TrendChartProps {
  serie: MetricSeriesPoint[];
}

const AXIS_TICK = { fontSize: 12, fill: '#64748b' };

// Inclui a hora: várias análises no mesmo dia precisam de rótulos distintos no eixo X.
function formatDate(value: string | null): string {
  if (!value) return '';
  return new Date(value).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function TrendChart({ serie }: TrendChartProps) {
  const data = serie.map((point) => ({
    data: formatDate(point.concluida_em),
    valor: point.valor_medido,
  }));

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 12, right: 16, bottom: 4, left: 0 }}>
          <defs>
            <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3478f6" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#3478f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="data" tick={AXIS_TICK} axisLine={false} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={40} />
          <Tooltip
            contentStyle={{
              borderRadius: 12,
              border: '1px solid #e2e8f0',
              boxShadow: '0 8px 24px -8px rgba(15, 29, 71, 0.2)',
              fontSize: 13,
            }}
            cursor={{ stroke: '#bcd8ff', strokeWidth: 1 }}
          />
          <Area
            type="monotone"
            dataKey="valor"
            name="Valor"
            stroke="#1f5ae0"
            strokeWidth={3}
            fill="url(#trend-fill)"
            dot={{ r: 4, fill: '#ffffff', stroke: '#1f5ae0', strokeWidth: 2 }}
            activeDot={{ r: 6, fill: '#1f5ae0', stroke: '#ffffff', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default TrendChart;
