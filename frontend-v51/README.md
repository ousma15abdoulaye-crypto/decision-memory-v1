# DMS frontend-v51 (Next.js)

## API backend (`NEXT_PUBLIC_API_URL`)

Toutes les requêtes passent par l’URL de l’API FastAPI racine (`main.py`), **sans** préfixe `/api` pour l’auth :

| Variable | Exemple local | Production |
|----------|---------------|------------|
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | `https://decision-memory-v1-production.up.railway.app:8080` |

- **Login** : `POST {NEXT_PUBLIC_API_URL}/auth/login` (JSON `email` + `password`). Le champ `email` accepte aussi le **nom d’utilisateur**.
- **Compat Swagger** : `POST /auth/token` (formulaire OAuth2 `username` / `password`).
- **Ressources V5.1** : `GET /api/dashboard`, `/api/workspaces/...`, etc.

Fichier client : [`lib/api-client.ts`](lib/api-client.ts) (`API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`).

> **⚠️ Railway / production** : `NEXT_PUBLIC_*` variables are inlined at **build time** by Next.js.
> Set `NEXT_PUBLIC_API_URL` in the Railway service environment **before** triggering a deploy,
> otherwise the built bundle will fall back to `http://localhost:8000` and all API calls will fail.
> See [`railway.toml`](railway.toml) and [`.env.example`](.env.example) for reference values.

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
