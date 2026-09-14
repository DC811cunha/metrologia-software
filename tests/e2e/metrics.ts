/**
 * Rótulos das 6 métricas do catálogo, na mesma ordem/texto usado pelo dashboard
 * (`src/frontend/src/metricsCatalog.ts`). Mantido como uma cópia simples (em vez de
 * importar o módulo do frontend) para manter o pacote de testes E2E independente de
 * dependências de build do frontend (Vite/Recharts) — ver `data-model.md` para o
 * catálogo canônico (nome, unidade, fórmula, fonte bibliográfica).
 */
export const METRICS_GAUGE_LABELS = [
  'Complexidade Ciclomática',
  'Linhas de Código (LOC)',
  'Índice de Manutenibilidade',
  'Cobertura de Testes',
  'Acoplamento (Instabilidade)',
  'Score de Duplicação',
] as const;
