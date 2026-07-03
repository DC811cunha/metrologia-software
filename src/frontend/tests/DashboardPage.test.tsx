import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import DashboardPage from '../src/pages/DashboardPage';
import { getAnalysis } from '../src/services/analysisService';
import { generateAndDownloadReport } from '../src/services/reportService';

jest.mock('../src/services/analysisService', () => ({
  getAnalysis: jest.fn(),
}));

jest.mock('../src/services/reportService', () => ({
  generateAndDownloadReport: jest.fn(),
}));

const COMPLETED_ANALYSIS = {
  id: 'analysis-1',
  repositorio_id: 'repo-1',
  status: 'concluida',
  motivo_falha: null,
  solicitada_em: '2026-06-01T00:00:00Z',
  concluida_em: '2026-06-01T00:00:05Z',
  status_conformidade_geral: 'Conforme',
  medicoes: [
    { metrica_chave: 'complexidade_ciclomatica', valor_medido: 5, status_conformidade: 'Conforme' },
    { metrica_chave: 'loc', valor_medido: 20, status_conformidade: 'Conforme' },
    { metrica_chave: 'indice_manutenibilidade', valor_medido: 80, status_conformidade: 'Conforme' },
    { metrica_chave: 'cobertura_testes', valor_medido: null, status_conformidade: 'Não disponível' },
    { metrica_chave: 'acoplamento', valor_medido: 0.3, status_conformidade: 'Conforme' },
    { metrica_chave: 'score_duplicacao', valor_medido: 2, status_conformidade: 'Conforme' },
  ],
};

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/repositories/repo-1/analyses/analysis-1']}>
      <Routes>
        <Route path="/repositories/:repositoryId/analyses/:analysisId" element={<DashboardPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('DashboardPage', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders the 6 gauges for a completed analysis', async () => {
    (getAnalysis as jest.Mock).mockResolvedValueOnce(COMPLETED_ANALYSIS);

    renderDashboard();

    await waitFor(() => expect(screen.getByText('Complexidade Ciclomática')).toBeInTheDocument());
    expect(screen.getByText('Linhas de Código (LOC)')).toBeInTheDocument();
    expect(screen.getByText('Índice de Manutenibilidade')).toBeInTheDocument();
    expect(screen.getByText('Cobertura de Testes')).toBeInTheDocument();
    expect(screen.getByText('Acoplamento (Instabilidade)')).toBeInTheDocument();
    expect(screen.getByText('Score de Duplicação')).toBeInTheDocument();
    expect(getAnalysis).toHaveBeenCalledWith('repo-1', 'analysis-1');
  });

  it('shows the overall conformity status', async () => {
    (getAnalysis as jest.Mock).mockResolvedValueOnce(COMPLETED_ANALYSIS);

    renderDashboard();

    await waitFor(() =>
      expect(screen.getByText(/Conformidade geral:/i).parentElement).toHaveTextContent(
        'Conformidade geral: Conforme',
      ),
    );
  });

  it('shows "Não disponível" for the coverage gauge when there is no artifact', async () => {
    (getAnalysis as jest.Mock).mockResolvedValueOnce(COMPLETED_ANALYSIS);

    renderDashboard();

    await waitFor(() => expect(screen.getAllByText('Não disponível').length).toBeGreaterThan(0));
  });

  it('shows a failure message when the analysis failed', async () => {
    (getAnalysis as jest.Mock).mockResolvedValueOnce({
      ...COMPLETED_ANALYSIS,
      status: 'falhou',
      motivo_falha: 'Repositório inacessível',
      medicoes: [],
    });

    renderDashboard();

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Análise falhou: Repositório inacessível'),
    );
  });

  it('shows an error message when the analysis cannot be loaded', async () => {
    (getAnalysis as jest.Mock).mockRejectedValueOnce(new Error('network error'));

    renderDashboard();

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível carregar a análise.'),
    );
  });

  it('generates and downloads the PDF report on button click', async () => {
    (getAnalysis as jest.Mock).mockResolvedValueOnce(COMPLETED_ANALYSIS);
    (generateAndDownloadReport as jest.Mock).mockResolvedValueOnce(undefined);

    renderDashboard();
    await waitFor(() => expect(screen.getByText('Complexidade Ciclomática')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /gerar relatório pdf/i }));

    await waitFor(() =>
      expect(generateAndDownloadReport).toHaveBeenCalledWith('repo-1', 'analise_unica', 'analysis-1'),
    );
  });

  it('shows an error message when report generation fails', async () => {
    (getAnalysis as jest.Mock).mockResolvedValueOnce(COMPLETED_ANALYSIS);
    (generateAndDownloadReport as jest.Mock).mockRejectedValueOnce(new Error('fail'));

    renderDashboard();
    await waitFor(() => expect(screen.getByText('Complexidade Ciclomática')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /gerar relatório pdf/i }));

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível gerar o relatório.'),
    );
  });
});
