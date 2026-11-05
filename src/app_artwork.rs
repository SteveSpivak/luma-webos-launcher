//! Installed-app artwork is discovered and decoded on its own worker. The UI
//! requests visible cards only; it uploads finished pixels on the SDL thread.
use crate::model::valid_app_id;
use image::{ImageReader, Limits, RgbaImage};
use serde::Serialize;
use serde_json::Value;
use std::{
    cell::RefCell,
    collections::HashMap,
    fs::File,
    io::{Cursor, Read},
    path::{Component, Path, PathBuf},
    sync::{Arc, mpsc},
    thread,
};

const ROOTS: [&str; 3] = [
    "/media/developer/apps/usr/palm/applications",
    "/media/cryptofs/apps/usr/palm/applications",
    "/usr/palm/applications",
];
pub const MAX_FILE: usize = 512 * 1024;
// Room for every installed app's icon (256 KB each at most), so the Apps
// grid never waits for a decode while its cards fade in.
const CACHE_BYTES: usize = 48 * 1024 * 1024;
const CACHE_ENTRIES: usize = 256;
// Cache app-specific artwork between app launches, not just within a process.
const DISK_ARTWORK_MAX: usize = 768 * 1024;

// Zero-decode binary texture cache (.ltex): 12-byte header + raw RGBA8 or
// RGB565 pixels. Skips PNG/JPEG decompression entirely on cache hits.
const LTEX_MAGIC: [u8; 4] = *b"LTEX";
const LTEX_VERSION: u8 = 1;

#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PixelFormat {
    Rgba8 = 1,
    Rgb565 = 2,
}

pub struct RawCachedTexture {
    pub width: u16,
    pub height: u16,
    pub format: PixelFormat,
    pub data: Vec<u8>,
}

impl RawCachedTexture {
    pub fn from_rgba8(width: u16, height: u16, rgba: &[u8]) -> Self {
        Self {
            width,
            height,
            format: PixelFormat::Rgba8,
            data: rgba.to_vec(),
        }
    }

    /// Converts RGBA8 to RGB565 (cuts VRAM and disk footprint in half for
    /// opaque Jellyfin/Plex/Nivío posters and backdrops).
    pub fn from_rgba8_as_rgb565(width: u16, height: u16, rgba: &[u8]) -> Self {
        let w = width as usize;
        let h = height as usize;
        let mut out = Vec::with_capacity(w * h * 2);
        const BAYER_2X2: [[i16; 2]; 2] = [[-2, 1], [2, -1]];
        for y in 0..h {
            let row_dither = BAYER_2X2[y & 1];
            for x in 0..w {
                let idx = (y * w + x) * 4;
                let d = row_dither[x & 1];
                let r = ((rgba[idx] as i16 + d).clamp(0, 255) as u16) >> 3;
                let g = ((rgba[idx + 1] as i16 + (d >> 1)).clamp(0, 255) as u16) >> 2;
                let b = ((rgba[idx + 2] as i16 + d).clamp(0, 255) as u16) >> 3;
                let packed: u16 = (r << 11) | (g << 5) | b;
                out.extend_from_slice(&packed.to_le_bytes());
            }
        }
        Self {
            width,
            height,
            format: PixelFormat::Rgb565,
            data: out,
        }
    }

    pub fn save_to_disk(&self, path: &Path) -> std::io::Result<()> {
        let mut f = File::create(path)?;
        let mut header = [0u8; 12];
        header[0..4].copy_from_slice(&LTEX_MAGIC);
        header[4] = LTEX_VERSION;
        header[5] = self.format as u8;
        header[6..8].copy_from_slice(&self.width.to_le_bytes());
        header[8..10].copy_from_slice(&self.height.to_le_bytes());
        f.write_all(&header)?;
        f.write_all(&self.data)?;
        Ok(())
    }

    pub fn load_from_disk(path: &Path) -> std::io::Result<Self> {
        let mut f = File::open(path)?;
        let mut header = [0u8; 12];
        f.read_exact(&mut header)?;
        if header[0..4] != LTEX_MAGIC || header[4] != LTEX_VERSION {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "Invalid LTEX header",
            ));
        }
        let format = match header[5] {
            1 => PixelFormat::Rgba8,
            2 => PixelFormat::Rgb565,
            _ => {
                return Err(std::io::Error::new(
                    std::io::ErrorKind::InvalidData,
                    "Unknown PixelFormat",
                ))
            }
        };
        let width = u16::from_le_bytes([header[6], header[7]]);
        let height = u16::from_le_bytes([header[8], header[9]]);
        let bpp = match format {
            PixelFormat::Rgba8 => 4usize,
            PixelFormat::Rgb565 => 2usize,
        };
        let expected_len = (width as usize) * (height as usize) * bpp;
        let mut data = vec![0u8; expected_len];
        f.read_exact(&mut data)?;
        Ok(Self {
            width,
            height,
            format,
            data,
        })
    }
}

fn disk_key(source: &Source) -> Option<String> {
    let bytes = serde_json::to_vec(source).ok()?;
    let hash = bytes.iter().fold(0xcbf29ce484222325u64, |h, byte| {
        (h ^ u64::from(*byte)).wrapping_mul(0x100000001b3)
    });
    Some(format!("{hash:016x}.ltex"))
}
fn persistent_load(source: &Source, directory: &Path) -> Option<Artwork> {
    let filename = disk_key(source)?;
    let path = directory.join(filename);
    let cached = RawCachedTexture::load_from_disk(&path).ok()?;
    let pixels = match cached.format {
        PixelFormat::Rgba8 => image::RgbaImage::from_vec(cached.width.into(), cached.height.into(), cached.data).ok()?,
        PixelFormat::Rgb565 => {
            let w = cached.width as usize;
            let h = cached.height as usize;
            let mut rgba = Vec::with_capacity(w * h * 4);
            for i in 0..(w * h) {
                let packed = u16::from_le_bytes([cached.data[i * 2], cached.data[i * 2 + 1]]);
                let r = ((packed >> 11) & 0x1F) as u8 * 255 / 31;
                let g = ((packed >> 5) & 0x3F) as u8 * 255 / 63;
                let b = (packed & 0x1F) as u8 * 255 / 31;
                rgba.extend_from_slice(&[r, g, b, 255]);
            }
            image::RgbaImage::from_vec(cached.width.into(), cached.height.into(), rgba).ok()?
        }
    };
    let color = background(&pixels);
    Some(Artwork {
        key: String::new(),
        pixels,
        color,
    })
}
fn persistent_write(source: &Source, directory: &Path, image: &Artwork) {
    let Some(key) = disk_key(source) else {
        return;
    };
    if std::fs::create_dir_all(directory).is_err() {
        return;
    }
    let (width, height) = (image.pixels.width() as u16, image.pixels.height() as u16);
    let raw = RawCachedTexture::from_rgba8_as_rgb565(width, height, &image.pixels);
    if raw.data.len() > DISK_ARTWORK_MAX {
        return;
    }
    let final_path = directory.join(&key);
    let temporary = directory.join(format!(".{}.{}.tmp", key, std::process::id()));
    if raw.save_to_disk(&temporary).is_ok() {
        let _ = std::fs::rename(&temporary, &final_path);
    }
    let _ = std::fs::remove_file(temporary);
}

#[derive(Clone, Debug, PartialEq, Eq, Hash, Serialize)]
pub struct Source {
    pub id: String,
    directory: Option<PathBuf>,
    large_icon: Option<String>,
    icon: Option<String>,
    // Part of the cache key: an app update changes it, so its icon is read
    // again, while unchanged apps keep their decoded artwork across refreshes.
    version: Option<String>,
}

impl Source {
    pub fn new(id: &str, metadata: &Value) -> Self {
        let text = |key| {
            metadata
                .get(key)
                .and_then(Value::as_str)
                .filter(|s| !s.is_empty() && s.len() <= 4096 && !s.chars().any(char::is_control))
        };
        Self {
            id: id.into(),
            directory: text("folderPath").map(PathBuf::from).filter(|p| {
                p.components().all(|c| !matches!(c, Component::ParentDir))
                    && ROOTS.iter().any(|root| p.parent() == Some(Path::new(root)))
            }),
            large_icon: text("largeIcon").map(str::to_owned),
            icon: text("icon").map(str::to_owned),
            version: text("version").map(str::to_owned),
        }
    }

    fn directories(&self) -> Vec<PathBuf> {
        let mut directories: Vec<_> = self.directory.iter().cloned().collect();
        for root in ROOTS {
            let directory = Path::new(root).join(&self.id);
            if !directories.contains(&directory) {
                directories.push(directory);
            }
        }
        directories
    }
}

/// Artwork is decoded once and shared: identity is the same image.
impl PartialEq for Artwork {
    fn eq(&self, other: &Self) -> bool {
        std::ptr::eq(self, other)
    }
}

pub struct Artwork {
    pub key: String,
    pub pixels: RgbaImage,
    pub color: [u8; 3],
}

fn read_bounded(path: &Path, limit: usize) -> Option<Vec<u8>> {
    let file = File::open(path).ok()?;
    let metadata = file.metadata().ok()?;
    if !metadata.is_file() || metadata.len() > limit as u64 {
        return None;
    }
    let mut bytes = Vec::new();
    file.take(limit as u64 + 1).read_to_end(&mut bytes).ok()?;
    (bytes.len() <= limit).then_some(bytes)
}

fn icon_path(directory: &Path, value: &str) -> Option<PathBuf> {
    if value.is_empty() || value.len() > 4096 || value.chars().any(char::is_control) {
        return None;
    }
    let value = value.strip_prefix("file://").unwrap_or(value);
    if value.contains("://") {
        return None;
    }
    let path = Path::new(value);
    if path
        .components()
        .any(|part| matches!(part, Component::ParentDir))
    {
        return None;
    }
    let path = if path.is_absolute() {
        path.to_owned()
    } else {
        directory.join(path)
    };
    ROOTS
        .iter()
        .any(|root| path.starts_with(root))
        .then_some(path)
}

fn decode(bytes: &[u8]) -> Option<Artwork> {
    let mut reader = ImageReader::new(Cursor::new(bytes))
        .with_guessed_format()
        .ok()?;
    let mut limits = Limits::default();
    limits.max_image_width = Some(2048);
    limits.max_image_height = Some(2048);
    limits.max_alloc = Some(32 * 1024 * 1024);
    reader.limits(limits);
    let image = reader.decode().ok()?;
    let pixels = image.thumbnail(256, 256).into_rgba8();
    let color = background(&pixels);
    Some(Artwork {
        key: String::new(),
        pixels,
        color,
    })
}

fn background(image: &RgbaImage) -> [u8; 3] {
    // Match the icon's opaque edges rather than letting its central logo choose
    // the card colour. Transparent artwork gets a neutral dark background, even
    // when its logo reaches into the edge band: those few opaque pixels would
    // otherwise fill the card with the logo's own colour and hide it.
    let sample = image::imageops::resize(image, 48, 48, image::imageops::FilterType::Triangle);
    let mut bins = HashMap::<[u8; 3], (usize, [usize; 3])>::new();
    let (mut edge, mut opaque) = (0, 0);
    for (x, y, pixel) in sample.enumerate_pixels() {
        if (6..42).contains(&x) && (6..42).contains(&y) {
            continue;
        }
        edge += 1;
        if pixel[3] < 230 {
            continue;
        }
        opaque += 1;
        let bin = bins
            .entry([pixel[0] >> 4, pixel[1] >> 4, pixel[2] >> 4])
            .or_default();
        bin.0 += 1;
        for channel in 0..3 {
            bin.1[channel] += pixel[channel] as usize;
        }
    }
    if opaque * 2 < edge {
        return [20; 3];
    }
    bins.into_iter()
        .max_by_key(|(key, (count, _))| (*count, *key))
        .map_or([20; 3], |(_, (count, sum))| {
            sum.map(|s| ((s + count / 2) / count) as u8)
        })
}

fn load(source: &Source) -> Option<Artwork> {
    if !valid_app_id(&source.id) {
        return None;
    }
    if let Some(image) = load_local(source, read_bounded) {
        return Some(image);
    }
    // Some jailed installations cannot read other applications' files. Use the
    // same native-authenticated elevated service as inventory, on this worker.
    match crate::platform::read_app_icons(source) {
        Ok(icons) => icons.iter().find_map(|bytes| decode(bytes)),
        Err(error) => {
            eprintln!("Luma installed icon {}: {error}", source.id);
            None
        }
    }
}

fn load_local(
    source: &Source,
    mut read: impl FnMut(&Path, usize) -> Option<Vec<u8>>,
) -> Option<Artwork> {
    for directory in source.directories() {
        let manifest = read(&directory.join("appinfo.json"), 64 * 1024)
            .and_then(|bytes| serde_json::from_slice::<Value>(&bytes).ok())
            .filter(|value| value.get("id").and_then(Value::as_str) == Some(&source.id));
        let manifest_icon = |key| {
            manifest
                .as_ref()
                .and_then(|m| m.get(key))
                .and_then(Value::as_str)
        };
        for icon in [
            source.large_icon.as_deref(),
            manifest_icon("largeIcon"),
            source.icon.as_deref(),
            manifest_icon("icon"),
            Some("icon.png"),
        ]
        .into_iter()
        .flatten()
        {
            if let Some(artwork) = icon_path(&directory, icon)
                .and_then(|path| read(&path, MAX_FILE))
                .and_then(|bytes| decode(&bytes))
            {
                return Some(artwork);
            }
        }
    }
    None
}

struct Request {
    token: u64,
    source: Source,
}
struct Reply {
    request: Request,
    image: Option<Arc<Artwork>>,
}
struct Entry {
    token: u64,
    used: u64,
    // None: pending; Some(None): unavailable until the next inventory refresh.
    image: Option<Option<Arc<Artwork>>>,
}
#[derive(Default)]
struct Cache {
    clock: u64,
    entries: HashMap<Source, Entry>,
}

pub struct Service {
    sender: Option<mpsc::SyncSender<Request>>,
    receiver: mpsc::Receiver<Reply>,
    cache: RefCell<Cache>,
}

impl Service {
    pub fn new(enabled: bool) -> Self {
        let disk = enabled
            .then(|| crate::storage::default_path(true).ok())
            .flatten()
            .map(|path| path.with_extension("artwork"));
        Self::with_loader(enabled, move |source| {
            if let Some(ref folder) = disk
                && let Some(image) = persistent_load(source, folder)
            {
                return Some(image);
            }
            let image = load(source)?;
            if let Some(ref folder) = disk {
                persistent_write(source, folder, &image);
            }
            Some(image)
        })
    }

    fn with_loader(
        enabled: bool,
        loader: impl Fn(&Source) -> Option<Artwork> + Send + 'static,
    ) -> Self {
        let (sender, requests) = mpsc::sync_channel::<Request>(16);
        // Room for a full request queue: an idle UI only polls on its next
        // wake, and a one-slot reply channel held the worker to one icon each.
        let (responses, receiver) = mpsc::sync_channel(16);
        if enabled {
            thread::spawn(move || {
                while let Ok(request) = requests.recv() {
                    let image = loader(&request.source).map(|mut image| {
                        image.key = format!("installed-icon:{}", request.token);
                        Arc::new(image)
                    });
                    if responses.send(Reply { request, image }).is_err() {
                        break;
                    }
                }
            });
        }
        Self {
            sender: enabled.then_some(sender),
            receiver,
            cache: RefCell::default(),
        }
    }

    pub fn get(&self, source: &Source) -> Option<Arc<Artwork>> {
        let sender = self.sender.as_ref()?;
        let mut cache = self.cache.borrow_mut();
        cache.clock += 1;
        let clock = cache.clock;
        if let Some(entry) = cache.entries.get_mut(source) {
            entry.used = clock;
            return entry.image.clone().flatten();
        }
        let request = Request {
            token: clock,
            source: source.clone(),
        };
        // A full queue is retried when the next completed request redraws the
        // scene. Neither scrolling nor a slow Homebrew service can block input.
        if sender.try_send(request).is_ok() {
            cache.entries.insert(
                source.clone(),
                Entry {
                    token: clock,
                    used: clock,
                    image: None,
                },
            );
        }
        None
    }

    /// Whether a requested icon has not come back yet, so the event loop
    /// should wake soon to poll for it.
    pub fn pending(&self) -> bool {
        self.cache
            .borrow()
            .entries
            .values()
            .any(|entry| entry.image.is_none())
    }

    /// Refresh apps: every icon is read again. Replies to earlier requests
    /// no longer match an entry's token and are dropped.
    pub fn reset(&self) {
        self.cache.borrow_mut().entries.clear();
    }

    /// After an automatic inventory refresh: icons that were unavailable are
    /// tried again. Decoded and pending icons stay, because a `Source` names
    /// the app's version and icon paths, so an updated app has a new one.
    pub fn refresh(&self) {
        self.cache
            .borrow_mut()
            .entries
            .retain(|_, entry| !matches!(entry.image, Some(None)));
    }

    pub fn poll(&self) -> bool {
        let mut changed = false;
        let mut cache = self.cache.borrow_mut();
        while let Ok(reply) = self.receiver.try_recv() {
            changed = true;
            if let Some(entry) = cache.entries.get_mut(&reply.request.source)
                && entry.token == reply.request.token
            {
                entry.image = Some(reply.image);
            }
        }
        if !changed {
            return false;
        }
        let mut bytes: usize = cache
            .entries
            .values()
            .filter_map(|e| e.image.as_ref()?.as_ref())
            .map(|i| i.pixels.as_raw().len())
            .sum();
        let mut old: Vec<_> = cache
            .entries
            .iter()
            .filter(|(_, e)| e.image.is_some())
            .map(|(s, e)| (s.clone(), e.used))
            .collect();
        old.sort_by_key(|(_, used)| *used);
        for (source, _) in old {
            if bytes <= CACHE_BYTES && cache.entries.len() <= CACHE_ENTRIES {
                break;
            }
            if let Some(entry) = cache.entries.remove(&source)
                && let Some(Some(image)) = entry.image
            {
                bytes -= image.pixels.as_raw().len();
            }
        }
        changed
    }
}

#[cfg(test)]
#[path = "app-artwork-tests.rs"]
mod tests;
