"""Map a concept_id to its file in a bundle, and back.

A concept_id is ``/``-separated, and its file mirrors it under the bundle
root with ``.md`` appended. Two rules make that mapping exact and portable:

* ``.md`` is **appended**, never substituted with ``Path.with_suffix``, which
  would cut a dotted leaf such as ``org.apache.flink:flink-avro`` at its last
  dot and make siblings overwrite each other.
* Characters some filesystems cannot hold in a name (``" * : < > ? | \\``
  and control characters — NTFS forbids them, and ``actions/upload-artifact``
  refuses them) are percent-escaped in the file name only. ``%`` is escaped
  too, so decoding is exact. The concept_id in frontmatter and in
  ``](/<concept_id>.md)`` references keeps its original characters.
"""

from __future__ import annotations

from pathlib import Path, PurePath
from urllib.parse import unquote

_FORBIDDEN = frozenset('"*:<>?|\\%')


def _escape(segment: str) -> str:
    return "".join(
        f"%{ord(ch):02X}" if ch in _FORBIDDEN or ord(ch) < 32 else ch for ch in segment
    )


def concept_rel_path(concept_id: str) -> PurePath:
    """Bundle-relative file path for ``concept_id``.

    Rejects empty, ``.``/``..`` and ``~``-prefixed segments so a crafted
    concept_id cannot escape the bundle directory.
    """
    segments = concept_id.split("/")
    for seg in segments:
        if seg in ("", ".", "..") or seg.startswith("~"):
            raise ValueError(f"unsafe concept_id segment {seg!r} in {concept_id!r}")
    escaped = [_escape(s) for s in segments]
    return PurePath(*escaped[:-1], escaped[-1] + ".md")


def concept_path(concept_id: str, bundle_dir: Path) -> Path:
    """Absolute file path for ``concept_id`` inside ``bundle_dir``."""
    return bundle_dir / concept_rel_path(concept_id)


def concept_file_name(concept_id: str) -> str:
    """File name (no directories) for ``concept_id``."""
    return concept_rel_path(concept_id).name


def concept_id_from_path(rel: PurePath) -> str:
    """Inverse of :func:`concept_rel_path` for a bundle-relative ``.md`` path."""
    parts = list(rel.parts)
    parts[-1] = parts[-1].removesuffix(".md")
    return "/".join(unquote(p) for p in parts)
