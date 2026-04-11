"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CommandPalette } from "@/components/command-palette";
import { api } from "@/lib/api-client";

interface WorkspaceDetail {
  status: string;
}

/**
 * Composant client racine — monté à l'intérieur de Providers.
 * Injecte la CommandPalette (⌘K) disponible sur toutes les pages.
 */
export function GlobalShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  // Extrait workspace id depuis l'URL si on est dans /workspaces/[id]
  const wsMatch = pathname.match(/^\/workspaces\/([^/]+)/);
  const currentWorkspaceId = wsMatch?.[1];

  const { data: ws } = useQuery({
    queryKey: ["workspace", currentWorkspaceId],
    queryFn: () =>
      api.get<WorkspaceDetail>(`/api/workspaces/${currentWorkspaceId}`),
    enabled: !!currentWorkspaceId,
    staleTime: 30_000,
  });

  const isWorkspaceSealed =
    ws?.status === "sealed" || ws?.status === "closed";

  return (
    <>
      {children}
      <CommandPalette
        currentWorkspaceId={currentWorkspaceId}
        isWorkspaceSealed={isWorkspaceSealed}
      />
    </>
  );
}
