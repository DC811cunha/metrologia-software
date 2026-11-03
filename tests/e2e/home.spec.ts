import { expect, test } from '@playwright/test';

/**
 * Página inicial pública (apresentação do SoftMeter): é a porta de entrada para o
 * visitante, com chamadas para cadastro/login e um carrossel de tutorial.
 */
test.describe('Página inicial', () => {
  test('visitante vê a apresentação e segue para o login', async ({ page }) => {
    await page.goto('/');

    await expect(
      page.getByRole('heading', { level: 1, name: /meça a qualidade do seu código/i }),
    ).toBeVisible();

    await page.getByRole('banner').getByRole('link', { name: 'Entrar' }).click();
    await expect(page).toHaveURL(/\/login$/);
  });

  test('visitante segue para o cadastro pelo botão principal', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('link', { name: 'Começar agora' }).click();
    await expect(page).toHaveURL(/\/register$/);
  });

  test('carrossel de tutorial navega entre os passos', async ({ page }) => {
    await page.goto('/');

    const carousel = page.getByRole('region', { name: 'Tutorial passo a passo' });
    await carousel.scrollIntoViewIfNeeded();
    await expect(carousel.getByRole('group', { name: '1 de 6' })).toBeVisible();

    await carousel.getByRole('button', { name: 'Próximo passo' }).click();
    await expect(carousel.getByRole('group', { name: '2 de 6' })).toBeVisible();

    await carousel.getByRole('button', { name: /ir para o passo 5/i }).click();
    await expect(carousel.getByRole('group', { name: '5 de 6' })).toBeVisible();
  });
});
