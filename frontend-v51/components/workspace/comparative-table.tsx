"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

interface EvalFrame {
  scores_matrix: Record<string, Record<string, { score: number; confidence: number; signal: string }>>;
  criteria: { id: string; critere_nom: string; ponderation: number; is_eliminatory: boolean }[];
  suppliers: { id: string; name: string }[];
  weighted_totals: Record<string, number>;
}

export function ComparativeTable({ workspaceId }: { workspaceId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["evaluation-frame", workspaceId],
    queryFn: () =>
      api.get<EvalFrame>(`/api/workspaces/${workspaceId}/evaluation-frame`),
    enabled: !!workspaceId,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse rounded-lg border p-4 dark:border-gray-800">
        <div className="h-4 w-48 rounded bg-gray-200 dark:bg-gray-700" />
        <div className="mt-4 h-32 rounded bg-gray-100 dark:bg-gray-800" />
      </div>
    );
  }

  if (!data?.criteria?.length) return null;

  const SIGNAL_COLORS: Record<string, string> = {
    green: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    yellow: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
    red: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  };

  return (
    <div className="overflow-x-auto rounded-lg border dark:border-gray-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-gray-50 dark:border-gray-800 dark:bg-gray-900">
            <th className="px-4 py-2 text-left font-medium">Critère</th>
            <th className="px-4 py-2 text-center font-medium">Pond.</th>
            {data.suppliers?.map((s) => (
              <th key={s.id} className="px-4 py-2 text-center font-medium">
                {s.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.criteria.map((c) => (
            <tr key={c.id} className="border-b dark:border-gray-800">
              <td className="px-4 py-2">
                {c.critere_nom}
                {c.is_eliminatory && (
                  <span className="ml-1 text-xs text-red-500">ELIM</span>
                )}
              </td>
              <td className="px-4 py-2 text-center">
                {c.is_eliminatory ? "—" : `${c.ponderation}%`}
              </td>
              {data.suppliers?.map((s) => {
                const cell = data.scores_matrix?.[s.id]?.[c.id];
                if (!cell)
                  return (
                    <td
                      key={s.id}
                      className="px-4 py-2 text-center text-gray-400"
                    >
                      —
                    </td>
                  );
                return (
                  <td key={s.id} className="px-4 py-2 text-center">
                    <span
                      className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${
                        SIGNAL_COLORS[cell.signal] || ""
                      }`}
                    >
                      {cell.score.toFixed(1)}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
          {data.weighted_totals && (
            <tr className="bg-gray-50 font-medium dark:bg-gray-900">
              <td className="px-4 py-2">Total pondéré</td>
              <td className="px-4 py-2" />
              {data.suppliers?.map((s) => (
                <td key={s.id} className="px-4 py-2 text-center">
                  {data.weighted_totals[s.id]?.toFixed(1) ?? "—"}
                </td>
              ))}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
