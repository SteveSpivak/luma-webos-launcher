//! Nivío Continue Watching consumer service.
//!
//! Luma never constructs playback targets or manages Nivío accounts. Luma
//! only fetches stack items (title, poster, contentTarget) from a future
//! Nivío producer API and renders them as cards. Clicking a card launches
//! the title via `Effect::NuvioLaunch` (Phase 1), which Nivío's own
//! deep-link receiver handles.
//!
//! This service follows the exact Jellyfin/Plex `Service` pattern: a worker
//! thread with `mpsc` channels, `Command::Fetch` → `Response::Items`.
//!
//! Data sources (in priority order):
//!   1. LCKV binary bridge file (`LUMA_NUVIO_BRIDGE_PATH`, default
//!      `/tmp/nuvio_stacks.lckv`) — zero-copy read, written by a
//!      NuvioTV-side producer (not yet confirmed in the inspected Nuvio
//!      repository; see cross-repo forensic review).
//!   2. Synthetic fixtures — used when the bridge file is absent, so the
//!      consumer side can be developed and tested in isolation.
//! Until a Nivío producer contract is authorized, `fetch()` returns synthetic
//! fixtures so the consumer side can be developed and tested in isolation.

use crate::fast_kv::{default_bridge_path, read_bridge_cards, FastBridgeCard};
use crate::stacks::StackItem;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Mutex, mpsc};
use std::thread;

/// Maximum items per collection (matches `stacks::HOME_ROW_MAX`).
const MAX_ITEMS_PER_COLLECTION: usize = 20;

pub enum Command {
    /// Cards for (stack index, collection id).
    Fetch(Vec<(usize, String)>),
}

pub enum Response {
    Items(usize, Vec<StackItem>),
}

pub struct Service {
    sender: Mutex<mpsc::Sender<Command>>,
    pub receiver: Mutex<mpsc::Receiver<Response>>,
}

/// Bumped by every Fetch; synthetic-fixture generation stops when it moves.
static FETCH_ATTEMPT: AtomicU64 = AtomicU64::new(0);

impl Service {
    pub fn new(_cache: PathBuf) -> Self {
        let (sender, commands) = mpsc::channel::<Command>();
        let (reply, receiver) = mpsc::channel();
        thread::spawn(move || {
            for command in commands {
                match command {
                    Command::Fetch(stacks) => fetch(&reply, stacks),
                }
            }
        });
        Self {
            sender: Mutex::new(sender),
            receiver: Mutex::new(receiver),
        }
    }

    pub fn send(&self, command: Command) {
        let _ = self.sender.lock().unwrap().send(command);
    }
}

/// Fetch stack items for each (index, collection) pair. Results are sent
/// back as `Response::Items(index, items)` so `main.rs` can write them into
/// `state.stack_items[index]`.
///
/// Reads the LCKV binary bridge first; falls back to synthetic fixtures
/// when the bridge file is absent or contains no items for the collection.
fn fetch(reply: &mpsc::Sender<Response>, stacks: Vec<(usize, String)>) {
    let bridge_path = default_bridge_path();
    for (index, collection) in stacks {
        let items = bridge_items(&bridge_path, &collection)
            .unwrap_or_else(|| match collection.as_str() {
                "continue-watching" => continue_watching_items(),
                "watchlist" => watchlist_items(),
                "library" => library_items(),
                _ => vec![],
            });
        let bounded: Vec<StackItem> = items.into_iter().take(MAX_ITEMS_PER_COLLECTION).collect();
        FETCH_ATTEMPT.fetch_add(1, Ordering::SeqCst);
        let _ = reply.send(Response::Items(index, bounded));
    }
}

/// Extracts the bare "tt" IMDb id (e.g. "tt0137523") from a card id that
/// may include episode suffixes (e.g. "tt0137523:1:2").
fn imdb_id(id: &str) -> &str {
    id.split(':').next().unwrap_or(id).trim()
}

/// Derives a Stremio Metahub CDN poster URL (2:3 vertical) from a "tt" id.
/// Live domain: https://images.metahub.space/poster/medium/{tt}/img
fn metahub_poster_url(id: &str) -> Option<String> {
    let base = imdb_id(id);
    if base.starts_with("tt") && base.len() >= 7 && base[2..].chars().all(|c| c.is_ascii_digit()) {
        return Some(format!("https://images.metahub.space/poster/medium/{base}/img"));
    }
    None
}

/// Derives a Stremio Metahub CDN still URL (16:9 landscape) from a "tt" id.
/// Live domain: https://images.metahub.space/background/medium/{tt}/img
fn metahub_still_url(id: &str) -> Option<String> {
    let base = imdb_id(id);
    if base.starts_with("tt") && base.len() >= 7 && base[2..].chars().all(|c| c.is_ascii_digit()) {
        return Some(format!("https://images.metahub.space/background/medium/{base}/img"));
    }
    None
}

/// Reads cards from the LCKV binary bridge for a collection, converting them
/// to `StackItem`s. Returns `None` only if the bridge file is missing or
/// unreadable (caller falls back to synthetic). Returns `Some(vec![])` when
/// the bridge exists but contains no items for the collection — a valid empty
/// snapshot means show nothing, not synthetic demo content.
fn bridge_items(bridge_path: &PathBuf, collection: &str) -> Option<Vec<StackItem>> {
    let cards = match read_bridge_cards(bridge_path, collection) {
        Ok(cards) => cards,
        Err(_) => return None,
    };
    Some(
        cards
            .into_iter()
            .enumerate()
            .map(|(seq, c)| StackItem {
                title: c.title,
                poster: None,
                // Deterministic per-item identity: FNV-1a-64 of the card's
                // unique id, mixed with its sequence position so two cards
                // with the same id in different collections never collide,
                // and two cards in the same collection always differ.
                id: unique_card_id(&c.id, &c.content_target, seq),
                content_target: c.content_target,
                progress_permille: c.progress_permille,
                poster_url: metahub_poster_url(&c.id),
                still_url: metahub_still_url(&c.id),
            })
            .collect(),
    )
}

/// Derives a deterministic positive i64 identity for a single bridge card.
/// Uses FNV-1a-64 of the card id mixed with the content target and sequence
/// position, so every card in a collection has a unique id.
fn unique_card_id(card_id: &str, content_target: &str, seq: usize) -> i64 {
    let mut h = crate::fast_kv::fnv1a_64(card_id.as_bytes());
    h ^= crate::fast_kv::fnv1a_64(content_target.as_bytes()).rotate_left(13);
    h = h.wrapping_add(seq as u64);
    // Keep strictly positive i64 (> 0)
    let positive = (h & 0x7FFF_FFFF_FFFF_FFC0) | ((seq as u64) & 0x3F);
    positive.max(1) as i64
}
}

/// Synthetic Continue Watching items — replaced by real Nivío producer API.
/// Each item carries a `content_target` so the card can launch via Phase 1.
fn continue_watching_items() -> Vec<StackItem> {
    vec![StackItem {
        title: "Example Movie".into(),
        poster: None,
        id: 1,
        content_target: String::new(),
        progress_permille: 0,
        poster_url: None,
        still_url: None,
    }]
}

/// Synthetic Watchlist items — replaced by real Nivío producer API.
fn watchlist_items() -> Vec<StackItem> {
    vec![]
}

/// Synthetic Library items — replaced by real Nivío producer API.
fn library_items() -> Vec<StackItem> {
    vec![]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fetch_returns_items_for_continue_watching() {
        let (reply, receiver) = mpsc::channel();
        fetch(&reply, vec![(0, "continue-watching".to_owned())]);
        let response = receiver.recv_timeout(std::time::Duration::from_secs(5)).unwrap();
        match response {
            Response::Items(index, items) => {
                assert_eq!(index, 0);
                assert_eq!(items.len(), 1);
                assert_eq!(items[0].title, "Example Movie");
            }
            _ => panic!("unexpected response: {response:?}"),
        }
    }

    #[test]
    fn fetch_returns_empty_for_watchlist_and_library() {
        let (reply, receiver) = mpsc::channel();
        fetch(&reply, vec![(0, "watchlist".to_owned()), (1, "library".to_owned())]);
        let r1 = receiver.recv_timeout(std::time::Duration::from_secs(5)).unwrap();
        let r2 = receiver.recv_timeout(std::time::Duration::from_secs(5)).unwrap();
        match (r1, r2) {
            (Response::Items(0, items), Response::Items(1, _)) => {
                assert!(items.is_empty());
            }
            _ => panic!("unexpected responses: {r1:?}, {r2:?}"),
        }
    }

    #[test]
    fn fetch_bounded_to_max_items() {
        // Synthetic fixtures return fewer than MAX_ITEMS_PER_COLLECTION,
        // but the take() bound guarantees the limit regardless of source.
        let (reply, receiver) = mpsc::channel();
        fetch(&reply, vec![(0, "continue-watching".to_owned())]);
        let response = receiver.recv_timeout(std::time::Duration::from_secs(5)).unwrap();
        match response {
            Response::Items(_, items) => {
                assert!(items.len() <= MAX_ITEMS_PER_COLLECTION);
            }
            _ => panic!("unexpected response: {response:?}"),
        }
    }
}
