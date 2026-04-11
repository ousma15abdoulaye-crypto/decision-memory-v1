"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api-client";

interface BridgeResult {
  created: number;
  updated: number;
  skipped: number;
  unmapped_bundles: string[];
  unmapped_criteria: string[];
  errors: string[];
}

export function M14SyncButton({ workspaceId }: { workspaceId: string }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BridgeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSync() {
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await api.post<BridgeResult>(
        `/api/workspaces/${workspaceId}/m16/sync-from-m14`,
        {},
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erreur lors de la synchronisation");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <button
          type="button"
          data-m14-sync
          onClick={handleSync}
          disabled={loading}
          className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-sm font-medium text-[var(--foreground)] hover:bg-gray-50 disabled:opacity-50 dark:hover:bg-gray-800"
        >
          {loading ? "Synchronisation…" : "Sync scores M14 → M16"}
        </button>
        <span className="text-xs text-[var(--foreground-muted)]">
          Pré-remplit les assessments depuis les scores M14 calculés
        </span>
      </div>

      {error && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {result && (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 text-sm">
          <p className="font-semibold text-[var(--foreground)]">
            Synchronisation terminée
          </p>
          <div className="mt-2 grid grid-cols-3 gap-3 text-center">
            <div className="rounded-md bg-green-50 p-2 dark:bg-green-950">
              <div className="text-lg font-bold text-green-700 dark:text-green-300">{result.created}</div>
              <div className="text-xs text-green-600 dark:text-green-400">Créés</div>
            </div>
            <div className="rounded-md bg-blue-50 p-2 dark:bg-blue-950">
              <div className="text-lg font-bold text-blue-700 dark:text-blue-300">{result.updated}</div>
              <div className="text-xs text-blue-600 dark:text-blue-400">Mis à jour</div>
            </div>
            <div className="rounded-md bg-gray-50 p-2 dark:bg-gray-900">
              <div className="text-lg font-bold text-[var(--foreground-muted)]">{result.skipped}</div>
              <div className="text-xs text-[var(--foreground-subtle)]">Ignorés</div>
            </div>
          </div>
          {result.unmapped_bundles.length > 0 && (
            <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
              {result.unmapped_bundles.length} offre(s) non mappée(s) —{" "}
              <span className="font-mono">{result.unmapped_bundles.slice(0, 2).join(", ")}</span>
              {result.unmapped_bundles.length > 2 && ` +${result.unmapped_bundles.length - 2}`}
            </p>
          )}
          {result.errors.length > 0 && (
            <ul className="mt-2 space-y-0.5 text-xs text-red-600 dark:text-red-400">
              {result.errors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

