import { Navigate, Route, BrowserRouter, Routes } from 'react-router-dom';

import ProtectedRoute from './components/ProtectedRoute';

/**
 * SoftMeter — Frontend React
 *
 * Rotas planejadas (adicionadas incrementalmente por user story):
 * /login, /register        → US5 (Autenticação)
 * /repositories             → US1 (Cadastro e análise)
 * /repositories/:id          → US2 (Dashboard de gauges)
 * /repositories/:id/history    → US3 (Histórico e tendências)
 */
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Navigate to="/repositories" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
