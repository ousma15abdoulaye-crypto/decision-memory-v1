"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { ThemeToggle } from "@/components/theme-toggle";

interface SidebarWorkspace {
  id: string;
  reference_code: string;
  cognitive: { phase: string; confidence_regime: string };
}

const REGIME_DOT: Record<string, string> = {
  red: "bg-red-500",
  amber: "bg-amber-500",
  yellow: "bg-amber-500",
  green: "bg-green-500",
};

export function Sidebar() {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const { data: dashData } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () =>
      api.get<{ workspaces: SidebarWorkspace[]; total?: number }>(
        "/api/dashboard",
      ),
    refetchInterval: 30_000,
    staleTime: 10_000,
  });

  const linkClass = (href: string) =>
    `flex items-center gap-2 rounded-md px-3 py-2 text-sm transition ${
      pathname === href
        ? "bg-blue-50 font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300"
        : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
    }`;

  return (
    <aside
      className="flex w-56 flex-col border-r border-[var(--border)] bg-[var(--surface)]"
      role="navigation"
      aria-label="Navigation principale"
    >
      <div className="flex h-14 items-center justify-between gap-2 border-b border-[var(--border)] px-4">
        <Link
          href="/dashboard"
          className="text-lg font-bold text-[var(--foreground)]"
          aria-label="Tableau de bord DMS — accueil"
        >
          DMS
        </Link>
        <ThemeToggle />
      </div>

      {/* Cmd+K trigger */}
      <button
        onClick={() => {
          const e = new KeyboardEvent("keydown", {
            key: "k",
            metaKey: true,
            bubbles: true,
          });
          window.dispatchEvent(e);
        }}
        className="mx-3 mt-3 flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-left text-xs text-[var(--foreground-muted)] hover:border-[var(--brand)] hover:text-[var(--foreground)] transition-colors"
        aria-label="Ouvrir la palette de commandes (Ctrl+K)"
      >
        <svg aria-hidden="true" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <span className="flex-1">Rechercher…</span>
        <kbd className="rounded border border-[var(--border)] px-1 font-mono text-[9px]">⌘K</kbd>
      </button>

      <nav className="flex-1 overflow-y-auto p-3 pt-2" aria-label="Menu">
        <div className="space-y-1">
          <Link
            href="/dashboard"
            className={linkClass("/dashboard")}
            aria-current={pathname === "/dashboard" ? "page" : undefined}
          >
            Tableau de bord
          </Link>
        </div>

        {dashData?.workspaces && dashData.workspaces.length > 0 && (
          <div className="mt-4">
            <div className="px-3 pb-1 text-xs font-medium uppercase tracking-wider text-gray-400">
              Workspaces
              {dashData.total != null
                ? ` (${dashData.workspaces.length}/${dashData.total})`
                : ` (${dashData.workspaces.length})`}
            </div>
            <div className="max-h-[min(60vh,28rem)] space-y-0.5 overflow-y-auto">
              {dashData.workspaces.map((ws) => {
                const isActive = pathname === `/workspaces/${ws.id}`;
                return (
                  <Link
                    key={ws.id}
                    href={`/workspaces/${ws.id}`}
                    className={linkClass(`/workspaces/${ws.id}`)}
                    aria-current={isActive ? "page" : undefined}
                    aria-label={`Processus ${ws.reference_code} — phase ${ws.cognitive?.phase ?? "inconnue"}`}
                  >
                    <span
                      aria-hidden="true"
                      className={`h-2 w-2 shrink-0 rounded-full ${
                        REGIME_DOT[ws.cognitive?.confidence_regime] ?? "bg-gray-400"
                      }`}
                    />
                    <span className="truncate">{ws.reference_code}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </nav>

      <div className="border-t border-[var(--border)] p-3">
        <div className="flex items-center justify-between text-xs">
          <span className="truncate text-[var(--foreground-muted)]">
            {user?.full_name ?? "—"}
          </span>
          <button
            onClick={() => {
              logout();
              document.cookie =
                "dms-auth=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
              window.location.href = "/login";
            }}
            className="text-red-500 hover:underline focus-visible:outline-2 focus-visible:outline-red-500 rounded"
            aria-label="Se déconnecter"
          >
            Déconnexion
          </button>
        </div>
      </div>
    </aside>
  );
}
