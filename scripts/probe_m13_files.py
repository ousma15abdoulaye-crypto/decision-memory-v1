#!/usr/bin/env python3
"""
Vérifie la présence des chemins M13 V5 (FREEZE CANDIDATE → FREEZE).

Usage: python scripts/probe_m13_files.py
Exit 0 si tous les chemins existent sous la racine du dépôt.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 60 chemins uniques : 19 YAML + cœur src + contrats + migration + tests + ancres repo.
REQUIRED_PATHS: tuple[str, ...] = (
    # config/regulatory (19)
    "config/regulatory/registry.yaml",
    "config/regulatory/_template/framework_template.yaml",
    "config/regulatory/principles/uncitral_wb_oecd_principles.yaml",
    "config/regulatory/sci/thresholds.yaml",
    "config/regulatory/sci/procedure_types.yaml",
    "config/regulatory/sci/required_documents.yaml",
    "config/regulatory/sci/timelines.yaml",
    "config/regulatory/sci/control_organs.yaml",
    "config/regulatory/sci/derogations.yaml",
    "config/regulatory/sci/principles_mapping.yaml",
    "config/regulatory/sci/document_validity_rules.yaml",
    "config/regulatory/dgmp_mali/thresholds.yaml",
    "config/regulatory/dgmp_mali/procedure_types.yaml",
    "config/regulatory/dgmp_mali/required_documents.yaml",
    "config/regulatory/dgmp_mali/timelines.yaml",
    "config/regulatory/dgmp_mali/control_organs.yaml",
    "config/regulatory/dgmp_mali/derogations.yaml",
    "config/regulatory/dgmp_mali/principles_mapping.yaml",
    "config/regulatory/dgmp_mali/document_validity_rules.yaml",
    # src — moteurs M13 + dépendances (22)
    "src/procurement/compliance_models_m13.py",
    "src/procurement/m13_confidence.py",
    "src/procurement/regulatory_config_loader.py",
    "src/procurement/regulatory_yaml_validity.py",
    "src/procurement/regime_resolver.py",
    "src/procurement/requirements_instantiator.py",
    "src/procurement/compliance_gate_assembler.py",
    "src/procurement/derogation_assessor.py",
    "src/procurement/principles_mapper.py",
    "src/procurement/ocds_coverage_builder.py",
    "src/procurement/m12_reconstruct.py",
    "src/procurement/benchmark_status_service.py",
    "src/procurement/m13_engine.py",
    "src/procurement/m13_regulatory_profile_repository.py",
    "src/procurement/regulatory_index.py",
    "src/procurement/document_validity_rules.py",
    "src/procurement/compliance_models.py",
    "src/procurement/procedure_models.py",
    "src/procurement/document_ontology.py",
    "src/annotation/passes/pass_2a_regulatory_profile.py",
    "src/annotation/orchestrator.py",
    "src/api/routes/regulatory_profile.py",
    # entrée & migration (2)
    "main.py",
    "alembic/versions/057_m13_regulatory_profile_and_correction_log.py",
    # documentation & contrats (7)
    "docs/adr/ADR-M13-001_regulatory_profile_engine.md",
    "docs/contracts/annotation/PASS_2A_REGULATORY_PROFILE_CONTRACT.md",
    "docs/contracts/annotation/M12_M13_HANDOFF_CONTRACT.md",
    "docs/contracts/annotation/M13_M14_HANDOFF_CONTRACT.md",
    "docs/contracts/annotation/ANNOTATION_ORCHESTRATOR_FSM.md",
    "docs/contracts/annotation/PASS_OUTPUT_STANDARD.md",
    "docs/freeze/CONTEXT_ANCHOR.md",
    # scripts & tests (8)
    "scripts/probe_alembic_head.py",
    "scripts/validate_mrd_state.py",
    "tests/procurement/m13_test_fixtures.py",
    "tests/procurement/test_m13_engine_smoke.py",
    "tests/procurement/test_regime_resolver.py",
    "tests/annotation/test_pass_2a_regulatory_profile.py",
    "tests/test_046b_imc_map_fix.py",
    "scripts/probe_m13_files.py",
    # ancres dépôt (2)
    "pyproject.toml",
    "CLAUDE.md",
)


def main() -> int:
    if len(set(REQUIRED_PATHS)) != len(REQUIRED_PATHS):
        print("INTERNAL: duplicate paths in REQUIRED_PATHS")
        return 2
    missing: list[str] = []
    for rel in REQUIRED_PATHS:
        p = ROOT / rel
        if not p.is_file():
            missing.append(rel)
    if missing:
        print("MISSING:", len(missing))
        for m in missing:
            print(" ", m)
        return 1
    print("OK:", len(REQUIRED_PATHS), "paths under", ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
