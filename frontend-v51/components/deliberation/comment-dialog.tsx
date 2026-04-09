"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

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
      queryClient.invalidateQueries({
        queryKey: ["evaluation-frame", workspaceId],
      });
      onClose();
    },
  });

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>Ajouter un commentaire</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
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

        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Annuler
          </Button>
          <Button
            type="button"
            onClick={() =>
              mutation.mutate({
                content,
                is_flag: isFlag,
                criterion_id: criterionId,
                supplier_id: supplierId,
              })
            }
            disabled={!content.trim() || mutation.isPending}
          >
            {mutation.isPending ? "Envoi..." : "Publier"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
