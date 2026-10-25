# Independent console workspace composition review

The corrected local composition passes this review. No actionable finding remains
in the frozen sources tested in `freeze-2`. This accepts the bounded controller,
Solid owner and production-route composition slice; it does not qualify live
login, customer/provider operation, browser behavior or a GA gate.

The final independent receipt is
[`verification/console-workspace-composition-review/attempts/freeze-2/receipt.json`](../verification/console-workspace-composition-review/attempts/freeze-2/receipt.json).
It records base revision `9a2bf16b59f98f2e0094ea6820c337ec1ed82c8c`, copied inputs,
every command/output, tool versions, cleanup and source tree SHA-256
`948d9af6d29f85dc4e727b97b952558de2a4bf19f654ed1dd357fa416633be22`.
The selected live files matched those copies after execution. This digest covers
the receipt's full allowlist, including review harness, console sources/tests,
instructions, configuration and website brand inputs; it is not the Git tree ID.

## Findings repaired before acceptance

1. The initial binding updated the controller only in `createEffect(on(session,
   ...))`. An actual Solid client-runtime probe showed both an earlier memo and
   a later `createComputed` observing a logged-out session together with the prior
   session's ready organization rows. Replacing a ready session with a different
   client exposed the same mismatch. Effect ordering therefore did not establish
   a session boundary. Root repaired the binding: every read compares the live
   immutable session value with the admitted epoch, returns a frozen empty
   loading/auth/unavailable fallback during a mismatch, and exposes only six
   guarded UI commands. The private controller's session/subscription/disposal
   methods are no longer reachable through the binding. Disposal hides data
   before cancellation can reenter. The historical reproduction and source copies
   remain in [`early/`](../verification/console-workspace-composition-review/early/).
2. `/workspace/` matched `WorkspacePage` and active workspace navigation while
   the shell rendered `Page not found`, because its label compared the raw
   pathname exactly. The failing real StaticRouter SSR result remains in
   [`freeze-1/11-independent-ssr.stdout`](../verification/console-workspace-composition-review/attempts/freeze-1/11-independent-ssr.stdout).
   Root now obtains the label from the matched route's original path. The final
   run verifies the corrected workspace trailing slash and query/fragment forms;
   the producer regression also covers build/release forms and an unknown child.

Root also added a permanent ordinary-suite regression for a pure consumer
registered before the binding. The child test wrapper removes inherited
`NODE_TEST_CONTEXT` and requires four child tests with zero failures, so an empty
child execution cannot masquerade as a pass.

## Reviewed contracts and sources

The review read `AGENTS.md` and `PLAN.md` and inspected the actual controller,
binding, context/provider, routed page, application routes/shell and their new
tests. The existing ordinary directory domain, client, component and brand files
were reviewed only as dependencies. No product source was edited by this lane.

| Final source | SHA-256 |
| --- | --- |
| `console/src/state/workspace-controller.ts` | `dffa9e47db325db6f8da3fcd4467059fb1741cd619fd594c37befad8c09ccac4` |
| `console/src/state/workspace-binding.ts` | `cf91e0324ec50fd56803f149c876283043d01ae8dfdcae6cb9fb5bfe0d4d0d94` |
| `console/src/state/workspace-context.tsx` | `9bb2ec22c4338250f9c4c512a9b13d298fd1a11e6614490d1a28d5a6cb2018bf` |
| `console/src/components/WorkspacePage.tsx` | `d007823676714c3b9ecbc87ae18fa6796846bdc483c4a1827cc0ef4a300fca53` |
| `console/src/App.tsx` | `3c7fe14c2484080501372d41b924932094b940ca74cd65057fd45bcfd8240afc` |

Request identity combines the active request object, generation, immutable session
epoch, client identity and abort state. Organization and session changes clear
dependent project state before cancellation/notification. Response validation and
error classification are followed by renewed current-request checks. The
notification loop stops superseded rounds, honors removal/addition, and isolates
synchronous and rejected asynchronous observer failures. These are in-memory
coordination safeguards; they do not grant hosted authorization or release
authority.

The provider lives outside the router and owns request/selection lifetime. The
page receives a shared binding and delegates its six UI operations. A session
adapter must supply a fresh immutable session value for every account/session
epoch, including replacement that reuses the same client. Mutating or reusing an
old epoch object as a new session is outside this explicit contract. Browser
navigation lifecycle remains a separate pending check.

## Independent execution

The final invocation was:

```sh
python3 verification/console-workspace-composition-review/run.py freeze-2 \
  --source-freeze 'Root refreeze2: useCurrentMatches route label + permanent pure-consumer regression; producer 20261025T144613993605Z; 2026-10-25'
```

The runner builds copied allowlisted sources with existing dependencies, then
removes its scratch products and dependency symlinks. It never runs the shared
hosted test entry point. Exact absolute subprocess arguments and working
directories are recorded in the receipt. Replays require a fresh attempt name.

| Check | Observed result |
| --- | --- |
| Selected existing controller/binding/app/brand test replay | 33 top-level tests pass; binding wrapper separately executes 4 child tests; zero failed/skipped |
| Strict emitted binding/controller/client/domain compilation | Pass |
| New independent Solid/controller probes | 9 tests pass; zero failed/skipped |
| Actual production TSX/router SSR compilation | Pass |
| New independent SSR/context/route probes | 5 tests pass; zero failed/skipped |

Counts are reported separately: producer tests overlap the reviewed behavior and
the child wrapper is not four additional top-level tests. This lane did not
independently repeat the full console suite or production build. Root's separate
full-suite/typecheck/build receipt is
[`verification/console-workspace-composition/attempts/20261025T144613993605Z/receipt.json`](../verification/console-workspace-composition/attempts/20261025T144613993605Z/receipt.json).

The nine new runtime probes cover earlier-memo/later-computed observations,
batched logout/unavailability/replacement reads and all command guards, an earlier
pure consumer attempting an old-session request, replacement with the same client,
all six completion orders across three request epochs with stale successes and
auth failures, project parsing that reenters session replacement, subscription
churn during nested replacement, disposal inside abort handlers, and rejected
async observers without unhandled rejection. The five SSR probes exercise the
branded production workspace route's honest state messages, ready SSR with zero
adapter calls and no private-value serialization, distinct build/release/missing
routes and disabled production preview paths, a missing-provider failure, and
workspace URL variants. Existing brand parity verifies website token declarations
and logo/favicon bytes.

Tools were Node `v22.23.3`, Python `3.14.8`, TypeScript `5.9.3`, Vite `8.3.5`,
Solid `1.9.17`, Solid Router `1.0.0` and vite-plugin-solid `2.11.14` on
`darwin-arm64`. No dependency was added.

## Preserved failures, cleanup and limits

`candidate-1` is a preliminary successful run. `freeze-1` intentionally retains
the newly discovered trailing-slash failure. The early probe retains its first
reviewer fixture import-path failure and the corrected defect reproduction; an
early SSR fixture build's path failure is described with its tool-output excerpt.
No failed output was replaced by the final successful run. The metadata correction
in [`receipt-corrections.json`](../verification/console-workspace-composition-review/receipt-corrections.json)
clarifies that the selected producer replay, unlike the added probes, starts and
closes its owned ephemeral loopback HTTP listener.

Every final scratch directory and dependency symlink was removed. The producer
binding test closes all connections and awaits `server.close` in `finally`; its
subprocess exited. No browser, DOM automation, screen capture, native simulator,
emulator or phone was used or started. No unrelated process/resource was changed.
Frozen hosted catalog-inspector/authority-driver and rejected outbound Worker V2
lanes were not read, imported, compiled or executed. No commit, push, production
publication, customer message, credential change or destructive migration was
performed by this review lane.

Live login/session acquisition, a production browser's DOM/hydration/router
navigation, layout and accessibility, real hosted/default Endpoint/Repo joining,
provider deployment/operation and final physical-device acceptance remain pending.
This receipt is host development evidence and does not pass any GA gate.
