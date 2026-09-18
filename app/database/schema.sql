CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS revisions (
    case_id TEXT,
    revision INTEGER,
    data TEXT NOT NULL,
    PRIMARY KEY (case_id, revision)
);
