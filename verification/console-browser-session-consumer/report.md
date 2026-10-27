# Closed browser session consumer: producer handoff

Status: frozen source and producer evidence, awaiting independent review. Root selected the released frontend contract on 2026-10-27. Producer success does not accept an independent review or any GA gate.

The production entry now constructs one Solid-owned browser session binding and passes its live accessor through the existing App/WorkspaceProvider seam. A closed `/auth/session` reader admits only bounded, strictly parsed authenticated or unauthenticated metadata. Local epochs, wall and monotonic deadlines, visibility/bfcache invalidation, current-result fences and cancellation protect the actual cookie workspace adapter. Cross-tab messages contain only `{type: "invalidate"}` and request a fresh server check.

The canonical backend still lacks the required session and cookie workspace routes. A missing session endpoint or a static server's HTML fallback leaves the console unavailable and makes zero workspace requests. Authenticated test metadata is a synthetic host fixture. This work supplies no login UI, provider trust, active backend session, callback acceptance, deployment or customer-readiness evidence.

## Frozen inputs and ownership

`source-manifest.json` records revision `114a2632fd58076574bd5b2444c511861c3b30d4`, its tracked tree and all 65 selected file hashes: 57 console files, the four existing external regression fixtures, and AGENTS/product-plan/selected-contract documents. `frozen-inputs/` contains those exact bytes. The selected source digest is `7cd673b6b2c729c60586b0506ef57e0d063183046c76ffab5c44f6b3f88314b8`; the eight owned product/test files have digest `c39aec67a5c051687ff86b2d9ec6b3a61a4ca37228d8885a0a159283d839b54a`.

Owned product files are the three new `browser-session-client`, `browser-session-controller` and `browser-session-binding` modules plus `console/src/main.tsx`. The four new tests are exactly the contract-named client, controller, binding and binding-runner files. Existing App, workspace binding/controller/client/transport, domain/pagination files and tests were unchanged. No packages or new external checkout inputs were added. Root retains metadata/workflow/delivery ownership.

## Host validation

Each attempt records the exact command, cwd, tool versions, selected source hashes, complete stdout/stderr, direct PID, PGID, wall cap, exit code and captured-group cleanup. Every group was absent after completion. Each meaningful command had a 55-second cap; the longest attempt took 30.496 seconds while exposing a test-harness mistake that was subsequently corrected. The final full regression took 2.085 seconds.

- Client cases: 14 passed in the initial focused attempt and in the final full regression.
- Final affected controller/binding run: 17 outer tests passed; the binding wrapper additionally ran 10 passing Solid client-runtime child tests.
- Complete console host regression: 149 outer tests passed, zero failures, zero skips and zero cancellations. Separately, the new binding runner's 10 tests and the existing workspace runner's four tests passed inside their parent wrapper tests. These nested counts are not added to the outer count.
- Strict TypeScript `tsc --noEmit`: passed.
- Production `tsc --noEmit && vite build`: passed. The normal ignored `console/dist` output is retained, with hashes in `build-artifacts.json`; it was not served or published.

Tools: Node 22.23.3, npm 10.9.9, TypeScript 5.9.3 and Vite 8.3.5 on macOS arm64. The existing full regression also runs standalone Elixir Scope parity and bounded loopback HTTP fixtures; its Elixir version/output is recorded in that attempt. It does not start the hosted application, PostgreSQL or the stopped callback review harness.

The first focused attempt found missing explicit TypeScript parameter annotations on the workspace wrapper; its client tests passed while controller/binding compilation failed. The second attempt found tests inspecting the existing workspace transport before its asynchronous header step dispatched fetch, and inadequate child TAP diagnostics. Explicit argument types, request-dispatch waits and diagnostic forwarding corrected these issues. All original attempt logs remain under `attempts/`. One initially passing response-fence test had instead waited for a transport timeout; the corrected final test exercises actual response completion promptly.

## Scope and cleanup

Synthetic EventTargets, MessageEvents and the actual Solid client runtime exercise foreground/hidden/pagehide/pageshow, cross-tab data rejection, synchronous pure read/action fences, expiry, rollback, supersession, disposal and the real cookie/workspace binding join. Actual App SSR exercises the same session prop without issuing workspace requests or serializing private metadata. This is host execution, not browser or UI automation.

The new tests start zero HTTP servers; pre-existing HTTP regression fixtures close their owned servers. Tests remove their compilation/SSR cache directories and assert cancellation/listener/timer/channel disposal. The final owned-cache check found zero `mixer-browser-session-*` directories. No global process inventory, browser/UI/capture, native simulator/emulator, phone run, Git mutation, push, publication, stopped-lane retry, customer message or credential operation occurred. The compiler lane is released; no further compiler/test command follows the final green build.

Real browser cookie/cross-tab/bfcache behavior, accessibility/UI, same-origin ingress/CDN/cache isolation, current Endpoint/default verifier/default Repo joining, provider/OIDC identity binding, startup/custody, activation/logout/revocation races, customer/FieldLog immutable-package qualification and GA remain pending. Native and browser/UI/capture checks remain paused. Source/evidence ownership is frozen for root's independent review.
