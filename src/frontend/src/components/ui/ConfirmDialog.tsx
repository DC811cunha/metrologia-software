import { KeyboardEvent, MouseEvent, ReactNode, useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';

import Button from './Button';
import { AlertCircleIcon, TrashIcon } from './Icon';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  /** Explicação do que a confirmação causa. */
  children: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  /** Enquanto a ação confirmada executa: bloqueia os botões, o Esc e o clique no fundo. */
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled])';

type DialogContentProps = Omit<ConfirmDialogProps, 'open'>;

function DialogContent({
  title,
  children,
  confirmLabel,
  cancelLabel = 'Cancelar',
  loading = false,
  onConfirm,
  onCancel,
}: DialogContentProps) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    // O foco inicial vai para a ação segura: Enter acidental nunca confirma uma exclusão.
    cancelRef.current?.focus();

    return () => {
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, []);

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.stopPropagation();
      if (!loading) onCancel();
      return;
    }
    if (event.key !== 'Tab' || !dialogRef.current) return;

    // Mantém o foco dentro do diálogo (WCAG 2.4.3): Tab/Shift+Tab dão a volta.
    const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function handleBackdropClick(event: MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget && !loading) onCancel();
  }

  return (
    <div
      onMouseDown={handleBackdropClick}
      onKeyDown={handleKeyDown}
      className="fixed inset-0 z-[60] flex animate-fade-in items-center justify-center overflow-y-auto bg-canvas/80 px-4 py-6 backdrop-blur-sm"
    >
      <div
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className="w-full max-w-md animate-fade-up rounded-3xl border border-red-500/30 bg-gradient-to-b from-surface to-surface/90 p-6 shadow-[0_0_0_1px_rgb(239_68_68/0.25),0_24px_64px_-12px_rgb(0_0_0/0.8)] sm:p-7"
      >
        <div className="flex items-start gap-4">
          <span
            aria-hidden="true"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-red-500/15 text-red-300 ring-1 ring-inset ring-red-400/30"
          >
            <AlertCircleIcon className="h-6 w-6" />
          </span>
          <div className="min-w-0">
            <h2 id={titleId} className="text-lg font-extrabold text-fg">
              {title}
            </h2>
            <div id={descriptionId} className="mt-2 space-y-2 text-sm leading-relaxed text-fg-muted">
              {children}
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button ref={cancelRef} variant="secondary" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant="destructive"
            icon={<TrashIcon className="h-4 w-4" />}
            loading={loading}
            disabled={loading}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * Janela secundária (modal) de confirmação para ações destrutivas. Renderizada em um portal sobre a
 * página, com foco preso, Esc para cancelar e retorno do foco ao elemento que a abriu.
 */
function ConfirmDialog({ open, ...props }: ConfirmDialogProps) {
  if (!open) return null;
  return createPortal(<DialogContent {...props} />, document.body);
}

export default ConfirmDialog;
