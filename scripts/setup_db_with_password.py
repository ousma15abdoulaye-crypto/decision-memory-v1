#!/usr/bin/env python3
"""
DMS Database Setup — Crée la base avec le mot de passe fourni.
Usage: python scripts/setup_db_with_password.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import psycopg
    from psycopg import sql
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg[binary]", file=sys.stderr)
    sys.exit(1)


def try_create_db(
    password: str,
    superuser: str = "postgres",
    host: str = "localhost",
    port: int = 5432,
    db_name: str = "dms",
    db_user: str = "dms",
    db_password: str = "dms_dev_password_change_me",
) -> bool:
    """Essaie de créer la DB avec le mot de passe fourni."""
    
    print(f"[*] Tentative de connexion avec l'utilisateur '{superuser}'...")
    
    try:
        # Essayer de se connecter en tant que superuser
        admin_conn = psycopg.connect(
            f"postgresql://{superuser}:{password}@{host}:{port}/postgres"
        )
        admin_conn.autocommit = True
        print(f"[OK] Connexion reussie avec '{superuser}'!")
        
        with admin_conn.cursor() as cur:
            # Créer le rôle
            print(f"[*] Creation du role '{db_user}'...")
            cur.execute(
                sql.SQL("""
                    DO $$
                    BEGIN
                      IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s) THEN
                        CREATE ROLE {} LOGIN PASSWORD %s;
                      ELSE
                        ALTER ROLE {} PASSWORD %s;
                      END IF;
                    END$$;
                """).format(
                    sql.Identifier(db_user),
                    sql.Identifier(db_user)
                ),
                (db_user, db_password, db_password)
            )
            print(f"[OK] Role '{db_user}' cree/mis a jour")
            
            # Créer la base
            print(f"[*] Creation de la base '{db_name}'...")
            try:
                cur.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(db_name),
                        sql.Identifier(db_user)
                    )
                )
                print(f"[OK] Base '{db_name}' creee")
            except psycopg.errors.DuplicateDatabase:
                print(f"[WARN] Base '{db_name}' existe deja, on continue...")
            
        admin_conn.close()
        
        # Se connecter en tant que db_user pour activer l'extension
        print(f"[*] Activation de l'extension pg_trgm...")
        user_conn = psycopg.connect(
            f"postgresql://{db_user}:{db_password}@{host}:{port}/{db_name}"
        )
        user_conn.autocommit = True
        
        with user_conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            print("[OK] Extension pg_trgm activee")
        
        user_conn.close()
        
        print("\n" + "="*70)
        print("[OK] SETUP COMPLET!")
        print("="*70)
        print(f"Base de donnees: {db_name}")
        print(f"Utilisateur: {db_user}")
        print(f"Mot de passe: {db_password}")
        print(f"\nDATABASE_URL pour le fichier .env:")
        print(f"postgresql+psycopg://{db_user}:{db_password}@{host}:{port}/{db_name}")
        print("="*70)
        
        return True
        
    except psycopg.OperationalError as e:
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"[ERREUR] Echec de connexion: {error_msg}")
        return False
    except Exception as e:
        error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"[ERREUR] Erreur: {error_msg}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup DMS PostgreSQL avec mot de passe")
    parser.add_argument("--password", default="", help="Mot de passe PostgreSQL superuser (requis si non fourni via variable d'environnement PGPASSWORD)")
    parser.add_argument("--superuser", default="postgres", help="Nom de l'utilisateur superuser")
    parser.add_argument("--host", default="localhost", help="Host PostgreSQL")
    parser.add_argument("--port", type=int, default=5432, help="Port PostgreSQL")
    parser.add_argument("--db-name", default="dms", help="Nom de la base")
    parser.add_argument("--db-user", default="dms", help="Nom de l'utilisateur DB")
    parser.add_argument("--db-password", default="dms_dev_password_change_me", help="Mot de passe utilisateur DB")
    
    args = parser.parse_args()
    
    # Récupérer le mot de passe depuis l'argument ou la variable d'environnement
    password = args.password
    if not password:
        import os
        password = os.environ.get("PGPASSWORD", "")
        if not password:
            print("[ERREUR] Mot de passe requis. Fournissez-le via:")
            print("  --password 'votre_mot_de_passe'")
            print("  OU via variable d'environnement: $env:PGPASSWORD = 'votre_mot_de_passe'")
            sys.exit(1)
    
    # Essayer avec l'utilisateur fourni
    success = try_create_db(
        password=password,
        superuser=args.superuser,
        host=args.host,
        port=args.port,
        db_name=args.db_name,
        db_user=args.db_user,
        db_password=args.db_password,
    )
    
    if not success:
        print("\nSuggestions:")
        print("1. Verifie que PostgreSQL est demarre (Services Windows)")
        print("2. Verifie le nom d'utilisateur (peut-etre pas 'postgres'?)")
        print("3. Verifie le mot de passe")
        print("4. Essaie avec pgAdmin pour voir quel utilisateur fonctionne")
        sys.exit(1)
    
    sys.exit(0)
