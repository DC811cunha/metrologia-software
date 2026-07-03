import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AxiosError } from 'axios';

import RepositoriesPage from '../src/pages/RepositoriesPage';
import { triggerAnalysis } from '../src/services/analysisService';
import {
  createRepository,
  deleteRepository,
  listRepositories,
} from '../src/services/repositoryService';

jest.mock('../src/services/repositoryService', () => ({
  listRepositories: jest.fn(),
  createRepository: jest.fn(),
  deleteRepository: jest.fn(),
}));

jest.mock('../src/services/analysisService', () => ({
  triggerAnalysis: jest.fn(),
}));

function axiosErrorWithStatus(statusCode: number) {
  const error = new AxiosError('Request failed');
  error.response = { status: statusCode, data: {}, statusText: '', headers: {}, config: {} as never };
  return error;
}

const SAMPLE_REPOSITORY = {
  id: 'repo-1',
  url: 'https://github.com/octocat/Hello-World',
  owner_nome: 'octocat/Hello-World',
  linguagens_detectadas: ['python'],
  status_acesso: 'ativo' as const,
  criado_em: '2026-06-01T00:00:00Z',
  ultima_analise_status: null,
};

describe('RepositoriesPage', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('shows an empty state when there are no repositories', async () => {
    (listRepositories as jest.Mock).mockResolvedValueOnce([]);

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);

    await waitFor(() =>
      expect(screen.getByText('Nenhum repositório cadastrado ainda.')).toBeInTheDocument(),
    );
  });

  it('lists existing repositories with their detected languages', async () => {
    (listRepositories as jest.Mock).mockResolvedValueOnce([SAMPLE_REPOSITORY]);

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);

    await waitFor(() => expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument());
    expect(screen.getByText('python')).toBeInTheDocument();
  });

  it('registers a new repository and reloads the list', async () => {
    (listRepositories as jest.Mock)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([SAMPLE_REPOSITORY]);
    (createRepository as jest.Mock).mockResolvedValueOnce(SAMPLE_REPOSITORY);

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => expect(listRepositories).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByLabelText('URL do repositório GitHub'), {
      target: { value: 'https://github.com/octocat/Hello-World' },
    });
    fireEvent.click(screen.getByRole('button', { name: /cadastrar/i }));

    await waitFor(() =>
      expect(createRepository).toHaveBeenCalledWith('https://github.com/octocat/Hello-World'),
    );
    await waitFor(() => expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument());
  });

  it('shows a duplicate-repository message on 409', async () => {
    (listRepositories as jest.Mock).mockResolvedValueOnce([]);
    (createRepository as jest.Mock).mockRejectedValueOnce(axiosErrorWithStatus(409));

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => expect(listRepositories).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByLabelText('URL do repositório GitHub'), {
      target: { value: 'https://github.com/octocat/Hello-World' },
    });
    fireEvent.click(screen.getByRole('button', { name: /cadastrar/i }));

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Este repositório já está cadastrado.'),
    );
  });

  it('triggers an analysis and shows the resulting conformity status', async () => {
    (listRepositories as jest.Mock).mockResolvedValue([SAMPLE_REPOSITORY]);
    (triggerAnalysis as jest.Mock).mockResolvedValueOnce({
      id: 'analysis-1',
      repositorio_id: 'repo-1',
      status: 'concluida',
      motivo_falha: null,
      solicitada_em: '2026-06-01T00:00:00Z',
      concluida_em: '2026-06-01T00:00:05Z',
      status_conformidade_geral: 'Conforme',
      medicoes: [],
    });

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /executar análise/i }));

    await waitFor(() =>
      expect(screen.getByText(/conformidade geral: Conforme/i)).toBeInTheDocument(),
    );
  });

  it('removes a repository', async () => {
    (listRepositories as jest.Mock)
      .mockResolvedValueOnce([SAMPLE_REPOSITORY])
      .mockResolvedValueOnce([]);
    (deleteRepository as jest.Mock).mockResolvedValueOnce(undefined);

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /remover/i }));

    await waitFor(() => expect(deleteRepository).toHaveBeenCalledWith('repo-1'));
    await waitFor(() =>
      expect(screen.getByText('Nenhum repositório cadastrado ainda.')).toBeInTheDocument(),
    );
  });
});
