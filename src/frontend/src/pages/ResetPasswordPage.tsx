import { FormEvent, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { isAxiosError } from 'axios';

import AuthLayout from '../components/AuthLayout';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import { LockIcon } from '../components/ui/Icon';
import Input from '../components/ui/Input';
import api from '../services/api';

const LINK_CLASSES = 'font-semibold text-brand-400 hover:text-brand-300 hover:underline';

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
        setError('A senha deve ter entre 8 e 72 caracteres.');
      } else {
        setError('Este link de recuperação é inválido ou expirou.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <AuthLayout
        title="Link inválido"
        subtitle="Não conseguimos identificar o seu pedido de recuperação."
        footer={
          <Link to="/forgot-password" className={LINK_CLASSES}>
            Solicitar novo link
          </Link>
        }
      >
        <Alert>Este link de recuperação está incompleto. Solicite um novo.</Alert>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Redefinir senha"
      subtitle="Escolha uma nova senha para sua conta"
      footer={
        <Link to="/login" className={LINK_CLASSES}>
          Voltar para o login
        </Link>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <Input
          id="password"
          label="Nova senha"
          type="password"
          autoComplete="new-password"
          icon={<LockIcon />}
          hint="Use de 8 a 72 caracteres."
          minLength={8}
          maxLength={72}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        {error && <Alert>{error}</Alert>}

        <Button type="submit" loading={submitting} disabled={submitting} className="w-full min-h-[44px]">
          {submitting ? 'Salvando…' : 'Redefinir senha'}
        </Button>
      </form>
    </AuthLayout>
  );
}

export default ResetPasswordPage;
