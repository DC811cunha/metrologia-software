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
    'bg-gradient-to-b from-brand-500 to-brand-600 text-white shadow-brand hover:from-brand-500 hover:to-brand-700 active:translate-y-px',
  secondary:
    'border border-slate-300 bg-white text-slate-700 shadow-sm hover:border-brand-300 hover:bg-brand-50 hover:text-brand-800 active:translate-y-px',
  danger:
    'border border-red-200 bg-white text-red-700 hover:border-red-300 hover:bg-red-50 active:translate-y-px',
  ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  inverse:
    'bg-white text-brand-800 shadow-sm hover:bg-brand-50 active:translate-y-px focus-visible:ring-offset-ink-900',
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
