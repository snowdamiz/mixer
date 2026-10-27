# Independent browser session consumer review

No actionable product finding was confirmed in the released source or the executed
host probes. The independent review supports root acceptance of the selected
closed frontend source slice only. Root has not accepted implementation through
this report. Authentication, real browser behavior, backend integration and GA
remain outside this result.

## Reviewed candidate and independence

The root release is
`verification/console-session-and-checkout-root-review/session-consumer-frozen-release.json`.
The candidate is based on HEAD `114a2632fd58076574bd5b2444c511861c3b30d4`, tree
`8666138ed9c87272a35759df84ce968db690abc8`, with selected source digest
`7cd673b6b2c729c60586b0506ef57e0d063183046c76ffab5c44f6b3f88314b8`.
All 65 selected working-tree inputs matched that release before and after each
independent compiler or Node command. The preaccess oracle hash
`58969cf14bb489ff3d3ddce7b2963ee3d762b153facc344beb4bd933a9491f36`
was checked before producer access and each command. The original preaccess
oracles and custody were preserved. Nine canonical cookie/workspace/Solid/package
inputs are compared again against the original b231 baseline in `review-receipt.json`.

The producer's four product files and relevant cookie/workspace dependencies were
read, as were the released producer report, receipt and source manifest. The
independent probes were authored from the frozen 42-item preaccess roster and
executed against a separately emitted candidate and the actual existing cookie
and workspace modules. They do not import or execute producer test bodies. The
Solid probes use the actual Solid client runtime with synthetic EventTargets,
fetch responses, clocks and BroadcastChannel; this is host evidence.

## Results and exact attribution

| Command group | Result | Attribution |
| --- | --- | --- |
| Strict TypeScript emit of browser-session-binding + workspace-binding and transitive modules | Passed; 0.514 s | Independent strict compilation, one command. |
| Independent protocol/controller Node harness | 30 passed, 0 failed; 0.214 s captured wall time | CL01-CL15 and CO01-CO15. |
| Independent Solid `--conditions=browser` harness | 11 passed, 1 failed; 0.221 s | SO01-SO08 and SO10-SO12 passed; SO09 originally failed due to the independent fixture's action timing. |
| Root-authorized targeted Solid `--test-name-pattern '^SO09 '` correction | 1 passed, 0 failed; 0.098 s | Only corrected SO09. This does not relabel the original command as 12/12 passing. |

There are 42 unique roster probes with successful final scoped observations across
these commands. The initial SO09 harness failure is retained and is not counted as
a candidate pass. No full regression, second compilation, Vite build, server or
browser was rerun. Producer typecheck/build/full-regression results remain
producer-attributed evidence, as recorded in its frozen packet.

The protocol probes cover fixed request options, exact response envelopes,
duplicate/escaped aliases, safe integer lexical forms, canonical43 unused bits,
no-store/media-type/length rules, byte and reader-call limits, fatal UTF-8/BOM,
non-200/HTML failure, one deadline through decode, noncooperative fetch/read and
cancel cleanup, and late rejection isolation. The controller probes cover fresh
same/different-generation epochs, captured stale clients, dual exclusive expiry,
900-second cap, unsafe and backwards clocks, current workspace401, scoped caller
abort, actual cookie requests, postawait result/error fences, synchronous observer
exceptions/reentrancy, abort-handler reentrancy and terminal disposal.

The Solid probes cover visible/hidden startup, coalesced foreground replacement,
pure read/action fences, pagehide/pageshow, exact cross-tab invalidation and absence
of channel, queued invalidation/visibility/disposal races, current401, same/different
epoch page/selection/cursor reset, listener/channel ownership, and the current
missing-endpoint/HTML failure behavior. The production main/App reactive prop seam
is source-reviewed and structurally asserted; its actual rendered DOM was not
executed by this independent lane.

## Preserved SO09 harness correction

The original independent `createComputed` observer read the live directory and
unconditionally called `nextProjects({organizationId:'org α',cursor:'MORE'})`.
When the fixture project page became ready, reactivity reran the observer and
immediately started the next page. Existing canonical
`workspace-controller.ts:242-246` permits that call and invokes `beginProjects`;
`beginProjects` sets projects loading. The fixture's following `selectProject`
correctly could not select a row because `workspace-controller.ts:231-236`
requires projects ready. Therefore the original expected selected-project
assertion failed due to an action issued by the test itself.

The original harness and execution wrapper are preserved byte-for-byte as
`solid.test.mjs.before-so09-correction` and
`execute-review.py.before-so09-correction`; original TAP/receipts are in
`run-solid/`. The sole fixture change introduces an `armed` flag around the
explicit revalidation/pure-action transition. Before that transition the observer
only reads state. `fixture-correction.patch` records the exact delta. The separate
targeted run passed with unchanged candidate source. No product fix was made or
requested for this harness failure.

## Contract scope and pending evidence

`checked-pending-matrix.json` maps every preaccess ID to its independent run and
notes structural/producer-only edges. The 42 probes are bounded adversarial
samples, not an exhaustive scheduling or browser implementation proof.

For observer isolation, the independent CO13 runtime probe exercises synchronous
throws and reentrant actions. The closed contract's publication text says
"Subscriber throws/rejections cannot break admission, invalidation or disposal."
Candidate controller line65 also consumes returned-promise rejection, and the
producer's controller test at line232 explicitly includes an async rejecting
observer. That async behavior is source/producer-evidence reviewed, not separately
runtime-replayed here. No expanded asynchronous subscriber API requirement or
finding is inferred.

Pending evidence includes real Endpoint/default-verifier/default-Repo
session-to-workspace composition; accepted callback/storage/provider/OIDC identity
binding; controlled activation/logout/revocation and startup/custody; real cookie,
BroadcastChannel, bfcache, visibility and accessibility/UI behavior; same-origin
ingress/CDN/cache isolation; customer workflows and immutable FieldLog dogfood
packages; native/phone acceptance and all specified GA qualification. The released
canonical endpoint absence remains an expected unavailable state, with zero
workspace calls demonstrated by host fixtures.

Every captured command group was absent after completion. Timers and owned
event/channel listeners were asserted cleaned by the probes; late promises were
settled after cancellation/disposal with no unhandled rejection observed. The
owned emitted scratch and node_modules resolution symlink were removed during
finalization, with emitted file hashes retained in command receipts. No global
process inventory, production/customer/credential change, Git mutation, dependency
installation, hosted edit, stopped callback/Android retry, UI/browser/capture,
native simulator/emulator or phone process occurred. No GA gate is verified.
