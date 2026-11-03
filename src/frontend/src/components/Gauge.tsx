import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts';

export interface GaugeBand {
  /** Limite superior desta faixa, no domínio [min, max] do gauge. */
  upTo: number;
  color: string;
}

export interface GaugeProps {
  label: string;
  value: number | null;
  unit: string;
  min: number;
  max: number;
  bands: GaugeBand[];
  statusLabel: string;
}

const STATUS_BADGE_CLASSES: Record<string, string> = {
  Conforme: 'bg-conforme-bg text-conforme-text',
  Condicional: 'bg-condicional-bg text-condicional-text',
  'Não-Conforme': 'bg-nao-conforme-bg text-nao-conforme-text',
  'Não disponível': 'bg-nao-disponivel-bg text-nao-disponivel-text',
};

const STATUS_ACCENT_CLASSES: Record<string, string> = {
  Conforme: 'border-t-conforme',
  Condicional: 'border-t-condicional',
  'Não-Conforme': 'border-t-nao-conforme',
  'Não disponível': 'border-t-slate-300',
};

function formatValue(value: number): string {
  return value.toLocaleString('pt-BR', { maximumFractionDigits: 2 });
}

function needleAngleDeg(value: number, min: number, max: number): number {
  const fraction = max > min ? (value - min) / (max - min) : 0;
  const clamped = Math.min(1, Math.max(0, fraction));
  return -90 + clamped * 180;
}

function Gauge({ label, value, unit, min, max, bands, statusLabel }: GaugeProps) {
  const segments = bands.map((band, index) => ({
    name: band.color,
    value: band.upTo - (index === 0 ? min : bands[index - 1].upTo),
    color: band.color,
  }));

  return (
    <div
      data-testid="gauge-card"
      className={`flex flex-col items-center rounded-2xl border border-t-[3px] border-slate-200/80 bg-white p-5 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover ${
        STATUS_ACCENT_CLASSES[statusLabel] ?? 'border-t-slate-300'
      }`}
    >
      <span className="text-center text-sm font-semibold text-slate-700">{label}</span>

      <div className="relative mt-3 h-[142px] w-[210px] overflow-hidden">
        <ResponsiveContainer width="100%" height={248}>
          <PieChart>
            <Pie
              data={segments}
              dataKey="value"
              startAngle={180}
              endAngle={0}
              cx="50%"
              cy={116}
              innerRadius={68}
              outerRadius={98}
              paddingAngle={2}
              cornerRadius={4}
              stroke="none"
              isAnimationActive={false}
            >
              {segments.map((segment) => (
                <Cell key={segment.name} fill={segment.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        <span aria-hidden="true" className="absolute bottom-0 left-1 w-9 text-center text-[11px] font-medium tabular-nums text-slate-400">
          {formatValue(min)}
        </span>
        <span aria-hidden="true" className="absolute bottom-0 right-1 w-9 text-center text-[11px] font-medium tabular-nums text-slate-400">
          {formatValue(max)}
        </span>

        {value !== null && (
          <>
            <div
              data-testid="gauge-needle"
              className="absolute bottom-[26px] left-1/2 h-[86px] w-[3px] origin-bottom animate-needle-sweep rounded-full bg-ink-900"
              style={{ transform: `translateX(-50%) rotate(${needleAngleDeg(value, min, max)}deg)` }}
            />
            <div
              aria-hidden="true"
              className="absolute bottom-[18px] left-1/2 h-4 w-4 -translate-x-1/2 rounded-full border-[3px] border-white bg-ink-900 shadow"
            />
          </>
        )}
      </div>

      <span
        className={`mt-2 tabular-nums ${
          value !== null ? 'text-2xl font-extrabold text-ink-900' : 'text-base font-semibold text-slate-400'
        }`}
      >
        {value !== null ? `${formatValue(value)} ${unit}`.trim() : 'Não disponível'}
      </span>
      <span
        className={`status-dot mt-2 inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
          STATUS_BADGE_CLASSES[statusLabel] ?? 'bg-slate-100 text-slate-600'
        }`}
      >
        {statusLabel}
      </span>
    </div>
  );
}

export default Gauge;
