from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_cli.config import AppConfig


class ConfigTests(unittest.TestCase):
    def test_from_env_prefers_oauth_and_sets_default_token_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oauth_client = root / "credentials" / "oauth-client.json"
            oauth_client.parent.mkdir(parents=True, exist_ok=True)
            oauth_client.write_text("{}", encoding="utf-8")

            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "GOOGLE_SHEET_ID": "sheet-id",
                    "GOOGLE_OAUTH_CLIENT_FILE": "credentials/oauth-client.json",
                },
                clear=True,
            ):
                config = AppConfig.from_env(root)

            self.assertEqual(config.google_auth_mode_label(), "OAuth user credentials")
            self.assertEqual(config.google_oauth_client_file, oauth_client.resolve())
            self.assertEqual(
                config.google_oauth_token_file,
                (root / "data" / "google" / "oauth-token.json").resolve(),
            )
            self.assertEqual(config.missing_google_vars(), [])

    def test_missing_google_vars_accepts_service_account_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            creds = root / "credentials" / "service-account.json"
            creds.parent.mkdir(parents=True, exist_ok=True)
            creds.write_text("{}", encoding="utf-8")

            with patch.dict(
                os.environ,
                {
                    "GOOGLE_SHEET_ID": "sheet-id",
                    "GOOGLE_SERVICE_ACCOUNT_FILE": "credentials/service-account.json",
                },
                clear=True,
            ):
                config = AppConfig.from_env(root)

            self.assertEqual(config.google_auth_mode_label(), "service account credentials")
            self.assertEqual(config.missing_google_vars(), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
