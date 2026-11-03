interface LogoProps {
  /** `light` para fundos escuros, `dark` para fundos claros. */
  tone?: 'light' | 'dark';
  className?: string;
}

/** Marca do SoftMeter: um medidor (gauge) estilizado + wordmark. */
function Logo({ tone = 'dark', className = '' }: LogoProps) {
  const wordmarkClass = tone === 'light' ? 'text-white' : 'text-fg';
  const accentClass = tone === 'light' ? 'text-brand-300' : 'text-brand-400';

  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <svg
        viewBox="0 0 64 64"
        className="h-9 w-9 drop-shadow-sm"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <linearGradient id="logo-gradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#589bff" />
            <stop offset="1" stopColor="#1a47b8" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill="url(#logo-gradient)" />
        <path
          d="M14 42a18 18 0 0 1 36 0"
          fill="none"
          stroke="#fff"
          strokeOpacity=".45"
          strokeWidth="5"
          strokeLinecap="round"
        />
        <path
          d="M14 42a18 18 0 0 1 24-17"
          fill="none"
          stroke="#fff"
          strokeWidth="5"
          strokeLinecap="round"
        />
        <path d="M32 42 42 28" stroke="#fff" strokeWidth="4" strokeLinecap="round" />
        <circle cx="32" cy="42" r="4.5" fill="#fff" />
      </svg>
      <span className={`text-xl font-extrabold tracking-tight ${wordmarkClass}`}>
        Soft<span className={accentClass}>Meter</span>
      </span>
    </span>
  );
}

export default Logo;
