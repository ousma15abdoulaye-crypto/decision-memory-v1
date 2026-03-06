#!/usr/bin/env python3
"""
Seed taxonomie L1/L2/L3 · idempotent · ON CONFLICT DO NOTHING.
IDs stables · lisibles terrain · audit-proof.
REGLE-T01 · REGLE-T02.

Usage :
    $env:DATABASE_URL = "<Railway>"
    python scripts/seed_taxonomy_v2.py
    python scripts/seed_taxonomy_v2.py --verify
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace(
    "postgresql+psycopg://", "postgresql://"
)
if not DATABASE_URL:
    sys.exit("[KO] DATABASE_URL manquante")

# ------------------------------------------------------------------
# TAXONOMIE CANON · SOURCE DE VERITE
# ------------------------------------------------------------------
L1_DOMAINS = [
    ("ALIM_VIVRES", "Alimentation & vivres", 1),
    ("CARB_LUB", "Carburants & lubrifiants", 2),
    ("SANTE", "Sante & biomedical", 3),
    ("NUTRITION", "Nutrition (dont therapeutique)", 4),
    ("WASH", "Eau / hygiene / assainissement", 5),
    ("TRAVAUX_CONST", "Travaux & Construction", 6),
    ("ENERGIE_ELEC", "Energie & electricite", 7),
    ("IT_TELECOM", "Informatique & Telecom", 8),
    ("VEHIC_TRANSPORT", "Vehicules & transport", 9),
    ("NFI_MENAGE", "NFI / Articles menagers essentiels", 10),
    ("SECURITE_EPI", "Securite / surete / EPI", 11),
    ("COMM_MEDIAS", "Communication, medias, impression", 12),
    ("LOG_ENTREPOSAGE", "Logistique, entreposage, manutention", 13),
    ("SERVICES_GEN", "Services generaux", 14),
    ("SERVICES_PRO", "Services professionnels", 15),
]

L2_FAMILIES = [
    ("CEREALES_LEG", "ALIM_VIVRES", "Cereales & legumineuses", 1),
    ("HUILES_GRAISSES", "ALIM_VIVRES", "Huiles & graisses alimentaires", 2),
    ("CONDIMENTS", "ALIM_VIVRES", "Condiments & conserves", 3),
    ("EAU_BOISSONS", "ALIM_VIVRES", "Eau & boissons", 4),
    ("CARBURANTS", "CARB_LUB", "Carburants", 1),
    ("LUBRIFIANTS", "CARB_LUB", "Lubrifiants & fluides", 2),
    ("MEDICAMENTS", "SANTE", "Medicaments essentiels", 1),
    ("CONSOMM_MED", "SANTE", "Consommables medicaux", 2),
    ("EQUIP_MED", "SANTE", "Equipements medicaux", 3),
    ("LAB_REACTIFS", "SANTE", "Laboratoire & reactifs", 4),
    ("NUTRI_THERAP", "NUTRITION", "Nutrition therapeutique", 1),
    ("NUTRI_SUPPL", "NUTRITION", "Supplements nutritionnels", 2),
    ("TRAITEMENT_EAU", "WASH", "Traitement & stockage eau", 1),
    ("HYGIENE", "WASH", "Articles d'hygiene", 2),
    ("ASSAINISSEMENT", "WASH", "Equipements assainissement", 3),
    ("MAT_LIANTS", "TRAVAUX_CONST", "Materiaux liants", 1),
    ("MAT_FERRAILLAGE", "TRAVAUX_CONST", "Ferraillage & acier", 2),
    ("MAT_AGREGATS", "TRAVAUX_CONST", "Agregats & granulats", 3),
    ("MAT_MACONNERIE", "TRAVAUX_CONST", "Materiaux de maconnerie", 4),
    ("MAT_COUVERTURE", "TRAVAUX_CONST", "Couverture & etancheite", 5),
    ("MAT_BOIS", "TRAVAUX_CONST", "Bois & menuiserie", 6),
    ("MAT_PLOMBERIE", "TRAVAUX_CONST", "Plomberie & sanitaire", 7),
    ("MAT_ELECTRICITE", "TRAVAUX_CONST", "Electricite de batiment", 8),
    ("MAT_PEINTURE", "TRAVAUX_CONST", "Peinture & finitions", 9),
    ("SERV_CONST", "TRAVAUX_CONST", "Services de construction", 10),
    ("SOLAIRE", "ENERGIE_ELEC", "Energie solaire", 1),
    ("GROUPE_ELEC", "ENERGIE_ELEC", "Groupes electrogenes", 2),
    ("ELEC_RESEAU", "ENERGIE_ELEC", "Electricite reseau", 3),
    ("HARDWARE", "IT_TELECOM", "Materiel informatique", 1),
    ("PERIPHERIQUES", "IT_TELECOM", "Peripheriques", 2),
    ("TELECOM", "IT_TELECOM", "Telecommunication", 3),
    ("SOFT_LICENCES", "IT_TELECOM", "Logiciels & licences", 4),
    ("SERVICES_IT", "IT_TELECOM", "Services IT", 5),
    ("VEHIC_LEGERS", "VEHIC_TRANSPORT", "Vehicules legers", 1),
    ("VEHIC_LOURDS", "VEHIC_TRANSPORT", "Vehicules lourds", 2),
    ("DEUX_ROUES", "VEHIC_TRANSPORT", "Deux-roues", 3),
    ("PIECES_AUTO", "VEHIC_TRANSPORT", "Pieces detachees auto", 4),
    ("ABRIS", "NFI_MENAGE", "Articles d'abri", 1),
    ("MENAGE_BASE", "NFI_MENAGE", "Articles menagers de base", 2),
    ("HABILLEMENT", "NFI_MENAGE", "Habillement & chaussures", 3),
    ("EPI", "SECURITE_EPI", "Equipements de protection", 1),
    ("SECURITE_SITE", "SECURITE_EPI", "Securite de site", 2),
    ("PRESSE_ABO", "COMM_MEDIAS", "Presse & abonnements medias", 1),
    ("IMPRESSION", "COMM_MEDIAS", "Impression & reprographie", 2),
    ("PROMO_COMM", "COMM_MEDIAS", "Promotion & communication", 3),
    ("PROD_CONTENUS", "COMM_MEDIAS", "Production de contenus", 4),
    ("EMBALLAGE", "LOG_ENTREPOSAGE", "Emballage & conditionnement", 1),
    ("MANUTENTION", "LOG_ENTREPOSAGE", "Manutention & stockage", 2),
    ("TRANSPORT_SERV", "LOG_ENTREPOSAGE", "Services de transport", 3),
    ("NETTOYAGE", "SERVICES_GEN", "Nettoyage & hygiene locaux", 1),
    ("CATERING", "SERVICES_GEN", "Restauration & catering", 2),
    ("MAINTENANCE_GEN", "SERVICES_GEN", "Maintenance generale", 3),
    ("DIVERS", "SERVICES_GEN", "Divers", 4),
    ("AUDIT_CONSEIL", "SERVICES_PRO", "Audit & conseil", 1),
    ("INGENIERIE", "SERVICES_PRO", "Ingenierie & etudes", 2),
    ("FORMATION", "SERVICES_PRO", "Formation & renforcement", 3),
    ("EVENEMENTIEL", "SERVICES_PRO", "Evenementiel & location", 4),
]

L3_SUBFAMILIES = [
    ("riz", "CEREALES_LEG", "Riz", 1),
    ("mais", "CEREALES_LEG", "Mais", 2),
    ("mil_sorgho", "CEREALES_LEG", "Mil & sorgho", 3),
    ("legumineuses", "CEREALES_LEG", "Legumineuses", 4),
    ("huile_alim", "HUILES_GRAISSES", "Huiles alimentaires", 1),
    ("beurre_karite", "HUILES_GRAISSES", "Beurre de karite", 2),
    ("sel_sucre", "CONDIMENTS", "Sel & sucre", 1),
    ("conserves", "CONDIMENTS", "Conserves & condiments", 2),
    ("eau_potable", "EAU_BOISSONS", "Eau potable", 1),
    ("boissons", "EAU_BOISSONS", "Boissons & lait", 2),
    ("gasoil", "CARBURANTS", "Gasoil", 1),
    ("essence", "CARBURANTS", "Essence super", 2),
    ("jet_a1", "CARBURANTS", "Jet A-1", 3),
    ("petrole_lamp", "CARBURANTS", "Petrole lampant", 4),
    ("huile_moteur", "LUBRIFIANTS", "Huile moteur", 1),
    ("huile_hydraulique", "LUBRIFIANTS", "Huile hydraulique", 2),
    ("graisse_lubr", "LUBRIFIANTS", "Graisses lubrifiantes", 3),
    ("antipaludeens", "MEDICAMENTS", "Antipaludeens", 1),
    ("antibiotiques", "MEDICAMENTS", "Antibiotiques", 2),
    ("analgesiques", "MEDICAMENTS", "Analgesiques", 3),
    ("vaccins_serums", "MEDICAMENTS", "Vaccins & serums", 4),
    ("arv", "MEDICAMENTS", "Antiretroviraux", 5),
    ("injectables", "CONSOMM_MED", "Injectables & perfusion", 1),
    ("protection", "CONSOMM_MED", "Protection & pansements", 2),
    ("diagnostic_cons", "CONSOMM_MED", "Consommables diagnostic", 3),
    ("diagnostic_equip", "EQUIP_MED", "Equipements diagnostic", 1),
    ("hospitalier", "EQUIP_MED", "Equipements hospitaliers", 2),
    ("urgence", "EQUIP_MED", "Urgence & chirurgie", 3),
    ("tests_rapides", "LAB_REACTIFS", "Tests rapides", 1),
    ("reactifs_bio", "LAB_REACTIFS", "Reactifs biologiques", 2),
    ("rutf", "NUTRI_THERAP", "RUTF (Plumpy Nut etc.)", 1),
    ("f75_f100", "NUTRI_THERAP", "F75 / F100", 2),
    ("csb_plus", "NUTRI_THERAP", "CSB+", 3),
    ("vitamines", "NUTRI_SUPPL", "Vitamines", 1),
    ("mineraux", "NUTRI_SUPPL", "Mineraux & oligo", 2),
    ("chloration", "TRAITEMENT_EAU", "Chloration", 1),
    ("stockage_eau", "TRAITEMENT_EAU", "Stockage eau", 2),
    ("pompage", "TRAITEMENT_EAU", "Pompage & forage", 3),
    ("savon_detergent", "HYGIENE", "Savon & detergent", 1),
    ("desinfectant", "HYGIENE", "Desinfectants", 2),
    ("latrines", "ASSAINISSEMENT", "Latrines & sanitaires", 1),
    ("reseau_assain", "ASSAINISSEMENT", "Reseau assainissement", 2),
    ("ciment", "MAT_LIANTS", "Ciment", 1),
    ("chaux_platre", "MAT_LIANTS", "Chaux & platre", 2),
    ("mortier_enduit", "MAT_LIANTS", "Mortier & enduit", 3),
    ("fer_ha", "MAT_FERRAILLAGE", "Fer a beton HA", 1),
    ("fer_rond", "MAT_FERRAILLAGE", "Fer rond", 2),
    ("profiles_acier", "MAT_FERRAILLAGE", "Profiles acier", 3),
    ("treillis", "MAT_FERRAILLAGE", "Treillis soude", 4),
    ("sable", "MAT_AGREGATS", "Sable", 1),
    ("gravier", "MAT_AGREGATS", "Gravier", 2),
    ("moellon_laterite", "MAT_AGREGATS", "Moellon & laterite", 3),
    ("parpaing_agglo", "MAT_MACONNERIE", "Parpaings & agglos", 1),
    ("brique", "MAT_MACONNERIE", "Briques", 2),
    ("hourdis_dalle", "MAT_MACONNERIE", "Hourdis & dalles", 3),
    ("tole_ondulee", "MAT_COUVERTURE", "Tole ondulee", 1),
    ("tuile", "MAT_COUVERTURE", "Tuile", 2),
    ("etancheite", "MAT_COUVERTURE", "Etancheite", 3),
    ("planche_sciee", "MAT_BOIS", "Planches sciees", 1),
    ("chevron_madrier", "MAT_BOIS", "Chevrons & madriers", 2),
    ("contre_plaque", "MAT_BOIS", "Contre-plaque", 3),
    ("tuyau_pvc", "MAT_PLOMBERIE", "Tuyaux PVC", 1),
    ("tuyau_galva", "MAT_PLOMBERIE", "Tuyaux galva", 2),
    ("robinetterie", "MAT_PLOMBERIE", "Robinetterie", 3),
    ("sanitaire", "MAT_PLOMBERIE", "Sanitaires", 4),
    ("cable_elec", "MAT_ELECTRICITE", "Cables electriques", 1),
    ("appareillage", "MAT_ELECTRICITE", "Appareillage", 2),
    ("tableau_elec", "MAT_ELECTRICITE", "Tableaux electriques", 3),
    ("peinture", "MAT_PEINTURE", "Peinture", 1),
    ("vernis_laque", "MAT_PEINTURE", "Vernis & laques", 2),
    ("enduit_lissage", "MAT_PEINTURE", "Enduits de lissage", 3),
    ("etudes_diagnostic", "SERV_CONST", "Etudes & diagnostics", 1),
    ("topographie", "SERV_CONST", "Topographie & terrain", 2),
    ("supervision", "SERV_CONST", "Supervision & controle", 3),
    ("rehabilitation", "SERV_CONST", "Rehabilitation", 4),
    ("location_engins", "SERV_CONST", "Location engins & MO", 5),
    ("panneau_solaire", "SOLAIRE", "Panneaux solaires", 1),
    ("batterie_solaire", "SOLAIRE", "Batteries solaires", 2),
    ("onduleur_reg", "SOLAIRE", "Onduleurs & regulateurs", 3),
    ("groupe_elec", "GROUPE_ELEC", "Groupes electrogenes", 1),
    ("pieces_groupe", "GROUPE_ELEC", "Pieces & entretien", 2),
    ("cablage_hta", "ELEC_RESEAU", "Cablage HTA", 1),
    ("transformateur", "ELEC_RESEAU", "Transformateurs", 2),
    ("ordinateur", "HARDWARE", "Ordinateurs", 1),
    ("serveur", "HARDWARE", "Serveurs", 2),
    ("stockage_info", "HARDWARE", "Stockage informatique", 3),
    ("impression", "PERIPHERIQUES", "Impression", 1),
    ("projection", "PERIPHERIQUES", "Projection & affichage", 2),
    ("alimentation_info", "PERIPHERIQUES", "Alimentation info (UPS)", 3),
    ("mobile_tablette", "TELECOM", "Mobile & tablette", 1),
    ("reseau_telecom", "TELECOM", "Reseau & connectivite", 2),
    ("radio_satcom", "TELECOM", "Radio & satcom", 3),
    ("os_bureau", "SOFT_LICENCES", "OS & bureautique", 1),
    ("securite_info", "SOFT_LICENCES", "Securite informatique", 2),
    ("saas_cloud", "SOFT_LICENCES", "SaaS & cloud", 3),
    ("maintenance_it", "SERVICES_IT", "Maintenance IT", 1),
    ("cablage_reseau", "SERVICES_IT", "Cablage reseau", 2),
    ("formation_it", "SERVICES_IT", "Formation IT", 3),
    ("4x4", "VEHIC_LEGERS", "4x4 & station wagon", 1),
    ("pick_up", "VEHIC_LEGERS", "Pick-up", 2),
    ("minibus", "VEHIC_LEGERS", "Minibus", 3),
    ("camion", "VEHIC_LOURDS", "Camions", 1),
    ("remorque", "VEHIC_LOURDS", "Remorques", 2),
    ("engin_tp", "VEHIC_LOURDS", "Engins TP", 3),
    ("moto", "DEUX_ROUES", "Motos", 1),
    ("velo", "DEUX_ROUES", "Velos", 2),
    ("pneumatiques", "PIECES_AUTO", "Pneumatiques", 1),
    ("filtres_consomm", "PIECES_AUTO", "Filtres & consommables", 2),
    ("pieces_meca", "PIECES_AUTO", "Pieces mecaniques", 3),
    ("bache_tente", "ABRIS", "Baches & tentes", 1),
    ("kit_abri", "ABRIS", "Kits abri", 2),
    ("literie", "MENAGE_BASE", "Literie", 1),
    ("ustensiles", "MENAGE_BASE", "Ustensiles", 2),
    ("jerrycan_seau", "MENAGE_BASE", "Jerrycans & seaux", 3),
    ("vetements", "HABILLEMENT", "Vetements", 1),
    ("chaussures", "HABILLEMENT", "Chaussures", 2),
    ("protection_tete", "EPI", "Protection tete", 1),
    ("protection_corps", "EPI", "Protection corps", 2),
    ("protection_pieds", "EPI", "Protection pieds", 3),
    ("surveillance", "SECURITE_SITE", "Surveillance", 1),
    ("controle_acces", "SECURITE_SITE", "Controle d'acces", 2),
    ("incendie", "SECURITE_SITE", "Lutte incendie", 3),
    ("journaux_locaux", "PRESSE_ABO", "Journaux locaux", 1),
    ("presse_internat", "PRESSE_ABO", "Presse internationale", 2),
    ("revues_pro", "PRESSE_ABO", "Revues professionnelles", 3),
    ("impression_offset", "IMPRESSION", "Impression offset", 1),
    ("consomm_impression", "IMPRESSION", "Consommables impression", 2),
    ("materiel_comm", "PROMO_COMM", "Materiel de comm", 1),
    ("evenements_comm", "PROMO_COMM", "Evenements comm", 2),
    ("photo_video", "PROD_CONTENUS", "Photo & video", 1),
    ("design_redac", "PROD_CONTENUS", "Design & redaction", 2),
    ("sacs_cartons", "EMBALLAGE", "Sacs & cartons", 1),
    ("palette_film", "EMBALLAGE", "Palettes & film", 2),
    ("materiel_stock", "MANUTENTION", "Materiel stockage", 1),
    ("pesage", "MANUTENTION", "Pesage & mesure", 2),
    ("location_vehic", "TRANSPORT_SERV", "Location vehicules", 1),
    ("fret", "TRANSPORT_SERV", "Fret & messagerie", 2),
    ("produits_nett", "NETTOYAGE", "Produits nettoyage", 1),
    ("prestation_nett", "NETTOYAGE", "Prestation nettoyage", 2),
    ("repas_bureau", "CATERING", "Repas & pauses", 1),
    ("traiteur", "CATERING", "Traiteur evenements", 2),
    ("maintenance_clim", "MAINTENANCE_GEN", "Maintenance climatisation", 1),
    ("maintenance_plomb", "MAINTENANCE_GEN", "Maintenance plomberie", 2),
    ("maintenance_mob", "MAINTENANCE_GEN", "Maintenance mobilier", 3),
    ("DIVERS_NON_CLASSE", "DIVERS", "Divers non classe", 1),
    ("audit_financier", "AUDIT_CONSEIL", "Audit financier", 1),
    ("conseil_juridique", "AUDIT_CONSEIL", "Conseil juridique", 2),
    ("expertise_compta", "AUDIT_CONSEIL", "Expertise comptable", 3),
    ("etude_faisab", "INGENIERIE", "Etude de faisabilite", 1),
    ("eval_projet", "INGENIERIE", "Evaluation de projet", 2),
    ("ingenierie_syst", "INGENIERIE", "Ingenierie systemes", 3),
    ("formation_metier", "FORMATION", "Formation metier", 1),
    ("atelier_conf", "FORMATION", "Ateliers & conferences", 2),
    ("location_salle", "EVENEMENTIEL", "Location salle", 1),
    ("organisation_evt", "EVENEMENTIEL", "Organisation evenement", 2),
]


def seed(conn: psycopg.Connection) -> dict:
    stats = {"l1": 0, "l2": 0, "l3": 0}

    with conn.transaction():
        for domain_id, label_fr, sort_order in L1_DOMAINS:
            conn.execute(
                """
                INSERT INTO couche_b.taxo_l1_domains
                    (domain_id, label_fr, sort_order)
                VALUES (%s, %s, %s)
                ON CONFLICT (domain_id) DO NOTHING
                """,
                (domain_id, label_fr, sort_order),
            )
            stats["l1"] += 1

        for family_l2_id, domain_id, label_fr, sort_order in L2_FAMILIES:
            conn.execute(
                """
                INSERT INTO couche_b.taxo_l2_families
                    (family_l2_id, domain_id, label_fr, sort_order)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (family_l2_id) DO NOTHING
                """,
                (family_l2_id, domain_id, label_fr, sort_order),
            )
            stats["l2"] += 1

        for subfamily_id, family_l2_id, label_fr, sort_order in L3_SUBFAMILIES:
            conn.execute(
                """
                INSERT INTO couche_b.taxo_l3_subfamilies
                    (subfamily_id, family_l2_id, label_fr, sort_order)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (subfamily_id) DO NOTHING
                """,
                (subfamily_id, family_l2_id, label_fr, sort_order),
            )
            stats["l3"] += 1

    return stats


def verify(conn: psycopg.Connection) -> bool:
    ok = True
    print("\n--- VERIFICATION TAXONOMIE ---")

    r = conn.execute("SELECT COUNT(*) AS n FROM couche_b.taxo_l1_domains").fetchone()
    status = "[OK]" if r["n"] == len(L1_DOMAINS) else "[KO] STOP-T2"
    print(f"  L1 : {r['n']}/{len(L1_DOMAINS)} {status}")
    if r["n"] != len(L1_DOMAINS):
        ok = False

    r = conn.execute("SELECT COUNT(*) AS n FROM couche_b.taxo_l2_families").fetchone()
    status = "[OK]" if r["n"] == len(L2_FAMILIES) else "[KO]"
    print(f"  L2 : {r['n']}/{len(L2_FAMILIES)} {status}")
    if r["n"] != len(L2_FAMILIES):
        ok = False

    r = conn.execute(
        "SELECT COUNT(*) AS n FROM couche_b.taxo_l3_subfamilies"
    ).fetchone()
    status = "[OK]" if r["n"] == len(L3_SUBFAMILIES) else "[KO]"
    print(f"  L3 : {r['n']}/{len(L3_SUBFAMILIES)} {status}")
    if r["n"] != len(L3_SUBFAMILIES):
        ok = False

    r = conn.execute("""
        SELECT COUNT(*) AS n FROM couche_b.taxo_l2_families l2
        LEFT JOIN couche_b.taxo_l1_domains l1
            ON l2.domain_id = l1.domain_id
        WHERE l1.domain_id IS NULL
    """).fetchone()
    if r["n"] > 0:
        print(f"  [KO] STOP-T3 · {r['n']} L2 sans L1")
        ok = False
    else:
        print("  [OK] FK L2->L1 coherentes")

    r = conn.execute("""
        SELECT COUNT(*) AS n FROM couche_b.taxo_l3_subfamilies l3
        LEFT JOIN couche_b.taxo_l2_families l2
            ON l3.family_l2_id = l2.family_l2_id
        WHERE l2.family_l2_id IS NULL
    """).fetchone()
    if r["n"] > 0:
        print(f"  [KO] STOP-T4 · {r['n']} L3 sans L2")
        ok = False
    else:
        print("  [OK] FK L3->L2 coherentes")

    r = conn.execute("""
        SELECT COUNT(*) AS n FROM couche_b.taxo_l3_subfamilies
        WHERE subfamily_id = 'DIVERS_NON_CLASSE'
    """).fetchone()
    status = "[OK]" if r["n"] == 1 else "[KO] DIVERS_NON_CLASSE manquant"
    print(f"  Residuel DIVERS_NON_CLASSE : {status}")
    if r["n"] != 1:
        ok = False

    return ok


def main(do_verify: bool) -> None:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:

        if do_verify:
            ok = verify(conn)
            sys.exit(0 if ok else 1)

        print("Insertion taxonomie L1/L2/L3...")
        stats = seed(conn)
        print(f"  L1 tentés (ON CONFLICT DO NOTHING) : {stats['l1']}")
        print(f"  L2 tentés (ON CONFLICT DO NOTHING) : {stats['l2']}")
        print(f"  L3 tentés (ON CONFLICT DO NOTHING) : {stats['l3']}")

        ok = verify(conn)
        if not ok:
            sys.exit(1)

        print("\n[OK] Seed taxonomie termine · STOP · poster · GO TL")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    main(args.verify)
