ALTER TABLE orders ADD COLUMN IF NOT EXISTS deleted_at timestamptz;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS deleted_by text REFERENCES customers(id) ON DELETE SET NULL;
