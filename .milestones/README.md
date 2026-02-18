# Milestones — Gates CI (V3.3.2)

Fichiers `.done` marquant la complétion des milestones DMS V3.3.2.  
Ordre strict défini dans `MILESTONES_EXECUTION_PLAN_V3.3.2.md`.  
Le workflow `ci-milestones-gates.yml` échoue si l’ordre est violé.

Les gates (coverage, invariants) ne deviennent **bloquantes** que lorsque le milestone correspondant est marqué DONE.

## Marquer un milestone DONE

Créer un fichier vide (ou avec contenu optionnel) :

```bash
.milestones/<ID>.done
