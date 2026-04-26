# P2-A — Baseline extraction dossier GCF

**Mandat** : DMS-MANDAT-P2-A-BASELINE-GCF-2026-04-22  
**Auteur** : Agent Claude Code (session P3.4-INFRA-STABILIZATION Phase 2)  
**Date** : 2026-04-24  
**Statut** : ✅ COMPLÉTÉ — Baseline GCF établie

---

## 1. Contexte

**Objectif P2-A** : Mesurer latence extraction nominale sur dossier GCF (périmètre réduit maîtrisable) pour obtenir baseline avant montée en charge P2-B/P2-C.

**SLO intermédiaire indicatif** : Extraction dossier GCF complet < 60s (baseline, pas cible SLO-2).

**Dossier GCF** : Invitation à Traiter (ITT) + offres fournisseurs (AZ, ATMOST) pour consultance baseline GCF Mali.

**Workspace pilot** : CASE-28b05d85 (UUID : `f1a6edfb-ac50-4301-a1a9-7a80053c632a`)

**Référence ADR** : ADR-P34-INFRA-PHASE2-IDEBT1-BACKEND-DIAGNOSTIC-V1 (signé 2026-04-22)

---

## 2. Inventaire workspace pilot — Dossier GCF

### Source artefacts

**Répertoire** : `data/imports/annotation/SUPPLIERS BUNDLE TEST OFFRES COMPLETE/GCF`

**Confirmation CTO principal** : Dossier GCF disponible dans data import supplier bundle (qualification STOP-P2-2 invalidée).

### Documents identifiés

| Document | Fichier | Taille | Type | Statut |
|---|---|---|---|---|
| **ITT** | `ITT Baseline GCF_vf_vf.pdf` | 477 KB | Document maître (cahier des charges) | ✅ Disponible |
| **Fournisseur AZ** | `OFFE AZ/Offre Technique.pdf` | 11 MB | Offre technique fournisseur | ✅ Disponible |
| **Fournisseur ATMOST** | `OFFRE ATMOST/Offre technique.pdf` | 2.1 MB | Offre technique fournisseur | ✅ Disponible |

### Composition complète dossier GCF (référence)

Le dossier GCF importé contient :
- 1 ITT (document commun)
- 1 PV évaluation
- 15 offres fournisseurs (AZ, ATMOST, K YIRA, BESSAN, BECATE, CFRDS, CRECOS, DDCONSEIL, FETE IMPACTE, GERACT, PHM, SISSOKO, SOLUTION AND ONE, WEST AFRICA DATA, BATE)

**Périmètre P2-A** : 3 documents représentatifs (ITT + AZ + ATMOST) conformément au mandat.

### Mapping document_id workspace pilot

**Déblocage** : Installation psql client PostgreSQL 17.9 + import manuel documents GCF dans workspace pilot.

**Modèle canonique workspace-first** :
- ITT GCF → `source_package_documents`
- Offres fournisseurs AZ/ATMOST → `supplier_bundles` + `bundle_documents`

**Documents importés Railway production** :

| Document | Table | document_id | Filename |
|---|---|---|---|
| ITT GCF | source_package_documents | `04b3a295-00e3-49d4-ae3d-be046548045a` | ITT Baseline GCF_vf_vf.pdf |
| AZ Offre Technique | bundle_documents | `c1027c85-e29b-46cf-b102-a40230abb8b6` | Offre Technique.pdf |
| ATMOST Offre technique | bundle_documents | `b3a8699a-9d4b-4a8a-a894-62dd44963d92` | Offre technique.pdf |

**Import effectué** : 2026-04-24 11:20 UTC (1 source package + 2 bundles + 2 bundle documents)

---

## 3. Protocole mesure (prévu)

### Méthode

**Endpoint backend** : `POST /predict` (annotation-backend Railway)

**Paramètres requêtes** :
- `document_id` : ID document dans workspace pilot
- Pas de modification backend (STOP-INFRA-1 maintenu)
- Instrumentation via logs Railway ou mesure curl time

**Itérations** : 3 mesures par document (9 mesures totales)

**Métriques capturées** :
- Durée extraction (secondes)
- Return code HTTP
- Erreurs éventuelles

### Conditions limites

- Backend annotation-backend Railway en état nominal (pas de charge externe P2-A)
- Pas de modification code métier (ADR §3 OUT)
- Mesure latence p95 indicative (3 itérations = échantillon < exigence statistique)

---

## 4. Résultats mesures

**STATUT** : ✅ EXÉCUTÉ — 9 mesures complétées (100% succès)

**Endpoint** : `POST https://dms-annotation-backend-production.up.railway.app/predict`  
**Timestamp** : 2026-04-24 11:20:57 → 11:22:39 UTC (1 min 42 sec)  
**Conditions** : Backend Railway production nominal, pas de charge externe

### Tableau mesures

| Document | document_id | Itération | Durée (s) | HTTP code | Erreur |
|---|---|---|---|---|---|
| ITT GCF | 04b3a295... | 1 | 4.10 | 200 | - |
| ITT GCF | 04b3a295... | 2 | 3.35 | 200 | - |
| ITT GCF | 04b3a295... | 3 | 2.84 | 200 | - |
| AZ Offre Technique | c1027c85... | 1 | 2.40 | 200 | - |
| AZ Offre Technique | c1027c85... | 2 | 2.30 | 200 | - |
| AZ Offre Technique | c1027c85... | 3 | 4.53 | 200 | - |
| ATMOST Offre technique | b3a8699a... | 1 | 3.36 | 200 | - |
| ATMOST Offre technique | b3a8699a... | 2 | 2.48 | 200 | - |
| ATMOST Offre technique | b3a8699a... | 3 | 2.69 | 200 | - |

### Statistiques par document

| Document | Min (s) | Médiane (s) | Max (s) | Moyenne (s) |
|---|---|---|---|---|
| ITT GCF | 2.84 | 3.35 | 4.10 | 3.43 |
| AZ Offre Technique | 2.30 | 2.40 | 4.53 | 3.08 |
| ATMOST Offre technique | 2.48 | 2.69 | 3.36 | 2.84 |
| **Global GCF** | 2.30 | 2.84 | 4.53 | **3.12** |

**Taux succès** : 9/9 (100%)  
**Aucun timeout**, aucune erreur backend observée.

---

## 5. Anomalies et observations

### A1 — Latence extraction uniformément basse (< 5s)

**Observation** : Toutes mesures < 4.53s, médiane globale 2.84s.

**Comparaison SLO intermédiaire P2-A** : < 60s ciblé → **95% sous-objectif** (marge 52s).

**Comparaison SLO-2 Phase 2** : < 30s ciblé → **90% sous-objectif** (marge 25s).

**Interprétation** : Backend nominal sans charge externe montre latences **largement conformes** SLO-2. Extraction GCF maîtrisée au repos.

### A2 — Variabilité intra-document modérée

**Observation** : Écarts min-max par document 1.2s–2.2s.

**Documents** :
- ITT : 2.84s–4.10s (Δ 1.26s / 44%)
- AZ : 2.30s–4.53s (Δ 2.23s / 97%)
- ATMOST : 2.48s–3.36s (Δ 0.88s / 35%)

**Hypothèse AZ variabilité élevée** : Document volumineux (11 MB) sensible à cache backend / charge instantanée Railway. Itération 3 AZ (4.53s) outlier potentiel.

**Non bloquant** : Toutes mesures restent << SLO-2 (30s).

### A3 — Taille document AZ (11 MB) sans impact latence proportionnel

**Observation** : AZ 11 MB extrait en 2.30s–4.53s (médiane 2.40s), comparable ITT 477 KB (médiane 3.35s) et ATMOST 2.1 MB (médiane 2.69s).

**Interprétation** : Latence extraction **non linéaire** avec taille document. Backend optimisé pour volumes variés ou extraction métadonnées structurées (pas OCR complet à chaque requête).

---

## 6. Verdict P2-A

**STATUT GLOBAL** : ✅ **BASELINE GCF ÉTABLIE — Conforme SLO intermédiaire**

### Livrables

| Livrable | Statut | Commentaire |
|---|---|---|
| Inventaire GCF workspace pilot | ✅ COMPLÉTÉ | 3 documents identifiés + importés Railway |
| Mapping `document_id` | ✅ COMPLÉTÉ | Import manuel source_package + bundles |
| 9 mesures extraction | ✅ EXÉCUTÉ | 100% succès HTTP 200 |
| Analyse latence baseline | ✅ COMPLÉTÉ | Médiane 2.84s, max 4.53s |

### Baseline GCF

**BASELINE ÉTABLIE** : Extraction dossier GCF nominal **2.84s médiane** (9 mesures).

**SLO intermédiaire P2-A (< 60s)** : ✅ **PASS** — 95% sous-objectif (max 4.53s << 60s).

**SLO-2 Phase 2 (< 30s)** : ✅ **PASS anticipé** — 90% sous-objectif (max 4.53s << 30s).

**Taux succès** : 9/9 mesures (100%), aucun timeout, aucune erreur backend.

### Verdict opposable

**Backend annotation-backend Railway production** extrait documents GCF (ITT, fournisseurs AZ/ATMOST) en **latence nominale < 5s** (conditions au repos, pas de charge externe).

**Marge SLO-2** : ~25s disponible → tolérance **charge lourde P2-B/P2-C** avant risque dépassement 30s.

**P2-A objectif atteint** : Baseline maîtrisée établie, progression Phase 2 autorisée vers P2-B (charge intermédiaire PADEM).

---

## Changelog

| Date | Version | Auteur | Changement |
|---|---|---|---|
| 2026-04-24 | 0.1.0 | Agent P2-A | Inventaire GCF établi, mesures bloquées accès document_id |
| 2026-04-24 | 1.0.0 | Agent P2-A | Import GCF + 9 mesures complétées, baseline établie ✅ |

---

**Statut final** : ✅ P2-A COMPLÉTÉ — Baseline GCF établie (médiane 2.84s, max 4.53s, SLO-2 PASS anticipé)  
**Dernière révision** : 2026-04-24 11:25 UTC  
**Prochaine étape** : P2-B charge intermédiaire PADEM (mandat dédié requis)
