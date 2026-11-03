import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';

import AuthLayout from '../components/AuthLayout';
import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import { ArrowLeftIcon, MailIcon } from '../components/ui/Icon';
import Input from '../components/ui/Input';
import api from '../services/api';

/**
 * Tela de "esqueci minha senha" (US5, FR-010).
 */
function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await api.post('/api/v1/auth/forgot-password', { email });
      setMessage(response.data.message);
    } catch {
      // Falha de comunicação com a API — o backend nunca revela se o e-mail existe,
      // então qualquer erro aqui é de rede/servidor e o usuário pode tentar de novo.
      setError('Não foi possível processar o pedido agora. Tente novamente em instantes.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Esqueceu sua senha?"
      subtitle="Informe seu e-mail e enviaremos um link para redefinir sua senha"
      footer={
        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 font-semibold text-brand-600 hover:text-brand-700 hover:underline"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Voltar para o login
        </Link>
      }
    >
      {message ? (
        <Alert variant="info">{message}</Alert>
      ) : (
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

          {error && <Alert>{error}</Alert>}

          <Button type="submit" loading={submitting} disabled={submitting} className="w-full min-h-[44px]">
            {submitting ? 'Enviando…' : 'Enviar link de recuperação'}
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}

export default ForgotPasswordPage;
