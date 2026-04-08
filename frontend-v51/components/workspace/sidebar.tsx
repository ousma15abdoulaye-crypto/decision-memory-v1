"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

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
      api.get<{ workspaces: SidebarWorkspace[] }>("/api/dashboard"),
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
    <aside className="flex w-56 flex-col border-r bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="flex h-14 items-center border-b px-4 dark:border-gray-800">
        <Link href="/dashboard" className="text-lg font-bold">
          DMS
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto p-3">
        <div className="space-y-1">
          <Link href="/dashboard" className={linkClass("/dashboard")}>
            Tableau de bord
          </Link>
        </div>

        {dashData?.workspaces && dashData.workspaces.length > 0 && (
          <div className="mt-4">
            <div className="px-3 pb-1 text-xs font-medium uppercase tracking-wider text-gray-400">
              Workspaces
            </div>
            <div className="space-y-0.5">
              {dashData.workspaces.slice(0, 15).map((ws) => (
                <Link
                  key={ws.id}
                  href={`/workspaces/${ws.id}`}
                  className={linkClass(`/workspaces/${ws.id}`)}
                >
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full ${
                      REGIME_DOT[ws.cognitive?.confidence_regime] || "bg-gray-400"
                    }`}
                  />
                  <span className="truncate">{ws.reference_code}</span>
                </Link>
              ))}
            </div>
          </div>
        )}
      </nav>

      <div className="border-t p-3 dark:border-gray-800">
        <div className="flex items-center justify-between text-xs">
          <span className="truncate text-gray-500">
            {user?.full_name || "\u2014"}
          </span>
          <button
            onClick={() => {
              logout();
              document.cookie =
                "dms-auth=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
              window.location.href = "/login";
            }}
            className="text-red-500 hover:underline"
          >
            Déconnexion
          </button>
        </div>
      </div>
    </aside>
  );
}
