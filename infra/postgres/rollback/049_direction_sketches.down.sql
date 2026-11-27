-- Rollback of 049_direction_sketches. NOT discovered by the migration runner (it reads infra/postgres/*.sql only).
-- Run by hand, inside one transaction, only with the owner's approval (CLAUDE.md section 5: backup branch first). It
-- DELETES the direction sketches (what was shown, who paid for its words, the pointer to the model call). The money of
-- those calls stays in intake_reservations and credit_reservations; this table holds no amount. Roll back the code that
-- reads the table FIRST: omni_prod/direction_sketch/store.py fails closed (the sketch routes answer 503) without it.
BEGIN;
DROP INDEX IF EXISTS direction_sketches_reservation;
DROP INDEX IF EXISTS direction_sketches_project_time;
DROP INDEX IF EXISTS direction_sketches_one_free;
DROP TABLE IF EXISTS direction_sketches;
DELETE FROM schema_migrations WHERE version = 49;
COMMIT;
