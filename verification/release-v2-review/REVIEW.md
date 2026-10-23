# Independent release-v2 composition review

No confirmed implementation defect remains in this bounded review of immutable
source `16f6175441565adf5d1a2dc13bf2a591e65518e6`. This is evidence for the local
development HTTP/storage composition slice, not release authorization or GA.

The independently authored host probes passed `go vet ./release` and
`go test -race -count=1 -json ./release -run ^TestReview`: **9 top-level tests,
36 executions including subtests, zero failures and zero skips**. The runner
exports the pinned `services` tree, removes its existing Go test files, copies
only this review's original test source into the private export, and removes the
export afterward. No implementation, other lane, physical-device, production,
customer or credential state was changed.

## Source analysis

- `server.go` selects `/v1` or `/v2` before typed body decoding. Upload,
  validation and channel mutations require agreement between route, registered
  host, artifact and assignment. Public reads filter protocol families. The
  existing v1 public artifact envelope remains `signed_manifest` plus `payload`.
- `versioned.go` keeps v1 records untagged with their previous JSON field layout,
  gives v2 a closed explicit storage discriminator, and replaces receivers only
  after a complete successful decode. PostgreSQL dispatches an exact numeric
  signed schema into a separate complete typed decoder. A failed decoder does
  not try another protocol.
- `store.go` clones the old snapshot, applies writes to the clone, then commits
  the schema upgrade, domain objects, idempotency response, audit and outbox
  together through the existing durable write path. An application callback
  failure does not publish the clone. The new reopen checks bind storage
  variants and channel heads to their immutable artifact and stored schema.
- `storage.go` and `postgres.go` bind artifacts/channels to authenticated tenant
  scope, require validated artifacts, preserve immutable payload/signature bytes,
  and reject protocol changes or non-increasing sequences at an existing head.
  Runtime fingerprint remains part of the channel key. Both protocols share the
  original capacity, idempotency, role, audit and outbox mechanisms.
- PostgreSQL migration001 is unchanged from the pinned commit's parent, with
  SHA256 `c352755698244eff1a5d65ac32d0255478ea270be1fc143a94bdbba876b47605`.
  Its existing opaque signed `bytea`, FORCE RLS, grants, ownership/startup guards
  and SQL sequence enforcement remain the storage contracts.
- `updater.Open` now rejects non-v1 protocol/ABI/UI combinations before storage
  creation. The public Swift HTTP consumer pins one selected version and checks
  the artifact URL's protocol, digest, tenant and origin before verification.

## Original adversarial checks

`independent_test.go` constructs new non-executable TEST payloads, scoped hosts,
typed HTTP/storage grants, and standard Ed25519 signatures from deterministic
public TEST seeds. It does not consume the implementation lane's fixtures or
test helpers. It checks:

1. A v2 write staged inside a transaction followed by a forced callback error
   leaves the schema1 file byte-identical, consumes no key, and permits a later
   successful transaction to use that key once.
2. Cross-version uploads, version hints in query strings, unknown/case-mismatched
   route families, wrong tenant tokens, signed tenant substitutions and reader
   writes reject without upgrading or mutating schema1.
3. Missing, mixed, unknown, duplicate, null, trailing, case-confused, floating,
   negative and string-valued storage variants reject; failed record/channel
   decoding preserves the receiver.
4. PostgreSQL signed-byte dispatch accepts each original protocol and rejects
   version-confused schemas, extra envelope tags and malformed discriminators.
   This check calls the adapter's actual decoders without starting a database.
5. An unpublished rollback target and a stale sequence reject. A fresh greater
   rollback sequence survives restart and an idempotent retry. Previously
   published v1 HTTP bytes, update bytes and audit hashes remain identical.
6. Sixty-four legacy records exhaust shared capacity; a v2 overflow fails while
   preserving schema1 and all existing bytes.
7. Eight concurrent distinct requests for one v2 assignment sequence produce
   one publication and seven conflicts, with one set of durable effects.
8. One scope/runtime cannot register both protocols, and cross-protocol
   validation cannot reinterpret a validated legacy record.
9. A tenant's v1/v2 idempotency collision rejects without upgrade, an authorized
   same-tenant retry preserves its original response, another tenant can reuse
   the key independently, and tenant reads cannot see the other tenant's data.

## Matched implementing-lane evidence

`audit_evidence.py` independently matched all **57 source manifest entries** to
the immutable pin and all **63 preserved evidence files** to their byte lengths,
SHA256 hashes and committed contents. It reparsed the retained raw results:

- Full Go race output: 839 passed test executions, zero failed or skipped tests.
  Three package-level `skip` events denote packages without test files; they are
  listed explicitly in the audit report. Vet exited zero. CLI reported 15 tests.
- Real isolated PostgreSQL 17.11 output: 13 top-level functions and 46 total
  executions, zero failures/skips; 12 functions exercise the database and one
  checks configuration. The receipt reports cluster removal. Existing SQL
  migration bytes are unchanged.
- Actual loopback HTTP to the public Swift verifier: v1 and v2 reports pass,
  selected version and URL binding remain explicit, v1 has no typed grant
  authority, and v2 has two verified typed grants plus signed resource limits.
  The optimized Python harness records old-binary schema2 refusal without
  mutation and v1/v2 preservation across restart.
- Existing v1 HTTP/Swift CLI/local integer-VM regression reports pass. That
  harness uses an existing VM binary and does not independently attest its
  source build.

Those implementing-lane commands were **audited from preserved output**, not
rerun by this reviewer. The original independent race probes are separate.
Implementation source manifest SHA256:
`15a98c124cbe66d7b1d4635f58d57aaff6e0d6512141e531042a295c8e16ac36`.

## Evidence and replay

- `evidence/16f6175-final/receipt.json` records exact commands, tools/versions,
  tool hashes, source export manifest/digest, original test hash, raw output
  hashes and all passed names. Go was `go1.26.4 darwin/arm64`; Python was 3.14.8
  on macOS 27.0.1 build26A434.
- `evidence/16f6175-matched-evidence-final.json` records source/evidence matching,
  reparsed counts, scope and the exact Git inspection commands/hashes.
- The initial independent run failed because this review's HTTP helper omitted
  `Content-Type: application/json`. The rejected requests never exercised the
  intended successful operations. Both initial raw output and the exact initial
  probe source are retained under `evidence/16f6175-initial/`. Adding that header
  to both original request constructors fixed the review harness; no product
  source changed.
- The initial evidence audit treated Go's three package-level no-test-file
  events as skipped tests. Its failed report is retained at
  `evidence/16f6175-matched-evidence.json`; the final audit distinguishes `Test`
  events from package events. The implementing-lane receipt separately discloses
  its CLI summary classifier correction from preserved successful output.

Replay the original host probes with a new evidence name:

```sh
python3 -B verification/release-v2-review/run.py \
  --revision 16f6175441565adf5d1a2dc13bf2a591e65518e6 \
  --name another-local-replay
```

The HTTP/Swift evidence is scoped to small non-executable TEST payloads and
typed metadata verification. It does not establish native guest imports,
capability execution, activation, compiler/OTA eligibility, immutable published
FieldLog consumption, outbox dispatch, hosted identity/deployment/backup/failover,
signing infrastructure, physical iOS/Android qualification or GA approval.
Phones remained disconnected and no device calls were attempted.
