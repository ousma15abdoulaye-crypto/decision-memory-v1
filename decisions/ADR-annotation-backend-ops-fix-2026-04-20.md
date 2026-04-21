# ADR — Fixes Opérationnels annotation-backend (ex-post)

**Date**: 2026-04-20  
**Statut**: ACCEPTÉ (ex-post, CTO principal)  
**Contexte**: E4-bis benchmark validation (mandat 2026-04-21)  
**Auteur**: CTO principal (Abdoulaye Ousmane)  
**Légitimation agent**: Session Claude Sonnet 4.5 (handover E4-bis)

---

## Contexte

Lors du handover E4-bis (2026-04-21), l'agent a identifié 2 commits post-merge P3.2:

- **2490f6f3**: `chore(railway): config fichier dédié annotation-backend (Dockerfile services/)`
- **e754f821**: `fix(annotation-backend): psycopg + src/db/core pour Pass 2A / orchestrateur`

Ces commits ont modifié fichiers figés selon §8 doctrine (operational freeze annotation-backend).

**Question agent (Tour 2 D1)**: Ces commits violent-ils §8 ? Faut-il STOP ?

**Réponse CTO principal (V1)**: "oui je valide" — ces commits sont des **fixes opérationnels** pour maintenir le service Railway en état de fonctionnement.

---

## Décision

**ACCEPTÉ (ex-post)**: Commits 2490f6f3 + e754f821 sont **légitimes** et ne violent pas §8.

**Doctrine G1** (établie par cet ADR):

> **Fix opérationnel ≠ industrialisation**  
> Un commit qui restaure la fonctionnalité d'un service en production (Railway annotation-backend) sans ajouter de features ou modifier l'architecture prévue par le Plan Directeur V4.1 n'est **pas** une industrialisation prématurée.  
> Le freeze §8 vise à empêcher l'implémentation anticipée de features V4.1 hors mandat CTO, pas à bloquer les corrections nécessaires pour maintenir les services existants en état de marche.

---

## Conséquences

1. **Commits 2490f6f3 + e754f821**: Validés rétroactivement, pas de revert nécessaire.
2. **Branche E4-bis**: Peut procéder sans divergence HEAD (e754f821 est HEAD légitime).
3. **Future policy**: Agent peut distinguer "fix opérationnel" vs "industrialisation" via doctrine G1 sans micro-arbitrage systématique.
4. **Autorité déléguée**: CTO principal délègue au LLM la qualification fix opérationnel dans limites doctrine G1 (Doctrine G10-G11).

---

## Justification Technique

### Commit 2490f6f3 (chore railway config)
- **Nature**: Configuration Railway pour annotation-backend
- **Impact**: Déploiement correct du service (Dockerfile, config Railway)
- **Industrialisation?**: Non — config infrastructure pour service existant

### Commit e754f821 (fix psycopg + src/db/core)
- **Nature**: Correction dépendances + imports orchestrateur Pass 2A
- **Impact**: Correction bugs empêchant le fonctionnement du backend annotation
- **Industrialisation?**: Non — fixes pour code existant, pas de nouvelles features

---

## Références

- **§8 Doctrine**: Operational freeze annotation-backend (empêche industrialisation prématurée V4.1)
- **Handover E4-bis**: Tour 2 D1-D4, V1 validation CTO principal
- **Plan Directeur V4.1**: `docs/freeze/DMS_V4.1.0_FREEZE.md` (immuable)
- **Doctrine G10-G11**: Autonomie agent + autorité déléguée (mandat consolidé)

---

## Notes Agent

Cet ADR matérialise une décision CTO déjà prise (ex-post), ne crée pas de nouvelle règle. Il documente pour traçabilité future et réduit le risque de micro-arbitrage sur des situations similaires.
