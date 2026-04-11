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

/** POST /api/agent/prompt : 422 guardrail (detail objet) ou validation Pydantic (detail tableau). */
function parseAgentPrompt422Body(raw: unknown): {
  isInvW06: boolean;
  message: string;
} {
  if (!raw || typeof raw !== "object") {
    return {
      isInvW06: false,
      message:
        "Réponse 422 inattendue du serveur. Vérifiez la console réseau ou contactez l’administrateur.",
    };
  }
  const b = raw as Record<string, unknown>;
  const d = b.detail;

  if (d && typeof d === "object" && !Array.isArray(d)) {
    const obj = d as Record<string, unknown>;
    if (obj.error === "guardrail_inv_w06" && typeof obj.message === "string") {
      return { isInvW06: true, message: obj.message };
    }
    if (typeof obj.message === "string") {
      return { isInvW06: false, message: obj.message };
    }
  }

  if (Array.isArray(d)) {
    const parts = d
      .filter((e): e is Record<string, unknown> => e != null && typeof e === "object")
      .map((e) => (typeof e.msg === "string" ? e.msg : null))
      .filter((m): m is string => m != null);
    const msg =
      parts.length > 0
        ? parts.join(" ")
        : "Requête invalide (champs manquants ou format incorrect).";
    return { isInvW06: false, message: msg };
  }

  if (typeof d === "string") {
    return { isInvW06: false, message: d };
  }
  if (typeof b.message === "string") {
    return { isInvW06: false, message: b.message };
  }

  return {
    isInvW06: false,
    message:
      "Erreur 422 sans détail lisible. Ouvrez l’onglet Réseau du navigateur pour le corps de la réponse.",
  };
}

const SUGGESTED_QUERIES = [
  "Prix du ciment à Bamako ce mois ?",
  "Quelles sont les règles ECHO pour ce marché ?",
  "Où en est ce dossier ?",
];

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  const isSystem = msg.role === "system";

  if (isSystem) {
    return (
      <div
        role="alert"
        className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
      >
        {msg.content}
      </div>
    );
  }

  return (
    <div className={`flex gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div
          aria-hidden="true"
          className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--brand)] text-[10px] font-bold text-white"
        >
          A
        </div>
      )}
      <div
        className={`max-w-[80%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
          isUser
            ? "bg-[var(--brand)] text-white"
            : "bg-gray-100 text-[var(--foreground)] dark:bg-gray-800"
        }`}
      >
        <div className="whitespace-pre-wrap break-words">{msg.content}</div>
        {msg.sources && msg.sources.length > 0 && (
          <div className="mt-2 border-t border-white/20 pt-2 text-[11px] opacity-80 dark:border-gray-700">
            <span className="font-medium">Sources :</span>{" "}
            {msg.sources.map((s, j) => (
              <span key={j}>
                {s.name}
                {s.is_official && (
                  <span className="ml-0.5 text-green-400" title="Source officielle" aria-label="officielle">
                    ✓
                  </span>
                )}
                {j < msg.sources!.length - 1 && ", "}
              </span>
            ))}
          </div>
        )}
      </div>
      {isUser && (
        <div
          aria-hidden="true"
          className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gray-200 text-[10px] font-bold text-gray-600 dark:bg-gray-700 dark:text-gray-300"
        >
          U
        </div>
      )}
    </div>
  );
}

export function AgentConsole({
  workspaceId,
  initialPrompt,
}: {
  /** Si absent, l’agent répond sans contexte dossier (questions générales / marchés). */
  workspaceId?: string;
  /** Déclenche un premier envoi une fois (ex. lien `?agent=` depuis la palette). */
  initialPrompt?: string | null;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [promptBlock, setPromptBlock] = useState<{
    isInvW06: boolean;
    message: string;
  } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const streamAbortRef = useRef<AbortController | null>(null);
  const consumedInitialRef = useRef<string | null>(null);

  useEffect(() => {
    return () => { streamAbortRef.current?.abort(); };
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendPrompt = useCallback(
    async (query: string) => {
      streamAbortRef.current?.abort();
      const ac = new AbortController();
      streamAbortRef.current = ac;

      setPromptBlock(null);
      setMessages((prev) => [...prev, { role: "user", content: query }]);
      setStreaming(true);

      try {
        const body: Record<string, unknown> = { query };
        if (workspaceId) body.workspace_id = workspaceId;

        const res = await api.rawPost("/api/agent/prompt", body, {
          signal: ac.signal,
        });

        if (res.status === 422) {
          let raw: unknown;
          try {
            raw = await res.json();
          } catch {
            raw = null;
          }
          setPromptBlock(parseAgentPrompt422Body(raw));
          setStreaming(false);
          return;
        }

        if (!res.ok) {
          let detail = "";
          try {
            const body = await res.json();
            detail = body.detail || body.message || "";
          } catch {
            // ignore parse error
          }
          const HTTP_ERRORS: Record<number, string> = {
            401: "Session expirée. Reconnectez-vous.",
            403: "Accès refusé. Vérifiez vos permissions pour ce workspace.",
            429: "Trop de requêtes. Réessayez dans quelques secondes.",
          };
          const human =
            HTTP_ERRORS[res.status] ||
            detail ||
            `Erreur serveur (${res.status}). Réessayez ou contactez l'administrateur.`;
          throw new Error(human);
        }

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

              if (event.type === "sources") {
                currentSources = event.sources;
              }

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
            } catch { /* skip malformed */ }
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        setMessages((prev) => [
          ...prev,
          { role: "system", content: `Erreur : ${err instanceof Error ? err.message : "inconnue"}` },
        ]);
      } finally {
        if (streamAbortRef.current === ac) streamAbortRef.current = null;
        setStreaming(false);
        inputRef.current?.focus();
      }
    },
    [workspaceId],
  );

  useEffect(() => {
    const q = initialPrompt?.trim();
    if (!q) return;
    if (consumedInitialRef.current === q) return;
    consumedInitialRef.current = q;
    void sendPrompt(q);
  }, [initialPrompt, sendPrompt]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q || streaming) return;
    setInput("");
    sendPrompt(q);
  }

  const isEmpty = messages.length === 0 && !promptBlock;

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-green-500" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-[var(--foreground)]">
            Assistant DMS
            {!workspaceId && (
              <span className="ml-2 font-normal text-[var(--foreground-muted)]">
                (sans dossier)
              </span>
            )}
          </h3>
        </div>
        {messages.length > 0 && (
          <button
            onClick={() => { setMessages([]); setPromptBlock(null); }}
            className="text-xs text-[var(--foreground-subtle)] hover:text-[var(--foreground-muted)]"
          >
            Effacer
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="h-80 overflow-y-auto p-4">
        {isEmpty ? (
          <div className="flex h-full flex-col items-center justify-center gap-4">
            <p className="text-sm text-[var(--foreground-muted)]">
              {workspaceId
                ? "Posez une question sur les marchés ou ce dossier."
                : "Posez une question générale (marchés, règles). Ouvrez un processus pour le contexte dossier."}
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTED_QUERIES.map((q) => (
                <button
                  key={q}
                  onClick={() => sendPrompt(q)}
                  className="rounded-full border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--foreground-muted)] hover:border-[var(--brand)] hover:text-[var(--brand)] transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((m, i) => (
              <MessageBubble key={i} msg={m} />
            ))}
            {streaming && (
              <div className="flex items-center gap-2 text-xs text-[var(--foreground-muted)]">
                <span className="flex gap-1">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--brand)] [animation-delay:0ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--brand)] [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--brand)] [animation-delay:300ms]" />
                </span>
                Génération…
              </div>
            )}
            {promptBlock && (
              <div
                role="alert"
                className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
              >
                {promptBlock.isInvW06 ? (
                  <span className="font-semibold">Guardrail INV-W06 — </span>
                ) : (
                  <span className="font-semibold">Requête non traitée (422) — </span>
                )}
                {promptBlock.message}
              </div>
            )}
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 border-t border-[var(--border)] p-3"
      >
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Posez une question…"
          disabled={streaming}
          className="flex-1 rounded-lg border border-[var(--border)] bg-transparent px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-subtle)] outline-none focus:border-[var(--brand)] focus:ring-1 focus:ring-[var(--brand)] disabled:opacity-60"
          aria-label="Message pour l'assistant DMS"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--brand-hover)] disabled:opacity-50 transition-colors"
          aria-label="Envoyer"
        >
          {streaming ? (
            <span aria-hidden="true" className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-white" />
            </span>
          ) : (
            "↑"
          )}
        </button>
      </form>
    </div>
  );
}
