"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { ErrorBoundary } from "@/components/error-boundary";

interface DashboardWorkspace {
  id: string;
  reference_code: string;
  title: string;
  process_type: string;
  status: string;
  estimated_value: number;
  currency: string;
  created_at: string;
  sealed_at: string;
  cognitive: {
    state: string;
    label_fr: string;
    phase: string;
    completeness: number;
    can_advance: boolean;
    advance_blockers: string[];
    confidence_regime: string;
  };
}

interface DashboardResponse {
  workspaces: DashboardWorkspace[];
  total: number;
  phase_stats: Record<string, number>;
}

const REGIME_BADGE: Record<string, { bg: string; text: string; dot: string }> = {
  green:  { bg: "bg-green-100 dark:bg-green-900/40",  text: "text-green-800 dark:text-green-300",  dot: "bg-green-500" },
  yellow: { bg: "bg-amber-100 dark:bg-amber-900/40",  text: "text-amber-800 dark:text-amber-300",  dot: "bg-amber-500" },
  red:    { bg: "bg-red-100 dark:bg-red-900/40",    text: "text-red-800 dark:text-red-300",    dot: "bg-red-500" },
};

const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  sealed:    { label: "Scellé", cls: "text-green-600 dark:text-green-400" },
  closed:    { label: "Clos",   cls: "text-gray-500" },
  cancelled: { label: "Annulé", cls: "text-gray-400" },
};

function WorkspaceCard({ ws, onClick }: { ws: DashboardWorkspace; onClick: () => void }) {
  const regime = REGIME_BADGE[ws.cognitive.confidence_regime] ?? {
    bg: "bg-gray-100 dark:bg-gray-800",
    text: "text-gray-600 dark:text-gray-400",
    dot: "bg-gray-400",
  };
  const statusMeta = STATUS_LABEL[ws.status];
  const pct = Math.round(ws.cognitive.completeness * 100);

  return (
    <button
      onClick={onClick}
      className="group w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 text-left shadow-sm transition hover:border-[var(--brand)] hover:shadow-md focus-visible:outline-2 focus-visible:outline-[var(--brand)] dark:hover:border-blue-700"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {/* Header row */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-semibold tracking-tight text-[var(--foreground)]">
              {ws.reference_code}
            </span>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${regime.bg} ${regime.text}`}
              aria-label={`État cognitif : ${ws.cognitive.label_fr}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${regime.dot}`} aria-hidden="true" />
              {ws.cognitive.label_fr}
            </span>
            {statusMeta && (
              <span className={`text-xs font-medium ${statusMeta.cls}`}>
                {statusMeta.label}
              </span>
            )}
          </div>

          {/* Title */}
          <p className="mt-1.5 truncate text-sm text-[var(--foreground-muted)]">{ws.title}</p>

          {/* Phase + blockers */}
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-[var(--foreground-subtle)]">
            <span>{ws.cognitive.phase}</span>
            {ws.cognitive.advance_blockers.length > 0 && (
              <span className="text-amber-600 dark:text-amber-400">
                ⚠ {ws.cognitive.advance_blockers[0]}
                {ws.cognitive.advance_blockers.length > 1 &&
                  ` +${ws.cognitive.advance_blockers.length - 1}`}
              </span>
            )}
          </div>
        </div>

        {/* Completeness */}
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className="text-lg font-bold tabular-nums text-[var(--foreground)]">{pct}%</span>
          <div
            className="h-1.5 w-20 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className={`h-full rounded-full transition-all ${regime.dot}`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      </div>
    </button>
  );
}

function PhaseStats({ stats }: { stats: Record<string, number> }) {
  const entries = Object.entries(stats).sort((a, b) => b[1] - a[1]);
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {entries.map(([phase, count]) => (
        <div
          key={phase}
          className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm"
        >
          <div className="text-2xl font-bold tabular-nums text-[var(--foreground)]">{count}</div>
          <div className="mt-0.5 truncate text-xs font-medium text-[var(--foreground-muted)]">
            {phase}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardResponse>("/api/dashboard"),
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--brand)] border-t-transparent"
          aria-label="Chargement"
        />
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="m-6 rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
      >
        Erreur chargement dashboard : {(error as Error).message}
      </div>
    );
  }

  const workspaces = data?.workspaces ?? [];
  const sealed = workspaces.filter((w) => w.status === "sealed" || w.status === "closed").length;
  const active = workspaces.filter((w) => w.status !== "sealed" && w.status !== "closed" && w.status !== "cancelled").length;

  return (
    <ErrorBoundary>
      <div className="space-y-8 p-6">
        {/* Header */}
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-[var(--foreground)]">Tableau de bord</h1>
            <p className="mt-1 text-sm text-[var(--foreground-muted)]">
              {data?.total ?? 0} processus ·{" "}
              <span className="text-green-600 dark:text-green-400">{sealed} scellés</span>
              {active > 0 && (
                <>
                  {" "}·{" "}
                  <span className="text-[var(--brand)]">{active} en cours</span>
                </>
              )}
            </p>
          </div>
        </div>

        {/* Phase stats */}
        {data?.phase_stats && Object.keys(data.phase_stats).length > 0 && (
          <section aria-label="Répartition par phase">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--foreground-muted)]">
              Par phase
            </h2>
            <PhaseStats stats={data.phase_stats} />
          </section>
        )}

        {/* Workspace list */}
        <section aria-label="Liste des processus">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--foreground-muted)]">
            Processus ({workspaces.length})
          </h2>
          {workspaces.length === 0 ? (
            <p className="rounded-xl border border-dashed border-[var(--border)] p-8 text-center text-sm text-[var(--foreground-muted)]">
              Aucun processus accessible.
            </p>
          ) : (
            <div className="space-y-3">
              {workspaces.map((ws) => (
                <WorkspaceCard
                  key={ws.id}
                  ws={ws}
                  onClick={() => router.push(`/workspaces/${ws.id}`)}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </ErrorBoundary>
  );
}
