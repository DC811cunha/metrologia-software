import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { isAxiosError } from 'axios';

import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import { triggerAnalysis } from '../services/analysisService';
import {
  Repository,
  createRepository,
  deleteRepository,
  listRepositories,
} from '../services/repositoryService';

const STATUS_BADGE_CLASSES: Record<string, string> = {
  Conforme: 'bg-conforme-bg text-conforme-text',
  Condicional: 'bg-condicional-bg text-condicional-text',
  'Não-Conforme': 'bg-nao-conforme-bg text-nao-conforme-text',
  concluida: 'bg-conforme-bg text-conforme-text',
  processando: 'bg-condicional-bg text-condicional-text',
  falhou: 'bg-nao-conforme-bg text-nao-conforme-text',
};

function StatusBadge({ label }: { label: string }) {
  const classes = STATUS_BADGE_CLASSES[label] ?? 'bg-slate-100 text-slate-600';
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${classes}`}>
      {label}
    </span>
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
    } catch {
      setError('Não foi possível executar a análise.');
    } finally {
      setAnalyzingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Repositórios</h1>
        <p className="mt-1 text-sm text-slate-500">
          Cadastre um repositório público (Python, JavaScript ou TypeScript) para inspecionar
          conformidade de qualidade.
        </p>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Input
              id="repository-url"
              label="URL do repositório GitHub"
              type="url"
              placeholder="https://github.com/owner/repo"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              required
            />
          </div>
          <Button type="submit" disabled={submitting}>
            {submitting ? 'Cadastrando…' : 'Cadastrar'}
          </Button>
        </form>
      </Card>

      {error && <Alert>{error}</Alert>}
      {lastResultMessage && <Alert variant="info">{lastResultMessage}</Alert>}

      {loading ? (
        <p className="text-sm text-slate-500">Carregando repositórios…</p>
      ) : repositories.length === 0 ? (
        <Card className="text-sm text-slate-500">Nenhum repositório cadastrado ainda.</Card>
      ) : (
        <ul className="flex flex-col gap-3">
          {repositories.map((repository) => (
            <Card key={repository.id} className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-col gap-1">
                <span className="font-medium text-slate-900">{repository.owner_nome}</span>
                <div className="flex flex-wrap items-center gap-2">
                  {repository.linguagens_detectadas.map((lang) => (
                    <span
                      key={lang}
                      className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600"
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

              <div className="flex gap-2">
                {repository.ultima_analise_status === 'concluida' && repository.ultima_analise_id && (
                  <Link
                    to={`/repositories/${repository.id}/analyses/${repository.ultima_analise_id}`}
                    className="inline-flex items-center rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Ver dashboard
                  </Link>
                )}
                <Button
                  variant="secondary"
                  onClick={() => handleAnalyze(repository.id)}
                  disabled={analyzingId === repository.id || repository.status_acesso === 'inacessivel'}
                >
                  {analyzingId === repository.id ? 'Analisando…' : 'Executar análise'}
                </Button>
                <Button variant="danger" onClick={() => handleDelete(repository.id)}>
                  Remover
                </Button>
              </div>
            </Card>
          ))}
        </ul>
      )}
    </div>
  );
}

export default RepositoriesPage;
