import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import HistoryPage from '../src/pages/HistoryPage';
import { getMetricTrend, listAnalysesHistory } from '../src/services/analysisService';

jest.mock('../src/services/analysisService', () => ({
  listAnalysesHistory: jest.fn(),
  getMetricTrend: jest.fn(),
}));

const HISTORY = [
  {
    id: 'analysis-1',
    concluida_em: '2026-06-01T00:00:00Z',
    status_conformidade_geral: 'Condicional',
    medicoes: [],
  },
  {
    id: 'analysis-2',
    concluida_em: '2026-06-15T00:00:00Z',
    status_conformidade_geral: 'Conforme',
    medicoes: [],
  },
];

const TREND = {
  metrica_chave: 'complexidade_ciclomatica',
  tendencia: 'melhorando' as const,
  serie: [
    { analise_id: 'analysis-1', concluida_em: '2026-06-01T00:00:00Z', valor_medido: 15, status_conformidade: 'Condicional' },
    { analise_id: 'analysis-2', concluida_em: '2026-06-15T00:00:00Z', valor_medido: 5, status_conformidade: 'Conforme' },
  ],
};

function renderHistoryPage() {
  return render(
    <MemoryRouter initialEntries={['/repositories/repo-1/history']}>
      <Routes>
        <Route path="/repositories/:repositoryId/history" element={<HistoryPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('HistoryPage', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('lists the chronological history of analyses', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce(HISTORY);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce(TREND);

    renderHistoryPage();

    const list = await screen.findByRole('list', { name: 'Histórico de análises' });
    expect(within(list).getByText('Condicional')).toBeInTheDocument();
    expect(within(list).getByText('Conforme')).toBeInTheDocument();
  });

  it('shows the current status of the metric next to the trend', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce(HISTORY);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce(TREND);

    renderHistoryPage();

    // O último ponto da série (valor 5) é Conforme: o usuário vê o status sem precisar ler o gráfico.
    await waitFor(() => expect(screen.getByText(/Situação atual:/)).toBeInTheDocument());
    expect(screen.getByText(/Situação atual:/).parentElement).toHaveTextContent('Situação atual:Conforme');
    expect(screen.getByText(/Tendência: Melhorando/i)).toBeInTheDocument();
  });

  it('explains the status colours of the chart with a text legend', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce(HISTORY);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce(TREND);

    renderHistoryPage();

    const legend = await screen.findByRole('list', { name: 'Legenda das faixas de conformidade' });
    expect(within(legend).getByText('Conforme')).toBeInTheDocument();
    expect(within(legend).getByText('Condicional')).toBeInTheDocument();
    expect(within(legend).getByText('Não-Conforme')).toBeInTheDocument();
  });

  it('describes the chart to screen readers with the latest value and status', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce(HISTORY);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce(TREND);

    renderHistoryPage();

    const chart = await screen.findByRole('img', { name: /Gráfico de tendência de Complexidade Ciclomática/ });
    expect(chart).toHaveAccessibleName(/último valor 5 cam\.\/função, Conforme/);
  });

  it('links back to the dashboard of the most recent completed analysis', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce(HISTORY);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce(TREND);

    renderHistoryPage();

    const back = await screen.findByRole('link', { name: /voltar ao dashboard/i });
    expect(back).toHaveAttribute('href', '/repositories/repo-1/analyses/analysis-2');
  });

  it('falls back to the repository list when there is no completed analysis yet', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce([]);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce({
      metrica_chave: 'complexidade_ciclomatica',
      tendencia: null,
      serie: [],
    });

    renderHistoryPage();

    const back = await screen.findByRole('link', { name: /repositórios/i });
    expect(back).toHaveAttribute('href', '/repositories');
    expect(screen.queryByRole('link', { name: /voltar ao dashboard/i })).not.toBeInTheDocument();
  });

  it('shows the trend label for the selected metric', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce(HISTORY);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce(TREND);

    renderHistoryPage();

    await waitFor(() => expect(screen.getByText(/Tendência: Melhorando/i)).toBeInTheDocument());
    expect(getMetricTrend).toHaveBeenCalledWith('repo-1', 'complexidade_ciclomatica');
  });

  it('shows insufficient-data message when the series has points but no measured values', async () => {
    // Regressão: cobertura_testes (ou qualquer métrica "Não disponível" em todas as
    // análises) retorna uma série não-vazia com valor_medido: null em cada ponto —
    // o gráfico não deve ser renderizado vazio nesse caso.
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce(HISTORY);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce({
      metrica_chave: 'cobertura_testes',
      tendencia: null,
      serie: [
        { analise_id: 'analysis-1', concluida_em: '2026-06-01T00:00:00Z', valor_medido: null, status_conformidade: 'Não disponível' },
        { analise_id: 'analysis-2', concluida_em: '2026-06-15T00:00:00Z', valor_medido: null, status_conformidade: 'Não disponível' },
      ],
    });

    renderHistoryPage();

    await waitFor(() =>
      expect(
        screen.getByText(/Sem dados suficientes para a tendência/i),
      ).toBeInTheDocument(),
    );
  });

  it('shows an empty state when there is no history', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce([]);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce({
      metrica_chave: 'complexidade_ciclomatica',
      tendencia: null,
      serie: [],
    });

    renderHistoryPage();

    await waitFor(() =>
      expect(screen.getByText('Nenhuma análise registrada ainda.')).toBeInTheDocument(),
    );
  });
});
