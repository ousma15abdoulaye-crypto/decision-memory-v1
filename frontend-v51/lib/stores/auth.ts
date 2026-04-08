import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  tenant_id: string;
}

const ACCESS_COOKIE_MAX_AGE = 60 * 60; // 1 h (mandat) ; JWT access serveur souvent 30 min

function setSessionCookies(access: string) {
  if (typeof document === "undefined") return;
  const enc = encodeURIComponent(access);
  document.cookie = [
    `dms_token=${enc}`,
    "path=/",
    "SameSite=Strict",
    `max-age=${ACCESS_COOKIE_MAX_AGE}`,
  ].join("; ");
  document.cookie = [
    "dms-auth=1",
    "path=/",
    "SameSite=Strict",
    "max-age=3600",
  ].join("; ");
}

function clearSessionCookies() {
  if (typeof document === "undefined") return;
  document.cookie = "dms_token=; path=/; max-age=0";
  document.cookie = "dms-auth=; path=/; max-age=0";
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  setAuth: (user: User, access: string, refresh: string | null) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      setAuth: (user, access, refresh) => {
        set({
          user,
          accessToken: access,
          refreshToken: refresh ?? null,
        });
        setSessionCookies(access);
      },
      logout: () => {
        clearSessionCookies();
        set({ user: null, accessToken: null, refreshToken: null });
      },
      isAuthenticated: () => !!get().accessToken,
    }),
    { name: "dms-auth" },
  ),
);
