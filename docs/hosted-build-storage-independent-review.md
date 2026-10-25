# Hosted build storage independent review

Verdict: passed for the internal development storage slice, with no unresolved
actionable finding in the reviewed scope. Root owns acceptance and integration.
This does not pass W12, tenant authorization, operational, native or GA gates.

The reviewer audited exact-scope reads, row locking and revision CAS, creation
conflict behavior, replay against indexed metadata, latest-state duplicate
results, cancellation uncertainty, and real Ecto.Multi/Oban composition. No
production file was edited by the reviewer. The frozen catalog inspector and
authority-driver lane were neither opened nor executed.

## Bound source and execution

The root collector ran the frozen candidate and nine independently authored
controls together in one host suite. The reviewer did not rerun PostgreSQL or
the test suite; the reviewer inspected raw outputs and separately verified the
retained archive, source bindings and command logs. This is independent test
authorship and source/evidence review, with execution owned by root.

The retained collector revision is
`ba9ad4372f94463ba4d363cdfd76dd565c96413f`. Its 83-input working-tree digest is
`42af466e065e67c4f8be4320b86eb198b23f5898f09b3f4026c3aab9e2cc532c`.
The source archive and every archived input match the receipt; ten current
reviewed source/test/fixture bindings also match. The exact checks are executable
without starting Elixir, PostgreSQL, a listener or a native runtime:

```sh
python3 verification/hosted-build-storage-independent-review/verify_evidence.py
```

| Input | SHA-256 |
| --- | --- |
| Storage | `465351cfb4c29150c47b6547a16e4ad7aaa41d14bfb9dc1634d240c55987d0ad` |
| Record | `4394feecd6e04eba55e6aec6d3cde832a14616d0ff10a9682700477ad11930c2` |
| Journal | `3386d7338d189ffc9bdd97ea9669d9c66569ec300e94154b69e14dafd41053ea` |
| Build migration | `9d848ba6c781cd018aca43989313e78320b5e970da7fc4c863a1da644a16d7f2` |
| Independent controls | `a0b9bd8d0f4efc440273d63c183043908edf7efa9eda4849202bcf3407f623cb` |

The full suite reports **208 passed, two skipped**, including all nine review
controls, 15 producer storage tests and 14 journal tests. Formatting,
warnings-as-errors compilation, packaged-release construction and expected
missing-configuration rejection passed. The recorded host tool output identifies
Elixir 1.20.4, Erlang/OTP 29 and PostgreSQL 17.11. The existing toolchain file pins
OTP 29.1.1; the full collector's version command prints only the OTP major.

The two skips are existing Linux-only identity network checks on the Darwin run:

- `MixerHosted.Identity.KeyOwnerLinuxNetworkTest`: K03 production
  resolver/classifier pins the public peer despite rebinding while leaving the
  private sink untouched.
- `MixerHosted.Identity.StartupLinuxNetworkTest`: IS04/IS05 configured startup,
  cold production DNS/TLS admission and lifecycle.

Those skips remain unverified by this run. No storage, journal or review control
was skipped. Root's owned PostgreSQL instance stopped and its scratch directory
was removed, as recorded by the command log and cleanup receipt.

## Controls and corrections

The source review identified a pre-finalization Oban boundary: a valid job
changeset could request uniqueness/replacement, historical state, changed schema
metadata, repository options or an insert preparation callback. Checking args
before insertion alone would not guarantee a new, correctly bound intent. Root
corrected this before the frozen run. Storage now rebuilds a fresh changeset from
a closed field allowlist, rejects the alternate insertion behaviors, and checks
the inserted identity, arguments, queue, initial state, attempt and conflict flag
inside the transaction. Producer hostile-factory controls passed against that
correction. This source finding was not presented as an independently executed
pre-correction exploit.

The nine independent controls additionally establish, within the fixture:

| Control | Observed result |
| --- | --- |
| Concurrent different builds using one request key | One accepted record/job; the other request conflicts. |
| Concurrent different request keys for one build | One immutable winner; the other request receives a build conflict. |
| Concurrent different payloads under one event ID | One applied transition; the other receives an event conflict. |
| Concurrent exact event delivery | One revision/job; redelivery returns current state and never runs its factory. |
| Fresh scheduled job and duplicate creation | The explicit schedule/retry/priority persist; redelivery cannot reschedule it. |
| Factory exception and surrounding Multi failures | Existing journal, revision and prior jobs remain unchanged; earlier job inserts roll back. |
| Every indexed scope field and request key mismatch | Read and mutation reject disagreement with replayed creation. |
| Invalid journal with matching event count | Repeated/reordered events and backwards observation time fail closed. |
| Historical duplicate after retry and success | Returns the latest successful second attempt without another revision/job or reopening old work. |

The underlying Oban Multi implementation substitutes the actual transaction Repo
for insertion, preserving ordinary same-transaction composition. Job factories
remain trusted BEAM application code: they must construct changesets without
external effects. Normalization is not a sandbox against a compromised caller.

## Scope and pending work

The fixture uses real `mixer_builds` rows, real PostgreSQL locks/CAS and real Oban
rows. The collector's inherited statement about a synthetic domain table refers
to its separate foundation probe; it does not describe the build table added by
this slice. The build consumer remains test-only, and no production dispatcher or
public build route is supplied.

The database uses synthetic migration-owner fixture access on loopback without
TLS. These tests do not qualify runtime role restrictions, authoritative current
identity/membership policy, transaction-bound authorization or FORCE RLS. They
also do not provide authenticated worker observations, a coordinator lease,
fleet-wide quotas, source/toolchain resolution, hostile worker isolation, artifact
content/provenance verification, signing, publication, stores or usage billing.
Neon/Cloudflare lifecycle, wake, failover, restore and external-effect recovery
remain pending. No physical device, simulator or emulator was used, and no
customer, release or GA authorization follows from this review.

The [review result](../verification/hosted-build-storage-independent-review/review.json)
binds the checks and limitations. The [root collector receipt](../verification/hosted-build-storage/attempt-1/receipt.json)
retains exact commands, log hashes, source archive and cleanup evidence.
