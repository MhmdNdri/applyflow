"""Google Sheets integration."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .config import ConfigurationError
from .constants import (
    APPLICATION_STATUS_OPTIONS,
    COVER_LETTER_LINK_LABEL,
    DEFAULT_APPLICATION_STATUS,
    INTERMEDIATE_SHEET_HEADERS,
    LEGACY_SHEET_HEADERS,
    SHEET_HEADERS,
)
from .google_auth import GoogleAuthSettings, load_google_dependencies

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsValidationError(RuntimeError):
    """Raised when the Google Sheets setup is invalid."""


class GoogleSheetsLogger:
    def __init__(
        self,
        service_account_file: Path | None,
        sheet_id: str,
        *,
        oauth_client_file: Path | None = None,
        oauth_token_file: Path | None = None,
        credentials: Any | None = None,
    ) -> None:
        self.auth_settings = GoogleAuthSettings(
            service_account_file=service_account_file,
            oauth_client_file=oauth_client_file,
            oauth_token_file=oauth_token_file,
        )
        self.sheet_id = sheet_id
        self._credentials = credentials
        self._client = None
        self._spreadsheet = None
        self._worksheet = None
        self._formatted = False

    @property
    def client(self) -> Any:
        if self._client is not None:
            return self._client

        if self._credentials is not None:
            credentials = self._credentials
        else:
            credentials, _ = load_google_dependencies(
                auth_settings=self.auth_settings,
                scopes=SHEETS_SCOPES,
            )

        try:
            import gspread
        except ImportError as exc:  # pragma: no cover - depends on local environment
            raise ConfigurationError(
                "The `gspread` package is not installed. Run `pip install -e .` first."
            ) from exc

        self._client = gspread.authorize(credentials)
        return self._client

    @property
    def spreadsheet(self) -> Any:
        if self._spreadsheet is not None:
            return self._spreadsheet

        self._spreadsheet = self.client.open_by_key(self.sheet_id)
        return self._spreadsheet

    @property
    def worksheet(self) -> Any:
        if self._worksheet is not None:
            return self._worksheet

        self._worksheet = self.spreadsheet.sheet1
        return self._worksheet

    def validate_access(self) -> None:
        self.ensure_schema()
        self.apply_formatting()

    def ensure_schema(self) -> None:
        existing = self.worksheet.row_values(1)
        normalized = [value.strip() for value in existing if value.strip()]
        if not normalized:
            self.worksheet.update(
                range_name="A1",
                values=[SHEET_HEADERS],
                value_input_option="USER_ENTERED",
            )
            return

        if normalized == SHEET_HEADERS:
            return

        if normalized == INTERMEDIATE_SHEET_HEADERS:
            self._migrate_intermediate_sheet()
            return

        if normalized == LEGACY_SHEET_HEADERS:
            self._migrate_legacy_sheet()
            return

        raise SheetsValidationError(
            "First worksheet headers do not match the expected schema."
        )

    def append_row(self, row: list[str]) -> None:
        self.ensure_schema()
        if not self._formatted:
            self.apply_formatting()
        self.worksheet.append_row(row, value_input_option="USER_ENTERED")

    def apply_formatting(self) -> None:
        sheet_id = self.worksheet.id
        metadata = self.spreadsheet.fetch_sheet_metadata()
        sheet_metadata = next(
            (
                item
                for item in metadata.get("sheets", [])
                if item.get("properties", {}).get("sheetId") == sheet_id
            ),
            {},
        )

        requests: list[dict[str, Any]] = []

        for banded_range in reversed(sheet_metadata.get("bandedRanges", [])):
            requests.append(
                {"deleteBanding": {"bandedRangeId": banded_range["bandedRangeId"]}}
            )

        for index in reversed(range(len(sheet_metadata.get("conditionalFormats", [])))):
            requests.append(
                {"deleteConditionalFormatRule": {"sheetId": sheet_id, "index": index}}
            )

        requests.extend(
            [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {"frozenRowCount": 1},
                        },
                        "fields": "gridProperties.frozenRowCount",
                    }
                },
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(SHEET_HEADERS),
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.87,
                                    "green": 0.92,
                                    "blue": 0.98,
                                },
                                "horizontalAlignment": "CENTER",
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {
                                        "red": 0.13,
                                        "green": 0.2,
                                        "blue": 0.32,
                                    },
                                },
                                "wrapStrategy": "WRAP",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,wrapStrategy)",
                    }
                },
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(SHEET_HEADERS),
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "verticalAlignment": "MIDDLE",
                                "wrapStrategy": "WRAP",
                            }
                        },
                        "fields": "userEnteredFormat(verticalAlignment,wrapStrategy)",
                    }
                },
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": header_index("score"),
                            "endColumnIndex": header_index("score") + 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "horizontalAlignment": "CENTER",
                                "textFormat": {"bold": True},
                            }
                        },
                        "fields": "userEnteredFormat(horizontalAlignment,textFormat)",
                    }
                },
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": header_index("application_status"),
                            "endColumnIndex": header_index("application_status") + 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "horizontalAlignment": "CENTER",
                            }
                        },
                        "fields": "userEnteredFormat(horizontalAlignment)",
                    }
                },
                {
                    "setDataValidation": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": header_index("application_status"),
                            "endColumnIndex": header_index("application_status") + 1,
                        },
                        "rule": {
                            "condition": {
                                "type": "ONE_OF_LIST",
                                "values": [
                                    {"userEnteredValue": status}
                                    for status in APPLICATION_STATUS_OPTIONS
                                ],
                            },
                            "strict": True,
                            "showCustomUi": True,
                        },
                    }
                },
                {
                    "addBanding": {
                        "bandedRange": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,
                                "startColumnIndex": 0,
                                "endColumnIndex": len(SHEET_HEADERS),
                            },
                            "rowProperties": {
                                "headerColor": {
                                    "red": 0.87,
                                    "green": 0.92,
                                    "blue": 0.98,
                                },
                                "firstBandColor": {
                                    "red": 0.98,
                                    "green": 0.99,
                                    "blue": 1.0,
                                },
                                "secondBandColor": {
                                    "red": 0.95,
                                    "green": 0.97,
                                    "blue": 0.99,
                                },
                            },
                        }
                    }
                },
            ]
        )

        for column_index, pixel_size in enumerate(column_widths(), start=0):
            requests.append(
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": column_index,
                            "endIndex": column_index + 1,
                        },
                        "properties": {"pixelSize": pixel_size},
                        "fields": "pixelSize",
                    }
                }
            )

        requests.extend(score_conditional_format_requests(sheet_id))
        requests.extend(application_status_conditional_format_requests(sheet_id))
        self.spreadsheet.batch_update({"requests": requests})
        self._formatted = True

    def _migrate_legacy_sheet(self) -> None:
        rows = self.worksheet.get_all_values()
        migrated_rows = [SHEET_HEADERS]

        for row in rows[1:]:
            padded_row = row + [""] * (len(LEGACY_SHEET_HEADERS) - len(row))
            legacy = dict(zip(LEGACY_SHEET_HEADERS, padded_row))
            migrated_rows.append(
                [
                    normalize_date_value(legacy["timestamp"]),
                    legacy["company"],
                    legacy["role_title"],
                    DEFAULT_APPLICATION_STATUS,
                    legacy["location"],
                    legacy["source_url"],
                    legacy["score"],
                    legacy["verdict"],
                    legacy["top_strengths_summary"],
                    legacy["critical_gaps_summary"],
                    legacy["feedback"],
                    "",
                    legacy["archived_job_path"],
                    legacy["profile_hash"],
                    legacy["model"],
                ]
            )

        self._replace_all_rows(migrated_rows)

    def _migrate_intermediate_sheet(self) -> None:
        rows = self.worksheet.get_all_values()
        migrated_rows = [SHEET_HEADERS]

        for row in rows[1:]:
            padded_row = row + [""] * (len(INTERMEDIATE_SHEET_HEADERS) - len(row))
            current = dict(zip(INTERMEDIATE_SHEET_HEADERS, padded_row))
            migrated_rows.append(
                [
                    normalize_date_value(current["date"]),
                    current["company"],
                    current["role_title"],
                    DEFAULT_APPLICATION_STATUS,
                    current["location"],
                    current["source_url"],
                    current["score"],
                    current["verdict"],
                    current["top_strengths_summary"],
                    current["critical_gaps_summary"],
                    current["feedback"],
                    current["cover_letter_doc_url"],
                    current["archived_job_path"],
                    current["profile_hash"],
                    current["model"],
                ]
            )

        self._replace_all_rows(migrated_rows)

    def _replace_all_rows(self, rows: list[list[str]]) -> None:
        self.worksheet.clear()
        self.worksheet.update(
            range_name="A1",
            values=rows,
            value_input_option="USER_ENTERED",
        )


def build_cover_letter_formula(url: str | None) -> str:
    if not url:
        return ""
    escaped_url = url.replace('"', '""')
    escaped_label = COVER_LETTER_LINK_LABEL.replace('"', '""')
    return f'=HYPERLINK("{escaped_url}","{escaped_label}")'


def normalize_date_value(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    if "T" in cleaned:
        try:
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return cleaned.split("T", maxsplit=1)[0]
    return cleaned


def column_widths() -> list[int]:
    return [100, 180, 220, 170, 120, 200, 90, 120, 220, 220, 280, 160, 220, 160, 120]


def score_conditional_format_requests(sheet_id: int) -> list[dict[str, Any]]:
    base_range = {
        "sheetId": sheet_id,
        "startRowIndex": 1,
        "startColumnIndex": header_index("score"),
        "endColumnIndex": header_index("score") + 1,
    }
    score_column_letter = column_letter(header_index("score"))
    return [
        {
            "addConditionalFormatRule": {
                "index": 0,
                "rule": {
                    "ranges": [base_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": f"=${score_column_letter}2>=80"}],
                        },
                        "format": {
                            "backgroundColor": {"red": 0.85, "green": 0.94, "blue": 0.86},
                            "textFormat": {"bold": True},
                        },
                    },
                },
            }
        },
        {
            "addConditionalFormatRule": {
                "index": 1,
                "rule": {
                    "ranges": [base_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [
                                {
                                    "userEnteredValue": (
                                        f"=AND(${score_column_letter}2>=60,"
                                        f"${score_column_letter}2<80)"
                                    )
                                }
                            ],
                        },
                        "format": {
                            "backgroundColor": {"red": 0.99, "green": 0.95, "blue": 0.8},
                        },
                    },
                },
            }
        },
        {
            "addConditionalFormatRule": {
                "index": 2,
                "rule": {
                    "ranges": [base_range],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": f"=${score_column_letter}2<60"}],
                        },
                        "format": {
                            "backgroundColor": {"red": 0.99, "green": 0.87, "blue": 0.87},
                        },
                    },
                },
            }
        },
    ]


def application_status_conditional_format_requests(sheet_id: int) -> list[dict[str, Any]]:
    status_column_index = header_index("application_status")
    status_column_letter = column_letter(status_column_index)
    ranges = [
        {
            "sheetId": sheet_id,
            "startRowIndex": 1,
            "startColumnIndex": status_column_index,
            "endColumnIndex": status_column_index + 1,
        }
    ]
    status_colors = {
        "wishlist": {"red": 0.93, "green": 0.94, "blue": 0.98},
        "applied": {"red": 0.84, "green": 0.92, "blue": 0.99},
        "waiting": {"red": 0.98, "green": 0.95, "blue": 0.8},
        "recruiter screen": {"red": 0.87, "green": 0.95, "blue": 0.91},
        "interview scheduled": {"red": 0.79, "green": 0.9, "blue": 0.85},
        "interviewing": {"red": 0.72, "green": 0.87, "blue": 0.81},
        "final round": {"red": 0.71, "green": 0.84, "blue": 0.95},
        "offer": {"red": 0.84, "green": 0.95, "blue": 0.82},
        "accepted": {"red": 0.73, "green": 0.88, "blue": 0.71},
        "rejected": {"red": 0.98, "green": 0.84, "blue": 0.84},
        "withdrawn": {"red": 0.9, "green": 0.9, "blue": 0.9},
    }
    requests: list[dict[str, Any]] = []
    for index, status in enumerate(APPLICATION_STATUS_OPTIONS, start=3):
        requests.append(
            {
                "addConditionalFormatRule": {
                    "index": index,
                    "rule": {
                        "ranges": ranges,
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [
                                    {
                                        "userEnteredValue": (
                                            f'=LOWER(${status_column_letter}2)="{status}"'
                                        )
                                    }
                                ],
                            },
                            "format": {
                                "backgroundColor": status_colors[status],
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {
                                        "red": 0.14,
                                        "green": 0.14,
                                        "blue": 0.14,
                                    },
                                },
                            },
                        },
                    },
                }
            }
        )
    return requests


def header_index(name: str) -> int:
    return SHEET_HEADERS.index(name)


def column_letter(index: int) -> str:
    value = index + 1
    letters = []
    while value:
        value, remainder = divmod(value - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))
