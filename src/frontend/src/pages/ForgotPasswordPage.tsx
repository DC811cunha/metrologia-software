import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';

import Alert from '../components/ui/Alert';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import api from '../services/api';

/**
 * Tela de "esqueci minha senha" (US5, FR-010).
 */
function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const response = await api.post('/api/v1/auth/forgot-password', { email });
      setMessage(response.data.message);
    } catch {
      // Mesmo em erro de rede, não revelamos se o e-mail existe — a mensagem
      // genérica do backend cobre o caso de sucesso; aqui só cobrimos falha
      // de comunicação com a API.
      setMessage('Não foi possível processar o pedido agora. Tente novamente em instantes.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold text-slate-900">Esqueceu sua senha?</h1>
        <p className="mb-6 text-sm text-slate-500">
          Informe seu e-mail e enviaremos um link para redefinir sua senha
        </p>

        {message ? (
          <Alert variant="info">{message}</Alert>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              id="email"
              label="E-mail"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />

            <Button type="submit" disabled={submitting}>
              {submitting ? 'Enviando…' : 'Enviar link de recuperação'}
            </Button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-slate-500">
          Lembrou a senha?{' '}
          <Link to="/login" className="font-medium text-sky-600 hover:text-sky-700">
            Entrar
          </Link>
        </p>
      </Card>
    </div>
  );
}

export default ForgotPasswordPage;
