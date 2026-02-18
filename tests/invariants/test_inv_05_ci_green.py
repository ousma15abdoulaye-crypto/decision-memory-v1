"""Test Invariant 5: CI verte obligatoire.

Constitution V3.3.3 §2: Aucune PR ne doit être mergée avec CI rouge.
"""

import os

import pytest
import yaml


def test_inv_05_no_force_success():
    """Les workflows CI ne doivent pas forcer le succès avec || true."""
    workflows_dir = ".github/workflows"
    if not os.path.exists(workflows_dir):
        pytest.skip("Workflows directory not found")

    for file in os.listdir(workflows_dir):
        if file.endswith(".yml") or file.endswith(".yaml"):
            filepath = os.path.join(workflows_dir, file)
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
                # Vérifier qu'il n'y a pas de || true qui masque les erreurs
                assert "|| true" not in content
                assert "||true" not in content


def test_inv_05_ci_fails_on_error():
    """La CI doit échouer si les tests échouent."""
    # Vérifier que les workflows de test n'ont pas de continue-on-error: true
    workflows_dir = ".github/workflows"
    if os.path.exists(workflows_dir):
        for file in os.listdir(workflows_dir):
            if file.endswith(".yml") or file.endswith(".yaml"):
                filepath = os.path.join(workflows_dir, file)
                with open(filepath, encoding="utf-8") as f:
                    workflow = yaml.safe_load(f)
                    if workflow and "jobs" in workflow:
                        for job_name, job_config in workflow["jobs"].items():
                            if "steps" in job_config:
                                for step in job_config["steps"]:
                                    # Vérifier qu'il n'y a pas de continue-on-error sur les steps de test
                                    if "run" in step and ("pytest" in step["run"] or "test" in step["run"].lower()):
                                        assert step.get("continue-on-error", False) is False


def test_inv_05_required_checks():
    """Les checks CI requis doivent être présents."""
    # Vérifier que les workflows essentiels existent
    required_workflows = [
        "ci-main.yml",  # Workflow principal
        "ci-freeze-integrity.yml",  # Vérification freeze
    ]

    workflows_dir = ".github/workflows"
    if os.path.exists(workflows_dir):
        existing_workflows = os.listdir(workflows_dir)
        for required in required_workflows:
            assert required in existing_workflows, f"Workflow requis manquant: {required}"
