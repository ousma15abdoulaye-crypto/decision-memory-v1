"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth";
import { api } from "@/lib/api-client";

/** Réponse POST /api/auth/login (`LoginResponse` côté serveur). */
interface LoginJsonResponse {
  user: {
    id: number;
    email: string;
    username: string;
    full_name: string;
    role: string;
    tenant_id: string;
  };
  access_token: string;
  token_type: string;
  refresh_token: string;
}

export default function LoginPage() {
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const id = loginId.trim();
      const res = await api.postFormUnauthenticated<LoginJsonResponse>(
        "/api/auth/login",
        {
          email: id,
          username: id,
          password,
        },
      );

      const u = res.user;
      setAuth(
        {
          id: u.id,
          email: u.email,
          full_name: u.full_name ?? "",
          role: u.role,
          tenant_id: u.tenant_id ?? "",
        },
        res.access_token,
        res.refresh_token ?? null,
      );
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
      <div className="w-full max-w-sm space-y-6 rounded-lg border bg-white p-8 shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-bold tracking-tight">DMS</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Decision Memory System
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <label htmlFor="loginId" className="text-sm font-medium">
              Email ou nom d&apos;utilisateur
            </label>
            <input
              id="loginId"
              type="text"
              name="username"
              autoComplete="username"
              value={loginId}
              onChange={(e) => setLoginId(e.target.value)}
              required
              className="w-full rounded-md border bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700"
              placeholder="prenom.nom@organisation.org"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">
              Mot de passe
            </label>
            <input
              id="password"
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-md border bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
