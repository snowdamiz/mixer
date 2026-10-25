# Independent customer workspace client review

**Disposition: no actionable finding in the reviewed client.** The actual selected
TypeScript compiled under strict checks; the original **12/12** client methods
and **9/9** new independent Node probes passed. No product change was requested
or made. This is client-only host evidence, not App/session composition or browser
qualification.

## Source and producer binding

The review read `console/src/api/workspace-client.ts`, its ordinary
`workspace-directory.ts` dependency, and `console/tests/workspace-client.test.mjs`
against `docs/hosted-customer-workspace-contract.md`. It did not inspect unfinished
backend lanes or modify the sealed HTTP packet.

| Reviewed source | SHA-256 |
| --- | --- |
| `console/src/api/workspace-client.ts` | `a6f7bed91df56745c1170fccf8be6bac119c8e9a1539551c446dd9edb36acdce` |
| `console/src/domain/workspace-directory.ts` | `ee23d78e263ead8fe9d3c5b68c88f44e9a5d9a8b2a20fe709db9ab8fe6c8f4dc` |
| `console/tests/workspace-client.test.mjs` | `c4d95e0e4a8b67cf6b95f304261528ae18a1952c9c1b9d2969c38fe60d7f2412` |

Those bytes match the producer's
`verification/console-workspace-client/attempts/20261025T140620108003Z/receipt.json`.
That producer packet records the full console's 68 tests and build. This review
independently replays only the twelve client tests, then executes nine additional
probes against a separately compiled selected-source snapshot. It does not claim
to independently repeat the full console suite or build.

The supplied revision `6ed7df4f147b3a3254dab91dd3224b9513f586a8` is root's repair
HEAD context; exact copied input hashes bind the uncommitted client. No selected
source changed during the passing run.

## Request and token assessment

The client captures one trusted configured API origin. It requires HTTPS unless
HTTP loopback is explicitly enabled, rejects credentials/path/query/fragment in
that origin, and never takes an origin from tenant IDs or response fields. Its
two fixed request paths match the contract. Projects encode the full validated
organization ID exactly once in `organization_id`; dots, slashes, plus, percent,
Unicode and query punctuation remain query values.

Every request independently resolves the supplied current-session function.
Tokens are not cached or persisted by the client. Invalid token material rejects
before fetch. The bearer appears only in the Authorization header; no body or
alternative token parameter is emitted. Fetch options explicitly set
`credentials: omit`, `redirect: error`, `cache: no-store`, and
`referrerPolicy: no-referrer`. The returned API object and validated pages are
frozen. Those flags were checked at the actual fetch-call boundary; the new
redirect test additionally exercises native Node fetch against two owned local
HTTP origins and proves the second origin receives no request.

The page argument is a closed typed request with bounded integer limit and an
optional bounded opaque cursor. The client does not decode or invent cursor
authority; the server owns canonical cursor/version/collection validation. This
matches the console-facing opaque cursor contract. Missing or invalid selected
organization IDs cannot silently request an unscoped project collection.

## Deadlines, cancellation and output assessment

One timer covers session-provider resolution, fetch and body consumption. Caller
abort and timer expiry race the whole operation. Checks after awaited provider
and fetch results prevent a late token from starting a fetch and cancel a late
unread response. Cancellation is best effort and is not awaited, so an underlying
body cancellation promise cannot extend the caller's deadline. Late rejected
fetch work remains handled by the operation's installed promise handlers.

Responses must have status 200 and accepted JSON media, cannot be redirected,
and pass declared-length validation before reading. Actual accumulated bytes are
bounded to 262,144 independently of Content-Length. Reader operations, including
empty chunks, are finite, and malformed UTF-8/JSON or invalid pages fail closed.
The domain dependency validates closed page/row shapes, IDs, nullable names,
canonical role arrays, duplicate rows, project organization equality and page
bounds, then returns frozen copies. It preserves the server's row ordering.
Subsequent actions must still authorize at the server; visible roles and cursors
never become release or artifact authority.

Expected HTTP failures become bounded categories. Other provider, transport,
stream or validation failures are converted to fixed `WorkspaceClientError`
messages without raw body, token, URL, cause or provider text. Even a thrown
instance with modified message/code is reconstructed and restricted to known
categories. The client performs no hidden retry, mutation or session refresh.
Its caller remains responsible for choosing a session provider, aborting work
when session/selection changes, and rendering precise states.

## Independent execution

```sh
python3 verification/console-workspace-client-review/run.py \
  --source-revision 6ed7df4f147b3a3254dab91dd3224b9513f586a8
```

Passing **run-3** binds input tree
`2a8ca1562437b592e1a9afe6d55209c723af33bf176f2eb91d549c979b541d51` and compiler
dependency manifest
`177b66542160ed5cb34ac13e2fdb818c5e34cbc5827e51172cd0f9f80abeacd3`.
Environment: Node 22.23.3, TypeScript 5.9.3, Darwin arm64. The collector snapshots
an explicit source allowlist, compiles only the client and its domain import,
records every compiler input and emitted-file hash, replays the original twelve
tests, then executes the nine new probes against the emitted snapshot. Exact
commands, tool versions, stdout/stderr, hashes and cleanup are retained.

The new probes establish:

1. Native fetch rejects a cross-origin 302 and never sends the bearer to its sink.
2. A fetch that ignores abort is bounded by timeout; its late unread response is
   cancelled rather than decoded or returned.
3. Caller cancellation wins a pending fetch, and its later rejection does not
   create an unhandled error or replace the fixed aborted result.
4. Aborting an active reader returns promptly even when underlying stream
   cancellation never settles; the reader lock is released.
5. The real UTF-8 byte boundary accepts 262,144 bytes and rejects 262,145 bytes.
6. Rejected status/media cancels unread private bodies and sanitizes errors from
   body cancellation itself.
7. Concurrent calls resolve independent tokens, preserve exact full IDs, and use
   the required cookie/redirect/cache/referrer/header/body settings.
8. Invalid scope, roles, names and extra fields reject; accepted pages are deeply
   frozen and cannot be modified by the caller.
9. Late provider tokens start no fetch, and modified provider error instances
   expose no private text or unknown error code.

Earlier attempts remain preserved. **run-1** compiled successfully, then the
review collector rejected a relative compiler `--listFiles` entry that needed
resolution against its snapshot working directory. **run-2** passed the original
twelve tests but misclassified Node's own `node-compile-cache` directory as leaked
client compiler scratch. The check now distinguishes the client's named temporary
directory from runtime cache; the parent removes both. Neither failure required
a product fix. Every attempt removed its owned scratch.

## Limits and separate integration work

The new tests close their two owned loopback listeners and all connections in
`finally` blocks; the original loopback fixture also closes its listener. No
production endpoint, browser, native runtime, capture process or provider account
is used. Cookie/cache/referrer behavior in an actual browser, root App/session/
selection composition, login/SSO and user interaction remain pending.

The independent integration lane separately identified a backend access-token
scope-filter omission for `mixer.workspace.read`. Root owns that correction and
its real-JWT regression. This client forwards the bearer unchanged and correctly
categorizes a resulting 403; the finding is not a client defect, and this review
does not qualify that fix or repeat the Node-to-Phoenix join.

Deployed API/CORS/Neon/Cloudflare behavior, production lifecycle/revocation,
customer acceptance, FieldLog immutable published-package consumption and G22/G24
remain separate gates. No product/shared/Git edit, production publication,
credential change or customer message occurred. Browser/capture/native tests
remain paused/pending.
