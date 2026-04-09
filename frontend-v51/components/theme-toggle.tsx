"use client";

import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const next = resolvedTheme === "dark" ? "light" : "dark";
  const label =
    resolvedTheme === undefined
      ? "Thème"
      : resolvedTheme === "dark"
        ? "Clair"
        : "Sombre";

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="h-8 px-2 text-xs"
      onClick={() => setTheme(next)}
      data-testid="theme-toggle"
      aria-label="Basculer thème clair / sombre"
    >
      {label}
    </Button>
  );
}
