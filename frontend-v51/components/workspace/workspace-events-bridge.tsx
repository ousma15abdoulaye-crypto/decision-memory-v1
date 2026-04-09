"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api-client";

function readAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("dms-auth");
  if (!raw) return null;
  try {
    return JSON.parse(raw)?.state?.accessToken ?? null;
  } catch {
    return null;
  }
}

/**
 * Connexion WebSocket Canon O2 — événements `workspace_events` (diffusion pure).
 */
export function WorkspaceEventsBridge({ workspaceId }: { workspaceId: string }) {
  const [status, setStatus] = useState<"idle" | "open" | "error">("idle");
  const [lastLine, setLastLine] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = readAccessToken();
    if (!token || !workspaceId) {
      return undefined;
    }

    let stopped = false;
    const apiUrl = new URL(API_BASE);
    const wsProto = apiUrl.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${apiUrl.host}/ws/workspace/${encodeURIComponent(workspaceId)}/events?token=${encodeURIComponent(token)}`;

    const connect = () => {
      if (stopped) return;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => {
        if (!stopped) setStatus("open");
      };
      ws.onmessage = (ev) => {
        if (stopped) return;
        try {
          const j = JSON.parse(ev.data as string) as { type?: string };
          if (j.type === "heartbeat") return;
          setLastLine(
            typeof ev.data === "string" ? ev.data.slice(0, 200) : "event",
          );
        } catch {
          setLastLine(String(ev.data).slice(0, 200));
        }
      };
      ws.onerror = () => {
        if (!stopped) setStatus("error");
      };
      ws.onclose = () => {
        if (stopped) return;
        wsRef.current = null;
        setStatus("error");
      };
    };

    connect();

    // Fermeture obligatoire à la navigation / changement de `workspaceId` — évite fuites
    // WebSocket (revue merge CONDITIONAL GO). `close()` est valide OPEN ou CONNECTING.
    return () => {
      stopped = true;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [workspaceId]);

  if (status === "idle") return null;

  return (
    <div
      className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-900 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-100"
      data-testid="workspace-ws-banner"
    >
      <span className="font-medium">Temps réel</span>
      {status === "open" && (
        <span className="ml-2 text-blue-700 dark:text-blue-300">connecté</span>
      )}
      {status === "error" && (
        <span className="ml-2 text-amber-800 dark:text-amber-200">
          déconnecté (vérifiez l’API / le token)
        </span>
      )}
      {lastLine && (
        <pre className="mt-1 max-h-16 overflow-auto whitespace-pre-wrap break-all text-[10px] opacity-80">
          {lastLine}
        </pre>
      )}
    </div>
  );
}
