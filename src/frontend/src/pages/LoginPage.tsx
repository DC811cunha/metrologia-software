import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import AuthLayout from '../components/AuthLayout';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import { LockIcon, MailIcon } from '../components/ui/Icon';
import Input from '../components/ui/Input';
import api, { ACCESS_TOKEN_KEY } from '../services/api';

const LINK_CLASSES = 'font-semibold text-brand-400 hover:text-brand-300 hover:underline';

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
    <AuthLayout
      title="Bem-vindo de volta"
      subtitle="Entre para acessar seus repositórios"
      footer={
        <>
          Não tem conta?{' '}
          <Link to="/register" className={LINK_CLASSES}>
            Cadastre-se
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <Input
          id="email"
          label="E-mail"
          type="email"
          autoComplete="email"
          placeholder="voce@exemplo.com"
          icon={<MailIcon />}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <div className="flex flex-col gap-2">
          <Input
            id="password"
            label="Senha"
            type="password"
            autoComplete="current-password"
            icon={<LockIcon />}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <Link to="/forgot-password" className={`self-end text-sm ${LINK_CLASSES}`}>
            Esqueci minha senha
          </Link>
        </div>

        {error && <Alert>{error}</Alert>}

        <Button type="submit" loading={submitting} disabled={submitting} className="w-full min-h-[44px]">
          {submitting ? 'Entrando…' : 'Entrar'}
        </Button>
      </form>
    </AuthLayout>
  );
}

export default LoginPage;
