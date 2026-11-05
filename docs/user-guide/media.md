# Movies, Series and Music (Jellyfin / Plex)

## Sign-in flow

### Jellyfin (Quick Connect)

```
[Settings › Stacks › Add Jellyfin]
        |
        v
jellyfin_service().send(Command::Discover)    [src/main.rs]
        |
        v
[Worker: scan LAN /24 port 8096, check saved address]
        |
        v
Response::Servers(Vec<Server>)
        |
        v
[User selects server → Command::Connect]
        |
        v
[Worker: Quick Connect/Initiate → secret + code]
        |
        v
Response::Code { code, address }
        |
        v
[User approves on phone: jellyfin.link/connect]
        |
        v
[Worker: poll every 3s for 10 min → token]
        |
        v
Response::Linked(JellyfinLink)
        |
        v
Preferences saved, stacks created, stacks_refresh()
```

### Plex (plex.tv PIN)

```
[Settings › Stacks › Add Plex]
        |
        v
plex_service().send(Command::Link { client_id }) [src/main.rs]
        |
        v
[Worker: plex.tv PIN request → code + QR]
        |
        v
Response::Code { code, qr }
        |
        v
[User approves at plex.tv/link]
        |
        v
Response::Linked(PlexLink)
        |
        v
Preferences saved, stacks created, stacks_refresh()
```

## Browse flow

```
[Stack card → OK]
        |
        v
open_movie(item, pool, Target::StackCard)     [src/state.rs]
        |
        v
MovieCard created, focus → Target::MoviePlay
        |
        v
Effect::MediaDetails(id)
        |
        v
[Worker: fetch detail → Response::Details]
        |
        v
state.media_detail() → state.movie_details()  [src/state.rs]
        |
        v
[Title card: backdrop, cast, seasons, episodes, qualities, subtitles]
```

## Detail page elements

| Element                                 | Source                                                |
| --------------------------------------- | ----------------------------------------------------- |
| Backdrop                                | `src/media.rs::poster_backdrop()` (16:9 blurred crop) |
| Poster                                  | Cached poster file path                               |
| Title, year, minutes, genres, countries | `media::Detail`                                       |
| Plot, director, cast                    | `media::Detail`                                       |
| Tags (4K, 5.1, etc.)                    | `media::Detail.tags`                                  |
| IMDB / Kinopoisk ratings                | `media::Detail.imdb`, `media::Detail.kinopoisk`       |
| Audio tracks                            | `media::Detail.audio`                                 |
| Subtitles                               | `media::Detail.subtitles`                             |
| Qualities                               | `media::Detail.qualities`                             |
| Trailer                                 | `media::Detail.trailer`                               |
| Seasons / episodes                      | `media::Detail.seasons`, `media::Detail.episodes`     |
| Next unwatched                          | `media::Detail.next`                                  |

## Playback flow

```
[OK on Target::MoviePlay]
        |
        v
Effect::MediaPlay(request)
        |
        v
jellyfin_service().send(Command::Play)        [src/jellyfin.rs]
        |
        v
[Worker: resolve play URL → OpenRequest]
        |
        v
open_player(state, platform, request)         [src/main.rs]
        |
        +-- webOS: Request::WebPlayer(signed URLs + token)
        |       |
        |       v
        |   [Luma Player web app: HTML5 video, HLS]
        |
        +-- desktop: local playback session
```

**Playback progress:** Saved to `preferences.playback_progress[id]` on close.

## Music flow

```
[Album card → OK]
        |
        v
open_album(item, Target::StackCard)
        |
        v
[Album page: songs, cover, now-playing]
        |
        v
[Play → background playback, album card stays open]
```

**Source owners:** `src/jellyfin.rs`, `src/plex.rs`, `src/media.rs`, `src/movie.rs`, `src/movie_view.rs`, `src/player.rs`, `src/player_backend.rs`, `src/album.rs`, `src/album_view.rs`, `src/music.rs`

## Plex note

Plex support is newer and less tested than Jellyfin.

## Visual reference

| Screenshot                    | Shows                     |
| ----------------------------- | ------------------------- |
| `docs/screenshots/movie.jpg`  | Movie page                |
| `docs/screenshots/series.jpg` | Series page with episodes |
| `docs/screenshots/music.jpg`  | Now playing               |
| `docs/screenshots/album.jpg`  | Album                     |
