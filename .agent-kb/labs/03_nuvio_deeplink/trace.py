#!/usr/bin/env python3
#
# Lab 3: Nuvio Deep-Link Tracer
#
# Simulates the Luma → Nuvio Lab deep-link launch path without a TV or Rust
# toolchain. Validates:
#   - validate_nuvio_target() accepts/rejects correct targets
#   - nuvio_app_id(lab) returns correct ID based on feature flag
#   - nuvio_launch_params_lab() builds correct JSON payload
#   - Production app ID never used for lab launches
#
# Usage:
#   python3 trace.py
#
# Output: Pass/Fail for each contract assertion
#

import json
import sys

# --- Contract constants (must match src/platform.rs) ---
NUVIO_APP_ID = "space.nuvio.webos"
NUVIO_LAB_APP_ID = "space.nuvio.lab"

# --- FNV-1a-64 (for collection hashing, mirrored from fast_kv.rs) ---
FNV_OFFSET = 0xcbf29ce484222325
FNV_PRIME = 0x100000001b3


def fnv1a_64(data: bytes) -> int:
    h = FNV_OFFSET
    for b in data:
        h ^= b
        h = (h * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


# --- validate_nuvio_target (mirrored from src/platform.rs) ---
def validate_nuvio_target(target: str) -> str:
    """Return target if valid, raise ValueError if invalid."""
    invalid_msg = "Invalid Nuvio content target"
    if not target.startswith("nuvio://tmdb/"):
        raise ValueError(invalid_msg)
    rest = target[len("nuvio://tmdb/"):]
    if "/" not in rest:
        raise ValueError(invalid_msg)
    kind, id_part = rest.split("/", 1)
    if kind not in ("movie", "tv"):
        raise ValueError(invalid_msg)
    if not id_part or not all(c.isdigit() for c in id_part):
        raise ValueError(invalid_msg)
    return target


# --- nuvio_app_id (mirrored from src/platform.rs) ---
def nuvio_app_id(lab: bool, feature_nuvio_lab: bool) -> str:
    """Return the Nuvio app ID for the given target mode.
    
    If lab=True but feature_nuvio_lab=False, fall back to production
    to prevent silent runtime override.
    """
    if lab:
        if feature_nuvio_lab:
            return NUVIO_LAB_APP_ID
        else:
            # Lab feature not compiled in: fall back to production
            return NUVIO_APP_ID
    return NUVIO_APP_ID


# --- nuvio_launch_params_lab (mirrored from src/platform.rs) ---
def nuvio_launch_params_lab(content_target: str) -> str:
    """Build launch params JSON for the lab app."""
    return json.dumps({
        "id": NUVIO_LAB_APP_ID,
        "params": {"contentTarget": content_target},
    })


# --- nuvio_launch_params (production) ---
def nuvio_launch_params(content_target: str) -> str:
    """Build launch params JSON for production app."""
    return json.dumps({
        "id": NUVIO_APP_ID,
        "params": {"contentTarget": content_target},
    })


# --- valid_app_id (mirrored from src/model.rs) ---
def valid_app_id(id_str: str) -> bool:
    """Validate app ID format: non-empty, <=128 chars, dot/dash/underscore
    separated alphanumeric parts."""
    if not id_str or len(id_str) > 128:
        return False
    for part in id_str.replace("_", ".").replace("-", ".").split("."):
        if not part:
            return False
        if not all(c.isascii() and c.isalnum() for c in part):
            return False
    return True


# --- Test assertions ---
errors = []

def check(condition: bool, msg: str):
    if condition:
        print(f"  [PASS] {msg}")
    else:
        print(f"  [FAIL] {msg}")
        errors.append(msg)


print("=" * 60)
print("  Lab 3: Nuvio Deep-Link Contract Tracer")
print("=" * 60)

# --- Test 1: validate_nuvio_target accepts valid targets ---
print("\n--- Test 1: validate_nuvio_target accepts valid targets ---")
for target in ["nuvio://tmdb/movie/603", "nuvio://tmdb/tv/129973", "nuvio://tmdb/tv/1"]:
    try:
        result = validate_nuvio_target(target)
        check(result == target, f"accepts {target}")
    except ValueError as e:
        check(False, f"accepts {target} (unexpectedly rejected: {e})")

# --- Test 2: validate_nuvio_target rejects invalid targets ---
print("\n--- Test 2: validate_nuvio_target rejects invalid targets ---")
invalid_targets = [
    "",
    "nuvio://tmdb/movie/",
    "nuvio://tmdb/movie/abc",
    "nuvio://tmdb/movie/603/",
    "nuvio://tmdb/movie/603/extra",
    "nuvio://tmdb/episode/603",
    "nuvio://tmdb/movie/603?autoplay=1",
    "nuvio://other/movie/603",
    "NUVIO://TMDB/MOVIE/603",
    "nuvio://tmdb/movie/603 ",
    "tmdb/movie/603",
    "https://nuvio.example/movie/603",
]
for target in invalid_targets:
    try:
        validate_nuvio_target(target)
        check(False, f"rejects '{target}' (unexpectedly accepted)")
    except ValueError:
        check(True, f"rejects '{target}'")

# --- Test 3: nuvio_app_id production ---
print("\n--- Test 3: nuvio_app_id returns production ID ---")
check(nuvio_app_id(False, False) == NUVIO_APP_ID, "lab=False → production ID")
check(nuvio_app_id(False, True) == NUVIO_APP_ID, "lab=False, feature=nuvio_lab → production ID")

# --- Test 4: nuvio_app_id lab ---
print("\n--- Test 4: nuvio_app_id returns lab ID ---")
check(nuvio_app_id(True, True) == NUVIO_LAB_APP_ID, "lab=True, feature=nuvio_lab → lab ID")
check(nuvio_app_id(True, False) == NUVIO_APP_ID, "lab=True, no feature → production (no silent override)")

# --- Test 5: Launch params ---
print("\n--- Test 5: Launch params build correct JSON ---")
expected_prod = json.dumps({"id": NUVIO_APP_ID, "params": {"contentTarget": "nuvio://tmdb/movie/603"}})
check(nuvio_launch_params("nuvio://tmdb/movie/603") == expected_prod,
      "production params match contract")

expected_lab = json.dumps({"id": NUVIO_LAB_APP_ID, "params": {"contentTarget": "nuvio://tmdb/movie/603"}})
check(nuvio_launch_params_lab("nuvio://tmdb/movie/603") == expected_lab,
      "lab params match contract")

# --- Test 6: App IDs are distinct and valid ---
print("\n--- Test 6: App IDs distinct and valid ---")
check(NUVIO_APP_ID != NUVIO_LAB_APP_ID, "production ID != lab ID")
check(valid_app_id(NUVIO_APP_ID), "production ID passes valid_app_id()")
check(valid_app_id(NUVIO_LAB_APP_ID), "lab ID passes valid_app_id()")

# --- Test 7: FNV-1a constants ---
print("\n--- Test 7: FNV-1a-64 constants verified ---")
cw = fnv1a_64(b"continue-watching")
wl = fnv1a_64(b"watchlist")
lb = fnv1a_64(b"library")
check(cw == 0x01aa2aebbc61d6f6, f"continue-watching = 0x{cw:016x}")
check(wl == 0xa05bdde6192df670, f"watchlist = 0x{wl:016x}")
check(lb == 0xe029b3e5014c2890, f"library = 0x{lb:016x}")

# --- Summary ---
print("\n" + "=" * 60)
if errors:
    print(f"  LAB 3 FAILED — {len(errors)} assertion(s) failed:")
    for e in errors:
        print(f"    - {e}")
    sys.exit(1)
else:
    print("  LAB 3 PASSED — All contract assertions hold")
    sys.exit(0)