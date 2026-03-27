"""Local persistence helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid
from typing import Any

from .config import AppPaths, ConfigurationError
from .constants import CONTEXT_TEMPLATE, RESUME_TEMPLATE


def ensure_data_directories(paths: AppPaths) -> None:
    for directory in (
        paths.data_dir,
        paths.google_dir,
        paths.profile_dir,
        paths.jobs_dir,
        paths.letters_dir,
        paths.runs_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_profile_templates(paths: AppPaths) -> list[Path]:
    created: list[Path] = []
    for target, template in (
        (paths.profile_dir / "resume.md", RESUME_TEMPLATE),
        (paths.profile_dir / "context.md", CONTEXT_TEMPLATE),
    ):
        if target.exists():
            continue
        target.write_text(template, encoding="utf-8")
        created.append(target)
    return created


def load_profile(paths: AppPaths) -> tuple[str, str]:
    resume_path = paths.profile_dir / "resume.md"
    context_path = paths.profile_dir / "context.md"

    missing = [path.name for path in (resume_path, context_path) if not path.exists()]
    if missing:
        joined = ", ".join(missing)
        raise ConfigurationError(
            f"Missing profile files: {joined}. Run `jobfit setup` first."
        )

    resume_text = resume_path.read_text(encoding="utf-8").strip()
    context_text = context_path.read_text(encoding="utf-8").strip()

    if not resume_text or not context_text:
        raise ConfigurationError(
            "Profile files are empty. Fill in both data/profile/resume.md and data/profile/context.md."
        )

    return resume_text, context_text


def compute_profile_hash(resume_text: str, context_text: str) -> str:
    digest = hashlib.sha256()
    digest.update(resume_text.encode("utf-8"))
    digest.update(b"\n---\n")
    digest.update(context_text.encode("utf-8"))
    return digest.hexdigest()


def build_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def archive_job_description(
    paths: AppPaths,
    run_id: str,
    company: str | None,
    role_title: str | None,
    job_description: str,
) -> Path:
    slug = slugify(" ".join(part for part in (company, role_title) if part))
    file_name = f"{run_id}-{slug or 'job-description'}.md"
    target = paths.jobs_dir / file_name
    target.write_text(job_description.strip() + "\n", encoding="utf-8")
    return target


def save_run_record(paths: AppPaths, run_id: str, payload: dict[str, Any]) -> Path:
    target = paths.runs_dir / f"{run_id}.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def save_cover_letter(
    paths: AppPaths,
    run_id: str,
    company: str | None,
    role_title: str | None,
    cover_letter: str,
) -> Path:
    slug = slugify(" ".join(part for part in (company, role_title) if part))
    file_name = f"{run_id}-{slug or 'cover-letter'}.md"
    target = paths.letters_dir / file_name
    target.write_text(cover_letter.strip() + "\n", encoding="utf-8")
    return target


def relative_path(root: Path, target: Path) -> str:
    return target.relative_to(root).as_posix()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized[:60]
