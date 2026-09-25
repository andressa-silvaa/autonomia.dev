ALTER TABLE exercises ADD COLUMN required INTEGER NOT NULL DEFAULT 0 CHECK (required IN (0, 1));
ALTER TABLE exercises ADD COLUMN options TEXT NOT NULL DEFAULT '[]';
ALTER TABLE exercises ADD COLUMN accepted_answers TEXT NOT NULL DEFAULT '[]';
ALTER TABLE exercises ADD COLUMN rubric TEXT NOT NULL DEFAULT '[]';
ALTER TABLE exercises ADD COLUMN hints TEXT NOT NULL DEFAULT '[]';
ALTER TABLE exercises ADD COLUMN reference_answer TEXT NOT NULL DEFAULT '';
ALTER TABLE exercises ADD COLUMN source_path TEXT NOT NULL DEFAULT '';
ALTER TABLE exercises ADD COLUMN position INTEGER NOT NULL DEFAULT 0;
ALTER TABLE exercises ADD COLUMN retired INTEGER NOT NULL DEFAULT 0 CHECK (retired IN (0, 1));
CREATE UNIQUE INDEX idx_exercises_slug ON exercises(slug);

ALTER TABLE attempts ADD COLUMN passed INTEGER NOT NULL DEFAULT 0 CHECK (passed IN (0, 1));
ALTER TABLE attempts ADD COLUMN graded_by TEXT NOT NULL DEFAULT '';

CREATE TABLE exercise_progress (
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exercise_id    INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    started_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    hints_revealed INTEGER NOT NULL DEFAULT 0 CHECK (hints_revealed >= 0),
    passed_at      TEXT,
    PRIMARY KEY (user_id, exercise_id),
    CHECK (passed_at IS NULL OR passed_at >= started_at)
);

CREATE TABLE xp_events (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind       TEXT    NOT NULL CHECK (kind IN ('competency', 'activity')),
    amount     INTEGER NOT NULL CHECK (amount >= 0),
    source     TEXT    NOT NULL,
    source_id  INTEGER,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_xp_events_user ON xp_events(user_id, created_at);
