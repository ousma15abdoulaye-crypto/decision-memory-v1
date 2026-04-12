/**
 * Regex (une ligne = un motif) pour les chemins API consommés par le frontend V5.1.
 * Tenir à jour en même temps que `app/`, `components/`, `lib/`.
 *
 * Voir `types/README.md` — ce fichier n’est pas le schéma OpenAPI complet.
 */
export const CONSUMED_API_PATH_REGEXES = [
  String.raw`^/api/auth/login$`,
  String.raw`^/api/auth/ws-token$`,
  String.raw`^/api/dashboard$`,
  String.raw`^/api/agent/prompt$`,
  String.raw`^/api/workspaces$`,
  String.raw`^/api/workspaces/[^/]+$`,
  String.raw`^/api/workspaces/[^/]+/bundles$`,
  String.raw`^/api/workspaces/[^/]+/upload-zip$`,
  String.raw`^/api/workspaces/[^/]+/run-pipeline`,
  String.raw`^/api/workspaces/[^/]+/comments$`,
  String.raw`^/api/workspaces/[^/]+/status$`,
  String.raw`^/api/workspaces/[^/]+/cognitive-state$`,
  String.raw`^/api/workspaces/[^/]+/committee/pv`,
  String.raw`^/api/workspaces/[^/]+/m16/sync-from-m14$`,
  String.raw`^/api/workspaces/[^/]+/comparative-matrix$`,
] as const;
