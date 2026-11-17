import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import HistoryPage from '../src/pages/HistoryPage';
import { getMetricTrend, listAnalysesHistory } from '../src/services/analysisService';

jest.mock('../src/services/analysisService', () => ({
  listAnalysesHistory: jest.fn(),
  getMetricTrend: jest.fn(),
}));

const KEYS = [
  'complexidade_ciclomatica',
  'loc',
  'indice_manutenibilidade',
  'cobertura_testes',
  'acoplamento',
  'score_duplicacao',
];

/** 6 medições: `cc` para a Complexidade Ciclomática, `others` para as demais (a última é a Duplicação). */
function medicoes(cc: [number, string], others: string[]) {
  return [
    { metrica_chave: KEYS[0], valor_medido: cc[0], status_conformidade: cc[1] },
    ...others.map((status, i) => ({ metrica_chave: KEYS[i + 1], valor_medido: 1, status_conformidade: status })),
  ];
}

const HISTORY = [
  {
    id: 'analysis-1',
    status: 'concluida' as const,
    motivo_falha: null,
    solicitada_em: '2026-06-01T00:00:00Z',
    concluida_em: '2026-06-01T00:00:00Z',
    status_conformidade_geral: 'Condicional',
    // 4 Conformes + 2 Condicionais = (400 + 100) / 6 = 83,3 → Condicional
    medicoes: medicoes([15, 'Condicional'], ['Conforme', 'Conforme', 'Conforme', 'Condicional', 'Conforme']),
  },
  {
    id: 'analysis-2',
    status: 'concluida' as const,
    motivo_falha: null,
    solicitada_em: '2026-06-15T00:00:00Z',
    concluida_em: '2026-06-15T00:00:00Z',
    // O índice geral agrega as 6 métricas: pode ser Condicional mesmo com esta métrica Conforme.
    status_conformidade_geral: 'Condicional',
    medicoes: medicoes([5, 'Conforme'], ['Conforme', 'Conforme', 'Conforme', 'Conforme', 'Não-Conforme']),
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
    expect(within(list).getAllByText('Índice geral')).toHaveLength(2);
  });

  it('separates the overall index from the status of the selected metric in each row', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce(HISTORY);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce(TREND);

    renderHistoryPage();

    // Regressão: a linha mostrava só o índice geral ("Condicional") enquanto o gráfico, da métrica
    // selecionada, mostrava "Conforme" — parecia contradição. Agora cada linha rotula os dois.
    const list = await screen.findByRole('list', { name: 'Histórico de análises' });
    const secondRow = within(list).getAllByText('Índice geral')[1].closest('[class*="rounded-2xl"]') as HTMLElement;
    expect(within(secondRow).getByText('Índice geral').parentElement).toHaveTextContent('Índice geral83,3Condicional');
    expect(within(secondRow).getByText('Complexidade Ciclomática').parentElement).toHaveTextContent('5');
    expect(within(secondRow).getByText('Complexidade Ciclomática').parentElement).toHaveTextContent('Conforme');
  });

  it('says which metrics hold the overall index down in each analysis', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce(HISTORY);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce(TREND);

    renderHistoryPage();

    const list = await screen.findByRole('list', { name: 'Histórico de análises' });
    expect(within(list).getByText(/Pontos de atenção: Score de Duplicação \(Não-Conforme\)/)).toBeInTheDocument();
    expect(
      within(list).getByText(/Pontos de atenção: Complexidade Ciclomática \(Condicional\), Acoplamento \(Instabilidade\) \(Condicional\)/),
    ).toBeInTheDocument();
  });

  it('explains how the overall index is calculated', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce(HISTORY);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce(TREND);

    renderHistoryPage();

    const note = await screen.findByTestId('index-note');
    expect(within(note).getByText('Como o índice geral é calculado?')).toBeInTheDocument();
    expect(note).toHaveTextContent('Conforme vale 100, Condicional vale 50 e Não-Conforme vale 0');
    expect(note).toHaveTextContent('uma única Não-Conforme já tira 16,7 pontos');
  });

  it('shows a failed attempt as "Falhou" with its reason, not as in progress', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce([
      ...HISTORY,
      {
        id: 'analysis-3',
        status: 'falhou' as const,
        motivo_falha: 'O GitHub está indisponível no momento. Tente novamente em instantes.',
        solicitada_em: '2026-06-20T00:00:00Z',
        concluida_em: '2026-06-20T00:00:01Z',
        status_conformidade_geral: null,
        medicoes: [],
      },
    ]);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce(TREND);

    renderHistoryPage();

    const list = await screen.findByRole('list', { name: 'Histórico de análises' });
    expect(within(list).getByText('Falhou')).toBeInTheDocument();
    expect(within(list).getByText(/O GitHub está indisponível/)).toBeInTheDocument();
    expect(within(list).queryByText('Em andamento')).not.toBeInTheDocument();
  });

  it('shows an attempt that is still running as "Em andamento" using its request date', async () => {
    (listAnalysesHistory as jest.Mock).mockResolvedValueOnce([
      {
        id: 'analysis-4',
        status: 'processando' as const,
        motivo_falha: null,
        solicitada_em: '2026-06-21T10:00:00Z',
        concluida_em: null,
        status_conformidade_geral: null,
        medicoes: [],
      },
    ]);
    (getMetricTrend as jest.Mock).mockResolvedValueOnce(TREND);

    renderHistoryPage();

    const list = await screen.findByRole('list', { name: 'Histórico de análises' });
    expect(within(list).getByText('Em andamento')).toBeInTheDocument();
    expect(within(list).getByText(/2026/)).toBeInTheDocument();
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
