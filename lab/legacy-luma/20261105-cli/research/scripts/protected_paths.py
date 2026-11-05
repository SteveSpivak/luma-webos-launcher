"""Single source of truth for which checkout paths count as protected.

Extracted unchanged from ``build_audit.py`` (same literal prefixes/files) so
``luma_cli.py review`` and any future script agree with the audit gate instead
of drifting from a second hand-copied list. Pure data; no filesystem access.
"""
from __future__ import annotations

#: A path under any of these prefixes is protected native/app source.
PREFIXES = ("src/", "tv-helper/", "tv/", "vector-geometry/", "assets/", "tools/", "tests/")

#: Exact protected root files (lockfiles and app identity/config).
FILES = ("Cargo.toml", "Cargo.lock", "package.json", "appinfo.json")


def is_protected(path: str) -> bool:
    """True if ``path`` (repo-relative, forward slashes) is protected."""
    return path.startswith(PREFIXES) or path in FILES


def filter_protected(paths):
    """Protected subset of an iterable of repo-relative paths, in order."""
    return [p for p in paths if is_protected(p)]
