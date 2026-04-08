"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";

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

const REGIME_COLORS: Record<string, string> = {
  red: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  yellow: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  green: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
};

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
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4 text-red-600 dark:bg-red-950">
        Erreur chargement dashboard : {(error as Error).message}
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tableau de bord</h1>
        <span className="text-sm text-gray-500">{data?.total} processus</span>
      </div>

      {data?.phase_stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Object.entries(data.phase_stats).map(([phase, count]) => (
            <div
              key={phase}
              className="rounded-lg border p-3 dark:border-gray-800"
            >
              <div className="text-2xl font-bold">{count}</div>
              <div className="text-xs text-gray-500">{phase}</div>
            </div>
          ))}
        </div>
      )}

      <div className="space-y-3">
        {data?.workspaces.map((ws) => (
          <button
            key={ws.id}
            onClick={() => router.push(`/workspaces/${ws.id}`)}
            className="w-full rounded-lg border p-4 text-left transition hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-900"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">
                    {ws.reference_code}
                  </span>
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      REGIME_COLORS[ws.cognitive.confidence_regime] ||
                      "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {ws.cognitive.label_fr}
                  </span>
                </div>
                <p className="mt-1 truncate text-sm text-gray-600 dark:text-gray-400">
                  {ws.title}
                </p>
              </div>

              <div className="text-right">
                <div className="text-sm font-medium">
                  {Math.round(ws.cognitive.completeness * 100)}%
                </div>
                <div className="mt-1 h-1.5 w-16 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                  <div
                    className="h-full rounded-full bg-blue-600"
                    style={{
                      width: `${Math.round(ws.cognitive.completeness * 100)}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            {ws.cognitive.advance_blockers.length > 0 && (
              <div className="mt-2 text-xs text-amber-600 dark:text-amber-400">
                En attente : {ws.cognitive.advance_blockers[0]}
                {ws.cognitive.advance_blockers.length > 1 &&
                  ` (+${ws.cognitive.advance_blockers.length - 1})`}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
