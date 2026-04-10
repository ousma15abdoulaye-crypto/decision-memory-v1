"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useCognitiveState } from "@/lib/hooks/use-cognitive-state";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { ComparativeTable } from "@/components/workspace/comparative-table";
import { AgentConsole } from "@/components/agent/agent-console";
import { SealButton } from "@/components/deliberation/seal-button";
import { CommentDialog } from "@/components/deliberation/comment-dialog";
import { PvExportButtons } from "@/components/workspace/pv-export-buttons";
import { PdfDrilldownPlaceholder } from "@/components/workspace/pdf-drilldown-placeholder";
import { WorkspaceEventsBridge } from "@/components/workspace/workspace-events-bridge";
import { M14SyncButton } from "@/components/workspace/m14-sync-button";
import { ErrorBoundary } from "@/components/error-boundary";

interface WorkspaceDetail {
  id: string;
  reference_code: string;
  title: string;
  process_type: string;
  status: string;
  estimated_value: number;
  currency: string;
}

const REGIME_BADGE: Record<string, { bg: string; text: string; dot: string }> = {
  green:  { bg: "bg-green-100 dark:bg-green-900/40",  text: "text-green-800 dark:text-green-300",  dot: "bg-green-500" },
  yellow: { bg: "bg-amber-100 dark:bg-amber-900/40",  text: "text-amber-800 dark:text-amber-300",  dot: "bg-amber-500" },
  red:    { bg: "bg-red-100 dark:bg-red-900/40",    text: "text-red-800 dark:text-red-300",    dot: "bg-red-500" },
};

const PROCESS_TYPE_LABEL: Record<string, string> = {
  dao: "DAO",
  cotation: "Cotation",
  gre_a_gre: "Gré à gré",
};

export default function WorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const { data: cog, isLoading: cogLoading } = useCognitiveState(id);
  const [showComment, setShowComment] = useState(false);

  const { data: ws, isLoading: wsLoading, error: wsError } = useQuery({
    queryKey: ["workspace", id],
    queryFn: () => api.get<WorkspaceDetail>(`/api/workspaces/${id}`),
    enabled: !!id,
  });

  const workspaceFailed = wsError != null;

  // Si le détail workspace est déjà en échec, ne pas bloquer l’UI sur l’état cognitif
  // (sinon bandeau d’erreur sans Assistant DMS — régression UX fréquente en 403 terrain).
  if ((wsLoading || cogLoading) && !workspaceFailed) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--brand)] border-t-transparent"
          aria-label="Chargement"
        />
      </div>
    );
  }

  if (workspaceFailed) {
    const msg =
      wsError instanceof Error ? wsError.message : "Erreur inconnue.";
    const isAuth = msg.includes("401") || msg.includes("403");
    return (
      <div className="space-y-6 p-6">
        <div
          role="alert"
          className="rounded-md bg-red-50 p-6 text-red-700 dark:bg-red-950 dark:text-red-300"
        >
          <p className="font-medium">Impossible de charger ce workspace.</p>
          <p className="mt-1 text-sm">{msg}</p>
          {isAuth && (
            <p className="mt-2 text-sm">
              Votre session a peut-être expiré.{" "}
              <a href="/login" className="underline">
                Reconnectez-vous.
              </a>
            </p>
          )}
        </div>
        {id ? (
          <ErrorBoundary>
            <p className="text-xs text-[var(--foreground-muted)]">
              L&apos;assistant DMS reste disponible ci-dessous (contexte dossier via
              l&apos;URL). Les réponses dépendent des permissions API sur ce workspace.
            </p>
            <AgentConsole workspaceId={id} />
          </ErrorBoundary>
        ) : null}
      </div>
    );
  }

  const isSealed = ws?.status === "sealed" || ws?.status === "closed";
  const isCancelled = ws?.status === "cancelled";
  const canSeal = !!cog?.can_advance && !isSealed;

  const regime = cog ? (REGIME_BADGE[cog.confidence_regime] ?? REGIME_BADGE.yellow) : null;
  const pct = cog ? Math.round(cog.completeness * 100) : 0;

  return (
    <ErrorBoundary>
      <div className="space-y-6 p-6">

        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-mono text-xl font-bold text-[var(--foreground)]">
                {ws?.reference_code}
              </h1>
              {cog && regime && (
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${regime.bg} ${regime.text}`}
                  aria-label={`État : ${cog.label_fr}`}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${regime.dot}`} aria-hidden="true" />
                  {cog.label_fr}
                </span>
              )}
              {ws?.process_type && (
                <span className="rounded-full border border-[var(--border)] px-2.5 py-0.5 text-xs text-[var(--foreground-muted)]">
                  {PROCESS_TYPE_LABEL[ws.process_type] ?? ws.process_type.toUpperCase()}
                </span>
              )}
              {isCancelled && (
                <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-500 dark:bg-gray-800">
                  Annulé
                </span>
              )}
            </div>
            <p className="mt-1.5 text-sm text-[var(--foreground-muted)]">{ws?.title}</p>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-2">
            {!isSealed && !isCancelled && (
              <button
                onClick={() => setShowComment(true)}
                className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--foreground-muted)] hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Commenter
              </button>
            )}
            {!isCancelled && (
              <SealButton workspaceId={id} canSeal={canSeal} isSealed={isSealed} />
            )}
          </div>
        </div>

        {/* ── Cognitive state cards ───────────────────────────────── */}
        {cog && (
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm">
              <div className="text-xs font-medium uppercase tracking-wide text-[var(--foreground-muted)]">Phase</div>
              <div className="mt-1 text-lg font-semibold text-[var(--foreground)]">{cog.phase}</div>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm">
              <div className="text-xs font-medium uppercase tracking-wide text-[var(--foreground-muted)]">Progression</div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-lg font-semibold text-[var(--foreground)]">{pct}%</span>
                <div
                  className="flex-1 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
                  style={{ height: 6 }}
                  role="progressbar"
                  aria-valuenow={pct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className={`h-full rounded-full ${regime?.dot ?? "bg-gray-400"}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm">
              <div className="text-xs font-medium uppercase tracking-wide text-[var(--foreground-muted)]">Actions dispo.</div>
              <div className="mt-1 text-lg font-semibold text-[var(--foreground)]">
                {cog.available_actions.length}
              </div>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm">
              <div className="text-xs font-medium uppercase tracking-wide text-[var(--foreground-muted)]">Valeur estimée</div>
              <div className="mt-1 text-lg font-semibold text-[var(--foreground)]">
                {ws?.estimated_value != null
                  ? `${Number(ws.estimated_value).toLocaleString("fr-FR")} ${ws.currency ?? ""}`
                  : "—"}
              </div>
            </div>
          </div>
        )}

        {/* ── Blockers ───────────────────────────────────────────── */}
        {cog?.advance_blockers && cog.advance_blockers.length > 0 && (
          <div
            role="alert"
            className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950"
          >
            <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-200">
              Blocages ({cog.advance_blockers.length})
            </h3>
            <ul className="mt-2 space-y-1 text-sm text-amber-700 dark:text-amber-300">
              {cog.advance_blockers.map((b, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span aria-hidden="true" className="mt-0.5">▸</span>
                  {b}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ── Real-time events ───────────────────────────────────── */}
        <WorkspaceEventsBridge workspaceId={id} />

        {/* ── PV Export (sealed only) ────────────────────────────── */}
        {isSealed && <PvExportButtons workspaceId={id} />}

        {/* ── M14 → M16 Sync (when not sealed) ──────────────────── */}
        {!isSealed && !isCancelled && (
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold text-[var(--foreground)]">
              Données M14 → Assessments M16
            </h3>
            <M14SyncButton workspaceId={id} />
          </div>
        )}

        {/* ── PDF drilldown ──────────────────────────────────────── */}
        <PdfDrilldownPlaceholder />

        {/* ── Comparative table ─────────────────────────────────── */}
        <ErrorBoundary>
          <section>
            <h2 className="mb-3 text-sm font-semibold text-[var(--foreground)]">
              Matrice comparative
            </h2>
            <ComparativeTable workspaceId={id} />
          </section>
        </ErrorBoundary>

        {/* ── Agent console ─────────────────────────────────────── */}
        <ErrorBoundary>
          <AgentConsole workspaceId={id} />
        </ErrorBoundary>

        {/* ── Comment dialog ────────────────────────────────────── */}
        {showComment && (
          <CommentDialog
            workspaceId={id}
            onClose={() => setShowComment(false)}
          />
        )}
      </div>
    </ErrorBoundary>
  );
}
