"""Tests for Phase 0: Safety, cleanup, permissions, and git cache tracking checks."""

import os
import subprocess
import time
from pathlib import Path
import pytest

from config import (
    REPO_ROOT,
    atomic_write,
    check_git_tracked_cache,
    cleanup_old_artifacts,
    set_owner_only_permissions,
)


class TestGitIgnoreRules:
    """Verify check-ignore passes for all required sensitive patterns."""

    @pytest.mark.parametrize(
        "pattern",
        [
            ".cache/sample.json",
            ".env",
            "archive.zip",
            "storage_state.json",
            "site_memory.json",
            "traces/run1.trace",
            "profiles/default/Cookies",
        ],
    )
    def test_check_ignore_passes_for_sensitive_patterns(self, pattern: str):
        res = subprocess.run(
            ["git", "check-ignore", pattern],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert res.returncode == 0, f"Expected {pattern} to be ignored by git, but git check-ignore returned {res.returncode}"
        assert pattern in res.stdout or Path(pattern).name in res.stdout or any(p in res.stdout for p in pattern.split("/"))


class TestStartupCacheWarning:
    """Startup check warns if .cache files are git-tracked."""

    def test_startup_warning_fires_on_tracked_fixture(self, tmp_path: Path, monkeypatch):
        # Create a mock git repository with a tracked file in .cache
        repo_dir = tmp_path / "mock_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=str(repo_dir), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(repo_dir), check=True)

        cache_dir = repo_dir / ".cache"
        cache_dir.mkdir()
        leak_file = cache_dir / "leaked_session.json"
        leak_file.write_text('{"token": "secret"}', encoding="utf-8")

        subprocess.run(["git", "add", "-f", str(leak_file)], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "commit", "-m", "leaked cache"], cwd=str(repo_dir), check=True)

        warnings_caught = []
        import config
        monkeypatch.setattr(config.logger, "warning", lambda msg: warnings_caught.append(msg))

        tracked = check_git_tracked_cache(repo_dir=repo_dir)
        assert len(tracked) >= 1
        assert any("leaked_session.json" in t for t in tracked)
        assert any("SECURITY WARNING" in w for w in warnings_caught)

    def test_startup_warning_empty_on_clean_repo(self):
        # In current repo, .cache should not be tracked
        tracked = check_git_tracked_cache(repo_dir=REPO_ROOT)
        assert tracked == []


class TestAtomicWritesAndPermissions:
    """Verify atomic write semantics and owner-only permissions."""

    def test_atomic_write_json_and_read(self, tmp_path: Path):
        target = tmp_path / "subdir" / "state.json"
        data = {"session_id": "test_123", "logged_in": True}

        result_path = atomic_write(target, data, owner_only=True)
        assert result_path.exists()
        assert target.exists()

        import json
        read_back = json.loads(target.read_text(encoding="utf-8"))
        assert read_back == data

    def test_owner_only_permissions(self, tmp_path: Path):
        target = tmp_path / "sensitive.txt"
        target.write_text("secret", encoding="utf-8")

        ok = set_owner_only_permissions(target)
        assert ok is True
        assert target.exists()


class TestCleanupJob:
    """Verify cleanup job removes traces/screenshots older than 7 days."""

    def test_cleanup_deletes_older_files_preserves_new(self, tmp_path: Path):
        test_dir = tmp_path / "artifacts"
        test_dir.mkdir()

        old_file = test_dir / "old_trace.zip"
        old_file.write_text("old trace content", encoding="utf-8")
        # Set mtime to 8 days ago
        eight_days_ago = time.time() - (8 * 86400)
        os.utime(str(old_file), (eight_days_ago, eight_days_ago))

        new_file = test_dir / "recent_screenshot.png"
        new_file.write_text("new screenshot content", encoding="utf-8")
        # Set mtime to 1 day ago
        one_day_ago = time.time() - (1 * 86400)
        os.utime(str(new_file), (one_day_ago, one_day_ago))

        deleted = cleanup_old_artifacts(days=7, directories=[test_dir])

        assert old_file in deleted
        assert not old_file.exists()
        assert new_file.exists()
