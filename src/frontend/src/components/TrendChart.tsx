import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { MetricGaugeConfig } from '../metricsCatalog';
import { MetricSeriesPoint } from '../services/analysisService';

interface TrendChartProps {
  serie: MetricSeriesPoint[];
  /** Faixas de conformidade, escala e unidade da métrica exibida. */
  config: MetricGaugeConfig;
}

export const STATUS_COLORS: Record<string, string> = {
  Conforme: '#22c55e',
  Condicional: '#f59e0b',
  'Não-Conforme': '#ef4444',
  'Não disponível': '#94a3b8',
};

const LEGEND_STATUSES = ['Conforme', 'Condicional', 'Não-Conforme'];

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

function formatNumber(value: number): string {
  return value.toLocaleString('pt-BR', { maximumFractionDigits: 2 });
}

interface ChartPoint {
  data: string;
  valor: number | null;
  status: string;
}

interface DotProps {
  cx?: number;
  cy?: number;
  payload?: ChartPoint;
}

/** Ponto colorido pelo status de conformidade daquela análise. */
function StatusDot({ cx, cy, payload }: DotProps) {
  if (cx === undefined || cy === undefined || !payload || payload.valor === null) return <g />;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={5.5}
      fill={STATUS_COLORS[payload.status] ?? STATUS_COLORS['Não disponível']}
      stroke="#0d1732"
      strokeWidth={2.5}
    />
  );
}

function ActiveStatusDot({ cx, cy, payload }: DotProps) {
  if (cx === undefined || cy === undefined || !payload || payload.valor === null) return <g />;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={8}
      fill={STATUS_COLORS[payload.status] ?? STATUS_COLORS['Não disponível']}
      stroke="#ffffff"
      strokeWidth={2.5}
    />
  );
}

interface TooltipProps {
  active?: boolean;
  payload?: { payload: ChartPoint }[];
  unit: string;
}

function TrendTooltip({ active, payload, unit }: TooltipProps) {
  const point = payload?.[0]?.payload;
  if (!active || !point || point.valor === null) return null;
  return (
    <div className="rounded-xl border border-brand-500/45 bg-surface px-3.5 py-2.5 text-[13px] shadow-neon">
      <p className="text-fg-muted">{point.data}</p>
      <p className="mt-0.5 font-bold text-fg">
        {formatNumber(point.valor)} {unit}
      </p>
      <p className="mt-1 flex items-center gap-1.5 font-semibold" style={{ color: STATUS_COLORS[point.status] }}>
        <span
          aria-hidden="true"
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: STATUS_COLORS[point.status] }}
        />
        {point.status}
      </p>
    </div>
  );
}

function TrendChart({ serie, config }: TrendChartProps) {
  const data: ChartPoint[] = serie.map((point) => ({
    data: formatDate(point.concluida_em),
    valor: point.valor_medido,
    status: point.status_conformidade,
  }));

  const values = serie.map((point) => point.valor_medido).filter((value): value is number => value !== null);
  // A escala acompanha as faixas da métrica (para o status ficar legível), mas se algum valor
  // passar do máximo configurado o eixo cresce para ele continuar visível.
  const domainMax = Math.max(config.max, ...values);
  // Marcas do eixo Y nos limites das faixas: o eixo já mostra onde cada status começa.
  const yTicks = [...new Set([config.min, ...config.bands.map((band) => band.upTo), domainMax])].sort(
    (a, b) => a - b,
  );

  const last = [...serie].reverse().find((point) => point.valor_medido !== null);
  const summary = last
    ? `último valor ${formatNumber(last.valor_medido as number)} ${config.unidade}, ${last.status_conformidade}`.trim()
    : 'sem valores medidos';

  return (
    <div>
      <div
        role="img"
        aria-label={`Gráfico de tendência de ${config.label}: ${summary}`}
        className="h-[300px] w-full"
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 12, right: 16, bottom: 4, left: 0 }}>
            <defs>
              <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4d94ff" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#4d94ff" stopOpacity={0} />
              </linearGradient>
            </defs>

            {config.bands.map((band, index) => (
              <ReferenceArea
                key={`area-${band.upTo}`}
                y1={index === 0 ? config.min : config.bands[index - 1].upTo}
                y2={index === config.bands.length - 1 ? domainMax : band.upTo}
                fill={band.color}
                fillOpacity={0.1}
                stroke="none"
              />
            ))}
            {config.bands.slice(0, -1).map((band) => (
              <ReferenceLine
                key={`line-${band.upTo}`}
                y={band.upTo}
                stroke={band.color}
                strokeOpacity={0.45}
                strokeDasharray="5 5"
              />
            ))}

            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d55" vertical={false} />
            <XAxis dataKey="data" tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis
              domain={[config.min, domainMax]}
              ticks={yTicks}
              tick={AXIS_TICK}
              tickFormatter={formatNumber}
              axisLine={false}
              tickLine={false}
              width={44}
            />
            <Tooltip
              content={<TrendTooltip unit={config.unidade} />}
              cursor={{ stroke: '#4d94ff', strokeOpacity: 0.5, strokeWidth: 1 }}
            />
            <Area
              type="monotone"
              dataKey="valor"
              name="Valor"
              stroke="#4d94ff"
              strokeWidth={3}
              fill="url(#trend-fill)"
              dot={<StatusDot />}
              activeDot={<ActiveStatusDot />}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <ul
        aria-label="Legenda das faixas de conformidade"
        className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-fg-muted"
      >
        {LEGEND_STATUSES.map((status) => (
          <li key={status} className="inline-flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: STATUS_COLORS[status] }}
            />
            {status}
          </li>
        ))}
        <li className="text-fg-subtle">As faixas de cor ao fundo mostram os limites; cada ponto tem a cor do status daquela análise.</li>
      </ul>
    </div>
  );
}

export default TrendChart;
