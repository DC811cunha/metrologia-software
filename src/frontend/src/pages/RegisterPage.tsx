import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { isAxiosError } from 'axios';

import AuthLayout from '../components/AuthLayout';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import { LockIcon, MailIcon } from '../components/ui/Icon';
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
    <AuthLayout
      title="Criar conta"
      subtitle="Comece a inspecionar seus repositórios"
      footer={
        <>
          Já tem conta?{' '}
          <Link to="/login" className="font-semibold text-brand-400 hover:text-brand-300 hover:underline">
            Entrar
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
        <Input
          id="password"
          label="Senha"
          type="password"
          autoComplete="new-password"
          icon={<LockIcon />}
          hint="Use pelo menos 8 caracteres."
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        {error && <Alert>{error}</Alert>}

        <Button type="submit" loading={submitting} disabled={submitting} className="w-full min-h-[44px]">
          {submitting ? 'Cadastrando…' : 'Cadastrar'}
        </Button>
      </form>
    </AuthLayout>
  );
}

export default RegisterPage;
