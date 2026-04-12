# AO CTO — Ordre unique : merge PR → `main` = agent

**Émetteur** : CTO (Abdoulaye Ousmane)  
**Objet** : supprimer toute ambiguïté entre « l’agent ne merge jamais » et la pratique réelle des sessions Cursor.  
**Statut** : **opposable** pour les agents et l’outillage ; aligne **RÈGLE-ORG-10** dans `docs/freeze/DMS_V4.1.0_FREEZE.md`.

---

## Décision (une phrase)

**Le merge Git d’une pull request vers la branche `main` est exécuté par l’agent** (session qui porte le mandat et la PR), via `gh pr merge` ou équivalent, **dès que les garde-fous obligatoires sont satisfaits**.

Il **n’y a pas** de politique parallèle « merge réservé à l’humain » pour cet acte technique sur le dépôt.

---

## Garde-fous obligatoires (tous requis)

| # | Contrôle |
|---|----------|
| 1 | **CI** verte sur la PR (gates requis par l’équipe). |
| 2 | **Revue** : commentaires Copilot + threads de revue humains lus et traités (correctifs ou réponses). |
| 3 | **Alembic** : `alembic heads` = **exactement une** ligne (**STOP-1** sinon — ne pas merger). |
| 4 | **Railway / prod** : le merge Git **ne remplace pas** un **GO CTO** pour `alembic upgrade` ou mutations prod ; le documenter si une action prod reste à faire. |

---

## Ce qui ne change pas

- **DoD / feu vert métier** : là où le freeze ou le mandat exigent une validation humaine **avant** de considérer le livrable « vert », cela reste en vigueur (ex. RÈGLE-ORG-04 sur certaines étapes).
- **Tags de jalon** : pratique équipe (souvent posés par l’humain) — distinct du merge PR.
- **Autres règles** : périmètre mandat, pas de travail direct sur `main` pour le dev du mandat, schema/validator freeze, etc.

---

## Fichiers de vérité (ordre de lecture agent)

1. `CLAUDE.md` — § **DÉCISION CTO — PR : MERGE = AGENT**
2. `docs/ops/ADDENDUM_CTO_AGENT_MERGE_AUTHORITY.md`
3. `docs/freeze/DMS_V4.1.0_FREEZE.md` — **RÈGLE-ORG-10**
4. `.cursor/rules/dms-agent-mandate-protocol.mdc` — § 3.2

Les handovers historiques qui mentionnent encore l’ancienne formulation sont **non normatifs** pour le merge Git une fois cette PR fusionnée.
