"use client";

import type { ReactNode } from "react";
import { CommandPalette } from "@/components/command-palette";
import { usePathname } from "next/navigation";

/**
 * Composant client racine — monté à l'intérieur de Providers.
 * Injecte la CommandPalette (⌘K) disponible sur toutes les pages.
 */
export function GlobalShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  // Extrait workspace id depuis l'URL si on est dans /workspaces/[id]
  const wsMatch = pathname.match(/^\/workspaces\/([^/]+)/);
  const currentWorkspaceId = wsMatch?.[1];

  return (
    <>
      {children}
      <CommandPalette currentWorkspaceId={currentWorkspaceId} />
    </>
  );
}
