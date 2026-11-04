CREATE TABLE orders (
    request_id uuid PRIMARY KEY,
    fingerprint text NOT NULL,
    number text NOT NULL UNIQUE,
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    status text NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'in_progress', 'completed', 'cancelled')),
    created timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX orders_status_created_idx ON orders (status, created DESC);

CREATE TABLE order_status_history (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    number text NOT NULL REFERENCES orders (number),
    previous text NOT NULL CHECK (previous IN ('new', 'in_progress', 'completed', 'cancelled')),
    current text NOT NULL CHECK (current IN ('new', 'in_progress', 'completed', 'cancelled')),
    changed timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX order_status_history_number_idx ON order_status_history (number, id);

CREATE TABLE order_notifications (
    number text PRIMARY KEY REFERENCES orders (number),
    sent_at timestamptz,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_attempt timestamptz,
    last_error text
);

CREATE INDEX order_notifications_pending_idx ON order_notifications (last_attempt, number)
    WHERE sent_at IS NULL;
