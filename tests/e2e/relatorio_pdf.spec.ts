import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

import { openDashboard, registerAndAnalyzeRepo, registerNewUser, uniqueEmail } from './helpers';

/**
 * User Story 4 (P2) — spec.md Acceptance Scenario 1 / FR-009.
 *
 * A partir de uma análise concluída, gerar o relatório PDF pelo dashboard e confirmar
 * que o navegador recebe um arquivo PDF de verdade para download (o conteúdo
 * detalhado — fórmula/fonte/limites por métrica — já é coberto pelo teste unitário
 * `test_report_builder.py`; aqui validamos a jornada completa pela UI real).
 */
test.describe('US4 — Geração de relatório técnico em PDF', () => {
  test('gera e baixa o PDF do relatório a partir do dashboard', async ({ page }) => {
    await registerNewUser(page, uniqueEmail('us4'));
    await registerAndAnalyzeRepo(page);
    await openDashboard(page);

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'Gerar relatório PDF' }).click(),
    ]);

    expect(download.suggestedFilename()).toMatch(/^softmeter-relatorio-.+\.pdf$/);

    const path = await download.path();
    expect(path).not.toBeNull();
    const bytes = readFileSync(path as string);
    expect(bytes.subarray(0, 5).toString('latin1')).toBe('%PDF-');
    expect(bytes.length).toBeGreaterThan(1000);
  });
});
