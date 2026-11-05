CREATE TABLE customers (
    id text PRIMARY KEY,
    issuer text NOT NULL,
    subject text NOT NULL,
    email text NOT NULL,
    name text NOT NULL DEFAULT '',
    phone text NOT NULL DEFAULT '',
    addresses text NOT NULL DEFAULT '[]',
    created bigint NOT NULL,
    UNIQUE (issuer, subject)
);
CREATE TABLE customer_sessions (
    token_hash text PRIMARY KEY,
    customer_id text NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    expires bigint NOT NULL
);
CREATE INDEX customer_sessions_expiry_idx ON customer_sessions(expires);
CREATE TABLE customer_login_flows (
    state_hash text PRIMARY KEY,
    nonce text NOT NULL,
    verifier text NOT NULL,
    destination text NOT NULL,
    expires bigint NOT NULL
);
CREATE TABLE customer_state (
    customer_id text PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
    cart text NOT NULL DEFAULT '{}',
    favorites text NOT NULL DEFAULT '[]',
    version integer NOT NULL DEFAULT 0
);
ALTER TABLE orders ADD COLUMN customer_id text REFERENCES customers(id);
CREATE INDEX orders_customer_created_idx ON orders(customer_id, created DESC);
