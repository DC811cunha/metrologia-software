import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import Alert from '../components/ui/Alert';
import Card from '../components/ui/Card';
import TrendChart from '../components/TrendChart';
import { METRICS_GAUGE_CONFIG } from '../metricsCatalog';
import {
  AnalysisHistoryItem,
  MetricTrend,
  getMetricTrend,
  listAnalysesHistory,
} from '../services/analysisService';

const TREND_LABEL: Record<string, string> = {
  melhorando: 'Melhorando',
  piorando: 'Piorando',
  estavel: 'Estável',
};

const TREND_CLASSES: Record<string, string> = {
  melhorando: 'text-conforme-text',
  piorando: 'text-nao-conforme-text',
  estavel: 'text-slate-600',
};

function HistoryPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [metrica, setMetrica] = useState(METRICS_GAUGE_CONFIG[0].chave);
  const [trend, setTrend] = useState<MetricTrend | null>(null);

  useEffect(() => {
    if (!repositoryId) return;
    listAnalysesHistory(repositoryId)
      .then(setHistory)
      .catch(() => setError('Não foi possível carregar o histórico.'))
      .finally(() => setLoading(false));
  }, [repositoryId]);

  useEffect(() => {
    if (!repositoryId) return;
    getMetricTrend(repositoryId, metrica)
      .then(setTrend)
      .catch(() => setTrend(null));
  }, [repositoryId, metrica]);

  const metricConfig = METRICS_GAUGE_CONFIG.find((config) => config.chave === metrica);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link to="/repositories" className="text-sm font-medium text-sky-600 hover:text-sky-700">
          ← Repositórios
        </Link>
        <h1 className="mt-1 text-2xl font-semibold text-slate-900">Histórico e Tendências</h1>
      </div>

      {error && <Alert>{error}</Alert>}

      <Card>
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <label htmlFor="metric-select" className="text-sm font-medium text-slate-700">
            Métrica
          </label>
          <select
            id="metric-select"
            value={metrica}
            onChange={(event) => setMetrica(event.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
          >
            {METRICS_GAUGE_CONFIG.map((config) => (
              <option key={config.chave} value={config.chave}>
                {config.label}
              </option>
            ))}
          </select>
          {trend?.tendencia && (
            <span className={`text-sm font-semibold ${TREND_CLASSES[trend.tendencia]}`}>
              Tendência: {TREND_LABEL[trend.tendencia]}
            </span>
          )}
        </div>

        {trend && trend.serie.length > 0 ? (
          <TrendChart serie={trend.serie} />
        ) : (
          <p className="text-sm text-slate-500">
            Sem dados suficientes para a tendência de {metricConfig?.label}.
          </p>
        )}
      </Card>

      {loading ? (
        <p className="text-sm text-slate-500">Carregando histórico…</p>
      ) : history.length === 0 ? (
        <Card className="text-sm text-slate-500">Nenhuma análise registrada ainda.</Card>
      ) : (
        <ul className="flex flex-col gap-2">
          {history.map((item) => (
            <Card key={item.id} className="flex items-center justify-between">
              <span className="text-sm text-slate-700">
                {item.concluida_em ? new Date(item.concluida_em).toLocaleString('pt-BR') : 'Em andamento'}
              </span>
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-slate-900">
                  {item.status_conformidade_geral ?? '—'}
                </span>
                {repositoryId && (
                  <Link
                    to={`/repositories/${repositoryId}/analyses/${item.id}`}
                    className="text-sm font-medium text-sky-600 hover:text-sky-700"
                  >
                    Ver dashboard
                  </Link>
                )}
              </div>
            </Card>
          ))}
        </ul>
      )}
    </div>
  );
}

export default HistoryPage;
