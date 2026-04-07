import { useQuery } from "@tanstack/react-query";

/** Sous-ensemble utile à la matrice (aligné réponse API M16 frame). */
export type M16FrameApi = {
  domains: Array<{
    id: string;
    code: string;
    label: string;
    display_order: number;
  }>;
  assessments: Array<{
    id: string;
    bundle_id: string;
    criterion_key: string;
    cell_json: Record<string, unknown>;
    assessment_status: string;
    confidence?: number | null;
    signal?: string | null;
    computed_weighted_contribution?: number | null;
  }>;
  bundle_weighted_totals?: Record<string, number | null>;
  weight_validation?: { valid: boolean; weighted_sum: number; errors: string[] };
};

async function fetchFrame(workspaceId: string): Promise<M16FrameApi> {
  const r = await fetch(
    `/api/workspaces/${workspaceId}/m16/targets/workspace/${workspaceId}/frame`,
    { credentials: "include" },
  );
  if (!r.ok) throw new Error(`frame ${r.status}`);
  return r.json() as Promise<M16FrameApi>;
}

export function useEvaluationFrame(workspaceId: string) {
  return useQuery({
    queryKey: ["m16", "frame", workspaceId],
    queryFn: () => fetchFrame(workspaceId),
    networkMode: "offlineFirst",
  });
}
