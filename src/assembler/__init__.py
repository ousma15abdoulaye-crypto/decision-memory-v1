"""Module Pass -1 — Assemblage ZIP → bundles fournisseurs.

Pipeline stateful LangGraph orchestrant :
  - Validation déterministe du ZIP
  - OCR (Mistral OCR 3 + fallback Azure Document Intelligence)
  - Classification M12 (Mistral Small)
  - Liaison fournisseur
  - Calcul complétude
  - Interruption HITL si bundle incomplet
  - Écriture supplier_bundles + bundle_documents

Référence : docs/freeze/DMS_V4.2.0_ADDENDUM.md §VI — Pass -1
ADR-V420-001 (pydantic-ai), ADR-V420-002 (langgraph)
Performance gate : ZIP 15 fichiers SCI Mali → 4 bundles < 30s
"""
