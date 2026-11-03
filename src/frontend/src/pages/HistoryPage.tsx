import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import Alert from '../components/ui/Alert';
import Card from '../components/ui/Card';
import { ArrowLeftIcon, ChartIcon, TrendDownIcon, TrendFlatIcon, TrendUpIcon } from '../components/ui/Icon';
import PageHeader from '../components/ui/PageHeader';
import Skeleton from '../components/ui/Skeleton';
import StatusBadge from '../components/ui/StatusBadge';
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
  melhorando: 'bg-conforme-bg text-conforme-text',
  piorando: 'bg-nao-conforme-bg text-nao-conforme-text',
  estavel: 'bg-slate-100 text-slate-700',
};

const TREND_ICONS: Record<string, typeof TrendUpIcon> = {
  melhorando: TrendUpIcon,
  piorando: TrendDownIcon,
  estavel: TrendFlatIcon,
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
  // A série pode ter itens (uma análise por execução) sem nenhum valor plotável —
  // ex.: cobertura_testes ausente em todas as análises — nesse caso o gráfico não
  // deve ser exibido vazio, e sim a mensagem de dados insuficientes.
  const hasPlottableData = trend?.serie.some((point) => point.valor_medido !== null) ?? false;
  const TrendIcon = trend?.tendencia ? TREND_ICONS[trend.tendencia] : null;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Evolução"
        title="Histórico e Tendências"
        description="Acompanhe como cada métrica evolui a cada análise executada."
        back={
          <Link
            to="/repositories"
            className="mb-1.5 inline-flex w-fit items-center gap-1.5 text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            <ArrowLeftIcon className="h-4 w-4" />
            Repositórios
          </Link>
        }
      />

      {error && <Alert>{error}</Alert>}

      <Card className="animate-fade-up [animation-delay:80ms]">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
            <label htmlFor="metric-select" className="text-sm font-semibold text-slate-700">
              Métrica
            </label>
            <select
              id="metric-select"
              value={metrica}
              onChange={(event) => setMetrica(event.target.value)}
              className="min-h-[44px] rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-900 shadow-sm outline-none transition-all hover:border-slate-400 focus:border-brand-500 focus:shadow-glow focus-visible:ring-0"
            >
              {METRICS_GAUGE_CONFIG.map((config) => (
                <option key={config.chave} value={config.chave}>
                  {config.label}
                </option>
              ))}
            </select>
          </div>
          {trend?.tendencia && TrendIcon && (
            <span
              className={`inline-flex w-fit items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-semibold ${TREND_CLASSES[trend.tendencia]}`}
            >
              <TrendIcon className="h-4 w-4" />
              Tendência: {TREND_LABEL[trend.tendencia]}
            </span>
          )}
        </div>

        {trend && hasPlottableData ? (
          <TrendChart serie={trend.serie} />
        ) : (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-slate-200 bg-slate-50/60 py-12 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-white text-slate-400 shadow-sm ring-1 ring-slate-200">
              <ChartIcon className="h-6 w-6" />
            </span>
            <p className="max-w-sm text-sm text-slate-500">
              Sem dados suficientes para a tendência de {metricConfig?.label}.
            </p>
          </div>
        )}
      </Card>

      {loading ? (
        <div className="flex flex-col gap-2" aria-busy="true">
          <p role="status" className="sr-only">
            Carregando histórico…
          </p>
          {[0, 1, 2].map((item) => (
            <Skeleton key={item} className="h-16 rounded-2xl" />
          ))}
        </div>
      ) : history.length === 0 ? (
        <Card className="text-center text-sm text-slate-500">Nenhuma análise registrada ainda.</Card>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {history.map((item, index) => (
            <Card
              key={item.id}
              interactive
              style={{ animationDelay: `${index * 50}ms` }}
              className="flex animate-fade-up items-center justify-between gap-4 px-5 py-4"
            >
              <div className="flex items-center gap-3">
                <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full bg-brand-500 ring-4 ring-brand-100" />
                <span className="text-sm font-medium text-slate-700">
                  {item.concluida_em ? new Date(item.concluida_em).toLocaleString('pt-BR') : 'Em andamento'}
                </span>
              </div>
              <div className="flex items-center gap-4">
                {item.status_conformidade_geral ? (
                  <StatusBadge label={item.status_conformidade_geral} />
                ) : (
                  <span className="text-sm font-medium text-slate-400">—</span>
                )}
                {repositoryId && (
                  <Link
                    to={`/repositories/${repositoryId}/analyses/${item.id}`}
                    className="text-sm font-semibold text-brand-600 hover:text-brand-700 hover:underline"
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
