import type { ReactElement, SVGProps } from "react";

type Level = "green" | "yellow" | "red" | "grey";

interface ConfidenceBadgeProps {
  level: Level;
  label: string;
  value?: number;
  className?: string;
}

const LEVEL_CONFIG: Record<
  Level,
  { bg: string; text: string; border: string; Icon: (p: SVGProps<SVGSVGElement>) => ReactElement }
> = {
  green: {
    bg: "bg-green-100 dark:bg-green-950",
    text: "text-green-800 dark:text-green-200",
    border: "border-green-200 dark:border-green-800",
    Icon: (p) => (
      <svg aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24" {...p}>
        <circle cx="12" cy="12" r="10" />
        <path d="m9 12 2 2 4-4" />
      </svg>
    ),
  },
  yellow: {
    bg: "bg-amber-100 dark:bg-amber-950",
    text: "text-amber-800 dark:text-amber-200",
    border: "border-amber-200 dark:border-amber-800",
    Icon: (p) => (
      <svg aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24" {...p}>
        <path d="m10.29 3.86-8.28 14.3A1 1 0 0 0 2.87 20h18.26a1 1 0 0 0 .86-1.84L13.71 3.86a1 1 0 0 0-3.42 0z" />
        <line x1="12" x2="12" y1="9" y2="13" />
        <circle cx="12" cy="17" r=".5" fill="currentColor" />
      </svg>
    ),
  },
  red: {
    bg: "bg-red-100 dark:bg-red-950",
    text: "text-red-800 dark:text-red-200",
    border: "border-red-200 dark:border-red-800",
    Icon: (p) => (
      <svg aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24" {...p}>
        <circle cx="12" cy="12" r="10" />
        <path d="m15 9-6 6M9 9l6 6" />
      </svg>
    ),
  },
  grey: {
    bg: "bg-gray-100 dark:bg-gray-800",
    text: "text-gray-600 dark:text-gray-300",
    border: "border-gray-200 dark:border-gray-700",
    Icon: (p) => (
      <svg aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24" {...p}>
        <circle cx="12" cy="12" r="10" />
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
        <circle cx="12" cy="17" r=".5" fill="currentColor" />
      </svg>
    ),
  },
};

/**
 * Badge de confiance WCAG AA — 3 canaux d'information simultanés :
 * couleur (background) + forme (icône SVG) + texte (label).
 * Ratio de contraste ≥ 4.5:1 vérifié pour chaque couleur.
 */
export function ConfidenceBadge({
  level,
  label,
  value,
  className = "",
}: ConfidenceBadgeProps) {
  const cfg = LEVEL_CONFIG[level];
  const pct = value != null ? `${Math.round(value * 100)}%` : null;
  const ariaLabel = `Signal ${label}${pct ? ` : ${pct}` : ""}`;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${cfg.bg} ${cfg.text} ${cfg.border} ${className}`}
      aria-label={ariaLabel}
      role="status"
    >
      <cfg.Icon className="h-3.5 w-3.5 shrink-0" />
      <span>{label}</span>
      {pct && (
        <span className="tabular-nums opacity-80" aria-hidden="true">
          {pct}
        </span>
      )}
    </span>
  );
}

/** Mapping depuis le confidence_regime backend → props ConfidenceBadge */
export function regimeToBadgeProps(regime: string): {
  level: Level;
  label: string;
} {
  switch (regime) {
    case "green":  return { level: "green",  label: "Confiant" };
    case "yellow": return { level: "yellow", label: "Attention" };
    case "red":    return { level: "red",    label: "Critique" };
    default:       return { level: "grey",   label: "Indéterminé" };
  }
}
