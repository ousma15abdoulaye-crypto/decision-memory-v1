"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";

interface SealButtonProps {
  workspaceId: string;
  canSeal: boolean;
  isSealed: boolean;
}

interface SealPreconditionError {
  error: string;
  message: string;
  errors: string[];
  warnings: string[];
}

export function SealButton({ workspaceId, canSeal, isSealed }: SealButtonProps) {
  const [confirm, setConfirm] = useState(false);
  const [preconditionErrors, setPreconditionErrors] = useState<SealPreconditionError | null>(null);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      api.patch(`/api/workspaces/${workspaceId}/status`, { status: "sealed" }),
    retry: false,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspace", workspaceId] });
      queryClient.invalidateQueries({ queryKey: ["cognitive-state", workspaceId] });
      setConfirm(false);
      setPreconditionErrors(null);
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 422) {
        const body = err.body as Partial<SealPreconditionError>;
        setPreconditionErrors({
          error: body.error ?? "seal_preconditions_failed",
          message: body.message ?? err.message,
          errors: Array.isArray(body.errors) ? body.errors : [err.message],
          warnings: Array.isArray(body.warnings) ? body.warnings : [],
        });
        setConfirm(false);
      }
    },
    onError: () => {
      setConfirm(false);
    },
  });

  if (isSealed) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-green-50 px-4 py-2 text-sm font-medium text-green-700 dark:bg-green-950 dark:text-green-300">
        <span aria-hidden="true">✓</span> Processus scellé
      </div>
    );
  }

  if (!canSeal) return null;

  return (
    <div className="space-y-3">
      {/* Precondition errors panel (422) */}
      {preconditionErrors && (
        <div
          role="alert"
          className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-950"
        >
          <p className="font-semibold text-amber-800 dark:text-amber-200">
            Pré-conditions non remplies
          </p>
          {preconditionErrors.errors.length > 0 && (
            <ul className="mt-2 space-y-1 text-amber-700 dark:text-amber-300">
              {preconditionErrors.errors.map((e, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span aria-hidden="true" className="mt-0.5 text-red-500">✗</span>
                  {e}
                </li>
              ))}
            </ul>
          )}
          {preconditionErrors.warnings.length > 0 && (
            <ul className="mt-2 space-y-1 text-amber-600 dark:text-amber-400">
              {preconditionErrors.warnings.map((w, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span aria-hidden="true" className="mt-0.5">⚠</span>
                  {w}
                </li>
              ))}
            </ul>
          )}
          <button
            onClick={() => setPreconditionErrors(null)}
            className="mt-3 text-xs text-amber-600 underline hover:no-underline dark:text-amber-400"
          >
            Fermer
          </button>
        </div>
      )}

      {/* Mutation error (non-422) */}
      {mutation.isError && !preconditionErrors && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {(mutation.error as Error).message}
        </div>
      )}

      {!confirm ? (
        <button
          onClick={() => {
            setPreconditionErrors(null);
            setConfirm(true);
          }}
          className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 focus-visible:outline-2 focus-visible:outline-amber-500"
        >
          Sceller le processus
        </button>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-amber-700 dark:text-amber-400">
            Action irréversible. Confirmer ?
          </span>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-red-600"
          >
            {mutation.isPending ? "Scellement…" : "Confirmer"}
          </button>
          <button
            onClick={() => {
              setConfirm(false);
              mutation.reset();
            }}
            className="rounded-lg px-3 py-2 text-sm text-[var(--foreground-muted)] hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Annuler
          </button>
        </div>
      )}
    </div>
  );
}
