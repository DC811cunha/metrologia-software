import { render, screen, waitFor } from '@testing-library/react';
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

    await waitFor(() => expect(screen.getByText('Condicional')).toBeInTheDocument());
    expect(screen.getByText('Conforme')).toBeInTheDocument();
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
