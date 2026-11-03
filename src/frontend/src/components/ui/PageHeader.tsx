import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  /** Texto curto acima do título (contexto/seção). */
  eyebrow?: string;
  /** Slot acima do eyebrow — ex.: link de voltar. */
  back?: ReactNode;
  /** Ações alinhadas à direita em telas largas. */
  actions?: ReactNode;
}

function PageHeader({ title, description, eyebrow, back, actions }: PageHeaderProps) {
  return (
    <div className="flex animate-fade-up flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex flex-col gap-1.5">
        {back}
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand-600">{eyebrow}</p>
        )}
        <h1 className="text-3xl font-extrabold text-ink-900">{title}</h1>
        {description && <p className="max-w-2xl text-sm leading-relaxed text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
    </div>
  );
}

export default PageHeader;
