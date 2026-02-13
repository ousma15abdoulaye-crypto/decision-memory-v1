📝 NOTE DE TRANSMISSION – DMS V3 (Constitution, Milestones, Discipline)
Projet : Decision Memory System (DMS)
Rôle : Assistant intelligent de procurement (ONG, États, Mines, Privé)
Référence produit : docs/CONSTITUTION_V3.md (incluant l’Addendum FROZEN+)

Cette note fixe le cadre de travail non négociable pour tout agent (IA ou humain) intervenant sur le projet.

1. Référence unique : Constitution V3 + Addendum
La seule source de vérité fonctionnelle et stratégique est la Constitution V3 (fichier docs/CONSTITUTION_V3.md).

L’Addendum FROZEN+ fait partie intégrante de cette Constitution (frontière A/B, machine d’état, doctrine d’échec, responsabilité humaine).

Toute proposition, PR, refactor ou évolution doit être compatible avec:

la séparation stricte Couche A / Couche B,

la machine d’état des processus,

le principe “le système aide à décider, mais ne décide jamais”.

Si une instruction ou une optimisation contredit la Constitution, la Constitution prime.

2. Milestones à suivre – Ordre figé (aucun saut)
L’agent doit respecter strictement l’ordre suivant, sans sauter ni réordonner les milestones:

M2‑EXTENDED – Références & catégories

État: DONE, mergé.

M4A‑FIX – Chaîne Alembic 002→003→004

État: DONE, mergé.

M‑REFACTOR – Découpage de main.py

Objectif: supprimer le monolithe, sortir les routes dans des modules src/api/*, src/couche_a/*, etc.

main.py ne doit contenir que: création app, wiring des routeurs, middlewares, config.

Aucune modification fonctionnelle, uniquement structure.

M‑TESTS – Remonter la qualité des tests

Objectif: tests fiables, CI sans masquage, couverture ≥ 40% sur modules critiques (upload_security, auth, Couche A core).

Suppression définitive de tout || true dans la CI.

M8 – Couche B MVP – Mémoire vivante minimaliste

Migration pg_trgm, resolvers fuzzy, endpoints Couche B, tests dédiés.

Respect absolu de la frontière: Couche B ne modifie jamais Couche A.

Ensuite seulement :

M3A – Extraction typée des critères,

M3B, M2B, M5, M6, M7, etc., selon la roadmap définie dans la Constitution V3.

Tout agent qui propose d’implémenter M8, M3A ou toute autre feature avant M‑REFACTOR et M‑TESTS est en dehors du cadre de ce projet.

3. Discipline CI / Tests – Niveau “haut standard”
Exigences non négociables:

CI verte réelle

Interdiction absolue de masquer les échecs (|| true dans .github/workflows/ci.yml).

Si pytest échoue, la CI doit être rouge et bloquer le merge.

Pipeline minimal attendu

alembic upgrade head doit passer.

pytest tests/ -v --tb=short doit passer.

python -m compileall src/ -q doit réussir.

Sécurité auth (M4A-F)

Endpoints /auth/token, /auth/register, /auth/me doivent être protégés par rate limiting via slowapi (@limiter.limit(...)).

Toute PR qui touche à l’auth doit préserver ou renforcer ces protections.

Qualité des tests

Toute nouvelle logique métier doit venir avec des tests.

Objectif: couverture progressive, mais ≥ 40% sur les modules sensibles.

Aucun “code magique” ou non testé dans les zones critiques (upload, auth, critères).

4. Frontière Couche A / Couche B – Ligne rouge
Couche A : ouvrier cognitif, moteur d’analyse, CBA/PV, décision processuelle.

Couche B : mémoire intelligente, historique, market intelligence, patterns, Q/R factuelles.

Règles de fer:

Couche B est read‑only vis-à-vis de Couche A:

pas de modification de scores,

pas de recalcul de notes,

pas de changement d’ordre des classements.

Aucun endpoint, module ou agent de Couche B ne peut modifier un état, un calcul, un export Couche A.

Les suggestions de la Couche B sont des faits, des comparaisons, des questions, jamais des prescriptions.

Toute dérive (reco fournisseur, “best choice”, scoring global fournisseur) est strictement interdite.

5. Doctrine d’échec & responsabilité humaine
Le DMS préfère échouer explicitement (refuser un CBA, marquer un document comme incomplet) plutôt que produire un résultat ambigu ou trompeur.

Les documents générés (CBA, PV, exports) sont des pré‑documents à valider par des humains habilités.

La décision finale reste 100% humaine (comités, managers, autorités).

Aucune feature ne doit déplacer la responsabilité sur le système.

6. Attentes de professionnalisme pour tout agent
Pour ce projet, le niveau attendu est celui d’un tech lead senior dans un environnement critique:

Respect strict de la séquence de milestones (pas de “sauts” opportunistes).

PR petites, ciblées, lisibles, avec descriptions claires et tests associés.

Pas de shortcuts en CI ou sécurité, même “temporairement”.

Conformité stricte à docs/CONSTITUTION_V3.md + Addendum, considérés comme contrat produit/tech.

Capacité à dire non à une évolution si elle viole les invariants (même si elle semble “intéressante”).

Règle ultime pour l’agent :
“Si un choix technique améliore localement quelque chose mais affaiblit la Constitution, la roadmap ou la discipline CI, il doit être refusé.”
