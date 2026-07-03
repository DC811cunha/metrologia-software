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

const STATUS_TEXT_CLASSES: Record<string, string> = {
  Conforme: 'text-conforme-text',
  Condicional: 'text-condicional-text',
  'Não-Conforme': 'text-nao-conforme-text',
  'Não disponível': 'text-nao-disponivel-text',
};

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
    <div className="flex flex-col items-center rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <span className="text-sm font-medium text-slate-700">{label}</span>

      <div className="relative h-[100px] w-[180px] overflow-hidden">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={segments}
              dataKey="value"
              startAngle={180}
              endAngle={0}
              cx="50%"
              cy={100}
              innerRadius={55}
              outerRadius={85}
              stroke="none"
              isAnimationActive={false}
            >
              {segments.map((segment) => (
                <Cell key={segment.name} fill={segment.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {value !== null && (
          <div
            data-testid="gauge-needle"
            className="absolute bottom-0 left-1/2 h-[70px] w-0.5 origin-bottom bg-slate-800"
            style={{ transform: `translateX(-50%) rotate(${needleAngleDeg(value, min, max)}deg)` }}
          />
        )}
      </div>

      <span className="text-lg font-semibold text-slate-900">
        {value !== null ? `${value} ${unit}` : 'Não disponível'}
      </span>
      <span className={`text-sm font-medium ${STATUS_TEXT_CLASSES[statusLabel] ?? 'text-slate-500'}`}>
        {statusLabel}
      </span>
    </div>
  );
}

export default Gauge;
