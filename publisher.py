# -*- coding: utf-8 -*-
"""Publish generated HTML output to the GitHub Pages repository."""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from config import (
    BASE_DIR,
    GENERATED_HTML,
    OUTPUT_DIR,
    PUBLISH_BRANCH,
    PUBLISHED_HTML,
    PUBLISHED_URL,
    PUBLISH_EXTRA_ASSETS,
    SITE_REPOSITORY,
)

COMMIT_MESSAGE = "Daily site update"
GIT = "git"

log = logging.getLogger("scanner")


def publish_site(html_path: Optional[Path] = None) -> bool:
    """Copy generated site files and push them from the publication repo.

    Args:
        html_path: Path to the HTML file produced by the generator. If omitted,
            the configured default ``output/<GENERATED_HTML>`` is used.

    Returns:
        True when publication completed or there was nothing to commit. False
        when a required path is missing or a git command fails.
    """
    log.info("Starting publication...")

    source_html = _resolve_generated_html(html_path)
    site_repo = _resolve_path(SITE_REPOSITORY, BASE_DIR)
    if not _validate_paths(source_html, site_repo):
        return False
    if not _prepare_repository(site_repo):
        return False

    log.info("Copying generated HTML...")
    try:
        _copy_file(source_html, site_repo / PUBLISHED_HTML)
        if not _copy_extra_assets(site_repo):
            return False
    except OSError as exc:
        log.error("Failed to copy publication files: %s", exc)
        return False
    log.info("Copied successfully.")

    log.info("Running git add...")
    published_paths = _published_git_paths()
    if not _run_git(["add", "--", *published_paths], site_repo):
        return False

    if not _has_staged_changes(site_repo, published_paths):
        log.info("Nothing changed.")
        return _verify_published_content(source_html)

    log.info("Running git commit...")
    if not _run_git(["commit", "-m", COMMIT_MESSAGE, "--", *published_paths], site_repo):
        return False

    log.info("Running git push...")
    push_result = _run_git(["push", "origin", PUBLISH_BRANCH], site_repo)
    if not push_result:
        log.error("Git push failed; publication files were committed locally.")
        return False
    if not _verify_remote_head(site_repo):
        log.error("Git push returned success, but origin/%s was not verified.",
                  PUBLISH_BRANCH)
        return False
    if not _verify_published_content(source_html):
        log.error("GitHub Pages did not serve the generated landing in time.")
        return False

    log.info("Publication completed successfully.")
    return True


def _verify_published_content(
    source_html: Path,
    *,
    requester: Optional[Callable] = None,
    sleeper=time.sleep,
    attempts: int = 1000,
    delay_seconds: float = 5.0,
    deadline_seconds: float = 900.0,
    clock=time.monotonic,
) -> bool:
    """Wait until the public URL serves the generated build."""
    expected_bytes = source_html.read_bytes()
    expected_digest = hashlib.sha256(expected_bytes).hexdigest()
    marker_match = re.search(
        rb'<meta name="bank-analyst-build" content="([^"]+)">',
        expected_bytes[:16384],
    )
    expected_marker = marker_match.group(0) if marker_match else b""
    separator = "&" if "?" in PUBLISHED_URL else "?"
    deadline = clock() + deadline_seconds
    for attempt in range(attempts):
        # GitHub's CDN may cache a pre-deployment response for ten minutes,
        # even with Cache-Control: no-cache.  A unique URL per poll avoids
        # poisoning every later verification attempt with that stale object.
        nonce = time.time_ns()
        url = (
            f"{PUBLISHED_URL}{separator}published={expected_digest[:16]}"
            f"&attempt={attempt}-{nonce}"
        )
        if requester is None:
            result = subprocess.run(
                [
                    "curl", "--fail", "--location", "--silent",
                    "--show-error", "--max-time", "20",
                    "--header", "Cache-Control: no-cache",
                    *(["--range", "0-16383"] if expected_marker else []),
                    url,
                ],
                capture_output=True,
                check=False,
            )
            status_code = 200 if result.returncode == 0 else 0
            content = result.stdout
            if result.returncode != 0:
                error = result.stderr.decode("utf-8", errors="replace").strip()
                if error:
                    log.warning("Public landing verification failed: %s", error)
        else:
            response = requester(
                url,
                headers={"Cache-Control": "no-cache"},
                timeout=10,
            )
            status_code = getattr(response, "status_code", 0)
            content = response.content
        content_matches = (
            expected_marker in content
            if expected_marker
            else hashlib.sha256(content).hexdigest() == expected_digest
        )
        if status_code == 200 and content_matches:
            log.info("Published landing verified: %s", PUBLISHED_URL)
            return True
        remaining = deadline - clock()
        if attempt + 1 >= attempts or remaining <= 0:
            break
        sleeper(min(delay_seconds, remaining))
    return False


def _prepare_repository(site_repo: Path) -> bool:
    """Require a clean branch state and update it before creating a commit."""
    git_dir = site_repo / ".git"
    if any((git_dir / marker).exists() for marker in (
        "rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD",
    )):
        log.error("Publication repository has an unfinished Git operation.")
        return False

    branch = _git_output(["branch", "--show-current"], site_repo)
    if branch != PUBLISH_BRANCH:
        shown = branch or "detached HEAD"
        log.error("Publication repository must be on %s; current state: %s.",
                  PUBLISH_BRANCH, shown)
        return False

    log.info("Updating publication branch before copying files...")
    return _run_git(
        ["pull", "--rebase", "origin", PUBLISH_BRANCH], site_repo,
    )


def _verify_remote_head(site_repo: Path) -> bool:
    """Confirm that the remote publication branch points at local HEAD."""
    local_head = _git_output(["rev-parse", "HEAD"], site_repo)
    remote_line = _git_output(
        ["ls-remote", "origin", f"refs/heads/{PUBLISH_BRANCH}"], site_repo,
    )
    remote_head = remote_line.split()[0] if remote_line else ""
    return bool(local_head and remote_head and local_head == remote_head)


def _resolve_generated_html(html_path: Optional[Path]) -> Path:
    """Return the generated HTML path from the caller or configuration."""
    if html_path is not None:
        return _resolve_path(Path(html_path), BASE_DIR)
    return OUTPUT_DIR / GENERATED_HTML


def _resolve_path(path: Path, base_dir: Path) -> Path:
    """Resolve relative paths against the project root."""
    return path if path.is_absolute() else base_dir / path


def _validate_paths(source_html: Path, site_repo: Path) -> bool:
    """Validate required source and destination paths before publishing."""
    if not source_html.exists():
        log.error("Generated HTML not found: %s", source_html)
        return False
    if not source_html.is_file():
        log.error("Generated HTML path is not a file: %s", source_html)
        return False
    if not site_repo.exists():
        log.error("Publication repository not found: %s", site_repo)
        return False
    if not (site_repo / ".git").exists():
        log.error("Publication path is not a git repository: %s", site_repo)
        return False
    return True


def _copy_file(source: Path, destination: Path) -> None:
    """Copy one file preserving metadata."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_extra_assets(site_repo: Path) -> bool:
    """Copy configured additional site assets."""
    for source, destination in PUBLISH_EXTRA_ASSETS:
        source_path = _resolve_path(source, BASE_DIR)
        destination_path = _resolve_path(destination, site_repo)
        if not source_path.exists():
            log.error("Configured publication asset not found: %s", source_path)
            return False
        _copy_file(source_path, destination_path)
    return True


def _published_git_paths() -> list[str]:
    """Return paths that publication is allowed to add and commit."""
    paths = [PUBLISHED_HTML]
    paths.extend(str(destination) for _, destination in PUBLISH_EXTRA_ASSETS)
    return paths


def _has_staged_changes(repo_path: Path, paths: list[str]) -> bool:
    """Return True when git has staged changes ready to commit."""
    result = subprocess.run(
        [GIT, "diff", "--cached", "--quiet", "--", *paths],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return False
    if result.returncode == 1:
        return True
    _log_git_error(result)
    return False


def _run_git(args: list[str], repo_path: Path) -> bool:
    """Run a git command in the publication repository."""
    result = subprocess.run(
        [GIT, *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        _log_git_error(result)
        return False
    return True


def _git_output(args: list[str], repo_path: Path) -> str:
    """Run a read-only git command and return stripped stdout."""
    result = subprocess.run(
        [GIT, *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        _log_git_error(result)
        return ""
    return result.stdout.strip()


def _log_git_error(result: subprocess.CompletedProcess[str]) -> None:
    """Log stderr from a failed git command."""
    stderr = result.stderr.strip() or result.stdout.strip()
    log.error("Git command failed with exit code %s.", result.returncode)
    if stderr:
        log.error(stderr)
