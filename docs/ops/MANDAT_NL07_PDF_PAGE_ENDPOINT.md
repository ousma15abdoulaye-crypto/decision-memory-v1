# Mandat technique — NL-07 Drill-down PDF (split vue)

**Statut** : proposition de contrat — **non implémentée** dans l’API au 2026-04-09.  
**Frontend** : placeholder [`frontend-v51/components/workspace/pdf-drilldown-placeholder.tsx`](../../frontend-v51/components/workspace/pdf-drilldown-placeholder.tsx).

## Objectif produit

Permettre une **vue fractionnée** : extrait structuré (MQL / cadre d’évaluation) ↔ **page ou région du PDF source**, pour audit humain sans recalcul métier.

## Hors périmètre

- Pas de nouveau calcul de score dans l’endpoint.
- Pas d’exposition de fichiers hors périmètre workspace (RLS / `require_workspace_access`).

## Contrat API (proposition)

| Élément | Proposition |
|---------|-------------|
| Méthode | `GET` |
| Chemin (exemple) | `/api/workspaces/{workspace_id}/documents/{document_id}/pdf/page/{page_number}` |
| Réponse | `application/pdf` (bytes d’une seule page) **ou** `image/png` (rendu page) |
| AuthZ | Même modèle que les routes workspace existantes |
| Erreurs | 404 si document absent / page hors limites ; 403 si pas d’accès workspace |

Alternative acceptable : `GET .../preview?page=3&format=png` avec cache contrôlé.

## Tests attendus

- Test client `TestClient` : 403 sans accès ; 404 document inconnu.
- Pas de fuite : utilisateur A ne récupère pas le PDF du workspace B.

## Dépendances

- Bibliothèque de rendu PDF côté serveur (PyMuPDF, pdf2image, etc.) — **à valider** avec l’image Docker / Railway (taille image, deps système).
- Alignement avec la chaîne documents existante (`evaluation_documents`, bundles, etc.) — inventaire avant implémentation.

## Référence export PV existant

Export PV complet : [`src/api/routers/documents.py`](../../src/api/routers/documents.py) (`GET .../committee/pv`) — sert de modèle pour auth et `Response` binaire.
