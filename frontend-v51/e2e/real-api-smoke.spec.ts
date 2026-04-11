import { expect, test } from "@playwright/test";

const realApi = process.env.E2E_REAL_API === "1";
const email = process.env.E2E_LOGIN_EMAIL ?? "";
const password = process.env.E2E_LOGIN_PASSWORD ?? "";
const workspaceId = process.env.E2E_WORKSPACE_ID ?? "";

test.describe("Smoke API réelle (opt-in)", () => {
  test.beforeEach(() => {
    test.skip(
      !realApi,
      "Définir E2E_REAL_API=1 et les variables E2E_LOGIN_* / E2E_WORKSPACE_ID pour activer.",
    );
    test.skip(
      !email || !password || !workspaceId,
      "E2E_LOGIN_EMAIL, E2E_LOGIN_PASSWORD et E2E_WORKSPACE_ID requis lorsque E2E_REAL_API=1.",
    );
  });

  test("connexion puis page workspace sans mock de routes API", async ({
    page,
  }) => {
    await page.goto("/login");
    await page.getByLabel(/Email ou nom/i).fill(email);
    await page.getByLabel(/^Mot de passe$/i).fill(password);
    await page.getByRole("button", { name: /Se connecter/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 30_000 });

    await page.goto(`/workspaces/${workspaceId}`);

    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({
      timeout: 30_000,
    });
    await expect(
      page.getByRole("heading", { name: "Ingestion et pipeline" }),
    ).toBeVisible({ timeout: 15_000 });
  });
});
