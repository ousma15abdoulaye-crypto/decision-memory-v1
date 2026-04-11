-- Trigger append-only sur score_history (fn_reject_mutation public).
-- Idempotent — même logique que bloc DO $$ dans migration 094.

DO $body$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE p.proname = 'fn_reject_mutation' AND n.nspname = 'public'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        WHERE c.relname = 'score_history'
          AND t.tgname = 'trg_score_history_append_only'
    ) THEN
        CREATE TRIGGER trg_score_history_append_only
            BEFORE DELETE OR UPDATE ON public.score_history
            FOR EACH ROW
            EXECUTE FUNCTION public.fn_reject_mutation();
    END IF;
END
$body$;

-- ROLLBACK manuel :
-- DROP TRIGGER IF EXISTS trg_score_history_append_only ON public.score_history;
