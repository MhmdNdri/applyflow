from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


class MigrationTests(unittest.TestCase):
    def test_alembic_upgrade_creates_foundation_tables(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "foundation.db"
            config = Config(str(root / "alembic.ini"))
            config.set_main_option("script_location", str(root / "alembic"))
            config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

            command.upgrade(config, "head")

            engine = create_engine(f"sqlite:///{db_path}")
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            background_task_columns = {column["name"] for column in inspector.get_columns("background_tasks")}
            cover_letter_columns = {column["name"] for column in inspector.get_columns("cover_letters")}
            engine.dispose()

        self.assertTrue(
            {
                "users",
                "profiles",
                "resume_versions",
                "context_versions",
                "jobs",
                "evaluations",
                "cover_letters",
                "application_status_events",
                "background_tasks",
            }.issubset(tables)
        )
        self.assertFalse({"google_connections", "google_documents", "google_sheet_syncs"} & tables)
        self.assertTrue({"attempt_count", "max_attempts", "last_attempt_at", "next_retry_at"}.issubset(background_task_columns))
        self.assertNotIn("google_doc_url", cover_letter_columns)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
