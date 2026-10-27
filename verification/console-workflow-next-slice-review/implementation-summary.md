# Console first-page return implementation

The customer can now return to the first organizations or projects page after using Next. First remains reachable after a later-page failure, so a failed or expired cursor no longer strands earlier choices. The controls are disabled while their own list loads and hidden for signed-out, invalid or stale project scope. The controller independently guards each action, sends the existing frozen cursor-free first-page request, clears dependent selection immediately and retains no previous rows or cursor history. The Solid binding gates the actions on the current admitted session. Existing ordinary API, transport, permissions and response contracts are unchanged.

## Observed validation

- `node --test --test-concurrency=1 tests/workspace-controller.test.mjs tests/workspace-directory-domain.test.mjs tests/workspace-directory-view.test.mjs tests/workspace-binding.test.mjs`: attempt 1 passes all 57 outer tests, including one binding wrapper, with no failures, skipped or cancelled tests; the wrapper separately records all four nested host binding cases passing. Actual outer decomposition is 31 controller, 14 directory-domain, 11 compiled SSR view and one binding wrapper.
- `node node_modules/typescript/bin/tsc --noEmit`: attempt 1 passes.
- `git diff --check` on the 11 owned source/test/docs files passes.
- Node v22.23.3, TypeScript 5.9.3 and Vite 8.3.5. Focused command took 1.929 seconds; project typecheck took 0.611 seconds. Both had a 50-second deadline.

This is Node host behavior, Solid host reactivity with loopback Node HTTP, compiled Solid SSR markup and TypeScript composition evidence. No browser interaction or runtime accessibility acceptance is claimed. Computer use, capture and native runtime remain paused; physical phones remain disconnected. Real provider login, deployed customer API/Cloudflare operation, FieldLog immutable-package dogfooding and all GA gates remain pending. Production App still needs an admitted session; builds/releases remain unavailable.

## Cleanup and handoff

Owned test PID/PGID 99638 and typecheck PID/PGID 99664 are terminal/reaped and their exact process groups are absent. The version probe PID/PGID 99637 is also absent. No cleanup signal was required. Test hooks removed all newly generated controller temporary, binding cache and SSR directories. No intentionally untracked generated file remains outside this verification packet. Every file in this packet is an intentional source-review, source-binding, log, diff or receipt artifact; no build output is delivered. There was no compiler retry, Git mutation, provider/server deployment, browser/UI/native/capture run or global process inspection.

All 11 paths in `owned-final-source-manifest.json` and this packet are released to root for independent read-only verification and authorized delivery. The tested full console input preimage is retained in `implementation-source-manifest.json`; the initial read-only review preimage remains separately preserved in `reviewed-source-manifest.json`. No further lane source writes or test runs are planned.
