-- 002_rollback.sql
-- Reverses 002_add_orders_index.sql

DROP INDEX IF EXISTS idx_orders_user_created;
