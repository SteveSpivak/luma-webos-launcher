# Navigation and Controls

## Input mapping

| Input                     | Action                                                  |
| ------------------------- | ------------------------------------------------------- |
| Arrows                    | Move focus, revealing remote-focused content            |
| OK / Enter                | Activate on release                                     |
| Hold OK 600 ms            | Reorder Home favorite or open app options               |
| OK or Back in move mode   | Finish reordering without launching                     |
| Escape / Back / Backspace | Parent navigation, overlay dismissal, or quit from Home |
| Menu / M / right-click    | App options                                             |
| Pointer / wheel           | Hover, click, hold, scrolling                           |
| F5                        | Refresh inventory (desktop)                             |

Backspace deletes while editing.

## Native Back (webOS)

Native Back uses SDL's webOS-specific keycode:

- `SDL_SCANCODE_WEBOS_BACK` → Keycode `(1 << 30) | 482` (scancode outside rust-sdl2 standard)
- TV network-input `sendSpecialKey("BACK")` → keycode `2_097_155`, scancode=None

Verified on LG C1 on 2026-10-24.

## Focus navigation

```
state.direction(direction, controls)          [src/state.rs]
```

Focus navigation rules:

- **Apps grid:** Up/Down follows six-column grid order, including offscreen rows. Only first row's Up reaches category toolbar.
- **Home favorites:** Left/Right follows saved order (including reorder mode). Up returns to Home navigation. Down enters nearest input in first row.
- **Stack cards:** Left/Right within row, Up/Down between rows.
- **Settings:** Left at left edge returns to preceding level.
- **Wheel:** Horizontal over favorites, vertical elsewhere.
- **Pointer:** Hover/down never moves clicked control.

## Focus animation

- Focus level: `state.focus_level(target)` → tweened 0→1
- Focus pop: `state.focus_pop(target)` → spring + light sheen
- Zoom: `1. + 0.06 * pop` (stack cards), `1. + 0.07 * pop` (app tiles)
- Entrance cascade: `motion::cascade_progress()` per card on tab entry
- Reduced motion: instant focus, no animation

## Back precedence

```
state.back()                                  [src/state.rs]
```

Order of precedence:

1. Ambient mode → leave ambient
2. Moving selection → cancel move
3. Game shot → clear shot
4. Game active → close game
5. Album active → close album
6. Playback active → close playback (saves `playback_progress[id]`)
7. Movie active → close movie (saves `playback_progress[id]`)
8. Overlay → dismiss overlay
9. Settings subpage → close subpage
10. Settings section → pop section
11. Page → previous page
12. Home → quit application (`Effect::Quit`)

## Back from specific screens

| From               | Back goes to                       |
| ------------------ | ---------------------------------- |
| Keyboard           | Dismiss keyboard, restore focus    |
| Weather Location   | Parent Location row                |
| HDMI choices       | HDMI row                           |
| Background gallery | Background sidebar                 |
| Settings sidebar   | Settings tab                       |
| Settings tab       | Home                               |
| Movie              | Previous position (progress saved) |
| Playback           | Previous position (progress saved) |
| Game               | Close game                         |
| Album              | Close album                        |
