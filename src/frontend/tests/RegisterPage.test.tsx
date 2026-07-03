import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AxiosError } from 'axios';

import RegisterPage from '../src/pages/RegisterPage';
import api, { ACCESS_TOKEN_KEY } from '../src/services/api';

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: { post: jest.fn() },
  ACCESS_TOKEN_KEY: 'softmeter_token',
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

function renderRegisterPage() {
  return render(
    <MemoryRouter initialEntries={['/register']}>
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/repositories" element={<div>Repositories Page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('RegisterPage', () => {
  afterEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  it('stores the access token and navigates to /repositories on success', async () => {
    (api.post as jest.Mock).mockResolvedValueOnce({ data: { access_token: 'fake-token' } });

    renderRegisterPage();
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'dev@example.com' } });
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'super-secret-123' } });
    fireEvent.click(screen.getByRole('button', { name: /cadastrar/i }));

    await waitFor(() => expect(screen.getByText('Repositories Page')).toBeInTheDocument());
    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe('fake-token');
  });

  it('shows a duplicate-email message on 409', async () => {
    (api.post as jest.Mock).mockRejectedValueOnce(axiosErrorWithStatus(409));

    renderRegisterPage();
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'dup@example.com' } });
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'super-secret-123' } });
    fireEvent.click(screen.getByRole('button', { name: /cadastrar/i }));

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Este e-mail já está cadastrado.'),
    );
  });

  it('shows a validation message on 422', async () => {
    (api.post as jest.Mock).mockRejectedValueOnce(axiosErrorWithStatus(422));

    renderRegisterPage();
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'bad' } });
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'short' } });
    // Usa fireEvent.submit para contornar a validação nativa do HTML (minlength/type=email)
    // e exercitar o tratamento de erro 422 vindo do servidor.
    fireEvent.submit(screen.getByRole('button', { name: /cadastrar/i }).closest('form')!);

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(
        'E-mail inválido ou senha deve ter ao menos 8 caracteres.',
      ),
    );
  });
});
