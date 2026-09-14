import { Page, expect } from '@playwright/test';

/**
 * Repositório público real usado nos fluxos E2E que precisam de uma análise de
 * verdade (US1/US2/US3/US4): pequeno (download rápido do zipball), estável e
 * mantido pela própria PyPA — evita depender de um repositório de terceiros que
 * pode ser renomeado/excluído (ver Edge Cases em spec.md).
 */
export const E2E_REPO_URL = 'https://github.com/pypa/sampleproject';
export const E2E_REPO_LABEL = 'pypa/sampleproject';

/** E-mail único por execução — evita 409 (e-mail já cadastrado) entre reruns. */
export function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

export const E2E_PASSWORD = 'senha-forte-123';

/** Cadastra um novo visitante pela tela de registro real (US5, FR-010). */
export async function registerNewUser(
  page: Page,
  email: string,
  password: string = E2E_PASSWORD,
): Promise<void> {
  await page.goto('/register');
  await page.getByLabel('E-mail').fill(email);
  await page.getByLabel('Senha').fill(password);
  await page.getByRole('button', { name: 'Cadastrar' }).click();
  await page.waitForURL('**/repositories');
}

/**
 * Cadastra o repositório de teste e dispara a análise síncrona pela UI real
 * (US1), aguardando a mensagem de conclusão. Repositórios como
 * `pypa/sampleproject` ficam abaixo do limiar de análise síncrona
 * (`sync_analysis_size_limit_kb`), então a análise conclui na mesma requisição
 * — sem depender do worker Celery/Redis estar de pé.
 */
export async function registerAndAnalyzeRepo(
  page: Page,
  repoUrl: string = E2E_REPO_URL,
): Promise<void> {
  await page.getByLabel('URL do repositório GitHub').fill(repoUrl);
  await page.getByRole('button', { name: 'Cadastrar' }).click();

  const card = repositoryCard(page);
  await expect(card).toBeVisible({ timeout: 15_000 });

  await card.getByRole('button', { name: 'Executar análise' }).click();
  await expect(page.getByText(/Análise (concluída|falhou)/)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/Análise concluída/)).toBeVisible();
}

/**
 * Localiza o card do repositório de teste na lista. Os cards (`Card` → `<div>`) são
 * renderizados como filhos diretos de um `<ul>` (RepositoriesPage.tsx); navegadores
 * preservam esse aninhamento mesmo não sendo `<li>`, mas evitamos depender da tag.
 */
export function repositoryCard(page: Page) {
  return page.locator('ul > div').filter({ hasText: E2E_REPO_LABEL });
}

/** Navega da lista de repositórios para o dashboard da última análise concluída. */
export async function openDashboard(page: Page): Promise<void> {
  await repositoryCard(page).getByRole('link', { name: 'Ver dashboard' }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard de Conformidade' })).toBeVisible();
}
