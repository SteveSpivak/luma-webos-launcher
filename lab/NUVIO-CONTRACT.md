# Source-backed Nuvio TV interoperability contract (consumer side)

**Origin:** private `SteveSpivak/nuvio-perf-lab` branch `claude/migrate-136-integration-20261104`, commit `c97c38da61511fc5b644680aabb6e646f9785f1d`. Key paths: `appinfo.json`, `js/core/deeplink/deepLinkParser.js`, `js/core/deeplink/launchDeepLink.js`, `js/core/launchIntent.js`. These are **source observations**, not end-to-end TV tests. The target repo is PUBLIC; **do not copy private repo code or user data**. Fetch through authorized connector when available; if unavailable, use this contract, report verification BLOCKED.

## Existing Nuvio consumer path (OBSERVED SOURCE)
- Real webOS app ID `space.nuvio.webos`; version in pinned app manifest `1.3.6`; `handlesRelaunch: true`.
- LG app-launch params provide a `contentTarget` string of form `nuvio://tmdb/movie/603`.
- Existing parser accepts:
  - `nuvio://tmdb/movie/603` -> `{type:"movie",id:"tmdb:603"}`
  - `nuvio://imdb/series/tt0903747` -> `{type:"series",id:"tt0903747"}`
  - `nuvio://detail/movie/tt0133093` -> movie detail
  - `nuvio://meta?type=movie&tmdb=603` -> movie detail
- `launchDeepLink.js` maintains one pending title until login / setup / profile/PIN and route ready, then `navigate("detail", {itemId,itemType})` exactly once; already on the requested detail avoids duplicate navigation.
- It is NOT a public HTTP endpoint. It does NOT provide Continue Watching enumeration, playback controls, authenticated account export or a remote player API.
- The `lgtv.intent@1` keyboard injection file is **lab-only**, flag guarded and targeted at `space.nuvio.lab`. DO NOT USE as the product integration.

## Proposed Luma producer (NOT IMPLEMENTED)
Use existing Luma `src/platform.rs` worker and Luna `com.webos.applicationManager/launch`, extending the validated allowlisted launch path rather than generic arbitrary-RPC. The Luma-only request shape is:
```json
{"id":"space.nuvio.webos","params":{"contentTarget":"nuvio://tmdb/movie/603"}}
```
Allow only the fixed app ID and bounded known title link forms; reject unknown schemes, arbitrary service URLs, command strings, raw account/media tokens, invalid IDs and overlong params. Encoding must match Nuvio parser, not interpolate unchecked user strings. Treat launch as successful *request acceptance*, not proof Nuvio navigation or playback. Implement no automatic play.

## CW feed (PROPOSED, not existing API)
A potential owner-approved future read-only producer schema:
```json
{
  "schema":"nuvio.launcher.cw.v1",
  "revision":1,
  "generated_at":"2026-11-05T00:00:00Z",
  "profile_alias":"local-profile-a",
  "items":[
    {"type":"movie","source":"tmdb","source_id":"603","title":"Example title","progress_seconds":120,"duration_seconds":3600,"artwork_ref":"opaque:poster-a","updated_at":"2026-11-05T00:00:00Z"}
  ]
}
```
This is a **synthetic design example**, not a claim that Nuvio currently exposes such a feed. The actual producer, storage, authorization and artwork fetch access are UNKNOWN until source audit. Design request cancellation, freshness budget, item count cap, image byte/crop cap, current-profile isolation, complete/safe deletion on logout, provenance and offline read-only fallback. Avoid leaking streaming links, add-on URLs, names of watched titles or account secrets to public GitHub or logging.

## Negative tests and ownership
Reject mismatched profile, stale generation, unknown source/media type, bad UUID/ID, path traversal, malformed JSON, raw URL in artwork field, overlong feed, rogue app ID, replayed request, and account switches with pending requests. Test delay until Nuvio user/profile selection. Never read `/media/developer/space.nuvio.webos` or private storage without separate owner authorization. Nuvio owns watch history, per-profile sync and progress; Luma owns UI only.

## Acceptance
Offline contract parser PASS is not a live Nuvio connection. Actual TV acceptance needs independent app installed identity, bounded owner-approved launch on a fresh title, navigation into correct detail, Back and Home return, and all protected streaming/DRM/settings unaffected. No playback initiated by the launcher.
