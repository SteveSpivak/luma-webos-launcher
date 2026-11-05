"""Compatibility import path for immutable historical lg-luma unit tests.
Keep original imported scripts/tests and source blob SHAs byte-for-byte unchanged.
Only available when PYTHONPATH=lab/legacy-luma/compat is explicitly set.
"""
from pathlib import Path
import sys
ORIGINAL=Path(__file__).resolve().parents[3]/"scripts"
if not (ORIGINAL/"analyze_native_diagnostics.py").is_file():
    raise ImportError("pinned historical diagnostics source missing")
sys.path.insert(0,str(ORIGINAL))
from analyze_native_diagnostics import analyze, nearest_rank
