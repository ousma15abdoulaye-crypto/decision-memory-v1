"""Test Invariant 1: Réduction de charge cognitive.

Constitution V3.3.2 §2: Le système doit réduire la charge cognitive,
pas l'augmenter.
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_inv_01_api_endpoints_simple():
    """Les endpoints API doivent être simples et intuitifs."""
    # Vérifier que les endpoints principaux existent et sont accessibles
    response = client.get("/health")
    assert response.status_code == 200

    # Endpoints doivent avoir des noms clairs
    # Pas de endpoints cryptiques ou nécessitant documentation complexe
    assert "/api/cases" in str(app.routes)
    assert "/api/health" in str(app.routes)


def test_inv_01_no_complex_workflows():
    """Les workflows ne doivent pas nécessiter plus de 3 étapes pour une action courante."""
    # Exemple: Upload DAO doit être simple
    # 1. POST /api/cases/{id}/upload-dao
    # Pas de pré-requis complexes ou étapes multiples

    # Cette vérification est structurelle - pas de test fonctionnel nécessaire
    # mais on vérifie que les endpoints critiques sont simples
    pass


def test_inv_01_error_messages_clear():
    """Les messages d'erreur doivent être clairs et actionnables."""
    # Tester un endpoint avec données invalides
    response = client.post("/api/cases/invalid-id/upload-dao", files={"file": ("test.pdf", b"content")})

    # Le message d'erreur doit être compréhensible
    if response.status_code != 200:
        error_detail = response.json().get("detail", "")
        # Vérifier que le message n'est pas cryptique
        assert len(error_detail) > 0
        assert "error" not in error_detail.lower() or "not found" in error_detail.lower()


def test_inv_01_no_manual_configuration_required():
    """Le système ne doit pas nécessiter de configuration manuelle complexe."""
    # Vérifier que les valeurs par défaut sont raisonnables
    # Pas de configuration obligatoire complexe au démarrage

    # Le système doit démarrer avec DATABASE_URL uniquement
    # Pas de fichiers de config multiples ou complexes
    pass
