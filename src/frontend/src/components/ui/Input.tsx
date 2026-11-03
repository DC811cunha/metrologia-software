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
      <label htmlFor={id} className="text-sm font-medium text-fg-soft">
        {label}
      </label>
      <div className="relative">
        {icon && (
          <span className="pointer-events-none absolute inset-y-0 left-0 flex w-11 items-center justify-center text-fg-subtle [&>svg]:h-[18px] [&>svg]:w-[18px]">
            {icon}
          </span>
        )}
        <input
          ref={ref}
          id={id}
          type={effectiveType}
          aria-describedby={hintId}
          className={`min-h-[44px] w-full rounded-lg border border-line-strong bg-field px-3.5 py-2.5 text-sm text-fg outline-none transition-all placeholder:text-fg-subtle hover:border-brand-400/60 focus:border-brand-400 focus:shadow-glow focus-visible:ring-0 ${
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
            className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-lg text-fg-subtle transition-colors hover:text-brand-300"
          >
            {revealed ? <EyeOffIcon className="h-[18px] w-[18px]" /> : <EyeIcon className="h-[18px] w-[18px]" />}
          </button>
        )}
      </div>
      {hint && (
        <p id={hintId} className="text-xs text-fg-muted">
          {hint}
        </p>
      )}
    </div>
  );
});

export default Input;
