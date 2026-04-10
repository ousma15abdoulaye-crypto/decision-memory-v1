import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Garde UX (middleware Next.js 16) : on lit seulement le payload JWT (exp). La signature n'est pas
 * vérifiée ici — l'API FastAPI reste la barrière d'authentification réelle.
 */
const PUBLIC = ["/login", "/api/auth", "/_next", "/favicon"];

/** Décode l'expiration JWT sans vérifier la signature (usage middleware uniquement). */
function jwtExpSeconds(token: string): number | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    let b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const pad = b64.length % 4;
    if (pad) b64 += "=".repeat(4 - pad);
    const json = atob(b64);
    const payload = JSON.parse(json) as { exp?: number };
    return typeof payload.exp === "number" ? payload.exp : null;
  } catch {
    return null;
  }
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Page d'accueil publique (liens Connexion / Tableau de bord) — ne pas exiger JWT.
  if (pathname === "/" || PUBLIC.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const raw = request.cookies.get("dms_token")?.value;
  let token: string | null = null;
  if (raw) {
    try {
      token = decodeURIComponent(raw);
    } catch {
      token = null;
    }
  }
  if (!token) {
    token =
      request.headers.get("authorization")?.replace(/^Bearer\s+/i, "") ?? null;
  }

  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const exp = jwtExpSeconds(token);
  if (exp === null || exp < Math.floor(Date.now() / 1000)) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
