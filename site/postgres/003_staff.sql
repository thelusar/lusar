CREATE TABLE staff_roles (
    customer_id text PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('admin', 'manager'))
);

CREATE TABLE order_staff_activity (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    number text NOT NULL REFERENCES orders(number),
    actor_id text REFERENCES customers(id),
    actor_email text NOT NULL,
    action text NOT NULL CHECK (action IN ('status', 'payment', 'return', 'refund_paid')),
    detail text NOT NULL,
    changed timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX order_staff_activity_number_idx ON order_staff_activity(number, id DESC);
