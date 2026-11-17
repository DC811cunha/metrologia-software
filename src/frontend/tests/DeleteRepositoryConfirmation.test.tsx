import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import RepositoriesPage from '../src/pages/RepositoriesPage';
import { deleteRepository, listRepositories } from '../src/services/repositoryService';

jest.mock('../src/services/repositoryService', () => ({
  listRepositories: jest.fn(),
  createRepository: jest.fn(),
  deleteRepository: jest.fn(),
}));

jest.mock('../src/services/analysisService', () => ({
  triggerAnalysis: jest.fn(),
}));

const BASE = {
  id: 'repo-1',
  url: 'https://github.com/octocat/Hello-World',
  owner_nome: 'octocat/Hello-World',
  linguagens_detectadas: ['python'],
  status_acesso: 'ativo' as const,
  criado_em: '2026-06-01T00:00:00Z',
  ultima_analise_status: null,
  ultima_analise_id: null,
};

const WITH_ANALYSES_AND_REPORTS = { ...BASE, total_analises: 10, total_relatorios: 2 };

function renderPage() {
  return render(
    <MemoryRouter>
      <RepositoriesPage />
    </MemoryRouter>,
  );
}

async function openDialog(repository = WITH_ANALYSES_AND_REPORTS) {
  (listRepositories as jest.Mock).mockResolvedValueOnce([repository]);
  renderPage();
  await waitFor(() => expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument());
  const trigger = screen.getByRole('button', { name: /remover/i });
  trigger.focus(); // um clique real no navegador foca o botão; fireEvent.click não
  fireEvent.click(trigger);
  return { trigger, dialog: await screen.findByRole('alertdialog') };
}

describe('Excluir repositório que já tem análises ou relatórios', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('opens a confirmation dialog instead of deleting right away', async () => {
    const { dialog } = await openDialog();

    expect(deleteRepository).not.toHaveBeenCalled();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(within(dialog).getByRole('heading', { name: 'Deseja mesmo excluir este repositório?' })).toBeInTheDocument();
  });

  it('explains what will be lost: analyses and issued reports', async () => {
    const { dialog } = await openDialog();

    expect(dialog).toHaveTextContent('octocat/Hello-World já possui 10 análises e 2 relatórios emitidos.');
    expect(dialog).toHaveTextContent('todo o histórico, os indicadores e os relatórios em PDF deste repositório');
    expect(dialog).toHaveTextContent('apagados permanentemente');
    expect(dialog).toHaveTextContent('Esta ação não pode ser desfeita.');
  });

  it('uses the singular form for a single analysis and omits the PDF mention without reports', async () => {
    const { dialog } = await openDialog({ ...BASE, total_analises: 1, total_relatorios: 0 });

    expect(dialog).toHaveTextContent('já possui 1 análise.');
    expect(dialog).not.toHaveTextContent('relatório');
    expect(dialog).not.toHaveTextContent('PDF');
    expect(dialog).toHaveTextContent('todo o histórico e os indicadores deste repositório');
  });

  it('uses the singular form for a single report', async () => {
    const { dialog } = await openDialog({ ...BASE, total_analises: 2, total_relatorios: 1 });

    expect(dialog).toHaveTextContent('2 análises e 1 relatório emitido');
  });

  it('puts the focus on the safe action so an accidental Enter never deletes', async () => {
    const { dialog } = await openDialog();

    expect(within(dialog).getByRole('button', { name: 'Cancelar' })).toHaveFocus();
  });

  it('cancels with the button, keeps the repository and returns the focus to the trigger', async () => {
    const { trigger } = await openDialog();

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(deleteRepository).not.toHaveBeenCalled();
    expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it('cancels with Escape', async () => {
    const { dialog } = await openDialog();

    fireEvent.keyDown(dialog, { key: 'Escape' });

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(deleteRepository).not.toHaveBeenCalled();
  });

  it('cancels when the backdrop is clicked, but not when the dialog itself is', async () => {
    const { dialog } = await openDialog();

    fireEvent.mouseDown(dialog);
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();

    fireEvent.mouseDown(dialog.parentElement as HTMLElement);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(deleteRepository).not.toHaveBeenCalled();
  });

  it('deletes only after the user confirms, then refreshes the list', async () => {
    (deleteRepository as jest.Mock).mockResolvedValueOnce(undefined);
    const { dialog } = await openDialog();
    (listRepositories as jest.Mock).mockResolvedValueOnce([]);

    fireEvent.click(within(dialog).getByRole('button', { name: 'Excluir repositório' }));

    await waitFor(() => expect(deleteRepository).toHaveBeenCalledWith('repo-1'));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await waitFor(() =>
      expect(screen.getByText('Nenhum repositório cadastrado ainda.')).toBeInTheDocument(),
    );
  });

  it('blocks the buttons, Escape and the backdrop while the deletion is running', async () => {
    let finish: () => void = () => undefined;
    (deleteRepository as jest.Mock).mockReturnValueOnce(new Promise<void>((resolve) => (finish = resolve)));
    const { dialog } = await openDialog();

    fireEvent.click(within(dialog).getByRole('button', { name: 'Excluir repositório' }));

    await waitFor(() => expect(within(dialog).getByRole('button', { name: 'Cancelar' })).toBeDisabled());
    expect(within(dialog).getByRole('button', { name: 'Excluir repositório' })).toBeDisabled();
    fireEvent.keyDown(dialog, { key: 'Escape' });
    fireEvent.mouseDown(dialog.parentElement as HTMLElement);
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();

    (listRepositories as jest.Mock).mockResolvedValueOnce([]);
    finish();
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
  });

  it('shows the failure on the page and closes the dialog when the deletion fails', async () => {
    (deleteRepository as jest.Mock).mockRejectedValueOnce(new Error('500'));
    const { dialog } = await openDialog();

    fireEvent.click(within(dialog).getByRole('button', { name: 'Excluir repositório' }));

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível remover o repositório.'),
    );
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('keeps the focus inside the dialog when tabbing past the last or before the first button', async () => {
    const { dialog } = await openDialog();
    const cancel = within(dialog).getByRole('button', { name: 'Cancelar' });
    const confirm = within(dialog).getByRole('button', { name: 'Excluir repositório' });

    confirm.focus();
    fireEvent.keyDown(confirm, { key: 'Tab' });
    expect(cancel).toHaveFocus();

    cancel.focus();
    fireEvent.keyDown(cancel, { key: 'Tab', shiftKey: true });
    expect(confirm).toHaveFocus();
  });

  it('locks the page scroll while open and restores it on close', async () => {
    const { dialog } = await openDialog();
    expect(document.body.style.overflow).toBe('hidden');

    fireEvent.keyDown(dialog, { key: 'Escape' });

    expect(document.body.style.overflow).not.toBe('hidden');
  });

  it('is announced with an accessible name and description', async () => {
    const { dialog } = await openDialog();

    expect(dialog).toHaveAccessibleName('Deseja mesmo excluir este repositório?');
    expect(dialog).toHaveAccessibleDescription(/já possui 10 análises e 2 relatórios emitidos/);
  });
});

describe('Excluir repositório sem nada a perder', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it.each([
    ['sem os totais', BASE],
    ['com totais zerados', { ...BASE, total_analises: 0, total_relatorios: 0 }],
  ])('deletes immediately, with no dialog, %s', async (_label, repository) => {
    (listRepositories as jest.Mock).mockResolvedValueOnce([repository]).mockResolvedValueOnce([]);
    (deleteRepository as jest.Mock).mockResolvedValueOnce(undefined);
    renderPage();
    await waitFor(() => expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /remover/i }));

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    await waitFor(() => expect(deleteRepository).toHaveBeenCalledWith('repo-1'));
  });
});
