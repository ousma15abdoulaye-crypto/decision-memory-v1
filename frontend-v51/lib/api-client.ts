export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail || body.message || res.statusText);
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

    const res = await fetch(`${API_BASE}${path}`, { headers });
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
  rawPost(
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

    return fetch(`${API_BASE}${path}`, {
      ...init,
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export const api = new ApiClient();
