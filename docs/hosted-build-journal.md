# Hosted build lifecycle journal

`MixerHosted.Builds.Journal` is an internal, pure persistence codec for the
accepted `MixerHosted.Builds.Lifecycle` API. A journal contains creation inputs
and ordered accepted events. Restoring it invokes `Lifecycle.new/4`, then
`Lifecycle.transition/4` for every row in recorded order. Each stored transition
must return `:applied`; duplicate persisted rows are invalid. There is no stored
`Build` snapshot, current-state override, or arbitrary term deserialization.

## API

```elixir
Journal.new(spec, policy, request_key, now_ms)
# {:ok, document, build} | {:error, lifecycle_reason | :journal_limit}

Journal.restore(document)
# {:ok, build} | {:error, :invalid_journal}

Journal.append(document, event_id, event, now_ms)
# {:ok, document, build, :applied | :duplicate} | {:error, reason}
```

Creation accepts the native lifecycle spec/policy maps or their `Spec`/`Policy`
structs. Append accepts native lifecycle event maps, including exact `WorkerRef`
and `ArtifactRef` structs. Only explicit known fields and enum values convert to
JSON. Restore accepts a string-key map, such as the result of ordinary
`Jason.decode/1`; it does not parse unbounded JSON bytes itself. The storage or
transport layer must bound encoded bytes before JSON decoding.

An exact duplicate append returns the original document and the current replayed
build. It never adds a row or overwrites the first observation time. Duplicate
delivery time is ignored, including invalid or later time, matching the lifecycle
contract. Reusing an event ID with a different payload returns `:event_conflict`.
New events retain lifecycle errors for semantic failures such as stale worker
scope/fence, invalid transition, backoff, deadline and time overflow. Malformed
new event shapes return `:invalid_event`; an invalid ID returns
`:invalid_event_id`. Invalid persisted data always returns `:invalid_journal`.

## Schema 1

The only top-level keys are `schema`, `creation` and `events`. This is an example
newly created journal; every key shown is required:

```json
{
  "schema": 1,
  "creation": {
    "spec": {
      "organization_id": "org-1",
      "project_id": "project-1",
      "application_id": "app-1",
      "build_id": "build-1",
      "platform": "ios",
      "source": {
        "kind": "revision",
        "sha256": "0000000000000000000000000000000000000000000000000000000000000064",
        "reference": "refs/heads/main"
      },
      "toolchain_lock_sha256": "0000000000000000000000000000000000000000000000000000000000000065",
      "build_definition_sha256": "0000000000000000000000000000000000000000000000000000000000000066"
    },
    "policy": {
      "max_attempts": 5,
      "timeout_ms": 100,
      "retry_backoff_ms": 10
    },
    "request_key": "request-1",
    "now_ms": 0
  },
  "events": []
}
```

Every event row is exactly `{"id": string, "event": object, "now_ms": integer}`.
Event objects have these exact fields:

| `type` | Other required fields |
| --- | --- |
| `start` | `ref` |
| `expire` | `ref` |
| `cancel` | `reason` |
| `retry` | none |
| `stopped` | `ref`, `diagnostic_sha256` |
| `completed` | `ref`, `result` |

A `ref` is exactly `organization_id`, `project_id`, `application_id`, `build_id`,
`platform`, `attempt` and `fence`. No `__struct__` marker is serialized or accepted.
Successful results are exactly `{"outcome": "succeeded", "artifacts": [...]}`;
failed results are exactly `outcome`, `class`, `code` and `diagnostic_sha256`,
where `outcome` is `failed`. Artifact objects are exactly `kind`, `sha256` and
`size_bytes`.

Enums use their lifecycle atom spelling as a string. Platforms are `ios` and
`android`; source kinds are `revision` and `upload`. Failure classes/codes retain
the lifecycle allowlist and its class/code pairing. All seven distinct artifact
kinds are required: `unsigned_native_binary`, `guest_artifact`,
`resource_inventory`, `debug_symbols`, `compatibility_report`, `sbom` and
`provenance`. Equal artifact digests must retain equal sizes. Enum decoding uses
finite literal tables and never creates atoms from caller strings.

## Bounds and rejection

All objects are closed: unknown, extra or missing fields, wrong key types,
unexpected structs/tuples, invalid enums, malformed references/digests and wrong
primitive types fail. Field/list bounds run before JSON-size traversal and before
replay. The codec does not recursively walk arbitrary input to convert it.

The journal has at most 32 event rows, each successful result has exactly seven
artifacts, and JSON serialized with default compact JSON escaping must be at most
131,072 bytes. The byte budget counts JSON punctuation, decimal integers, UTF-8
bytes and escaping without allocating an encoded journal. A fixed depth ceiling
of eight additionally bounds that traversal. Fields retain lifecycle byte limits:
128-byte identities/request/event IDs, 1,024-byte source references and 512-byte
cancellation reasons. Text remains valid printable UTF-8, without normalization;
digests remain 64 lowercase hexadecimal bytes. Times are integers from zero to
9,223,372,036,854,775,807; worker counters, policy and artifact sizes retain all
lifecycle bounds.

The lifecycle currently cannot accept 32 distinct events in one valid build:
its finite attempt and terminal-state rules stop earlier. Tests exercise the
19-event five-attempt timeout/retry path and reject repeated rows at 31/32 as
invalid replay, plus 33-row input at the list bound. They do not forge in-memory
build state to manufacture a passing 32-event history. The JSON size cap is an
additional ceiling; field bounds can reject malformed oversized data sooner.

Replay rejects invalid transition order, decreasing observations, stale worker
references, duplicate IDs and scope mismatches. A party able to rewrite an entire
valid history can construct a different valid history: this codec provides no
cryptographic integrity or authenticity guarantee.

## Evidence and limits

`verification/hosted-build-journal/receipt.json` records the exact source hashes,
base revision, Elixir/Erlang versions, commands, exit codes and raw output hashes.
The focused suite round trips through the existing Jason dependency and compares
each accepted append and restored state against the existing lifecycle API.
It covers creation, every event/result enum, all artifact kinds, cancellation and
timeout reconciliation, retries/fences, duplicate/conflicting delivery, corrupted
history, malformed input, oversized/deep structures and Unicode byte boundaries.

This evidence is pure host verification. It starts no hosted application,
database, network listener, worker, native runtime or signing process. It does
not establish durable transaction/CAS behavior, tenant authorization, source
resolution, worker authenticity, artifact existence/provenance, operational
recovery, release eligibility, or any GA gate. Physical phones remain deferred.
