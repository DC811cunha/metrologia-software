import { HTMLAttributes } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Eleva o card ao passar o mouse — para itens clicáveis/de lista. */
  interactive?: boolean;
  /** Borda azul luminosa (neon) — para cards de destaque, como os gauges. */
  glow?: boolean;
}

function Card({ className = '', interactive = false, glow = false, ...props }: CardProps) {
  const edge = glow
    ? 'border-brand-500/40 shadow-neon hover:shadow-neon-hover hover:-translate-y-0.5 transition-all duration-300'
    : 'border-line shadow-card';
  const interactiveClasses = interactive
    ? 'transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-400/50 hover:shadow-card-hover'
    : '';
  return (
    <div
      className={`rounded-2xl border bg-gradient-to-b from-surface to-surface/80 p-6 ${edge} ${interactiveClasses} ${className}`}
      {...props}
    />
  );
}

export default Card;
