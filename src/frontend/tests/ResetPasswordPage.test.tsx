import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AxiosError } from 'axios';

import ResetPasswordPage from '../src/pages/ResetPasswordPage';
import api from '../src/services/api';

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: { post: jest.fn() },
}));

function axiosErrorWithStatus(statusCode: number) {
  const error = new AxiosError('Request failed');
  error.response = {
    status: statusCode,
    data: {},
    statusText: '',
    headers: {},
    config: {} as never,
  };
  return error;
}

function renderResetPasswordPage(initialEntry = '/reset-password?token=abc123') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/forgot-password" element={<div>Forgot Password Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ResetPasswordPage', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('shows an invalid-link message when the URL has no token', () => {
    renderResetPasswordPage('/reset-password');

    expect(screen.getByText(/link inválido/i)).toBeInTheDocument();
  });

  it('submits the token from the URL and navigates to /login on success', async () => {
    (api.post as jest.Mock).mockResolvedValueOnce({});

    renderResetPasswordPage();
    fireEvent.change(screen.getByLabelText('Nova senha'), { target: { value: 'new-password-456' } });
    fireEvent.click(screen.getByRole('button', { name: /redefinir senha/i }));

    await waitFor(() => expect(screen.getByText('Login Page')).toBeInTheDocument());
    expect(api.post).toHaveBeenCalledWith('/api/v1/auth/reset-password', {
      token: 'abc123',
      new_password: 'new-password-456',
    });
  });

  it('shows an expired/invalid token message on 400', async () => {
    (api.post as jest.Mock).mockRejectedValueOnce(axiosErrorWithStatus(400));

    renderResetPasswordPage();
    fireEvent.change(screen.getByLabelText('Nova senha'), { target: { value: 'new-password-456' } });
    fireEvent.click(screen.getByRole('button', { name: /redefinir senha/i }));

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Este link de recuperação é inválido ou expirou.',
      ),
    );
  });

  it('shows a validation message on 422', async () => {
    (api.post as jest.Mock).mockRejectedValueOnce(axiosErrorWithStatus(422));

    renderResetPasswordPage();
    fireEvent.change(screen.getByLabelText('Nova senha'), { target: { value: 'short' } });
    fireEvent.submit(screen.getByRole('button', { name: /redefinir senha/i }).closest('form')!);

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('A senha deve ter ao menos 8 caracteres.'),
    );
  });
});
