import { METRICS_GAUGE_CONFIG } from './metricsCatalog';
import { Measurement } from './services/analysisService';

/** Escore de cada status no índice geral — espelha `conformity_service.py` (RN01 do RFC). */
const SCORE_BY_STATUS: Record<string, number> = {
  Conforme: 100,
  Condicional: 50,
  'Não-Conforme': 0,
};

/**
 * Índice geral (0–100): média dos escores das métricas, todas com o mesmo peso. Métricas "Não
 * disponível" ficam de fora; sem nenhuma avaliável, não há índice.
 */
export function conformityIndex(medicoes: Measurement[]): number | null {
  const scores = medicoes
    .map((m) => SCORE_BY_STATUS[m.status_conformidade])
    .filter((score): score is number => score !== undefined);
  if (scores.length === 0) return null;
  return scores.reduce((sum, score) => sum + score, 0) / scores.length;
}

export function formatIndex(index: number): string {
  return index.toLocaleString('pt-BR', { maximumFractionDigits: 1 });
}

export interface AttentionMetric {
  label: string;
  status: string;
}

/** Métricas que não estão Conformes — as que puxam o índice geral para baixo. */
export function attentionMetrics(medicoes: Measurement[]): AttentionMetric[] {
  return METRICS_GAUGE_CONFIG.flatMap((config) => {
    const medicao = medicoes.find((m) => m.metrica_chave === config.chave);
    if (!medicao || (medicao.status_conformidade !== 'Condicional' && medicao.status_conformidade !== 'Não-Conforme')) {
      return [];
    }
    return [{ label: config.label, status: medicao.status_conformidade }];
  });
}
