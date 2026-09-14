import { expect, test } from '@playwright/test';

import { E2E_REPO_LABEL, registerAndAnalyzeRepo, registerNewUser, uniqueEmail } from './helpers';

/**
 * User Story 1 (P1, MVP) — spec.md Acceptance Scenarios 1-2 / FR-001 a FR-004.
 *
 * Cadastra um repositório GitHub público real e dispara uma análise automática pela
 * UI, confirmando que o conjunto completo de métricas é calculado e persistido.
 */
test.describe('US1 — Cadastro de repositório e execução de análise', () => {
  test('cadastra um repositório público e conclui uma análise com sucesso', async ({ page }) => {
    await registerNewUser(page, uniqueEmail('us1'));
    await expect(page.getByRole('heading', { name: 'Repositórios' })).toBeVisible();

    await registerAndAnalyzeRepo(page);

    // FR-007: a análise concluída fica disponível como registro histórico e o dashboard
    // passa a ser acessível a partir da lista.
    const card = page.locator('ul > div').filter({ hasText: E2E_REPO_LABEL });
    await expect(card.getByRole('link', { name: 'Ver dashboard' })).toBeVisible();
    await expect(card.getByText('concluida')).toBeVisible();
  });

  test('rejeita o cadastro duplicado da mesma URL pelo mesmo usuário (FR-015)', async ({
    page,
  }) => {
    await registerNewUser(page, uniqueEmail('us1-dup'));

    await page.getByLabel('URL do repositório GitHub').fill('https://github.com/pypa/sampleproject');
    await page.getByRole('button', { name: 'Cadastrar' }).click();
    await expect(page.locator('ul > div').filter({ hasText: E2E_REPO_LABEL })).toBeVisible();

    await page.getByLabel('URL do repositório GitHub').fill('https://github.com/pypa/sampleproject');
    await page.getByRole('button', { name: 'Cadastrar' }).click();

    await expect(page.getByText('Este repositório já está cadastrado.')).toBeVisible();
  });
});
