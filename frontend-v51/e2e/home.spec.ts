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
