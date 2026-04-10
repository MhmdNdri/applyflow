"""Google Docs and Drive integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .google_auth import GoogleAuthSettings, load_google_dependencies

DOCS_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]


class GoogleDocsValidationError(RuntimeError):
    """Raised when Google Docs or Drive access is invalid."""


class GoogleDocsClient:
    def __init__(
        self,
        service_account_file: Path | None,
        folder_id: str | None = None,
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
        self.folder_id = folder_id
        self._credentials = credentials
        self._docs_service = None
        self._drive_service = None

    @property
    def docs_service(self) -> Any:
        if self._docs_service is not None:
            return self._docs_service

        if self._credentials is not None:
            credentials = self._credentials
            try:
                from googleapiclient.discovery import build
            except ImportError as exc:  # pragma: no cover - depends on local environment
                raise ConfigurationError(
                    "Google API packages are not installed. Run `pip install -e .` first."
                ) from exc
        else:
            credentials, build = load_google_dependencies(
                auth_settings=self.auth_settings,
                scopes=DOCS_SCOPES,
            )
        self._docs_service = build("docs", "v1", credentials=credentials, cache_discovery=False)
        return self._docs_service

    @property
    def drive_service(self) -> Any:
        if self._drive_service is not None:
            return self._drive_service

        if self._credentials is not None:
            credentials = self._credentials
            try:
                from googleapiclient.discovery import build
            except ImportError as exc:  # pragma: no cover - depends on local environment
                raise ConfigurationError(
                    "Google API packages are not installed. Run `pip install -e .` first."
                ) from exc
        else:
            credentials, build = load_google_dependencies(
                auth_settings=self.auth_settings,
                scopes=DOCS_SCOPES,
            )
        self._drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        return self._drive_service

    def validate_access(self) -> None:
        document_id = None
        try:
            document_id = self._create_document("jobfit setup validation")
            self._write_document(
                document_id,
                "Temporary validation document for Job Fit Evaluator setup.",
            )
            self._share_document(document_id)
        except Exception as exc:
            raise GoogleDocsValidationError(f"Google Docs validation failed: {exc}") from exc
        finally:
            if document_id:
                try:
                    self.drive_service.files().delete(fileId=document_id).execute()
                except Exception:
                    pass

    def create_cover_letter_doc(self, *, title: str, content: str) -> str:
        document_id = self._create_document(title)
        self._write_document(document_id, content)
        self._share_document(document_id)
        return f"https://docs.google.com/document/d/{document_id}/edit"

    def _create_document(self, title: str) -> str:
        if self.folder_id:
            response = self.drive_service.files().create(
                body={
                    "name": title,
                    "mimeType": "application/vnd.google-apps.document",
                    "parents": [self.folder_id],
                },
                fields="id",
                supportsAllDrives=True,
            ).execute()
            document_id = response.get("id")
        else:
            response = self.docs_service.documents().create(body={"title": title}).execute()
            document_id = response.get("documentId")
        if not document_id:
            raise GoogleDocsValidationError("Google Docs create response did not include a documentId.")
        return document_id

    def _write_document(self, document_id: str, content: str) -> None:
        normalized_content = content.strip() + "\n"
        self.docs_service.documents().batchUpdate(
            documentId=document_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": normalized_content,
                        }
                    }
                ]
            },
        ).execute()
        self.docs_service.documents().batchUpdate(
            documentId=document_id,
            body={"requests": build_cover_letter_formatting_requests(normalized_content)},
        ).execute()

    def _share_document(self, document_id: str) -> None:
        self.drive_service.permissions().create(
            fileId=document_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
            supportsAllDrives=True,
        ).execute()


def build_cover_letter_formatting_requests(content: str) -> list[dict[str, Any]]:
    full_length = len(content) + 1
    requests: list[dict[str, Any]] = [
        {
            "updateDocumentStyle": {
                "documentStyle": {
                    "marginTop": {"magnitude": 96, "unit": "PT"},
                    "marginBottom": {"magnitude": 72, "unit": "PT"},
                    "marginLeft": {"magnitude": 72, "unit": "PT"},
                    "marginRight": {"magnitude": 72, "unit": "PT"},
                },
                "fields": "marginTop,marginBottom,marginLeft,marginRight",
            }
        },
        {
            "updateParagraphStyle": {
                "range": {"startIndex": 1, "endIndex": full_length},
                "paragraphStyle": {
                    "lineSpacing": 115,
                    "spaceBelow": {"magnitude": 14, "unit": "PT"},
                },
                "fields": "lineSpacing,spaceBelow",
            }
        },
    ]

    first_line_end = content.find("\n")
    if first_line_end > 0:
        requests.append(
            {
                "updateTextStyle": {
                    "range": {"startIndex": 1, "endIndex": first_line_end + 1},
                    "textStyle": {
                        "italic": True,
                        "foregroundColor": {
                            "color": {
                                "rgbColor": {
                                    "red": 0.35,
                                    "green": 0.35,
                                    "blue": 0.35,
                                }
                            }
                        },
                    },
                    "fields": "italic,foregroundColor",
                }
            }
        )
        requests.append(
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": 1, "endIndex": first_line_end + 1},
                    "paragraphStyle": {
                        "spaceBelow": {"magnitude": 20, "unit": "PT"},
                    },
                    "fields": "spaceBelow",
                }
            }
        )

    closing_index = content.lower().rfind("best regards,")
    if closing_index >= 0:
        requests.append(
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": closing_index + 1, "endIndex": full_length},
                    "paragraphStyle": {
                        "spaceAbove": {"magnitude": 10, "unit": "PT"},
                    },
                    "fields": "spaceAbove",
                }
            }
        )

    return requests
