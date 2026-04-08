"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api-client";

interface SSEEvent {
  type: "token" | "sources" | "tool_call" | "done" | "error";
  content?: string;
  sources?: { name: string; source_type: string; is_official: boolean }[];
  tool?: string;
  code?: string;
  message?: string;
}

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SSEEvent["sources"];
}

export function AgentConsole({ workspaceId }: { workspaceId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [guardrailBlock, setGuardrailBlock] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const streamAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
    };
  }, []);

  const sendPrompt = useCallback(
    async (query: string) => {
      streamAbortRef.current?.abort();
      const ac = new AbortController();
      streamAbortRef.current = ac;

      setGuardrailBlock(null);
      setMessages((prev) => [...prev, { role: "user", content: query }]);
      setStreaming(true);

      try {
        const res = await api.rawPost(
          "/api/agent/prompt",
          {
            query,
            workspace_id: workspaceId,
          },
          { signal: ac.signal },
        );

        if (res.status === 422) {
          const body = await res.json();
          setGuardrailBlock(
            body.detail?.message || body.message || "Requête bloquée par le guardrail INV-W06.",
          );
          ac.abort();
          setStreaming(false);
          return;
        }

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const reader = res.body?.getReader();
        if (!reader) return;

        let buffer = "";
        let assistantContent = "";
        let currentSources: SSEEvent["sources"] | undefined;

        const decoder = new TextDecoder();

        while (true) {
          if (ac.signal.aborted) break;
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const block of lines) {
            if (ac.signal.aborted) break;
            const line = block.replace(/^data: /, "").trim();
            if (!line || line === "[DONE]") continue;

            try {
              const event: SSEEvent = JSON.parse(line);

              if (event.type === "token" && event.content) {
                assistantContent += event.content;
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last?.role === "assistant") {
                    return [
                      ...updated.slice(0, -1),
                      { ...last, content: assistantContent, sources: currentSources },
                    ];
                  }
                  return [
                    ...updated,
                    { role: "assistant", content: assistantContent, sources: currentSources },
                  ];
                });
              }

              if (event.type === "sources") {
                currentSources = event.sources;
              }
            } catch {
              // skip malformed events
            }
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        setMessages((prev) => [
          ...prev,
          {
            role: "system",
            content: `Erreur : ${err instanceof Error ? err.message : "inconnue"}`,
          },
        ]);
      } finally {
        if (streamAbortRef.current === ac) {
          streamAbortRef.current = null;
        }
        setStreaming(false);
        scrollRef.current?.scrollIntoView({ behavior: "smooth" });
      }
    },
    [workspaceId],
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q || streaming) return;
    setInput("");
    sendPrompt(q);
  }

  return (
    <div className="rounded-lg border dark:border-gray-800">
      <div className="border-b px-4 py-2 dark:border-gray-800">
        <h3 className="text-sm font-medium">Assistant DMS</h3>
      </div>

      <div className="h-80 overflow-y-auto p-4 space-y-3 text-sm">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rounded-lg p-3 ${
              m.role === "user"
                ? "ml-8 bg-blue-50 dark:bg-blue-950"
                : m.role === "system"
                  ? "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300"
                  : "mr-8 bg-gray-100 dark:bg-gray-800"
            }`}
          >
            <div className="whitespace-pre-wrap">{m.content}</div>
            {m.sources && m.sources.length > 0 && (
              <div className="mt-2 border-t pt-2 text-xs text-gray-500 dark:border-gray-700">
                Sources :{" "}
                {m.sources.map((s, j) => (
                  <span key={j}>
                    {s.name}
                    {s.is_official && " ✓"}
                    {j < m.sources!.length - 1 && ", "}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}

        {guardrailBlock && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
            <strong>Guardrail INV-W06</strong> — {guardrailBlock}
          </div>
        )}

        <div ref={scrollRef} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 border-t p-3 dark:border-gray-800"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Posez une question sur les marchés..."
          disabled={streaming}
          className="flex-1 rounded-md border bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {streaming ? "..." : "Envoyer"}
        </button>
      </form>
    </div>
  );
}
