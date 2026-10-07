"""Configuration and safety infrastructure for Orion and Nebula.

Global rules enforced:
- pathlib and relative repo roots (no hardcoded absolute paths)
- Atomic file writes (temp + rename)
- Owner-only permissions on sensitive files (session, traces, site memory)
- Cleanup jobs for traces and screenshots older than 7 days
- Startup checks warning if cache files are git-tracked
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable, List, Optional, Union

logger = logging.getLogger("orion.config")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Root directory resolution (dynamic, portable)
REPO_ROOT = Path(__file__).resolve().parent
CACHE_DIR = REPO_ROOT / ".cache"
TRACES_DIR = REPO_ROOT / "traces"
PROFILES_DIR = REPO_ROOT / "profiles"
TASKS_DIR = CACHE_DIR / "tasks"
STORAGE_STATE_FILE = REPO_ROOT / "storage_state.json"
SITE_MEMORY_FILE = CACHE_DIR / "site_memory.json"
LOGS_DIR = REPO_ROOT / "logs"

# Ensure runtime directories exist
for directory in (CACHE_DIR, TRACES_DIR, PROFILES_DIR, TASKS_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def set_owner_only_permissions(path: Union[str, Path]) -> bool:
    """Restricts access of target file/directory to owner only."""
    p = Path(path)
    if not p.exists():
        return False

    try:
        if sys.platform == "win32":
            # On Windows, try setting icacls to grant current user full control and remove inheritance
            username = os.environ.get("USERNAME") or os.environ.get("USER")
            if username:
                subprocess.run(
                    ["icacls", str(p), "/inheritance:r", "/grant:r", f"{username}:(F)"],
                    capture_output=True,
                    check=False,
                )
        # Also enforce POSIX/standard stat mode (0600 for file, 0700 for dir)
        if p.is_dir():
            p.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        else:
            p.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return True
    except Exception as e:
        logger.warning(f"Failed to set owner-only permissions on {p}: {e}")
        return False


def atomic_write(
    target_path: Union[str, Path],
    content: Union[str, bytes, dict, list],
    owner_only: bool = False,
    encoding: str = "utf-8",
) -> Path:
    """Atomically writes content to a target file via temp file + atomic replace."""
    dest = Path(target_path).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Serialize if dict/list
    if isinstance(content, (dict, list)):
        raw_data = json.dumps(content, indent=2).encode(encoding)
    elif isinstance(content, str):
        raw_data = content.encode(encoding)
    elif isinstance(content, bytes):
        raw_data = content
    else:
        raise TypeError(f"Unsupported content type for atomic_write: {type(content)}")

    # Use a temp file in the same directory to guarantee atomic rename across filesystem boundaries
    fd, temp_path = tempfile.mkstemp(dir=str(dest.parent), prefix=".tmp_atomic_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw_data)
            f.flush()
            os.fsync(f.fileno())

        if owner_only:
            set_owner_only_permissions(temp_path)

        # Atomic replacement
        os.replace(temp_path, dest)
        if owner_only:
            set_owner_only_permissions(dest)
        return dest
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def cleanup_old_artifacts(
    days: int = 7,
    directories: Optional[Iterable[Path]] = None,
) -> List[Path]:
    """Deletes traces, screenshots, and logs older than the specified retention days."""
    cutoff_time = time.time() - (days * 86400)
    target_dirs = list(directories) if directories else [TRACES_DIR, CACHE_DIR, LOGS_DIR]
    deleted_files: List[Path] = []

    target_extensions = {".zip", ".png", ".jpg", ".jpeg", ".webm", ".log", ".trace"}

    for base_dir in target_dirs:
        p_dir = Path(base_dir)
        if not p_dir.exists():
            continue

        for item in p_dir.rglob("*"):
            if item.is_file() and item.suffix.lower() in target_extensions:
                try:
                    mtime = item.stat().st_mtime
                    if mtime < cutoff_time:
                        item.unlink(missing_ok=True)
                        deleted_files.append(item)
                        logger.info(f"Cleaned up expired artifact: {item}")
                except Exception as e:
                    logger.warning(f"Error checking/deleting artifact {item}: {e}")

    return deleted_files


def check_git_tracked_cache(repo_dir: Optional[Union[str, Path]] = None) -> List[str]:
    """Startup check: inspects git to verify no .cache files are git-tracked.
    Emits a high-priority warning if any tracked files exist.
    """
    root = Path(repo_dir) if repo_dir else REPO_ROOT
    try:
        res = subprocess.run(
            ["git", "ls-files", ".cache"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        tracked = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        if tracked:
            warning_msg = (
                f"SECURITY WARNING: {len(tracked)} file(s) under .cache are tracked by Git: "
                f"{tracked}. Untrack immediately with 'git rm -r --cached .cache'!"
            )
            logger.warning(warning_msg)
            sys.stderr.write(warning_msg + "\n")
            return tracked
        return []
    except Exception as e:
        logger.debug(f"Git check skipped or failed: {e}")
        return []


# Run safety check on module load if within git repo
_tracked_cache_warning = check_git_tracked_cache(REPO_ROOT)
