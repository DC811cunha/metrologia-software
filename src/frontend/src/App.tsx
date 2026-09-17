import { Navigate, Route, BrowserRouter, Routes } from 'react-router-dom';

import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import DashboardPage from './pages/DashboardPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import HistoryPage from './pages/HistoryPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import RepositoriesPage from './pages/RepositoriesPage';
import ResetPasswordPage from './pages/ResetPasswordPage';

/**
 * SoftMeter — Frontend React
 *
 * Rotas planejadas (adicionadas incrementalmente por user story):
 * /login, /register        → US5 (Autenticação)
 * /forgot-password, /reset-password → US5 (Recuperação de senha)
 * /repositories             → US1 (Cadastro e análise)
 * /repositories/:repositoryId/analyses/:analysisId → US2 (Dashboard de gauges)
 * /repositories/:id/history    → US3 (Histórico e tendências)
 */
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/repositories" replace />} />
            <Route path="/repositories" element={<RepositoriesPage />} />
            <Route
              path="/repositories/:repositoryId/analyses/:analysisId"
              element={<DashboardPage />}
            />
            <Route path="/repositories/:repositoryId/history" element={<HistoryPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
