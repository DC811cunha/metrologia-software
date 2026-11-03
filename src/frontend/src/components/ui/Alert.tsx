import { ReactNode } from 'react';

import { AlertCircleIcon, CheckCircleIcon, InfoIcon } from './Icon';

type Variant = 'error' | 'success' | 'info';

const VARIANT_CLASSES: Record<Variant, string> = {
  error: 'border-red-200 bg-red-50 text-red-800',
  success: 'border-conforme/30 bg-conforme-bg text-conforme-text',
  info: 'border-brand-200 bg-brand-50 text-brand-900',
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
