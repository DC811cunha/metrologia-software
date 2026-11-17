import { expect, test } from '@playwright/test';

import {
  E2E_REPO_URL,
  registerAndAnalyzeRepo,
  registerNewUser,
  repositoryCard,
  uniqueEmail,
} from './helpers';

/**
 * Excluir um repositório que já tem análise pede confirmação em uma janela secundária (modal) que
 * explica o que será apagado; sem nada a perder, a exclusão continua imediata.
 */
test.describe('Exclusão de repositório com análise', () => {
  test('pede confirmação, mantém o repositório ao cancelar e exclui ao confirmar', async ({ page }) => {
    await registerNewUser(page, uniqueEmail('exclusao'));
    await registerAndAnalyzeRepo(page);
    const card = repositoryCard(page);

    // Cancelar: a janela fecha e o repositório continua na lista.
    await card.getByRole('button', { name: 'Remover' }).click();
    const dialog = page.getByRole('alertdialog');
    await expect(dialog).toBeVisible();
    await expect(
      dialog.getByRole('heading', { name: 'Deseja mesmo excluir este repositório?' }),
    ).toBeVisible();
    await expect(dialog).toContainText('já possui 1 análise');
    await expect(dialog).toContainText('Esta ação não pode ser desfeita.');
    await dialog.getByRole('button', { name: 'Cancelar' }).click();
    await expect(dialog).toBeHidden();
    await expect(card).toBeVisible();

    // Esc também cancela.
    await card.getByRole('button', { name: 'Remover' }).click();
    await expect(dialog).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
    await expect(card).toBeVisible();

    // Confirmar: exclui e a lista volta ao estado vazio.
    await card.getByRole('button', { name: 'Remover' }).click();
    await dialog.getByRole('button', { name: 'Excluir repositório' }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByText('Nenhum repositório cadastrado ainda.')).toBeVisible();
  });

  test('repositório sem análise é removido na hora, sem janela de confirmação', async ({ page }) => {
    await registerNewUser(page, uniqueEmail('exclusao-vazio'));
    await page.getByLabel('URL do repositório GitHub').fill(E2E_REPO_URL);
    await page.getByRole('button', { name: 'Cadastrar' }).click();
    const card = repositoryCard(page);
    await expect(card).toBeVisible({ timeout: 15_000 });

    await card.getByRole('button', { name: 'Remover' }).click();

    await expect(page.getByRole('alertdialog')).toHaveCount(0);
    await expect(page.getByText('Nenhum repositório cadastrado ainda.')).toBeVisible();
  });
});
