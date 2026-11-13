#!/usr/bin/env python3
#
# Lab 2: LCKV Binary Fixture Generator
#
# Generates canonical LCKV binary bridge files without a Rust toolchain.
# Used to verify the LCKV consumer contract (read-only, seqlock, exact length,
# UTF-8 enforcement) independently of cargo test.
#
# Layout: 32-byte header + count * 396-byte records + 8-byte trailer
#   Header: magic(4) + version(1) + padding(3) + count(2) + seq(8) + crc(4) + reserved(12) = 32
#   Record: fixed 396 bytes (see src/fast_kv.rs FastBridgeCard layout)
#   Trailer: seq(8) — repeated for torn-read detection
#
# Usage:
#   python3 generate.py golden-436       # 1 card, seq=2, exactly 436 bytes
#   python3 generate.py tombstone-40     # 0 cards, seq=4, exactly 40 bytes
#   python3 generate.py all              # Generate all standard fixtures
#
# Output: /tmp/lckv_fixtures/<name>.lckv
#

import os
import struct
import sys

HEADER_SIZE = 32
RECORD_SIZE = 396
TRAILER_SIZE = 8
MAX_BRIDGE_CARDS = 40
MAX_BRIDGE_BYTES = 16_384

OUTPUT_DIR = "/tmp/lckv_fixtures"

# FNV-1a-64 constants (verified independently)
FNV_OFFSET = 0xcbf29ce484222325
FNV_PRIME = 0x100000001b3


def fnv1a_64(data: bytes) -> int:
    h = FNV_OFFSET
    for b in data:
        h ^= b
        h = (h * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


def pack_fixed_str(s: str, max_bytes: int = 96) -> bytes:
    """Pack a string into a fixed slot: 1 length byte + content bytes.
    Back up to UTF-8 char boundary if content exceeds max_bytes."""
    b = s.encode("utf-8")
    if len(b) <= max_bytes - 1:
        return bytes([len(b)]) + b + b"\x00" * (max_bytes - 1 - len(b))
    # Truncate at UTF-8 char boundary
    content = s.encode("utf-8")
    cut = max_bytes - 1
    while cut > 0:
        try:
            content[:cut].decode("utf-8")
            break
        except UnicodeDecodeError:
            cut -= 1
    return bytes([cut]) + content[:cut] + b"\x00" * (max_bytes - 1 - cut)


def make_card(collection_hash: int, progress: int, ambient: int,
              card_id: str, title: str, subtitle: str, content_target: str) -> bytes:
    """Build a 396-byte LCKV record."""
    buf = bytearray(RECORD_SIZE)
    struct.pack_into("<Q", buf, 0, collection_hash)
    struct.pack_into("<H", buf, 8, progress)
    struct.pack_into("<H", buf, 10, ambient)
    buf[12:12 + 96] = pack_fixed_str(card_id)
    buf[108:108 + 96] = pack_fixed_str(title)
    buf[204:204 + 96] = pack_fixed_str(subtitle)
    buf[300:300 + 96] = pack_fixed_str(content_target)
    return bytes(buf)


def write_lckv(path: str, seq: int, cards: list):
    """Write an LCKV file with seqlock header + records + trailer."""
    committed_seq = seq & ~1  # Force even
    count = len(cards)
    total_size = HEADER_SIZE + count * RECORD_SIZE + TRAILER_SIZE

    if total_size > MAX_BRIDGE_BYTES:
        raise ValueError(f"File size {total_size} exceeds MAX_BRIDGE_BYTES {MAX_BRIDGE_BYTES}")
    if count > MAX_BRIDGE_CARDS:
        raise ValueError(f"Card count {count} exceeds MAX_BRIDGE_CARDS {MAX_BRIDGE_CARDS}")

    buf = bytearray(total_size)

    # Header
    buf[0:4] = b"LCKV"  # magic
    buf[4] = 1  # version
    struct.pack_into("<H", buf, 8, count)  # count
    struct.pack_into("<Q", buf, 10, committed_seq)  # seq

    # Records
    offset = HEADER_SIZE
    for card in cards:
        buf[offset:offset + RECORD_SIZE] = card
        offset += RECORD_SIZE

    # Trailer: repeat committed_seq
    struct.pack_into("<Q", buf, total_size - TRAILER_SIZE, committed_seq)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(buf)

    print(f"Wrote {path}: {total_size} bytes ({count} cards, seq={committed_seq})")
    return total_size


def verify_lckv(path: str, expected_size: int, expected_count: int,
                expected_seq: int, collection: str = "continue-watching"):
    """Verify an LCKV file's structure without Rust."""
    with open(path, "rb") as f:
        buf = f.read()

    assert len(buf) == expected_size, f"Size mismatch: {len(buf)} != {expected_size}"
    assert buf[0:4] == b"LCKV", "Bad magic"
    assert buf[4] == 1, "Bad version"
    count = struct.unpack_from("<H", buf, 8)[0]
    seq_head = struct.unpack_from("<Q", buf, 10)[0]
    seq_tail = struct.unpack_from("<Q", buf, len(buf) - TRAILER_SIZE)[0]

    assert count == expected_count, f"Count mismatch: {count} != {expected_count}"
    assert seq_head == seq_tail, f"Seqlock mismatch: head={seq_head} tail={seq_tail}"
    assert seq_head % 2 == 0, f"Odd seq: {seq_head}"
    assert seq_head == expected_seq, f"Seq mismatch: {seq_head} != {expected_seq}"

    print(f"  Verified: size={len(buf)}, count={count}, seq={seq_head} (even, head==tail)")
    return True


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cw_hash = fnv1a_64(b"continue-watching")
    print(f"FNV-1a-64('continue-watching') = 0x{cw_hash:016x}")
    assert cw_hash == 0x01aa2aebbc61d6f6, f"FNV mismatch: 0x{cw_hash:016x}"

    targets = sys.argv[1:] if len(sys.argv) > 1 else ["golden-436", "tombstone-40"]

    for target in targets:
        if target == "golden-436":
            path = os.path.join(OUTPUT_DIR, "golden-436.lckv")
            cards = [make_card(
                collection_hash=cw_hash,
                progress=645,
                ambient=0x18E3,
                card_id="tt0133093",
                title="The Matrix",
                subtitle="1999 · Sci-Fi",
                content_target="nuvio://tmdb/movie/603",
            )]
            size = write_lckv(path, 2, cards)
            verify_lckv(path, 436, 1, 2)
        elif target == "tombstone-40":
            path = os.path.join(OUTPUT_DIR, "tombstone-40.lckv")
            size = write_lckv(path, 4, [])
            verify_lckv(path, 40, 0, 4)
        elif target == "truncated":
            path = os.path.join(OUTPUT_DIR, "truncated.lckv")
            cards = [make_card(
                collection_hash=cw_hash, progress=645, ambient=0x18E3,
                card_id="tt0133093", title="The Matrix",
                subtitle="1999 · Sci-Fi", content_target="nuvio://tmdb/movie/603",
            )]
            write_lckv(path, 2, cards)
            with open(path, "rb") as f:
                buf = bytearray(f.read())
            buf = buf[:-10]  # Remove trailer + 2 bytes
            struct.pack_into("<H", buf, 8, 2)  # Patch count to still claim 2
            with open(path, "wb") as f:
                f.write(buf)
            print(f"Wrote {path}: {len(buf)} bytes (truncated, should fail read)")
        elif target == "odd-seq":
            path = os.path.join(OUTPUT_DIR, "odd-seq.lckv")
            cards = [make_card(
                collection_hash=cw_hash, progress=645, ambient=0x18E3,
                card_id="tt0133093", title="The Matrix",
                subtitle="1999 · Sci-Fi", content_target="nuvio://tmdb/movie/603",
            )]
            write_lckv(path, 3, cards)  # Odd seq
            with open(path, "rb") as f:
                buf = bytearray(f.read())
            struct.pack_into("<Q", buf, len(buf) - TRAILER_SIZE, 3)
            with open(path, "wb") as f:
                f.write(buf)
            print(f"Wrote {path}: odd seq=3 (should fail read with WouldBlock)")
        else:
            print(f"Unknown target: {target}")
            print("Available: golden-436, tombstone-40, truncated, odd-seq, all")
            sys.exit(1)

    print(f"\nAll fixtures generated in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()