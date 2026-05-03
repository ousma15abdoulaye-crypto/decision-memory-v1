# P2-A-quater — Exécution Pass -1 GCF baseline OCR

**Mandat** : DMS-MANDAT-P2-A-QUATER-PASS1-GCF-BASELINE-V1  
**Autorité** : CTO principal DMS  
**Date** : 2026-04-24  
**Statut** : 🔄 EN COURS — Job ARQ enqueued, monitoring worker

---

## 1. Préparation ZIP GCF

**Archive créée** : `data/imports/annotation/gcf_baseline.zip`  
**Taille** : 13 616 914 bytes (13.6 MB)

**Contenu** :

| Document               | Chemin ZIP                          | Taille     |
| ---------------------- | ----------------------------------- | ---------- |
| ITT GCF                | `ITT/ITT Baseline GCF_vf_vf.pdf`    | 487 446    |
| AZ Offre Technique     | `AZ/Offre Technique.pdf`            | 10 978 848 |
| ATMOST Offre technique | `ATMOST/Offre technique.pdf`        | 2 150 214  |

**Méthode** : Python `zipfile` (structure dossiers fournisseurs)

---

## 2. Enqueue job ARQ

**Script** : `scripts/run_pass1_gcf_simple.py`

**Paramètres** :
- `workspace_id` : `f1a6edfb-ac50-4301-a1a9-7a80053c632a`
- `tenant_id` : `9ef5926e-81c5-4ee6-9f60-11c71d1cbcb5` (SCI Mali)
- `zip_path` : Local filesystem (pas R2)
- `zip_r2_key` : Vide

**Redis** : `junction.proxy.rlwy.net:52643` (proxy externe Railway)

**Résultat enqueue** :
- ✅ Job ARQ ID : `af4b3c8f62fc41ffab2e846808a34b3d`
- ⏱️ Durée enqueue : 0.95s
- Timestamp : 2026-04-24 (heure locale)

---

## 3. Monitoring worker ARQ

**Service Railway** : `arq-worker` (lié)

**Logs attendus** :
```
[PASS-1] ZIP local workspace=f1a6edfb-ac50-4301-a1a9-7a80053c632a path=...
[OCR-MISTRAL] ...
[PASS-1] Terminé workspace=... bundles=...
```

**Commande monitoring** : `railway logs --tail 50` (en cours)

---

## 4. Vérification persistance (à faire)

**Requête SQL Railway DB** :
```sql
SELECT id, filename, LENGTH(raw_text) as raw_text_size,
       ocr_engine, ocr_confidence, extracted_at
FROM bundle_documents
WHERE workspace_id = 'f1a6edfb-ac50-4301-a1a9-7a80053c632a'
ORDER BY uploaded_at DESC
LIMIT 10;
```

**Critères succès** :
- 3 documents avec `raw_text_size > 1000`
- `ocr_engine = "mistral_ocr_3"` ou `"none"` (PDF natif)
- `ocr_confidence ∈ {0.6, 0.8, 0.85, 1.0}`

---

## 5. Mesures OCR (à extraire logs)

**Métriques cibles** :
- Durée OCR par document (ITT, AZ, ATMOST)
- Confidence OCR
- Taille `raw_text` extrait
- Total bundles créés

**Extraction depuis logs worker** :
- Chercher timestamps `[PASS-1]` début/fin
- Parser durées OCR si loguées par `ocr_with_mistral()`

---

## 6. Résultat exécution

**❌ ÉCHEC job ARQ** : `af4b3c8f62fc41ffab2e846808a34b3d`

**Log worker** (ligne 3) :
```
[PASS-1] ZIP introuvable : pas de zip_r2_key en base pour workspace f1a6edfb-ac50-4301-a1a9-7a80053c632a.
```

**Cause** : Worker ARQ Railway cherche ZIP sur R2 Object Storage (via `zip_r2_key` DB), pas filesystem local. ZIP local inaccessible depuis worker (services isolés).

**Durée job** : 1.18s (échec immédiat, pas d'OCR exécuté)

---

## 7. Documents GCF existants workspace pilot

**Investigation P2-A** (2026-04-24 11:20 UTC) : Documents GCF déjà importés manuellement en base.

**3 documents identifiés** :

| Document ID                            | Table                    | Filename                   | État raw_text P2-A |
| -------------------------------------- | ------------------------ | -------------------------- | ------------------ |
| 04b3a295-00e3-49d4-ae3d-be046548045a | source_package_documents | ITT Baseline GCF_vf_vf.pdf | 0 bytes (vide)     |
| c1027c85-e29b-46cf-b102-a40230abb8b6 | bundle_documents         | Offre Technique.pdf (AZ)   | 0 bytes (vide)     |
| b3a8699a-9d4b-4a8a-a894-62dd44963d92 | bundle_documents         | Offre technique.pdf (ATMOST) | 0 bytes (vide)     |

**Constat P2-A-ter** : Import manuel SQL sans exécution Pass -1 → `raw_text` vide → mesures P2-A invalides.

**État actuel** (à vérifier) : Documents toujours en base, `raw_text` probablement toujours vide.

---

## 8. Conclusion P2-A-quater

**STATUT** : ❌ **ÉCHEC EXÉCUTION** — Pass -1 non déclenchable sans upload ZIP via API

**Blocages identifiés** :

1. **ZIP local inaccessible worker ARQ** : Services Railway isolés, filesystem non partagé
2. **Upload API requis** : Endpoint `POST /api/workspaces/{id}/upload-zip` nécessite JWT token authentification
3. **Documents existants sans OCR** : GCF déjà en base mais `raw_text = 0` (import manuel P2-A)

**Baseline OCR cold** : ❌ **NON ÉTABLIE**

**Recommandation CTO** :

Option A — **Upload ZIP via API authentifiée** :
- Obtenir JWT token (login API ou créer user test)
- Upload `gcf_baseline.zip` → R2
- Déclenchement automatique Pass -1 ARQ

Option B — **Re-import documents via Pass -1 complet** :
- Créer nouveau workspace ou réutiliser pilot
- Upload ZIP via interface DMS (si disponible)
- Monitoring worker ARQ jusqu'à completion

Option C — **Exécution Pass -1 directe local** (si autorisée CTO) :
- Invoquer graphe LangGraph local
- Connexion DB Railway pour persistance
- Contourne ARQ mais valide OCR Mistral

---

**Dernière mise à jour** : 2026-04-24 (échec job ARQ, documents existants identifiés)  
**Prochaine action** : Arbitrage CTO méthode déblocage baseline OCR
