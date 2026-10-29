# Isolated Android axis host JSON binding correction

This source-only sibling corrects the shared JSON comparison that refused the
root-selected host on run 40909865814, attempt 1, job 123574592818 at source
2cea1013151ccc38bb635fb4755793cd25a0bd1b. The retained failure is in
verification/android-axis-refusal-expression-host-failure-2026-10-29/local/.
Root reports that Host/tool selection failed before Swift and that there are no
artifacts. The manual allowance is consumed without replay. This packet grants
no selection, dispatch or additional allowance.

The frozen predecessor is verification/android-axis-refusal-host-admission-expression-correction. Its verifier is 18083 bytes, SHA256
cb62acbbe45fc98d205e3b7b8dfa0d6cc83975c5e9ca3a0e5227e05d57a1dbad;
its workflow is 6670 bytes, SHA256
8483fbf0b110ab9f1806004f51b857d47eebb46acb9521ee1ee91bbfb5a86dc5.
The predecessor and currently installed workflow remain untouched by this lane.

The failure used an exact 1624-byte compact, recursively sorted producer string,
SHA256 3af103fcba99e9fd728f40c7642acbd5c9418f73e156ad62a7ce968c18d98874.
Its retained 1802-byte pretty form has SHA256
42c593d7fdecbaf7c471acfee1fac16b32c348ecfeffd20ebb1ac673d1cfa620.
Both host and budget contain the selected values with different object key
insertion order from the verifier literals. JSON.stringify equality treated that
serialization difference as a binding failure. Roster objects can have the same
problem; fixing only two literal orders would leave the shared defect.

The replacement validates both complete operands as JSON data, then recursively
compares exact object key sets without regard to order. Arrays retain their
length and positions; scalars retain their type and exact value. Object.is makes
negative zero distinct from positive zero; this is explicit fail-closed
strictness and does not alter any positive selected limit. Plain objects with a
null prototype are accepted as JSON values, as are repeated noncyclic references.
Undefined, functions, symbols, bigint, nonfinite numbers, sparse arrays, extra
array members, hidden or symbol keys, accessors, exotic prototypes and cycles
are refused. Accessors are inspected as descriptors without invoking getters.
This is the JSON data domain, not an arbitrary JavaScript proxy sandbox.

The separate rootSelectionSHA256 continues to hash JSON.stringify(selection)
exactly as before. Thus semantic object comparison is order-independent while
the recorded serialized-input identity still changes with insertion order. The
existing explicit String normalization of run ID and attempt remains unchanged.
Top-level selection remains field-validated: unknown-key refusal is claimed for
whole objects compared by equal(), including host, budget and snapshots. This
change adds no new top-level schema policy.

The workflow changes only its admission sibling paths. The verifier changes
only PIN.admissionRelative and the reviewed comparator block. The expression
placement correction, exact tool/source/hash/result contracts, 27-file package,
required nineteen methods, budgets, command, attempt ceiling and dispatch ceiling
remain unchanged. The false template binds the new workflow hash and updates its
authority prose to state that no consumed allowance is renewed. selected and
dispatch_authorized remain false; source_revision and run_id remain null.

controls.mjs retains the original forty-seven cases byte for byte.
expression-controls.mjs retains the original eighteen expression cases byte for
byte as historical source. expression-binding-controls.mjs carries those same
eighteen cases for this sibling and extends the exact allowed verifier delta to
the reviewed comparator block. binding-controls.mjs prepares 124 pure source/data
cases, including the actual producer serialization through JSON.parse and
verifyBinding, recursive object permutations, strict array/roster order, every
host/budget changed/missing/typed value, extra keys and non-JSON rejection.
All controls are inert and UNRUN in this preparation lane. Root must review and
execute them under its denial guards before any new delivery. The inert composed
preflight fixture additionally traverses the final workflow, frozen27/source pins,
producer binding, roster and four owned in-memory receipt writes before any new
host selection. See DATA-HARNESS.md.

Only guarded Node fs/crypto data reads, exact source-text transformations and
writes inside this new packet were used. No target module, subject, oracle,
regression script, CLI, child process, compiler, runtime, network, held-process
probe, signal, timer, UI, capture or native operation was invoked. The source-only
fs/hash comparisons in source-checks.json are not test or host evidence.

The immutable package remains 27 files and 284605 bytes, manifest
601b9722df4f42c6649f0e0b6943fe5e3ad96bc6ebeeeecc186da475875e5782,
projection 257ed4dfa93d43b15d4bfe2d51372d261e4fec5fd9e80c3f1ca62b1967a3a793.
SDK22/adapter23 source pair.5 remains canonical; its separate .6 proposal is
unapplied and outside this lane. Swift compilation/discovery, eight XCTest and
eleven Swift Testing results remain pending. Native/UI/capture, phones, held
process/custody, immutable external FieldLog, OTA, production/store/customer and
GA restrictions remain. This packet makes no cleanup or process-custody claim.

admission-manifest.json lists the payload closure, excluding itself and
receipt.json to avoid circular hashing. The receipt binds its final hash.
