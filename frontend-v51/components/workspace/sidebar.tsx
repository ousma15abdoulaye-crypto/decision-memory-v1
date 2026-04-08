"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Tableau de bord", icon: "📊" },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <aside className="flex w-56 flex-col border-r bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="flex h-14 items-center border-b px-4 dark:border-gray-800">
        <Link href="/dashboard" className="text-lg font-bold">
          DMS
        </Link>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm transition ${
              pathname === item.href
                ? "bg-blue-50 font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
            }`}
          >
            <span>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="border-t p-3 dark:border-gray-800">
        <div className="flex items-center justify-between text-xs">
          <span className="truncate text-gray-500">
            {user?.full_name || "—"}
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
