"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { CommentDialog } from "@/components/deliberation/comment-dialog";

const UUID_LIKE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

interface EvalFrameCriteria {
  id?: string;
  criterion_key?: string;
  critere_nom?: string;
  ponderation?: number;
  is_eliminatory?: boolean;
  present?: boolean;
}

interface EvalFrame {
  scores_matrix: Record<
    string,
    Record<string, { score: number; confidence: number; signal: string }>
  >;
  criteria: EvalFrameCriteria[];
  suppliers?: { id: string; name: string }[];
  weighted_totals?: Record<string, number>;
}

function deriveSuppliers(data: EvalFrame): { id: string; name: string }[] {
  if (data.suppliers?.length) return data.suppliers;
  return Object.keys(data.scores_matrix || {})
    .filter((k) => UUID_LIKE.test(k))
    .map((id) => ({ id, name: `${id.slice(0, 8)}…` }));
}

function deriveCriteriaRows(
  data: EvalFrame,
  supplierIds: string[],
): {
  id: string;
  label: string;
  ponderation: number;
  is_eliminatory: boolean;
}[] {
  if (data.criteria?.length) {
    return data.criteria.map((c) => ({
      id: String(c.id ?? c.criterion_key ?? ""),
      label: String(c.critere_nom ?? c.criterion_key ?? c.id ?? "—"),
      ponderation: c.ponderation ?? 0,
      is_eliminatory: Boolean(c.is_eliminatory),
    }));
  }
  const keys = new Set<string>();
  for (const bid of supplierIds) {
    const row = data.scores_matrix?.[bid];
    if (row && typeof row === "object") {
      for (const ck of Object.keys(row)) {
        keys.add(ck);
      }
    }
  }
  return [...keys].sort().map((id) => ({
    id,
    label: id,
    ponderation: 0,
    is_eliminatory: false,
  }));
}

export function ComparativeTable({ workspaceId }: { workspaceId: string }) {
  const [cellComment, setCellComment] = useState<{
    criterionId: string;
    supplierId: string;
  } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["evaluation-frame", workspaceId],
    queryFn: () =>
      api.get<EvalFrame>(`/api/workspaces/${workspaceId}/evaluation-frame`),
    enabled: !!workspaceId,
  });

  const suppliers = useMemo(
    () => (data ? deriveSuppliers(data) : []),
    [data],
  );
  const criteriaRows = useMemo(
    () => (data ? deriveCriteriaRows(data, suppliers.map((s) => s.id)) : []),
    [data, suppliers],
  );

  if (isLoading) {
    return (
      <div className="animate-pulse rounded-lg border p-4 dark:border-gray-800">
        <div className="h-4 w-48 rounded bg-gray-200 dark:bg-gray-700" />
        <div className="mt-4 h-32 rounded bg-gray-100 dark:bg-gray-800" />
      </div>
    );
  }

  if (!data || !criteriaRows.length) return null;

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
            {suppliers.map((s) => (
              <th key={s.id} className="px-4 py-2 text-center font-medium">
                {s.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {criteriaRows.map((c) => (
            <tr key={c.id} className="border-b dark:border-gray-800">
              <td className="px-4 py-2">
                {c.label}
                {c.is_eliminatory && (
                  <span className="ml-1 text-xs text-red-500">ELIM</span>
                )}
              </td>
              <td className="px-4 py-2 text-center">
                {c.is_eliminatory ? "—" : `${c.ponderation}%`}
              </td>
              {suppliers.map((s) => {
                const cell = data.scores_matrix?.[s.id]?.[c.id];
                if (!cell)
                  return (
                    <td
                      key={s.id}
                      className="px-4 py-2 text-center text-gray-400"
                    >
                      <div className="flex flex-col items-center gap-1">
                        <span>—</span>
                        <button
                          type="button"
                          onClick={() =>
                            setCellComment({
                              criterionId: c.id,
                              supplierId: s.id,
                            })
                          }
                          className="text-xs text-blue-600 hover:underline dark:text-blue-400"
                        >
                          Commenter
                        </button>
                      </div>
                    </td>
                  );
                return (
                  <td key={s.id} className="px-4 py-2 text-center">
                    <div className="flex flex-col items-center gap-1">
                      <span
                        className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${
                          SIGNAL_COLORS[cell.signal] || ""
                        }`}
                      >
                        {cell.score.toFixed(1)}
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          setCellComment({
                            criterionId: c.id,
                            supplierId: s.id,
                          })
                        }
                        className="text-xs text-blue-600 hover:underline dark:text-blue-400"
                      >
                        Commenter
                      </button>
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
          {data.weighted_totals && (
            <tr className="bg-gray-50 font-medium dark:bg-gray-900">
              <td className="px-4 py-2">Total pondéré</td>
              <td className="px-4 py-2" />
              {suppliers.map((s) => (
                <td key={s.id} className="px-4 py-2 text-center">
                  {data.weighted_totals?.[s.id]?.toFixed(1) ?? "—"}
                </td>
              ))}
            </tr>
          )}
        </tbody>
      </table>

      {cellComment && (
        <CommentDialog
          workspaceId={workspaceId}
          criterionId={cellComment.criterionId}
          supplierId={cellComment.supplierId}
          onClose={() => setCellComment(null)}
        />
      )}
    </div>
  );
}
