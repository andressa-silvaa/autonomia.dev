CREATE TABLE diagnostic_questions (
    id               INTEGER PRIMARY KEY,
    competency_id    INTEGER NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    slug             TEXT    NOT NULL UNIQUE,
    kind             TEXT    NOT NULL,
    prompt           TEXT    NOT NULL,
    options          TEXT    NOT NULL DEFAULT '[]',
    accepted_answers TEXT    NOT NULL,
    explanation      TEXT    NOT NULL DEFAULT '',
    position         INTEGER NOT NULL DEFAULT 0,
    retired          INTEGER NOT NULL DEFAULT 0 CHECK (retired IN (0, 1))
);
CREATE INDEX idx_diagnostic_questions_competency ON diagnostic_questions(competency_id);

CREATE TABLE diagnostic_runs (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    finished_at TEXT,
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);
CREATE UNIQUE INDEX idx_diagnostic_runs_one_open_per_user
    ON diagnostic_runs(user_id) WHERE finished_at IS NULL;

CREATE TABLE diagnostic_answers (
    run_id           INTEGER NOT NULL REFERENCES diagnostic_runs(id) ON DELETE CASCADE,
    question_id      INTEGER NOT NULL REFERENCES diagnostic_questions(id) ON DELETE CASCADE,
    answer           TEXT    NOT NULL DEFAULT '',
    is_correct       INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    confidence       TEXT    NOT NULL CHECK (confidence IN ('sure', 'guess', 'dont_know')),
    duration_seconds INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    answered_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (run_id, question_id)
);

CREATE TABLE mastery_events (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    competency_id INTEGER NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    from_mastery  TEXT    NOT NULL CHECK (from_mastery IN (
                      'not_studied', 'unknown', 'beginning', 'recognizes',
                      'can_apply', 'can_explain', 'can_teach', 'mastery')),
    to_mastery    TEXT    NOT NULL CHECK (to_mastery IN (
                      'not_studied', 'unknown', 'beginning', 'recognizes',
                      'can_apply', 'can_explain', 'can_teach', 'mastery')),
    source        TEXT    NOT NULL,
    source_id     INTEGER,
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_mastery_events_user_competency
    ON mastery_events(user_id, competency_id, created_at);

CREATE TABLE user_goals (
    user_id   INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    set_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
