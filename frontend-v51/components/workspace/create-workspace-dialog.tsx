"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, ApiError } from "@/lib/api-client";

const PROCESS_TYPES: { value: string; label: string }[] = [
  { value: "devis_unique", label: "Devis unique" },
  { value: "devis_simple", label: "Devis simple" },
  { value: "devis_formel", label: "Devis formel" },
  { value: "appel_offres_ouvert", label: "Appel d'offres ouvert" },
  { value: "rfp_consultance", label: "RFP / consultance" },
  { value: "contrat_direct", label: "Contrat direct" },
];

const HUMANITARIAN: { value: string; label: string }[] = [
  { value: "none", label: "Aucun" },
  { value: "cat1", label: "Cat. 1" },
  { value: "cat2", label: "Cat. 2" },
  { value: "cat3", label: "Cat. 3" },
  { value: "cat4", label: "Cat. 4" },
];

interface CreateWorkspaceResponse {
  workspace_id: string;
  status: string;
}

interface CreateWorkspaceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateWorkspaceDialog({
  open,
  onOpenChange,
}: CreateWorkspaceDialogProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [referenceCode, setReferenceCode] = useState("");
  const [processType, setProcessType] = useState("devis_simple");
  const [currency, setCurrency] = useState("XOF");
  const [estimatedValue, setEstimatedValue] = useState("");
  const [humanitarianContext, setHumanitarianContext] = useState("none");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function resetForm() {
    setTitle("");
    setReferenceCode("");
    setProcessType("devis_simple");
    setCurrency("XOF");
    setEstimatedValue("");
    setHumanitarianContext("none");
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const ref = referenceCode.trim();
    const tit = title.trim();
    if (!ref || !tit) {
      setError("Le code référence et le titre sont obligatoires.");
      return;
    }

    let ev: number | null = null;
    if (estimatedValue.trim() !== "") {
      const n = Number(estimatedValue.replace(",", "."));
      if (Number.isNaN(n)) {
        setError("Valeur estimée invalide.");
        return;
      }
      ev = n;
    }

    setSubmitting(true);
    try {
      const res = await api.post<CreateWorkspaceResponse>("/api/workspaces", {
        title: tit,
        reference_code: ref,
        process_type: processType,
        currency: currency.trim() || "XOF",
        estimated_value: ev,
        humanitarian_context: humanitarianContext,
      });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      resetForm();
      onOpenChange(false);
      router.push(`/workspaces/${res.workspace_id}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Création impossible.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) resetForm();
        onOpenChange(v);
      }}
    >
      <DialogContent className="max-h-[90vh] overflow-y-auto border-[var(--border)] bg-[var(--surface)] sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-[var(--foreground)]">
            Nouveau processus (workspace)
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="grid gap-4 pt-2">
          {error && (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
            >
              {error}
            </div>
          )}
          <div className="grid gap-1.5">
            <label
              htmlFor="ws-ref"
              className="text-xs font-medium text-[var(--foreground-muted)]"
            >
              Code référence <span className="text-red-500">*</span>
            </label>
            <input
              id="ws-ref"
              value={referenceCode}
              onChange={(e) => setReferenceCode(e.target.value)}
              className="rounded-lg border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-sm text-[var(--foreground)] outline-none focus:border-[var(--brand)] focus:ring-1 focus:ring-[var(--brand)]"
              placeholder="ex. MARCHE-2026-001"
              autoComplete="off"
              required
            />
          </div>
          <div className="grid gap-1.5">
            <label
              htmlFor="ws-title"
              className="text-xs font-medium text-[var(--foreground-muted)]"
            >
              Titre <span className="text-red-500">*</span>
            </label>
            <input
              id="ws-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="rounded-lg border border-[var(--border)] bg-transparent px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--brand)] focus:ring-1 focus:ring-[var(--brand)]"
              placeholder="Intitulé du marché ou du dossier"
              required
            />
          </div>
          <div className="grid gap-1.5">
            <label
              htmlFor="ws-ptype"
              className="text-xs font-medium text-[var(--foreground-muted)]"
            >
              Type de procédure
            </label>
            <select
              id="ws-ptype"
              value={processType}
              onChange={(e) => setProcessType(e.target.value)}
              className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--brand)]"
            >
              {PROCESS_TYPES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <label
                htmlFor="ws-curr"
                className="text-xs font-medium text-[var(--foreground-muted)]"
              >
                Devise
              </label>
              <input
                id="ws-curr"
                value={currency}
                onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                className="rounded-lg border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-sm text-[var(--foreground)] outline-none focus:border-[var(--brand)]"
                maxLength={8}
              />
            </div>
            <div className="grid gap-1.5">
              <label
                htmlFor="ws-ev"
                className="text-xs font-medium text-[var(--foreground-muted)]"
              >
                Valeur estimée (optionnel)
              </label>
              <input
                id="ws-ev"
                value={estimatedValue}
                onChange={(e) => setEstimatedValue(e.target.value)}
                inputMode="decimal"
                className="rounded-lg border border-[var(--border)] bg-transparent px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--brand)]"
                placeholder="—"
              />
            </div>
          </div>
          <div className="grid gap-1.5">
            <label
              htmlFor="ws-hum"
              className="text-xs font-medium text-[var(--foreground-muted)]"
            >
              Contexte humanitaire
            </label>
            <select
              id="ws-hum"
              value={humanitarianContext}
              onChange={(e) => setHumanitarianContext(e.target.value)}
              className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--brand)]"
            >
              {HUMANITARIAN.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm text-[var(--foreground-muted)] hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--brand-hover)] disabled:opacity-50"
            >
              {submitting ? "Création…" : "Créer"}
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
