import { expect, test } from '@playwright/test';

import { METRICS_GAUGE_LABELS } from './metrics';
import { openDashboard, registerAndAnalyzeRepo, registerNewUser, uniqueEmail } from './helpers';

const VALID_STATUS = /^(Conforme|Condicional|Não-Conforme|Não disponível)$/;

/**
 * User Story 2 (P1, MVP) — spec.md Acceptance Scenarios 1-2 / FR-005, FR-006.
 *
 * Após uma análise concluída, o dashboard deve exibir as 6 métricas do catálogo como
 * gauges, cada um com valor medido (ou "Não disponível"), unidade e status de
 * conformidade — sempre a partir do mesmo componente reutilizável (Princípio III).
 */
test.describe('US2 — Dashboard de gauges metrológicos', () => {
  test('exibe os 6 gauges com valor e status de conformidade', async ({ page }) => {
    await registerNewUser(page, uniqueEmail('us2'));
    await registerAndAnalyzeRepo(page);
    await openDashboard(page);

    const cards = page.getByTestId('gauge-card');
    await expect(cards).toHaveCount(METRICS_GAUGE_LABELS.length);

    for (const label of METRICS_GAUGE_LABELS) {
      const card = cards.filter({ hasText: label });
      await expect(card).toHaveCount(1);
      // Estrutura fixa do Gauge (Gauge.tsx): <span>label</span>, gauge visual,
      // <span>valor</span>, <span>status</span> — o último <span> é sempre o status,
      // mesmo quando o valor também exibe "Não disponível" (ex.: cobertura_testes).
      await expect(card.locator('> span').last()).toHaveText(VALID_STATUS);
    }

    await expect(page.getByText(/Conformidade geral:/)).toBeVisible();
  });
});
