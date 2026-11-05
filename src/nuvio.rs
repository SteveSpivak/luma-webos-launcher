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
//! Until a Nivío producer contract is authorized, `fetch()` returns synthetic
//! fixtures so the consumer side can be developed and tested in isolation.

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
fn fetch(reply: &mpsc::Sender<Response>, stacks: Vec<(usize, String)>) {
    for (index, collection) in stacks {
        let items = match collection.as_str() {
            "continue-watching" => continue_watching_items(),
            "watchlist" => watchlist_items(),
            "library" => library_items(),
            _ => vec![],
        };
        let bounded: Vec<StackItem> = items.into_iter().take(MAX_ITEMS_PER_COLLECTION).collect();
        FETCH_ATTEMPT.fetch_add(1, Ordering::SeqCst);
        let _ = reply.send(Response::Items(index, bounded));
    }
}

/// Synthetic Continue Watching items — replaced by real Nivío producer API.
/// Each item carries a `content_target` so the card can launch via Phase 1.
fn continue_watching_items() -> Vec<StackItem> {
    vec![StackItem {
        title: "Example Movie".into(),
        poster: None,
        id: 1,
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