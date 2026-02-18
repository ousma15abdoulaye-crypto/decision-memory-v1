#!/usr/bin/env python3
"""
Script ultra-simple pour créer la base de données DMS.
Essaie plusieurs combinaisons automatiquement.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
from psycopg import sql

def try_create_db():
    """Essaie de créer la DB avec différentes combinaisons."""
    
    # SECURITE: Ne pas hardcoder de mots de passe. Utiliser variable d'environnement ou prompt.
    import os
    passwords = [
        os.environ.get("PGPASSWORD", ""),
        "",  # Essayer sans mot de passe (trust local)
    ]
    users = ["postgres", "abdoulaye.ousmane"]
    
    db_name = "dms"
    db_user = "dms"
    db_password = "dms123"  # Simple pour dev
    
    print("="*60)
    print("Creation de la base de donnees DMS")
    print("="*60)
    print()
    
    for user in users:
        for pwd in passwords:
            print(f"Essai: utilisateur={user}, password={'***' if pwd else '(vide)'}")
            try:
                # Essayer de se connecter
                conn_str = f"postgresql://{user}:{pwd}@{'localhost'}:5432/postgres" if pwd else f"postgresql://{user}@localhost:5432/postgres"
                conn = psycopg.connect(conn_str)
                conn.autocommit = True
                
                print(f"[OK] Connexion reussie avec {user}!")
                
                with conn.cursor() as cur:
                    # Créer le rôle
                    print(f"Creation du role '{db_user}'...")
                    try:
                        cur.execute(
                            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                                sql.Identifier(db_user),
                                sql.Literal(db_password)
                            )
                        )
                        print(f"[OK] Role '{db_user}' cree")
                    except psycopg.errors.DuplicateObject:
                        print(f"[OK] Role '{db_user}' existe deja")
                    
                    # Créer la base
                    print(f"Creation de la base '{db_name}'...")
                    try:
                        cur.execute(
                            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                                sql.Identifier(db_name),
                                sql.Identifier(db_user)
                            )
                        )
                        print(f"[OK] Base '{db_name}' creee")
                    except psycopg.errors.DuplicateDatabase:
                        print(f"[OK] Base '{db_name}' existe deja")
                
                conn.close()
                
                # Se connecter en tant que dms pour activer l'extension
                print("Activation de l'extension pg_trgm...")
                user_conn = psycopg.connect(f"postgresql://{db_user}:{db_password}@localhost:5432/{db_name}")
                user_conn.autocommit = True
                
                with user_conn.cursor() as cur:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                    print("[OK] Extension pg_trgm activee")
                
                user_conn.close()
                
                print()
                print("="*60)
                print("[SUCCES] Base de donnees creee!")
                print("="*60)
                print(f"Database: {db_name}")
                print(f"User: {db_user}")
                print(f"Password: {db_password}")
                print()
                print("Mets a jour .env avec:")
                print(f"DATABASE_URL=postgresql+psycopg://{db_user}:{db_password}@localhost:5432/{db_name}")
                print("="*60)
                
                return True
                
            except psycopg.OperationalError:
                print(f"[ECHEC] Connexion impossible")
                continue
            except Exception as e:
                print(f"[ERREUR] {e}")
                continue
    
    print()
    print("="*60)
    print("[ECHEC] Impossible de se connecter a PostgreSQL")
    print("="*60)
    print()
    print("Solutions:")
    print("1. Utilise DBeaver pour te connecter manuellement")
    print("2. Verifie que PostgreSQL est demarre (Services Windows)")
    print("3. Reinitialise le mot de passe (voir RESET_PASSWORD.md)")
    print()
    return False

if __name__ == "__main__":
    success = try_create_db()
    sys.exit(0 if success else 1)
