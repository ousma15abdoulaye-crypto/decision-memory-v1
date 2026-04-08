"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

interface CognitiveState {
  state: string;
  label_fr: string;
  phase: string;
  completeness: number;
  can_advance: boolean;
  advance_blockers: string[];
  available_actions: string[];
  confidence_regime: string;
}

export function useCognitiveState(workspaceId: string) {
  return useQuery({
    queryKey: ["cognitive-state", workspaceId],
    queryFn: () =>
      api.get<CognitiveState>(
        `/api/workspaces/${workspaceId}/cognitive-state`,
      ),
    refetchInterval: 30_000,
    enabled: !!workspaceId,
  });
}
