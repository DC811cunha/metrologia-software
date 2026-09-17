import { FormEvent, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { isAxiosError } from 'axios';

import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import api from '../services/api';

/**
 * Tela de redefinição de senha (US5, FR-010) — acessada pelo link enviado por e-mail.
 */
function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.post('/api/v1/auth/reset-password', { token, new_password: password });
      navigate('/login', { replace: true });
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 422) {
        setError('A senha deve ter ao menos 8 caracteres.');
      } else {
        setError('Este link de recuperação é inválido ou expirou.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <Card className="w-full max-w-sm">
          <h1 className="mb-1 text-xl font-semibold text-slate-900">Link inválido</h1>
          <Alert>Este link de recuperação está incompleto. Solicite um novo.</Alert>
          <p className="mt-6 text-center text-sm text-slate-500">
            <Link to="/forgot-password" className="font-medium text-sky-600 hover:text-sky-700">
              Solicitar novo link
            </Link>
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold text-slate-900">Redefinir senha</h1>
        <p className="mb-6 text-sm text-slate-500">Escolha uma nova senha para sua conta</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            id="password"
            label="Nova senha"
            type="password"
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          {error && <Alert>{error}</Alert>}

          <Button type="submit" disabled={submitting}>
            {submitting ? 'Salvando…' : 'Redefinir senha'}
          </Button>
        </form>
      </Card>
    </div>
  );
}

export default ResetPasswordPage;
