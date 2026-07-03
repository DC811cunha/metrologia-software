import api from './api';

export interface Repository {
  id: string;
  url: string;
  owner_nome: string;
  linguagens_detectadas: string[];
  status_acesso: 'ativo' | 'inacessivel';
  criado_em: string;
  ultima_analise_status?: string | null;
  ultima_analise_id?: string | null;
}

export async function listRepositories(): Promise<Repository[]> {
  const response = await api.get<Repository[]>('/api/v1/repositories');
  return response.data;
}

export async function createRepository(url: string): Promise<Repository> {
  const response = await api.post<Repository>('/api/v1/repositories', { url });
  return response.data;
}

export async function deleteRepository(id: string): Promise<void> {
  await api.delete(`/api/v1/repositories/${id}`);
}
