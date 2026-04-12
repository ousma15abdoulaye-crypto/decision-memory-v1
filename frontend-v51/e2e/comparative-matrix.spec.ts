/**
 * Tests **UX** de la matrice comparative (filtres, clavier, zoom).
 *
 * Toutes les routes `/api/workspaces/**` sont **mockées** (pas de chaîne réelle
 * login → DB → pipeline). Ne constitue **pas** une preuve produit bout-en-bout.
 * Voir `e2e/README.md` et `real-api-smoke.spec.ts` (opt-in).
 */
import { expect, test } from "@playwright/test";

const WS_ID = "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee";

/** Cookie attendu par `middleware.ts` : JWT minimal avec `exp` futur (signature non vérifiée). */
function e2eDmsToken(): string {
  const exp = Math.floor(Date.now() / 1000) + 86_400;
  const payload = Buffer.from(JSON.stringify({ exp })).toString("base64url");
  return `e2e.${payload}.sig`;
}

const mockWorkspace = {
  id: WS_ID,
  reference_code: "E2E-WS",
  title: "Workspace test",
  process_type: "standard",
  status: "active",
  estimated_value: 0,
  currency: "XOF",
};

const mockCognitive = {
  state: "deliberation",
  label_fr: "Délibération",
  phase: "P3",
  completeness: 0.5,
  can_advance: false,
  advance_blockers: [],
  available_actions: [],
  confidence_regime: "green",
};

const sid1 = "11111111-1111-4111-8111-111111111111";
const sid2 = "22222222-2222-4222-8222-222222222222";

const mockComparativeMatrix = {
  schema_version: "comparative_matrix_v1",
  source: "m14",
  scores_matrix: {
    [sid1]: {
      c1: { score: 8, confidence: 0.8, signal: "green" },
      c2: { score: 4, confidence: 0.8, signal: "red" },
    },
    [sid2]: {
      c1: { score: 6, confidence: 0.8, signal: "yellow" },
      c2: { score: 7, confidence: 0.8, signal: "green" },
    },
  },
  criteria: [
    {
      id: "c1",
      criterion_key: "c1",
      critere_nom: "Critère 1",
      ponderation: 40,
      is_eliminatory: false,
    },
    {
      id: "c2",
      criterion_key: "c2",
      critere_nom: "Critère 2 ELIM",
      ponderation: 60,
      is_eliminatory: true,
    },
  ],
  suppliers: [
    { id: sid1, name: "Fournisseur A" },
    { id: sid2, name: "Fournisseur B" },
  ],
  weighted_totals: { [sid1]: 5.2, [sid2]: 6.1 },
  cognitive_state: "E5",
  cognitive_state_detail: {},
  committee_session: null,
  elimination_flags: [],
  market_signals: [],
  dissents: [],
  data_quality_score: 0.8,
  low_confidence_bundles: [],
  zones_of_clarification: [],
};

test.describe("Matrice comparative (NL-01 / NL-08 / NL-09)", () => {
  test.beforeEach(async ({ page }) => {
    const base = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000";
    await page.context().addCookies([
      {
        name: "dms_token",
        value: encodeURIComponent(e2eDmsToken()),
        url: base,
      },
    ]);

    await page.addInitScript(() => {
      window.localStorage.setItem(
        "dms-auth",
        JSON.stringify({ state: { accessToken: "e2e-fake-jwt" } }),
      );
    });

    const fulfillJson = (body: unknown) => ({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });

    await page.route("**/api/workspaces/**", async (route) => {
      const reqUrl = route.request().url();
      const path = new URL(reqUrl).pathname.replace(/\/$/, "");
      const base = `/api/workspaces/${WS_ID}`;
      if (path === base) {
        await route.fulfill(fulfillJson(mockWorkspace));
        return;
      }
      if (path.includes("/cognitive-state")) {
        await route.fulfill(fulfillJson(mockCognitive));
        return;
      }
      if (path.includes("/comparative-matrix")) {
        await route.fulfill(fulfillJson(mockComparativeMatrix));
        return;
      }
      if (path.includes("/bundles")) {
        await route.fulfill(
          fulfillJson({ workspace_id: WS_ID, bundles: [] }),
        );
        return;
      }
      await route.fulfill({ status: 404, body: "{}" });
    });
  });

  test("filtres et grille cliquable (focus clavier)", async ({ page }) => {
    await page.goto(`/workspaces/${WS_ID}`);

    const grid = page.getByTestId("comparative-table-grid");
    await expect(grid).toBeVisible({
      timeout: 15_000,
    });

    await page.getByTestId("filter-eliminatory").check();
    // Strict mode : même libellé dans la grille et hors grille (ex. zoom) — cibler la grille.
    await expect(grid.getByText("Critère 2 ELIM")).toBeVisible();
    await expect(grid.getByText("Critère 1")).not.toBeVisible();

    await page.getByTestId("filter-eliminatory").uncheck();
    await page.getByTestId("filter-red").check();
    await expect(grid.getByText("Critère 2 ELIM")).toBeVisible();

    await grid.click();
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("vue zoom fournisseur", async ({ page }) => {
    await page.goto(`/workspaces/${WS_ID}`);
    await expect(page.getByTestId("comparative-table-grid")).toBeVisible({
      timeout: 15_000,
    });
    await page.getByTestId("zoom-supplier").selectOption(sid1);
    await expect(
      page.getByRole("columnheader", { name: "Fournisseur A" }),
    ).toBeVisible();
  });
});
