import { HTMLAttributes } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Eleva o card ao passar o mouse — para itens clicáveis/de lista. */
  interactive?: boolean;
}

function Card({ className = '', interactive = false, ...props }: CardProps) {
  const interactiveClasses = interactive
    ? 'transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-card-hover'
    : '';
  return (
    <div
      className={`rounded-2xl border border-slate-200/80 bg-white p-6 shadow-card ${interactiveClasses} ${className}`}
      {...props}
    />
  );
}

export default Card;
