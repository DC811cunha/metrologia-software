import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import Gauge from '../components/Gauge';
import { METRICS_GAUGE_CONFIG } from '../metricsCatalog';
import { Analysis, getAnalysis } from '../services/analysisService';
import { generateAndDownloadReport } from '../services/reportService';

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
    return <p className="text-sm text-slate-500">Carregando dashboard…</p>;
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

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/repositories" className="text-sm font-medium text-sky-600 hover:text-sky-700">
            ← Repositórios
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">Dashboard de Conformidade</h1>
          <p className="text-sm text-slate-500">
            Conformidade geral: <span className="font-medium">{analysis.status_conformidade_geral}</span>
          </p>
        </div>
        <div className="flex items-center gap-4">
          {repositoryId && (
            <Link
              to={`/repositories/${repositoryId}/history`}
              className="text-sm font-medium text-sky-600 hover:text-sky-700"
            >
              Ver histórico e tendências →
            </Link>
          )}
          <Button variant="secondary" onClick={handleGenerateReport} disabled={generatingReport}>
            {generatingReport ? 'Gerando…' : 'Gerar relatório PDF'}
          </Button>
        </div>
      </div>

      {reportError && <Alert>{reportError}</Alert>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {METRICS_GAUGE_CONFIG.map((config) => {
          const measurement = analysis.medicoes.find((m) => m.metrica_chave === config.chave);
          return (
            <Gauge
              key={config.chave}
              label={config.label}
              value={measurement?.valor_medido ?? null}
              unit={config.unidade}
              min={config.min}
              max={config.max}
              bands={config.bands}
              statusLabel={measurement?.status_conformidade ?? 'Não disponível'}
            />
          );
        })}
      </div>
    </div>
  );
}

export default DashboardPage;
