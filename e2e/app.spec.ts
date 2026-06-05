/**
 * End-to-end tests for kill-prop.
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

/** Run the full pipeline via the UI and wait for "Complete" status. */
async function runPipeline(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: /run full pipeline/i }).click();
  // Wait for the status card to show "Complete" or the results pane to appear
  await expect(page.getByText('Pipeline Results')).toBeVisible({ timeout: 30_000 });
}

// ---------------------------------------------------------------------------
// Page load / sidebar
// ---------------------------------------------------------------------------

test.describe('Application shell', () => {
  test('loads the page with correct title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/kill-prop/i);
  });

  test('sidebar is visible with app name and subtitle', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'kill-prop' })).toBeVisible();
    await expect(page.getByText('Source Triangulation Analyzer')).toBeVisible();
  });

  test('sidebar has all four navigation buttons', async ({ page }) => {
    await page.goto('/');
    // Scope to sidebar nav to avoid matching "Run Full Pipeline" button
    const nav = page.locator('.sidebar-nav');
    await expect(nav.getByRole('button', { name: /pipeline/i })).toBeVisible();
    await expect(nav.getByRole('button', { name: /event feed/i })).toBeVisible();
    await expect(nav.getByRole('button', { name: /review console/i })).toBeVisible();
    await expect(nav.getByRole('button', { name: /articles/i })).toBeVisible();
  });

  test('default view is Pipeline Runner', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Pipeline Runner' })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Pipeline Runner
// ---------------------------------------------------------------------------

test.describe('Pipeline Runner view', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('shows pipeline stage list', async ({ page }) => {
    await expect(page.getByText(/source intake/i)).toBeVisible();
    await expect(page.getByText(/normalization/i)).toBeVisible();
    await expect(page.getByText(/clustering/i)).toBeVisible();
    await expect(page.getByText(/extraction/i)).toBeVisible();
    await expect(page.getByText(/scoring/i)).toBeVisible();
    await expect(page.getByText(/presentation/i)).toBeVisible();
  });

  test('"Run Full Pipeline" button is present and enabled', async ({ page }) => {
    const btn = page.getByRole('button', { name: /run full pipeline/i });
    await expect(btn).toBeVisible();
    await expect(btn).toBeEnabled();
  });

  test('shows "Ready" status initially', async ({ page }) => {
    await expect(page.getByText('Ready')).toBeVisible();
  });

  test('runs the pipeline end-to-end and shows Complete', async ({ page }) => {
    await runPipeline(page);
    await expect(page.getByText('Pipeline Results')).toBeVisible();
  });

  test('shows summary text after pipeline run', async ({ page }) => {
    await runPipeline(page);
    // "ingested" appears in multiple log lines; checking any of them is sufficient
    await expect(page.getByText(/ingested/i).first()).toBeVisible();
  });

  test('"View Event Feed" button appears after pipeline completes', async ({ page }) => {
    await runPipeline(page);
    await expect(page.getByRole('button', { name: /view event feed/i })).toBeVisible();
  });

  test('clicking "View Event Feed" navigates to Event Feed', async ({ page }) => {
    await runPipeline(page);
    await page.getByRole('button', { name: /view event feed/i }).click();
    await expect(page.getByRole('heading', { name: 'Event Feed' })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Event Feed
// ---------------------------------------------------------------------------

test.describe('Event Feed view', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure data exists
    await runPipeline(page);
    await page.getByRole('button', { name: /view event feed/i }).click();
    await expect(page.getByRole('heading', { name: 'Event Feed' })).toBeVisible();
  });

  test('shows stats row with total events', async ({ page }) => {
    await expect(page.getByText('Total Events')).toBeVisible();
    await expect(page.getByText('Pool Spread')).toBeVisible();
  });

  test('renders at least one event card', async ({ page }) => {
    // After pipeline there should be at least one event
    const card = page.locator('.event-card').first();
    await expect(card).toBeVisible({ timeout: 10_000 });
  });

  test('event card shows title, confidence badge and source count', async ({ page }) => {
    const card = page.locator('.event-card').first();
    await expect(card.locator('.event-title')).toBeVisible();
    await expect(card.locator('.badge')).toBeVisible();
    // "sources" in the footer span — scope to .event-footer to avoid matching the title
    await expect(card.locator('.event-footer').getByText(/\d+ sources/)).toBeVisible();
  });

  test('filter dropdown changes the visible events', async ({ page }) => {
    // The confidence filter dropdown is present
    const confidenceSelect = page.locator('select').nth(1);
    await expect(confidenceSelect).toBeVisible();
    await confidenceSelect.selectOption('confirmed');
    // After filtering the UI updates without error
    await expect(page.locator('.filters-bar')).toBeVisible();
  });

  test('clicking an event card navigates to the detail view', async ({ page }) => {
    await page.locator('.event-card').first().click();
    // Header changes to the event title (not "Event Feed")
    await expect(page.getByRole('heading', { name: 'Event Feed' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: /back to events/i })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Event Detail
// ---------------------------------------------------------------------------

test.describe('Event Detail view', () => {
  test.beforeEach(async ({ page }) => {
    await runPipeline(page);
    await page.getByRole('button', { name: /view event feed/i }).click();
    await page.locator('.event-card').first().click();
    await expect(page.getByRole('button', { name: /back to events/i })).toBeVisible();
  });

  test('shows back button and event metadata', async ({ page }) => {
    await expect(page.getByRole('button', { name: /back to events/i })).toBeVisible();
    // Some metadata badge should be present (confidence, etc.)
    await expect(page.locator('.badge').first()).toBeVisible();
  });

  test('shows fact layer section', async ({ page }) => {
    await expect(page.getByText(/facts agreed across sources/i)).toBeVisible();
  });

  test('shows source claims table', async ({ page }) => {
    await expect(page.getByText(/source claims/i)).toBeVisible();
  });

  test('back button returns to Event Feed', async ({ page }) => {
    await page.getByRole('button', { name: /back to events/i }).click();
    await expect(page.getByRole('heading', { name: 'Event Feed' })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Review Console
// ---------------------------------------------------------------------------

test.describe('Review Console view', () => {
  test.beforeEach(async ({ page }) => {
    await runPipeline(page);
    await page.getByRole('button', { name: /review console/i }).click();
    await expect(page.getByRole('heading', { name: 'Review Console' })).toBeVisible();
  });

  test('shows dashboard stats', async ({ page }) => {
    await expect(page.getByText(/total events/i)).toBeVisible();
  });

  test('shows events list', async ({ page }) => {
    const rows = page.locator('.review-row, .event-card');
    await expect(rows.first()).toBeVisible({ timeout: 10_000 });
  });
});

// ---------------------------------------------------------------------------
// Articles view
// ---------------------------------------------------------------------------

test.describe('Articles view', () => {
  test.beforeEach(async ({ page }) => {
    await runPipeline(page);
    await page.getByRole('button', { name: /articles/i }).click();
    await expect(page.getByRole('heading', { name: 'Articles' })).toBeVisible();
  });

  test('shows articles list after pipeline run', async ({ page }) => {
    // Articles are rendered as buttons in a column; check the heading
    await expect(page.getByText(/articles \(\d+\)/i)).toBeVisible({ timeout: 10_000 });
  });

  test('clicking an article shows its claims', async ({ page }) => {
    // Articles are <button> elements in the left column
    await page.locator('button.btn').first().click();
    // Extracted Claims pane should appear
    await expect(page.getByText(/extracted claims/i)).toBeVisible({ timeout: 10_000 });
  });
});

// ---------------------------------------------------------------------------
// Sidebar navigation
// ---------------------------------------------------------------------------

test.describe('Sidebar navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('can switch between all views using the sidebar', async ({ page }) => {
    const nav = page.locator('.sidebar-nav');

    // Event Feed
    await nav.getByRole('button', { name: /event feed/i }).click();
    await expect(page.getByRole('heading', { name: 'Event Feed' })).toBeVisible();

    // Review Console
    await nav.getByRole('button', { name: /review console/i }).click();
    await expect(page.getByRole('heading', { name: 'Review Console' })).toBeVisible();

    // Articles
    await nav.getByRole('button', { name: /articles/i }).click();
    await expect(page.getByRole('heading', { name: 'Articles' })).toBeVisible();

    // Pipeline
    await nav.getByRole('button', { name: /pipeline/i }).click();
    await expect(page.getByRole('heading', { name: 'Pipeline Runner' })).toBeVisible();
  });

  test('active nav button is highlighted', async ({ page }) => {
    // Pipeline nav button (scoped to sidebar) should be active on load
    const nav = page.locator('.sidebar-nav');
    const pipelineBtn = nav.getByRole('button', { name: /pipeline/i });
    await expect(pipelineBtn).toHaveClass(/active/);

    // After clicking Event Feed it becomes active
    await nav.getByRole('button', { name: /event feed/i }).click();
    await expect(nav.getByRole('button', { name: /event feed/i })).toHaveClass(/active/);
    await expect(pipelineBtn).not.toHaveClass(/active/);
  });

  test('sidebar footer shows event count after pipeline run', async ({ page }) => {
    await runPipeline(page);
    // Navigate to Review Console which triggers stats load
    await page.locator('.sidebar-nav').getByRole('button', { name: /review console/i }).click();
    await expect(page.getByRole('heading', { name: 'Review Console' })).toBeVisible();
    // Footer should now show "<n> events"
    const footer = page.locator('.sidebar-footer');
    await expect(footer).toContainText(/\d+ events/i, { timeout: 10_000 });
  });
});
