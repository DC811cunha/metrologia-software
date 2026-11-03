/** Placeholder pulsante usado enquanto os dados carregam (evita saltos de layout). */
function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-lg bg-white/10 ${className}`} />;
}

export default Skeleton;
