import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should load login page', async ({ page }) => {
    await page.goto('/login');
    
    await expect(page).toHaveTitle(/CloudiQS Demo agent/);
    await expect(page.getByText('Select Demo Persona')).toBeVisible();
    await expect(page.getByText('Northstar Technologies')).toBeVisible();
  });

  test('should login as Asha (employee)', async ({ page }) => {
    await page.goto('/login');
    
    // Ensure Northstar is selected (default)
    await expect(page.getByText('Northstar Technologies')).toBeVisible();
    
    // Select Asha persona
    await page.getByText('Asha Patel').click();
    await page.getByRole('button', { name: /enter workspace/i }).click();
    
    // Wait for redirect to dashboard
    await expect(page).toHaveURL('/');
    
    // Verify we're logged in
    await expect(page.getByText(/good morning/i)).toBeVisible();
  });

  test('should not allow terminated user to login', async ({ page }) => {
    await page.goto('/login');
    
    // Select Omar (terminated)
    await page.getByText('Omar Ali').click();
    
    // Button should be disabled or show error
    await expect(page.getByText(/terminated/i)).toBeVisible();
  });

  test('should allow logout', async ({ page }) => {
    await page.goto('/login');
    
    // Login as Asha
    await page.getByText('Asha Patel').click();
    await page.getByRole('button', { name: /enter workspace/i }).click();
    await page.waitForURL('/');
    
    // Click logout button in header
    // Note: This will need the actual logout button selector
    await page.locator('[aria-label="Logout"], button:has-text("Logout")').first().click();
    
    // Should redirect to login
    await expect(page).toHaveURL('/login');
  });
});
