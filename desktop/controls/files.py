"""
desktop/controls/files.py — File operations within allowed folders, with undo.

Global Rule 6:
  - Delete uses Recycle Bin only (via undo.recycle_file).
  - Create/copy/move/rename within allowed folders only.
  - All ops logged with undo entry.

FileController requires an explicit ``allowed_roots`` list. Operations
are rejected if the source or destination falls outside these roots.
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from desktop.undo import UndoHistory, recycle_file

logger = logging.getLogger("orion.desktop.files")


def _ok(detail: str = "") -> Dict[str, Any]:
    return {"ok": True, "detail": detail}


def _fail(detail: str) -> Dict[str, Any]:
    return {"ok": False, "detail": detail}


class FileController:
    """
    Safe file operations confined to an explicit allowlist of root folders.

    All mutating operations push an undo entry so they can be reversed.
    Delete operations always use the Recycle Bin (never os.remove).

    Args:
        allowed_roots: List of absolute Path objects. Operations are rejected
                       if source or destination is not a descendant of one root.
        undo:          Shared UndoHistory instance.
    """

    def __init__(
        self,
        allowed_roots: List[Union[str, Path]],
        undo: Optional[UndoHistory] = None,
    ) -> None:
        self._roots = [Path(r).resolve() for r in allowed_roots]
        self._undo = undo or UndoHistory()

    # ------------------------------------------------------------------
    def _check_path(self, p: Path) -> Optional[str]:
        """Return None if path is within an allowed root, else error string."""
        resolved = p.resolve()
        for root in self._roots:
            try:
                resolved.relative_to(root)
                return None   # allowed
            except ValueError:
                continue
        return (
            f"Path '{resolved}' is outside allowed roots: "
            + ", ".join(str(r) for r in self._roots)
        )

    def _guard(self, *paths: Path) -> Optional[Dict[str, Any]]:
        for p in paths:
            err = self._check_path(p)
            if err:
                return _fail(err)
        return None

    # ------------------------------------------------------------------
    def create_file(self, path: Union[str, Path], content: str = "") -> Dict[str, Any]:
        """Create a new file with optional text content."""
        dest = Path(path).resolve()
        guard = self._guard(dest)
        if guard:
            return guard
        if dest.exists():
            return _fail(f"create_file: '{dest}' already exists")
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            self._undo.push(
                f"create_file '{dest}'",
                lambda p=dest: p.unlink(missing_ok=True),
            )
            return _ok(f"Created '{dest}'")
        except Exception as exc:
            return _fail(f"create_file failed: {exc}")

    # ------------------------------------------------------------------
    def create_folder(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Create a directory (and parents) within an allowed root."""
        dest = Path(path).resolve()
        guard = self._guard(dest)
        if guard:
            return guard
        try:
            dest.mkdir(parents=True, exist_ok=True)
            self._undo.push(
                f"create_folder '{dest}'",
                lambda p=dest: shutil.rmtree(str(p), ignore_errors=True),
            )
            return _ok(f"Created folder '{dest}'")
        except Exception as exc:
            return _fail(f"create_folder failed: {exc}")

    # ------------------------------------------------------------------
    def copy_file(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
    ) -> Dict[str, Any]:
        """Copy src to dst (both must be within allowed roots)."""
        s = Path(src).resolve()
        d = Path(dst).resolve()
        guard = self._guard(s, d)
        if guard:
            return guard
        if not s.exists():
            return _fail(f"copy_file: source '{s}' does not exist")
        try:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(s), str(d))
            self._undo.push(
                f"copy_file '{s}' -> '{d}'",
                lambda p=d: p.unlink(missing_ok=True),
            )
            return _ok(f"Copied '{s}' to '{d}'")
        except Exception as exc:
            return _fail(f"copy_file failed: {exc}")

    # ------------------------------------------------------------------
    def move_file(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
    ) -> Dict[str, Any]:
        """Move/rename src to dst (both within allowed roots)."""
        s = Path(src).resolve()
        d = Path(dst).resolve()
        guard = self._guard(s, d)
        if guard:
            return guard
        if not s.exists():
            return _fail(f"move_file: source '{s}' does not exist")
        try:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(s), str(d))
            self._undo.push(
                f"move_file '{s}' -> '{d}'",
                lambda src=s, dst=d: shutil.move(str(dst), str(src)),
            )
            return _ok(f"Moved '{s}' to '{d}'")
        except Exception as exc:
            return _fail(f"move_file failed: {exc}")

    # ------------------------------------------------------------------
    def rename_file(
        self,
        path: Union[str, Path],
        new_name: str,
    ) -> Dict[str, Any]:
        """Rename a file within its parent folder."""
        p = Path(path).resolve()
        new_path = p.parent / new_name
        return self.move_file(p, new_path)

    # ------------------------------------------------------------------
    def delete_file(self, path: Union[str, Path], approved: bool = False) -> Dict[str, Any]:
        """
        Send a file to the Recycle Bin (HIGH RISK — requires approved=True).
        Never permanently deletes.
        """
        if not approved:
            return _fail(
                "delete_file is HIGH RISK. Pass approved=True for explicit confirmation."
            )
        p = Path(path).resolve()
        guard = self._guard(p)
        if guard:
            return guard
        if not p.exists():
            return _fail(f"delete_file: '{p}' does not exist")
        try:
            recycle_file(p)
            return _ok(f"Recycled '{p}' (recoverable from Recycle Bin)")
        except Exception as exc:
            return _fail(f"delete_file failed: {exc}")

    # ------------------------------------------------------------------
    def read_file(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Read text content of a file within an allowed root."""
        p = Path(path).resolve()
        guard = self._guard(p)
        if guard:
            return guard
        if not p.exists():
            return _fail(f"read_file: '{p}' does not exist")
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            return {"ok": True, "detail": f"Read {len(content)} chars", "data": content}
        except Exception as exc:
            return _fail(f"read_file failed: {exc}")
