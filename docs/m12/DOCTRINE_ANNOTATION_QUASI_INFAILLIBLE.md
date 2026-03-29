# Doctrine d’annotation M12 / DMS — logique à suivre (agents & annotateurs)

**Objectif.** Réduire au minimum les exports **inexploitables** (`export_ok=false`, `json_parse_error`, `schema_validation`) et les écarts entre **Label Studio** et le **schéma DMS** gelé, sans dépendre uniquement de correctifs pipeline.

**Autorité.** Le contrat normatif reste **`docs/freeze/CONTEXT_ANCHOR.md`** (E-01 à E-67) et le schéma **`DMSAnnotation`** (`services/annotation-backend/prompts/schema_validator.py` — gel sans mandat CTO). Cette doctrine est une **couche opérationnelle** ; en cas de conflit, le gel prime.

---

## 1. Règle d’or — le champ `extracted_json` est du JSON pur

1. Le textarea **`extracted_json`** doit contenir **un seul objet JSON** valide : premier caractère utile **`{`**, dernier **`}`** (après trim).
2. **Interdit** d’y coller tel quel la sortie « chat » avec :
   - préfixe **` ```json `** ou **` ``` `** ;
   - texte avant/après le JSON (« Voici le JSON : », etc.).
3. **Pourquoi.** `json.loads` échoue au premier caractère si le flux commence par `` ` `` — cela produit **`json_parse_error`** et **aucun** `dms_annotation`, même si le cœur du JSON est bon.
4. **Si déjà collé avec fences.** Le pipeline d’export peut les retirer (voir `m12_export_line.py`) ; **ne pas s’y fier** pour la qualité : la doctrine exige du JSON pur dans LS pour traçabilité et revue humaine.

---

## 2. Confiance — uniquement `{0.6, 0.8, 1.0}`

1. Toute clé **`confidence`** dans un bloc type FieldValue `{ value, confidence, evidence }` doit être **0.6**, **0.8** ou **1.0**.
2. **Interdit** : `0.9`, `0.95`, `0.0` sur champs APPLICABLE (sauf conventions explicites NOT_APPLICABLE côté schéma).
3. **Pourquoi.** Sinon **`schema_validation`** au moment de `DMSAnnotation.model_validate`.

---

## 3. Sentinelles — ne pas utiliser `null` à la place d’une chaîne obligatoire

1. Les champs modélisés en **`str`** dans **`identifiants`** et **`_meta`** ne doivent **pas** être **`null`** si tu veux un JSON **déjà valide** dans LS.
2. Utiliser **`NOT_APPLICABLE`** ou **`ABSENT`** selon le sens métier (document hors périmètre fournisseur / information absente du texte), **comme chaînes**.
3. Cas fréquents à corriger **dans le JSON** avant validation :
   - `identifiants.case_id`, `identifiants.supplier_id` → **`"NOT_APPLICABLE"`** (ou valeur texte réelle si présente).
   - `_meta.parent_document_id`, `_meta.parent_document_role` → **`"NOT_APPLICABLE"`** si non concerné.
4. **Note.** L’export peut encore **coercer** `null` → `NOT_APPLICABLE` sur certains chemins ; la doctrine demande de **ne pas compter là-dessus** pour la qualité en base LS.

---

## 4. Gates (`couche_5_gates`) — enum stricte

1. **`gate_state`** : **seulement** **`"APPLICABLE"`** ou **`"NOT_APPLICABLE"`**.
2. **Interdit** pour ce champ : **`"ABSENT"`**, **`"AMBIGUOUS"`** (le schéma Gate ne les accepte pas — utiliser **`NOT_APPLICABLE`** si le gate ne s’applique pas au document).
3. Si **`gate_state` = `NOT_APPLICABLE`** → **`gate_value`** doit être **`null`** ; **`confidence`** = **`1.0`** (Loi DMS NOT_APPLICABLE).
4. Si **`gate_state` = `APPLICABLE`** → **`gate_value`** doit être **`true`** ou **`false`** (pas `null`, pas chaîne libre non booléenne).
5. **Nombre et ordre des gates.** Respecter le schéma (10 gates attendus dans le modèle racine) — ne pas tronquer la liste.

---

## 5. Identifiants — ADR-013 (`supplier_phone_raw` / `supplier_email_raw`)

1. Si **`supplier_phone`** et/ou **`supplier_email`** (blocs pseudonymisés) sont présents, le schéma exige aussi **`supplier_phone_raw`** et **`supplier_email_raw`**.
2. En pratique pour un doc **sans** contact fournisseur : mettre **`""`** (chaîne vide) pour les `*_raw` lorsque les blocs `present: false` sont là, ou suivre le squelette fourni par le backend.
3. **Pourquoi.** Sans ces clés → **`Field required`** à la validation, donc export **cassé** si la normalisation export n’est pas alignée ou absente.

---

## 6. FieldValue — structure minimale

Pour tout champ « extrait » au format objet :

- **`value`** : type attendu par le schéma (scalaire, liste, sentinelle).
- **`confidence`** : voir §2.
- **`evidence`** : chaîne ; **`"ABSENT"`** ou justification courte ; **éviter chaîne vide** si `value` n’est pas une sentinelle d’absence (sinon risque QA / schéma selon champ).

---

## 7. Evidence et texte source (bonne pratique, sans bloquer `export_ok`)

1. L’export M12 calcule encore **`evidence_violations`** (présumée absence de la preuve dans le texte source / OCR) mais **ne met plus `export_ok=false`** pour cela — évite les faux négatifs liés à l’OCR et aux formulations.
2. **Doctrine qualité.** Continuer à citer des **extraits réels** du document dans **`evidence`** quand c’est possible : traçabilité humaine et audits ultérieurs.
3. **Audit optionnel.** Pour exiger ce contrôle sur un fichier JSONL, utiliser **`scripts/validate_annotation.py`** avec **`--require-evidence-substring`** (hors chemin d’export par défaut).

---

## 8. Cohérence routing / rôle document

1. **`couche_1_routing.document_role`** et **`taxonomy_core`** doivent être **cohérents** avec le type de pièce (offre, DAO, politique interne, etc.).
2. Un document **policy / supporting_doc** : champs « procédure / lots / prix » en **`NOT_APPLICABLE`** avec preuves explicites — **évite** les incohérences financières et les faux positifs QA.

---

## 9. Statut dans LS vs statut dans `_meta`

1. Le choix **`annotation_status`** dans Label Studio (ex. **`annotated_validated`**) est **indépendant** de **`_meta.annotation_status`** dans le JSON.
2. **Doctrine.** Lorsque tu valides dans LS, le JSON peut encore contenir `"annotation_status": "pending"` dans `_meta` : ce n’est pas bloquant pour le schéma si les autres champs sont valides ; l’outil de synchro / export peut aligner plus tard. **Ne pas** se contredire sciemment entre LS et JSON sans raison documentée.

---

## 10. Checklist immédiate avant « Soumettre / Valider » dans LS

- [ ] `extracted_json` : JSON pur, **`{` … `}`**, pas de **` ```json `**.
- [ ] Aucune **`confidence`** hors **0.6 / 0.8 / 1.0**.
- [ ] Pas de **`null`** sur les **`str`** obligatoires listés en §3 (utiliser **`NOT_APPLICABLE`** / **`ABSENT`**).
- [ ] Tous les **`gate_state`** ∈ **`APPLICABLE` | `NOT_APPLICABLE`** ; **`gate_value`** cohérent (§4).
- [ ] **`supplier_phone_raw` / `supplier_email_raw`** présents si blocs phone/email (§5).
- [ ] **10 gates** présents, noms conformes au schéma.
- [ ] **Evidences** : ancrées dans le texte source quand la QA stricte est requise (§7).

---

## 11. Ce que les agents **ne** doivent **pas** faire

1. **Ne pas** proposer de modifier **`schema_validator.py`** ou le gel **`DMS_V4.1.0_FREEZE.md`** sans **mandat CTO** explicite.
2. **Ne pas** suggérer **`to_name": "text"`** dans la config LS — la valeur canonique est **`document_text`** (E-66).
3. **Ne pas** introduire de **`confidence`** hors **{0.6, 0.8, 1.0}**.
4. **Ne pas** stocker de **secrets** (tokens, mots de passe) dans le JSON d’annotation ou dans des fichiers versionnés — utiliser **`.env.local`** (gitignoré).

---

## 12. Références rapides

| Sujet | Référence |
|--------|-----------|
| Export JSONL, flags `--no-enforce-validated-qa` | [`M12_EXPORT.md`](./M12_EXPORT.md) |
| Ligne d’export partagée webhook / script | `services/annotation-backend/m12_export_line.py` |
| Schéma Pydantic | `services/annotation-backend/prompts/schema_validator.py` |
| Variables LS / TLS | `.env.example`, `services/annotation-backend/ENVIRONMENT.md` |

---

**Version.** Rédigé pour être transmis tel quel aux agents (Cursor, humains, orchestrateurs). Dernière mise à jour : alignée sur les incidents réels corpus 12 lignes (fences Markdown, gates, nulls, confidences, QA evidence, ADR-013).
