import { useQuery } from "@tanstack/react-query";

export function useDeliberationThreads(workspaceId: string) {
  return useQuery({
    queryKey: ["m16", "threads", workspaceId],
    queryFn: async () => {
      const r = await fetch(
        `/api/workspaces/${workspaceId}/m16/deliberation/threads`,
        { credentials: "include" },
      );
      if (!r.ok) throw new Error(String(r.status));
      return r.json() as Promise<{ threads: unknown[] }>;
    },
    networkMode: "offlineFirst",
  });
}
