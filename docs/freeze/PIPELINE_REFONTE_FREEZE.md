# PIPELINE REFONTE — FREEZE DÉFINITIF
Date : 2026-03-18
Statut : FREEZE — supérieur à tout mandat pipeline antérieur

## DÉCISION CTO
M12 bloqué sur 0/15 annotated_validated.
Cause racine : 3 bugs backend.py + prompt monolithique.
Solution : corrections chirurgicales séquentielles — pas de réécriture.

## BUGS CONFIRMÉS — SÉQUENCE DE CORRECTION

### BUG-1 — to_name désaligné (E-66) — BLOQUANT CRITIQUE
Symptôme : textarea Label Studio vide sur chaque document
Cause    : backend.py envoie to_name="text"
           XML déclare <Text name="document_text" value="$text"/>
           Label Studio cherche to_name="document_text" — ne trouve pas
Fix      : remplacer to_name="text" par to_name="document_text"
           dans _build_ls_result() ET _build_empty_result()
Fichier  : services/annotation-backend/backend.py

### BUG-2 — document_role non passé à _build_messages() (E-67 pattern)
Symptôme : Mistral reçoit prompt générique sans contexte type document
           → hallucination sur champs interdits selon LOI 1bis
Cause    : /predict extrait document_role depuis task["data"]
           mais ne le passe pas à _build_messages(user_content, document_role="")
Fix      : extraire document_role = task_data.get("document_role", "")
           passer à _build_messages(user_content, document_role=document_role)
Fichier  : services/annotation-backend/backend.py

### BUG-3 — _normalize_gates() incomplet sur AMBIG-5
Symptôme : gate_value=null sur gate_state=APPLICABLE passe sans correction
           → Pydantic rejette en aval → document perdu
Cause    : cas null+APPLICABLE non couvert ou couvert partiellement
Fix      : dans _normalize_gates() — vérifier et ajouter si absent :
           if gate.get("gate_state") == "APPLICABLE"
              and gate.get("gate_value") is None:
               gate["gate_value"] = False
               ambiguites.append(
                 f"AMBIG-5_gate_{gate.get('gate_name')}_value_null_forced_false"
               )
Fichier  : services/annotation-backend/backend.py

## FLUX CANONIQUE CIBLE
ingestion → router → extracteur spécialisé → validator → Label Studio

## STATUTS PIPELINE
annotated_validated | review_required | rejected

## CONFIDENCE
{0.6, 0.8, 1.0} — aucune autre valeur autorisée

## FREEZE ACTIFS
schema-freeze-v1.0    : DMSExtractionResult — intouchable
validator-freeze-v1.0 : schema_validator.py — intouchable

## DÉPRÉCIATIONS FORMELLES
system_prompt.txt monolithique 587 lignes : DEPRECATED — remplacé par prompts spécialisés par type
json_object mode Mistral                  : DEPRECATED — remplacé par json_schema mode
to_name="text" dans backend.py            : DEPRECATED — remplacé par "document_text"

## SEUIL DE SORTIE M12
15 annotated_validated — travail humain AO uniquement (RÈGLE-25)
Les 3 fixes backend.py débloquent la capacité d'annoter.
L'annotation reste non délégable.

## MANDATS SÉQUENCE
GOV-01  : gouvernance — 4 fichiers docs — zéro Python
FIX-01  : BUG-1 to_name — backend.py chirurgical
FIX-02  : BUG-2 document_role — backend.py chirurgical
FIX-03  : BUG-3 normalize_gates — backend.py chirurgical
