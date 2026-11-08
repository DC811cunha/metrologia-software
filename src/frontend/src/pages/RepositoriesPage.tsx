import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { isAxiosError } from 'axios';

import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { GaugeIcon, GithubIcon, PlayIcon, PlusIcon, TrashIcon } from '../components/ui/Icon';
import Input from '../components/ui/Input';
import PageHeader from '../components/ui/PageHeader';
import Skeleton from '../components/ui/Skeleton';
import StatusBadge from '../components/ui/StatusBadge';
import { triggerAnalysis } from '../services/analysisService';
import {
  Repository,
  createRepository,
  deleteRepository,
  listRepositories,
} from '../services/repositoryService';

/** Mensagem em português devolvida pelo backend (cota do GitHub, indisponibilidade, repositório grande demais…). */
function serverDetail(err: unknown): string | null {
  if (isAxiosError(err) && typeof err.response?.data?.detail === 'string') {
    return err.response.data.detail;
  }
  return null;
}

function RepositoryAvatar({ name }: { name: string }) {
  const repoName = name.split('/').pop() ?? name;
  return (
    <span
      aria-hidden="true"
      className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-800 text-lg font-extrabold uppercase text-white shadow-brand"
    >
      {repoName.charAt(0)}
    </span>
  );
}

function EmptyState() {
  return (
    <Card className="flex animate-fade-up flex-col items-center gap-3 border-dashed py-14 text-center">
      <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-500/10 text-brand-400 ring-8 ring-brand-50/60">
        <GaugeIcon className="h-8 w-8" />
      </span>
      <p className="text-base font-semibold text-fg">Nenhum repositório cadastrado ainda.</p>
      <p className="max-w-sm text-sm text-fg-muted">
        Cole a URL de um repositório público do GitHub acima e execute a primeira análise para ver
        seus indicadores de qualidade.
      </p>
    </Card>
  );
}

function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [url, setUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [lastResultMessage, setLastResultMessage] = useState<string | null>(null);

  async function loadRepositories() {
    setLoading(true);
    try {
      setRepositories(await listRepositories());
    } catch {
      setError('Não foi possível carregar os repositórios.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRepositories();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createRepository(url);
      setUrl('');
      await loadRepositories();
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 409) {
        setError('Este repositório já está cadastrado.');
      } else if (isAxiosError(err) && err.response?.status === 422) {
        setError('URL inválida, repositório inacessível ou linguagem não suportada (Python/JS/TS).');
      } else if (isAxiosError(err) && (err.response?.status === 429 || err.response?.status === 502)) {
        setError(serverDetail(err) ?? 'O GitHub não respondeu agora. Tente novamente em instantes.');
      } else {
        setError('Não foi possível cadastrar o repositório.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteRepository(id);
      await loadRepositories();
    } catch {
      setError('Não foi possível remover o repositório.');
    }
  }

  async function handleAnalyze(id: string) {
    setError(null);
    setLastResultMessage(null);
    setAnalyzingId(id);
    try {
      const analysis = await triggerAnalysis(id);
      if (analysis.status === 'falhou') {
        setLastResultMessage(`Análise falhou: ${analysis.motivo_falha ?? 'motivo desconhecido'}`);
      } else {
        setLastResultMessage(
          `Análise concluída — conformidade geral: ${analysis.status_conformidade_geral}`,
        );
      }
      await loadRepositories();
    } catch (err) {
      const status = isAxiosError(err) ? err.response?.status : undefined;
      const explainable = status !== undefined && [409, 422, 429, 502, 503].includes(status);
      setError((explainable ? serverDetail(err) : null) ?? 'Não foi possível executar a análise.');
    } finally {
      setAnalyzingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Workspace"
        title="Repositórios"
        description="Cadastre um repositório público (Python, JavaScript ou TypeScript) para inspecionar conformidade de qualidade."
      />

      <Card glow className="animate-fade-up [animation-delay:80ms]">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Input
              id="repository-url"
              label="URL do repositório GitHub"
              type="url"
              placeholder="https://github.com/owner/repo"
              icon={<GithubIcon />}
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              required
            />
          </div>
          <Button
            type="submit"
            icon={<PlusIcon className="h-4 w-4" />}
            loading={submitting}
            disabled={submitting}
            className="min-h-[44px] sm:min-w-[140px]"
          >
            {submitting ? 'Cadastrando…' : 'Cadastrar'}
          </Button>
        </form>
      </Card>

      {error && <Alert>{error}</Alert>}
      {lastResultMessage && <Alert variant="info">{lastResultMessage}</Alert>}

      {loading ? (
        <div className="flex flex-col gap-3" aria-busy="true">
          <p role="status" className="sr-only">
            Carregando repositórios…
          </p>
          {[0, 1, 2].map((item) => (
            <Skeleton key={item} className="h-24 rounded-2xl" />
          ))}
        </div>
      ) : repositories.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="flex flex-col gap-3">
          <p className="text-sm font-medium text-fg-muted">
            {repositories.length} {repositories.length === 1 ? 'repositório cadastrado' : 'repositórios cadastrados'}
          </p>
          <ul className="flex flex-col gap-3">
            {repositories.map((repository, index) => (
              <Card
                key={repository.id}
                interactive
                style={{ animationDelay: `${index * 60}ms` }}
                className="flex animate-fade-up flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-center gap-4">
                  <RepositoryAvatar name={repository.owner_nome} />
                  <div className="flex flex-col gap-2">
                    <span className="font-semibold text-fg">{repository.owner_nome}</span>
                    <div className="flex flex-wrap items-center gap-2">
                      {repository.linguagens_detectadas.map((lang) => (
                        <span
                          key={lang}
                          className="rounded-md bg-brand-500/10 px-2 py-0.5 text-xs font-semibold capitalize text-brand-300 ring-1 ring-inset ring-brand-500/20"
                        >
                          {lang}
                        </span>
                      ))}
                      {repository.status_acesso === 'inacessivel' && <StatusBadge label="Não-Conforme" />}
                      {repository.ultima_analise_status && (
                        <StatusBadge label={repository.ultima_analise_status} />
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {repository.ultima_analise_status === 'concluida' && repository.ultima_analise_id && (
                    <Link
                      to={`/repositories/${repository.id}/analyses/${repository.ultima_analise_id}`}
                      className="inline-flex min-h-[40px] items-center rounded-lg border border-brand-500/30 bg-brand-500/10 px-4 py-2 text-sm font-semibold text-brand-300 transition-colors hover:border-brand-400/50 hover:bg-brand-500/100/25"
                    >
                      Ver dashboard
                    </Link>
                  )}
                  <Button
                    variant="secondary"
                    icon={<PlayIcon className="h-4 w-4" />}
                    loading={analyzingId === repository.id}
                    onClick={() => handleAnalyze(repository.id)}
                    disabled={analyzingId === repository.id || repository.status_acesso === 'inacessivel'}
                  >
                    {analyzingId === repository.id ? 'Analisando…' : 'Executar análise'}
                  </Button>
                  <Button
                    variant="danger"
                    icon={<TrashIcon className="h-4 w-4" />}
                    onClick={() => handleDelete(repository.id)}
                  >
                    Remover
                  </Button>
                </div>
              </Card>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default RepositoriesPage;
