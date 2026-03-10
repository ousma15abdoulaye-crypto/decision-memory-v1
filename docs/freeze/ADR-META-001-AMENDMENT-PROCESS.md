# ADR-META-001-AMENDMENT-PROCESS
# Statut    : FREEZE DÉFINITIF
# Date      : 2026-03-10
# Décideur  : AO — Abdoulaye Ousmane
# Portée    : tous les documents gelés DMS sans exception
# Amendable : uniquement par ADR-META-002 signé AO

---

## 1. OBJET

Définir le processus unique autorisé pour modifier,
compléter, patcher ou remplacer un document gelé DMS.

Sans ce processus :
  Au 5e ajustement : quelqu'un patchera vite fait.
  Un autre lira l'ancien. Un autre le nouveau.
  Le brouillard revient. Les agents dérivent.
  Le génome se fragmente.

La gouvernance elle-même est gouvernée.

---

## 2. DOCUMENTS CONCERNÉS

  DMS_V4.1.0_FREEZE.md
  DMS_ORCHESTRATION_FRAMEWORK_V1.md
  DMS_ENTERPRISE_TARGET_ARCHITECTURE_V1.md
  DMS_MRD_PLAN_V1.md
  SYSTEM_CONTRACT.md
  FREEZE_HASHES.md
  BASELINE_MRD_PRE_REBUILD.md
  Tout document explicitement marqué FREEZE
  Tout document présent dans FREEZE_HASHES.md

  CONTEXT_ANCHOR.md — statut spécial :
    Document dérivé contrôlé — pas une loi produit.
    Versionné et traçable.
    Modifiable par l'agent dans BLOC 9 de chaque
    milestone sans processus ADR-META complet.
    Non soumis au délai de 5 jours.
    Reste traçable dans git — jamais modifié
    silencieusement hors mandat.

---

## 3. RÈGLE ABSOLUE

Un document gelé et hashé n'est jamais
modifié en place.

Interdictions absolues :
  Éditer le contenu d'un document hashé existant.
  Réécrire l'historique pour masquer un changement.
  Changer un fichier gelé sans nouvelle référence
  formelle.
  Mettre à jour le hash sans document d'amendement.
  Créer un document dont le nom implique une relation
  avec un document gelé hors processus :
    Formats interdits :
      *_UPDATED.md *_NEW.md *_REVISED.md *_FIXED.md
      *_V2_DRAFT.md *_TEMP.md

---

## 4. SEULS MODES DE CHANGEMENT AUTORISÉS

### 4.1 PATCH

  Quand :
    correction locale
    précision de formulation
    ajout limité
    pas de refonte structurelle

  Format : NOM_DU_DOCUMENT_V1.1_PATCH.md
  Exemple :
    DMS_ORCHESTRATION_FRAMEWORK_V1.1_PATCH.md

### 4.2 NOUVELLE VERSION

  Quand :
    changement structurel
    changement de doctrine
    nouveau périmètre
    remplacement partiel ou total

  Format : NOM_DU_DOCUMENT_V2.md
  Exemple :
    DMS_ORCHESTRATION_FRAMEWORK_V2.md

### 4.3 ADR D'AMENDEMENT

  Obligatoire pour tout patch ou nouvelle version.
  Format : ADR-META-XXX-<objet>.md
  Exemple :
    ADR-META-002-AMEND-FRAMEWORK-V1.md

---

## 5. CONTENU OBLIGATOIRE D'UN AMENDEMENT

  document_source    : nom et version exacte
  nature_changement  : PATCH | NOUVELLE_VERSION
  raison_factuelle   : pourquoi l'ancien gel
                       ne suffit plus
  probes             : preuves brutes — output exact
                       repo / DB / CI
  impact_autres_docs : liste documents gelés affectés
  decision_AO        : décision explicite AO
  nouveau_hash       : SHA256 du nouveau document
  lien_ancien_nouveau: relation entre ancien et nouveau

---

## 6. MOTIFS VALIDES D'AMENDEMENT

Un amendement n'est autorisé que si AU MOINS UN
cas est vrai :

  Contradiction prouvée avec l'état réel repo/DB.
  Faille de gouvernance détectée et prouvée.
  Faille de sécurité ou auditabilité détectée.
  Exigence réglementaire nouvelle.
  Besoin d'architecture non couvert par le gel.
  Ambiguïté prouvée créant une dérive agent.
  Coût de non-amendement supérieur au coût
  du changement.

Motifs invalides — refus automatique :
  Confort rédactionnel.
  Envie de reformuler.
  Préférence personnelle non prouvée.
  Ajout de littérature non exécutable.
  Inflation de gouvernance sans effet système.

---

## 7. PROCESSUS STANDARD D'AMENDEMENT

### ÉTAPE A — PROBE

  Poster les preuves brutes :
    repo, DB, CI, schéma, output brut.
  Zéro interprétation. Output brut uniquement.

### ÉTAPE B — DIAGNOSTIC

  Montrer précisément :
    ce que le document dit
    ce que la réalité montre
    où est la contradiction ou l'insuffisance

### ÉTAPE C — DÉCISION AO

  Délai : 5 jours ouvrés maximum.

  AO choisit :
    pas de changement
    patch
    nouvelle version

  Au-delà de 5 jours ouvrés sans décision :
    Amendement classé "en attente".
    Ancien document fait foi.
    L'ADR reste ouvert — non bloquant pour
    les milestones en cours.

### ÉTAPE D — PRODUCTION

  Créer l'ADR d'amendement.
  Créer le patch ou la nouvelle version.
  Calculer SHA256 du nouveau document.
  Ajouter dans FREEZE_HASHES.md.
  Mettre à jour CONTEXT_ANCHOR.md si hiérarchie
  change.

### ÉTAPE E — CLÔTURE

  Commiter les 3 fichiers ensemble :
    ADR d'amendement
    + nouveau document (patch ou V2)
    + FREEZE_HASHES.md mis à jour
  Noter dans MRD_CURRENT_STATE.md :
    quel document fait désormais foi
    date de l'amendement

---

## 7bis. EMERGENCY TRACK — FAST-TRACK 24H

Déclencheurs — un seul suffit :
  Faille de sécurité inter-tenant prouvée.
  Corruption du génome canonique détectée.
  Exigence réglementaire urgente documentée.

Processus :
  ÉTAPE A-URGENCE : probe immédiat — output brut
  ÉTAPE B-URGENCE : diagnostic en 2h maximum
  ÉTAPE C-URGENCE : décision AO sous 24h
  ÉTAPE D-URGENCE : production immédiate
  ÉTAPE E-URGENCE : post-mortem obligatoire
                    dans les 5 jours ouvrés suivants

  Le post-mortem documente :
    pourquoi l'emergency track a été déclenché
    si le processus standard pouvait suffire
    mesures préventives pour éviter la récurrence

Format identique au processus standard.
Seul le délai change.

---

## 8. RÈGLE DE PRÉCÉDENCE

  Document source : archive de vérité historique.
                    Jamais supprimé. Jamais écrasé.

  Patch / V2 : référence active si et seulement si
               présent dans FREEZE_HASHES.md.

  Signal de validation unique et binaire :
    Présent dans FREEZE_HASHES.md = validé AO = fait foi.
    Absent de FREEZE_HASHES.md = non applicable.
    Zéro interprétation.

  Ordre de priorité :
    1. Version la plus récente dans FREEZE_HASHES.md
    2. Sinon document source gelé
    3. Sinon STOP — poster au CTO

---

## 9. FREEZE_HASHES — RÈGLE D'INTÉGRITÉ

  À chaque amendement valide :
    SHA256 du nouveau document calculé.
    Ajout dans FREEZE_HASHES.md.
    Hash de l'ancien document jamais modifié.
    L'ancien hash reste — trace historique immuable.

  Format dans FREEZE_HASHES.md :
    NOM_DOCUMENT_V1.md              = [SHA256]
    NOM_DOCUMENT_V1.1_PATCH.md      = [SHA256]
    ADR-META-XXX-OBJET.md           = [SHA256]

  Suppression d'un hash = violation critique.
  Modification d'un hash existant = violation critique.

---

## 10. INTERDICTIONS ABSOLUES

  "Petit edit rapide" sur document hashé.
  Correction directe dans un document hashé.
  Changement non référencé dans un ADR.
  Suppression d'un document gelé pour "faire propre".
  Patch implicite dans un mandat.
  Usage d'un document officieux non hashé comme vérité.
  Création de NOM_UPDATED.md / NOM_NEW.md /
  NOM_FIXED.md hors processus ADR-META.
  Mise à jour FREEZE_HASHES.md sans ADR associé.

---

## 11. FORMAT MINIMUM ADR D'AMENDEMENT

```markdown
# ADR-META-XXX — [objet en une ligne]
## Statut      : DÉCIDÉ
## Date        : YYYY-MM-DD
## Décideur    : AO — Abdoulaye Ousmane
## Track       : STANDARD | EMERGENCY

### Document source
[nom exact + version]

### Problème prouvé
[preuves brutes — output exact — pas d'interprétation]

### Décision
[PATCH | NOUVELLE_VERSION + justification]

### Impact sur autres documents gelés
[liste ou "aucun impact prouvé"]

### Nouveau document de référence
[nom exact du patch ou V2]

### SHA256 mis à jour
[valeur dans FREEZE_HASHES.md]

### Post-mortem (si EMERGENCY)
[obligatoire dans les 5 jours]
```

---

## 12. PRINCIPE DIRECTEUR

  Un gel n'est jamais modifié en silence.
  Un changement de gel doit être traçable.
  La gouvernance elle-même est gouvernée.

  Pourquoi c'est critique :
    Sans méta-gouvernance, au 5e ajustement :
    quelqu'un patchera vite fait.
    Un agent lira l'ancien. Un autre le nouveau.
    Le brouillard revient.
    Le génome se fragmente.
    Les milestones divergent.
    Le projet perd sa mémoire.

---

## 13. CHECKSUMS

  SHA256 : [GÉNÉRÉ APRÈS COMMIT]
  Date   : [GÉNÉRÉE APRÈS COMMIT]

  sha256sum docs/freeze/ADR-META-001-AMENDMENT-PROCESS.md

  Amendement → ADR-META-002 signé AO
  Ce fichier n'est plus jamais modifié après hash.
