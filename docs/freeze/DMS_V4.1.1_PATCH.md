# DMS V4.1.1 — PATCH DOCUMENTATION

## Statut
PATCH OFFICIEL · complète V4.1.0 sans le modifier

## Date
2026-03-04

## Auteur
CTO — Abdoulaye Ousmane

---

## CORRECTION 1 — Portée produit

### V4.1.0 (inexact)
"Système d'aide à la décision procurement humanitaire."

### V4.1.1 (correct)
Système d'aide à la décision procurement pour :
- États et collectivités (marchés publics · DGMP Mali · AOF)
- Organisations humanitaires (SCI · MSF · OCHA · standards SPHERE)
- ONG de développement (AFD · GIZ · USAID · projets terrain)
- Entreprises privées (procurement corporate · supply chain)
- Industries extractives (mines · pétrole · BTP · logistique)

Invariants SCI §4.2 et §5.2 = profil défaut beta uniquement.
Autres profils activés via M13 (PROFILES).

---

## CORRECTION 2 — Infrastructure PostgreSQL

| Environnement | Version | Notes |
|---|---|---|
| PostgreSQL prod Railway | 17.7 | Environnement de production |
| PostgreSQL local Windows | 15.16 | Environnement de développement |

**Backup UNIQUEMENT via Python psycopg3.**
`pg_dump` local v15 incompatible avec Railway 17.7.

---

## CORRECTION 3 — Profils M13 (liste initiale)

| Profil | Description |
|---|---|
| `PROFIL_SCI` | Seuils SCI · comité · critères éliminatoires |
| `PROFIL_DGMP` | Seuils DGMP Mali · appel d'offres public |
| `PROFIL_ONG` | Standards bailleurs (USAID · UE · AFD) |
| `PROFIL_CORPORATE` | Procurement entreprise privée |
| `PROFIL_MINE` | Procurement industrie extractive · volumes lourds |

---

## CORRECTION 4 — Variables d'environnement clés API

| Variable Railway | Usage | Local |
|---|---|---|
| `LLAMADMS` | LlamaCloud API key (parsing PDF) | Export `$env:LLAMADMS` |
| `DATABASE_URL` | PostgreSQL connexion | `.env` local |

**Ne jamais hardcoder les clés. Ne jamais committer `.env` avec des clés réelles.**
