"""Generate golden dataset cases 011-050 for DMS VIVANT V2 (GAP-9).

Run once:  python scripts/_generate_golden_dataset.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

CASES_DIR = Path(__file__).parent.parent / "data" / "golden" / "cases"
EXPECTED_DIR = Path(__file__).parent.parent / "data" / "golden" / "expected"

CASES_DIR.mkdir(parents=True, exist_ok=True)
EXPECTED_DIR.mkdir(parents=True, exist_ok=True)

# Each entry: (case_n, description, framework, family, value, currency, zone, humanitarian, tags,
#              expected_framework, procedure_types, principles_count, sustainability, derog_count, derog_gte, notes)

ENTRIES = [
    # ── DGMP Mali, Goods ─────────────────────────────────────────────────────
    (11, "DGMP goods procurement AOO Bamako, 50M XOF", "dgmp", "goods", 50_000_000, "XOF", "Bamako", False,
     ["dgmp", "goods", "aoo", "high_value"],
     "dgmp", ["appel_offres_ouvert"], 9, True, 0, None,
     "DGMP AOO — above threshold, Bamako, standard"),
    (12, "DGMP services, Mopti, 8M XOF, below AOO threshold", "dgmp", "services", 8_000_000, "XOF", "Mopti", False,
     ["dgmp", "services", "mopti", "below_threshold"],
     "dgmp", ["demande_cotation", "consultation_restreinte"], 9, True, 0, None,
     "DGMP below AOO threshold in Mopti"),
    (13, "DGMP works, Bamako, 120M XOF, construction", "dgmp", "works", 120_000_000, "XOF", "Bamako", False,
     ["dgmp", "works", "construction", "bamako"],
     "dgmp", ["appel_offres_ouvert"], 9, True, 0, None,
     "DGMP works large value"),
    (14, "DGMP goods, Kidal, 30M XOF, security zone", "dgmp", "goods", 30_000_000, "XOF", "Kidal", False,
     ["dgmp", "goods", "kidal", "security"],
     "dgmp", ["appel_offres_restreint", "entente_directe"], 9, True, None, 1,
     "DGMP Kidal security derogation possible"),
    (15, "DGMP services, Tombouctou, no value, security", "dgmp", "services", None, "XOF", "Tombouctou", False,
     ["dgmp", "services", "tombouctou", "no_value"],
     "dgmp", ["appel_offres_ouvert", "appel_offres_restreint", "entente_directe"], 9, True, None, 1,
     "DGMP Tombouctou, no value → highest tier + security derogation"),

    # ── SCI Framework, Services ───────────────────────────────────────────────
    (16, "SCI services, Bamako, USD 5000, IT services", "sci", "services", 5_000, "USD", "Bamako", False,
     ["sci", "services", "it", "low_value"],
     "sci", ["request_for_quotation"], 9, True, 0, None,
     "SCI services low value below ITB"),
    (17, "SCI services, Mopti, USD 120000, consultancy", "sci", "services", 120_000, "USD", "Mopti", False,
     ["sci", "services", "consultancy", "mopti"],
     "sci", ["open_international", "open_national"], 9, True, 0, None,
     "SCI consultancy above ITB Mopti"),
    (18, "SCI goods, Kidal, USD 8000, humanitarian", "sci", "goods", 8_000, "USD", "Kidal", True,
     ["sci", "goods", "kidal", "humanitarian"],
     "sci", ["request_for_quotation", "direct_procurement"], 9, True, None, 1,
     "SCI humanitarian + Kidal = derogation"),
    (19, "SCI works, Bamako, USD 200000, construction rehab", "sci", "works", 200_000, "USD", "Bamako", False,
     ["sci", "works", "construction", "bamako"],
     "sci", ["open_international", "open_national"], 9, True, 0, None,
     "SCI works large above ITB"),
    (20, "SCI services, Tombouctou, USD 45000, logistics", "sci", "services", 45_000, "USD", "Tombouctou", True,
     ["sci", "services", "logistics", "tombouctou", "humanitarian"],
     "sci", ["request_for_quotation", "direct_procurement"], 9, True, None, 1,
     "SCI humanitarian logistics Tombouctou"),

    # ── Entente Directe / Direct Procurement ─────────────────────────────────
    (21, "SCI goods, entente directe, sole source, Bamako", "sci", "goods", 3_000, "USD", "Bamako", False,
     ["sci", "goods", "sole_source", "direct"],
     "sci", ["direct_procurement", "request_for_quotation"], 9, True, None, 1,
     "Sole source justification required"),
    (22, "DGMP services, entente directe, emergency, Mopti", "dgmp", "services", 5_000_000, "XOF", "Mopti", True,
     ["dgmp", "services", "emergency", "entente_directe"],
     "dgmp", ["entente_directe"], 9, True, None, 1,
     "Emergency entente directe DGMP"),
    (23, "DGMP goods, emergency flood relief, Mopti", "dgmp", "goods", 15_000_000, "XOF", "Mopti", True,
     ["dgmp", "goods", "flood", "emergency", "humanitarian"],
     "dgmp", ["entente_directe"], 9, True, None, 1,
     "Emergency flood relief entente directe"),
    (24, "SCI goods, emergency nutrition, Kidal", "sci", "goods", 50_000, "USD", "Kidal", True,
     ["sci", "goods", "nutrition", "emergency", "kidal", "humanitarian"],
     "sci", ["direct_procurement"], 9, True, None, 2,
     "Emergency nutrition Kidal double derogation"),
    (25, "DGMP works, emergency bridge repair, Gao", "dgmp", "works", 40_000_000, "XOF", "Gao", True,
     ["dgmp", "works", "bridge", "emergency", "gao"],
     "dgmp", ["entente_directe"], 9, True, None, 1,
     "Emergency works Gao security zone"),

    # ── AOI (Appel Offres International) ─────────────────────────────────────
    (26, "DGMP AOI goods, high value, Bamako", "dgmp", "goods", 500_000_000, "XOF", "Bamako", False,
     ["dgmp", "goods", "aoi", "very_high_value"],
     "dgmp", ["appel_offres_international"], 9, True, 0, None,
     "DGMP AOI above international threshold"),
    (27, "SCI AOI services, Bamako, USD 500k", "sci", "services", 500_000, "USD", "Bamako", False,
     ["sci", "services", "aoi", "very_high_value"],
     "sci", ["open_international"], 9, True, 0, None,
     "SCI open international services"),
    (28, "DGMP AOI works, construction, Bamako, 1B XOF", "dgmp", "works", 1_000_000_000, "XOF", "Bamako", False,
     ["dgmp", "works", "aoi", "very_high_value", "construction"],
     "dgmp", ["appel_offres_international"], 9, True, 0, None,
     "DGMP billion XOF construction AOI"),

    # ── Edge cases: Menaka, Taoudenit ─────────────────────────────────────────
    (29, "SCI goods, Menaka, USD 12000, insecure zone", "sci", "goods", 12_000, "USD", "Menaka", False,
     ["sci", "goods", "menaka", "security"],
     "sci", ["request_for_quotation", "direct_procurement"], 9, True, None, 1,
     "Menaka security zone derogation"),
    (30, "DGMP services, Taoudenit, 6M XOF, remote", "dgmp", "services", 6_000_000, "XOF", "Taoudenit", False,
     ["dgmp", "services", "taoudenit", "remote", "security"],
     "dgmp", ["consultation_restreinte", "entente_directe"], 9, True, None, 1,
     "Taoudenit remote + security"),
    (31, "SCI works, Menaka, USD 80000, humanitarian", "sci", "works", 80_000, "USD", "Menaka", True,
     ["sci", "works", "menaka", "humanitarian", "security"],
     "sci", ["direct_procurement", "request_for_quotation"], 9, True, None, 2,
     "Menaka humanitarian works double derogation"),

    # ── Framework boundary / threshold edge cases ────────────────────────────
    (32, "SCI goods, USD 24999, just below ITB threshold", "sci", "goods", 24_999, "USD", "Bamako", False,
     ["sci", "goods", "threshold_edge", "below_itb"],
     "sci", ["request_for_quotation", "open_national"], 9, True, 0, None,
     "Just below ITB threshold — RFQ or national open"),
    (33, "SCI goods, USD 25001, just above ITB threshold", "sci", "goods", 25_001, "USD", "Bamako", False,
     ["sci", "goods", "threshold_edge", "above_itb"],
     "sci", ["open_national", "open_international"], 9, True, 0, None,
     "Just above ITB threshold — national or international open"),
    (34, "DGMP goods, 74999999 XOF, just below AOO threshold", "dgmp", "goods", 74_999_999, "XOF", "Bamako", False,
     ["dgmp", "goods", "threshold_edge", "below_aoo"],
     "dgmp", ["consultation_restreinte", "demande_cotation"], 9, True, 0, None,
     "Just below DGMP AOO threshold"),
    (35, "DGMP goods, 75000001 XOF, just above AOO threshold", "dgmp", "goods", 75_000_001, "XOF", "Bamako", False,
     ["dgmp", "goods", "threshold_edge", "above_aoo"],
     "dgmp", ["appel_offres_ouvert"], 9, True, 0, None,
     "Just above DGMP AOO threshold"),

    # ── Multi-lot procurement ─────────────────────────────────────────────────
    (36, "SCI goods multi-lot, Bamako, USD 45000 total", "sci", "goods", 45_000, "USD", "Bamako", False,
     ["sci", "goods", "multi_lot", "bamako"],
     "sci", ["open_national", "request_for_quotation"], 9, True, 0, None,
     "Multi-lot within open national threshold"),
    (37, "DGMP services multi-lot, Bamako, 200M XOF", "dgmp", "services", 200_000_000, "XOF", "Bamako", False,
     ["dgmp", "services", "multi_lot"],
     "dgmp", ["appel_offres_ouvert", "appel_offres_international"], 9, True, 0, None,
     "DGMP multi-lot services high value"),

    # ── Framework compliance edge cases ──────────────────────────────────────
    (38, "SCI goods, USD 0, pro bono donation", "sci", "goods", 0, "USD", "Bamako", False,
     ["sci", "goods", "zero_value", "donation"],
     "sci", ["direct_procurement"], 9, True, None, 1,
     "Zero value procurement / donation edge case"),
    (39, "DGMP services, 1 XOF symbolic", "dgmp", "services", 1, "XOF", "Bamako", False,
     ["dgmp", "services", "symbolic_value"],
     "dgmp", ["demande_cotation"], 9, True, 0, None,
     "Symbolic 1 XOF procurement"),
    (40, "SCI works, USD 15000, sanitation WASH", "sci", "works", 15_000, "USD", "Mopti", True,
     ["sci", "works", "wash", "sanitation", "humanitarian"],
     "sci", ["request_for_quotation", "direct_procurement"], 9, True, None, 1,
     "WASH humanitarian works Mopti"),

    # ── Sustainability scoring edge cases ─────────────────────────────────────
    (41, "SCI goods, USD 35000, green procurement", "sci", "goods", 35_000, "USD", "Bamako", False,
     ["sci", "goods", "green", "sustainability"],
     "sci", ["open_national", "open_international"], 9, True, 0, None,
     "Green procurement sustainability emphasis"),
    (42, "DGMP goods, 80M XOF, local preference", "dgmp", "goods", 80_000_000, "XOF", "Bamako", False,
     ["dgmp", "goods", "local_preference"],
     "dgmp", ["appel_offres_ouvert"], 9, True, 0, None,
     "DGMP local preference clause in AOO"),

    # ── Derogation complex cases ──────────────────────────────────────────────
    (43, "SCI goods, USD 20000, sole source + humanitarian", "sci", "goods", 20_000, "USD", "Bamako", True,
     ["sci", "goods", "sole_source", "humanitarian"],
     "sci", ["direct_procurement"], 9, True, None, 2,
     "Sole source AND humanitarian = 2 derogations"),
    (44, "SCI services, USD 60000, single source consultant", "sci", "services", 60_000, "USD", "Bamako", False,
     ["sci", "services", "single_source"],
     "sci", ["open_national", "direct_procurement"], 9, True, None, 1,
     "Single source specialist consultant"),
    (45, "DGMP works, 90M XOF, Kidal urgent repair", "dgmp", "works", 90_000_000, "XOF", "Kidal", True,
     ["dgmp", "works", "kidal", "urgent", "security", "humanitarian"],
     "dgmp", ["entente_directe"], 9, True, None, 2,
     "Kidal + emergency = maximum derogation DGMP"),

    # ── Validation / rejection edge cases ────────────────────────────────────
    (46, "SCI goods, negative value edge test", "sci", "goods", -1, "USD", "Bamako", False,
     ["sci", "goods", "invalid_value"],
     "sci", ["request_for_quotation"], 9, True, 0, None,
     "Negative value treated as unknown — fallback to lowest tier"),
    (47, "DGMP unknown zone, 50M XOF", "dgmp", "goods", 50_000_000, "XOF", "Unknown", False,
     ["dgmp", "goods", "unknown_zone"],
     "dgmp", ["appel_offres_ouvert"], 9, True, 0, None,
     "Unknown zone — no security derogation"),

    # ── Mixed currency edge cases ─────────────────────────────────────────────
    (48, "DGMP goods EUR 50000 imported", "dgmp", "goods", 50_000, "EUR", "Bamako", False,
     ["dgmp", "goods", "eur", "imported"],
     "dgmp", ["appel_offres_ouvert", "appel_offres_international"], 9, True, 0, None,
     "EUR denomination — converted to XOF equivalent for threshold"),

    # ── Final comprehensive edge cases ───────────────────────────────────────
    (49, "SCI services Bamako, USD 1000000, programme-level contract", "sci", "services", 1_000_000, "USD", "Bamako", False,
     ["sci", "services", "programme_level", "very_high_value"],
     "sci", ["open_international"], 9, True, 0, None,
     "Programme-level contract USD 1M open international"),
    (50, "DGMP works Gao 250M XOF humanitarian infrastructure", "dgmp", "works", 250_000_000, "XOF", "Gao", True,
     ["dgmp", "works", "gao", "humanitarian", "security", "infrastructure"],
     "dgmp", ["appel_offres_restreint", "entente_directe"], 9, True, None, 2,
     "Gao humanitarian infrastructure — security + emergency = 2 derogations"),
]


def write_case(n, desc, framework, family, value, currency, zone, humanitarian, tags):
    path = CASES_DIR / f"case_{n:03d}.json"
    data = {
        "case_id": f"GOLDEN-{n:03d}",
        "description": desc,
        "framework": framework,
        "procurement_family": family,
        "estimated_value": value,
        "currency": currency,
        "zone": zone,
        "humanitarian_context": humanitarian,
        "tags": tags,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {path.name}")


def write_expected(n, case_id, exp_framework, procedure_types, principles_count,
                   sustainability, derog_count, derog_gte, notes):
    path = EXPECTED_DIR / f"case_{n:03d}_expected.json"
    data: dict = {
        "case_id": case_id,
        "expected_framework": exp_framework,
        "expected_procedure_type_in": procedure_types,
        "expected_principles_count": principles_count,
        "expected_sustainability_present": sustainability,
        "notes": notes,
    }
    if derog_count is not None:
        data["expected_derogation_count"] = derog_count
    if derog_gte is not None:
        data["expected_derogation_count_gte"] = derog_gte
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {path.name}")


def main():
    print("Generating golden dataset cases 011-050 ...")
    for entry in ENTRIES:
        (n, desc, framework, family, value, currency, zone, humanitarian, tags,
         exp_framework, procedure_types, principles_count, sustainability,
         derog_count, derog_gte, notes) = entry

        write_case(n, desc, framework, family, value, currency, zone, humanitarian, tags)
        write_expected(n, f"GOLDEN-{n:03d}", exp_framework, procedure_types,
                       principles_count, sustainability, derog_count, derog_gte, notes)

    print(f"\nDone — {len(ENTRIES)} cases generated.")


if __name__ == "__main__":
    main()
