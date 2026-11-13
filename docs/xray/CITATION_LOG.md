# Citation Log

> ⚡ **BLUF**: Every citation in this log resolves to a real file and line range
> in the repository. Format: `[description](src/main.rs#L1-L5)`.
> Missing or broken citations fail the M1 gate in `scripts/xray/verify_kb.py`.

All citations below resolve to real files and line ranges in this repository.
Format: `[description](src/main.rs#L1-L5)`.

- [Platform entry point](src/main.rs#L1-L40)
- [Nuvio app ID selection](src/platform.rs#L20-L40)
- [validate_nuvio_target()](src/platform.rs#L42-L60)
- [LCKV read bridge](src/fast_kv.rs#L120-L140)
- [LCKV seqlock check](src/fast_kv.rs#L124-L130)
- [bridge_items() consumer](src/nuvio.rs#L50-L70)
- [State launch guard](src/state.rs#L30-L50)
- [Renderer draw_mesh](src/renderer.rs#L2320-L2360)
- [if let guard failure site](src/renderer.rs#L2030-L2040)
- [StackItem struct fields](src/stacks.rs#L8-L25)
- [StackItem usage in main.rs](src/main.rs#L2085-L2100)

**Hotspot files cited:**
- `src/renderer.rs`
- `src/platform.rs`
- `src/main.rs`
- `src/state.rs`
- `src/stacks.rs`
