-- Rollback of 043_reference_store. NOT discovered by the migration runner (it reads infra/postgres/*.sql only).
-- Run by hand, inside one transaction, only with the owner's approval: it DELETES every reference card, offer,
-- rejection, alert and collect request. Touches nothing outside the seven tables 043 creates.
BEGIN;
DROP INDEX IF EXISTS idx_collect_queue_open;
DROP INDEX IF EXISTS idx_offer_rejections_brief;
DROP INDEX IF EXISTS idx_offer_rejections_category;
DROP INDEX IF EXISTS idx_reference_offers_category;
DROP INDEX IF EXISTS idx_reference_cards_category;
DROP TABLE IF EXISTS collect_queue;
DROP TABLE IF EXISTS offer_alerts;
DROP TABLE IF EXISTS offer_rejections;
DROP TABLE IF EXISTS reference_offers;
DROP TABLE IF EXISTS category_adjacency;
DROP TABLE IF EXISTS reference_card_components;
DROP TABLE IF EXISTS reference_cards;
DELETE FROM schema_migrations WHERE version = 43;
COMMIT;
