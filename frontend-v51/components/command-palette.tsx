"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useAuthStore } from "@/lib/stores/auth";

interface WorkspaceItem {
  id: string;
  reference_code: string;
  title: string;
  status: string;
}

interface DashboardResponse {
  workspaces: WorkspaceItem[];
}

interface CommandPaletteProps {
  currentWorkspaceId?: string;
  isWorkspaceSealed?: boolean;
}

export function CommandPalette({
  currentWorkspaceId,
  isWorkspaceSealed,
}: CommandPaletteProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardResponse>("/api/dashboard"),
    staleTime: 30_000,
    enabled: open,
  });

  const workspaces = data?.workspaces ?? [];
  const filteredWorkspaces = search
    ? workspaces.filter(
        (w) =>
          w.reference_code.toLowerCase().includes(search.toLowerCase()) ||
          w.title.toLowerCase().includes(search.toLowerCase()),
      )
    : workspaces.slice(0, 5);

  const close = useCallback(() => {
    setOpen(false);
    setSearch("");
  }, []);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  if (!open) return null;

  function navigate(path: string) {
    close();
    router.push(path);
  }

  const isInWorkspace = !!currentWorkspaceId;
  const looksLikeQuery = search.length > 3 && !filteredWorkspaces.length;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
        aria-hidden="true"
        onClick={close}
      />

      {/* Panel */}
      <div
        role="dialog"
        aria-label="Palette de commandes"
        aria-modal="true"
        className="fixed inset-x-0 top-24 z-50 mx-auto w-full max-w-xl px-4"
      >
        <Command
          className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl"
          onKeyDown={(e) => {
            if (e.key === "Escape") close();
          }}
          shouldFilter={false}
        >
          <div className="flex items-center gap-2 border-b border-[var(--border)] px-4 py-3">
            {/* Search icon */}
            <svg
              aria-hidden="true"
              className="h-4 w-4 shrink-0 text-[var(--foreground-muted)]"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <Command.Input
              ref={inputRef}
              value={search}
              onValueChange={setSearch}
              placeholder="Rechercher ou poser une question…"
              className="flex-1 bg-transparent text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-subtle)] outline-none"
              aria-label="Recherche ou question pour l'assistant"
            />
            <kbd
              className="rounded border border-[var(--border)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--foreground-subtle)]"
              aria-label="Appuyer sur Échap pour fermer"
            >
              Esc
            </kbd>
          </div>

          <Command.List
            className="max-h-96 overflow-y-auto"
            aria-label="Résultats de la recherche"
          >
            <Command.Empty className="py-8 text-center text-sm text-[var(--foreground-muted)]">
              {looksLikeQuery ? (
                <button
                  className="text-[var(--brand)] hover:underline"
                  onClick={() => {
                    close();
                    router.push(`?agent=${encodeURIComponent(search)}`);
                  }}
                >
                  Poser à l&apos;assistant : &ldquo;{search}&rdquo;
                </button>
              ) : (
                "Aucun résultat."
              )}
            </Command.Empty>

            {/* Workspaces */}
            {filteredWorkspaces.length > 0 && (
              <Command.Group
                heading={
                  <span className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--foreground-subtle)]">
                    Processus
                  </span>
                }
              >
                {filteredWorkspaces.map((ws) => (
                  <Command.Item
                    key={ws.id}
                    value={ws.reference_code}
                    onSelect={() => navigate(`/workspaces/${ws.id}`)}
                    className="flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm text-[var(--foreground)] hover:bg-gray-50 dark:hover:bg-gray-800 data-[selected=true]:bg-[var(--brand-muted)] data-[selected=true]:text-[var(--brand)]"
                    aria-label={`Ouvrir processus ${ws.reference_code} : ${ws.title}`}
                  >
                    <svg
                      aria-hidden="true"
                      className="h-4 w-4 shrink-0 text-[var(--foreground-muted)]"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2}
                      viewBox="0 0 24 24"
                    >
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                    <div className="min-w-0 flex-1">
                      <div className="font-mono text-xs font-semibold">{ws.reference_code}</div>
                      <div className="truncate text-xs text-[var(--foreground-muted)]">{ws.title}</div>
                    </div>
                    {ws.status === "sealed" && (
                      <span className="shrink-0 text-xs text-green-600 dark:text-green-400">Scellé</span>
                    )}
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Actions contextuelles */}
            {isInWorkspace && (
              <Command.Group
                heading={
                  <span className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--foreground-subtle)]">
                    Actions
                  </span>
                }
              >
                <Command.Item
                  value="sync m14"
                  onSelect={() => {
                    close();
                    document
                      .querySelector<HTMLButtonElement>("[data-m14-sync]")
                      ?.click();
                  }}
                  className="flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm text-[var(--foreground)] hover:bg-gray-50 dark:hover:bg-gray-800 data-[selected=true]:bg-[var(--brand-muted)] data-[selected=true]:text-[var(--brand)]"
                  aria-label="Synchroniser les scores M14 vers les assessments M16"
                >
                  <svg aria-hidden="true" className="h-4 w-4 shrink-0 text-[var(--foreground-muted)]" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path d="M21 2v6h-6M3 22v-6h6M3 11a9 9 0 0 1 15-6.7L21 8M3 13l3 3.3A9 9 0 0 0 21 13" />
                  </svg>
                  Synchroniser M14 → M16
                </Command.Item>

                {isWorkspaceSealed && (
                  <Command.Item
                    value="exporter pv"
                    onSelect={() => {
                      close();
                      document
                        .querySelector<HTMLButtonElement>("[data-pv-export]")
                        ?.click();
                    }}
                    className="flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm text-[var(--foreground)] hover:bg-gray-50 dark:hover:bg-gray-800 data-[selected=true]:bg-[var(--brand-muted)] data-[selected=true]:text-[var(--brand)]"
                    aria-label="Exporter le Procès-Verbal"
                  >
                    <svg aria-hidden="true" className="h-4 w-4 shrink-0 text-[var(--foreground-muted)]" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
                    </svg>
                    Exporter PV
                  </Command.Item>
                )}
              </Command.Group>
            )}

            {/* Suggestions agent */}
            {!isInWorkspace && !search && (
              <Command.Group
                heading={
                  <span className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--foreground-subtle)]">
                    Questions fréquentes
                  </span>
                }
              >
                {[
                  "Prix du ciment à Mopti ce mois ?",
                  "Quelles sont les règles ECHO pour ce marché ?",
                  "Quel est le seuil DAO au Mali ?",
                ].map((q) => (
                  <Command.Item
                    key={q}
                    value={q}
                    onSelect={() => {
                      close();
                      router.push(`/dashboard?agent=${encodeURIComponent(q)}`);
                    }}
                    className="flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm text-[var(--foreground)] hover:bg-gray-50 dark:hover:bg-gray-800 data-[selected=true]:bg-[var(--brand-muted)] data-[selected=true]:text-[var(--brand)]"
                    aria-label={`Poser la question : ${q}`}
                  >
                    <svg aria-hidden="true" className="h-4 w-4 shrink-0 text-[var(--foreground-muted)]" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" />
                      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01" />
                    </svg>
                    {q}
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Système */}
            <Command.Group
              heading={
                <span className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--foreground-subtle)]">
                  Système
                </span>
              }
            >
              <Command.Item
                value="dashboard accueil"
                onSelect={() => navigate("/dashboard")}
                className="flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm text-[var(--foreground)] hover:bg-gray-50 dark:hover:bg-gray-800 data-[selected=true]:bg-[var(--brand-muted)] data-[selected=true]:text-[var(--brand)]"
                aria-label="Retour au tableau de bord"
              >
                <svg aria-hidden="true" className="h-4 w-4 shrink-0 text-[var(--foreground-muted)]" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <rect x="3" y="3" width="7" height="7" rx="1" />
                  <rect x="14" y="3" width="7" height="7" rx="1" />
                  <rect x="14" y="14" width="7" height="7" rx="1" />
                  <rect x="3" y="14" width="7" height="7" rx="1" />
                </svg>
                Tableau de bord
              </Command.Item>

              <Command.Item
                value="se déconnecter logout"
                onSelect={() => {
                  close();
                  logout();
                  router.push("/login");
                }}
                className="flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950 data-[selected=true]:bg-red-50 dark:data-[selected=true]:bg-red-950"
                aria-label="Se déconnecter de l'application"
              >
                <svg aria-hidden="true" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
                </svg>
                Se déconnecter
              </Command.Item>
            </Command.Group>
          </Command.List>

          {/* Footer hint */}
          <div className="flex items-center gap-3 border-t border-[var(--border)] px-4 py-2 text-[10px] text-[var(--foreground-subtle)]">
            <span><kbd className="font-mono">↑↓</kbd> naviguer</span>
            <span><kbd className="font-mono">↵</kbd> sélectionner</span>
            <span><kbd className="font-mono">Esc</kbd> fermer</span>
          </div>
        </Command>
      </div>
    </>
  );
}
