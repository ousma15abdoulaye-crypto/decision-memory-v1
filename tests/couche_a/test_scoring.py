"""
Tests unitaires pour le moteur de scoring M3B.
"""
from datetime import datetime

import pytest

from src.core.models import DAOCriterion, SupplierPackage
from src.couche_a.scoring.engine import EliminationResult, ScoreResult, ScoringEngine


class TestScoringEngine:
    """Tests pour le moteur de scoring."""

    def test_score_result_creation(self):
        """Test de création d'un résultat de scoring."""
        score = ScoreResult(
            supplier_name="Fournisseur Test",
            category="commercial",
            score_value=85.5,
            calculation_method="price_lowest_100",
            calculation_details={"price": 1000, "lowest_price": 850, "currency": "XOF"},
            is_validated=False
        )

        assert score.supplier_name == "Fournisseur Test"
        assert score.category == "commercial"
        assert score.score_value == 85.5
        assert score.calculation_method == "price_lowest_100"
        assert "price" in score.calculation_details

    def test_elimination_result_creation(self):
        """Test de création d'un résultat d'élimination."""
        elimination = EliminationResult(
            supplier_name="Fournisseur Éliminé",
            criterion_id="crit_123",
            criterion_name="Certification ISO 9001",
            criterion_category="essential",
            failure_reason="Certification manquante",
            eliminated_at=datetime.utcnow()
        )

        assert elimination.supplier_name == "Fournisseur Éliminé"
        assert elimination.criterion_name == "Certification ISO 9001"
        assert elimination.criterion_category == "essential"
        assert elimination.failure_reason == "Certification manquante"

    def test_scoring_engine_initialization(self):
        """Test de l'initialisation du moteur de scoring."""
        engine = ScoringEngine()

        assert engine.commercial_method == "price_lowest_100"
        assert engine.capacity_method == "capacity_experience"
        assert engine.sustainability_method == "sustainability_certifications"

    def test_calculate_commercial_scores_basic(self):
        """Test du calcul des scores commerciaux avec données basiques."""
        engine = ScoringEngine()

        suppliers = [
            SupplierPackage(
                supplier_name="Fournisseur A",
                offer_ids=["offer_1"],
                documents=[],
                package_status="COMPLETE",
                has_financial=True,
                has_technical=True,
                has_admin=True,
                extracted_data={
                    "total_price": "1000 XOF",
                    "currency": "XOF"
                },
                missing_fields=[]
            ),
            SupplierPackage(
                supplier_name="Fournisseur B",
                offer_ids=["offer_2"],
                documents=[],
                package_status="COMPLETE",
                has_financial=True,
                has_technical=True,
                has_admin=True,
                extracted_data={
                    "total_price": "850 XOF",
                    "currency": "XOF"
                },
                missing_fields=[]
            )
        ]

        profile = {
            "criteria": [
                {"category": "essential", "weight": 0.0, "eliminatory": True},
                {"category": "commercial", "weight": 0.50, "min_weight": 0.40},
                {"category": "capacity", "weight": 0.30},
                {"category": "sustainability", "weight": 0.10, "min_weight": 0.10},
            ]
        }

        scores = engine._calculate_commercial_scores(suppliers, profile)

        assert len(scores) == 2
        assert any(s.supplier_name == "Fournisseur A" and s.category == "commercial" for s in scores)
        assert any(s.supplier_name == "Fournisseur B" and s.category == "commercial" for s in scores)

        # Fournisseur B a le prix le plus bas (850 XOF) donc devrait avoir 100 points
        supplier_b_score = next(s for s in scores if s.supplier_name == "Fournisseur B")
        assert supplier_b_score.score_value == 100.0

        # Fournisseur A devrait avoir un score basé sur la formule: (850/1000)*100 = 85
        supplier_a_score = next(s for s in scores if s.supplier_name == "Fournisseur A")
        assert supplier_a_score.score_value == 85.0

    def test_calculate_commercial_scores_no_prices(self):
        """Test du calcul des scores commerciaux sans prix disponibles."""
        engine = ScoringEngine()

        suppliers = [
            SupplierPackage(
                supplier_name="Fournisseur C",
                offer_ids=["offer_3"],
                documents=[],
                package_status="PARTIAL",
                has_financial=False,
                has_technical=True,
                has_admin=False,
                extracted_data={},
                missing_fields=["Prix total"]
            )
        ]

        profile = {"criteria": []}
        scores = engine._calculate_commercial_scores(suppliers, profile)

        assert len(scores) == 1
        assert scores[0].score_value == 0.0
        assert "error" in scores[0].calculation_details
        assert scores[0].calculation_details["error"] == "Aucun prix disponible"

    def test_calculate_capacity_scores(self):
        """Test du calcul des scores de capacité."""
        engine = ScoringEngine()

        suppliers = [
            SupplierPackage(
                supplier_name="Fournisseur avec références",
                offer_ids=["offer_1"],
                documents=[],
                package_status="COMPLETE",
                has_financial=True,
                has_technical=True,
                has_admin=True,
                extracted_data={
                    "technical_refs": ["Réf 1", "Réf 2", "Réf 3", "Réf 4", "Réf 5"]
                },
                missing_fields=[]
            ),
            SupplierPackage(
                supplier_name="Fournisseur sans références",
                offer_ids=["offer_2"],
                documents=[],
                package_status="COMPLETE",
                has_financial=True,
                has_technical=True,
                has_admin=True,
                extracted_data={
                    "technical_refs": []
                },
                missing_fields=[]
            )
        ]

        profile = {"criteria": []}
        scores = engine._calculate_capacity_scores(suppliers, profile)

        assert len(scores) == 2

        supplier_with_refs = next(s for s in scores if s.supplier_name == "Fournisseur avec références")
        assert supplier_with_refs.score_value == 100.0  # 5 références = 100 points
        assert supplier_with_refs.calculation_details["technical_references_count"] == 5

        supplier_no_refs = next(s for s in scores if s.supplier_name == "Fournisseur sans références")
        assert supplier_no_refs.score_value == 0.0

    def test_calculate_sustainability_scores(self):
        """Test du calcul des scores de durabilité."""
        engine = ScoringEngine()

        suppliers = [
            SupplierPackage(
                supplier_name="Fournisseur durable",
                offer_ids=["offer_1"],
                documents=["Document avec engagement environnemental et RSE"],
                package_status="COMPLETE",
                has_financial=True,
                has_technical=True,
                has_admin=True,
                extracted_data={},
                missing_fields=[]
            ),
            SupplierPackage(
                supplier_name="Fournisseur standard",
                offer_ids=["offer_2"],
                documents=["Document sans mots-clés"],
                package_status="COMPLETE",
                has_financial=True,
                has_technical=True,
                has_admin=True,
                extracted_data={},
                missing_fields=[]
            )
        ]

        profile = {"criteria": []}
        scores = engine._calculate_sustainability_scores(suppliers, profile)

        assert len(scores) == 2

        # Le fournisseur durable devrait avoir un score > 0
        sustainable_supplier = next(s for s in scores if s.supplier_name == "Fournisseur durable")
        assert sustainable_supplier.score_value > 0.0
        assert "environnement" in sustainable_supplier.calculation_details.get("found_keywords", []) or "rse" in sustainable_supplier.calculation_details.get("found_keywords", [])

    def test_calculate_total_scores(self):
        """Test du calcul des scores totaux pondérés."""
        engine = ScoringEngine()

        suppliers = [
            SupplierPackage(
                supplier_name="Fournisseur Test",
                offer_ids=["offer_1"],
                documents=[],
                package_status="COMPLETE",
                has_financial=True,
                has_technical=True,
                has_admin=True,
                extracted_data={},
                missing_fields=[]
            )
        ]

        # Scores simulés
        category_scores = [
            ScoreResult(
                supplier_name="Fournisseur Test",
                category="commercial",
                score_value=80.0,
                calculation_method="price_lowest_100",
                calculation_details={}
            ),
            ScoreResult(
                supplier_name="Fournisseur Test",
                category="capacity",
                score_value=70.0,
                calculation_method="capacity_experience",
                calculation_details={}
            ),
            ScoreResult(
                supplier_name="Fournisseur Test",
                category="sustainability",
                score_value=90.0,
                calculation_method="sustainability_certifications",
                calculation_details={}
            ),
            ScoreResult(
                supplier_name="Fournisseur Test",
                category="essentials",
                score_value=100.0,
                calculation_method="elimination_check",
                calculation_details={}
            )
        ]

        profile = {
            "criteria": [
                {"category": "essential", "weight": 0.0},
                {"category": "commercial", "weight": 0.50},
                {"category": "capacity", "weight": 0.30},
                {"category": "sustainability", "weight": 0.10},
            ]
        }

        total_scores = engine._calculate_total_scores(suppliers, category_scores, profile)

        assert len(total_scores) == 1
        total_score = total_scores[0]

        # Calcul attendu: (80 * 0.50) + (70 * 0.30) + (90 * 0.10) = 40 + 21 + 9 = 70
        expected_score = (80.0 * 0.50) + (70.0 * 0.30) + (90.0 * 0.10)
        assert abs(total_score.score_value - expected_score) < 0.01
        assert total_score.category == "total"
        assert total_score.calculation_method == "weighted_sum"

    def test_check_eliminatory_criteria(self):
        """Test de la vérification des critères éliminatoires."""
        engine = ScoringEngine()

        suppliers = [
            SupplierPackage(
                supplier_name="Fournisseur conforme",
                offer_ids=["offer_1"],
                documents=[],
                package_status="COMPLETE",
                has_financial=True,
                has_technical=True,
                has_admin=True,
                extracted_data={},
                missing_fields=[]
            )
        ]

        criteria = [
            DAOCriterion(
                categorie="essential",
                critere_nom="Certification requise",
                description="Certification ISO 9001 obligatoire",
                ponderation=0.0,
                type_reponse="boolean",
                seuil_elimination=1.0,  # Seuil d'élimination
                ordre_affichage=1
            ),
            DAOCriterion(
                categorie="commercial",
                critere_nom="Prix maximum",
                description="Prix ne doit pas dépasser 10000 XOF",
                ponderation=50.0,
                type_reponse="numeric",
                seuil_elimination=None,  # Pas éliminatoire
                ordre_affichage=2
            )
        ]

        eliminations = engine._check_eliminatory_criteria(suppliers, criteria)

        # La méthode _meets_criterion retourne True par défaut (stub)
        # Donc aucune élimination ne devrait être retournée
        assert len(eliminations) == 0

    def test_save_scores_to_db(self):
        """Test d'enregistrement des scores en base de données."""
        # Ce test vérifie que la méthode ne plante pas
        engine = ScoringEngine()

        scores = [
            ScoreResult(
                supplier_name="Fournisseur Test",
                category="commercial",
                score_value=85.5,
                calculation_method="price_lowest_100",
                calculation_details={"price": 1000, "lowest_price": 850},
                is_validated=False
            )
        ]

        # Vérifier que la méthode s'exécute sans erreur
        try:
            engine._save_scores_to_db("test_case_123", scores)
            assert True
        except Exception as e:
            pytest.fail(f"_save_scores_to_db a échoué avec: {e}")

    def test_save_eliminations_to_db(self):
        """Test d'enregistrement des éliminations en base de données."""
        engine = ScoringEngine()

        eliminations = [
            EliminationResult(
                supplier_name="Fournisseur Éliminé",
                criterion_id="crit_123",
                criterion_name="Certification manquante",
                criterion_category="essential",
                failure_reason="Certification ISO 9001 non fournie",
                eliminated_at=datetime.utcnow()
            )
        ]

        # Vérifier que la méthode s'exécute sans erreur
        try:
            engine.save_eliminations_to_db("test_case_123", eliminations)
            assert True
        except Exception as e:
            pytest.fail(f"save_eliminations_to_db a échoué avec: {e}")


class TestScoringIntegration:
    """Tests d'intégration pour le moteur de scoring."""

    def test_full_scoring_pipeline(self):
        """Test du pipeline complet de scoring."""
        engine = ScoringEngine()

        # Critères DAO
        criteria = [
            DAOCriterion(
                categorie="essential",
                critere_nom="Certification ISO 9001",
                description="Certification qualité obligatoire",
                ponderation=0.0,
                type_reponse="boolean",
                seuil_elimination=1.0,
                ordre_affichage=1
            ),
            DAOCriterion(
                categorie="commercial",
                critere_nom="Prix",
                description="Prix total de l'offre",
                ponderation=50.0,
                type_reponse="numeric",
                seuil_elimination=None,
                ordre_affichage=2
            ),
            DAOCriterion(
                categorie="capacity",
                critere_nom="Expérience",
                description="Expérience similaire dans les 3 dernières années",
                ponderation=30.0,
                type_reponse="numeric",
                seuil_elimination=None,
                ordre_affichage=3
            ),
            DAOCriterion(
                categorie="sustainability",
                critere_nom="Engagement RSE",
                description="Politique RSE documentée",
                ponderation=10.0,
                type_reponse="boolean",
                seuil_elimination=None,
                ordre_affichage=4
            )
        ]

        # Fournisseurs avec données extraites
        suppliers = [
            SupplierPackage(
                supplier_name="Fournisseur A",
                offer_ids=["offer_1"],
                documents=["Document avec engagement environnemental"],
                package_status="COMPLETE",
                has_financial=True,
                has_technical=True,
                has_admin=True,
                extracted_data={
                    "total_price": "1000 XOF",
                    "currency": "XOF",
                    "technical_refs": ["Projet 1", "Projet 2", "Projet 3"],
                    "lead_time_days": 30,
                    "validity_days": 60
                },
                missing_fields=[]
            ),
            SupplierPackage(
                supplier_name="Fournisseur B",
                offer_ids=["offer_2"],
                documents=["Document standard"],
                package_status="COMPLETE",
                has_financial=True,
                has_technical=True,
                has_admin=True,
                extracted_data={
                    "total_price": "850 XOF",
                    "currency": "XOF",
                    "technical_refs": ["Projet A", "Projet B"],
                    "lead_time_days": 45,
                    "validity_days": 90
                },
                missing_fields=[]
            )
        ]

        # Exécuter le calcul complet
        scores, eliminations = engine.calculate_scores_for_case(
            case_id="test_case_123",
            suppliers=suppliers,
            criteria=criteria
        )

        # Vérifications de base
        assert isinstance(scores, list)
        assert isinstance(eliminations, list)

        # Devrait avoir des scores pour chaque fournisseur et chaque catégorie
        # (2 fournisseurs × 5 catégories = 10 scores)
        assert len(scores) == 10  # commercial, capacity, sustainability, essentials, total pour chaque fournisseur

        # Vérifier que chaque fournisseur a un score total
        total_scores = [s for s in scores if s.category == "total"]
        assert len(total_scores) == 2

        # Vérifier que les scores commerciaux sont calculés
        commercial_scores = [s for s in scores if s.category == "commercial"]
        assert len(commercial_scores) == 2

        # Fournisseur B devrait avoir le score commercial le plus élevé (prix le plus bas)
        supplier_b_commercial = next(s for s in commercial_scores if s.supplier_name == "Fournisseur B")
        supplier_a_commercial = next(s for s in commercial_scores if s.supplier_name == "Fournisseur A")
        assert supplier_b_commercial.score_value == 100.0  # Prix le plus bas
        assert supplier_a_commercial.score_value < 100.0  # Prix plus élevé
