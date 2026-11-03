import { InputHTMLAttributes, ReactNode, forwardRef, useState } from 'react';

import { EyeIcon, EyeOffIcon } from './Icon';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  /** Ícone decorativo à esquerda do campo. */
  icon?: ReactNode;
  /** Texto de apoio abaixo do campo. */
  hint?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, id, className = '', icon, hint, type, ...props },
  ref,
) {
  const [revealed, setRevealed] = useState(false);
  const isPassword = type === 'password';
  const effectiveType = isPassword && revealed ? 'text' : type;
  const hintId = hint && id ? `${id}-hint` : undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-slate-700">
        {label}
      </label>
      <div className="relative">
        {icon && (
          <span className="pointer-events-none absolute inset-y-0 left-0 flex w-11 items-center justify-center text-slate-400 [&>svg]:h-[18px] [&>svg]:w-[18px]">
            {icon}
          </span>
        )}
        <input
          ref={ref}
          id={id}
          type={effectiveType}
          aria-describedby={hintId}
          className={`min-h-[44px] w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition-all placeholder:text-slate-400 hover:border-slate-400 focus:border-brand-500 focus:shadow-glow focus-visible:ring-0 ${
            icon ? 'pl-11' : ''
          } ${isPassword ? 'pr-11' : ''} ${className}`}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setRevealed((value) => !value)}
            aria-label="Alternar visibilidade do campo"
            aria-pressed={revealed}
            className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-lg text-slate-400 transition-colors hover:text-brand-600"
          >
            {revealed ? <EyeOffIcon className="h-[18px] w-[18px]" /> : <EyeIcon className="h-[18px] w-[18px]" />}
          </button>
        )}
      </div>
      {hint && (
        <p id={hintId} className="text-xs text-slate-500">
          {hint}
        </p>
      )}
    </div>
  );
});

export default Input;
