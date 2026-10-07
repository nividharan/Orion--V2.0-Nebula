"""
desktop/undo.py — Undo history with 20-item cap; Recycle Bin for file deletes.

Global Rule 6: Delete uses Recycle Bin only.

UndoHistory maintains a LIFO stack of reversible operations.
Each entry records the action, its inverse operation, and metadata.
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("orion.desktop.undo")

_MAX_UNDO_ITEMS = 20


@dataclass
class UndoEntry:
    """One reversible action in the undo stack."""
    action:      str                        # description of what was done
    inverse_fn:  Callable[[], None]         # callable that reverses the action
    metadata:    Dict[str, Any] = field(default_factory=dict)


class UndoHistory:
    """
    Thread-safe LIFO undo stack with a 20-item cap.

    Usage::

        undo = UndoHistory()
        undo.push("moved file X to Y", lambda: shutil.move(str(Y), str(X)))
        undo.pop()   # reverses the last action
    """

    def __init__(self, max_items: int = _MAX_UNDO_ITEMS) -> None:
        self._stack: List[UndoEntry] = []
        self._max = max_items
        self._lock = threading.Lock()

    def push(
        self,
        action: str,
        inverse_fn: Callable[[], None],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a reversible action."""
        with self._lock:
            entry = UndoEntry(
                action=action,
                inverse_fn=inverse_fn,
                metadata=metadata or {},
            )
            self._stack.append(entry)
            # Trim to max
            if len(self._stack) > self._max:
                dropped = self._stack.pop(0)
                logger.debug(f"UndoHistory: dropped oldest entry '{dropped.action}'")

    def pop(self) -> Optional[str]:
        """
        Undo the most recent action.

        Returns the action description string on success, None if stack empty.
        Raises RuntimeError on inverse failure.
        """
        with self._lock:
            if not self._stack:
                return None
            entry = self._stack.pop()

        try:
            entry.inverse_fn()
            logger.info(f"Undo: reversed '{entry.action}'")
            return entry.action
        except Exception as exc:
            raise RuntimeError(
                f"Undo failed for '{entry.action}': {exc}"
            ) from exc

    def peek(self) -> Optional[str]:
        """Return the description of the most recent action without undoing it."""
        with self._lock:
            return self._stack[-1].action if self._stack else None

    def clear(self) -> None:
        """Clear the entire undo stack."""
        with self._lock:
            self._stack.clear()

    @property
    def depth(self) -> int:
        """Current number of undo entries."""
        with self._lock:
            return len(self._stack)


# ---------------------------------------------------------------------------
# Recycle Bin delete (Global Rule 6: Delete uses Recycle Bin only)
# ---------------------------------------------------------------------------

def recycle_file(path: Path) -> None:
    """
    Move a file to the Recycle Bin (Windows) or Trash (macOS/Linux).

    Uses send2trash if available; falls back to `move to .cache/trash/`.
    Never permanently deletes without user approval.
    """
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Cannot recycle non-existent path: {p}")

    try:
        import send2trash  # type: ignore[import]
        send2trash.send2trash(str(p))
        logger.info(f"Recycled: {p}")
    except ImportError:
        # Fallback: move to a local trash folder within the repo
        from config import CACHE_DIR
        trash_dir = CACHE_DIR / "trash"
        trash_dir.mkdir(parents=True, exist_ok=True)
        dest = trash_dir / p.name
        # Avoid overwriting if a file with the same name exists
        counter = 0
        while dest.exists():
            counter += 1
            dest = trash_dir / f"{p.stem}_{counter}{p.suffix}"
        shutil.move(str(p), str(dest))
        logger.info(f"Moved to local trash (send2trash unavailable): {p} -> {dest}")
    except Exception as exc:
        raise RuntimeError(f"Recycle failed for {p}: {exc}") from exc
