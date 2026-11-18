import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AxiosError } from 'axios';

import RepositoriesPage from '../src/pages/RepositoriesPage';
import { AnalysisPollingTimeoutError, triggerAnalysis } from '../src/services/analysisService';
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
  ...jest.requireActual('../src/services/analysisService'),
  triggerAnalysis: jest.fn(),
}));

function axiosErrorWithDetail(statusCode: number, detail: string) {
  const error = new AxiosError('Request failed');
  error.response = {
    status: statusCode,
    data: { detail },
    statusText: '',
    headers: {},
    config: {} as never,
  };
  return error;
}

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

  it('shows the GitHub rate-limit message when registering a repository', async () => {
    (listRepositories as jest.Mock).mockResolvedValueOnce([]);
    (createRepository as jest.Mock).mockRejectedValueOnce(
      axiosErrorWithDetail(429, 'Limite de requisições do GitHub atingido. Tente novamente em cerca de 10 min.'),
    );

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => expect(listRepositories).toHaveBeenCalledTimes(1));
    fireEvent.change(screen.getByLabelText('URL do repositório GitHub'), {
      target: { value: 'https://github.com/octocat/Hello-World' },
    });
    fireEvent.click(screen.getByRole('button', { name: /cadastrar/i }));

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('cerca de 10 min'));
  });

  it.each([
    [429, 'Limite de requisições do GitHub atingido. Tente novamente em cerca de 30 min.'],
    [502, 'O GitHub está indisponível no momento. Tente novamente em instantes.'],
    [422, 'Repositório grande demais para análise (900 MB; máximo 195 MB)'],
    [503, 'Não foi possível enfileirar a análise agora. Tente novamente em instantes.'],
  ])('explains a %i failure when running an analysis', async (status, detail) => {
    (listRepositories as jest.Mock).mockResolvedValue([SAMPLE_REPOSITORY]);
    (triggerAnalysis as jest.Mock).mockRejectedValueOnce(axiosErrorWithDetail(status, detail));

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /executar análise/i }));

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(detail));
  });

  it('keeps the generic message for unexpected analysis errors', async () => {
    (listRepositories as jest.Mock).mockResolvedValue([SAMPLE_REPOSITORY]);
    (triggerAnalysis as jest.Mock).mockRejectedValueOnce(axiosErrorWithDetail(500, 'Traceback interno'));

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /executar análise/i }));

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível executar a análise.'),
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

  it('keeps the dashboard and history links after the latest attempt failed', async () => {
    // Regressão: a lista usava só a última tentativa; depois de uma falha (GitHub fora do ar, cota…) o link
    // do dashboard sumia, apesar de existirem análises concluídas.
    (listRepositories as jest.Mock).mockResolvedValueOnce([
      {
        ...SAMPLE_REPOSITORY,
        ultima_analise_status: 'falhou',
        ultima_analise_id: 'analysis-failed',
        ultima_concluida_id: 'analysis-ok',
        total_analises: 3,
      },
    ]);

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);

    const dashboard = await screen.findByRole('link', { name: 'Ver dashboard' });
    expect(dashboard).toHaveAttribute('href', '/repositories/repo-1/analyses/analysis-ok');
    expect(screen.getByRole('link', { name: 'Histórico' })).toHaveAttribute('href', '/repositories/repo-1/history');
    expect(screen.getByText('Falhou')).toBeInTheDocument();
  });

  it('shows no dashboard link when nothing ever completed', async () => {
    (listRepositories as jest.Mock).mockResolvedValueOnce([
      { ...SAMPLE_REPOSITORY, ultima_analise_status: 'falhou', ultima_analise_id: 'a', ultima_concluida_id: null },
    ]);

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);

    await screen.findByText('octocat/Hello-World');
    expect(screen.queryByRole('link', { name: 'Ver dashboard' })).not.toBeInTheDocument();
  });

  it('lets the user re-run the analysis of an inaccessible repository', async () => {
    // Regressão: o botão ficava desabilitado, mas o backend volta o repositório a "ativo" justamente na
    // próxima análise — o repositório ficava preso para sempre.
    (listRepositories as jest.Mock).mockResolvedValueOnce([{ ...SAMPLE_REPOSITORY, status_acesso: 'inacessivel' }]);

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);

    expect(await screen.findByRole('button', { name: /executar análise/i })).toBeEnabled();
    // O estado de acesso não é um status de conformidade: o selo diz "Inacessível", não "Não-Conforme".
    expect(screen.getByText('Inacessível')).toBeInTheDocument();
    expect(screen.queryByText('Não-Conforme')).not.toBeInTheDocument();
  });

  it('shows the exact reason from the server when registering fails with 422', async () => {
    (listRepositories as jest.Mock).mockResolvedValueOnce([]);
    (createRepository as jest.Mock).mockRejectedValueOnce(
      axiosErrorWithDetail(422, "Repositório 'octocat/Hello-World' não contém Python, JavaScript ou TypeScript"),
    );

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await waitFor(() => expect(listRepositories).toHaveBeenCalledTimes(1));
    fireEvent.change(screen.getByLabelText('URL do repositório GitHub'), {
      target: { value: 'https://github.com/octocat/Hello-World' },
    });
    fireEvent.click(screen.getByRole('button', { name: /cadastrar/i }));

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('não contém Python, JavaScript ou TypeScript'),
    );
  });

  it('does not swap the list for skeletons after an action (no flicker)', async () => {
    (listRepositories as jest.Mock).mockResolvedValue([SAMPLE_REPOSITORY]);
    (triggerAnalysis as jest.Mock).mockResolvedValueOnce({
      id: 'a',
      repositorio_id: 'repo-1',
      status: 'concluida',
      motivo_falha: null,
      solicitada_em: '',
      concluida_em: '',
      status_conformidade_geral: 'Conforme',
      medicoes: [],
    });

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await screen.findByText('octocat/Hello-World');
    fireEvent.click(screen.getByRole('button', { name: /executar análise/i }));

    await screen.findByText(/conformidade geral: Conforme/i);
    expect(screen.queryByText('Carregando repositórios…')).not.toBeInTheDocument();
    expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument();
  });

  it('explains that an analysis taking too long keeps running on the server', async () => {
    (listRepositories as jest.Mock).mockResolvedValue([SAMPLE_REPOSITORY]);
    (triggerAnalysis as jest.Mock).mockRejectedValueOnce(new AnalysisPollingTimeoutError());

    render(<MemoryRouter><RepositoriesPage /></MemoryRouter>);
    await screen.findByText('octocat/Hello-World');
    fireEvent.click(screen.getByRole('button', { name: /executar análise/i }));

    expect(await screen.findByText(/continua no servidor/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /executar análise/i })).toBeEnabled();
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
