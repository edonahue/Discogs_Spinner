/**
 * Webapp E2E smoke tests — no live backend required.
 *
 * All API calls are intercepted by Playwright's page.route() and served
 * from typed stub fixtures, making the suite deterministic and CI-safe.
 *
 * Optional screenshot mode:
 *   SAVE_SCREENSHOTS=1 npm run test:e2e
 * Outputs PNGs to docs/media/screenshots/webapp/.
 */

import * as path from "path";
import * as fs from "fs";
import { fileURLToPath } from "url";
import { test, expect, Page, Route } from "@playwright/test";
import {
  STUB_SETUP,
  STUB_COLLECTION,
  STUB_WANTLIST,
  STUB_VALUE_DASHBOARD,
  STUB_VALUE_QUEUE,
  STUB_HEALTH,
  STUB_RECENT,
  STUB_ANALYTICS,
  STUB_TRACKLIST,
} from "./fixtures";

const SAVE_SCREENSHOTS = !!process.env.SAVE_SCREENSHOTS;
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = path.resolve(
  __dirname,
  "../../docs/media/screenshots/webapp"
);

function fulfill(route: Route, json: unknown) {
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(json),
  });
}

async function mockSetup(page: Page) {
  await page.route("**/api/v1/setup**", (r) => fulfill(r, STUB_SETUP));
}

async function saveScreenshot(page: Page, filename: string) {
  if (!SAVE_SCREENSHOTS) return;
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename) });
}

// ── Collection ──────────────────────────────────────────────────────────────

test("Collection page renders release list", async ({ page }) => {
  await mockSetup(page);
  await page.route("**/api/v1/releases**", (r) => fulfill(r, STUB_COLLECTION));

  await page.goto("/collection");
  await expect(page.locator("h2")).toHaveText("Collection");
  await expect(page.locator("li")).toHaveCount(3);
  await expect(page.locator("li").first()).toContainText("Miles Davis");

  await saveScreenshot(page, "01-collection.png");
});

// ── Wantlist ────────────────────────────────────────────────────────────────

test("Wantlist page renders wantlist entries", async ({ page }) => {
  await mockSetup(page);
  await page.route("**/api/v1/wantlist**", (r) => fulfill(r, STUB_WANTLIST));

  await page.goto("/wantlist");
  await expect(page.locator("h2")).toHaveText("Wantlist");
  await expect(page.locator("li")).toHaveCount(1);
  await expect(page.locator("li").first()).toContainText("Portishead");
});

// ── Value ───────────────────────────────────────────────────────────────────

test("Value page renders top releases", async ({ page }) => {
  await mockSetup(page);
  await page.route("**/api/v1/value/dashboard**", (r) =>
    fulfill(r, STUB_VALUE_DASHBOARD)
  );
  await page.route("**/api/v1/value/queue**", (r) =>
    fulfill(r, STUB_VALUE_QUEUE)
  );

  await page.goto("/value");
  await expect(page.locator("h2")).toHaveText("Collection Value");
  await expect(page.getByText("Kind of Blue")).toBeVisible();
});

// ── Health ──────────────────────────────────────────────────────────────────

test("Collection Health page renders score", async ({ page }) => {
  await mockSetup(page);
  await page.route("**/api/v1/value/health**", (r) =>
    fulfill(r, STUB_HEALTH)
  );

  await page.goto("/health");
  await expect(page.locator("h2")).toHaveText("Collection Health");
  await expect(page.getByText("82")).toBeVisible();

  await saveScreenshot(page, "04-health.png");
});

// ── Recent ──────────────────────────────────────────────────────────────────

test("Recently Added page renders releases", async ({ page }) => {
  await mockSetup(page);
  await page.route("**/api/v1/releases/recent**", (r) =>
    fulfill(r, STUB_RECENT)
  );

  await page.goto("/recent");
  await expect(page.locator("h2")).toHaveText("Recently Added");
  await expect(page.locator("li")).toHaveCount(3);
  await expect(page.locator("li").first()).toContainText("Miles Davis");

  await saveScreenshot(page, "03-recent.png");
});

// ── Analytics ───────────────────────────────────────────────────────────────

test("Collection Analytics page renders stats", async ({ page }) => {
  await mockSetup(page);
  await page.route("**/api/v1/analytics**", (r) =>
    fulfill(r, STUB_ANALYTICS)
  );

  await page.goto("/analytics");
  await expect(page.locator("h2")).toHaveText("Collection Analytics");
  // Summary counters
  await expect(page.getByText("150")).toBeVisible();  // release_count_active
  await expect(page.getByText("120")).toBeVisible();  // mapped_count
  // Top genres table heading
  await expect(page.getByText("Top Genres")).toBeVisible();

  await saveScreenshot(page, "02-analytics.png");
});

// ── Tracklist modal (Collection page) ───────────────────────────────────────

test("Tracklist modal opens on release click", async ({ page }) => {
  await mockSetup(page);
  await page.route("**/api/v1/releases**", (r) => fulfill(r, STUB_COLLECTION));
  await page.route("**/api/v1/releases/1/tracklist**", (r) =>
    fulfill(r, STUB_TRACKLIST)
  );

  await page.goto("/collection");
  await expect(page.locator("li").first()).toContainText("Miles Davis");
  await page.locator("li").first().click();

  // Modal should appear with track data
  await expect(page.getByText("So What")).toBeVisible();
});
