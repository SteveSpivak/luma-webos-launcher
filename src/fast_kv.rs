//! Zero-copy binary KV & stack bridge between Luma and NuvioTV.
//!
//! Format: `LCKV` — a fixed-layout little-endian binary file that can be
//! read with zero deserialization. Uses a committed even sequence number
//! written at both the header (offset 8) and trailer (last 8 bytes) for
//! torn-read detection: a reader accepts the file only when head and tail
//! sequence numbers match and are both even.
//!
//! Layout: 32-byte header + count * 396-byte records + 8-byte trailer.
//! No 16 KB cap is enforced by the writer; callers must size their own
//! fixtures within whatever limit the producer contract allows.
//!
//! Compatible with any language: Rust reads via zero-copy slicing,
//! TypeScript/JS reads via a single `DataView` over an `ArrayBuffer`.

use std::fs::{File, OpenOptions};
use std::io::{self, Read, Write};
use std::path::Path;

const LCKV_MAGIC: [u8; 4] = *b"LCKV";
const LCKV_VERSION: u8 = 1;
/// Max bytes per fixed string slot (includes 1-byte length prefix).
const MAX_SLOT_STR: usize = 96;
/// Canonical bridge file size cap: 4 Linux 4KB pages = 16,384 bytes.
/// Writer MUST NOT exceed this; reader rejects files larger than this.
/// Matches Nuvio contract (40 cards max = 15,880 bytes <= 16,384).
pub const MAX_BRIDGE_BYTES: usize = 16_384;
/// Maximum 40 cards across all collections: 32 + (40 * 396) + 8 = 15,880 <= 16,384.
pub const MAX_BRIDGE_CARDS: usize = 40;
/// Header size: magic(4) + version(1) + padding(3) + count(2) + seq(8) + crc(4) + reserved(12) = 32
const HEADER_SIZE: usize = 32;
/// Trailer size: seq(8) — written at EOF for torn-read detection.
const TRAILER_SIZE: usize = 8;
/// Record size: collection_hash(8) + progress_permille(2) + ambient_rgb565(2) + 4 string slots(96*4) = 396
const RECORD_SIZE: usize = 396;

/// One continue-watching / watchlist / library card in the binary bridge.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FastBridgeCard {
    /// FNV-1a 64-bit hash of the collection id (e.g. "continue-watching").
    pub collection_hash: u64,
    /// Watch progress in permille (0..1000; 645 = 64.5% watched).
    pub progress_permille: u16,
    /// Precomputed OLED-safe ambient glow color as RGB565.
    pub ambient_rgb565: u16,
    pub id: String,
    pub title: String,
    pub subtitle: String,
    pub content_target: String,
}

/// FNV-1a 64-bit hash — same as used in `src/app_artwork.rs::disk_key`.
#[inline]
pub const fn fnv1a_64(bytes: &[u8]) -> u64 {
    let mut hash: u64 = 0xcbf29ce484222325;
    let mut i = 0;
    while i < bytes.len() {
        hash ^= bytes[i] as u64;
        hash = hash.wrapping_mul(0x100000001b3);
        i += 1;
    }
    hash
}

/// Packs a Rust string into a fixed-size slot: [len: u8][bytes...][0-padding].
/// Backs up `len` to a UTF-8 character boundary so multibyte codepoints are
/// never split mid-codepoint at slot edges.
fn pack_fixed_str(dst: &mut [u8; MAX_SLOT_STR], s: &str) {
    dst.fill(0);
    let b = s.as_bytes();
    let mut len = b.len().min(MAX_SLOT_STR - 1);
    while len > 0 && !s.is_char_boundary(len) {
        len -= 1;
    }
    dst[0] = len as u8;
    dst[1..=len].copy_from_slice(&b[..len]);
}

/// Unpacks a fixed-size slot back into a Rust string.
/// Validates the length byte and UTF-8 integrity; returns an error on corruption.
fn unpack_fixed_str(src: &[u8; MAX_SLOT_STR]) -> io::Result<String> {
    let len = src[0] as usize;
    if len >= MAX_SLOT_STR {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "LCKV string length byte exceeds slot capacity",
        ));
    }
    std::str::from_utf8(&src[1..1 + len])
        .map(|s| s.to_owned())
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "Invalid UTF-8 in LCKV slot"))
}

/// Reads the binary bridge snapshot with torn-read verification.
/// Returns `Err(WouldBlock)` if head/tail sequence numbers mismatch or
/// are odd (a write may be in progress or the file was torn).
pub fn read_bridge_cards(
    path: &Path,
    target_collection: &str,
) -> io::Result<Vec<FastBridgeCard>> {
    let mut f = File::open(path)?;
    let mut buf = Vec::with_capacity(MAX_BRIDGE_BYTES);
    f.read_to_end(&mut buf)?;

    // Reject files outside the canonical 16 KB size cap.
    if buf.len() > MAX_BRIDGE_BYTES {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!(
                "LCKV file size {} exceeds MAX_BRIDGE_BYTES {}",
                buf.len(),
                MAX_BRIDGE_BYTES
            ),
        ));
    }

    if buf.len() < HEADER_SIZE || buf[0..4] != LCKV_MAGIC || buf[4] != LCKV_VERSION {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "Invalid LCKV header",
        ));
    }

    // Torn-read invariant: header + trailer sequence numbers must match
    // and be even. A torn write (partial write, crash mid-update) will
    // produce mismatched head/tail seq numbers or an odd seq number.
    if buf.len() < HEADER_SIZE + TRAILER_SIZE {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "LCKV file too short for header + trailer",
        ));
    }
    let seq_head = u64::from_le_bytes(buf[8..16].try_into().unwrap());
    let seq_tail = u64::from_le_bytes(
        buf[buf.len() - TRAILER_SIZE..].try_into().unwrap(),
    );
    if (seq_head & 1) == 1 || seq_head != seq_tail {
        return Err(io::Error::new(
            io::ErrorKind::WouldBlock,
            "Bridge write in progress or torn read",
        ));
    }

    let count = u16::from_le_bytes([buf[6], buf[7]]) as usize;
    if count > MAX_BRIDGE_CARDS {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!(
                "LCKV record count {} exceeds MAX_BRIDGE_CARDS {}",
                count, MAX_BRIDGE_CARDS
            ),
        ));
    }
    let target_hash = fnv1a_64(target_collection.as_bytes());

    let record_size = 12 + (MAX_SLOT_STR * 4); // 396 bytes

    // Canonical LCKV layout: 32B header + count * 396B records + 8B even-seq trailer.
    // Max file size: 32 + (40 * 396) + 8 = 15,880 bytes <= 16,384 bytes (4 pages).
    // The file must be exactly this size; any shorter or longer file is corruption.
    let expected_len = HEADER_SIZE + count * record_size + TRAILER_SIZE;
    if buf.len() != expected_len {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!(
                "LCKV file length mismatch: expected {expected_len}, got {}",
                buf.len()
            ),
        ));
    }

    let mut offset = HEADER_SIZE;

    let mut out = Vec::new();

    for _ in 0..count {
        if offset + RECORD_SIZE > buf.len() {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "LCKV record truncated mid-file",
            ));
        }
        let col_hash = u64::from_le_bytes(buf[offset..offset + 8].try_into().unwrap());
        if col_hash == target_hash {
            let progress_permille = u16::from_le_bytes([buf[offset + 8], buf[offset + 9]]);
            if progress_permille > 1000 {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    format!(
                        "LCKV progress_permille {} exceeds 1000 at record offset {}",
                        progress_permille, offset
                    ),
                ));
            }
            let ambient_rgb565 = u16::from_le_bytes([buf[offset + 10], buf[offset + 11]]);
            let s_base = offset + 12;

            let id = unpack_fixed_str(buf[s_base..s_base + MAX_SLOT_STR].try_into().unwrap())?;
            let title = unpack_fixed_str(
                buf[s_base + MAX_SLOT_STR..s_base + MAX_SLOT_STR * 2]
                    .try_into()
                    .unwrap(),
            )?;
            let subtitle = unpack_fixed_str(
                buf[s_base + MAX_SLOT_STR * 2..s_base + MAX_SLOT_STR * 3]
                    .try_into()
                    .unwrap(),
            )?;
            let content_target = unpack_fixed_str(
                buf[s_base + MAX_SLOT_STR * 3..s_base + MAX_SLOT_STR * 4]
                    .try_into()
                    .unwrap(),
            )?;

            out.push(FastBridgeCard {
                collection_hash: col_hash,
                progress_permille,
                ambient_rgb565,
                id,
                title,
                subtitle,
                content_target,
            });
        }
        offset += RECORD_SIZE;
    }

    Ok(out)
}

/// Atomically writes cards to the binary bridge file.
/// Writes to a temp file then renames for POSIX atomicity.
/// The committed sequence number (always even) is written both at the
/// header (buf[8..16]) and as a trailer (last 8 bytes) so readers can
/// detect torn writes: a reader must see matching head/tail seq numbers
/// that are both even.
///
/// Kept `#[allow(dead_code)]` because it is part of the public LCKV bridge
/// contract and is exercised by unit tests; it is wired into the `luma labs
/// --module nuvio` preview seeder for production call sites.
#[allow(dead_code)]
pub fn write_bridge_cards(path: &Path, seq: u64, cards: &[FastBridgeCard]) -> io::Result<()> {
    let count = cards.len();
    if count > MAX_BRIDGE_CARDS {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            format!(
                "card count {} exceeds MAX_BRIDGE_CARDS {}",
                count, MAX_BRIDGE_CARDS
            ),
        ));
    }
    let count = count as u16;
    let payload_size = HEADER_SIZE + count as usize * RECORD_SIZE;
    let mut buf = vec![0u8; payload_size + TRAILER_SIZE];

    buf[0..4].copy_from_slice(&LCKV_MAGIC);
    buf[4] = LCKV_VERSION;
    buf[6..8].copy_from_slice(&count.to_le_bytes());
    // Commit with an even sequence number.
    let committed_seq = seq & !1;
    buf[8..16].copy_from_slice(&committed_seq.to_le_bytes());

    let mut offset = HEADER_SIZE;
    for c in cards.iter().take(count as usize) {
        buf[offset..offset + 8].copy_from_slice(&c.collection_hash.to_le_bytes());
        buf[offset + 8..offset + 10]
            .copy_from_slice(&c.progress_permille.to_le_bytes());
        buf[offset + 10..offset + 12]
            .copy_from_slice(&c.ambient_rgb565.to_le_bytes());

        let s_base = offset + 12;
        let mut slot = [0u8; MAX_SLOT_STR];

        pack_fixed_str(&mut slot, &c.id);
        buf[s_base..s_base + MAX_SLOT_STR].copy_from_slice(&slot);

        pack_fixed_str(&mut slot, &c.title);
        buf[s_base + MAX_SLOT_STR..s_base + MAX_SLOT_STR * 2]
            .copy_from_slice(&slot);

        pack_fixed_str(&mut slot, &c.subtitle);
        buf[s_base + MAX_SLOT_STR * 2..s_base + MAX_SLOT_STR * 3]
            .copy_from_slice(&slot);

        pack_fixed_str(&mut slot, &c.content_target);
        buf[s_base + MAX_SLOT_STR * 3..s_base + MAX_SLOT_STR * 4]
            .copy_from_slice(&slot);

        offset += RECORD_SIZE;
    }

    // Trailer: repeat committed_seq for torn-read detection.
    buf[payload_size..payload_size + TRAILER_SIZE]
        .copy_from_slice(&committed_seq.to_le_bytes());

    let tmp_path = path.with_extension("lckv.tmp");
    {
        let mut f = OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .open(&tmp_path)?;
        f.write_all(&buf)?;
    }
    std::fs::rename(&tmp_path, path)?;
    Ok(())
}

/// Returns the default bridge path: `$LUMA_NUVIO_BRIDGE_PATH` or
/// `/tmp/nuvio_stacks.lckv` (tmpfs on most LG webOS TVs).
pub fn default_bridge_path() -> std::path::PathBuf {
    std::env::var("LUMA_NUVIO_BRIDGE_PATH")
        .ok()
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| std::path::PathBuf::from("/tmp/nuvio_stacks.lckv"))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Verified FNV-1a-64 constants (offset 0xcbf29ce484222325, prime 0x100000001b3):
    ///   "continue-watching" → 0x01aa2aebbc61d6f6
    ///   "watchlist"         → 0xa05bdde6192df670
    ///   "library"           → 0xe029b3e5014c2890
    #[test]
    fn fnv1a_known_constants() {
        assert_eq!(
            fnv1a_64(b"continue-watching"),
            0x01aa2aebbc61d6f6u64
        );
        assert_eq!(fnv1a_64(b"watchlist"), 0xa05bdde6192df670u64);
        assert_eq!(fnv1a_64(b"library"), 0xe029b3e5014c2890u64);
    }

    #[test]
    fn fnv1a_deterministic() {
        assert_eq!(
            fnv1a_64(b"continue-watching"),
            fnv1a_64(b"continue-watching")
        );
    }

    #[test]
    fn round_trip_write_read() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.lckv");

        let cards = vec![FastBridgeCard {
            collection_hash: fnv1a_64(b"continue-watching"),
            progress_permille: 645,
            ambient_rgb565: 0x18E3,
            id: "tt0137523".into(),
            title: "The Matrix".into(),
            subtitle: "1999 · Sci-Fi".into(),
            content_target: "nuvio://tmdb/movie/603".into(),
        }];

        write_bridge_cards(&path, 42, &cards).unwrap();
        let read = read_bridge_cards(&path, "continue-watching").unwrap();
        assert_eq!(read.len(), 1);
        assert_eq!(read[0].title, "The Matrix");
        assert_eq!(read[0].progress_permille, 645);
        assert_eq!(read[0].ambient_rgb565, 0x18E3);

        // Wrong collection returns empty.
        let empty = read_bridge_cards(&path, "watchlist").unwrap();
        assert!(empty.is_empty());
    }

    #[test]
    fn rejects_truncated_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("truncated.lckv");

        // Build a valid 2-card file via write_bridge_cards, then truncate
        // the trailer + part of the last record while keeping count=2.
        let cards = vec![
            FastBridgeCard {
                collection_hash: fnv1a_64(b"continue-watching"),
                progress_permille: 645,
                ambient_rgb565: 0x18E3,
                id: "tt0137523".into(),
                title: "The Matrix".into(),
                subtitle: "1999 · Sci-Fi".into(),
                content_target: "nuvio://tmdb/movie/603".into(),
            },
            FastBridgeCard {
                collection_hash: fnv1a_64(b"watchlist"),
                progress_permille: 100,
                ambient_rgb565: 0x0000,
                id: "tt0068646".into(),
                title: "The Godfather".into(),
                subtitle: "1972 · Crime".into(),
                content_target: "nuvio://tmdb/movie/603".into(),
            },
        ];
        write_bridge_cards(&path, 42, &cards).unwrap();
        let mut buf = std::fs::read(&path).unwrap();
        // Truncate last 10 bytes: removes trailer (8) + 2 bytes of last record.
        buf.truncate(buf.len() - 10);
        // Patch count to still claim 2 records → expected_len > actual len.
        buf[6..8].copy_from_slice(&2u16.to_le_bytes());
        std::fs::write(&path, &buf).unwrap();

        let result = read_bridge_cards(&path, "continue-watching");
        assert!(result.is_err());
        assert_eq!(result.unwrap_err().kind(), io::ErrorKind::InvalidData);
    }

    #[test]
    fn rejects_oversized_count() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("oversized.lckv");

        // Write a valid 1-card file, then patch count to MAX_BRIDGE_CARDS + 1.
        let cards = vec![FastBridgeCard {
            collection_hash: fnv1a_64(b"continue-watching"),
            progress_permille: 645,
            ambient_rgb565: 0x18E3,
            id: "tt0137523".into(),
            title: "The Matrix".into(),
            subtitle: "1999 · Sci-Fi".into(),
            content_target: "nuvio://tmdb/movie/603".into(),
        }];
        write_bridge_cards(&path, 42, &cards).unwrap();
        let mut buf = std::fs::read(&path).unwrap();
        buf[6..8].copy_from_slice(&(MAX_BRIDGE_CARDS as u16 + 1).to_le_bytes());
        std::fs::write(&path, &buf).unwrap();

        let result = read_bridge_cards(&path, "continue-watching");
        assert!(result.is_err());
    }

    #[test]
    fn rejects_exceeds_max_bridge_bytes() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("oversize.lckv");

        // Write a file larger than MAX_BRIDGE_BYTES.
        let buf = vec![0u8; MAX_BRIDGE_BYTES + 1];
        std::fs::write(&path, &buf).unwrap();

        let result = read_bridge_cards(&path, "continue-watching");
        assert!(result.is_err());
    }

    #[test]
    fn rejects_invalid_utf8_in_slot() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("bad_utf8.lckv");

        // Build a valid 1-card file via write_bridge_cards, then inject
        // invalid UTF-8 (0xFF) as the first content byte of the id slot.
        let cards = vec![FastBridgeCard {
            collection_hash: fnv1a_64(b"continue-watching"),
            progress_permille: 645,
            ambient_rgb565: 0x18E3,
            id: "tt0137523".into(),
            title: "The Matrix".into(),
            subtitle: "1999 · Sci-Fi".into(),
            content_target: "nuvio://tmdb/movie/603".into(),
        }];
        write_bridge_cards(&path, 42, &cards).unwrap();
        let mut buf = std::fs::read(&path).unwrap();
        // id slot starts at HEADER_SIZE + 12, byte 1 is the first content byte.
        let id_slot_content_start = HEADER_SIZE + 12 + 1;
        buf[id_slot_content_start] = 0xFF;
        std::fs::write(&path, &buf).unwrap();

        let result = read_bridge_cards(&path, "continue-watching");
        assert!(result.is_err());
        assert_eq!(result.unwrap_err().kind(), io::ErrorKind::InvalidData);
    }

    #[test]
    fn accepts_seq_zero() {
        // seq == 0 is valid (even, head==tail). Only odd seq or mismatch
        // should be rejected.
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("seq_zero.lckv");
        let cards = vec![FastBridgeCard {
            collection_hash: fnv1a_64(b"continue-watching"),
            progress_permille: 645,
            ambient_rgb565: 0x18E3,
            id: "tt0137523".into(),
            title: "The Matrix".into(),
            subtitle: "1999 · Sci-Fi".into(),
            content_target: "nuvio://tmdb/movie/603".into(),
        }];
        write_bridge_cards(&path, 0, &cards).unwrap();
        let result = read_bridge_cards(&path, "continue-watching");
        assert!(result.is_ok());
        assert_eq!(result.unwrap().len(), 1);
    }

    #[test]
    fn rejects_odd_seq() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("odd_seq.lckv");
        let cards = vec![FastBridgeCard {
            collection_hash: fnv1a_64(b"continue-watching"),
            progress_permille: 645,
            ambient_rgb565: 0x18E3,
            id: "tt0137523".into(),
            title: "The Matrix".into(),
            subtitle: "1999 · Sci-Fi".into(),
            content_target: "nuvio://tmdb/movie/603".into(),
        }];
        write_bridge_cards(&path, 42, &cards).unwrap();
        let mut buf = std::fs::read(&path).unwrap();
        // Set both head and tail seq to odd (3).
        buf[8..16].copy_from_slice(&3u64.to_le_bytes());
        let tail_start = buf.len() - TRAILER_SIZE;
        buf[tail_start..tail_start + 8].copy_from_slice(&3u64.to_le_bytes());
        std::fs::write(&path, &buf).unwrap();

        let result = read_bridge_cards(&path, "continue-watching");
        assert!(result.is_err());
        assert_eq!(result.unwrap_err().kind(), io::ErrorKind::WouldBlock);
    }

    #[test]
    fn rejects_torn_seq() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("torn_seq.lckv");
        let cards = vec![FastBridgeCard {
            collection_hash: fnv1a_64(b"continue-watching"),
            progress_permille: 645,
            ambient_rgb565: 0x18E3,
            id: "tt0137523".into(),
            title: "The Matrix".into(),
            subtitle: "1999 · Sci-Fi".into(),
            content_target: "nuvio://tmdb/movie/603".into(),
        }];
        write_bridge_cards(&path, 42, &cards).unwrap();
        let mut buf = std::fs::read(&path).unwrap();
        // Head seq = 2, tail seq = 4 (mismatch → torn write).
        buf[8..16].copy_from_slice(&2u64.to_le_bytes());
        let tail_start = buf.len() - TRAILER_SIZE;
        buf[tail_start..tail_start + 8].copy_from_slice(&4u64.to_le_bytes());
        std::fs::write(&path, &buf).unwrap();

        let result = read_bridge_cards(&path, "continue-watching");
        assert!(result.is_err());
        assert_eq!(result.unwrap_err().kind(), io::ErrorKind::WouldBlock);
    }

    #[test]
    fn rejects_invalid_progress_permille() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("bad_progress.lckv");
        let cards = vec![FastBridgeCard {
            collection_hash: fnv1a_64(b"continue-watching"),
            progress_permille: 645,
            ambient_rgb565: 0x18E3,
            id: "tt0137523".into(),
            title: "The Matrix".into(),
            subtitle: "1999 · Sci-Fi".into(),
            content_target: "nuvio://tmdb/movie/603".into(),
        }];
        write_bridge_cards(&path, 42, &cards).unwrap();
        let mut buf = std::fs::read(&path).unwrap();
        // progress_permille is at HEADER_SIZE + 8, 2 bytes.
        let prog_offset = HEADER_SIZE + 8;
        buf[prog_offset..prog_offset + 2].copy_from_slice(&1001u16.to_le_bytes());
        std::fs::write(&path, &buf).unwrap();

        let result = read_bridge_cards(&path, "continue-watching");
        assert!(result.is_err());
        assert_eq!(result.unwrap_err().kind(), io::ErrorKind::InvalidData);
    }

    #[test]
    fn golden_436_lckv_single_card_round_trip() {
        // Golden fixture: 1 card, seq=2, collection="continue-watching",
        // id="tt0133093", content_target="nuvio://tmdb/movie/603".
        // Exact size: 32 header + 396 record + 8 trailer = 436 bytes.
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("golden-436.lckv");

        let cards = vec![FastBridgeCard {
            collection_hash: 0x01aa2aebbc61d6f6u64,
            progress_permille: 645,
            ambient_rgb565: 0x18E3,
            id: "tt0133093".into(),
            title: "The Matrix".into(),
            subtitle: "1999 · Sci-Fi".into(),
            content_target: "nuvio://tmdb/movie/603".into(),
        }];

        write_bridge_cards(&path, 2, &cards).unwrap();

        // Exact byte-length assertion.
        let buf = std::fs::read(&path).unwrap();
        assert_eq!(buf.len(), 436, "golden-436.lckv must be exactly 436 bytes");

        // Round-trip decode must recover the card exactly.
        let read = read_bridge_cards(&path, "continue-watching").unwrap();
        assert_eq!(read.len(), 1);
        assert_eq!(read[0].collection_hash, 0x01aa2aebbc61d6f6u64);
        assert_eq!(read[0].progress_permille, 645);
        assert_eq!(read[0].ambient_rgb565, 0x18E3);
        assert_eq!(read[0].id, "tt0133093");
        assert_eq!(read[0].title, "The Matrix");
        assert_eq!(read[0].subtitle, "1999 · Sci-Fi");
        assert_eq!(read[0].content_target, "nuvio://tmdb/movie/603");
    }

    #[test]
    fn tombstone_40_lckv_empty_bridge_round_trip() {
        // Tombstone fixture: 0 cards, seq=4 — valid empty bridge (authoritative empty state).
        // Exact size: 32 header + 0 records + 8 trailer = 40 bytes.
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("tombstone-40.lckv");

        write_bridge_cards(&path, 4, &[]).unwrap();

        // Exact byte-length assertion.
        let buf = std::fs::read(&path).unwrap();
        assert_eq!(buf.len(), 40, "tombstone-40.lckv must be exactly 40 bytes");

        // Round-trip decode must return empty vec (valid empty snapshot, not synthetic fallback).
        let read = read_bridge_cards(&path, "continue-watching").unwrap();
        assert_eq!(read.len(), 0);

        // Any other collection on an empty bridge also returns empty.
        let read_wl = read_bridge_cards(&path, "watchlist").unwrap();
        assert_eq!(read_wl.len(), 0);
    }

    #[test]
    fn pack_fixed_str_utf8_boundary_exact_fit() {
        // A 95-byte ASCII string fits exactly (1 len byte + 95 content bytes = 96).
        let s = "a".repeat(95);
        let mut slot = [0u8; MAX_SLOT_STR];
        pack_fixed_str(&mut slot, &s);
        assert_eq!(slot[0], 95);
        assert_eq!(&slot[1..96], s.as_bytes());
    }

    #[test]
    fn pack_fixed_str_utf8_backup_on_multibyte() {
        // "héllo" is 6 bytes but 5 chars. If slot only has room for 5 bytes,
        // we must back up to a char boundary (byte 4 = "h" + "é" first byte would be split).
        // With MAX_SLOT_STR-1 = 95, a string whose 96th byte is a continuation byte
        // must be truncated at the previous char boundary.
        let s = "é".repeat(48); // 48 chars × 2 bytes = 96 bytes, but slot max is 95 content bytes
        let mut slot = [0u8; MAX_SLOT_STR];
        pack_fixed_str(&mut slot, &s);
        let len = slot[0] as usize;
        // len must be a valid char boundary
        assert!(s.is_char_boundary(len));
        // The unpacked string must be valid UTF-8
        let unpacked = std::str::from_utf8(&slot[1..1 + len]).unwrap();
        assert_eq!(unpacked.chars().count(), len / 2); // each "é" is 2 bytes
    }
}
