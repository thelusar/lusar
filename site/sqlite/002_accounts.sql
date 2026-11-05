CREATE TABLE IF NOT EXISTS orders (
    request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
    number TEXT NOT NULL UNIQUE, payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new', created TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY, issuer TEXT NOT NULL, subject TEXT NOT NULL,
    email TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '',
    addresses TEXT NOT NULL DEFAULT '[]', created INTEGER NOT NULL, UNIQUE(issuer, subject)
);
CREATE TABLE IF NOT EXISTS customer_sessions (
    token_hash TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    expires INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS customer_sessions_expiry_idx ON customer_sessions(expires);
CREATE TABLE IF NOT EXISTS customer_login_flows (
    state_hash TEXT PRIMARY KEY, nonce TEXT NOT NULL, verifier TEXT NOT NULL,
    destination TEXT NOT NULL, expires INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS customer_state (
    customer_id TEXT PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
    cart TEXT NOT NULL DEFAULT '{}', favorites TEXT NOT NULL DEFAULT '[]', version INTEGER NOT NULL DEFAULT 0
);
