from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_cli.constants import INTERMEDIATE_SHEET_HEADERS, LEGACY_SHEET_HEADERS, SHEET_HEADERS
from jobfit_cli.sheets import (
    GoogleSheetsLogger,
    SheetsValidationError,
    application_status_conditional_format_requests,
    build_cover_letter_formula,
    column_letter,
    normalize_date_value,
    score_conditional_format_requests,
)


class FakeSpreadsheet:
    def __init__(self) -> None:
        self.batch_updates: list[dict] = []
        self.metadata = {
            "sheets": [
                {
                    "properties": {"sheetId": 77},
                    "bandedRanges": [],
                    "conditionalFormats": [],
                }
            ]
        }

    def fetch_sheet_metadata(self) -> dict:
        return self.metadata

    def batch_update(self, body: dict) -> None:
        self.batch_updates.append(body)


class FakeWorksheet:
    def __init__(self, rows: list[list[str]], spreadsheet: FakeSpreadsheet) -> None:
        self.rows = [list(row) for row in rows]
        self.id = 77
        self.spreadsheet = spreadsheet
        self.appended: list[tuple[list[str], str]] = []

    def row_values(self, index: int) -> list[str]:
        if 0 < index <= len(self.rows):
            return list(self.rows[index - 1])
        return []

    def get_all_values(self) -> list[list[str]]:
        return [list(row) for row in self.rows]

    def clear(self) -> None:
        self.rows = []

    def update(self, *, range_name: str, values: list[list[str]], value_input_option: str) -> None:
        assert range_name == "A1"
        assert value_input_option == "USER_ENTERED"
        self.rows = [list(row) for row in values]

    def append_row(self, row: list[str], value_input_option: str = "RAW") -> None:
        self.rows.append(list(row))
        self.appended.append((list(row), value_input_option))


class SheetsTests(unittest.TestCase):
    def test_migrates_legacy_headers_and_dates(self) -> None:
        spreadsheet = FakeSpreadsheet()
        worksheet = FakeWorksheet(
            [
                LEGACY_SHEET_HEADERS,
                [
                    "2026-03-26T17:58:39+00:00",
                    "Acme",
                    "Backend Engineer",
                    "Remote",
                    "",
                    "74",
                    "possible_fit",
                    "Python | APIs | Ownership",
                    "Kubernetes | GCP | Finance",
                    "Strong fit overall.",
                    "data/jobs/example.md",
                    "hash",
                    "gpt-4o-mini",
                ],
            ],
            spreadsheet,
        )
        logger = GoogleSheetsLogger(Path("credentials.json"), "sheet-id")
        logger._spreadsheet = spreadsheet
        logger._worksheet = worksheet

        logger.ensure_schema()

        self.assertEqual(worksheet.rows[0], SHEET_HEADERS)
        self.assertEqual(worksheet.rows[1][0], "2026-03-26")
        self.assertEqual(worksheet.rows[1][3], "waiting")
        self.assertEqual(worksheet.rows[1][11], "")

    def test_migrates_intermediate_headers_and_inserts_status(self) -> None:
        spreadsheet = FakeSpreadsheet()
        worksheet = FakeWorksheet(
            [
                INTERMEDIATE_SHEET_HEADERS,
                [
                    "2026-03-26",
                    "Acme",
                    "Backend Engineer",
                    "Remote",
                    "https://example.com/job",
                    "74",
                    "possible_fit",
                    "Python | APIs | Ownership",
                    "Kubernetes | GCP | Finance",
                    "Strong fit overall.",
                    '=HYPERLINK("https://docs.google.com/document/d/123/edit","Open cover letter")',
                    "data/jobs/example.md",
                    "hash",
                    "gpt-4o-mini",
                ],
            ],
            spreadsheet,
        )
        logger = GoogleSheetsLogger(Path("credentials.json"), "sheet-id")
        logger._spreadsheet = spreadsheet
        logger._worksheet = worksheet

        logger.ensure_schema()

        self.assertEqual(worksheet.rows[0], SHEET_HEADERS)
        self.assertEqual(worksheet.rows[1][3], "waiting")
        self.assertEqual(
            worksheet.rows[1][11],
            '=HYPERLINK("https://docs.google.com/document/d/123/edit","Open cover letter")',
        )

    def test_append_row_uses_user_entered_and_formats_once(self) -> None:
        spreadsheet = FakeSpreadsheet()
        worksheet = FakeWorksheet([SHEET_HEADERS], spreadsheet)
        logger = GoogleSheetsLogger(Path("credentials.json"), "sheet-id")
        logger._spreadsheet = spreadsheet
        logger._worksheet = worksheet

        logger.append_row(["2026-03-26"] + [""] * (len(SHEET_HEADERS) - 1))

        self.assertEqual(len(worksheet.appended), 1)
        self.assertEqual(worksheet.appended[0][1], "USER_ENTERED")
        self.assertEqual(len(spreadsheet.batch_updates), 1)
        self.assertIn("ONE_OF_LIST", str(spreadsheet.batch_updates[0]))

    def test_rejects_unexpected_headers(self) -> None:
        spreadsheet = FakeSpreadsheet()
        worksheet = FakeWorksheet([["wrong", "headers"]], spreadsheet)
        logger = GoogleSheetsLogger(Path("credentials.json"), "sheet-id")
        logger._spreadsheet = spreadsheet
        logger._worksheet = worksheet

        with self.assertRaises(SheetsValidationError):
            logger.ensure_schema()

    def test_build_cover_letter_formula_returns_hyperlink(self) -> None:
        formula = build_cover_letter_formula("https://docs.google.com/document/d/123/edit")
        self.assertIn("HYPERLINK", formula)
        self.assertIn("Open cover letter", formula)

    def test_normalize_date_value_keeps_day_only(self) -> None:
        self.assertEqual(normalize_date_value("2026-03-26T17:58:39+00:00"), "2026-03-26")

    def test_score_conditional_format_uses_score_column_letter(self) -> None:
        requests = score_conditional_format_requests(sheet_id=77)
        self.assertIn("=$G2>=80", str(requests[0]))

    def test_application_status_rules_cover_all_statuses(self) -> None:
        requests = application_status_conditional_format_requests(sheet_id=77)
        self.assertEqual(len(requests), 11)
        self.assertIn('=LOWER($D2)="applied"', str(requests[1]))

    def test_column_letter_handles_double_digits(self) -> None:
        self.assertEqual(column_letter(0), "A")
        self.assertEqual(column_letter(3), "D")
        self.assertEqual(column_letter(26), "AA")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
