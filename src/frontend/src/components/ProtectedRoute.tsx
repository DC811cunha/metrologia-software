import { Navigate, Outlet } from 'react-router-dom';

import { ACCESS_TOKEN_KEY } from '../services/api';

/**
 * Envolve rotas que exigem usuário autenticado (FR-010).
 * Redireciona para /login quando não há access token armazenado.
 */
function ProtectedRoute() {
  const isAuthenticated = Boolean(localStorage.getItem(ACCESS_TOKEN_KEY));

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
