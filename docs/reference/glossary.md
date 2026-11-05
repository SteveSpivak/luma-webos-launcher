# Glossary

| Term             | Definition                                                                    |
| ---------------- | ----------------------------------------------------------------------------- |
| App ID           | Reverse-DNS identifier for a webOS application (e.g. `com.denisefremov.luma`) |
| LS2              | Luna Service 2 — webOS inter-process communication bus                        |
| SAM              | Service Application Manager — webOS launch/pass metadata system               |
| Homebrew Channel | webOS homebrew application that provides elevated `exec` service              |
| Stack            | A row of content on Home from a linked source (Jellyfin, Plex, Moonlight)     |
| StackItem        | A single card in a stack: title, poster path, media ID                        |
| StackConfig      | User configuration for a stack: source, collection, shape, visibility         |
| CardShape        | Visual shape of a card: Poster (2:3), Square (1:1), Wide (16:9)               |
| Detail           | Full media information: title, poster, backdrop, cast, episodes, qualities    |
| PlayRequest      | Request to play media: ID, episode, quality, subtitles                        |
| OpenRequest      | Player open request: URL, title, source, poster, tracks                       |
| Effect           | An action produced by state navigation (launch, refresh, save, quit, etc.)    |
| Target           | A focusable UI element (app, stack card, setting, input, etc.)                |
| Platform worker  | Background thread for blocking TV service calls (never on SDL thread)         |
| Nivío            | Third-party TV app (`space.nuvio.webos`) launched via contentTarget deep link |
| contentTarget    | Nivío deep-link parameter specifying the title to open (`nuvio://tmdb/...`)   |
| Quick Connect    | Jellyfin phone-based sign-in (code displayed on TV, approved on phone)        |
| Plex PIN         | plex.tv four-letter link code for sign-in                                     |
| Moonlight        | Game streaming protocol (Steam games from PC via Sunshine/Apollo)             |
| Home Assistant   | Open-source home automation platform integrated via WebSocket                 |
| Reduced motion   | Accessibility setting that disables animations                                |
| VSync            | Vertical sync — frame pacing tied to display refresh rate                     |
| MSAA             | Multi-sample anti-aliasing (4× requested, 2×/1× fallbacks)                    |
| AFBC             | Adaptive Frame Buffer Compression (LG display format)                         |
| IPK              | webOS application package format                                              |
| Homebrew feed    | JSON repository of installable homebrew apps                                  |

## Source file prefixes

| Prefix               | Meaning                                             |
| -------------------- | --------------------------------------------------- |
| `src/main.rs`        | Application entry point and run loop                |
| `src/state.rs`       | UI state, navigation, focus, effects (single owner) |
| `src/view.rs`        | Rendering scene construction                        |
| `src/platform.rs`    | TV platform worker, Luna calls                      |
| `src/stacks.rs`      | Home stack source registry                          |
| `src/stacks_view.rs` | Stack card rendering                                |
| `src/jellyfin.rs`    | Jellyfin integration                                |
| `src/plex.rs`        | Plex integration                                    |
| `src/moonlight.rs`   | Moonlight game integration                          |
| `src/smart_home.rs`  | Home Assistant integration                          |
| `src/widgets.rs`     | Home widgets                                        |
| `src/media.rs`       | Shared media types                                  |
| `src/app_artwork.rs` | Installed app artwork                               |
| `src/renderer.rs`    | OpenGL ES 2 renderer                                |
| `src/motion.rs`      | Focus animation                                     |
| `src/model.rs`       | Data models                                         |
| `src/storage.rs`     | Preferences persistence                             |
| `src/i18n.rs`        | Translations                                        |
| `src/tests.rs`       | Unit tests                                          |
