import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { MetricSeriesPoint } from '../services/analysisService';

interface TrendChartProps {
  serie: MetricSeriesPoint[];
}

const AXIS_TICK = { fontSize: 12, fill: '#93a4c8' };

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
              <stop offset="5%" stopColor="#4d94ff" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#4d94ff" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2d55" vertical={false} />
          <XAxis dataKey="data" tick={AXIS_TICK} axisLine={false} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={40} />
          <Tooltip
            contentStyle={{
              borderRadius: 12,
              border: '1px solid rgba(56, 140, 255, 0.45)',
              background: '#0d1732',
              color: '#eaf0ff',
              boxShadow: '0 0 24px -6px rgba(56, 140, 255, 0.5)',
              fontSize: 13,
            }}
            labelStyle={{ color: '#93a4c8' }}
            itemStyle={{ color: '#eaf0ff' }}
            cursor={{ stroke: '#4d94ff', strokeOpacity: 0.5, strokeWidth: 1 }}
          />
          <Area
            type="monotone"
            dataKey="valor"
            name="Valor"
            stroke="#4d94ff"
            strokeWidth={3}
            fill="url(#trend-fill)"
            dot={{ r: 4, fill: '#0d1732', stroke: '#4d94ff', strokeWidth: 2 }}
            activeDot={{ r: 6, fill: '#4d94ff', stroke: '#ffffff', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default TrendChart;
