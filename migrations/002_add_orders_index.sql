-- 002_add_orders_index.sql
-- Optimizes query: SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC

CREATE INDEX IF NOT EXISTS idx_orders_user_created
ON orders(user_id, created_at DESC);
