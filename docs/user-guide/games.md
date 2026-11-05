# Games (Moonlight)

## Overview

Moonlight streams your Steam library from a PC running Sunshine or Apollo. Games are shown as a stack with Steam artwork. Game pages work like movie pages. **Play** opens the stream in Moonlight (webOS app `com.limelight.webos`).

## Architecture

| Component         | Source files                                | Responsibility                                       |
| ----------------- | ------------------------------------------- | ---------------------------------------------------- |
| Discovery         | `src/moonlight.rs`                          | UDP broadcast, TCP pairing, RSA authentication       |
| Game cache        | `src/moonlight.rs::GameLibrary`             | played (newest first, max 50), first_seen, favorites |
| Stack integration | `src/stacks.rs`                             | `"moonlight"` source, game collections               |
| Play launch       | `src/platform.rs::Request::MoonlightLaunch` | Launch `com.limelight.webos`                         |
| Game card         | `src/game.rs`, `src/game_view.rs`           | Game UI                                              |

## Game collections

| Collection  | Label                |
| ----------- | -------------------- |
| `recent`    | Recently played      |
| `added`     | Recently added games |
| `all`       | All games            |
| `favorites` | Favorite games       |

## Play flow

```
[Game stack card → OK]
        |
        v
GameCard created, focus → Target::GamePlay
        |
        v
Effect::GameInfo(id, title) → Effect::MoonlightPlay(id)
        |
        v
Request::MoonlightLaunch(link, id)
        |
        v
Request::Launch("com.limelight.webos")
        |
        v
[Moonlight app launches game stream]
```

## Back flow

```
[Remote: Back during game]
        |
        v
Effect::MoonlightQuit
        |
        v
[Close game on PC (Apollo /cancel)]
```

## GameLibrary

| Field        | Type                 | Description                                  |
| ------------ | -------------------- | -------------------------------------------- |
| `played`     | `Vec<(i64, u64)>`    | Newest first: (app id, unix seconds), max 50 |
| `first_seen` | `BTreeMap<i64, u64>` | When Luma first saw each game                |
| `favorites`  | `Vec<i64>`           | Favorite game IDs                            |

**Source owner:** `src/moonlight.rs`

## Visual reference

| Screenshot                    | Shows           |
| ----------------------------- | --------------- |
| `docs/screenshots/game.jpg`   | 007 First Light |
| `docs/screenshots/game-2.jpg` | Cyberpunk 2077  |
