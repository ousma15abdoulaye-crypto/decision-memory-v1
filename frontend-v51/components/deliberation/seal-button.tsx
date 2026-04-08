"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

interface SealButtonProps {
  workspaceId: string;
  canSeal: boolean;
  isSealed: boolean;
}

export function SealButton({
  workspaceId,
  canSeal,
  isSealed,
}: SealButtonProps) {
  const [confirm, setConfirm] = useState(false);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      api.patch(`/api/workspaces/${workspaceId}/status`, {
        status: "sealed",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspace", workspaceId] });
      queryClient.invalidateQueries({ queryKey: ["cognitive-state", workspaceId] });
      setConfirm(false);
    },
  });

  if (isSealed) {
    return (
      <div className="flex items-center gap-2 rounded-md bg-green-50 px-4 py-2 text-sm text-green-700 dark:bg-green-950 dark:text-green-300">
        <span>✓</span> Processus scellé
      </div>
    );
  }

  if (!canSeal) return null;

  if (!confirm) {
    return (
      <button
        onClick={() => setConfirm(true)}
        className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600"
      >
        Sceller le processus
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-amber-600 dark:text-amber-400">
        Action irréversible. Confirmer ?
      </span>
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
      >
        {mutation.isPending ? "Scellement..." : "Confirmer"}
      </button>
      <button
        onClick={() => setConfirm(false)}
        className="rounded-md px-3 py-2 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
      >
        Annuler
      </button>
    </div>
  );
}
