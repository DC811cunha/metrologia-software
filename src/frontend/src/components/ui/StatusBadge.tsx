const STATUS_BADGE_CLASSES: Record<string, string> = {
  Conforme: 'bg-conforme-bg text-conforme-text',
  Condicional: 'bg-condicional-bg text-condicional-text',
  'Não-Conforme': 'bg-nao-conforme-bg text-nao-conforme-text',
  'Não disponível': 'bg-nao-disponivel-bg text-nao-disponivel-text',
  concluida: 'bg-conforme-bg text-conforme-text',
  processando: 'bg-brand-100 text-brand-800',
  falhou: 'bg-nao-conforme-bg text-nao-conforme-text',
};

/** Selo de status com ponto colorido — a cor nunca é o único indicador (o texto sempre aparece). */
function StatusBadge({ label }: { label: string }) {
  const classes = STATUS_BADGE_CLASSES[label] ?? 'bg-slate-100 text-slate-600';
  return (
    <span
      className={`status-dot inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${classes}`}
    >
      {label}
    </span>
  );
}

export default StatusBadge;
