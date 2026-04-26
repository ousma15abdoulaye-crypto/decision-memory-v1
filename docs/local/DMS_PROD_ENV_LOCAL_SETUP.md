# DMS Production Env Local Setup

Use this setup when an agent needs production environment variables locally.

Secrets stay outside git.

## 1. Create The Local File

Create:

```text
.local/secrets/dms-production.env
```

This path is ignored by git.

## 2. Add Variables Locally

Put production values in the local file only.

Example without values:

```text
DATABASE_URL=<set locally>
MISTRAL_API_KEY=<set locally>
REDIS_URL=<set locally>
WORKER_AUTH_TOKEN=<set locally>
JWT_SECRET=<set locally>
R2_ACCESS_KEY_ID=<set locally>
R2_SECRET_ACCESS_KEY=<set locally>
R2_BUCKET=<set locally>
R2_ENDPOINT=<set locally>
LABEL_STUDIO_API_KEY=<set locally>
```

## 3. Load In PowerShell

Dot-source the loader so variables stay in the current session:

```powershell
. .\scripts\local\load_dms_prod_env.ps1
```

The loader prints only variable names, never values.

## 4. Check Required Variables

Run:

```powershell
.\scripts\local\check_dms_prod_env.ps1
```

The checker prints only `OK` or `MISSING`, never values.

## 5. Rules

- Never paste secret values into scripts.
- Never paste secret values into reports.
- Never commit `.local/`.
- Never commit `.local/secrets/dms-production.env`.
