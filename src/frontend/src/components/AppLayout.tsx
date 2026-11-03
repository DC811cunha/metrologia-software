import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';

import api, { ACCESS_TOKEN_KEY } from '../services/api';
import { FolderIcon, LogoutIcon } from './ui/Icon';
import Logo from './ui/Logo';

/**
 * Layout das rotas autenticadas: cabeçalho escuro com marca, navegação e ação de logout.
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
    <div className="flex min-h-screen flex-col">
      <a href="#conteudo" className="skip-link">
        Pular para o conteúdo
      </a>

      <header className="sticky top-0 z-40 border-b border-line bg-canvas/75 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex items-center gap-8">
            <Link to="/" aria-label="SoftMeter — página inicial" className="rounded-lg">
              <Logo tone="light" />
            </Link>
            <nav aria-label="Principal" className="hidden sm:block">
              <NavLink
                to="/repositories"
                className={({ isActive }) =>
                  `inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-500/15 text-white ring-1 ring-inset ring-brand-400/30'
                      : 'text-brand-100/80 hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                <FolderIcon className="h-4 w-4" />
                Repositórios
              </NavLink>
            </nav>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="inline-flex min-h-[40px] items-center gap-2 rounded-lg border border-line-strong px-3.5 py-2 text-sm font-medium text-fg-soft transition-colors hover:border-brand-400/60 hover:bg-brand-500/10 hover:text-white"
          >
            <LogoutIcon className="h-4 w-4" />
            Sair
          </button>
        </div>
      </header>

      <main id="conteudo" className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6">
        <Outlet />
      </main>

      <footer className="border-t border-line py-6 text-center text-xs text-fg-subtle">
        SoftMeter · Metrologia aplicada à qualidade de software
      </footer>
    </div>
  );
}

export default AppLayout;
