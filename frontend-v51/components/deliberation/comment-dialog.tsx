"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

interface CommentDialogProps {
  workspaceId: string;
  criterionId?: string;
  supplierId?: string;
  onClose: () => void;
}

export function CommentDialog({
  workspaceId,
  criterionId,
  supplierId,
  onClose,
}: CommentDialogProps) {
  const [content, setContent] = useState("");
  const [isFlag, setIsFlag] = useState(false);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (data: {
      content: string;
      is_flag: boolean;
      criterion_id?: string;
      supplier_id?: string;
    }) => api.post(`/api/workspaces/${workspaceId}/comments`, data),
    retry: 3,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspace", workspaceId] });
      onClose();
    },
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="comment-dialog-title"
    >
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg dark:bg-gray-900">
        <h2 id="comment-dialog-title" className="text-lg font-semibold">Ajouter un commentaire</h2>

        <div className="mt-4 space-y-4">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={4}
            className="w-full rounded-md border bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700"
            placeholder="Votre commentaire ou observation..."
          />

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isFlag}
              onChange={(e) => setIsFlag(e.target.checked)}
              className="rounded"
            />
            <span className="text-amber-600 dark:text-amber-400">
              Signaler un point d&apos;attention
            </span>
          </label>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            Annuler
          </button>
          <button
            onClick={() =>
              mutation.mutate({
                content,
                is_flag: isFlag,
                criterion_id: criterionId,
                supplier_id: supplierId,
              })
            }
            disabled={!content.trim() || mutation.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Envoi..." : "Publier"}
          </button>
        </div>
      </div>
    </div>
  );
}
