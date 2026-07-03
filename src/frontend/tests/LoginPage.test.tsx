import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import LoginPage from '../src/pages/LoginPage';
import api, { ACCESS_TOKEN_KEY } from '../src/services/api';

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: { post: jest.fn() },
  ACCESS_TOKEN_KEY: 'softmeter_token',
}));

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/repositories" element={<div>Repositories Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LoginPage', () => {
  afterEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  it('stores the access token and navigates to /repositories on success', async () => {
    (api.post as jest.Mock).mockResolvedValueOnce({ data: { access_token: 'fake-token' } });

    renderLoginPage();
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'dev@example.com' } });
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'super-secret-123' } });
    fireEvent.click(screen.getByRole('button', { name: /entrar/i }));

    await waitFor(() => expect(screen.getByText('Repositories Page')).toBeInTheDocument());
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe('fake-token');
    expect(api.post).toHaveBeenCalledWith('/api/v1/auth/login', {
      email: 'dev@example.com',
      password: 'super-secret-123',
    });
  });

  it('shows an error message when credentials are invalid', async () => {
    (api.post as jest.Mock).mockRejectedValueOnce(new Error('401'));

    renderLoginPage();
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'dev@example.com' } });
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'wrong-password' } });
    fireEvent.click(screen.getByRole('button', { name: /entrar/i }));

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Credenciais inválidas.'));
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
  });
});
