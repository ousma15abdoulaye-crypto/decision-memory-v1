"""
Offer processing: detection, aggregation, and extraction.
Handles partial offers and supplier package management.
"""

import re
from pathlib import Path
from typing import Any

from src.core.models import DAOCriterion, OfferSubtype, SupplierPackage


# =========================
# Document Subtype Detection (PARTIAL OFFERS)
# =========================
def detect_offer_subtype(text: str, filename: str) -> OfferSubtype:
    """
    Détection automatique du type de document d'offre.
    Permet de gérer les offres partielles (uniquement financière, etc.)
    """
    text_lower = text.lower()
    filename_lower = filename.lower()

    # Détection financière
    financial_patterns = [
        r"prix\s*(total|unitaire)",
        r"montant",
        r"co[uû]t",
        r"(fcfa|cfa|xof|usd|eur)",
        r"offre\s*(financière|de\s*prix)",
        r"bordereau\s*de\s*prix",
    ]
    has_financial = any(
        re.search(pattern, text_lower) for pattern in financial_patterns
    )

    # Détection technique
    technical_patterns = [
        r"(caract[ée]ristiques?\s*techniques?|spécifications?)",
        r"(r[ée]f[ée]rences?\s*(techniques?|clients?))",
        r"(exp[ée]rience|capacit[ée]\s*technique)",
        r"(certifications?|agr[ée]ments?)",
        r"offre\s*technique",
    ]
    has_technical = any(
        re.search(pattern, text_lower) for pattern in technical_patterns
    )

    # Détection administrative
    admin_patterns = [
        r"(documents?\s*(administratifs?|l[ée]gaux))",
        r"(attestation|certificat)",
        r"(kbis|rccm|nif|registre\s*de\s*commerce)",
        r"(fiscal|social)",
        r"offre\s*administrative",
    ]
    has_admin = any(re.search(pattern, text_lower) for pattern in admin_patterns)

    # Classification
    count = sum([has_financial, has_technical, has_admin])

    if count == 0:
        # Fallback: inférer depuis le nom de fichier
        if any(kw in filename_lower for kw in ["financ", "prix", "price", "cost"]):
            has_financial = True
        elif any(kw in filename_lower for kw in ["technique", "technical", "spec"]):
            has_technical = True
        elif any(kw in filename_lower for kw in ["admin", "legal", "conformit"]):
            has_admin = True
        count = sum([has_financial, has_technical, has_admin])

    # Détermination du subtype
    if count >= 2:
        subtype = "COMBINED"
        confidence = "HIGH" if count == 3 else "MEDIUM"
    elif has_financial:
        subtype = "FINANCIAL_ONLY"
        confidence = "MEDIUM" if count == 1 else "LOW"
    elif has_technical:
        subtype = "TECHNICAL_ONLY"
        confidence = "MEDIUM"
    elif has_admin:
        subtype = "ADMIN_ONLY"
        confidence = "MEDIUM"
    else:
        subtype = "UNKNOWN"
        confidence = "LOW"

    return OfferSubtype(
        subtype=subtype,
        has_financial=has_financial,
        has_technical=has_technical,
        has_admin=has_admin,
        confidence=confidence,
    )


def aggregate_supplier_packages(offers: list[dict]) -> list[SupplierPackage]:
    """
    Agrège les documents par fournisseur pour gérer les offres partielles.
    Un fournisseur peut soumettre plusieurs documents (financier, technique, admin).
    """
    # Grouper par nom de fournisseur
    by_supplier: dict[str, list[dict]] = {}
    for offer in offers:
        supplier_name = offer.get("supplier_name", "UNKNOWN")
        if supplier_name not in by_supplier:
            by_supplier[supplier_name] = []
        by_supplier[supplier_name].append(offer)

    packages: list[SupplierPackage] = []

    for supplier_name, docs in by_supplier.items():
        # Agréger les capacités
        has_financial = any(
            d.get("subtype", {}).get("has_financial", False) for d in docs
        )
        has_technical = any(
            d.get("subtype", {}).get("has_technical", False) for d in docs
        )
        has_admin = any(d.get("subtype", {}).get("has_admin", False) for d in docs)

        # Fusionner les données extraites
        merged_data = {
            "total_price": None,
            "total_price_source": None,
            "currency": "XOF",
            "lead_time_days": None,
            "lead_time_source": None,
            "validity_days": None,
            "validity_source": None,
            "technical_refs": [],
        }

        for doc in docs:
            for key in merged_data.keys():
                if key == "technical_refs":
                    merged_data[key].extend(doc.get(key, []))
                elif doc.get(key) is not None and merged_data[key] is None:
                    merged_data[key] = doc.get(key)

        # Déduplication des refs techniques
        merged_data["technical_refs"] = list(set(merged_data["technical_refs"]))

        # CRITIQUE: Séparer missing_parts (sections non soumises) vs missing_extracted_fields (données manquantes)
        missing_parts = []
        if not has_admin:
            missing_parts.append("ADMIN")
        if not has_technical:
            missing_parts.append("TECHNICAL")

        # missing_extracted_fields: données attendues mais non trouvées DANS les sections soumises
        missing_extracted = []
        if has_financial and merged_data["total_price"] is None:
            missing_extracted.append("Prix total")
        if has_financial and merged_data["lead_time_days"] is None:
            missing_extracted.append("Délai livraison")
        if has_financial and merged_data["validity_days"] is None:
            missing_extracted.append("Validité offre")
        if has_technical and not merged_data["technical_refs"]:
            missing_extracted.append("Références techniques")

        # missing_fields pour compatibilité (mais maintenant explicitement séparé)
        merged_data["missing_parts"] = missing_parts
        merged_data["missing_extracted_fields"] = missing_extracted
        merged_data["missing_fields"] = missing_extracted  # Backward compat

        # Statut du package
        if has_financial and has_technical and has_admin:
            package_status = "COMPLETE"
        elif has_financial or has_technical:
            package_status = "PARTIAL"
        else:
            package_status = "MISSING"

        packages.append(
            SupplierPackage(
                supplier_name=supplier_name,
                offer_ids=[d.get("artifact_id", "") for d in docs],
                documents=docs,
                package_status=package_status,
                has_financial=has_financial,
                has_technical=has_technical,
                has_admin=has_admin,
                extracted_data=merged_data,
                missing_fields=missing_extracted,  # Données manquantes (pas sections non soumises)
            )
        )

    return packages


def guess_supplier_name(text: str, filename: str) -> str:
    """
    Extract supplier name from filename or document.
    ❌ INTERDIT d'utiliser un offer_id comme nom fournisseur.

    Ordre de fallback:
    a) Nettoyer filename -> retourner si valide et significatif
    b) Chercher pattern "Société/Entreprise: ..." dans texte
    c) Chercher première ligne MAJUSCULE non-titre
    d) Retourner "FOURNISSEUR_INCONNU"
    """
    # a) Nettoyer filename
    base = Path(filename).stem
    # D'abord normaliser les séparateurs
    base = re.sub(r"[_\-]+", " ", base)
    # Puis retirer mots-clés communs (avec espaces comme séparateurs)
    base = re.sub(
        r"(?i)\b(offre|lot|dao|rfq|mpt|mopti|2026|2025|2024|annexe|annex)\b", " ", base
    )
    base = base.strip()

    # Retirer IDs UUID-like ou hash-like et nombres purs
    base = re.sub(r"\b[a-f0-9]{8,}\b", "", base, flags=re.IGNORECASE)
    base = re.sub(r"\b[A-F0-9\-]{32,}\b", "", base)
    base = re.sub(r"^\d+$", "", base)  # Retirer si c'est juste un nombre
    base = re.sub(r"\s+", " ", base).strip()  # Normaliser espaces multiples

    # Vérifier que le filename nettoyé est significatif (pas juste des chiffres/mots génériques)
    # Exclure mots génériques trop courts ou techniques
    generic_words = [
        "DOC",
        "PDF",
        "FILE",
        "DOCUMENT",
        "TEMP",
        "NEW",
        "OLD",
        "FINAL",
        "V",
        "VER",
    ]
    base_upper = base.upper().strip()

    if (
        len(base) >= 5
        and re.search(r"[A-Za-z]{3,}", base)
        and base_upper not in generic_words
    ):
        return base.upper()[:80]

    # b) Chercher pattern "Société/Entreprise: ..." dans texte (prioritaire sur ligne majuscule)
    match = re.search(
        r"(?i)(soci[ée]t[ée]|entreprise|firm|company)[:\s]+([A-Za-zÀ-ÿ\s]{4,80})", text
    )
    if match:
        return match.group(2).strip().upper()[:80]

    # c) Première ligne MAJUSCULE non-titre dans le document
    for line in text.splitlines():
        line = line.strip()
        if 4 <= len(line) <= 100 and line == line.upper() and re.search(r"[A-Z]", line):
            # Exclure titres de section
            if not re.match(r"^(OFFRE|PROPOSITION|SOUMISSION|ANNEXE)", line):
                return line[:80]

    # d) Dernier recours
    return "FOURNISSEUR_INCONNU"


def extract_offer_data_guided(
    offer_text: str, criteria: list[DAOCriterion]
) -> dict[str, Any]:
    """
    Extraction GUIDÉE par critères DAO (pas aveugle).
    Retourne: données + sources + champs manquants.
    """
    extracted = {
        "total_price": None,
        "total_price_source": None,
        "currency": "XOF",
        "lead_time_days": None,
        "lead_time_source": None,
        "validity_days": None,
        "validity_source": None,
        "technical_refs": [],
        "missing_fields": [],
    }

    # Prix (si critère commercial présent)
    commercial_criteria = [c for c in criteria if c.categorie == "commercial"]
    if commercial_criteria:
        money = re.findall(
            r"(?i)(prix\s+total|montant\s+total|total)[:\s]*(\d{1,3}(?:[\s\.,]\d{3})+(?:[\s\.,]\d{2})?|\d+)\s*(FCFA|CFA|XOF)",
            offer_text,
        )
        if not money:
            # Fallback: any large number with currency
            money = re.findall(
                r"(?i)(\d{1,3}(?:[\s\.,]\d{3})+(?:[\s\.,]\d{2})?|\d+)\s*(FCFA|CFA|XOF)",
                offer_text,
            )

        if money:

            def to_num(s: str) -> float:
                s = s.replace(" ", "").replace(",", ".")
                if s.count(".") > 1:
                    parts = s.split(".")
                    s = "".join(parts[:-1]) + "." + parts[-1]
                try:
                    return float(s)
                except (ValueError, TypeError):
                    return 0.0

            if len(money[0]) == 3:  # Format avec label
                best = max(money, key=lambda m: to_num(m[1]))
                extracted["total_price"] = f"{best[1]} {best[2].upper()}"
                extracted["total_price_source"] = f"Pattern: '{best[0]}'"
            else:
                best = max(money, key=lambda m: to_num(m[0]))
                extracted["total_price"] = f"{best[0]} {best[1].upper()}"
                extracted["total_price_source"] = "Heuristique: plus grand montant"
        else:
            extracted["missing_fields"].append("Prix total")

    # Délai
    m = re.search(
        r"(?i)(d[ée]lai\s+(?:de\s+)?livraison|lead\s*time)[:\s\-]*([0-9]{1,3})\s*(jours?|days?)",
        offer_text,
    )
    if m:
        extracted["lead_time_days"] = int(m.group(2))
        extracted["lead_time_source"] = f"Pattern: '{m.group(1)}'"
    else:
        extracted["missing_fields"].append("Délai livraison")

    # Validité
    m2 = re.search(
        r"(?i)(validit[ée]\s+(?:de\s+l['\u2019])?offre|valid\s*until)[:\s\-]*([0-9]{1,3})\s*(jours?|days?)",
        offer_text,
    )
    if m2:
        extracted["validity_days"] = int(m2.group(2))
        extracted["validity_source"] = f"Pattern: '{m2.group(1)}'"
    else:
        extracted["missing_fields"].append("Validité offre")

    # Références techniques
    technical_criteria = [c for c in criteria if c.categorie == "technique"]
    if technical_criteria:
        refs = re.findall(
            r"(?i)(r[ée]f[ée]rence|client|projet|contrat)[:\s]+([\w\s\-]{10,100})",
            offer_text,
        )
        extracted["technical_refs"] = [r[1].strip() for r in refs[:5]]
        if not extracted["technical_refs"]:
            extracted["missing_fields"].append("Références techniques")

    return extracted
