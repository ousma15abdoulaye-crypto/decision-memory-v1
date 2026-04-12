# Addendum CTO — autorité merge agents Cursor (conditions)

**Date** : 2026-04-12 (complément **responsabilité créateur PR** ; version 2026-04-11 conservée ci-dessous)  
**Émetteur** : CTO (Abdoulaye Ousmane)  
**Statut** : opposable pour les sessions agent ; complète `CLAUDE.md` et `.cursor/rules/dms-agent-mandate-protocol.mdc`.

## Objet

Les **agents Cursor** (et équivalents) **mergent** les PR vers `main` lorsque le mandat l’exige, **sous les conditions strictes** ci-dessous. **RÈGLE-ORG-10** du Plan Directeur gelé et ce dépôt sont **alignés** sur cette politique (**merge = agent**).

## Responsabilité du créateur de la PR (ordre CTO — 2026-04-12)

L’**agent / session qui a créé ou ouvert la PR** pour un mandat **doit en assumer la suite jusqu’au merge** : surveillance **CI jusqu’au vert**, **récupération et correction** des retours **GitHub Copilot** et des **revues** (threads), vérification **Alembic** (`alembic heads` = une ligne), puis **merge** (`gh pr merge` ou équivalent). **Pas de abandon** après un seul push sans itération. Un transfert à un autre agent ou au CTO **sans action explicite** ne dispense pas le créateur tant que le CTO n’a pas repris le fil.

## Conditions obligatoires avant merge (toutes requises)

1. **PR ouverte** sur la branche du mandat ; description : objectif, preuves, risques ; mention **Anchor** si addendum `CONTEXT_ANCHOR` requis ou explicite « lecture seule ».
2. **CI GitHub Actions vert** sur la PR (ou équivalent requis par l’équipe) — surveillance jusqu’à succès, pas d’abandon après un seul push.
3. **Revue Copilot / humains** : **récupérer** les commentaires (UI PR, `gh pr view`, API GitHub si besoin) ; lire les threads, **corriger** les retours pertinents, re-pousser ; itérer jusqu’à **CI vert** et traitement raisonnable des blocages.
4. **Alembic** : `alembic heads` = **exactement une ligne** (**STOP-1** `CLAUDE.md` si plusieurs heads — **ne pas merger**). Aucune réécriture de fichiers déjà fusionnés sous `alembic/versions/` ; nouvelles révisions = mandat Alembic + fichier séquentiel.
5. **Railway / production** : le merge Git **ne dispense pas** runbook + **GO CTO** pour `alembic upgrade` ou mutations prod ; documenter dans la PR si une action prod reste à faire.

## Fichiers de référence versionnés

- `docs/ops/CTO_AO_ORDRE_MERGE_PR_MAIN_AGENT.md` — AO CTO (décision en une page)
- `CLAUDE.md` — section merge (ordre CTO)
- `.cursor/rules/dms-agent-mandate-protocol.mdc` — protocole détaillé
- `.cursor/rules/dms-core.mdc` — rappel merge agent

## Note documentation historique

Les handovers et rapports d’époque antérieure à l’alignement **RÈGLE-ORG-10** sont **non normatifs** pour le merge Git ; en cas de doute : **`CLAUDE.md`**, ce addendum, **`DMS_V4.1.0_FREEZE.md`** (RÈGLE-ORG-10).
