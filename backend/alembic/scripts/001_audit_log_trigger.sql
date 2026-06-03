-- 001_audit_log_trigger.sql
-- Append-only enforcement for audit_log table (defense-in-depth).
--
-- This trigger rejects any UPDATE or DELETE on the audit_log table,
-- ensuring that audit records are truly immutable regardless of
-- how someone connects to the database.
--
-- Part of C-05 audit-log change.

CREATE OR REPLACE FUNCTION fn_audit_log_prevent_modifications()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE are not allowed'
        USING HINT = 'Audit records cannot be modified or deleted';
END;
$$;

CREATE TRIGGER trg_audit_log_append_only
    BEFORE UPDATE OR DELETE
    ON audit_log
    FOR EACH ROW
    EXECUTE FUNCTION fn_audit_log_prevent_modifications();
