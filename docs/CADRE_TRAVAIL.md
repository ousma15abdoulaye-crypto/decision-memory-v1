Titre : NOTE DE TRANSMISSION — DMS V3.3.2 (Constitution, Milestones, Discipline)
Projet : Decision Memory System (DMS)
Périmètre : Backend + DB + CI/CD + Docs + UX (selon milestones)
Rôle du système : Assistant intelligent de procurement (ONG, États, Mines, Privé)
Autorité : Abdoulaye Ousmane — Founder & CTO
Statut : CANONIQUE · OPPOSABLE · FREEZABLE
Date : 2026-02-16
Hash (à renseigner au freeze) : SHA256 dans docs/freeze/FREEZE_MANIFEST.md

0) Objet et force obligatoire

Cette note définit le cadre de travail non négociable applicable à tout agent (IA ou humain) qui :

propose une évolution,

écrit du code,

modifie une CI,

modifie la base,

modifie un document de référence,

ou prépare une PR.

Règle système : si un comportement n’est pas conforme à ce cadre, il est refusé, même s’il “améliore” localement le produit.

1) Sources de vérité (références uniques, opposables)
1.1 Documents canoniques obligatoires (ordre de lecture)

docs/CONSTITUTION_DMS_V3.3.2.md

inclut l’Addendum FROZEN+ (frontière A/B, machine d’état, doctrine d’échec, responsabilité humaine)

docs/MILESTONES_EXECUTION_PLAN_V3.3.2.md

docs/INVARIANTS.md

docs/adrs/ADR-0001.md

1.2 Règle de primauté

Si une instruction, une PR, un refactor, une optimisation ou un “quick win” contredit :

la séparation Couche A / Couche B,

la machine d’état,

ou “le système aide à décider mais ne décide jamais”,
alors la proposition est invalide.

1.3 Règle de gel (freeze)

Après freeze, ces documents deviennent immutables (édition uniquement via amendement versionné + ADR + validation CTO).

2) Séquence de milestones (ordre figé, aucun saut)
2.1 Principe général (binaire)

Un milestone est DONE ou ABSENT.

Un milestone suivant ne démarre pas tant que le précédent n’est pas DONE.

Aucun “démarrage en parallèle” sans ADR + validation CTO explicite.

2.2 Milestones internes (pré-registry) — ordre imposé

Ces milestones sont des pré-requis d’hygiène (repo/structure/CI) avant d’attaquer le registry complet V3.3.2.

M2-EXTENDED — Références & catégories

État : DONE, mergé.

Règle : considéré verrouillé ; tout changement = PR dédiée + justification + tests.

M4A-FIX — Chaîne Alembic 002→003→004

État : DONE, mergé.

Règle : aucune migration ne doit casser alembic upgrade head.

M-REFACTOR — Découpage de main.py (structure uniquement)

Objectif : supprimer le monolithe, organiser en modules :

src/api/ (routes + dépendances)

src/couche_a/ (logique Couche A)

src/couche_b/ (logique Couche B)

src/security/ (auth/rbac/rate limit)

src/db/ (connexions, migrations, helpers SQL)

Contrainte : main.py ne contient que :

création app,

wiring routeurs,

middlewares,

config.

Interdit : tout changement fonctionnel. Refactor = structure only.

M-TESTS — Remonter la qualité des tests

Objectif : tests fiables, CI sans masquage, couverture ≥ 40% sur modules critiques :

upload_security, auth, couche_a core

Interdit : || true dans la CI (suppression définitive).

Interdit : tests “flaky” non isolés ; si instable → corriger ou supprimer.

M8 — Couche B MVP (mémoire minimaliste)

Contenu minimal :

extension pg_trgm (si fuzzy matching DB),

resolvers fuzzy,

endpoints Couche B,

tests dédiés.

Ligne rouge : Couche B ne modifie jamais Couche A.

Ensuite seulement : milestones du registry V3.3.2

M3A (Extraction typée critères),

M3B, M2B, M5, M6, M7, etc.

Selon l’ordre défini dans docs/MILESTONES_EXECUTION_PLAN_V3.3.2.md.

2.3 Règle d’exclusion

Tout agent qui propose d’implémenter M8, M3A, ou toute feature avant M-REFACTOR et M-TESTS est hors cadre.

3) Discipline CI / Tests — niveau “haut standard” (non négociable)
3.1 Interdictions absolues

Interdit : masquer un échec CI (ex : || true, continue-on-error non justifié).

Interdit : merger avec CI rouge.

Interdit : introduire une dépendance non déclarée / non documentée.

Interdit : secrets en dur (tokens, passwords, URLs sensibles).

3.2 Pipeline CI minimal obligatoire (commandes exactes)

La CI doit exécuter et valider au minimum :

Migrations

alembic upgrade head doit passer (sur DB propre).

Tests

pytest tests/ -v --tb=short doit passer.

Compilation

python -m compileall src/ -q doit réussir.

Quality gate

Couverture : seuil progressif mais ≥ 40% sur modules sensibles (voir §2.2.4).

Toute nouvelle logique métier critique = tests obligatoires.

3.3 Sécurité Auth — protection minimale opposable

Tout endpoint d’auth doit rester protégé :

/auth/token

/auth/register

/auth/me

Exigence : rate limiting via slowapi (@limiter.limit(...)) + tests prouvant l’enforcement.

Règle : toute PR touchant auth doit préserver ou renforcer ces protections.

3.4 Qualité des tests (règles système)

Toute nouvelle logique métier = tests unitaires minimum.

Pas de “code magique” dans : upload, auth, critères, scoring, comité.

Pas de tests qui passent “par hasard” : fixtures explicites, données contrôlées.

4) Frontière Couche A / Couche B — ligne rouge (opposable)
4.1 Définition

Couche A : ouvrier cognitif, moteur d’analyse, pipeline documents→extraction→normalisation→scoring→exports (CBA/PV).

Couche B : mémoire intelligente, historique, market intelligence, patterns, Q/R factuelles.

4.2 Règles de fer (interdictions absolues)

Couche B est read-only vis-à-vis de Couche A :

Interdit à Couche B :

modifier des scores,

recalculer des notes,

changer un classement,

injecter un coefficient marché dans le scoring,

modifier un état d’un process Couche A,

modifier un export Couche A,

écrire dans des tables Couche A liées au process en cours (hors traces append-only strictement autorisées par Constitution).

4.3 Non-prescriptif (forme et contenu)

Les sorties Couche B sont :

faits,

comparaisons,

tendances,

questions,

anomalies factuelles.

Interdit :

recommandation fournisseur (“best choice”),

scoring global fournisseur,

“classement conseillé”,

toute formulation qui transfère la responsabilité au système.

5) Doctrine d’échec & responsabilité humaine (opposable)
5.1 Doctrine d’échec explicite

Le DMS préfère :

échouer explicitement (refuser un CBA, marquer incomplet),
plutôt que :

produire un résultat ambigu ou trompeur.

5.2 Responsabilité humaine

CBA/PV/exports sont des pré-documents à valider par des humains habilités.

La décision finale reste 100% humaine (comités, managers, autorités).

Aucune feature ne doit déplacer la responsabilité vers le système.

6) Attentes de professionnalisme (standard tech lead senior)
6.1 Règles d’exécution

Respect strict de la séquence milestones (pas de “sauts opportunistes”).

PR petites, ciblées, lisibles, avec description claire et tests associés.

Aucun shortcut en CI ou sécurité, même “temporairement”.

6.2 Règles de dépôt / environnement

Le code source officiel vit dans Git (repo).

Aucun changement “hors repo” n’est considéré comme existant.

Toute modification doit être intégrée via PR, puis déployée via pipeline prévu (Railway selon DevOps).

6.3 Règle ultime (non négociable)

“Si un choix technique améliore localement quelque chose mais affaiblit la Constitution, la roadmap, la frontière A/B, ou la discipline CI, il doit être refusé.”

7) Clause d’application (enforcement)

Toute PR non conforme à cette note doit être refusée.

Toute exception nécessite :

ADR,

justification,

validation explicite CTO,

tests prouvant l’absence de dérive.
