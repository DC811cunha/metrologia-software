import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import ForgotPasswordPage from '../src/pages/ForgotPasswordPage';
import api from '../src/services/api';

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: { post: jest.fn() },
}));

function renderForgotPasswordPage() {
  return render(
    <MemoryRouter initialEntries={['/forgot-password']}>
      <Routes>
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ForgotPasswordPage', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('shows the generic message returned by the API after submitting', async () => {
    (api.post as jest.Mock).mockResolvedValueOnce({
      data: { message: 'Se este e-mail estiver cadastrado, você receberá um link de recuperação em instantes.' },
    });

    renderForgotPasswordPage();
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'dev@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /enviar link de recuperação/i }));

    await waitFor(() =>
      expect(screen.getByText(/você receberá um link de recuperação/i)).toBeInTheDocument(),
    );
    expect(api.post).toHaveBeenCalledWith('/api/v1/auth/forgot-password', {
      email: 'dev@example.com',
    });
  });

  it('shows a generic failure message when the request errors out', async () => {
    (api.post as jest.Mock).mockRejectedValueOnce(new Error('network error'));

    renderForgotPasswordPage();
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'dev@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /enviar link de recuperação/i }));

    await waitFor(() =>
      expect(screen.getByText(/não foi possível processar o pedido agora/i)).toBeInTheDocument(),
    );
  });
});
