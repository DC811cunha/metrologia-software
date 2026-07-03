import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import api, { ACCESS_TOKEN_KEY } from '../services/api';

/**
 * Tela de login (US5, FR-010).
 */
function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await api.post('/api/v1/auth/login', { email, password });
      localStorage.setItem(ACCESS_TOKEN_KEY, response.data.access_token);
      navigate('/repositories', { replace: true });
    } catch {
      setError('Credenciais inválidas.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold text-slate-900">SoftMeter</h1>
        <p className="mb-6 text-sm text-slate-500">Entre para acessar seus repositórios</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            id="email"
            label="E-mail"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <Input
            id="password"
            label="Senha"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          {error && <Alert>{error}</Alert>}

          <Button type="submit" disabled={submitting}>
            {submitting ? 'Entrando…' : 'Entrar'}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Não tem conta?{' '}
          <Link to="/register" className="font-medium text-sky-600 hover:text-sky-700">
            Cadastre-se
          </Link>
        </p>
      </Card>
    </div>
  );
}

export default LoginPage;
