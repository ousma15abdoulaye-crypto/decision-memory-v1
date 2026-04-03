# Secrets Railway — fichier local uniquement

Objectif : définir **`RAILWAY_DATABASE_URL`** (et variables optionnelles) **une seule fois** sur le poste, sans les retaper à chaque session PowerShell, **sans jamais les committer**.

## Fichiers

| Fichier | Rôle | Git |
|---------|------|-----|
| `.env.railway.local.example` | Modèle sans secrets | Versionné |
| `.env.railway.local` | Tes secrets (copie du modèle) | **Ignoré** — ne pas ajouter à Git |

Le dépôt ignore déjà `.env.*.local` ; `.env.railway.local` ne peut pas être commité par erreur si l’outil respecte `.gitignore`.

## Mise en place (une fois)

À la racine du repo :

1. Copier le modèle :

   ```powershell
   Copy-Item .env.railway.local.example .env.railway.local
   ```

2. Éditer **`.env.railway.local`** et coller l’URL **publique** PostgreSQL (Railway → Postgres → *Public* / proxy), pas l’hostname `*.railway.internal`.

## Chargement — trois options

### A — Python (recommandé si PowerShell bloque les `.ps1`)

Sur Windows, la politique d’exécution peut interdire `load_railway_env.ps1` (« exécution de scripts désactivée »). Utiliser le lanceur qui charge **`.env.railway.local`** via `python-dotenv` :

```powershell
python scripts/with_railway_env.py python scripts/diagnose_railway_migrations.py
python scripts/with_railway_env.py python scripts/apply_railway_migrations_safe.py --apply
```

Aucun réglage `ExecutionPolicy` requis.

### B — PowerShell : dot-source du script

Depuis la racine du dépôt :

```powershell
. .\scripts\load_railway_env.ps1
```

Le point (`.`) exécute le script **dans** le shell courant pour remplir `$env:RAILWAY_DATABASE_URL`.

Si tu obtiens **PSSecurityException** / scripts désactivés, soit utiliser **A**, soit une fois par utilisateur :

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Puis relancer **`. .\scripts\load_railway_env.ps1`**.

### C — Après chargement (B uniquement)

```powershell
python scripts/diagnose_railway_migrations.py
python scripts/apply_railway_migrations_safe.py --apply
```

## Une ligne (option B)

```powershell
. .\scripts\load_railway_env.ps1; python scripts/diagnose_railway_migrations.py
```

Équivalent sans `.ps1` :

```powershell
python scripts/with_railway_env.py python scripts/diagnose_railway_migrations.py
```

## Références

- [RAILWAY_MIGRATION_RUNBOOK.md](RAILWAY_MIGRATION_RUNBOOK.md)
- [RAILWAY_CLI_LOCAL_LINK.md](RAILWAY_CLI_LOCAL_LINK.md)
