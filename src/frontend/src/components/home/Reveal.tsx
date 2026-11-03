import { ReactNode, useEffect, useRef, useState } from 'react';

interface RevealProps {
  children: ReactNode;
  className?: string;
  /** Atraso (ms) para escalonar itens de uma mesma seção. */
  delay?: number;
}

/**
 * Revela o conteúdo com um fade-up ao entrar na viewport. Sem IntersectionObserver
 * (testes, navegadores antigos) o conteúdo já nasce visível — nunca fica oculto.
 */
function Reveal({ children, className = '', delay = 0 }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const supportsObserver = typeof IntersectionObserver !== 'undefined';
  const [visible, setVisible] = useState(!supportsObserver);

  useEffect(() => {
    if (!supportsObserver || visible || !ref.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.12 },
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [supportsObserver, visible]);

  return (
    <div
      ref={ref}
      style={{ animationDelay: `${delay}ms` }}
      className={`${visible ? 'animate-fade-up' : 'opacity-0'} ${className}`}
    >
      {children}
    </div>
  );
}

export default Reveal;
