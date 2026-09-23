CREATE TABLE users (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE areas (
    id          INTEGER PRIMARY KEY,
    slug        TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE competencies (
    id          INTEGER PRIMARY KEY,
    area_id     INTEGER NOT NULL REFERENCES areas(id) ON DELETE RESTRICT,
    slug        TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX idx_competencies_area ON competencies(area_id);

CREATE TABLE tracks (
    id          INTEGER PRIMARY KEY,
    slug        TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE modules (
    id           INTEGER PRIMARY KEY,
    track_id     INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    slug         TEXT    NOT NULL,
    title        TEXT    NOT NULL,
    summary      TEXT    NOT NULL DEFAULT '',
    content_path TEXT,
    position     INTEGER NOT NULL DEFAULT 0,
    UNIQUE (track_id, slug)
);
CREATE INDEX idx_modules_track ON modules(track_id);

CREATE TABLE module_prerequisites (
    module_id       INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    prerequisite_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    PRIMARY KEY (module_id, prerequisite_id),
    CHECK (module_id <> prerequisite_id)
);
CREATE INDEX idx_module_prereq_prereq ON module_prerequisites(prerequisite_id);

CREATE TABLE module_competencies (
    module_id     INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    competency_id INTEGER NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    PRIMARY KEY (module_id, competency_id)
);
CREATE INDEX idx_module_comp_comp ON module_competencies(competency_id);

CREATE TABLE exercises (
    id          INTEGER PRIMARY KEY,
    module_id   INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    slug        TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    kind        TEXT    NOT NULL,
    grading     TEXT    NOT NULL,
    prompt      TEXT    NOT NULL,
    difficulty  INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
    xp          INTEGER NOT NULL DEFAULT 10 CHECK (xp >= 0),
    UNIQUE (module_id, slug)
);
CREATE INDEX idx_exercises_module ON exercises(module_id);

CREATE TABLE projects (
    id          INTEGER PRIMARY KEY,
    track_id    INTEGER REFERENCES tracks(id) ON DELETE SET NULL,
    slug        TEXT    NOT NULL UNIQUE,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    kind        TEXT    NOT NULL CHECK (kind IN ('integrator', 'surprise'))
);
CREATE INDEX idx_projects_track ON projects(track_id);

CREATE TABLE user_competencies (
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    competency_id INTEGER NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    mastery       TEXT    NOT NULL DEFAULT 'not_studied' CHECK (mastery IN (
                      'not_studied', 'unknown', 'beginning', 'recognizes',
                      'can_apply', 'can_explain', 'can_teach', 'mastery')),
    updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (user_id, competency_id)
);

CREATE TABLE study_sessions (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_id   INTEGER REFERENCES modules(id) ON DELETE SET NULL,
    started_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    ended_at    TEXT,
    notes       TEXT    NOT NULL DEFAULT '',
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);
CREATE INDEX idx_sessions_user_started ON study_sessions(user_id, started_at);

CREATE TABLE attempts (
    id               INTEGER PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exercise_id      INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    session_id       INTEGER REFERENCES study_sessions(id) ON DELETE SET NULL,
    submitted_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    answer           TEXT    NOT NULL DEFAULT '',
    score            REAL    CHECK (score IS NULL OR score BETWEEN 0 AND 1),
    feedback         TEXT    NOT NULL DEFAULT '',
    duration_seconds INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    hints_used       INTEGER NOT NULL DEFAULT 0 CHECK (hints_used >= 0),
    used_ai          INTEGER NOT NULL DEFAULT 0 CHECK (used_ai IN (0, 1))
);
CREATE INDEX idx_attempts_user_exercise ON attempts(user_id, exercise_id);
CREATE INDEX idx_attempts_session ON attempts(session_id);

CREATE TABLE reviews (
    id               INTEGER PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    competency_id    INTEGER NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    easiness         REAL    NOT NULL DEFAULT 2.5 CHECK (easiness >= 1.3),
    interval_days    INTEGER NOT NULL DEFAULT 0 CHECK (interval_days >= 0),
    repetitions      INTEGER NOT NULL DEFAULT 0 CHECK (repetitions >= 0),
    due_on           TEXT    NOT NULL DEFAULT (date('now')),
    last_reviewed_at TEXT,
    UNIQUE (user_id, competency_id)
);
CREATE INDEX idx_reviews_user_due ON reviews(user_id, due_on);
