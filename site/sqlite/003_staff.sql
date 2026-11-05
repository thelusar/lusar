CREATE TABLE IF NOT EXISTS staff_roles (
    customer_id TEXT PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'manager'))
);

CREATE TABLE IF NOT EXISTS order_staff_activity (
    id INTEGER PRIMARY KEY,
    number TEXT NOT NULL REFERENCES orders(number),
    actor_id TEXT REFERENCES customers(id),
    actor_email TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('status', 'payment', 'return', 'refund_paid')),
    detail TEXT NOT NULL,
    changed TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS order_staff_activity_number_idx ON order_staff_activity(number, id DESC);
