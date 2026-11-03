import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import Gauge from '../components/Gauge';
import { ArrowLeftIcon, DocumentIcon } from '../components/ui/Icon';
import Skeleton from '../components/ui/Skeleton';
import { METRICS_GAUGE_CONFIG } from '../metricsCatalog';
import { Analysis, getAnalysis } from '../services/analysisService';
import { generateAndDownloadReport } from '../services/reportService';

const PILL_CLASSES: Record<string, string> = {
  Conforme: 'bg-conforme-bg text-conforme-text',
  Condicional: 'bg-condicional-bg text-condicional-text',
  'Não-Conforme': 'bg-nao-conforme-bg text-nao-conforme-text',
};

const KPIS = [
  { status: 'Conforme', label: 'Conformes', dot: 'bg-conforme' },
  { status: 'Condicional', label: 'Condicionais', dot: 'bg-condicional' },
  { status: 'Não-Conforme', label: 'Não conformes', dot: 'bg-nao-conforme' },
  { status: 'Não disponível', label: 'Sem dados', dot: 'bg-slate-400' },
];

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-8" aria-busy="true">
      <p role="status" className="sr-only">
        Carregando dashboard…
      </p>
      <Skeleton className="h-52 rounded-3xl" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {KPIS.map((kpi) => (
          <Skeleton key={kpi.status} className="h-20 rounded-2xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {METRICS_GAUGE_CONFIG.map((config) => (
          <Skeleton key={config.chave} className="h-64 rounded-2xl" />
        ))}
      </div>
    </div>
  );
}

function DashboardPage() {
  const { repositoryId, analysisId } = useParams<{ repositoryId: string; analysisId: string }>();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  useEffect(() => {
    if (!repositoryId || !analysisId) return;
    setLoading(true);
    getAnalysis(repositoryId, analysisId)
      .then(setAnalysis)
      .catch(() => setError('Não foi possível carregar a análise.'))
      .finally(() => setLoading(false));
  }, [repositoryId, analysisId]);

  async function handleGenerateReport() {
    if (!repositoryId || !analysisId) return;
    setReportError(null);
    setGeneratingReport(true);
    try {
      await generateAndDownloadReport(repositoryId, 'analise_unica', analysisId);
    } catch {
      setReportError('Não foi possível gerar o relatório.');
    } finally {
      setGeneratingReport(false);
    }
  }

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (error || !analysis) {
    return <Alert>{error ?? 'Análise não encontrada.'}</Alert>;
  }

  if (analysis.status !== 'concluida') {
    return (
      <Alert variant={analysis.status === 'falhou' ? 'error' : 'info'}>
        {analysis.status === 'falhou'
          ? `Análise falhou: ${analysis.motivo_falha ?? 'motivo desconhecido'}`
          : 'Análise ainda em processamento…'}
      </Alert>
    );
  }

  const statusByMetric = METRICS_GAUGE_CONFIG.map(
    (config) =>
      analysis.medicoes.find((m) => m.metrica_chave === config.chave)?.status_conformidade ??
      'Não disponível',
  );
  const overallPill = PILL_CLASSES[analysis.status_conformidade_geral ?? ''] ?? 'bg-white/90 text-slate-700';

  return (
    <div className="flex flex-col gap-8">
      <section className="relative animate-fade-up overflow-hidden rounded-3xl bg-gradient-to-br from-ink-950 via-brand-900 to-brand-700 p-7 text-white shadow-brand sm:p-10">
        <div className="bg-grid absolute inset-0 [mask-image:radial-gradient(ellipse_at_top_right,black_20%,transparent_70%)]" />
        <div className="absolute -right-16 -top-16 h-72 w-72 rounded-full bg-brand-400/30 blur-3xl" />

        <div className="relative flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex flex-col gap-3">
            <Link
              to="/repositories"
              className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-brand-100 hover:text-white focus-visible:ring-offset-ink-900"
            >
              <ArrowLeftIcon className="h-4 w-4" />
              Repositórios
            </Link>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand-200">
              Relatório de conformidade
              {analysis.concluida_em &&
                ` · ${new Date(analysis.concluida_em).toLocaleString('pt-BR', {
                  dateStyle: 'short',
                  timeStyle: 'short',
                })}`}
            </p>
            <h1 className="text-3xl font-extrabold sm:text-4xl">Dashboard de Conformidade</h1>
            <p className="flex items-center gap-2 text-base text-brand-50">
              Conformidade geral:{' '}
              <span
                className={`status-dot inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${overallPill}`}
              >
                {analysis.status_conformidade_geral}
              </span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {repositoryId && (
              <Link
                to={`/repositories/${repositoryId}/history`}
                className="inline-flex min-h-[40px] items-center rounded-lg border border-white/25 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-white/10 focus-visible:ring-offset-ink-900"
              >
                Ver histórico e tendências →
              </Link>
            )}
            <Button
              variant="inverse"
              icon={<DocumentIcon className="h-4 w-4" />}
              loading={generatingReport}
              onClick={handleGenerateReport}
              disabled={generatingReport}
            >
              {generatingReport ? 'Gerando…' : 'Gerar relatório PDF'}
            </Button>
          </div>
        </div>
      </section>

      {reportError && <Alert>{reportError}</Alert>}

      <section aria-label="Resumo das métricas" className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {KPIS.map((kpi, index) => (
          <div
            key={kpi.status}
            style={{ animationDelay: `${index * 70}ms` }}
            className="flex animate-fade-up items-center gap-4 rounded-2xl border border-slate-200/80 bg-white px-5 py-4 shadow-card"
          >
            <span className={`h-10 w-1.5 shrink-0 rounded-full ${kpi.dot}`} aria-hidden="true" />
            <div>
              <p className="text-3xl font-extrabold tabular-nums text-ink-900">
                {statusByMetric.filter((status) => status === kpi.status).length}
              </p>
              <p className="text-xs font-medium text-slate-500">{kpi.label}</p>
            </div>
          </div>
        ))}
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <h2 className="text-xl font-bold text-ink-900">Indicadores por métrica</h2>
          <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500" aria-label="Legenda">
            {[
              ['Conforme', 'bg-conforme'],
              ['Condicional', 'bg-condicional'],
              ['Não-Conforme', 'bg-nao-conforme'],
            ].map(([text, dot]) => (
              <li key={text} className="inline-flex items-center gap-1.5">
                <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" />
                {text}
              </li>
            ))}
          </ul>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {METRICS_GAUGE_CONFIG.map((config, index) => {
            const measurement = analysis.medicoes.find((m) => m.metrica_chave === config.chave);
            return (
              <div
                key={config.chave}
                className="flex animate-fade-up flex-col [&>*]:flex-1"
                style={{ animationDelay: `${index * 80}ms` }}
              >
                <Gauge
                  label={config.label}
                  value={measurement?.valor_medido ?? null}
                  unit={config.unidade}
                  min={config.min}
                  max={config.max}
                  bands={config.bands}
                  statusLabel={measurement?.status_conformidade ?? 'Não disponível'}
                />
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export default DashboardPage;
