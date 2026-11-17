import { InfoIcon } from './ui/Icon';

/**
 * Explica como o índice geral é calculado — sem isso, o selo "Condicional" ao lado de métricas
 * Conformes parece uma contradição. Bloco recolhível (`details`), acessível por teclado.
 */
function ConformityIndexNote() {
  return (
    <details
      data-testid="index-note"
      className="group rounded-xl border border-line bg-white/[0.03] px-3.5 py-2.5 text-xs leading-relaxed text-fg-muted"
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 font-semibold text-fg-soft">
        <InfoIcon className="h-4 w-4 shrink-0 text-brand-400" />
        Como o índice geral é calculado?
        <span aria-hidden="true" className="ml-auto text-fg-subtle transition-transform group-open:rotate-180">
          ▾
        </span>
      </summary>
      <div className="mt-2 space-y-2 pl-6">
        <p>
          O índice geral é a <strong className="text-fg-soft">média dos escores das métricas</strong>: Conforme vale
          100, Condicional vale 50 e Não-Conforme vale 0. Todas as métricas têm o mesmo peso, e as que aparecem como
          &quot;Não disponível&quot; ficam de fora da conta.
        </p>
        <p>
          <strong className="text-fg-soft">Conforme:</strong> índice a partir de 90 ·{' '}
          <strong className="text-fg-soft">Condicional:</strong> de 70 a 89 ·{' '}
          <strong className="text-fg-soft">Não-Conforme:</strong> abaixo de 70.
        </p>
        <p>
          Por isso o índice geral pode diferir do status de uma métrica isolada: com 6 métricas, uma única
          Não-Conforme já tira 16,7 pontos e basta para o geral ficar Condicional, mesmo com todas as outras
          Conformes.
        </p>
      </div>
    </details>
  );
}

export default ConformityIndexNote;
