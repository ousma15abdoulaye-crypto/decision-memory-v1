const RAW_API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Base sans slash final — utilisée pour tous les `fetch`. */
export const API_BASE = RAW_API_BASE.replace(/\/$/, "");

/** Indique si l’URL d’API ressemble à un serveur local (défaut du build). */
function apiBaseLooksLocalhost(): boolean {
  try {
    const u = new URL(API_BASE);
    const h = u.hostname.toLowerCase();
    return h === "localhost" || h === "127.0.0.1";
  } catch {
    return API_BASE.includes("localhost") || API_BASE.includes("127.0.0.1");
  }
}

/**
 * Message d’aide quand `fetch` échoue au réseau (CORS, mauvaise URL, API down, mixed content).
 * Le cas le plus fréquent en prod : NEXT_PUBLIC_API_URL non défini au build → localhost dans le bundle.
 */
function failedToFetchUserMessage(): string {
  const isBrowser = typeof window !== "undefined";
  const pageHost = isBrowser ? window.location.hostname : "";
  const pageNotLocal =
    pageHost !== "" &&
    pageHost !== "localhost" &&
    pageHost !== "127.0.0.1";

  let msg =
    "Impossible de joindre l’API (réseau ou navigateur a bloqué la requête). ";

  if (isBrowser && apiBaseLooksLocalhost() && pageNotLocal) {
    msg +=
      `Vous êtes sur « ${pageHost} » mais l’URL d’API du build est « ${API_BASE} ». ` +
      "Définissez **NEXT_PUBLIC_API_URL** sur l’hébergeur du frontend (URL **publique HTTPS** du FastAPI, ex. `https://xxx.up.railway.app`) puis **redéployez** (rebuild obligatoire — variable injectée au build). ";
  }

  msg +=
    "Sinon : vérifier que l’API répond, éviter le **mixed content** (page en HTTPS et API en HTTP souvent bloquée), et que **CORS_ORIGINS** côté API contient l’origine exacte de cette page (ex. `https://votre-frontend.up.railway.app`).";

  return msg;
}

function rethrowIfNetworkFailure(e: unknown): never {
  if (e instanceof TypeError) {
    const m = (e.message || "").toLowerCase();
    if (m.includes("fetch") || m.includes("network") || m.includes("failed")) {
      throw new Error(failedToFetchUserMessage());
    }
  }
  throw e;
}

class ApiClient {
  /** Fusionne RequestInit.headers (Headers, tableau ou objet) sans perdre d’entrées. */
  private mergeHeaders(
    base: Record<string, string>,
    init?: HeadersInit,
  ): Record<string, string> {
    const out = { ...base };
    if (init == null) return out;
    new Headers(init).forEach((value, key) => {
      out[key] = value;
    });
    return out;
  }

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem("dms-auth");
    if (!raw) return null;
    try {
      return JSON.parse(raw)?.state?.accessToken ?? null;
    } catch {
      return null;
    }
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const token = this.getToken();
    const headers = this.mergeHeaders(
      { "Content-Type": "application/json" },
      options.headers,
    );
    if (token) headers["Authorization"] = `Bearer ${token}`;

    let res: Response;
    try {
      res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    } catch (e) {
      rethrowIfNetworkFailure(e);
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({})) as Record<string, unknown>;
      const message =
        typeof body.detail === "string"
          ? body.detail
          : typeof body.message === "string"
            ? body.message
            : res.statusText;
      throw new ApiError(res.status, message, body);
    }
    return res.json();
  }

  get<T>(path: string) {
    return this.request<T>(path);
  }

  post<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  patch<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  /** Téléchargement binaire (PDF, XLSX) — ne parse pas le corps en JSON. */
  async downloadBlob(
    path: string,
  ): Promise<{ blob: Blob; filename: string | null }> {
    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    let res: Response;
    try {
      res = await fetch(`${API_BASE}${path}`, { headers });
    } catch (e) {
      rethrowIfNetworkFailure(e);
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(
        res.status,
        (body.detail || body.message || res.statusText) as string,
      );
    }
    const cd = res.headers.get("Content-Disposition");
    let filename: string | null = null;
    if (cd) {
      const m = cd.match(/filename="?([^";]+)"?/);
      if (m) filename = m[1];
    }
    const blob = await res.blob();
    return { blob, filename };
  }

  /** POST brut (ex. SSE) — en-têtes auth alignés sur get/post ; supporte `signal` (AbortController). */
  async rawPost(
    path: string,
    body: unknown,
    init: RequestInit = {},
  ): Promise<Response> {
    const token = this.getToken();
    const headers = this.mergeHeaders(
      { "Content-Type": "application/json" },
      init.headers,
    );
    if (token) headers["Authorization"] = `Bearer ${token}`;

    try {
      return await fetch(`${API_BASE}${path}`, {
        ...init,
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
    } catch (e) {
      rethrowIfNetworkFailure(e);
    }
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public readonly body: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const api = new ApiClient();
