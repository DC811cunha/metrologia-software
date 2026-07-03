import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { isAxiosError } from 'axios';

import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import api, { ACCESS_TOKEN_KEY } from '../services/api';

/**
 * Tela de cadastro (US5, FR-010).
 */
function RegisterPage() {
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
      const response = await api.post('/api/v1/auth/register', { email, password });
      localStorage.setItem(ACCESS_TOKEN_KEY, response.data.access_token);
      navigate('/repositories', { replace: true });
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 409) {
        setError('Este e-mail já está cadastrado.');
      } else if (isAxiosError(err) && err.response?.status === 422) {
        setError('E-mail inválido ou senha deve ter ao menos 8 caracteres.');
      } else {
        setError('Não foi possível concluir o cadastro.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold text-slate-900">Criar conta</h1>
        <p className="mb-6 text-sm text-slate-500">Comece a inspecionar seus repositórios</p>

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
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          {error && <Alert>{error}</Alert>}

          <Button type="submit" disabled={submitting}>
            {submitting ? 'Cadastrando…' : 'Cadastrar'}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Já tem conta?{' '}
          <Link to="/login" className="font-medium text-sky-600 hover:text-sky-700">
            Entrar
          </Link>
        </p>
      </Card>
    </div>
  );
}

export default RegisterPage;
