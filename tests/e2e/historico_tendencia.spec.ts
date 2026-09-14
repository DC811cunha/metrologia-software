import { expect, test } from '@playwright/test';

import {
  openDashboard,
  registerAndAnalyzeRepo,
  registerNewUser,
  repositoryCard,
  uniqueEmail,
} from './helpers';

/**
 * User Story 3 (P2) — spec.md Acceptance Scenarios 1-2 / FR-008.
 *
 * Com duas análises do mesmo repositório, a tela de histórico deve listar ambas em
 * ordem cronológica e indicar a tendência (melhorando/piorando/estável) da métrica
 * selecionada. Reanalisar o mesmo commit produz valores idênticos para cada métrica,
 * então a tendência esperada e determinística é "Estável".
 */
test.describe('US3 — Histórico de análises e tendências', () => {
  test('lista o histórico de 2 análises e indica tendência estável', async ({ page }) => {
    await registerNewUser(page, uniqueEmail('us3'));
    await registerAndAnalyzeRepo(page);

    // Segunda análise do mesmo repositório (mesmo código-fonte ⇒ métricas idênticas).
    await repositoryCard(page).getByRole('button', { name: 'Executar análise' }).click();
    await expect(page.getByText(/Análise concluída/)).toBeVisible({ timeout: 30_000 });

    await openDashboard(page);
    await page.getByRole('link', { name: 'Ver histórico e tendências →' }).click();
    await expect(page.getByRole('heading', { name: 'Histórico e Tendências' })).toBeVisible();

    // FR-008: duas análises concluídas devem aparecer na lista cronológica, cada uma
    // navegável para seu próprio dashboard.
    await expect(page.getByRole('link', { name: 'Ver dashboard' })).toHaveCount(2);

    // Métrica selecionada por padrão é "Complexidade Ciclomática" (primeira do catálogo).
    await expect(page.getByText('Tendência: Estável')).toBeVisible();
  });
});
