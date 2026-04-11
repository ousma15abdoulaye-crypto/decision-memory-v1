"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type InputHTMLAttributes,
} from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";
import {
  fileListToSupplierZipFile,
  MAX_SERVER_ZIP_BYTES,
} from "@/lib/zip-directory";

interface SupplierBundleRow {
  id: string;
  vendor_name_raw?: string | null;
  vendor_id?: string | null;
  bundle_status?: string | null;
  completeness_score?: number | null;
  bundle_index?: number | null;
  assembled_at?: string | null;
}

interface BundlesResponse {
  workspace_id: string;
  bundles: SupplierBundleRow[];
}

interface UploadZipResponse {
  workspace_id: string;
  status: string;
  message: string;
}

interface PipelineV5Result {
  workspace_id: string;
  case_id?: string | null;
  completed: boolean;
  stopped_at?: string | null;
  error?: string | null;
  step_1_offers_extracted?: number;
  step_5_assessments_created?: number;
  duration_seconds?: number;
}

function isBlockedStatus(status: string | undefined): boolean {
  if (!status) return false;
  return status === "sealed" || status === "closed" || status === "cancelled";
}

export function WorkspaceIngestionPanel({
  workspaceId,
  workspaceStatus,
}: {
  workspaceId: string;
  workspaceStatus: string | undefined;
}) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const headingId = useId();
  const zipInputId = useId();
  const folderInputId = useId();
  const [passOnePending, setPassOnePending] = useState(false);
  const [zippingFolder, setZippingFolder] = useState(false);
  const [forceM14, setForceM14] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [pipelineSummary, setPipelineSummary] = useState<string | null>(null);

  const blocked = isBlockedStatus(workspaceStatus);

  const bundlesQuery = useQuery({
    queryKey: ["bundles", workspaceId],
    queryFn: () =>
      api.get<BundlesResponse>(`/api/workspaces/${workspaceId}/bundles`),
    enabled: !!workspaceId,
    refetchInterval: (query) => {
      if (!workspaceId || blocked) return false;
      const n = query.state.data?.bundles?.length ?? 0;
      if (workspaceStatus === "assembling") return 5_000;
      if (passOnePending && n === 0) return 5_000;
      return false;
    },
  });

  useEffect(() => {
    if (!passOnePending) return undefined;
    const t = window.setTimeout(() => setPassOnePending(false), 180_000);
    return () => window.clearTimeout(t);
  }, [passOnePending]);

  const uploadMutation = useMutation({
    onMutate: () => {
      setUploadMsg(null);
      setZippingFolder(false);
    },
    mutationFn: async (file: File) => {
      if (file.size > MAX_SERVER_ZIP_BYTES) {
        throw new Error(
          `ZIP trop volumineux (${Math.round(file.size / (1024 * 1024))} Mo). Limite serveur : ${Math.round(MAX_SERVER_ZIP_BYTES / (1024 * 1024))} Mo.`,
        );
      }
      const fd = new FormData();
      fd.append("file", file);
      return api.postMultipart<UploadZipResponse>(
        `/api/workspaces/${workspaceId}/upload-zip`,
        fd,
      );
    },
    onSuccess: (res) => {
      setUploadMsg(res.message ?? "Pass -1 accepté — traitement en arrière-plan.");
      setPassOnePending(true);
      void queryClient.invalidateQueries({ queryKey: ["bundles", workspaceId] });
      void queryClient.invalidateQueries({
        queryKey: ["cognitive-state", workspaceId],
      });
      void queryClient.invalidateQueries({ queryKey: ["workspace", workspaceId] });
    },
    onError: (err) => {
      setUploadMsg(
        err instanceof ApiError || err instanceof Error
          ? err.message
          : "Échec de l’envoi du ZIP.",
      );
    },
    onSettled: () => {
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (folderInputRef.current) folderInputRef.current.value = "";
    },
  });

  const pipelineMutation = useMutation({
    onMutate: () => {
      setPipelineSummary(null);
    },
    mutationFn: () => {
      const q = forceM14 ? "?force_m14=true" : "?force_m14=false";
      return api.postEmpty<PipelineV5Result>(
        `/api/workspaces/${workspaceId}/run-pipeline${q}`,
      );
    },
    onSuccess: (res) => {
      const parts = [
        res.completed ? "Pipeline terminé." : "Pipeline arrêté ou incomplet.",
        res.error ? `Détail : ${res.error}` : null,
        typeof res.duration_seconds === "number"
          ? `Durée : ${res.duration_seconds.toFixed(1)} s`
          : null,
      ].filter(Boolean);
      setPipelineSummary(parts.join(" "));
      void queryClient.invalidateQueries({
        queryKey: ["evaluation-frame", workspaceId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["cognitive-state", workspaceId],
      });
      void queryClient.invalidateQueries({ queryKey: ["workspace", workspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["bundles", workspaceId] });
    },
    onError: (err) => {
      setPipelineSummary(
        err instanceof ApiError ? err.message : "Échec du pipeline.",
      );
    },
  });

  const bundles = bundlesQuery.data?.bundles ?? [];
  const uploadBusy = uploadMutation.isPending || zippingFolder;

  return (
    <section
      className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm"
      aria-labelledby={headingId}
    >
      <h3
        id={headingId}
        className="mb-3 text-sm font-semibold text-[var(--foreground)]"
      >
        Ingestion et pipeline
      </h3>
      <div className="mb-4 space-y-2 text-xs text-[var(--foreground-muted)]">
        <p>
          L’API n’accepte qu’un fichier <strong className="text-[var(--foreground)]">.zip</strong>{" "}
          (pas un dossier brut). Choisissez un ZIP déjà prêt, ou un{" "}
          <strong className="text-[var(--foreground)]">dossier</strong> : le
          navigateur crée le ZIP localement puis l’envoie. Le ZIP envoyé doit
          rester ≤ <strong className="text-[var(--foreground)]">{Math.round(MAX_SERVER_ZIP_BYTES / (1024 * 1024))} MB</strong>{" "}
          (limite serveur).
        </p>
        <p>
          <strong className="text-[var(--foreground)]">Pass -1 (ingestion)</strong> : la
          réponse HTTP est immédiate ; l’assemblage des bundles tourne en{" "}
          <strong className="text-[var(--foreground)]">arrière-plan</strong> (plusieurs
          minutes possibles — la liste ci-dessous se met à jour automatiquement).
        </p>
        <p>
          <strong className="text-[var(--foreground)]">Pipeline V5</strong> : le bouton
          « Lancer le pipeline » appelle une route{" "}
          <strong className="text-[var(--foreground)]">synchrone</strong> : le
          navigateur attend la fin du traitement. Gros dossiers → durée longue et
          risque de <strong className="text-[var(--foreground)]">timeout</strong>{" "}
          (proxy / hébergeur) en production.
        </p>
      </div>

      {!blocked && (
        <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
          <div className="min-w-0 flex-1">
            <label
              htmlFor={zipInputId}
              className="mb-1 block text-xs font-medium text-[var(--foreground-muted)]"
            >
              Fichier ZIP
            </label>
            <input
              id={zipInputId}
              ref={fileInputRef}
              type="file"
              accept=".zip,application/zip"
              disabled={uploadBusy}
              className="block w-full max-w-md text-sm text-[var(--foreground)] file:mr-3 file:rounded-md file:border file:border-[var(--border)] file:bg-[var(--surface)] file:px-3 file:py-1.5 file:text-sm"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) uploadMutation.mutate(f);
              }}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span
              id={folderInputId}
              className="mb-1 block text-xs font-medium text-[var(--foreground-muted)]"
            >
              Ou dossier fournisseurs
            </span>
            <input
              ref={folderInputRef}
              type="file"
              className="sr-only"
              multiple
              disabled={uploadBusy}
              aria-labelledby={folderInputId}
              {...({ webkitdirectory: "" } as InputHTMLAttributes<HTMLInputElement>)}
              onChange={async (e) => {
                const list = e.target.files;
                if (!list?.length) return;
                setUploadMsg(null);
                setZippingFolder(true);
                try {
                  const zipFile = await fileListToSupplierZipFile(list);
                  uploadMutation.mutate(zipFile);
                } catch (err) {
                  const msg =
                    err instanceof Error
                      ? err.message
                      : "Échec de la compression du dossier.";
                  setUploadMsg(msg);
                  setZippingFolder(false);
                } finally {
                  if (folderInputRef.current) folderInputRef.current.value = "";
                }
              }}
            />
            <button
              type="button"
              disabled={uploadBusy}
              onClick={() => folderInputRef.current?.click()}
              className="w-fit rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)] hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-gray-800"
            >
              Choisir un dossier…
            </button>
          </div>
        </div>
      )}

      {zippingFolder && (
        <p
          role="status"
          className="mb-3 text-xs text-[var(--foreground-muted)]"
        >
          Compression du dossier en ZIP (local, peut prendre du temps)…
        </p>
      )}

      {uploadMsg && (
        <div
          role="status"
          className="mb-3 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-900 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-100"
        >
          {uploadMsg}
        </div>
      )}
      <div className="mb-4">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--foreground-muted)]">
          Bundles ({bundlesQuery.isLoading ? "…" : bundles.length})
        </h4>
        {bundlesQuery.isError && (
          <p role="alert" className="text-xs text-red-600 dark:text-red-400">
            {(bundlesQuery.error as Error).message}
          </p>
        )}
        {!bundlesQuery.isLoading && bundles.length === 0 && (
          <p className="text-xs text-[var(--foreground-muted)]">
            Aucun bundle — en attente de Pass -1 ou dossier vide.
          </p>
        )}
        {bundles.length > 0 && (
          <ul className="max-h-40 space-y-1 overflow-y-auto text-xs">
            {bundles.map((b) => (
              <li
                key={b.id}
                className="flex flex-wrap justify-between gap-2 rounded border border-[var(--border)] px-2 py-1"
              >
                <span className="font-mono text-[11px]">{b.id.slice(0, 8)}…</span>
                <span className="text-[var(--foreground-muted)]">
                  {b.vendor_name_raw ?? "—"}{" "}
                  {b.bundle_status ? `· ${b.bundle_status}` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {!blocked && (
        <div className="flex flex-wrap items-center gap-3 border-t border-[var(--border)] pt-4">
          <label className="flex cursor-pointer items-center gap-2 text-xs text-[var(--foreground)]">
            <input
              type="checkbox"
              checked={forceM14}
              onChange={(e) => setForceM14(e.target.checked)}
              disabled={pipelineMutation.isPending}
              className="rounded border-[var(--border)]"
            />
            Forcer réévaluation M14
          </label>
          <button
            type="button"
            disabled={pipelineMutation.isPending || bundles.length === 0}
            onClick={() => pipelineMutation.mutate()}
            className="rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--brand-hover)] disabled:cursor-not-allowed disabled:opacity-50"
            aria-busy={pipelineMutation.isPending}
          >
            {pipelineMutation.isPending ? "Pipeline en cours…" : "Lancer le pipeline V5"}
          </button>
        </div>
      )}
      {bundles.length === 0 && !blocked && (
        <p className="mt-2 text-xs text-[var(--foreground-muted)]">
          Le pipeline nécessite au moins un bundle assemblé.
        </p>
      )}

      {pipelineSummary && (
        <div
          role={pipelineMutation.isError ? "alert" : "status"}
          className={`mt-3 rounded-md px-3 py-2 text-xs ${
            pipelineMutation.isError
              ? "border border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200"
              : "border border-green-200 bg-green-50 text-green-900 dark:border-green-800 dark:bg-green-950 dark:text-green-100"
          }`}
        >
          {pipelineSummary}
        </div>
      )}
    </section>
  );
}
