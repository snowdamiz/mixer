# Stripe raw-body capture: next private implementation contract

Status: **proposal; root selection pending; no implementation or HTTP admission accepted**.
This W14/G23 slice follows product-plan sections 13.2 and 17. The accepted pure
signature verifier remains unchanged. Its module SHA-256 is
`3fa0a2d8bee3e4eb9a4204857aaec0d16565df7c0d3f0aa8062158d51f2e3cb6`;
the accepted 69-input hosted digest is
`eb6f50bde86c742e269a605f15e3170d8dd18646f71289c2b8e5c470f5f4808d`.
Both were rechecked for this contract. The prior 127 host passes, two existing
Linux-only skips and 2,352 independent signature cases are upstream evidence,
not raw HTTP evidence.

The next owner may implement a private capture module and disposable test Plug.
Do not add a live endpoint/route, success acknowledgment, secret owner, database
schema or Oban worker in that slice. A captured or signature-valid request is
neither an accepted Stripe event nor billing authority.

## Pinned behavior and its limits

The examined stack is Elixir 1.20.4 / OTP 29.1.1, Phoenix 1.8.16, Plug 1.20.3,
Bandit 1.13.1 and Thousand Island 1.6.0. The installed dependencies, lockfile,
tool versions, source observations and executable probes are frozen under
[`verification/stripe-raw-body-contract`](../verification/stripe-raw-body-contract).
General-purpose dependencies already appear in `THIRD_PARTY.yml`; no dependency
is added. Only official library source/documentation informed framework behavior.

* `Plug.Conn.read_body/2` delegates to the adapter. It returns
  `{:ok, bytes, new_conn}`, `{:more, bytes, new_conn}` or `{:error, reason}`.
  Carry the returned connection into every subsequent read and caller. Plug
  caches nothing. Its documented length/read-length values are approximate;
  `length: 1_048_576` does **not** enforce a strict accepted-body byte count.
  See [versioned Plug documentation](https://hexdocs.pm/plug/1.20.3/Plug.Conn.html#read_body/2)
  and frozen `plug/conn.ex:1135–1195`.
* `get_req_header(conn, "stripe-signature")` returns every matching value without
  comma joining. Bandit HTTP/1 lowercases header names and preserves occurrences;
  HTTP/2 preserves ordinary occurrences (cookies are special). Never use a map,
  first-value lookup, `put_req_header/3` or comma-join to capture this header.
  These are adapter-exposed field values, not the original wire header octets:
  HTTP parsing can remove field-line whitespace. The **body** must be exact.
* Bandit header parsing rejects multiple Content-Length field occurrences, even
  identical ones, but accepts a **single** identical comma list such as `3, 3`.
  HTTP/1 rejects Content-Length plus Transfer-Encoding and unsupported framing
  before Plug. The capture policy below is deliberately stricter about a comma
  list. Do not reimplement HTTP framing or claim to receive rejected requests.
* Bandit's HTTP/1 chunk reader strips chunk framing, ignores chunk extensions,
  and ignores trailers. Its trailer-reading path uses socket/default options,
  not the capture call's read timeout. HTTP/2 reads can exceed the requested
  length by a DATA frame, loop over multiple receives using the same per-receive
  timeout, and log inspected trailer values. Those hazards require explicit
  qualification/remediation before enabling those paths on a public webhook.
* Bandit adapter operations must run in the stream owner process. Spawning a
  `Task` to call `read_body` fails that ownership check. A synchronous deadline
  check or `read_timeout` cannot forcibly cancel an arbitrary blocking adapter.
  Thousand Island also emits received bytes in low-level telemetry metadata;
  the endpoint owner must exclude/redact raw transport telemetry and request
  connection metadata before any exporter/logger. Component silence alone does
  not prove end-to-end absence of body/header logging.

Specific source locations and hashes are in `source-observations.json`; installed
source snapshots are evidence about these pins, not stable public adapter APIs.
Dependency upgrades must repeat qualification.

## Private boundary

Proposed module: `MixerHosted.Billing.RawWebhookCapture.capture(conn)` returning
`{:ok, %{raw_body: binary, signature_header_values: [binary]}, new_conn}` or
`{:error, closed_reason, latest_conn}`. If `read_body` returns an error without
an updated connection, retain the most recent returned connection and mark the
connection unusable. A transport exception must propagate to framework error
handling rather than be turned into success. Never inspect/log the exception's
arbitrary reason, connection, body or headers. Implementation may use a fixed,
sanitized capture exception for a locally detected unusable connection.

The module has no public options for limits, tolerance, UTC time or secrets.
Use a trusted monotonic clock internally for reading deadlines, with a bounded
test seam that cannot be selected from HTTP input. It never parses JSON,
normalizes whitespace/Unicode/newlines, decompresses, decodes a charset, persists,
fetches configuration, invokes Stripe or calls the signature verifier itself.
Return the original header value list and concatenated exact body bytes. The
future caller passes those unchanged to `WebhookSignature.verify/4`, with current
endpoint secrets and trusted UTC clock supplied by a separate server owner.

Proposed test-only envelope (all values await root selection):

| Attribute | Proposed admission policy before the first body read |
| --- | --- |
| Method/path | Literal `POST`, `request_path == "/api/v1/webhooks/stripe"`, empty `query_string`. No percent decoding, path aliases, trailing slash, case folding or query parameters. The module checks raw `request_path`, not only Phoenix's decoded `path_info`. This is a private test target, not a registered/public route. |
| Parser placement | First body consumer, before `Plug.Parsers`, decompression, body instrumentation or controller conversion. Future endpoint dispatch must inspect the original method before `Plug.Head` can rewrite it. Existing Endpoint currently has RequestId, Head and Router; Router only exposes `/health/live`. An unfetched `body_params` value alone cannot prove nobody read the body. |
| Content-Type | Exactly one field, at most 128 bytes. Accept ASCII case-insensitive `application/json`, optionally one `charset=utf-8` parameter, with SP/HTAB around tokens/semicolon/equals. Accept no other parameter, quoted value, comma list, duplicate charset or invalid ASCII. Empty/missing/duplicate fields fail. This parses only metadata and does not transform the body. |
| Content-Encoding | No field at all; even `identity`, duplicate or empty field fails. No decompression. |
| Signature | Exactly one occurrence, 1–4,096 bytes. Preserve its bytes and singleton list. The existing verifier retains responsibility for field grammar, supported schemes, HMAC and freshness. Do not trim a malformed signature into a valid one. |
| Other framing metadata | Reject `Trailer`, `Expect` and upgrade requests before reading. No 100-continue negotiation is selected. Preserve repeated header occurrences. Proxy-selected endpoint identity and forwarded headers cannot select secrets/account/mode. |

Canonical Content-Length, where required or present, is exactly one field of
ASCII digits, `1` through `1048576`, no sign, comma, leading zero or surrounding
whitespace in the **adapter-exposed value**. Count/length checks precede numeric
conversion; at most seven digits. Framework rejection may happen first. For
missing length on a supported streaming path, the same aggregate cap still
applies; zero-length completion always fails. Never trust declared length as the
sole byte-count enforcement or interpret surplus wire bytes as body bytes.

## Transport profile is a root decision

Two bounded implementation candidates are recorded; neither is selected or
proof of a hard wall-clock bound:

1. **Normal Bandit framing**: accept HTTP/1.1 with canonical Content-Length or a
   single `Transfer-Encoding: chunked` and no Content-Length; accept HTTP/2 with
   optional canonical Content-Length and no Transfer-Encoding. HTTP/1.0 and other
   protocols fail. Reject `Trailer` declarations, but recognize that undeclared
   trailers can only be handled inside the adapter. Exact chunk payload/DATA
   bytes are accumulated, never wire chunk sizes or trailers. HTTP/2 `te` and all
   unsupported transfer/content codings fail. This candidate fits normal HTTP
   framing but still needs the trailer logging, timeout and memory findings
   qualified/remediated. A capture module cannot enforce invisible trailer policy.
2. **Restricted private qualification profile**: HTTP/1.1 and canonical
   Content-Length required; any Transfer-Encoding fails before reading. This
   reduces the first private test surface. It is not selected public API behavior,
   Stripe delivery compatibility, a permanent product restriction or a substitute
   for deadline qualification. Chunked and HTTP/2 remain mandatory unresolved
   transport paths before the full webhook plan is accepted. An ingress that
   translates protocols must independently prove byte and header-occurrence
   preservation; it does not inherit qualification from the private profile.

Root must choose/adjust one profile before implementation starts and record that
choice in its receipt. Do not silently convert a failed HTTP/2/chunked test to a
pass by changing to profile 2. No live endpoint becomes available at this stage.

## Read algorithm and precise bounds

Proposed fixed limits: accepted body `1..1_048_576` bytes; capture read target
32,768 bytes; at most **64 calls**; per socket-read timeout at most **1,000 ms**;
absolute capture success deadline **5,000 ms** from entry. These bound the module's
accepted data/read count and successful admission time. They do not bound bytes
already buffered by the HTTP server/OS or arbitrary adapter allocation.

1. Clear any prior capture result; validate the full envelope without body reads.
   Establish the monotonic deadline at entry, including metadata validation.
2. Before each read, reject expired deadline, exhausted call budget or exhausted
   byte budget. Set `length` and `read_length` to
   `min(32_768, remaining_body_budget)` and `read_timeout` to
   `min(1_000, positive_remaining_deadline_ms)`. With known Content-Length also
   cap by remaining declared bytes. Never pass zero or infinity as a timeout.
3. Match only the documented result shapes with binary chunks and a connection.
   Immediately check time again, then `byte_size(chunk)` and aggregate size
   **before** appending/copying it. Reject a chunk over the remaining aggregate
   budget or remaining declared bytes; never slice/truncate and verify a prefix.
   A returned chunk may exceed the requested read target, particularly on HTTP/2;
   accept it only within those aggregate bounds. No unbounded concatenation or
   storage of rejected data. Use a bounded reverse chunk list and flatten once
   on terminal success. Up to two body-sized copies may exist during flattening;
   this is not a claim of a 1 MiB process-memory ceiling.
4. `:more` must contain nonempty bytes and leave positive aggregate budget. If
   aggregate size is exactly 1 MiB with `:more`, reject immediately rather than
   reading more. This conservatively rejects a chunked exact-limit body when EOF
   needs one more read; document/test it, do not accept an unproven prefix. With
   known length, `:more` at that length also fails. Empty `:more` fails closed as
   no progress. No draining an over-limit/infinite stream. A byte-under-limit
   stream requiring more than 64 reads also rejects.
5. `:ok` requires nonempty total body and exact declared length when present.
   A final empty chunk is allowed only after earlier nonempty chunks and only
   within budgets/deadline. Clear temporary references on any ordinary return;
   do not attach raw content to a failed connection, assigns, errors or telemetry.

Do not advertise a five-second forced request termination: Bandit can perform
multiple internal reads with independently renewed timeouts before returning.
The algorithm rejects a late result but cannot interrupt that call. Even the
restricted profile cannot prove cancellation of an arbitrary adapter. A separate
endpoint/transport owner must qualify deadline termination, slowloris handling,
header-read deadlines, concurrency/rate limits, connection/stream disposal,
logging and buffer limits. Any required hard end-to-end bound remains **pending**
until that owner supplies real HTTP evidence and an appropriate cancellation
mechanism. Merely timing out a caller/task or sending an ordinary timer message
does not establish cancellation. Do not call private capture implementation
production admission while that boundary is unresolved.

## Failure and later ownership

Closed reasons may distinguish envelope, unsupported framing, too large, empty,
length mismatch, read limit, no progress, read deadline, transport failure and
unavailable state. They contain no request-derived strings. Capture sends no
response and invokes no downstream handler after failure. Future endpoint
handling must halt on all failures; suggested mappings are 400 malformed,
413 oversized, 415 unsupported media/content coding, 408 read deadline, and
503 unavailable internal configuration. Framework errors may instead close/reset
the connection. **No failure may produce any 2xx**, and no failed/partial read
may resume normal routing. With unread HTTP/1 bytes the future owner must qualify
connection close rather than permit request smuggling or automatic unbounded
body draining. Error mappings are future endpoint policy, not an acknowledgment
implemented here. The disposable test Plug uses a non-2xx marker for successful
capture too, so its success cannot resemble provider receipt.

After capture, separate contracts must provide: server-owned endpoint identity,
Stripe account/test/live mode/generation and current secrets; signed raw-body
verification; bounded JSON/event parsing including duplicate-key ambiguity and
event schema; authenticated account/mode checks; event-ID/content conflict
handling and durable inbox deduplication; one PostgreSQL transaction committing
that inbox and its Oban reconcile job; commit-confirmed acknowledgment; and
idempotent current-state Stripe reconciliation for duplicate/out-of-order events.
No request-selected key, clock, tolerance or unverified event account can choose
its authority. Replays in the signature window still require inbox deduplication.
Parsing/durability failures cannot receive a success acknowledgment either.

## Required implementation evidence

The executable contract-stage probes below inspect actual installed libraries
without starting a service. They demonstrate API semantics only. The complete
next-owner matrix is in `test-matrix.json`; every row starts **pending**.

* Use one disposable localhost Bandit listener, port 0, with the real private
  capture module in a test Plug and deterministic synthetic HMAC bodies. No
  production Endpoint/route, Stripe API, database or secret. Use raw TCP HTTP/1
  clients for repeated headers, framing failures, chunk segmentation/trailers,
  incomplete bodies, overlimit streams, disconnects and slow sends. Plug.Test
  alone cannot prove wire behavior. Prove the body reaching the existing signature
  verifier has identical SHA-256/bytes; whitespace/newline/UTF-8 byte changes must
  invalidate the original signature. Preserve duplicate signature occurrences,
  with zero verifier calls when the envelope rejects them.
* If profile 1 is selected, use the pinned real HTTP/2 stack and an actual
  localhost HTTP/2 client for DATA/end-stream boundaries, length mismatches,
  duplicated header occurrences, trailers and deadline behavior. Profile 2 must
  prove HTTP/2/chunked rejection; its successful HTTP/1 tests leave profile-1
  qualification explicitly pending. Resolve and verify telemetry/trailer redaction
  before claiming no raw-content export. Match each failure to zero 2xx, zero
  downstream/domain calls and connection/stream cleanup.
* Separately use a bounded fake Plug adapter for oversize returns despite a small
  `length`, empty `:more`, many chunks, malformed return shapes, errors, raises,
  late results and updated-connection threading. These are component fault tests,
  not Bandit/socket or forced-cancellation evidence. A harness timeout may kill
  its owned test process but cannot be reported as a product guarantee.
* Bound each wire client and test process externally, close sockets and stop the
  owned listener/processes on success and failure. Record versions, exact source
  digest/profile, commands, outputs, failed attempts and cleanup. Preserve other
  projects' services. No native runtime/device is needed for this slice.

Contract-stage commands:

```sh
python3 -B verification/stripe-raw-body-contract/collect.py
python3 -B verification/stripe-raw-body-contract/verify.py
```

This document and its sealed source/probe receipt are a reviewable proposal.
Raw-body implementation, real HTTP matrix, hard cancellation, ingress/provider
compatibility, endpoint ownership, durable inbox/atomic Oban, Stripe test-mode
reconciliation and G23 remain pending.
