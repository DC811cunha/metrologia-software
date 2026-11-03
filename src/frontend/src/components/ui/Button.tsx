import { ButtonHTMLAttributes, ReactNode } from 'react';

import { SpinnerIcon } from './Icon';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'inverse';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  /** Ícone decorativo exibido antes do rótulo. */
  icon?: ReactNode;
  /** Mostra um spinner no lugar do ícone (o rótulo continua sendo o texto acessível). */
  loading?: boolean;
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    'bg-gradient-to-b from-brand-500 to-brand-600 text-white shadow-brand hover:from-brand-400 hover:to-brand-600 hover:shadow-neon active:translate-y-px',
  secondary:
    'border border-line-strong bg-white/[0.04] text-fg-soft hover:border-brand-400/60 hover:bg-brand-500/10 hover:text-fg active:translate-y-px',
  danger:
    'border border-red-500/40 bg-red-500/5 text-red-300 hover:border-red-400/70 hover:bg-red-500/15 hover:text-red-200 active:translate-y-px',
  ghost: 'text-fg-soft hover:bg-white/10 hover:text-fg',
  inverse:
    'bg-white text-brand-800 shadow-sm hover:bg-brand-100 active:translate-y-px focus-visible:ring-offset-ink-900',
};

function Button({
  variant = 'primary',
  icon,
  loading = false,
  className = '',
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex min-h-[40px] items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    >
      {loading ? <SpinnerIcon /> : icon}
      {children}
    </button>
  );
}

export default Button;
