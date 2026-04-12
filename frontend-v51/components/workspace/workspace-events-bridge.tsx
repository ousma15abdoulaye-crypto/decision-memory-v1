"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api-client";

const MAX_RETRIES_BEFORE_BANNER = 5;
const BASE_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 30_000;
/** Refresh the WS token every 12 hours (token TTL is 24 h). */
const WS_TOKEN_REFRESH_INTERVAL_MS = 12 * 60 * 60 * 1000;

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

async function fetchWsToken(accessToken: string): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/ws-token`, {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { token?: string };
    return data.token ?? null;
  } catch {
    return null;
  }
}

/**
 * Connexion WebSocket Canon O2 — événements `workspace_events` (diffusion pure).
 * Reconnexion automatique avec backoff exponentiel (1s, 2s, 4s… max 30s).
 * Le banner d'erreur n'apparaît qu'après MAX_RETRIES_BEFORE_BANNER échecs consécutifs.
 *
 * Utilise un token WebSocket longue durée (TTL 24 h) obtenu via POST /api/auth/ws-token
 * pour éviter les déconnexions dues à l'expiration du token d'accès standard (30 min).
 * Le token WS est rafraîchi toutes les 12 heures.
 */
export function WorkspaceEventsBridge({ workspaceId }: { workspaceId: string }) {
  const [showError, setShowError] = useState(false);
  const [showWsTokenDegraded, setShowWsTokenDegraded] = useState(false);
  const [lastLine, setLastLine] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wsTokenRef = useRef<string | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wsTokenFallbackWarnedRef = useRef(false);

  useEffect(() => {
    const accessToken = readAccessToken();
    if (!accessToken || !workspaceId) return undefined;

    let stopped = false;
    const apiUrl = new URL(API_BASE);
    const wsProto = apiUrl.protocol === "https:" ? "wss:" : "ws:";

    const buildWsUrl = (token: string) =>
      `${wsProto}//${apiUrl.host}/ws/workspace/${encodeURIComponent(workspaceId)}/events?token=${encodeURIComponent(token)}`;

    const connect = () => {
      if (stopped) return;
      const token = wsTokenRef.current;
      if (!token) return;

      /** Un seul schedule par socket : navigateurs appellent souvent onerror puis onclose. */
      let reconnectScheduled = false;
      const ws = new WebSocket(buildWsUrl(token));
      wsRef.current = ws;

      ws.onopen = () => {
        if (stopped) return;
        reconnectScheduled = false;
        retriesRef.current = 0;
        setShowError(false);
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

      const scheduleReconnect = () => {
        if (stopped || reconnectScheduled) return;
        reconnectScheduled = true;
        wsRef.current = null;
        retriesRef.current += 1;
        if (retriesRef.current >= MAX_RETRIES_BEFORE_BANNER) {
          setShowError(true);
        }
        const delay = Math.min(
          BASE_BACKOFF_MS * Math.pow(2, retriesRef.current - 1),
          MAX_BACKOFF_MS,
        );
        timerRef.current = setTimeout(connect, delay);
      };

      ws.onerror = scheduleReconnect;
      ws.onclose = scheduleReconnect;
    };

    /** Fetch a WS-specific token, then open the WebSocket. */
    const initWsToken = async () => {
      const token = await fetchWsToken(accessToken);
      if (stopped) return;
      if (!token && !wsTokenFallbackWarnedRef.current) {
        wsTokenFallbackWarnedRef.current = true;
        setShowWsTokenDegraded(true);
      }
      // Fall back to the access token if the endpoint is unavailable.
      wsTokenRef.current = token ?? accessToken;
      connect();
    };

    /** Refresh the WS token and reconnect with the new one. */
    const refreshWsToken = async () => {
      if (stopped) return;
      const token = await fetchWsToken(accessToken);
      if (stopped || !token) return;
      wsTokenRef.current = token;
      // Close the current socket so it reconnects with the fresh token.
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };

    void initWsToken();

    refreshTimerRef.current = setInterval(() => {
      void refreshWsToken();
    }, WS_TOKEN_REFRESH_INTERVAL_MS);

    // Fermeture obligatoire à la navigation / changement de `workspaceId` — évite fuites
    // WebSocket (revue merge CONDITIONAL GO). `close()` est valide OPEN ou CONNECTING.
    return () => {
      stopped = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [workspaceId]);

  if (!showError && !showWsTokenDegraded) return null;

  return (
    <div className="space-y-2">
      {showWsTokenDegraded && (
        <div
          className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-900 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-100"
          data-testid="workspace-ws-token-degraded"
        >
          <span className="font-medium">Temps réel</span>
          <span className="ml-2">
            jeton WebSocket indisponible — repli sur le jeton d&apos;accès (session plus
            courte, reconnexions possibles).
          </span>
        </div>
      )}
      {showError && (
        <div
          className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
          data-testid="workspace-ws-banner"
        >
          <span className="font-medium">Temps réel</span>
          <span className="ml-2">déconnecté — reconnexion en cours…</span>
          {lastLine && (
            <pre className="mt-1 max-h-16 overflow-auto whitespace-pre-wrap break-all text-[10px] opacity-80">
              {lastLine}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
