import { ReactNode } from 'react';

type Variant = 'error' | 'success' | 'info';

const VARIANT_CLASSES: Record<Variant, string> = {
  error: 'bg-red-50 text-red-800 border-red-200',
  success: 'bg-conforme-bg text-conforme-text border-conforme/30',
  info: 'bg-sky-50 text-sky-800 border-sky-200',
};

function Alert({ variant = 'error', children }: { variant?: Variant; children: ReactNode }) {
  return (
    <p role="alert" className={`rounded-md border px-3 py-2 text-sm ${VARIANT_CLASSES[variant]}`}>
      {children}
    </p>
  );
}

export default Alert;
