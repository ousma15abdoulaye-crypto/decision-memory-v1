---
**ARCHIVÉ — Preuve de défaillance · 2026-03-08**
---

# HANDOVER M7.4 PHASE A — CLASSIFICATION TAXONOMIE LLM

```
Date            : 2026-03-07
Sprint          : M7.4 Dict Vivant — Phase A (classification L1/L2/L3 par Mistral)
Branche         : feat/m7-4-dict-vivant
Agent           : Composer
Statut          : SUSPENDU — Défaillance critique (voir RAPPORT_DEFAILLANCE_M74_PHASE_A.md)
Référence       : docs/freeze/DMS_V4.1.0_FREEZE.md
```

---

## [!] RAPPORT DE DEFAILLANCE

**Voir :** `RAPPORT_DEFAILLANCE_M74_PHASE_A.md` (même dossier)

Travail bâclé — 77,9 % flagged — LLM invente des codes L3. Phase A à reprendre après corrections.

---

## 1. CONTEXTE

**Phase A** = classification automatique des items `procurement_dict_items` (domain_id IS NULL) dans la taxonomie L1/L2/L3 via LLM Mistral. Les propositions vont dans `couche_b.taxo_proposals_v2` — jamais de mise à jour directe de `dict_items` (RÈGLE-V1).

**Items cibles** : ~1484 items actifs, domain_id NULL, label_fr non vide, slug non numérique.

---

## 2. ÉTAT ACTUEL (2026-03-07)

### Full run — en cours ou interrompu

| Métrique        | Valeur   |
|-----------------|----------|
| Proposals total | 1070     |
| pending         | 236      |
| flagged         | 834      |
| flagged_pct     | 77.9%    |
| residuel (DIVERS_NON_CLASSE) | 833 |
| residuel_pct    | 77.9%    |

**Gates** :
- STOP-V3 : flagged_pct ≤ 35% — **DÉPASSÉ** (77.9%)
- STOP-V4 : residuel_pct ≤ 25% — **DÉPASSÉ** (77.9%)

**Cause** : Le LLM invente des codes L3 (ex. `cafe`, `lait`, `farine`, `bois`, `fer`, `bazin`) qui n'existent pas dans la taxonomie DB. La taxonomie L3 ne contient que 23 codes (riz, gasoil, ciment, ordinateurs, etc.). Les items non mappables → DIVERS_NON_CLASSE → flagged.

---

## 3. SCRIPT `classify_taxonomy_v2.py`

### Failles corrigées (version finale)

| Faille | Correction |
|--------|------------|
| F-JSON | Parser défensif `parse_llm_response()` — accepte objet `{"classifications": [...]}` ET liste directe |
| F-IDS | Prompt injecte IDs L1+L2+L3 exacts depuis DB (labels + mapping L1→L2) |
| F-CONN | Connexion DB ouverte/fermée par batch — zéro idle timeout Railway |
| F-LOGP | logprobs supprimé (non supporté Mistral) |
| F-KEY | DMSAPIMISTRAL \| DMS_MISTRAL \| MISTRAL_API_KEY |

### Usage

```powershell
$env:DATABASE_URL  = "postgresql://postgres:...@maglev.proxy.rlwy.net:35451/railway"
$env:DMSAPIMISTRAL = "<cle>"

python scripts/classify_taxonomy_v2.py --estimate
python scripts/classify_taxonomy_v2.py --dry-run --sample 10
python scripts/classify_taxonomy_v2.py --mode sync --sample 50
python scripts/classify_taxonomy_v2.py --mode sync
```

### Adaptations Windows

- Caractères Unicode (`→`, `⛔`) remplacés par ASCII (`->`, `[!]`) pour éviter `UnicodeEncodeError` sur cp1252.

---

## 4. VARIABLES D'ENVIRONNEMENT

| Variable       | Usage |
|---------------|-------|
| DATABASE_URL  | PostgreSQL — URL publique Railway pour exécution locale |
| DMSAPIMISTRAL | Clé API Mistral (ou DMS_MISTRAL, MISTRAL_API_KEY) |

**Attention** : `postgres.railway.internal` = hostname interne Railway, inaccessible depuis la machine locale. Utiliser `maglev.proxy.rlwy.net:35451` pour les runs locaux.

---

## 5. SÉQUENCE POST FULL RUN

1. **Vérifier rapport final** — `print(report.summary())` en fin de script
2. **Gates** : flagged_pct ≤ 35%, residuel_pct ≤ 25%
3. **Si gates OK** → Phase B `validate_taxo` (dry-run puis run réel)
4. **Si gates KO** → Enrichir taxonomie L3 (scripts/seed_taxonomy_v2.py) ou accepter taux flagged élevé pour revue manuelle

---

## 6. REQUÊTES SURVEILLANCE

```sql
-- Distribution par status
SELECT status, COUNT(*) AS n, ROUND(AVG(confidence)::NUMERIC, 3) AS avg_conf
FROM couche_b.taxo_proposals_v2 WHERE taxo_version = '2.0.0'
GROUP BY status ORDER BY n DESC;

-- Gates STOP-V3 / STOP-V4
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE status = 'flagged') AS flagged,
  ROUND(COUNT(*) FILTER (WHERE status = 'flagged') * 100.0 / COUNT(*), 1) AS flagged_pct,
  COUNT(*) FILTER (WHERE subfamily_id = 'DIVERS_NON_CLASSE') AS residuel,
  ROUND(COUNT(*) FILTER (WHERE subfamily_id = 'DIVERS_NON_CLASSE') * 100.0 / COUNT(*), 1) AS residuel_pct
FROM couche_b.taxo_proposals_v2 WHERE taxo_version = '2.0.0';
```

---

## 7. SCRIPTS UTILITAIRES

| Script | Usage |
|--------|-------|
| `scripts/classify_taxonomy_v2.py` | Phase A — classification LLM |
| `scripts/seed_taxonomy_v2.py` | Seed L1/L2/L3 (prérequis Phase A) |
| `scripts/_probe_phase_a.py` | Probe état taxo_proposals_v2 |

---

## 8. PIÈGES

| Piège | Cause | Fix |
|-------|-------|-----|
| Timeout 10 min | run_terminal_cmd timeout par défaut | Relancer ou augmenter timeout (15 min) |
| UnicodeEncodeError | Windows cp1252 | Caractères ASCII dans summary |
| subfamily_id invalide | LLM invente codes L3 | Taxonomie L3 limitée — enrichir ou accepter flagged |

---

## 9. PROCHAINES ÉTAPES

1. Laisser le full run terminer (ou relancer si interrompu)
2. Poster rapport final + outputs SQL (distribution, gates)
3. Décision Tech Lead : enrichir L3 vs accepter flagged
4. Phase B `validate_taxo` — dry-run → run réel
5. Phase C `fix_backfill`
6. Probe post-apply — seed=51, résiduel ≤ 25%
7. pytest global — 0 failed
8. Tag `v4.3.0-m7-dict-vivant`

---

*Agent : Composer · DMS V4.1.0 · M7.4 Phase A · 2026-03-07*
