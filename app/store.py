import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  repository TEXT NOT NULL DEFAULT '',
  site_url TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hosts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  domain TEXT NOT NULL,
  protocol TEXT NOT NULL,
  username TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  intent TEXT NOT NULL,
  status TEXT NOT NULL,
  requires_confirmation INTEGER NOT NULL,
  confirmation_phrase TEXT NOT NULL,
  details TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  message TEXT NOT NULL,
  details TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.RLock()
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def init(self) -> None:
        with self.lock, self.connect() as db:
            db.executescript(SCHEMA)
            count = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            if count == 0:
                self._insert_project(db, "Demo Website", "", "", "ready")

    def _insert_project(self, db, name, repository, site_url, status):
        project_id = str(uuid4())
        db.execute(
            "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, name, repository, site_url, status, now()),
        )
        return project_id

    @staticmethod
    def rows(rows):
        return [dict(row) for row in rows]

    def list_projects(self):
        with self.connect() as db:
            return self.rows(db.execute("SELECT * FROM projects ORDER BY created_at"))

    def create_project(self, name: str, repository: str, site_url: str):
        with self.lock, self.connect() as db:
            project_id = self._insert_project(db, name, repository, site_url, "draft")
            db.commit()
            return dict(db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())

    def list_hosts(self):
        with self.connect() as db:
            return self.rows(db.execute("SELECT * FROM hosts ORDER BY created_at DESC"))

    def create_host(self, name: str, domain: str, protocol: str, username: str, status: str):
        host_id = str(uuid4())
        with self.lock, self.connect() as db:
            db.execute(
                "INSERT INTO hosts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (host_id, name, domain, protocol, username, status, now()),
            )
            db.commit()
            return dict(db.execute("SELECT * FROM hosts WHERE id=?", (host_id,)).fetchone())

    def list_tasks(self):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 100")
            result = self.rows(rows)
            for item in result:
                item["requires_confirmation"] = bool(item["requires_confirmation"])
                item["details"] = json.loads(item["details"])
            return result

    def create_task(self, project_id, intent, requires_confirmation, phrase, details):
        task_id = str(uuid4())
        status = "waiting-confirmation" if requires_confirmation else "queued"
        with self.lock, self.connect() as db:
            db.execute(
                "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    project_id,
                    intent,
                    status,
                    int(requires_confirmation),
                    phrase,
                    json.dumps(details),
                    now(),
                ),
            )
            db.execute(
                "INSERT INTO events(kind,message,details,created_at) VALUES(?,?,?,?)",
                ("task", f"Task {intent} created", json.dumps({"task_id": task_id}), now()),
            )
            db.commit()
        return self.get_task(task_id)

    def get_task(self, task_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                return None
            item = dict(row)
            item["requires_confirmation"] = bool(item["requires_confirmation"])
            item["details"] = json.loads(item["details"])
            return item

    def approve_task(self, task_id: str, confirmation: str):
        task = self.get_task(task_id)
        if task is None:
            return None, "not-found"
        if not task["requires_confirmation"]:
            return task, "not-required"
        if confirmation.strip().upper() != task["confirmation_phrase"].upper():
            return task, "wrong-confirmation"
        with self.lock, self.connect() as db:
            db.execute("UPDATE tasks SET status='queued' WHERE id=?", (task_id,))
            db.commit()
        return self.get_task(task_id), "approved"
