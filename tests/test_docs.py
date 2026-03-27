from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_cli.docs import build_cover_letter_formatting_requests


class DocsFormattingTests(unittest.TestCase):
    def test_build_cover_letter_formatting_requests_sets_margin_and_date_style(self) -> None:
        content = (
            "27 March 2026\n\n"
            "Dear Hiring Team,\n\n"
            "Paragraph one.\n\n"
            "Paragraph two.\n\n"
            "Paragraph three.\n\n"
            "Best regards,\n"
            "Mohammad Naderi\n"
        )

        requests = build_cover_letter_formatting_requests(content)

        self.assertEqual(requests[0]["updateDocumentStyle"]["documentStyle"]["marginTop"]["magnitude"], 96)
        self.assertEqual(requests[1]["updateParagraphStyle"]["paragraphStyle"]["lineSpacing"], 115)
        self.assertIn("updateTextStyle", requests[2])
        self.assertIn("Best regards", content)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
