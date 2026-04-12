"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function PvExportButtons({ workspaceId }: { workspaceId: string }) {
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

  const run = async (format: "json" | "pdf" | "xlsx") => {
    setErr(null);
    setLoading(format);
    try {
      const { blob, filename } = await api.downloadBlob(
        `/api/workspaces/${workspaceId}/committee/pv?format=${format}`,
      );
      const ext = format === "xlsx" ? "xlsx" : format;
      triggerDownload(
        blob,
        filename?.replace(/[/\\]/g, "_") ?? `pv_${workspaceId}.${ext}`,
      );
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.status === 404) {
          setErr(
            "Session comité introuvable — impossible d’exporter le PV (ouvrir/sceller le processus selon le parcours métier).",
          );
        } else if (e.status === 409) {
          setErr(
            "PV non disponible : la session comité n’est pas scellée ou le snapshot n’est pas prêt.",
          );
        } else if (e.status === 403) {
          setErr("Accès refusé pour l’export PV.");
        } else {
          setErr(e.message || "Échec du téléchargement.");
        }
      } else {
        setErr("Erreur réseau.");
      }
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-2" data-testid="pv-export-buttons">
      <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
        Exports PV (session scellée)
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={!!loading}
          onClick={() => run("json")}
          data-testid="pv-export-json"
        >
          {loading === "json" ? "…" : "JSON"}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={!!loading}
          onClick={() => run("pdf")}
          data-testid="pv-export-pdf"
        >
          {loading === "pdf" ? "…" : "PDF"}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={!!loading}
          onClick={() => run("xlsx")}
          data-testid="pv-export-xlsx"
        >
          {loading === "xlsx" ? "…" : "XLSX"}
        </Button>
      </div>
      {err && (
        <p className="text-sm text-amber-700 dark:text-amber-300" role="alert">
          {err}
        </p>
      )}
    </div>
  );
}
