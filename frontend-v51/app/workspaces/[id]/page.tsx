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

interface WorkspaceDetail {
  id: string;
  reference_code: string;
  title: string;
  process_type: string;
  status: string;
  estimated_value: number;
  currency: string;
}

export default function WorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const { data: cog, isLoading: cogLoading } = useCognitiveState(id);
  const [showComment, setShowComment] = useState(false);

  const { data: ws, isLoading: wsLoading } = useQuery({
    queryKey: ["workspace", id],
    queryFn: () => api.get<WorkspaceDetail>(`/api/workspaces/${id}`),
    enabled: !!id,
  });

  if (wsLoading || cogLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  const isSealed = ws?.status === "sealed" || ws?.status === "closed";
  const canSeal = !!cog?.can_advance && !isSealed;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold">{ws?.reference_code}</h1>
            {cog && (
              <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                {cog.label_fr}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-500">{ws?.title}</p>
        </div>

        <div className="flex items-center gap-2">
          {!isSealed && (
            <button
              onClick={() => setShowComment(true)}
              className="rounded-md border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"
            >
              Commenter
            </button>
          )}
          <SealButton
            workspaceId={id}
            canSeal={canSeal}
            isSealed={isSealed}
          />
        </div>
      </div>

      {cog && (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border p-4 dark:border-gray-800">
            <div className="text-sm text-gray-500">Phase</div>
            <div className="text-lg font-medium">{cog.phase}</div>
          </div>
          <div className="rounded-lg border p-4 dark:border-gray-800">
            <div className="text-sm text-gray-500">Progression</div>
            <div className="text-lg font-medium">
              {Math.round(cog.completeness * 100)}%
            </div>
          </div>
          <div className="rounded-lg border p-4 dark:border-gray-800">
            <div className="text-sm text-gray-500">Actions disponibles</div>
            <div className="text-lg font-medium">
              {cog.available_actions.length}
            </div>
          </div>
        </div>
      )}

      <WorkspaceEventsBridge workspaceId={id} />

      {isSealed && <PvExportButtons workspaceId={id} />}

      <PdfDrilldownPlaceholder />

      {cog?.advance_blockers && cog.advance_blockers.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950">
          <h3 className="text-sm font-medium text-amber-800 dark:text-amber-200">
            Blocages
          </h3>
          <ul className="mt-2 space-y-1 text-sm text-amber-700 dark:text-amber-300">
            {cog.advance_blockers.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </div>
      )}

      <ComparativeTable workspaceId={id} />

      <AgentConsole workspaceId={id} />

      {showComment && (
        <CommentDialog
          workspaceId={id}
          onClose={() => setShowComment(false)}
        />
      )}
    </div>
  );
}
