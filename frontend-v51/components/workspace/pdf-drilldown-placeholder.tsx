"use client";

/**
 * NL-07 — Drill-down PDF (split extraction ↔ original).
 * Le backend n’expose pas encore d’endpoint page PDF ; ce bloc documente l’intention produit.
 * Voir docs/ops/MANDAT_NL07_PDF_PAGE_ENDPOINT.md
 */
export function PdfDrilldownPlaceholder() {
  return (
    <div
      className="rounded-lg border border-dashed border-gray-300 p-4 text-sm text-gray-600 dark:border-gray-600 dark:text-gray-400"
      data-testid="pdf-drilldown-placeholder"
    >
      <p className="font-medium text-gray-800 dark:text-gray-200">
        Analyse PDF (NL-07)
      </p>
      <p className="mt-1">
        Vue fractionnée document source / extrait — en attente d’un endpoint API
        dédié (mandat CTO). Aucune donnée sensible n’est chargée ici.
      </p>
    </div>
  );
}
