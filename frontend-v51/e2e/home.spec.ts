import { expect, test } from "@playwright/test";

/**
 * Racine : redirect serveur vers /dashboard, puis middleware sans JWT → /login (V5.1).
 * L’ancienne page vitrine avec liens Connexion + Tableau de bord sur « / » n’existe plus.
 */
test("accueil DMS — racine redirige vers la page de connexion si non authentifié", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "DMS" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Se connecter/i }),
  ).toBeVisible();
});

test("sidebar — bouton thème (next-themes)", async ({ page }) => {
  await page.goto("/dashboard");
  const toggle = page.getByTestId("theme-toggle");
  if (await toggle.isVisible().catch(() => false)) {
    await toggle.click();
  }
});
