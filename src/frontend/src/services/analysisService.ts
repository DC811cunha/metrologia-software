import { isAxiosError } from 'axios';

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

export const POLL_INTERVAL_MS = 2000;
/** Quanto tempo a tela espera por uma análise assíncrona antes de desistir de acompanhar. */
export const POLL_TIMEOUT_MS = 10 * 60 * 1000;
/** Falhas de rede seguidas toleradas durante o polling antes de desistir. */
const MAX_CONSECUTIVE_POLL_FAILURES = 3;

/** A tela parou de esperar (tempo esgotado), mas a análise continua no servidor. */
export class AnalysisPollingTimeoutError extends Error {
  constructor() {
    super('A análise está demorando mais que o esperado.');
    this.name = 'AnalysisPollingTimeoutError';
  }
}

export function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === 'AbortError';
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Cancelado', 'AbortError'));
      return;
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    function onAbort() {
      clearTimeout(timer);
      reject(new DOMException('Cancelado', 'AbortError'));
    }
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

/**
 * Acompanha uma análise até o estado final. Antes era um laço infinito: uma análise presa no servidor
 * deixava a tela girando para sempre e continuava consultando a API depois de sair da página. Agora há um
 * tempo máximo, o `signal` cancela ao sair da tela e algumas falhas de rede seguidas são toleradas.
 */
async function pollUntilFinished(
  repositoryId: string,
  analysisId: string,
  signal?: AbortSignal,
): Promise<Analysis> {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  let failures = 0;
  while (Date.now() < deadline) {
    await wait(POLL_INTERVAL_MS, signal);
    try {
      const response = await api.get<Analysis>(
        `/api/v1/repositories/${repositoryId}/analyses/${analysisId}`,
        { signal },
      );
      failures = 0;
      if (response.data.status === 'concluida' || response.data.status === 'falhou') {
        return response.data;
      }
    } catch (err) {
      if (isAbortError(err) || (isAxiosError(err) && err.response?.status === 404)) throw err;
      failures += 1;
      if (failures >= MAX_CONSECUTIVE_POLL_FAILURES) throw err;
    }
  }
  throw new AnalysisPollingTimeoutError();
}

/**
 * Dispara uma análise e, se o backend responder 202 (caminho assíncrono), faz polling
 * até a análise atingir um estado terminal (concluida | falhou).
 */
export async function triggerAnalysis(repositoryId: string, signal?: AbortSignal): Promise<Analysis> {
  const response = await api.post<Analysis>(`/api/v1/repositories/${repositoryId}/analyses`);
  if (response.data.status === 'processando') {
    return pollUntilFinished(repositoryId, response.data.id, signal);
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
  status: 'pendente' | 'processando' | 'concluida' | 'falhou';
  motivo_falha: string | null;
  solicitada_em: string;
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
