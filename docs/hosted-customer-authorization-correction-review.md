# Customer authorization correction review

**Accepted as a finite pure authorization prerequisite.** No unresolved finding
remains in the reviewed correction. This does not accept durable/current customer
authorization, a protected transaction, customer HTTP/console behavior or a GA
gate. The historical review remains unchanged as evidence of its original P2.

The selected correction is
[`verification/hosted-customer-authorization-correction/seal.json`](../verification/hosted-customer-authorization-correction/seal.json),
SHA-256 `f4e57c20a9bde0a9d3066fb93594a7038d05e54dc8a22b106d369d7aee2cef4e`.
All 28 recorded files matched. Source revision context
`b375e55ded9e3e10c327891ab681beff2a471e26` was supplied by root; no Git ran.
The executed inputs, byte hashes, commands and outputs are retained under
[`verification/hosted-customer-authorization-correction-review/`](../verification/hosted-customer-authorization-correction-review/).

## Finding closure

**AUTHZ-REVIEW-001 / P2 is closed.** `Repository.evaluate/5` now creates a fresh
request-local reference captured by its callback. A successful result must carry
that exact envelope and pass `Policy.valid_decision?/5`. The original incomplete
Decision and a complete unwrapped Decision returned without the callback both
reject. Missing, invented and reused references reject, including an otherwise
valid success envelope retained from an earlier identical request.

The projection check requires the exact closed Decision structure, current
request action/target, credential/profile/version and evaluation time. Principal
and membership identifiers, nonempty sorted unique bounded membership/role lists,
action-compatible roles, role/membership cardinality and all four revisions must
meet the existing bounds. Missing keys, nil values, foreign keys, wrong request
bindings and malformed/oversized/improper lists reject. The ordinary policy,
role ceilings, token-scope intersection, identity binding, lineage and time
semantics are unchanged; `Scope` is byte-identical to the reviewed producer.

This contains accidental trusted-adapter failures. A trusted adapter remains
responsible for returning the callback envelope unchanged inside its real
protected transaction. The reference is not a malicious-BEAM sandbox, an
immutable cryptographic proof, a reusable capability or evidence of database
freshness. No process dictionary or global mutable state was added to product
code. Test fixtures use isolated test-process state only.

## Executed evidence

Latest independent `run-2` compiled the actual modules with warnings as errors
and passed **30/30 producer tests and 23/23 independent tests**, with zero stderr.
Environment: Darwin arm64, Elixir 1.20.4, Erlang/OTP 29.1.1, ERTS 17.1,
`ERL_FLAGS='+S 2:2'`. All executed input bytes still matched live files at run end.

The prior 16 independent probes were retained, including the original failing
regression, and now pass. Seven additional tests exercise complete unwrapped
success, callback envelope shape/reference/reuse, every required Decision field,
request binding and bounds, unchanged bounded failures and exceptions, all
six-role/action outcomes through the corrected facade, and valid multi-role and
64-membership projections. The deliberate stale-snapshot control still permits
old enabled evidence through a fresh callback: durable lookup/locking remains
necessary. `run-1` also passed all tests but emitted a warning from an unused
default in the review helper; only that owned helper was changed for clean
`run-2`. No product source changed between the two review runs.

The original producer seal remains
`9f8c9019b00fb0e3190362b3ed142ebe0bcc64bed59593b76c61860da803b97b`; the
original review seal remains
`5095744f44f7155ae2d4210dd6e50a0fc1bae73a8a09fbbafc8b75fe30982a7b`,
and all 92 historical review entries still match. No historical review or
producer snapshot was edited.

Both new owned scratch roots were removed. No database, migration, server,
provider, network, UI, native/device or frozen-lane execution occurred. Current
authoritative state, revocation locks, membership-aware RLS, full immutable audit
construction, idempotency/domain/Oban composition, additional customer restriction
policy, provider/service/CI qualification and accountable GA review remain pending.
