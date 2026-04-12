"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { CommentDialog } from "@/components/deliberation/comment-dialog";
import { Button } from "@/components/ui/button";

const UUID_LIKE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const W_CRIT = 200;
const W_POND = 72;
const W_SUP = 120;

/**
 * NL-04 : virtualisation **horizontale** (colonnes fournisseurs) si nombre d’offres
 * >= ce seuil. La virtualisation **verticale** (lignes critères) n’est pas implémentée
 * en V5.1 — ordre de grandeur terrain ~30 critères, DOM natif jugé suffisant.
 * Suivi : NL-04-vertical (V5.2) — voir `docs/ops/FRONTEND_V51_NL_TECH_DEBT.md`.
 */
const VIRTUAL_SUP_THRESHOLD = 14;

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
  source?: "m16" | "m14";
  schema_version?: string;
}

function deriveSuppliers(data: EvalFrame): {
  list: { id: string; name: string }[];
  partialNames: boolean;
} {
  if (data.suppliers?.length) {
    return { list: data.suppliers, partialNames: false };
  }
  const list = Object.keys(data.scores_matrix || {})
    .filter((k) => UUID_LIKE.test(k))
    .map((id) => ({ id, name: `${id.slice(0, 8)}…` }));
  return { list, partialNames: list.length > 0 };
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

type ZoomMode =
  | { kind: "all" }
  | { kind: "supplier"; id: string }
  | { kind: "criterion"; id: string };

const SIGNAL_COLORS: Record<string, string> = {
  green: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  yellow: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  red: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  bell: "bg-sky-100 text-sky-800 dark:bg-sky-900 dark:text-sky-200",
};

function rowMaxScore(
  data: EvalFrame,
  criterionId: string,
  supplierIds: string[],
): number {
  let m = -Infinity;
  for (const sid of supplierIds) {
    const cell = data.scores_matrix?.[sid]?.[criterionId];
    if (cell && Number.isFinite(cell.score)) m = Math.max(m, cell.score);
  }
  return Number.isFinite(m) ? m : 0;
}

function criterionPassesFilters(
  data: EvalFrame,
  c: { id: string; is_eliminatory: boolean },
  supplierIds: string[],
  onlyEliminatory: boolean,
  onlyRed: boolean,
  minGap: number | null,
): boolean {
  if (onlyEliminatory && !c.is_eliminatory) return false;
  let hasRed = false;
  let hasGap = false;
  const rmax = rowMaxScore(data, c.id, supplierIds);
  for (const sid of supplierIds) {
    const cell = data.scores_matrix?.[sid]?.[c.id];
    if (!cell) continue;
    if (cell.signal === "red") hasRed = true;
    if (minGap !== null && rmax - cell.score > minGap) hasGap = true;
  }
  if (onlyRed && !hasRed) return false;
  if (minGap !== null && !hasGap) return false;
  return true;
}

export function ComparativeTable({ workspaceId }: { workspaceId: string }) {
  const [cellComment, setCellComment] = useState<{
    criterionId: string;
    supplierId: string;
  } | null>(null);

  const [onlyEliminatory, setOnlyEliminatory] = useState(false);
  const [onlyRed, setOnlyRed] = useState(false);
  const [minGapInput, setMinGapInput] = useState("");
  const minGap = minGapInput.trim() === "" ? null : Number(minGapInput);
  const minGapValid = minGap === null || (Number.isFinite(minGap) && minGap >= 0);

  const [zoom, setZoom] = useState<ZoomMode>({ kind: "all" });

  const [focusRow, setFocusRow] = useState(0);
  const [focusSup, setFocusSup] = useState(0);
  const tableWrapRef = useRef<HTMLDivElement>(null);
  const hScrollRef = useRef<HTMLDivElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["comparative-matrix", workspaceId],
    queryFn: () =>
      api.get<EvalFrame>(`/api/workspaces/${workspaceId}/comparative-matrix`),
    enabled: !!workspaceId,
  });

  const supplierInfo = useMemo(
    () => (data ? deriveSuppliers(data) : { list: [], partialNames: false }),
    [data],
  );
  const suppliers = supplierInfo.list;
  const criteriaRows = useMemo(
    () => (data ? deriveCriteriaRows(data, suppliers.map((s) => s.id)) : []),
    [data, suppliers],
  );

  const baseSupplierIds = useMemo(() => {
    if (zoom.kind === "supplier")
      return suppliers.filter((s) => s.id === zoom.id).map((s) => s.id);
    return suppliers.map((s) => s.id);
  }, [suppliers, zoom]);

  const filteredCriteria = useMemo(() => {
    if (!data) return [];
    let rows = criteriaRows;
    if (zoom.kind === "criterion") {
      rows = rows.filter((r) => r.id === zoom.id);
    }
    const gap = minGapValid ? minGap : null;
    return rows.filter((c) =>
      criterionPassesFilters(
        data,
        c,
        baseSupplierIds,
        onlyEliminatory,
        onlyRed,
        gap,
      ),
    );
  }, [
    data,
    criteriaRows,
    baseSupplierIds,
    onlyEliminatory,
    onlyRed,
    minGap,
    minGapValid,
    zoom,
  ]);

  useEffect(() => {
    setFocusRow((r) => Math.min(r, Math.max(0, filteredCriteria.length - 1)));
    setFocusSup((c) => Math.min(c, Math.max(0, baseSupplierIds.length - 1)));
  }, [filteredCriteria.length, baseSupplierIds.length]);

  const useVirtualCols =
    baseSupplierIds.length >= VIRTUAL_SUP_THRESHOLD && zoom.kind !== "supplier";

  // eslint-disable-next-line react-hooks/incompatible-library -- virtualisation horizontale (NL-04)
  const colVirtualizer = useVirtualizer({
    horizontal: true,
    count: baseSupplierIds.length,
    getScrollElement: () => hScrollRef.current,
    estimateSize: () => W_SUP,
    overscan: 4,
    enabled: useVirtualCols,
  });

  const openComment = useCallback(
    (criterionId: string, supplierId: string) => {
      setCellComment({ criterionId, supplierId });
    },
    [],
  );

  const onTableKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!data || filteredCriteria.length === 0 || baseSupplierIds.length === 0)
        return;
      const maxR = filteredCriteria.length - 1;
      const maxS = baseSupplierIds.length - 1;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setFocusRow((r) => Math.min(maxR, r + 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusRow((r) => Math.max(0, r - 1));
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setFocusSup((s) => Math.min(maxS, s + 1));
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        setFocusSup((s) => Math.max(0, s - 1));
      } else if (e.key === "Enter") {
        e.preventDefault();
        const c = filteredCriteria[focusRow];
        const sid = baseSupplierIds[focusSup];
        if (c && sid) openComment(c.id, sid);
      }
    },
    [data, filteredCriteria, baseSupplierIds, focusRow, focusSup, openComment],
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

  const stickyTh =
    "sticky top-0 z-20 border-b bg-gray-50 dark:border-gray-800 dark:bg-gray-900";
  const stickyTd =
    "sticky z-10 border-b bg-white dark:border-gray-950 dark:bg-gray-950";

  const renderScoreCell = (
    c: { id: string },
    s: { id: string },
    rIdx: number,
    sIdx: number,
  ) => {
    const cell = data.scores_matrix?.[s.id]?.[c.id];
    const focused = rIdx === focusRow && sIdx === focusSup;
    const baseCls =
      "px-2 py-2 text-center align-middle outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1";
    if (!cell) {
      return (
        <td
          key={s.id}
          tabIndex={focused ? 0 : -1}
          className={`${baseCls} text-gray-400`}
        >
          <div className="flex flex-col items-center gap-1">
            <span>—</span>
            <button
              type="button"
              onClick={() => openComment(c.id, s.id)}
              className="text-xs text-blue-600 hover:underline dark:text-blue-400"
            >
              Commenter
            </button>
          </div>
        </td>
      );
    }
    return (
      <td
        key={s.id}
        tabIndex={focused ? 0 : -1}
        className={baseCls}
        data-testid={`matrix-cell-${rIdx}-${sIdx}`}
      >
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
            onClick={() => openComment(c.id, s.id)}
            className="text-xs text-blue-600 hover:underline dark:text-blue-400"
          >
            Commenter
          </button>
        </div>
      </td>
    );
  };

  const virtualItems = useVirtualCols ? colVirtualizer.getVirtualItems() : null;
  const totalVirtualWidth = useVirtualCols
    ? colVirtualizer.getTotalSize()
    : baseSupplierIds.length * W_SUP;

  const supplierName = (sid: string) =>
    suppliers.find((x) => x.id === sid)?.name ?? sid.slice(0, 8);

  const sourceLabel =
    data.source === "m16"
      ? "M16"
      : data.source === "m14"
        ? "M14"
        : "—";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-2.5 py-0.5 text-xs font-medium text-[var(--foreground-muted)]"
          data-testid="matrix-source-badge"
        >
          Source matrice : {sourceLabel}
        </span>
      </div>
      {supplierInfo.partialNames && (
        <div
          role="status"
          className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
          data-testid="matrix-suppliers-partial-banner"
        >
          Noms fournisseurs indisponibles — affichage partiel à partir des identifiants
          (données incomplètes).
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-medium text-gray-700 dark:text-gray-300">
          Filtres
        </span>
        <label className="flex cursor-pointer items-center gap-1.5">
          <input
            type="checkbox"
            checked={onlyEliminatory}
            onChange={(e) => setOnlyEliminatory(e.target.checked)}
            data-testid="filter-eliminatory"
          />
          Éliminatoires
        </label>
        <label className="flex cursor-pointer items-center gap-1.5">
          <input
            type="checkbox"
            checked={onlyRed}
            onChange={(e) => setOnlyRed(e.target.checked)}
            data-testid="filter-red"
          />
          Signal rouge
        </label>
        <label className="flex items-center gap-1.5">
          Écart au max ligne &gt;
          <input
            type="number"
            step="0.1"
            min={0}
            className="w-16 rounded border px-1 py-0.5 dark:border-gray-700 dark:bg-gray-900"
            value={minGapInput}
            onChange={(e) => setMinGapInput(e.target.value)}
            data-testid="filter-gap"
            aria-invalid={!minGapValid}
          />
        </label>
        <span className="text-gray-500">
          {filteredCriteria.length} critère(s) × {baseSupplierIds.length} offre(s)
          {useVirtualCols ? " (colonnes virtualisées)" : ""}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-medium text-gray-700 dark:text-gray-300">
          Vue
        </span>
        <Button
          type="button"
          variant={zoom.kind === "all" ? "default" : "outline"}
          size="sm"
          onClick={() => setZoom({ kind: "all" })}
          data-testid="zoom-all"
        >
          Matrice complète
        </Button>
        <select
          className="rounded border px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-900"
          value={zoom.kind === "supplier" ? zoom.id : ""}
          onChange={(e) => {
            const v = e.target.value;
            if (!v) setZoom({ kind: "all" });
            else setZoom({ kind: "supplier", id: v });
          }}
          aria-label="Zoom fournisseur"
          data-testid="zoom-supplier"
        >
          <option value="">— Fournisseur —</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <select
          className="rounded border px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-900"
          value={zoom.kind === "criterion" ? zoom.id : ""}
          onChange={(e) => {
            const v = e.target.value;
            if (!v) setZoom({ kind: "all" });
            else setZoom({ kind: "criterion", id: v });
          }}
          aria-label="Zoom critère"
          data-testid="zoom-criterion"
        >
          <option value="">— Critère —</option>
          {criteriaRows.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <div
        ref={useVirtualCols ? hScrollRef : tableWrapRef}
        role="grid"
        tabIndex={0}
        aria-label="Matrice comparative — flèches pour naviguer, Entrée pour commenter"
        onKeyDown={onTableKeyDown}
        className="max-h-[min(70vh,52rem)] overflow-auto rounded-lg border outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-800"
        data-testid="comparative-table-grid"
      >
        {!useVirtualCols ? (
          <table className="w-max min-w-full border-collapse text-sm">
            <thead>
              <tr className="border-b dark:border-gray-800">
                <th
                  className={`${stickyTh} px-3 py-2 text-left`}
                  style={{ left: 0, minWidth: W_CRIT, width: W_CRIT }}
                >
                  Critère
                </th>
                <th
                  className={`${stickyTh} px-2 py-2 text-center`}
                  style={{
                    left: W_CRIT,
                    minWidth: W_POND,
                    width: W_POND,
                  }}
                >
                  Pond.
                </th>
                {baseSupplierIds.map((sid) => {
                  const s = suppliers.find((x) => x.id === sid)!;
                  return (
                    <th
                      key={s.id}
                      className={`${stickyTh} px-2 py-2 text-center text-xs font-medium`}
                      style={{ minWidth: W_SUP, width: W_SUP }}
                    >
                      {s.name}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {filteredCriteria.map((c, rIdx) => (
                <tr key={c.id} className="border-b dark:border-gray-800">
                  <td
                    className={`${stickyTd} px-3 py-2`}
                    style={{ left: 0, minWidth: W_CRIT, width: W_CRIT }}
                  >
                    {c.label}
                    {c.is_eliminatory && (
                      <span className="ml-1 text-xs text-red-500">ELIM</span>
                    )}
                  </td>
                  <td
                    className={`${stickyTd} px-2 py-2 text-center`}
                    style={{
                      left: W_CRIT,
                      minWidth: W_POND,
                      width: W_POND,
                    }}
                  >
                    {c.is_eliminatory ? "—" : `${c.ponderation}%`}
                  </td>
                  {baseSupplierIds.map((sid, sIdx) => {
                    const s = suppliers.find((x) => x.id === sid)!;
                    return renderScoreCell(c, s, rIdx, sIdx);
                  })}
                </tr>
              ))}
              {data.weighted_totals && zoom.kind === "all" && (
                <tr className="border-b bg-gray-50 font-medium dark:border-gray-800 dark:bg-gray-900">
                  <td
                    className={`${stickyTd} px-3 py-2`}
                    style={{ left: 0, minWidth: W_CRIT }}
                  >
                    Total pondéré
                  </td>
                  <td
                    className={`${stickyTd} px-2 py-2`}
                    style={{ left: W_CRIT, minWidth: W_POND }}
                  />
                  {baseSupplierIds.map((sid) => (
                    <td key={sid} className="px-2 py-2 text-center">
                      {data.weighted_totals?.[sid]?.toFixed(1) ?? "—"}
                    </td>
                  ))}
                </tr>
              )}
            </tbody>
          </table>
        ) : (
          <div
            className="min-w-max"
            style={{ width: W_CRIT + W_POND + totalVirtualWidth }}
          >
            <div
              className={`${stickyTh} flex items-stretch border-b dark:border-gray-800`}
              style={{ minHeight: 44 }}
            >
              <div
                className={`${stickyTh} flex shrink-0 items-center px-3 text-left font-medium`}
                style={{
                  width: W_CRIT,
                  minWidth: W_CRIT,
                  left: 0,
                  position: "sticky",
                  zIndex: 30,
                }}
              >
                Critère
              </div>
              <div
                className={`${stickyTh} flex shrink-0 items-center justify-center border-l border-gray-200 px-2 text-center text-xs font-medium dark:border-gray-700`}
                style={{
                  width: W_POND,
                  minWidth: W_POND,
                  left: W_CRIT,
                  position: "sticky",
                  zIndex: 30,
                }}
              >
                Pond.
              </div>
              <div
                className="relative shrink-0 border-l border-gray-200 dark:border-gray-700"
                style={{ width: totalVirtualWidth, minHeight: 44 }}
              >
                {virtualItems?.map((vi) => (
                  <div
                    key={vi.key}
                    className={`${stickyTh} absolute top-0 flex items-center justify-center border-r border-gray-200 px-2 text-center text-xs font-medium dark:border-gray-700`}
                    style={{
                      left: vi.start,
                      width: vi.size,
                      height: "100%",
                    }}
                  >
                    {supplierName(baseSupplierIds[vi.index])}
                  </div>
                ))}
              </div>
            </div>

            {filteredCriteria.map((c, rIdx) => (
              <div
                key={c.id}
                className="flex items-stretch border-b dark:border-gray-800"
                style={{ minHeight: 56 }}
              >
                <div
                  className={`${stickyTd} flex shrink-0 items-center px-3 py-2`}
                  style={{
                    width: W_CRIT,
                    minWidth: W_CRIT,
                    left: 0,
                    position: "sticky",
                    zIndex: 15,
                  }}
                >
                  {c.label}
                  {c.is_eliminatory && (
                    <span className="ml-1 text-xs text-red-500">ELIM</span>
                  )}
                </div>
                <div
                  className={`${stickyTd} flex shrink-0 items-center justify-center border-l border-gray-200 px-2 py-2 text-center dark:border-gray-700`}
                  style={{
                    width: W_POND,
                    minWidth: W_POND,
                    left: W_CRIT,
                    position: "sticky",
                    zIndex: 15,
                  }}
                >
                  {c.is_eliminatory ? "—" : `${c.ponderation}%`}
                </div>
                <div
                  className="relative shrink-0 border-l border-gray-200 dark:border-gray-700"
                  style={{ width: totalVirtualWidth }}
                >
                  {virtualItems?.map((vi) => {
                    const sid = baseSupplierIds[vi.index];
                    const cell = data.scores_matrix?.[sid]?.[c.id];
                    const focused =
                      rIdx === focusRow && vi.index === focusSup;
                    return (
                      <div
                        key={vi.key}
                        tabIndex={focused ? 0 : -1}
                        className="absolute top-0 border-r border-gray-200 px-2 py-2 text-center outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-700"
                        style={{ left: vi.start, width: vi.size }}
                        data-testid={`matrix-cell-${rIdx}-${vi.index}`}
                      >
                        {!cell ? (
                          <div className="text-gray-400">
                            <div>—</div>
                            <button
                              type="button"
                              onClick={() => openComment(c.id, sid)}
                              className="mt-1 text-xs text-blue-600 hover:underline dark:text-blue-400"
                            >
                              Commenter
                            </button>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center gap-1">
                            <span
                              className={`inline-flex rounded px-1.5 py-0.5 text-xs font-medium ${
                                SIGNAL_COLORS[cell.signal] || ""
                              }`}
                            >
                              {cell.score.toFixed(1)}
                            </span>
                            <button
                              type="button"
                              onClick={() => openComment(c.id, sid)}
                              className="text-xs text-blue-600 hover:underline dark:text-blue-400"
                            >
                              Commenter
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}

            {data.weighted_totals && zoom.kind === "all" && (
              <div
                className="flex border-b bg-gray-50 font-medium dark:border-gray-800 dark:bg-gray-900"
                style={{ minHeight: 44 }}
              >
                <div
                  className="sticky left-0 z-10 flex shrink-0 items-center px-3 py-2"
                  style={{ width: W_CRIT, background: "inherit" }}
                >
                  Total pondéré
                </div>
                <div
                  className="sticky z-10 flex shrink-0 items-center border-l px-2 py-2 dark:border-gray-700"
                  style={{
                    width: W_POND,
                    left: W_CRIT,
                    background: "inherit",
                  }}
                />
                <div
                  className="relative shrink-0 border-l dark:border-gray-700"
                  style={{ width: totalVirtualWidth }}
                >
                  {virtualItems?.map((vi) => {
                    const sid = baseSupplierIds[vi.index];
                    return (
                      <div
                        key={vi.key}
                        className="absolute top-0 flex items-center justify-center border-r px-2 py-2 text-center dark:border-gray-700"
                        style={{ left: vi.start, width: vi.size }}
                      >
                        {data.weighted_totals?.[sid]?.toFixed(1) ?? "—"}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <p className="text-xs text-gray-500">
        Raccourcis : cliquez la matrice puis{" "}
        <kbd className="rounded border px-1">↑↓←→</kbd> Entrée pour ouvrir le
        commentaire sur la cellule focus.
      </p>

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
