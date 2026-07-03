import api from './api';

export interface Measurement {
  metrica_chave: string;
  valor_medido: number | null;
  status_conformidade: string;
}

export interface Analysis {
  id: string;
  repositorio_id: string;
  status: 'pendente' | 'processando' | 'concluida' | 'falhou';
  motivo_falha: string | null;
  solicitada_em: string;
  concluida_em: string | null;
  status_conformidade_geral: string | null;
  medicoes: Measurement[];
}

const POLL_INTERVAL_MS = 2000;

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollUntilFinished(repositoryId: string, analysisId: string): Promise<Analysis> {
  for (;;) {
    await wait(POLL_INTERVAL_MS);
    const response = await api.get<Analysis>(
      `/api/v1/repositories/${repositoryId}/analyses/${analysisId}`,
    );
    if (response.data.status === 'concluida' || response.data.status === 'falhou') {
      return response.data;
    }
  }
}

/**
 * Dispara uma análise e, se o backend responder 202 (caminho assíncrono), faz polling
 * até a análise atingir um estado terminal (concluida | falhou).
 */
export async function triggerAnalysis(repositoryId: string): Promise<Analysis> {
  const response = await api.post<Analysis>(`/api/v1/repositories/${repositoryId}/analyses`);
  if (response.data.status === 'processando') {
    return pollUntilFinished(repositoryId, response.data.id);
  }
  return response.data;
}

export async function getAnalysis(repositoryId: string, analysisId: string): Promise<Analysis> {
  const response = await api.get<Analysis>(
    `/api/v1/repositories/${repositoryId}/analyses/${analysisId}`,
  );
  return response.data;
}

export interface AnalysisHistoryItem {
  id: string;
  concluida_em: string | null;
  status_conformidade_geral: string | null;
  medicoes: Measurement[];
}

export async function listAnalysesHistory(repositoryId: string): Promise<AnalysisHistoryItem[]> {
  const response = await api.get<AnalysisHistoryItem[]>(
    `/api/v1/repositories/${repositoryId}/analyses`,
  );
  return response.data;
}

export interface MetricSeriesPoint {
  analise_id: string;
  concluida_em: string | null;
  valor_medido: number | null;
  status_conformidade: string;
}

export interface MetricTrend {
  metrica_chave: string;
  tendencia: 'melhorando' | 'piorando' | 'estavel' | null;
  serie: MetricSeriesPoint[];
}

export async function getMetricTrend(repositoryId: string, metrica: string): Promise<MetricTrend> {
  const response = await api.get<MetricTrend>(`/api/v1/repositories/${repositoryId}/analyses`, {
    params: { metrica },
  });
  return response.data;
}
