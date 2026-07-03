import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import ProtectedRoute from '../src/components/ProtectedRoute';
import { ACCESS_TOKEN_KEY } from '../src/services/api';

function renderWithRoute(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/repositories" element={<div>Repositories Page</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProtectedRoute', () => {
  afterEach(() => {
    localStorage.clear();
  });

  it('redirects to /login when there is no access token', () => {
    renderWithRoute('/repositories');
    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('renders the protected content when an access token exists', () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, 'fake-token');
    renderWithRoute('/repositories');
    expect(screen.getByText('Repositories Page')).toBeInTheDocument();
  });
});
