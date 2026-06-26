/**
 * End-to-end tests for Balanced News.
 *
 * These tests require both servers to be running (managed by Playwright's
 * webServer config in playwright.config.ts):
 *   - Backend:  uvicorn backend.main:app --port 8000
 *   - Frontend: npm run dev --prefix frontend  (→ http://localhost:5173)
 */
import { test, expect, Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Wait for at least one story card to appear (the app auto-refreshes on load). */
async function waitForStories(page: Page) {
  await page.goto('/');
  // The app auto-runs the pipeline on first load when there are no stories.
  await expect(page.locator('.event-card').first()).toBeVisible({ timeout: 30_000 });
}

/** Force a refresh via the header "Refresh news" button. */
async function refreshNews(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: /refresh news/i }).click();
  await expect(page.locator('.event-card').first()).toBeVisible({ timeout: 30_000 });
}

// ---------------------------------------------------------------------------
// Page load / sidebar
// ---------------------------------------------------------------------------

test.describe('Application shell', () => {
  test('loads the page with the Balanced News title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/balanced news/i);
  });

  test('sidebar shows the friendly app name and subtitle', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Balanced News' })).toBeVisible();
    await expect(page.getByText('See every side of the story')).toBeVisible();
  });

  test('sidebar has a Stories navigation button', async ({ page }) => {
    await page.goto('/');
    const nav = page.locator('.sidebar-nav');
    await expect(nav.getByRole('button', { name: /stories/i })).toBeVisible();
  });

  test('default view is the Latest stories feed', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Latest stories' })).toBeVisible();
  });

  test('does NOT expose the analyst Pipeline Runner', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: /run full pipeline/i })).toHaveCount(0);
    await expect(page.locator('.sidebar-nav').getByRole('button', { name: /pipeline/i })).toHaveCount(0);
  });
});

// ---------------------------------------------------------------------------
// Stories feed
// ---------------------------------------------------------------------------

test.describe('Stories feed', () => {
  test('auto-loads stories on first visit', async ({ page }) => {
    await waitForStories(page);
    await expect(page.locator('.event-card').first()).toBeVisible();
  });

  test('shows plain-language stats row', async ({ page }) => {
    await waitForStories(page);
    const stats = page.locator('.stats-row');
    await expect(stats.getByText('Stories', { exact: true })).toBeVisible();
    await expect(stats.getByText('Regions covered', { exact: true })).toBeVisible();
  });

  test('does NOT show technical jargon in stats', async ({ page }) => {
    await waitForStories(page);
    await expect(page.getByText('Pool Spread')).toHaveCount(0);
    await expect(page.getByText('Total Events')).toHaveCount(0);
  });

  test('event card shows title, reliability badge and source count', async ({ page }) => {
    await waitForStories(page);
    const card = page.locator('.event-card').first();
    await expect(card.locator('.event-title')).toBeVisible();
    await expect(card.locator('.badge')).toBeVisible();
    // "1 source" or "N sources" — match both singular and plural
    await expect(card.locator('.event-footer').getByText(/\d+ source/i)).toBeVisible();
  });

  test('event card uses plain "regions" wording (not "pools")', async ({ page }) => {
    await waitForStories(page);
    const card = page.locator('.event-card').first();
    await expect(card.locator('.event-footer').getByText(/\d+ region/i)).toBeVisible();
    await expect(card.locator('.event-footer').getByText(/\d+ pools/i)).toHaveCount(0);
  });

  test('region filter dropdown is present with friendly label', async ({ page }) => {
    await waitForStories(page);
    await expect(page.locator('option').filter({ hasText: 'All regions' })).toHaveCount(1);
  });

  test('reliability filter dropdown is present with friendly label', async ({ page }) => {
    await waitForStories(page);
    await expect(page.locator('option').filter({ hasText: 'All reliability' })).toHaveCount(1);
  });

  test('refresh news button re-pulls stories', async ({ page }) => {
    await refreshNews(page);
    await expect(page.locator('.event-card').first()).toBeVisible();
  });

  test('clicking a story card navigates to the detail view', async ({ page }) => {
    await waitForStories(page);
    await page.locator('.event-card').first().click();
    await expect(page.getByRole('button', { name: /back to stories/i })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Story detail
// ---------------------------------------------------------------------------

test.describe('Story detail view', () => {
  test.beforeEach(async ({ page }) => {
    await waitForStories(page);
    await page.locator('.event-card').first().click();
    await expect(page.getByRole('button', { name: /back to stories/i })).toBeVisible();
  });

  test('shows back button and a reliability badge', async ({ page }) => {
    await expect(page.getByRole('button', { name: /back to stories/i })).toBeVisible();
    await expect(page.locator('.badge').first()).toBeVisible();
  });

  test('shows the "How different sources report this" section', async ({ page }) => {
    await expect(page.getByText(/how different sources report this/i)).toBeVisible({ timeout: 15_000 });
  });

  test('shows the "Full coverage" section', async ({ page }) => {
    await expect(page.getByText('Full coverage')).toBeVisible({ timeout: 15_000 });
  });

  test('does NOT show the analyst review panel', async ({ page }) => {
    await expect(page.getByText(/human review/i)).toHaveCount(0);
    await expect(page.getByRole('button', { name: /save notes/i })).toHaveCount(0);
    await expect(page.getByRole('button', { name: /approve/i })).toHaveCount(0);
  });

  test('back button returns to the stories feed', async ({ page }) => {
    await page.getByRole('button', { name: /back to stories/i }).click();
    await expect(page.getByRole('heading', { name: 'Latest stories' })).toBeVisible();
  });
});
