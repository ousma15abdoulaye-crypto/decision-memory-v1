#!/usr/bin/env python3
"""Test pipeline V5 en local avec DB Railway"""
import json
import sys
import os
sys.path.insert(0, '.')

# DATABASE_URL pour la connexion
os.environ['DATABASE_URL'] = "postgresql://postgres:VvIxShbsVuwXdqGlipWTeZjfHKTEbFHP@maglev.proxy.rlwy.net:35451/railway"
os.environ['JWT_SECRET'] = "test-pipeline-v5-jwt-secret-minimum-32-characters-required-here"
os.environ['MISTRAL_API_KEY'] = "fake-key-for-pipeline-test"

def main():
    print(f'DB URL: {os.environ["DATABASE_URL"][:60]}...')

    try:
        from src.services.pipeline_v5_service import run_pipeline_v5

        workspace_id = 'f1a6edfb-ac50-4301-a1a9-7a80053c632a'
        print(f'\nRunning pipeline V5 for workspace: {workspace_id}')
        print('=' * 60)

        result = run_pipeline_v5(workspace_id)

        print('\n=== RESULTAT PIPELINE V5 ===')
        print(json.dumps(result.model_dump(), indent=2, default=str))
        print('\n=== SUCCESS ===')

    except Exception as e:
        import traceback
        print('\n=== ERREUR ===')
        traceback.print_exc()
        print(f'\nERREUR: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
