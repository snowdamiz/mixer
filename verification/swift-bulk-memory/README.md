# Private Swift bulk-memory candidate

Read `docs/swift-bulk-memory-contract.md` and
`docs/swift-bulk-memory-implementation.md` in the repository. `receipt.json`
records the exact scope and pending review/integration boundary. `candidate.patch`
is review material; no live source is changed by this lane.

Run the independent read-only replay from the repository root:

```text
python3 -B verification/swift-bulk-memory/verify.py --live-baseline
```

The baseline/candidate archives contain the canonical Cargo/src/tests/include
closure without build outputs. `sources/` also retains every exact final,
instrumented and failed command source closure. The command index binds argv,
cwd, tool environment, source manifests, raw compressed outputs and recorded
executable hashes. Historical cwd/target paths were owned disposable scratch and
are deliberately removed; collector scripts document collection, not a request
to recreate those historical paths or to modify the live checkout.

The sealed four runtime configurations execute 78 selections each, including all
BM01–BM16 names exactly once. `matrix-results.json`, final compiler MIR,
`canonical-audit.json`, positive inventory, measured layouts, exact Frozen
expansion and actual Frozen runtime pairs are separate evidence classes.
Accepted memory fields and types are retained; the explicit compiler-label
qualification delta is in `accepted-canonical-qualification-delta.json`.

`historical-*` and failed command receipts retain excluded drafts. All archived
source closures are validated against their original manifests; six early
closures were reconstructed byte-for-byte from retained versions. The cleanup
receipt records an empty targeted lsof result immediately before removing only
this lane's uniquely named scratch. No native/phone/UI runs, publication,
messages, credentials, commits or pushes are part of this packet.
