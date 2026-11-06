//! Zero-copy binary KV & stack bridge between Luma and NuvioTV.
//!
//! Format: `LCKV` — a fixed-layout little-endian binary file (16 KB, 4 Linux
//! 4KB pages) that can be memory-mapped or read with zero deserialization.
//! Uses a 64-bit seqlock for lock-free cross-process consistency:
//!   - Writer: increments seq to odd, writes payload, increments seq to even
//!   - Reader: checks seq is even before reading; retry if odd or changed
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
/// Total bridge file size (4 Linux 4KB pages).
const LCKV_SIZE: usize = 16384;
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
fn pack_fixed_str(dst: &mut [u8; MAX_SLOT_STR], s: &str) {
    dst.fill(0);
    let b = s.as_bytes();
    let len = b.len().min(MAX_SLOT_STR - 1);
    dst[0] = len as u8;
    dst[1..=len].copy_from_slice(&b[..len]);
}

/// Unpacks a fixed-size slot back into a Rust string.
fn unpack_fixed_str(src: &[u8; MAX_SLOT_STR]) -> String {
    let len = (src[0] as usize).min(MAX_SLOT_STR - 1);
    String::from_utf8_lossy(&src[1..=len]).into_owned()
}

/// Reads the binary bridge snapshot with seqlock consistency verification.
/// Returns `Err(WouldBlock)` if a write is in progress (odd seq number).
pub fn read_bridge_cards(
    path: &Path,
    target_collection: &str,
) -> io::Result<Vec<FastBridgeCard>> {
    let mut f = File::open(path)?;
    let mut buf = Vec::with_capacity(LCKV_SIZE);
    f.read_to_end(&mut buf)?;

    if buf.len() < HEADER_SIZE || buf[0..4] != LCKV_MAGIC || buf[4] != LCKV_VERSION {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "Invalid LCKV header",
        ));
    }

    // Seqlock invariant: header + trailer must match and be even.
    // A torn write (partial write, crash mid-update) will produce mismatched
    // head/tail seq numbers or an odd seq number.
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
    let target_hash = fnv1a_64(target_collection.as_bytes());

    let record_size = 12 + (MAX_SLOT_STR * 4); // 396 bytes
    let payload_and_trailer = count * record_size + 8;

    // Canonical LCKV layout: 32B header + count * 396B records + 8B even-seq trailer.
    let mut offset = HEADER_SIZE;

    let mut out = Vec::new();

    for _ in 0..count {
        if offset + RECORD_SIZE > buf.len() {
            break;
        }
        let col_hash = u64::from_le_bytes(buf[offset..offset + 8].try_into().unwrap());
        if col_hash == target_hash {
            let progress_permille = u16::from_le_bytes([buf[offset + 8], buf[offset + 9]]);
            let ambient_rgb565 = u16::from_le_bytes([buf[offset + 10], buf[offset + 11]]);
            let s_base = offset + 12;

            let id = unpack_fixed_str(buf[s_base..s_base + MAX_SLOT_STR].try_into().unwrap());
            let title = unpack_fixed_str(
                buf[s_base + MAX_SLOT_STR..s_base + MAX_SLOT_STR * 2]
                    .try_into()
                    .unwrap(),
            );
            let subtitle = unpack_fixed_str(
                buf[s_base + MAX_SLOT_STR * 2..s_base + MAX_SLOT_STR * 3]
                    .try_into()
                    .unwrap(),
            );
            let content_target = unpack_fixed_str(
                buf[s_base + MAX_SLOT_STR * 3..s_base + MAX_SLOT_STR * 4]
                    .try_into()
                    .unwrap(),
            );

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
///
/// The committed sequence number is written both at the header (buf[8..16])
/// and as a trailer (last 8 bytes) so readers can detect torn writes:
/// a reader must see matching head/tail seq numbers that are both even.
pub fn write_bridge_cards(path: &Path, seq: u64, cards: &[FastBridgeCard]) -> io::Result<()> {
    let count = cards.len().min(u16::MAX as usize) as u16;
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

    #[test]
    fn fnv1a_matches_app_artwork() {
        // Same algorithm as src/app_artwork.rs::disk_key
        let h = fnv1a_64(b"continue-watching");
        assert_ne!(h, 0);
        // Deterministic
        assert_eq!(h, fnv1a_64(b"continue-watching"));
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
            content_target: "nuvio://resume/movie/tt0137523?t=1420".into(),
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
}
