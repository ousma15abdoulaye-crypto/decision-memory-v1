-- Idempotent alignment with migration 094_security_market_mercurial_tenant_rls.
-- Source de vérité : appliquer de préférence `alembic upgrade head` (revision 094).
-- Ce script sert de référence / secours si exécution SQL manuelle approuvée CTO.

-- Vérification rapide : colonne présente
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN (
    'market_surveys', 'mercurials', 'market_signals_v2',
    'offers', 'extractions', 'analysis_summaries', 'survey_campaigns'
  )
  AND column_name = 'tenant_id';

-- Les DDL complets sont dans :
--   alembic/versions/094_security_market_mercurial_tenant_rls.py
-- Ne pas dupliquer ici pour éviter dérive ; copier depuis la migration si besoin.
