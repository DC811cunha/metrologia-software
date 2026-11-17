import { expect, request as playwrightRequest, test } from '@playwright/test';

import { E2E_PASSWORD, registerNewUser, uniqueEmail } from './helpers';

/**
 * User Story 5 (P3) — spec.md Acceptance Scenarios 1-3 / FR-010.
 *
 * Cadastro, login e redirecionamento de rotas protegidas para quem não está
 * autenticado.
 */
const API_URL = process.env.E2E_API_URL ?? 'http://localhost:3001';

test.describe('US5 — Autenticação de usuários', () => {
  test('visitante não autenticado é redirecionado ao acessar rota protegida', async ({ page }) => {
    await page.goto('/repositories');
    await expect(page).toHaveURL(/\/login$/);

    await page.goto('/repositories/00000000-0000-0000-0000-000000000000/history');
    await expect(page).toHaveURL(/\/login$/);
  });

  test('cadastro autentica automaticamente e login recupera a sessão', async ({ page }) => {
    const email = uniqueEmail('us5');

    await registerNewUser(page, email);
    await expect(page.getByRole('heading', { name: 'Repositórios' })).toBeVisible();

    // Sair encerra a sessão local e revoga o refresh token (AppLayout.handleLogout).
    await page.getByRole('button', { name: 'Sair' }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.goto('/repositories');
    await expect(page).toHaveURL(/\/login$/);

    // Login com as mesmas credenciais recupera acesso à própria conta (FR-010).
    await page.getByLabel('E-mail').fill(email);
    await page.getByLabel('Senha').fill(E2E_PASSWORD);
    await page.getByRole('button', { name: 'Entrar' }).click();
    await expect(page).toHaveURL(/\/repositories$/);
    await expect(page.getByRole('heading', { name: 'Repositórios' })).toBeVisible();
  });

  test('login com credenciais inválidas exibe erro e não autentica', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('E-mail').fill(uniqueEmail('us5-invalid'));
    await page.getByLabel('Senha').fill('senha-errada-123');
    await page.getByRole('button', { name: 'Entrar' }).click();

    await expect(page.getByText('Credenciais inválidas.')).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);
  });

  test('sair revoga a sessão no servidor mesmo com o access token já expirado', async ({ page, context }) => {
    await registerNewUser(page, uniqueEmail('us5-logout'));
    await expect(page.getByRole('heading', { name: 'Repositórios' })).toBeVisible();
    const refreshCookie = (await context.cookies()).find((c) => c.name === 'softmeter_refresh_token');
    expect(refreshCookie).toBeDefined();

    // Usuário ficou parado: o access token (15 min) não vale mais, mas o cookie do refresh ainda existe.
    await page.evaluate(() => localStorage.setItem('softmeter_token', 'token-expirado'));
    await page.getByRole('button', { name: 'Sair' }).click();
    await expect(page).toHaveURL(/\/login$/);

    // Alguém que tenha copiado o cookie antes do logout não pode mais renovar a sessão.
    const attacker = await playwrightRequest.newContext({
      baseURL: API_URL,
      extraHTTPHeaders: { Cookie: `softmeter_refresh_token=${refreshCookie!.value}` },
    });
    const response = await attacker.post('/api/v1/auth/refresh');
    expect(response.status()).toBe(401);
    await attacker.dispose();
  });
});
