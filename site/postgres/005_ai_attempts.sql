CREATE TABLE IF NOT EXISTS ai_attempts (
    scope TEXT NOT NULL,
    attempted_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS ai_attempts_scope_time_idx ON ai_attempts(scope, attempted_at);
CREATE INDEX IF NOT EXISTS ai_attempts_time_idx ON ai_attempts(attempted_at);
