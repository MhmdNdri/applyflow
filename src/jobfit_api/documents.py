"""Helpers for profile document uploads and text extraction."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import io
import re
from typing import Iterable
import xml.etree.ElementTree as ET
import zipfile
import zlib


MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
TEXT_EXTENSIONS = {
    ".txt",
    ".text",
    ".md",
    ".markdown",
    ".rst",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".log",
}


@dataclass(slots=True)
class UploadedDocumentInput:
    file_name: str
    content_type: str | None
    data: bytes

    @property
    def size_bytes(self) -> int:
        return len(self.data)


@dataclass(slots=True)
class ExtractedDocument:
    text: str
    file_name: str
    content_type: str | None
    size_bytes: int
    raw_bytes: bytes


def extract_uploaded_document(upload: UploadedDocumentInput, *, field_name: str) -> ExtractedDocument:
    if not upload.file_name.strip():
        raise ValueError(f"{field_name} upload must include a file name.")
    if not upload.data:
        raise ValueError(f"{field_name} upload is empty.")
    if upload.size_bytes > MAX_DOCUMENT_BYTES:
        raise ValueError(f"{field_name} upload exceeds the 5 MB limit.")

    suffix = normalized_suffix(upload.file_name)
    content_type = (upload.content_type or "").lower()

    if suffix == ".pdf" or content_type == "application/pdf":
        text = extract_pdf_text(upload.data)
    elif suffix == ".docx" or content_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        text = extract_docx_text(upload.data)
    else:
        text = extract_text_file(upload.data)

    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError(
            f"{field_name} upload did not contain readable text. "
            "If this file is a scanned or image-only PDF, paste the text manually or export it as a searchable PDF/DOCX."
        )

    return ExtractedDocument(
        text=normalized_text,
        file_name=upload.file_name.strip(),
        content_type=upload.content_type.strip() if upload.content_type else None,
        size_bytes=upload.size_bytes,
        raw_bytes=upload.data,
    )


def normalized_suffix(file_name: str) -> str:
    lowered = file_name.lower().strip()
    if "." not in lowered:
        return ""
    return lowered[lowered.rfind(".") :]


def extract_text_file(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1252", "latin1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def extract_docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ValueError("The DOCX file could not be read.") from exc

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        runs = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
        ]
        joined = "".join(runs).strip()
        if joined:
            paragraphs.append(joined)
    return "\n\n".join(paragraphs)


def extract_pdf_text(data: bytes) -> str:
    streams = iter_pdf_streams(data)
    chunks: list[str] = []
    for stream in streams:
        decoded = decode_pdf_stream(stream)
        if not decoded:
            continue
        text = extract_pdf_stream_text(decoded)
        if text:
            chunks.append(text)
    return "\n\n".join(chunk for chunk in chunks if chunk.strip())


def iter_pdf_streams(data: bytes) -> Iterable[tuple[bytes, bytes]]:
    pattern = re.compile(rb"(<<.*?>>)\s*stream\r?\n(.*?)\r?\nendstream", re.S)
    return pattern.findall(data)


def decode_pdf_stream(stream_match: tuple[bytes, bytes]) -> bytes:
    header, payload = stream_match
    decoded = payload
    filters = extract_pdf_filter_names(header)
    if not filters:
        return decoded

    for filter_name in filters:
        try:
            if filter_name in {"FlateDecode", "Fl"}:
                decoded = zlib.decompress(decoded)
            elif filter_name in {"ASCIIHexDecode", "AHx"}:
                decoded = decode_ascii_hex(decoded)
            elif filter_name in {"ASCII85Decode", "A85"}:
                decoded = decode_ascii85(decoded)
            else:
                return b""
        except (ValueError, zlib.error, binascii.Error):
            return b""
    return decoded


def extract_pdf_filter_names(header: bytes) -> list[str]:
    match = re.search(rb"/Filter\s*(\[(.*?)\]|/[^/\s<>\[\]()]+)", header, re.S)
    if not match:
        return []

    raw_value = match.group(1)
    return [
        name.decode("latin-1")
        for name in re.findall(rb"/([A-Za-z0-9]+)", raw_value)
    ]


def decode_ascii_hex(data: bytes) -> bytes:
    cleaned = re.sub(rb"\s+", b"", data).rstrip(b">")
    if len(cleaned) % 2 == 1:
        cleaned += b"0"
    if not cleaned:
        return b""
    return bytes.fromhex(cleaned.decode("ascii"))


def decode_ascii85(data: bytes) -> bytes:
    cleaned = re.sub(rb"\s+", b"", data)
    if not cleaned:
        return b""
    if cleaned.startswith(b"<~") and cleaned.endswith(b"~>"):
        return base64.a85decode(cleaned, adobe=True)
    return base64.a85decode(cleaned, adobe=False)


def extract_pdf_stream_text(data: bytes) -> str:
    text = data.decode("latin-1", errors="ignore")
    literals: list[str] = []

    literals.extend(parse_pdf_text_operators(text))
    if not literals and "TJ" not in text and "Tj" not in text:
        literals.extend(parse_pdf_literal_strings(text))

    normalized = "\n".join(chunk for chunk in (cleanup_pdf_text(item) for item in literals) if chunk)
    return normalized


def parse_pdf_text_operators(text: str) -> list[str]:
    matches: list[str] = []
    literal_or_hex_tj = re.findall(r"(\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]+>)\s*Tj", text)
    for match in literal_or_hex_tj:
        parsed = parse_pdf_text_token(match)
        if parsed:
            matches.append(parsed)

    for block in re.findall(r"\[(.*?)\]\s*TJ", text, re.S):
        pieces = re.findall(r"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]+>", block)
        if not pieces:
            continue
        parsed_pieces = [parse_pdf_text_token(piece) for piece in pieces]
        joined = "".join(piece for piece in parsed_pieces if piece)
        if joined:
            matches.append(joined)
    return matches


def parse_pdf_literal_strings(text: str) -> list[str]:
    matches = [parse_pdf_literal(match) for match in re.findall(r"\((?:\\.|[^\\()])*\)", text)]
    matches.extend(
        parse_pdf_hex_literal(match)
        for match in re.findall(r"<[0-9A-Fa-f\s]+>", text)
    )
    return matches


def parse_pdf_text_token(token: str) -> str:
    if token.startswith("("):
        return parse_pdf_literal(token)
    if token.startswith("<"):
        return parse_pdf_hex_literal(token)
    return ""


def parse_pdf_literal(literal: str) -> str:
    body = literal[1:-1]
    body = body.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
    body = body.replace(r"\n", "\n").replace(r"\r", "\r").replace(r"\t", "\t")

    def replace_octal(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 8))

    return re.sub(r"\\([0-7]{1,3})", replace_octal, body)


def parse_pdf_hex_literal(literal: str) -> str:
    body = re.sub(r"\s+", "", literal[1:-1])
    if not body:
        return ""
    if len(body) % 2 == 1:
        body += "0"
    try:
        data = bytes.fromhex(body)
    except ValueError:
        return ""
    return decode_pdf_text_bytes(data)


def decode_pdf_text_bytes(data: bytes) -> str:
    if not data:
        return ""
    if data.startswith((b"\xfe\xff", b"\xff\xfe")):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            pass
    if b"\x00" in data and len(data) % 2 == 0:
        try:
            return data.decode("utf-16-be")
        except UnicodeDecodeError:
            pass
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="ignore")


def cleanup_pdf_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    return re.sub(r"[ \t]+", " ", stripped)
