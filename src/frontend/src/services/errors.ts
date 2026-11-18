import { isAxiosError } from 'axios';

/** Mensagem em português devolvida pelo backend (`{"detail": "…"}`), ou null se não houver uma. */
export function serverDetail(err: unknown): string | null {
  if (isAxiosError(err) && typeof err.response?.data?.detail === 'string') {
    return err.response.data.detail;
  }
  return null;
}

/**
 * Mensagem de "muitas tentativas" (HTTP 429) vinda do servidor — ex.: "Muitas tentativas. Tente novamente
 * em 57 segundos." —, ou null para qualquer outro erro. Sem ela, o limite de requisições aparecia como
 * "credenciais inválidas" ou como uma falha genérica.
 */
export function tooManyRequestsMessage(err: unknown): string | null {
  return isAxiosError(err) && err.response?.status === 429 ? serverDetail(err) : null;
}
