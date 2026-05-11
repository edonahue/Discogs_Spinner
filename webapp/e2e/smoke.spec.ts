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
  STUB_STATUS,
  STUB_COLLECTION,
  STUB_COLLECTION_SUMMARY,
  STUB_COLLECTION_SUMMARY_AFTER_SYNC,
  STUB_COLLECTION_AFTER_SYNC,
  STUB_COLLECTION_DETAIL,
  STUB_COLLECTION_SYNC_SUMMARY,
  STUB_WANTLIST,
  STUB_WANTLIST_AFTER_SYNC,
  STUB_WANTLIST_DETAIL,
  STUB_WANTLIST_SYNC_SUMMARY,
  STUB_VALUE_DASHBOARD,
  STUB_VALUE_QUEUE,
  STUB_HIDDEN_GEMS,
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

function fulfillError(route: Route, message: string, status = 500) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify({
      ok: false,
      data: null,
      error: {
        code: "sync_failed",
        message,
        retryable: true,
        details: null,
      },
      meta: {},
    }),
  });
}

async function mockSetup(page: Page) {
  await page.route("**/api/v1/setup**", (r) => fulfill(r, STUB_SETUP));
}

async function mockCollectionRoutes(page: Page) {
  await page.route("**/api/v1/releases/summary?**", (r) =>
    fulfill(r, STUB_COLLECTION_SUMMARY)
  );
  await page.route("**/api/v1/releases/1?with_value=true", (r) =>
    fulfill(r, STUB_COLLECTION_DETAIL)
  );
  await page.route("**/api/v1/releases/2?with_value=true", (r) =>
    fulfill(r, {
      ...STUB_COLLECTION_DETAIL,
      data: {
        ...STUB_COLLECTION_DETAIL.data,
        discogs_release_id: 2,
        title: "Innervisions",
        artist: "Stevie Wonder",
        year: 1973,
      },
    })
  );
  await page.route("**/api/v1/releases/1/tracklist**", (r) =>
    fulfill(r, STUB_TRACKLIST)
  );
  await page.route("**/api/v1/releases?**", (r) => fulfill(r, STUB_COLLECTION));
}

async function mockWantlistRoutes(page: Page) {
  await page.route("**/api/v1/wantlist/10?with_value=true", (r) =>
    fulfill(r, STUB_WANTLIST_DETAIL)
  );
  await page.route("**/api/v1/wantlist?**", (r) => fulfill(r, STUB_WANTLIST));
}

async function mockValueRoutes(page: Page) {
  await page.route("**/api/v1/value/dashboard**", (r) =>
    fulfill(r, STUB_VALUE_DASHBOARD)
  );
  await page.route("**/api/v1/value/queue**", (r) =>
    fulfill(r, STUB_VALUE_QUEUE)
  );
  await page.route("**/api/v1/value/gems**", (r) =>
    fulfill(r, STUB_HIDDEN_GEMS)
  );
}

async function saveScreenshot(page: Page, filename: string) {
  if (!SAVE_SCREENSHOTS) return;
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename) });
}

// ── Collection ──────────────────────────────────────────────────────────────

test("Collection page renders release list", async ({ page }) => {
  await mockSetup(page);
  await mockCollectionRoutes(page);

  await page.goto("/collection");
  await expect(page.locator("h1")).toHaveText("Collection");
  await expect(page.locator("li")).toHaveCount(3);
  await expect(page.locator("li").first()).toContainText("Miles Davis");
  await expect(page.getByLabel("Collection summary")).toContainText("LPs");
  await expect(page.getByLabel("Collection summary")).toContainText("55.49");

  await saveScreenshot(page, "01-collection.png");
});

// ── Wantlist ────────────────────────────────────────────────────────────────

test("Wantlist page renders wantlist entries", async ({ page }) => {
  await mockSetup(page);
  await mockWantlistRoutes(page);

  await page.goto("/wantlist");
  await expect(page.locator("h1")).toHaveText("Wantlist");
  await expect(page.locator("li")).toHaveCount(1);
  await expect(page.locator("li").first()).toContainText("Portishead");
});

// ── Value ───────────────────────────────────────────────────────────────────

test("Value page renders top releases", async ({ page }) => {
  await mockSetup(page);
  await mockCollectionRoutes(page);
  await mockValueRoutes(page);

  await page.goto("/value");
  await expect(page.locator("h1")).toHaveText("Collection Value");
  await expect(page.getByText("Kind of Blue")).toBeVisible();
  await expect(page.getByText("Hidden Gems")).toBeVisible();
  await expect(
    page.locator("section").filter({ hasText: "Hidden Gems" }).getByText("Innervisions")
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "View in Collection" }).first()).toBeVisible();
});

test("Value page keeps top releases visible if Hidden Gems fails", async ({ page }) => {
  await mockSetup(page);
  await mockCollectionRoutes(page);
  await page.route("**/api/v1/value/dashboard**", (r) =>
    fulfill(r, STUB_VALUE_DASHBOARD)
  );
  await page.route("**/api/v1/value/queue**", (r) =>
    fulfill(r, STUB_VALUE_QUEUE)
  );
  await page.route("**/api/v1/value/gems**", (r) =>
    fulfillError(r, "Hidden Gems unavailable.", 503)
  );

  await page.goto("/value");
  await expect(page.getByText("Kind of Blue")).toBeVisible();
  await expect(page.getByText("Hidden Gems are temporarily unavailable")).toBeVisible();
  await expect(page.getByRole("link", { name: "View in Collection" }).first()).toBeVisible();
});

// ── Health ──────────────────────────────────────────────────────────────────

test("Collection Health page renders score", async ({ page }) => {
  await mockSetup(page);
  await page.route("**/api/v1/value/health**", (r) =>
    fulfill(r, STUB_HEALTH)
  );

  await page.goto("/health");
  await expect(page.locator("h1")).toHaveText("Collection Health");
  await expect(page.getByText("82")).toBeVisible();

  await saveScreenshot(page, "04-health.png");
});

// ── Recent ──────────────────────────────────────────────────────────────────

test("Recently Added page renders releases", async ({ page }) => {
  await mockSetup(page);
  await mockCollectionRoutes(page);
  await page.route("**/api/v1/releases/recent**", (r) =>
    fulfill(r, STUB_RECENT)
  );

  await page.goto("/recent");
  await expect(page.locator("h1")).toHaveText("Recently Added");
  await expect(page.locator("li")).toHaveCount(3);
  await expect(page.locator("li").first()).toContainText("Miles Davis");
  await expect(page.getByRole("link", { name: "View in Collection" }).first()).toBeVisible();

  await saveScreenshot(page, "03-recent.png");
});

// ── Analytics ───────────────────────────────────────────────────────────────

test("Collection Analytics page renders stats", async ({ page }) => {
  await mockSetup(page);
  await page.route("**/api/v1/analytics**", (r) =>
    fulfill(r, STUB_ANALYTICS)
  );

  await page.goto("/analytics");
  await expect(page.locator("h1")).toHaveText("Collection Analytics");
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
  await mockCollectionRoutes(page);

  await page.goto("/collection");
  await expect(page.locator("li").first()).toContainText("Miles Davis");
  await page.locator("li").first().click();

  // Modal should appear with track data
  await expect(page.getByText("So What")).toBeVisible();
});

test("Value page handoff opens focused collection detail", async ({ page }) => {
  await mockSetup(page);
  await mockCollectionRoutes(page);
  await mockValueRoutes(page);

  await page.goto("/value");
  await page.getByRole("link", { name: "View in Collection" }).first().click();

  await expect(page).toHaveURL(/\/collection\?focus=1$/);
  await expect(page.getByText("Focused Collection Detail")).toBeVisible();
  await expect(page.locator('li[aria-current="true"]')).toContainText("Miles Davis");
});

test("Recent page handoff opens focused collection detail", async ({ page }) => {
  await mockSetup(page);
  await mockCollectionRoutes(page);
  await page.route("**/api/v1/releases/recent**", (r) =>
    fulfill(r, STUB_RECENT)
  );

  await page.goto("/recent");
  await page.getByRole("link", { name: "View in Collection" }).first().click();

  await expect(page).toHaveURL(/\/collection\?focus=1$/);
  await expect(page.getByText("Focused Collection Detail")).toBeVisible();
});

test("Wantlist page can focus an item in place", async ({ page }) => {
  await mockSetup(page);
  await mockWantlistRoutes(page);

  await page.goto("/wantlist");
  await page.locator("li").first().click();

  await expect(page).toHaveURL(/\/wantlist\?focus=10$/);
  await expect(page.getByText("Focused Wantlist Detail")).toBeVisible();
  await expect(page.getByText("Prefer an early UK pressing.")).toBeVisible();
});

test("Home page sync buttons await completion and refresh status", async ({ page }) => {
  await mockSetup(page);

  let statusPayload = {
    ...STUB_STATUS,
    data: STUB_STATUS.data ? { ...STUB_STATUS.data } : null,
  };
  let releaseCollectionSync: (() => void) | null = null;
  const collectionSyncGate = new Promise<void>((resolve) => {
    releaseCollectionSync = resolve;
  });

  await page.route("**/api/v1/status", (r) => fulfill(r, statusPayload));
  await page.route("**/api/v1/sync/collection", async (r) => {
    await collectionSyncGate;
    statusPayload = {
      ...statusPayload,
      data: statusPayload.data
        ? {
            ...statusPayload.data,
            release_count_total: 4,
            release_count_active: 4,
            mapped_count: 3,
            unmatched_count: 1,
            last_sync_time: "2026-04-18T14:00:00",
          }
        : statusPayload.data,
    };
    await fulfill(r, STUB_COLLECTION_SYNC_SUMMARY);
  });
  await page.route("**/api/v1/sync/wantlist", async (r) => {
    statusPayload = {
      ...statusPayload,
      data: statusPayload.data
        ? {
            ...statusPayload.data,
            wantlist_count: 2,
          }
        : statusPayload.data,
    };
    await fulfill(r, STUB_WANTLIST_SYNC_SUMMARY);
  });

  await page.goto("/");

  const activeCard = page.locator(".app-stat-card").filter({ hasText: "Active releases" });
  const wantlistCard = page.locator(".app-stat-card").filter({ hasText: "Wantlist entries" });
  const syncCollectionButton = page.locator(".app-inline-actions button").first();

  await expect(activeCard).toContainText("3");
  await syncCollectionButton.click();
  await expect(syncCollectionButton).toBeDisabled();
  await expect(syncCollectionButton).toHaveText("Syncing…");

  releaseCollectionSync?.();

  await expect(page.getByText("Collection sync complete: fetched 4, upserted 4, deactivated 0.")).toBeVisible();
  await expect(syncCollectionButton).toBeEnabled();
  await expect(activeCard).toContainText("4");

  await page.locator(".app-inline-actions button").nth(1).click();
  await expect(page.getByText("Wantlist sync complete: fetched 2, upserted 2, deactivated 0.")).toBeVisible();
  await expect(wantlistCard).toContainText("2");
});

test("Collection page sync reloads releases and preserves focused detail", async ({ page }) => {
  await mockSetup(page);

  let collectionPayload = STUB_COLLECTION;
  let collectionSummaryPayload = STUB_COLLECTION_SUMMARY;
  await page.route("**/api/v1/releases/1?with_value=true", (r) =>
    fulfill(r, STUB_COLLECTION_DETAIL)
  );
  await page.route("**/api/v1/releases/1/tracklist**", (r) =>
    fulfill(r, STUB_TRACKLIST)
  );
  await page.route("**/api/v1/releases/summary?**", (r) =>
    fulfill(r, collectionSummaryPayload)
  );
  await page.route("**/api/v1/releases?**", (r) => fulfill(r, collectionPayload));
  await page.route("**/api/v1/sync/collection", async (r) => {
    collectionPayload = STUB_COLLECTION_AFTER_SYNC;
    collectionSummaryPayload = STUB_COLLECTION_SUMMARY_AFTER_SYNC;
    await fulfill(r, STUB_COLLECTION_SYNC_SUMMARY);
  });

  await page.goto("/collection?focus=1");
  await expect(page.locator("li")).toHaveCount(3);

  await page.getByRole("button", { name: "Sync Collection" }).click();

  await expect(page.getByText("Collection sync complete: fetched 4, upserted 4, deactivated 0.")).toBeVisible();
  await expect(page.locator("li")).toHaveCount(4);
  await expect(page).toHaveURL(/\/collection\?focus=1$/);
  await expect(page.getByText("Focused Collection Detail")).toBeVisible();
  await expect(page.locator('li[aria-current="true"]')).toContainText("Miles Davis");
  await expect(page.getByLabel("Collection summary")).toContainText("88.49");
});

test("Wantlist page sync reloads entries and preserves focused detail", async ({ page }) => {
  await mockSetup(page);

  let wantlistPayload = STUB_WANTLIST;
  await page.route("**/api/v1/wantlist/10?with_value=true", (r) =>
    fulfill(r, STUB_WANTLIST_DETAIL)
  );
  await page.route("**/api/v1/wantlist?**", (r) => fulfill(r, wantlistPayload));
  await page.route("**/api/v1/sync/wantlist", async (r) => {
    wantlistPayload = STUB_WANTLIST_AFTER_SYNC;
    await fulfill(r, STUB_WANTLIST_SYNC_SUMMARY);
  });

  await page.goto("/wantlist?focus=10");
  await expect(page.locator("li")).toHaveCount(1);

  await page.getByRole("button", { name: "Sync Wantlist" }).click();

  await expect(page.getByText("Wantlist sync complete: fetched 2, upserted 2, deactivated 0.")).toBeVisible();
  await expect(page.locator("li")).toHaveCount(2);
  await expect(page).toHaveURL(/\/wantlist\?focus=10$/);
  await expect(page.getByText("Focused Wantlist Detail")).toBeVisible();
  await expect(page.locator('li[aria-current="true"]')).toContainText("Portishead");
});

test("Collection page sync failure keeps the current list visible", async ({ page }) => {
  await mockSetup(page);
  await mockCollectionRoutes(page);
  await page.route("**/api/v1/sync/collection", (r) =>
    fulfillError(r, "Discogs collection sync failed.", 503)
  );

  await page.goto("/collection");
  await expect(page.locator("li")).toHaveCount(3);

  await page.getByRole("button", { name: "Sync Collection" }).click();

  await expect(page.getByText("Discogs collection sync failed.")).toBeVisible();
  await expect(page.locator("li")).toHaveCount(3);
  await expect(page.locator("li").first()).toContainText("Miles Davis");
});

test.describe("responsive layouts", () => {
  test.use({ viewport: { width: 900, height: 700 } });

  test("Collection page keeps nav and filters usable at 900px wide", async ({ page }) => {
    await mockSetup(page);
    await mockCollectionRoutes(page);

    await page.goto("/collection");
    await expect(page.getByRole("link", { name: "Analytics" })).toBeVisible();
    await expect(page.getByPlaceholder("Search artist or title")).toBeVisible();
    await expect(page.getByRole("button", { name: "Clear Filters" })).toBeVisible();
  });

  test("Value page keeps handoff actions visible at 900px wide", async ({ page }) => {
    await mockSetup(page);
    await mockCollectionRoutes(page);
    await mockValueRoutes(page);

    await page.goto("/value");
    await expect(page.getByRole("link", { name: "View in Collection" }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Refresh Values" })).toBeVisible();
  });

  test("Wantlist page keeps focused detail in place at 900px wide", async ({ page }) => {
    await mockSetup(page);
    await mockWantlistRoutes(page);

    await page.goto("/wantlist");
    await page.locator("li").first().click();

    await expect(page).toHaveURL(/\/wantlist\?focus=10$/);
    await expect(page.getByText("Focused Wantlist Detail")).toBeVisible();
    await expect(page.locator('li[aria-current="true"]')).toContainText("Portishead");
    await expect(page.locator("li").first()).toBeVisible();
  });
});
