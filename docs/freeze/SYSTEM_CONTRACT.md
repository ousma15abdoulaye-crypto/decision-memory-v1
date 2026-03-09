# SYSTEM_CONTRACT
# Couche zéro — en dessous de tout
# Avant le code. Avant les migrations. Avant les mandats.
# Statut   : FREEZE DÉFINITIF
# Date     : 2026-03-08
# Décideur : AO — Abdoulaye Ousmane
# Amendable : uniquement par SYSTEM_CONTRACT_V1.1_PATCH.md signé AO

---

## DÉFINITION

Le SYSTEM_CONTRACT définit les règles du processus d'exécution.
Pas des règles sur les données (→ invariants dans DMS_MRD_PLAN_V1.md).
Pas des règles sur le schéma (→ migrations Alembic).
Les règles sur QUI peut faire QUOI, QUAND, COMMENT.

Un agent peut respecter tous les invariants produit
et quand même dériver si les contrats sont violés.
Ces contrats rendent la dérive physiquement impossible.

---

## CONTRATS — LISTE FERMÉE

### CONTRACT-01 — Validation état avant toute session

  Règle :
    Toute session agent commence par :
    python scripts/validate_mrd_state.py
    Si exit(1) → zéro action avant GO CTO explicite

  Violation :
    Agent qui exécute une action sans avoir
    lancé validate_mrd_state.py en premier
    → toutes ses actions sont invalides
    → rollback demandé au CTO

  Vérification automatique :
    validate_mrd_state.py vérifie CONTRACT-01
    en lisant MRD_CURRENT_STATE.md

### CONTRACT-02 — Isolation DATABASE_URL

  Règle :
    DATABASE_URL ne contient jamais "railway"
    pendant une opération locale (migration, test, script)
    RAILWAY_DATABASE_URL = variable séparée, lecture seule

  Guard obligatoire dans tout script :
    db_url = os.environ.get('DATABASE_URL', '')
    if 'railway' in db_url.lower():
        raise SystemExit(
            'CONTRACT-02 VIOLE -- '
            'DATABASE_URL pointe Railway -- interdit'
        )

  Violation :
    Migration exécutée avec DATABASE_URL Railway
    → STOP immédiat
    → vérifier si données corrompues
    → poster au CTO avant toute suite

### CONTRACT-03 — Immutabilité docs/freeze/

  Règle :
    Un agent ne peut PAS modifier un fichier
    dans docs/freeze/ sauf si :
    a) le fichier est listé explicitement dans BLOC 3
       du mandat courant
    b) ET l'opération est listée dans BLOC 3
       (création | modification | suppression)

  Violation :
    Agent qui modifie docs/freeze/ hors BLOC 3
    → STOP immédiat
    → git diff docs/freeze/ posté au CTO
    → git checkout docs/freeze/ pour annuler

  Exception unique :
    MRD_CURRENT_STATE.md est modifié par AO uniquement
    jamais par un agent
    même si listé dans BLOC 3

### CONTRACT-04 — Séquence milestone non sautée

  Règle :
    Un milestone MRD-N ne peut pas démarrer
    si MRD_CURRENT_STATE.md indique
    next_milestone ≠ MRD-N

  Vérification obligatoire dans tout mandat :
    Lire MRD_CURRENT_STATE.md
    Si next_milestone ≠ milestone du mandat
    → STOP immédiat
    → poster au CTO
    → zéro action

  Violation :
    Agent qui démarre un milestone hors séquence
    → toutes ses actions sont invalides
    → rollback de la branche

### CONTRACT-05 — Tag git obligatoire avant milestone suivant

  Règle :
    Le tag mrd-N-done doit exister sur origin/main
    avant que MRD-N+1 puisse démarrer

  Vérification :
    git tag | grep mrd-$(N-1)-done
    Si absent → STOP

  Qui pose le tag :
    AO uniquement après merge validé
    Jamais un agent

### CONTRACT-06 — Commit atomique par milestone

  Règle :
    Chaque milestone produit exactement
    les fichiers listés dans son BLOC 9
    Ni plus. Ni moins.

  Vérification avant commit :
    git diff --staged --name-only
    Comparer avec BLOC 9 du mandat
    Si fichier hors liste → retirer du staging
    Si fichier manquant → ne pas commiter

  Violation :
    Commit avec fichier hors BLOC 9
    → git reset HEAD [fichier]
    → poster au CTO

### CONTRACT-07 — downgrade() obligatoire et testé

  Règle :
    Toute migration Alembic a un downgrade()
    qui restaure l'état précédent exactement
    Testé dans le cycle upgrade/downgrade local
    avant tout commit

  Vérification :
    Cycle : upgrade → tests → downgrade → upgrade → tests
    Si downgrade() échoue → migration interdite de merge

  Violation :
    Migration mergée sans downgrade() testé
    → documenter comme défaillance
    → corriger dans le milestone suivant
    → nommer DEF-MRD{N}-0N

### CONTRACT-08 — Lecture avant écriture

  Règle :
    Avant toute écriture (fichier, DB, git),
    l'agent lit l'état actuel de ce qu'il va modifier
    et le poste au CTO si CHECKPOINT

  Application :
    Avant ALTER TABLE → SELECT sur la contrainte actuelle
    Avant UPDATE fichier → cat du fichier actuel
    Avant git add → git diff du fichier

  Violation :
    Écriture sans lecture préalable
    → résultat potentiellement invalide
    → vérification CTO obligatoire

### CONTRACT-09 — Output brut non reformulé

  Règle :
    Tout output posté au CTO est l'output brut exact
    de la commande qui l'a produit
    Zéro reformulation. Zéro résumé. Zéro interprétation.
    Le CTO lit l'output brut et décide.

  Violation :
    Agent qui résume ou reformule un output STOP
    → CTO demande l'output brut
    → décision suspendue jusqu'à réception

### CONTRACT-10 — Un seul agent actif par milestone

  Règle :
    Un seul agent exécute un milestone à la fois
    Si une session est interrompue :
    → l'agent documente l'état exact
    → l'agent NE relance PAS depuis le début
    → l'agent poste l'état et attend le CTO
    → le CTO décide ROLLBACK ou REPRISE-N

  Violation :
    Deux agents sur le même milestone
    → résultats imprévisibles
    → STOP immédiat sur les deux
    → audit CTO avant toute suite

---

## HIÉRARCHIE DES RÈGLES

  SYSTEM_CONTRACT         ← présent document — couche zéro
  DMS_V4.1.0_FREEZE       ← loi produit
  ORCHESTRATION_FRAMEWORK ← loi d'exécution
  DMS_MRD_PLAN_V1         ← plan redressement
  MRD_CURRENT_STATE       ← état courant
  BASELINE                ← référence mathématique
  mandat du milestone     ← périmètre local

  Conflit entre couches → couche supérieure gagne
  Ambiguïté → STOP, poster au CTO

---

## ORDRE DE LECTURE OBLIGATOIRE

  Tout agent, toute session, lit dans cet ordre :

  0. docs/freeze/SYSTEM_CONTRACT.md                    ← EN PREMIER
  1. docs/freeze/DMS_V4.1.0_FREEZE.md
  2. docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md
  3. docs/freeze/DMS_MRD_PLAN_V1.md
  4. docs/freeze/MRD_CURRENT_STATE.md
  5. docs/freeze/BASELINE_MRD_PRE_REBUILD.md
  6. mandat du milestone en cours

  Puis exécuter :
  python scripts/validate_mrd_state.py

  Si exit(1) → STOP. Poster. Attendre GO CTO.

---

## CHECKSUMS

  SHA256 : [GÉNÉRÉ APRÈS COMMIT]
  Date   : [GÉNÉRÉE APRÈS COMMIT]

  sha256sum docs/freeze/SYSTEM_CONTRACT.md

  Amendement → SYSTEM_CONTRACT_V1.1_PATCH.md signé AO
  Ce fichier n'est plus modifié après hash.
