CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  public_token TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT DEFAULT '',
  requester TEXT DEFAULT '',
  assignee TEXT DEFAULT '',
  assignee_phone TEXT DEFAULT '',
  deadline TEXT,
  location TEXT,
  complexity TEXT NOT NULL,
  checklist_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'assigned',
  result_json TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  metadata_json TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);

CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  check_id TEXT,
  object_key TEXT NOT NULL,
  content_type TEXT DEFAULT 'application/octet-stream',
  created_at TEXT NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);
CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence(task_id);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  task_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_id ON events(id);
