-- Renommage préventif des tables hors périmètre DMS (Label Studio / Django / etc.).
-- EXÉCUTER UNIQUEMENT après inventaire sur LA base cible (pg_tables).
-- Idempotent : boucle DO $$ sur la liste cible + EXECUTE format(..., 'ALTER TABLE IF EXISTS ... RENAME TO ...').

DO $body$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename IN (
            'auth_group', 'auth_permission', 'django_migrations',
            'django_session', 'django_content_type', 'django_admin_log'
          )
    LOOP
        EXECUTE format(
            'ALTER TABLE IF EXISTS public.%I RENAME TO %I',
            r.tablename,
            '_deprecated_' || r.tablename
        );
    END LOOP;
END
$body$;

-- ROLLBACK : renommer manuellement _deprecated_* → nom d'origine.
