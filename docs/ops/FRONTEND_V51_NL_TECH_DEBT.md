# Dette technique — sprint NL frontend V5.1

Document de suivi post-revue **CONDITIONAL GO** (lecture froide). Non bloquant pour merge une fois CI E2E verte.

| ID | Sujet | Cible / artefact | Sprint cible |
|----|--------|------------------|--------------|
| **NL-04-vertical** | Virtualiser les **lignes** (critères) dans la matrice, pas seulement les colonnes offres | [`frontend-v51/components/workspace/comparative-table.tsx`](../../frontend-v51/components/workspace/comparative-table.tsx) | V5.2 |
| **NL-07** | Endpoint PDF page / split view | [`MANDAT_NL07_PDF_PAGE_ENDPOINT.md`](./MANDAT_NL07_PDF_PAGE_ENDPOINT.md) | Dès backend prêt |
| **Next.js 16** | Avertissement *middleware → proxy* au build | ADR ou ticket outillage — aligner sur la doc Next 16 | Upgrade / housekeeping |
| **Playwright TLS local** | Proxy d’entreprise / certificat manquant sur poste dev | [`docs/ops/DEV_SETUP.md`](./DEV_SETUP.md) § Playwright | Immédiat (doc) |

## Référence

- Seuil virtualisation horizontale : `VIRTUAL_SUP_THRESHOLD` dans `comparative-table.tsx` (commentaire NL-04).
