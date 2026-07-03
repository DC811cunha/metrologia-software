import { Outlet, useNavigate } from 'react-router-dom';

import api, { ACCESS_TOKEN_KEY } from '../services/api';

/**
 * Layout das rotas autenticadas: cabeçalho com marca, navegação e ação de logout.
 */
function AppLayout() {
  const navigate = useNavigate();

  async function handleLogout() {
    try {
      await api.post('/api/v1/auth/logout');
    } catch {
      // Mesmo se a revogação do refresh token falhar, o usuário deve poder sair localmente.
    } finally {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      navigate('/login', { replace: true });
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-lg font-semibold text-slate-900">SoftMeter</span>
          <button
            type="button"
            onClick={handleLogout}
            className="text-sm font-medium text-slate-600 hover:text-slate-900"
          >
            Sair
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}

export default AppLayout;
