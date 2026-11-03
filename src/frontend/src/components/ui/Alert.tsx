import { ReactNode } from 'react';

import { AlertCircleIcon, CheckCircleIcon, InfoIcon } from './Icon';

type Variant = 'error' | 'success' | 'info';

const VARIANT_CLASSES: Record<Variant, string> = {
  error: 'border-red-500/30 bg-red-500/10 text-red-200',
  success: 'border-conforme/30 bg-conforme-bg text-conforme-text',
  info: 'border-brand-400/30 bg-brand-500/10 text-brand-200',
};

const VARIANT_ICONS: Record<Variant, typeof InfoIcon> = {
  error: AlertCircleIcon,
  success: CheckCircleIcon,
  info: InfoIcon,
};

function Alert({ variant = 'error', children }: { variant?: Variant; children: ReactNode }) {
  const Icon = VARIANT_ICONS[variant];
  return (
    <p
      role="alert"
      className={`flex animate-fade-in items-start gap-2.5 rounded-xl border px-3.5 py-3 text-sm leading-snug ${VARIANT_CLASSES[variant]}`}
    >
      <Icon className="mt-px h-[18px] w-[18px] shrink-0" />
      <span>{children}</span>
    </p>
  );
}

export default Alert;
