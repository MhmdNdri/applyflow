from __future__ import annotations

import base64
import io
from pathlib import Path
import sys
import unittest
import zipfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_api.documents import UploadedDocumentInput, extract_uploaded_document


class DocumentExtractionTests(unittest.TestCase):
    def test_extracts_text_file(self) -> None:
        extracted = extract_uploaded_document(
            UploadedDocumentInput(
                file_name="resume.md",
                content_type="text/markdown",
                data=b"React engineer\nTypeScript\n",
            ),
            field_name="resume_text",
        )
        self.assertEqual(extracted.text, "React engineer\nTypeScript")
        self.assertEqual(extracted.size_bytes, 26)

    def test_extracts_docx_file(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(
                "word/document.xml",
                (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    "<w:body>"
                    "<w:p><w:r><w:t>Hello from DOCX</w:t></w:r></w:p>"
                    "<w:p><w:r><w:t>Second paragraph</w:t></w:r></w:p>"
                    "</w:body></w:document>"
                ),
            )

        extracted = extract_uploaded_document(
            UploadedDocumentInput(
                file_name="resume.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                data=buffer.getvalue(),
            ),
            field_name="resume_text",
        )
        self.assertIn("Hello from DOCX", extracted.text)
        self.assertIn("Second paragraph", extracted.text)

    def test_extracts_simple_pdf_text(self) -> None:
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Length 43 >>\nstream\n"
            b"BT\n/F1 12 Tf\n72 712 Td\n(Hello from PDF) Tj\nET\n"
            b"endstream\nendobj\n%%EOF"
        )
        extracted = extract_uploaded_document(
            UploadedDocumentInput(
                file_name="resume.pdf",
                content_type="application/pdf",
                data=pdf_bytes,
            ),
            field_name="resume_text",
        )
        self.assertIn("Hello from PDF", extracted.text)

    def test_extracts_pdf_hex_text(self) -> None:
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Length 53 >>\nstream\n"
            b"BT\n/F1 12 Tf\n72 712 Td\n<48656c6c6f2066726f6d20504446> Tj\nET\n"
            b"endstream\nendobj\n%%EOF"
        )
        extracted = extract_uploaded_document(
            UploadedDocumentInput(
                file_name="resume.pdf",
                content_type="application/pdf",
                data=pdf_bytes,
            ),
            field_name="resume_text",
        )
        self.assertIn("Hello from PDF", extracted.text)

    def test_extracts_ascii85_flate_pdf_text(self) -> None:
        content_stream = b"BT\n/F1 12 Tf\n72 712 Td\n(Compressed PDF text) Tj\nET\n"
        encoded_stream = base64.a85encode(zlib.compress(content_stream), adobe=True)
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Filter [/ASCII85Decode /FlateDecode] /Length "
            + str(len(encoded_stream)).encode("ascii")
            + b" >>\nstream\n"
            + encoded_stream
            + b"\nendstream\nendobj\n%%EOF"
        )
        extracted = extract_uploaded_document(
            UploadedDocumentInput(
                file_name="resume.pdf",
                content_type="application/pdf",
                data=pdf_bytes,
            ),
            field_name="resume_text",
        )
        self.assertIn("Compressed PDF text", extracted.text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
