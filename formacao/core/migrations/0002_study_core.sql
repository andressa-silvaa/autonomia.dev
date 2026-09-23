CREATE TABLE module_progress (
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_id    INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    status       TEXT    NOT NULL CHECK (status IN ('in_progress', 'completed')),
    started_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    completed_at TEXT,
    PRIMARY KEY (user_id, module_id),
    CHECK ((status = 'completed') = (completed_at IS NOT NULL))
);

CREATE TABLE checkins (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day        TEXT    NOT NULL,
    intention  TEXT    NOT NULL CHECK (length(trim(intention)) > 0),
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (user_id, day)
);

CREATE UNIQUE INDEX idx_sessions_one_active_per_user
    ON study_sessions(user_id) WHERE ended_at IS NULL;
