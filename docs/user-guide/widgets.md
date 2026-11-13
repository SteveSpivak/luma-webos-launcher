# Widgets

## Overview

Widgets appear on the Home screen right of the headline. Types: weather, crypto prices, HDMI input preview, Home Assistant status line. Sizes: small, medium, large, text-line.

## Widget types

| Type | Description | Source owner |
|---|---|---|
| Weather | Open-Meteo forecast, hourly + 10-day | `src/weather-service.rs` |
| Crypto | Binance, Coinbase, Kraken prices + charts | `src/widgets.rs` |
| HDMI input | HDMI input preview | `src/widgets.rs` |
| HA status | Home Assistant status line | `src/smart_home.rs` |

## Widget lifecycle

```
[Widget enabled + Home visible]
        |
        v
widgets::tick()                               [src/main.rs]
        |
        v
[Fetch data if needed (bounded background work)]
        |
        v
[Render widget on Home]
        |
        v
[Cache: fresh for bounded period]
```

**Source owner:** `src/widgets_state.rs`

## Settings

| Setting | Description |
|---|---|
| Show widget | Toggle widget visibility |
| Location | Weather city |
| Temperature | Celsius / Fahrenheit |

**Source owner:** `src/widgets_settings_view.rs`

## Visual reference

| Screenshot | Shows |
|---|---|
| `docs/screenshots/weather.jpg` | Weather widget |
| `docs/screenshots/crypto.jpg` | Crypto widget |
