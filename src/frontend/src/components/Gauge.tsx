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
      className="flex flex-col items-center rounded-2xl border border-brand-500/40 bg-gradient-to-b from-surface to-canvas/60 p-5 shadow-neon transition-all duration-300 hover:-translate-y-0.5 hover:border-brand-400/80 hover:shadow-neon-hover"
    >
      <span className="text-center text-sm font-semibold text-fg">{label}</span>

      <div className="relative mt-3 h-[142px] w-[210px] overflow-hidden [filter:drop-shadow(0_0_10px_rgb(56_140_255/0.18))]">
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

        <span aria-hidden="true" className="absolute bottom-0 left-1 w-9 text-center text-[11px] font-medium tabular-nums text-fg-subtle">
          {formatValue(min)}
        </span>
        <span aria-hidden="true" className="absolute bottom-0 right-1 w-9 text-center text-[11px] font-medium tabular-nums text-fg-subtle">
          {formatValue(max)}
        </span>

        {value !== null && (
          <>
            <div
              data-testid="gauge-needle"
              className="absolute bottom-[26px] left-1/2 h-[86px] w-[3px] origin-bottom animate-needle-sweep rounded-full bg-white shadow-[0_0_10px_rgb(255_255_255/0.55)]"
              style={{ transform: `translateX(-50%) rotate(${needleAngleDeg(value, min, max)}deg)` }}
            />
            <div
              aria-hidden="true"
              className="absolute bottom-[18px] left-1/2 h-4 w-4 -translate-x-1/2 rounded-full border-[3px] border-brand-500 bg-white shadow-[0_0_12px_rgb(56_140_255/0.8)]"
            />
          </>
        )}
      </div>

      <span
        className={`mt-2 tabular-nums ${
          value !== null ? 'text-2xl font-extrabold text-fg' : 'text-base font-semibold text-fg-subtle'
        }`}
      >
        {value !== null ? `${formatValue(value)} ${unit}`.trim() : 'Não disponível'}
      </span>
      <span
        className={`status-dot mt-2 inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
          STATUS_BADGE_CLASSES[statusLabel] ?? 'bg-white/10 text-fg-soft'
        }`}
      >
        {statusLabel}
      </span>
    </div>
  );
}

export default Gauge;
