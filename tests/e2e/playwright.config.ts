import { defineConfig, devices } from '@playwright/test';

/**
 * Config dos testes E2E do SoftMeter (research.md item 10 / plan.md).
 *
 * Pressupõe a aplicação completa já em execução (frontend em :3000, backend em :3001)
 * — via `docker compose up` (quickstart.md) ou rodando os dois serviços localmente.
 * Não sobe os serviços automaticamente: a analogia metrológica do projeto não faz
 * sentido "mockada" — os fluxos aqui batem em uma API real, então a aplicação real
 * precisa estar de pé antes de `npx playwright test`.
 */
export default defineConfig({
  testDir: '.',
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  fullyParallel: false, // fluxos criam/analisam repositórios reais no GitHub — evita rate limit
  retries: process.env.CI ? 1 : 0,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
