# fix(a11y): WCAG Level A compliance

Fixes #55, #56, #57, #58, #59, #60, #61, #63, #64, #66

**WCAG Level A compliance – no functional or visual changes**

## Summary

Patch de conformité accessibilité (normes WCAG Level A). Aucune modification fonctionnelle, métier, visuelle ou architecturale.

## Corrections par issue

| Issue | Correction |
|-------|------------|
| #55 | Labels associés aux inputs (`for`/`id`), `aria-label` sur champs |
| #56 | `aria-label` sur boutons d'upload fichier |
| #57 | Skip links + `role="main"` + `id="main-content"` |
| #58 | `scope="col"` sur `<th>`, `<caption>` sr-only sur table |
| #59 | `aria-live`, `role="status"`, `aria-atomic` sur zones dynamiques |
| #60 | `:focus-visible` sur liens et boutons |
| #61 | Canvas chart: wrapper `role="img"` + `#chart-summary` sr-only alimenté par JS |
| #63 | ARIA sur éléments créés en JS (role, aria-label, aria-hidden pour emojis) |
| #64 | `role="alert"`, `aria-live="assertive"` sur statuts async/erreurs |
| #66 | `:focus` / `:focus-visible` dans styles.css |

## Fichiers modifiés

- `static/index.html` – labels, skip link, ARIA
- `templates/index.html`, `dashboard.html`, `committee.html`, `offre_detail.html` – skip links, focus, labels
- `styles.css` – focus styles, sr-only, skip-link
- `static/styles.css` – copie pour servir /static/
- `app.js`, `static/app.js` – ARIA sur éléments dynamiques
- `static/dashboard.js` – chart summary, table roles, liens

## Validation

- Pas de modification de logique applicative
- Rendu visuel identique
- Diffs limités aux attributs HTML/ARIA, CSS accessibilité
