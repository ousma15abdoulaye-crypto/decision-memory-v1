# ADR-0014 — Re-séquencement Milestones Phase 3 : Analysis Summary / Export / Hardening

**Statut :** ACCEPTED
**Date :** 2026-02-24
**Auteur :** CTO Senior — Abdoulaye Ousmane
**Milestone :** #12 M-ANALYSIS-SUMMARY
**Références :** ADR-0003 (plan gelé), ADR-0008, ADR-0012

---

## Contexte

ADR-0003 gelait la séquence d'exécution de la Phase 3.
L'exécution réelle de M10/M11 a révélé une opportunité d'amélioration
architecturale : séparer explicitement la **synthèse** de la **mise en forme**.

## Décision

La séquence Phase 3+ est amendée comme suit :

| Ancien (ADR-0003) | Nouveau (ADR-0014) |
|---|---|
| M12 = M-CBA-GEN | M12 = M-ANALYSIS-SUMMARY |
| M13 = M-PV-GEN | M13 = M-CBA-EXPORT-RENDERER |
| M14 = M-PIPELINE-A-E2E-FINAL | M14 = M-SYSTEM-HARDENING-E2E |

### Nouvelle chaîne canonique

```
CAS v1 (exécution M10/M11)
  → SummaryDocument v1 (sens M12)
  → Artefact CBA STC (forme M13)
  → Preuve système (hardening M14)
```

## Raisons

1. **Découplage pipeline/template** : le moteur de synthèse
   ne doit pas connaître la mise en page client
2. **Contrat stable** : `SummaryDocument v1` est le contrat
   unique M12→M13 — gelé dans ADR-0015
3. **Réutilisabilité** : un deuxième client (UNICEF, gouvernement)
   = un nouveau renderer M13 — zéro modification M12
4. **Testabilité** : chaque couche est testable indépendamment
5. **Préparation M14** : le hardening teste des contrats stables,
   pas un monolithe génération/export

## Conséquences

- ADR-0003 reste la référence de discipline d'exécution
- Ce changement est une **surcouche ADR**, pas une improvisation
- M13 reçoit `SummaryDocument v1` comme seul contrat d'entrée
- M14 éprouve la chaîne M10→M13 complète

## Hash de certification

SHA-256 : 2B91181EA547E77021AFF7C15B81A67122986806C753542F874C0125313B4553
Méthode : sha256(contenu_utf8_de_ce_fichier)
Commande :
  Get-FileHash docs\adrs\ADR-0014_milestone-resequencing.md -Algorithm SHA256
