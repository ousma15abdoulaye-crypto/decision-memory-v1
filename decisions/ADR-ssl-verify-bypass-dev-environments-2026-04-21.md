# ADR — SSL verify bypass opt-in pour environnements dev avec proxy TLS

**Référence** : DMS-ADR-SSL-BYPASS-DEV-OPT-IN-V1  
**Date** : 2026-04-21  
**Auteur** : CTO Senior DMS (ex-post)  
**Ordonné par** : CTO principal DMS (décision opérationnelle E4-bis)  
**Commit d'application** : 2ef18d52  
**Contexte** : débouclage extraction E4-bis — proxy TLS entreprise SCI

---

## Contexte

Le backend annotation DMS (service Railway nouvellement créé pour DMS, `dms-annotation-backend-production.up.railway.app`) était joignable en `GET /health` (HTTP 200) mais les appels d'extraction depuis l'environnement Claude Code échouaient sur `SSL CERTIFICATE_VERIFY_FAILED`.

**Cause** : interception TLS par un proxy entreprise SCI dont le CA intermédiaire n'est pas dans le trust store de l'environnement agent.

---

## Pattern projet préexistant

Le fichier `.env.local` documente déjà 2 patterns SSL bypass opérationnels DMS :
- Label Studio (`LABEL_STUDIO_SSL_VERIFY=0`)
- Mistral OCR (`MISTRAL_HTTPX_VERIFY_SSL=0`)

Ce sont des patterns doctrinaux projet pour les environnements dev soumis à proxy TLS entreprise, non formalisés en ADR jusqu'ici.

---

## Décision

Extension du pattern SSL bypass opt-in à l'appel annotation-backend pour les environnements dev :

- **Variable** : `HTTPX_VERIFY_SSL` (defaults to `1` / secure)
- **Fichiers modifiés** (commit 2ef18d52) :
  - `src/couche_a/extraction/backend_client.py` (fonction `call_annotation_backend`)
  - `scripts/e4_run_benchmark.py` (fonction `precheck_annotation_backend`)

---

## Posture de sécurité

**Strictement opt-in** :
- **Défaut** : `verify=True` (comportement sécurisé)
- **Désactivation** : uniquement via `HTTPX_VERIFY_SSL=0` en variable d'environnement
- **Jamais actif en production** — les environnements Railway n'ont pas cette variable positionnée

---

## Qualification doctrinale

Même logique que `ADR-annotation-backend-ops-fix-2026-04-20.md` (Doctrine G1) :

**Fix opérationnel pour rendre un chantier exécutable ≠ industrialisation ni évolution d'architecture.**

Le gel §8.4 handover V3 vise l'industrialisation du tuyau d'extraction (horizon P6–P7). Un fix opt-in de compatibilité proxy TLS dev n'est pas une évolution — c'est une accommodation d'environnement.

---

## Dette technique ouverte

À ouvrir post-merge PR E4-bis finale, rejoint la liste §10 handover V3 :

**[tech-debt][security] Distribute corporate CA in DMS dev environments and remove HTTPX_VERIFY_SSL bypass**

**Objectif** : à terme, le CA SCI sera distribué proprement dans tous les environnements dev, et le bypass sera retiré.

---

## Règle d'usage immédiat

1. `HTTPX_VERIFY_SSL=0` autorisé uniquement en dev/local
2. Toute revue de code PR doit vérifier que cette variable n'est jamais settée par défaut dans CI, Railway production, ou équivalent
3. Les 3 patterns (Label Studio, Mistral OCR, annotation-backend) doivent être consolidés en une seule variable `DMS_DEV_SSL_BYPASS` post-E4 (dette ouverte)

---

## Traçabilité

- **Ordre opérationnel** : CTO principal DMS (2026-04-21)
- **Commit d'application** : 2ef18d52
- **Mandat de légitimation** : DMS-QUALIFICATION-A-CLOTURE-E4BIS-V1
- **Pattern projet source** : `.env.local` (Label Studio + Mistral OCR)
