from aion_core import tasks, worker
from tests.base import AionTest


class TestTaskDataClass(AionTest):
    def test_existing_default_is_internal_and_not_aux_eligible(self):
        tid = tasks.create("normal task", model_class="B", risk=1, time_est=1,
                           validation_command="python3 -c 'print(1)'")
        row = tasks.get(tid)
        self.assertEqual(row["data_class"], "INTERNAL")
        self.assertFalse(worker.auxiliary_eligible(row))

    def test_public_low_risk_validated_task_is_aux_eligible(self):
        tid = tasks.create("public formatting", model_class="B", data_class="PUBLIC",
                           risk=1, time_est=1, kind="format",
                           validation_command="python3 -c 'print(1)'")
        self.assertTrue(worker.auxiliary_eligible(tasks.get(tid)))

    def test_secret_task_can_never_be_aux_eligible(self):
        tid = tasks.create("secret", model_class="B", data_class="SECRET",
                           risk=1, time_est=1, validation_command="python3 -c 'print(1)'")
        self.assertFalse(worker.auxiliary_eligible(tasks.get(tid)))

    def test_invalid_data_class_is_rejected(self):
        with self.assertRaises(tasks.TaskError):
            tasks.create("bad", data_class="PRIVATE")

class TestTaskDataClassMigration(AionTest):
    def test_pre_v11_database_gets_internal_default_without_data_loss(self):
        import os, sqlite3
        from pathlib import Path
        from aion_core import db
        legacy = Path(self.tmp) / "legacy.sqlite3"
        db.close()
        raw = sqlite3.connect(legacy)
        raw.execute("""CREATE TABLE tasks (
            task_id TEXT PRIMARY KEY, project TEXT NOT NULL DEFAULT 'default', parent_task TEXT,
            title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'INBOX',
            priority INTEGER NOT NULL DEFAULT 3, impact REAL NOT NULL DEFAULT 3, probability REAL NOT NULL DEFAULT 0.7,
            unlocks REAL NOT NULL DEFAULT 1, info_gain REAL NOT NULL DEFAULT 1, cost REAL NOT NULL DEFAULT 1,
            risk REAL NOT NULL DEFAULT 1, time_est REAL NOT NULL DEFAULT 1, human_dependence REAL NOT NULL DEFAULT 1,
            owner_agent TEXT, model_class TEXT NOT NULL DEFAULT 'B', dependencies TEXT NOT NULL DEFAULT '',
            blockers TEXT NOT NULL DEFAULT '', approval_id TEXT, success_criteria TEXT NOT NULL DEFAULT '',
            validation_method TEXT NOT NULL DEFAULT '', output_location TEXT NOT NULL DEFAULT '', retry_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT, next_action TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL DEFAULT '', exec_command TEXT NOT NULL DEFAULT '',
            validation_command TEXT NOT NULL DEFAULT '', plan_id TEXT, evidence TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, claimed_at TEXT, started_at TEXT, completed_at TEXT)""")
        raw.execute("INSERT INTO tasks(task_id,title,status,created_at,updated_at) VALUES('TASK-OLD','legacy','READY','x','x')")
        raw.commit(); raw.close()
        os.environ["AION_DB"] = str(legacy)
        conn = db.connect()
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks)")}
        self.assertIn("data_class", cols)
        self.assertEqual(conn.execute("SELECT data_class FROM tasks WHERE task_id='TASK-OLD'").fetchone()[0], "INTERNAL")
        os.environ.pop("AION_DB", None)
        db.close()
