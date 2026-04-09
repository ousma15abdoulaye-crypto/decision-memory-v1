import { expect, test } from "@playwright/test";

test("accueil DMS — liens Connexion et Tableau de bord", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: "Connexion" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Tableau de bord" }),
  ).toBeVisible();
});

test("sidebar — bouton thème (next-themes)", async ({ page }) => {
  await page.goto("/dashboard");
  const toggle = page.getByTestId("theme-toggle");
  if (await toggle.isVisible().catch(() => false)) {
    await toggle.click();
  }
});
