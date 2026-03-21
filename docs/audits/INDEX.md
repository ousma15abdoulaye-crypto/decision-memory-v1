# INDEX AUDITS — DMS v4.1
<!-- Généré : 2026-03-17 — Ref : DETTE-02 audit CTO senior -->

## RÈGLE
- Rapports actifs : `docs/audits/` (convention à partir de maintenant)
- Rapports résolus : `docs/archives/audits/` (convention à partir de maintenant)
- Format des **nouveaux** rapports : `AUDIT_SUJET_YYYY-MM-DD.md` (les rapports historiques peuvent déroger)
- Archiver les nouveaux rapports après le milestone suivant

## RAPPORTS ACTIFS — ACTION REQUISE

| Fichier | Date | Statut | Actions |
|---------|------|--------|---------|
| AUDIT_CTO_SENIOR_2026-03-17.md | 2026-03-17 | EN COURS | 12 ASAP + 13 DETTE |
| EXIT_PLAN_ALIGN_01_MANIFEST.md | 2026-03-21 | LIVRÉ | **Paquet** EXIT-PLAN-ALIGN-01 — entrée unique |
| SYSMAP_DMS_EXIT_PLAN_01.md | 2026-03-21 | LIVRÉ | Cartographie système opposable (révisé : dual-app) |
| SEC_MT_THREAT_MODEL_MINIMAL_EXIT_01.md | 2026-03-21 | LIVRÉ | Menace minimale + barrières (hors annotation) |
| RUNTIME_DOC_ALIGNMENT_MATRIX_EXIT_01.md | 2026-03-21 | LIVRÉ | Matrice doc vs runtime — 10 lignes fermées |
| COPILOT_PR_MULTI_TENANT_REVIEW.md | 2026-03-21 | LIVRÉ | Revue PR GitHub Copilot (org_id JWT vs tenant_id) + merge |
| PR_234_MERGE_ALIGNMENT.md | 2026-03-21 | LIVRÉ | PR #234 : fusion exit-plan + anti-redondance agents / Copilot |

## RAPPORTS ARCHIVÉS — RÉSOLUS

> Remarque : la liste ci-dessous décrit la **structure cible** d’archivage et des familles de fichiers, pas un état exhaustif du dépôt à date.

| Fichier | Date | Milestone résolution |
|---------|------|----------------------|
| AUDIT_M4_M7_*.md (famille de ~7 fichiers) | 2025-xx | M8 |
| CI_*.md (famille de ~8 fichiers) | 2025-xx | M10 |
| AUDIT_M11_*.md | 2026-xx | M11 |

## STRUCTURE ARCHIVAGE (CIBLE)
```
docs/
  audits/
    INDEX.md              ← ce fichier
    AUDIT_CTO_SENIOR_2026-03-17.md  ← actif
  archives/
    audits/
      AUDIT_M4_M7_*.md   ← résolus
      CI_*.md             ← résolus
```

## PROCHAINE REVUE
Archiver AUDIT_CTO_SENIOR_2026-03-17.md après
validation complète des 12 ASAP — cible : post-Mandat 4.
