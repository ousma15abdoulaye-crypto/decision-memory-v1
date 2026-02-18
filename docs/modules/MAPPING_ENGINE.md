DMS — CBA Template Mapping Engine
Module: Couche A — Exécution Version module: V1.0 Compatibilité DMS: V3.3.2 (FREEZE) Statut: CANONIQUE · STABLE · OPPOSABLE Auteur: Abdoulaye Ousmane — Founder & CTO

1. Rôle du module
Le CBA Template Mapping Engine est le moteur responsable de la projection déterministe des données de soumission dans un template Excel CBA canonique.

Il garantit que :

le template Excel est figé (source de vérité),
le moteur n’ajuste jamais la structure du fichier,
les données sont placées par indices calculés, sans heuristique fragile.
Ce module matérialise le principe fondamental du DMS : le document est une interface contractuelle, pas un artefact malléable.

2. Périmètre fonctionnel exact
Le module prend en charge exclusivement :

le mapping des fournisseurs (jusqu’à 50 fournisseurs max),
la gestion des colonnes au-delà de Z (AA, AB, …),
l’application du masquage (pré-large / non retenus),
la canonisation stricte des noms d’onglets,
l’application de styles visuels normalisés (codes de confiance).
Il ne réalise pas :

le calcul des scores,
l’évaluation conformité métier,
la normalisation dictionnaire,
l’accès à la Couche B (Market Signal, mémoire, audit).
3. Contraintes structurelles (non négociables)
Ce moteur applique volontairement les contraintes suivantes :

❌ Aucune insertion dynamique de colonnes
❌ Aucune modification du template Excel
❌ Aucune logique métier procurement
❌ Aucune dépendance ERP
❌ Aucun état global ou cache
Toutes les colonnes calculées sont déterministes, basées sur :

un index fournisseur,
une base de colonne connue,
un algorithme robuste (support > Z).
4. Source de vérité (Template Spec)
La spécification du template est versionnée et constitue la seule source de vérité :

docs/templates/template_spec_v1.0.json
Cette spécification définit :

les onglets attendus,
les colonnes fixes,
les offsets fournisseurs,
les règles de masquage,
les zones éditables vs protégées.
⚠️ Toute modification du template impose une nouvelle version de spec.

5. Structure du module
src/mapping/
├── template_engine.py        # Orchestrateur principal
├── supplier_mapper.py        # Fonctions populate_* par section
├── column_calculator.py      # Calcul robuste des colonnes (> Z)
├── styling.py                # Styles & codes visuels de confiance
tests/mapping/
├── test_engine_smoke.py      # Test smoke canonique
docs/templates/
├── template_spec_v1.0.json   # Spécification versionnée
src/templates/
├── DMS-CBA-CANONICAL-V1.0.xlsx
6. API principale
Initialisation
from mapping.template_engine import TemplateMappingEngine

engine = TemplateMappingEngine(
    spec_path="docs/templates/template_spec_v1.0.json",
    template_path="src/templates/DMS-CBA-CANONICAL-V1.0.xlsx",
)
Export CBA
out = engine.export_cba(
    case_data=case_data,
    output_dir="out"
)
Le moteur retourne :

le chemin du fichier généré,
une trace d’exécution déterministe,
un statut de complétion.
7. Format d’entrée attendu (case_data)
case_data = {
  "case_id": "MOPTI-2026-01",
  "version": 1,
  "submissions": [
    {
      "supplier_name": "FOURNISSEUR A",
      "conformity": {"RC": True},
      "capacity_scores": {},
      "sustainability_scores": {},
      "line_items": []
    }
  ]
}
⚠️ Toute donnée fournie à ce module est supposée :

validée,
normalisée,
scorée en amont.
8. Tests & garanties
test_engine_smoke.py valide :

chargement du template,
projection minimale,
absence d’erreur runtime,
respect strict de la spec.
Ce module est conçu pour :

ne jamais casser silencieusement,
échouer tôt si la spec ou le template divergent.
9. Alignement Constitution DMS
Ce module est conforme aux invariants suivants :

INV-1 : Exécution rapide et déterministe
INV-2 : Couche A autonome
INV-3 : Aucune influence sur le scoring
INV-7 : ERP-agnostique
INV-9 : Résultat strictement égal à la formule/spec
10. Statut freeze
Module: CBA Template Mapping Engine
Version: V1.0
DMS: V3.3.2
Statut: FREEZE-COMPATIBLE
Modifiable: ❌ sans versioning
Responsable: Abdoulaye Ousmane (CTO)
Toute évolution future impose :

Nouvelle version de spec,
Tests dédiés,
Validation explicite CTO.
