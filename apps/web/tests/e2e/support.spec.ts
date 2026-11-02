import { test, expect } from '@playwright/test';

test.describe('AI Support', () => {
  test.beforeEach(async ({ page }) => {
    // Login as Asha before each test
    await page.goto('/login');
    await page.getByText('Asha Patel').click();
    await page.getByRole('button', { name: /enter workspace/i }).click();
    await page.waitForURL('/');
  });

  test('should navigate to support page', async ({ page }) => {
    await page.goto('/support');
    
    await expect(page.getByRole('heading', { name: /ai support/i })).toBeVisible();
    await expect(page.getByPlaceholder(/describe your issue/i)).toBeVisible();
  });

  test('should show suggested prompts', async ({ page }) => {
    await page.goto('/support');
    
    await expect(page.getByText('Fix my VPN connection')).toBeVisible();
    await expect(page.getByText('Why is my laptop slow?')).toBeVisible();
  });

  test('should send a message and show response', async ({ page }) => {
    await page.goto('/support');
    
    const input = page.getByPlaceholder(/describe your issue/i);
    await input.fill('Check my account status');
    
    const sendButton = page.getByRole('button').filter({ has: page.locator('svg') }).last();
    await sendButton.click();
    
    // Wait for response (this assumes the agent responds)
    await expect(page.getByText(/analyzing/i)).toBeVisible({ timeout: 10000 });
  });
});
