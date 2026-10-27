# Browser session consumer independent preaccess oracles

Prepared 2026-10-27 before access to the active candidate. This is a contract-derived
review plan and input-custody record, not implementation acceptance. The root's
`console-session-and-checkout-root-review/acceptance.json` selects the closed
`console-session-integration-selection/frontend-contract.json`; the contract's
historical proposed status is superseded only by that root selection. The observed
canonical revision is `b231f3d405c06bfb348f193d46a348af0529bd84`.

HEAD advanced concurrently during preparation to
`114a2632fd58076574bd5b2444c511861c3b30d4`; the first collector intentionally failed
its baseline assertion. The manifest therefore pins subsequent canonical custody
to the initially read revision and records observed HEAD separately. The failure
is retained in `preaccess-attempt-1-failure.json`; no candidate or test access
preceded or followed it.

The producer's new browser-session modules, current `main.tsx`, new tests, and
`verification/console-browser-session-consumer/` have not been read. Existing
cookie/workspace/Solid inputs were read exclusively through `git show HEAD:path`.
No compiler, test runtime, browser, UI, capture, native runtime, stopped callback
harness, Git mutation, hosted edit, dependency installation, or global inventory
was used. Root must release the candidate and allocate targeted execution before
this lane can inspect it or execute review probes.

## Observation model and test apparatus

The independent host harness will import the released compiled candidate and actual
canonical cookie/workspace/Solid modules rather than mock their implementation.
Synthetic session metadata and workspace pages will be labelled fixtures. Harness
capabilities will be restricted to test fetch, deferred promises, bounded fake
response/readers, controlled wall and monotonic globals, controlled timers, owned
event targets, and a fake BroadcastChannel. Neither production constructors nor
their options may gain injected sessions, clocks, providers, or dispatchers.

Each probe will assert public result/state identity, request count and exact request
shape, observed signal state, reader cancellation/release, pending timer/listener/
channel count, and unhandled rejection count where applicable. Tests will settle
late promises after public completion, including rejection, then check that state
and ownership stay correct. Every fake deferred or timer belongs to one probe and
is settled or retired in finally. A non-settling cancel promise must never be an
awaited prerequisite for public completion or cleanup.

Where a contract statement is structural (for example no persistence or reactive
entry props), source review will complement executable behavior. Structural checks
alone are not runtime/security acceptance. A fake browser event target does not
qualify actual cookie, bfcache, visibility, or cross-tab browser behavior.

## Client boundary roster

| ID | Adversarial input or schedule | Required oracle |
| --- | --- | --- |
| CL01 | Default construction; valid authenticated and unauthenticated responses, either field order and JSON space/tab/CR/LF | Frozen client; exact frozen scalar copy; no additional fields; exact relative GET `/auth/session`, JSON accept only, same-origin credentials, error redirects, no-store cache, no-referrer, no body/query. |
| CL02 | Options null/array/nonobject, unknown string or symbol own keys, nonfunction fetch, timeout 0/30001/fraction/NaN/Infinity; timeout bounds 1/30000 | Invalid options fail fixed invalid_request; permitted boundary values accepted; no rejected construction fetch. Confirm symbol/nonenumerable own keys are not silently admitted under exact own-key policy. |
| CL03 | 204/3xx/401/403/404/429/5xx, arbitrary error body; `200 text/html` SPA fallback | All non-200 become unavailable, never unauthenticated; HTML200 invalid_response; cancel body best effort without reading/displaying it; controller remains unavailable and dispatches zero workspace calls. |
| CL04 | redirected true; content-type absent, multiple types, other media type/charset/parameters; valid ASCII case and permitted whitespace | Reject disallowed header form before body reading; accept only application/json with optional charset=utf-8 under selected whitespace/case policy. |
| CL05 | Cache-Control absent/no-cache/quoted substring `x="no-store"`/`x-no-store`/token suffix or malformed field; separate no-store with other valid directives and ASCII case | Only syntactically separate valid no-store admits; unrelated headers including Date, Set-Cookie-looking/custom session headers grant nothing. |
| CL06 | Content-Length absent, 0, 8192; leading zero aliases, +1/-1, whitespace, comma, fraction, exponent, unsafe integer, 8193 | Only absent or canonical safe decimal <=8192 passes header admission. Actual bytes are independently enforced; declared length never authorizes larger success body. |
| CL07 | Complete valid metadata padded to exactly 4096 bytes, 4097 bytes; oversized first chunk and cumulative overflow | 4096 can pass; 4097 stops immediately, cancels/releases, invalid_response. No buffering to 8192 or workspace 262144 limit. |
| CL08 | 4095 data/empty chunks plus done on call 4096; 4096 data/empty chunks requiring done on 4097 | First can pass within byte limit; second rejects without call 4097. All reads including empty chunks and final done consume the bound. |
| CL09 | Missing body; malformed UTF-8, split multibyte sequence, BOM, overlong/invalid sequence, non-ASCII field/value, trailing junk | Missing/malformed body invalid_response; strict fatal decode; reject BOM even if TextDecoder would strip it; standard trailing JSON whitespace alone may pass. |
| CL10 | Duplicate literal keys, escaped-equivalent keys, any escaped name/value, extra/missing key, nested/array/null, duplicate document, trailing comma | Reject through the closed flat lexical contract, including JSON.parse last-key-wins attacks. Field order remains arbitrary. |
| CL11 | Canonical43 lengths 42/44, padding/+ or /, illegal ASCII, whitespace, unused trailing bits mutated; independently distinct generation and CSRF | Decode exactly 32 bytes and re-encode exact string. For 32 bytes the final base64url sextet index must be divisible by 4; a 43-character string with nonzero unused bits rejects. No equality/ordering requirement between the two fields is invented. |
| CL12 | expires_at -0/+1/negative/leading zeros/fraction/exponent/string/NaN-like token/unsafe integer; zero and maximum safe integer | Closed JSON decimal integer token only; no sign/decimal/exponent, safe nonnegative value. Safe seconds that overflow milliseconds can decode but must fail controller admission. |
| CL13 | Already-aborted signal; caller abort during noncooperative fetch/read; deadline during fetch then read; stalled cancel; late resolve and late reject | Caller abort reports aborted; deadline unavailable. One absolute deadline spans all stages; public completion is bounded without cooperative fetch/read/cancel. Late response is withheld/cancelled; no unhandled rejection; listeners/timer/reader released best effort. |
| CL14 | Fetch/header/body reader throws arbitrary private error or throwing property; dependency rejection after race; cancellation/release throws | Fixed code/message only, no private URL/body/token/provider text or dependency stack; cleanup cannot leak a raw caught dependency error or replace selected public result. |
| CL15 | Decode consumes remaining budget or abort occurs before publication; deadline boundary equality | No successful publication after absolute deadline or caller abort, even if all bytes arrived earlier. A stage reset of the timeout cannot extend lifetime. |

## Controller and actual cookie-client roster

| ID | Adversarial input or schedule | Required oracle |
| --- | --- | --- |
| CO01 | Construct controller without binding; subscribe; explicit revalidate | Frozen initial unavailable; constructor has no network/listeners; subscribe sees coherent state; first explicit revalidate makes one fixed session read. No cookie workspace client before admitted authenticated metadata. |
| CO02 | Ready A -> revalidate B with A session/workspace work still pending | New local epoch and unavailable installed synchronously before abort handlers/subscribers reenter; no retained private view before effects; old requests abort. |
| CO03 | A/B/C complete in all selected orders with equal server generation, then different generation; old failures after newest success | Only latest live operation admits. Each success is a different immutable session and client capability even for equal generation; old text equality cannot bypass local epoch. |
| CO04 | Ready A wrapper retained across same-generation success, different-generation success, unauthenticated success, invalidate, expiry, dispose | Retained organizations/projects methods reject existing WorkspaceClientError aborted before dispatch; no new fetch; old response/failure never publishes. |
| CO05 | wallStart/monoStart controlled; server expiration earlier/equal/later; lifetime >900000 ms; fractional monotonic start | Capture immediately before session read; exclusive wall deadline and captured min(900000, remaining wall) monotonic deadline; read latency consumes lifetime; current admission samples must be strictly before both deadlines. |
| CO06 | Date.now negative/fraction/NaN/Infinity/unsafe; performance.now negative/NaN/Infinity/unsafe; expires_at*1000 or mono sum unsafe | Fail unavailable and no workspace dispatch. Fractional finite monotonic samples are valid; wall samples must be nonnegative safe integer milliseconds. |
| CO07 | Advance wall only, mono only, exact equality; delayed timer; backwards wall or monotonic sample during epoch | getSession, delegate invocation, and result/failure publication synchronously fence both clocks. Rollback cannot extend capability; equality expires; timer throttling grants no grace. |
| CO08 | Timer fires/does not fire; expiry then foreground/explicit retry | One owned timer expires ready by captured remaining monotonic deadline; expiration starts no automatic network loop. Later independent explicit/foreground check may create a new capability. |
| CO09 | Admitted authenticated fixture -> actual wrapper organizations/projects calls with legal page/cursor/Unicode identifier fixtures | Actual createCookieWorkspaceClient/transport/domain parser join is used; exact `/console-api/v1/orgs` and scoped encoded projects query; matching fetch/timeout; same-origin credentials; no Authorization/Cookie/CSRF/generation header or configurable destination. |
| CO10 | Multiple concurrent actual workspace requests; caller abort one, then outer invalidate/supersede | Caller cancellation scoped to its operation; outer invalidation aborts every owned operation immediately. Listeners released in finally; already-aborted caller dispatches zero fetch. |
| CO11 | Actual current workspace401 vs403/404/503/invalid response; forged plain object/error name/code unauthenticated; stale401 | Actual current WorkspaceClientError unauthenticated invalidates outer ready synchronously, propagates category, starts no recheck. Other categories preserve existing scoped workspace handling. Forged or stale errors cannot clear a newer capability. |
| CO12 | Workspace success/failure settles at clock expiry or after local epoch change, including noncooperative fetch | Public wrapper rejects aborted and withholds payload/error; a second live check after await is mandatory. No late page/selection/cursor survives replacement. |
| CO13 | Subscriber throws, returns rejected promise, unsubscribes/subscribes, calls revalidate/invalidate/dispose during notification | No uncaught/unhandled observer error; coherent current state first; later observers cannot receive obsolete ready after a nested mutation; no resurrected operation or cleared newer request slot. |
| CO14 | Session/workspace abort handler reenters getSession/revalidate/invalidate/dispose; several requests abort in one outer action | Handler observes unavailable/updated epoch; reentrant newer operation remains owned and cannot be overwritten by the interrupted outer action. Dispose stays terminal and idempotent. |
| CO15 | Dispose during pending session/read/workspace/timer/notification; late resolves/rejects; repeated dispose/public actions | All owned work cancels; listeners/timers/subscribers dropped; no post-dispose publish, new request, or retained ready. Fixed error behavior remains safe. |

## Solid binding, entry, and workspace handoff roster

| ID | Adversarial input or schedule | Required oracle |
| --- | --- | --- |
| SO01 | Real Solid owner, visible mount; hidden mount followed by foreground | Subscribe before exactly one visible startup read. Hidden startup issues no read and stays unavailable until foreground. No external writable session or ready factory. |
| SO02 | Same-turn visible visibilitychange+focus+pageshow; foreground while earlier check pending | Coalesce duplicate notifications into one read per event turn. When a new actual check starts it replaces/aborts old work rather than retaining ready. No polling or automatic failure retry. |
| SO03 | Make document hidden without delivering event; pure accessor then captured workspace action before effects | Accessor synchronously invalidates and returns unavailable. Actual workspace binding pure read/action fence hides pages and blocks dispatch before reactive effects run. |
| SO04 | pagehide while document still says visible; accessor/read result races; persisted bfcache-style pagehide | Pagehide flag blocks ready immediately independent of visibility. Session result while hidden/pagehidden cannot admit visible ready; late work stays fenced. |
| SO05 | pageshow/focus/visibility foreground after pagehide, including duplicate events | Clear pagehide only on selected visible foreground handling; fresh session read; no restoration of old capability/page selection/cursor. |
| SO06 | Broadcast data exact plain `{type:'invalidate'}` vs extra own keys/symbols, arrays/null/class instance/foreign prototype/credential fields, arbitrary string | Only closed plain invalidation signal accepted. Inbound synchronously invalidates then schedules one visible read, never rebroadcasts. Reject credential-bearing or extra-field inputs. |
| SO07 | Local binding invalidate while ready/check pending/hidden | Exactly the fixed invalidation data may be emitted; no CSRF/generation/identity/page. Hidden remains unavailable without read. If channel unavailable, retain startup/foreground behavior without storage fallback. |
| SO08 | Cross-tab invalidate immediately before queued foreground callback; hide/dispose before queued callback; inbound invalidate during session resolution | Coalesce owned scheduling; no hidden/disposed read, stale ready, rebroadcast loop, or duplicate current read. Inbound signal alone never creates authenticated/unauthenticated state. |
| SO09 | Same-generation and different-generation success handed to real createWorkspaceBinding; pure computation reads/actions around session change | Fresh identity resets organizations to loading and clears projects/selection/cursors before effects; old ready wrapper no longer dispatches. Actual canonical workspace controller must own new page reads. |
| SO10 | Solid owner disposal during pending read/queued foreground/inbound callback; callbacks invoked after cleanup | Remove only owned listeners, close channel once, cancel queued work, dispose controller; no post-cleanup request/state publication. Preserve other owners and global objects. |
| SO11 | Source review of production main and compiled reactive entry; entry receives successful metadata transitions | Constructs binding once inside owned root and forwards live accessor as reactive App prop; preserves container/styles/App provider lifetime. No one-time snapshot, fixture session, bearer/token input, sign-in/logout UI, or new login route. |
| SO12 | `/auth/session`404, outage, HTML200 fallback or malformed no-store response through real binding+workspace join | Public workspace state unavailable with zero cookie workspace requests and no unauthenticated inference. This is the expected current canonical deployment behavior, not a claimed connected session. |

## Execution and acceptance boundary

After root release, record the exact candidate revision/tree or owned file digest
set before and after review. Establish that the candidate under test matches the
released packet and that unchanged canonical cookie/workspace files still match
the preaccess manifest. Retain each executed probe's command, runtime/tool version,
output, expected/observed behavior and cleanup accounting. Review producer tests
only after independent expectations above are frozen. Ask root for a bounded host
runtime/compiler allocation rather than competing with the producer lane.

A finding needs a concrete trigger, expected contract behavior, observed behavior,
and verified source location. An unexecuted roster item is pending, not passed.
Host fixtures cannot close actual Endpoint/default-verifier/default-Repo integration,
provider/startup/custody, callback/logout/revocation races, browser cookie/cross-tab/
bfcache, ingress/CDN/cache isolation, customer/FieldLog or GA qualification. No GA
gate is promoted by this packet. No native or browser process requires cleanup
because none was started in preaccess preparation.
