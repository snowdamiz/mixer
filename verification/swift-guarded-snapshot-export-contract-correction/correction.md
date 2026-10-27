# Separate guarded snapshot export contract/model correction

This packet corrects R1–R3 in the released producer contract/model. It selects no
working exporter, runtime behavior, product/native/OTA or GA acceptance. The
original 639-member producer, 767-member independent review, 29-member accounting
review and six-member binding review remain byte-for-byte frozen. Input custody
checks every member, exact byte count, declared tree algorithm and released seal
before and after the controls. No frozen wrapper or compiler is rerun.

Root selected this correction in
`guarded-snapshot-export-correction-selection.json` at SHA256
`9365220136da4af59d1403cf694f3c8108c4f601647c3fe7bf1b4385aff37511`.
The two explicitly selected synthetic fixture amendments are SHA256
`327db1241e13af8b0c68b0c795c1dcba2c8692c9da5bd7dc100b013025c11457` and
`76a2a3c91c46f401d04bfd51f830b50374c24b0d8cbbd4f5d91b48ab15eda518`.
Their exact paths/hashes are in both input custody records. Fresh independent
review and root acceptance remain required after this correction is frozen.

## R1: equations, presence and absence

`equality-table.json` contains 29 individually identified equations/relations,
absolute wire offsets, source evidence indexes, absence rules and explicit
non-equations. `source-equation-evidence.json` retains only 19 bounded source
excerpts with exact accepted-file hashes and line ranges. The accepted source
remains 144 members at tree
`9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb`.
No source copy or source edit is introduced here.

| Direct field or source relation | Required equality or rule | Accepted source |
| --- | --- | --- |
| Source extent | Outer, loader provenance, guard, validation input/source usage, Source File identity bytes and source directory count/capacity/charge/payload extent all equal source payload length | `swift.rs:419–460`; loader `1045`, `1129–1141`; guard `241` |
| Validation limits | All five outer/loader words equal; validation usage deadline equals that validation deadline | loader `1131`; `swift.rs:308–320,494` |
| Instructions | Outer, metadata and observation instruction counts equal | `swift.rs:479` |
| Eight buffer lengths | Directory logical counts equal the corresponding observation types/parameters/imports/functions/globals/exports/data/elements | `swift.rs:473–482` |
| Import/body totals | Import count is 34, defined functions equal validated bodies, imported+defined ≤80,000 | guard `199–202` |
| Memory minimum/host maximum | Each metadata word equals its observation word | `swift.rs:486,488` |
| Memory declaration maximum | Both presence and payload equal the observation Option pair | `swift.rs:487`; metadata `69–71` |
| Table minimum | Metadata equals observation | `swift.rs:489` |
| Table declaration maximum | Both presence and payload equal the observation Option pair | `swift.rs:490`; metadata `73–75` |
| Memory/table presence | Both metadata tuples must be present on the accepted Swift path | `swift.rs:470–471,541–562` |
| Resolved host maxima | Some maximum resolves to that value; None resolves to policy cap 768/65,536; minimum ≤host maximum | metadata `228–256` |
| Guard type count | Equals observation types | guard `241` |
| Guard slot limit | Equals min(runtime cache_entries, observation defined_functions), within 1…64 | guard `205–208,242` |
| Guard pin limit | Equals runtime active_pins, within 1…64 | guard `206–208,242` |
| Guard initial nonce | Exactly one | guard `225,242` |
| Guard cache capacity | Equals runtime cache_bytes | guard `243` |
| Guard entry limit | Equals runtime cache_entry_bytes | guard `243` |
| Buffer inventory | Each checked charge equals capacity×native element size; metadata_reserved equals proof 664 plus eight charges | `swift.rs:419–460`; original accepted inventory attribution |

Memory/table tuple presence is separate from declaration-maximum presence.
Actual accepted ABI requires memory Some((584,768)) with declared maximum None,
and table Some((46713,46713)) with declared maximum Some(46713). It later unwraps
both tuples to build observations. Thus clearing every serialized memory or table
word cannot create a conforming absent tuple. There is no observation tuple
presence word to fabricate or equate to the maximum Option flag.

The finite model implements the direct joins, tuple presence and generic parsed
limits relations. It does not reimplement `exact_abi`, validate Wasm, prove the
snapshot was produced by an accepted proof or make the synthetic values actual
accepted ABI values. Some(0) differs from None: Some(0) can be represented only
with a fitting zero minimum/host maximum; None has a zero payload and resolves
the host maximum to the policy cap. Fully consistent synthetic table None and
Some(0) controls test the limits/Option grammar; they do not assert acceptance
by the actual selected ABI. Actual serializers must derive the real fields from
one accepted immutable guard/proof and reject any internal disagreement.

There is no table host-maximum observation duplicate. There is a source-derived
relation between the metadata host maximum and its declaration Option, which is
checked separately. No blanket equality is invented between loader validation
limits and runtime limits/deadlines, between memory host maximum and runtime
memory_pages, or between current/peak/work/elapsed usage fields. Slot limit is a
minimum, not always the configured cache-entry limit. Cache base is the original
fixed layout amount, bounded by cache capacity; it is not that capacity or a new
admission floor. Source-backed fresh layout and work admission remain pending.
WASI None still zeros all 96 optional bytes; Some with zero limits/grants stays
distinct. The writer stays at 4,096 continuous bytes and 32 attempts per block.

## Preserved five failures and explicit positive migration

The independent original F03/F05 failures remain failures in their frozen
packet. These exact unchanged fixtures are now required negative controls:

- `bad-memory-minimum-duplicate.bin`
- `bad-memory-host-duplicate.bin`
- `bad-table-minimum-duplicate.bin`
- `bad-table-max-option-duplicate.bin`
- `bad-runtime-type-count-duplicate.bin`

`controls/exact-five-regressions.json` records original and fresh fixture hashes,
byte-for-byte equality, original acceptance and corrected refusal. Replaying
only the independent `formats()` function produces the same original synthetic
bytes. No fixture expectation was changed and no original failure was erased.

The producer's original synthetic positive contained three additional direct
contradictions. Root explicitly selected these changes in the separate builder:

| Absolute word offset | Original | Corrected derivation |
| --- | --- | --- |
| 792 | Source identity bytes 3 | len(source), 64 in the baseline |
| 1408 | Guard cache capacity 2 | runtime cache_bytes, 16,777,216 |
| 1416 | Guard entry limit 1 | runtime cache_entry_bytes, 8,388,608 |

`controls/migration/` preserves the exact original positive bytes, the migrated
positive and three independent single-word reversions. The original model
accepts the original; the corrected model refuses it. Each single reversion is
also refused. The original builder and original twelve-method test file remain
unchanged in the producer. The copied twelve-method suite changes only the
inventory assertion to five DIGESTS and six RETAINED_VALUES. No method is removed.
The synthetic minima and other arbitrary values remain untrusted grammar data.
No new product budget or positive operational grant is selected.

## R2: actual loader role and bound manifest scope

Actual `MIXLSE01` first section is the exact 64-byte **Source File identity**.
Loader identities are Source/Build/Session/Executable (`931–940`), and section
zero is compared to identities[0].encode() and Source extent (`1045`). The
Executable identity is identities[3]. Proposed `MIXLPR01` preserves the same four
roles and their order. This is a prose/source-fact correction only: actual loader
bytes, `MIXLBD01`/`MIXLSE01`, source, magic, order and behavior are unchanged.

Actual build parsing checks declared member counts 144 and 11 (`398–399`), the
bound complete manifest and other build-section hashes (`975–1001`), executable
and source digests, and local process correlation. It does not open and rehash
155 source/support files at runtime. This lane's offline custody verification
of the 144 accepted source members is a separate evidence check. The eleven
host-support members retain their earlier attribution and are not rerun.
`LoaderProvenanceV1` retains five actual digests (source/manifest/build/session/
executable) and one opaque 32-byte nonce (`1130–1140`). Six retained byte fields
must never be described as six cryptographic digests or signature authority.

## R3: existing shared prepare entry

`cache.rs:1473` already defines `pub(crate) fn prepare<'a>(...)`. The accepted
wrapper calls it at `initial_profile_v1.rs:137`, and line 138 starts the phase
match. The earlier review's line-138 shorthand is preserved in that frozen
review; the corrected roster uses the exact call token at 137. The method is the
existing shared construction admission entry, not a planned accessor or an
alternate admission path. Its body and original call remain unchanged.

## Fresh evidence, attribution and limits

Final `python3 -B verification/swift-guarded-snapshot-export-contract-correction/run_controls.py`
exits zero. Its command, Python version/executable hash, source revision context,
exact tested source hashes, output and cleanup are retained. Results are:

- Twelve copied producer format methods pass, with all methods retained.
- All six independent format groups F01–F06 pass all 26 format subcases. The
  earlier twelve groups/37 subcases also included compiler groups; none of those
  compiler runs is counted as a fresh correction test.
- All five exact original failed fixtures are preserved and refused.
- Fifty-three new duplicate, minimum/maximum, Option, absence, ceiling, guard
  min/pin/capacity, distinct deadline and WASI controls pass.
- Three original positive-word disagreements remain separate required negatives.
- All source-roster facts and 19 bounded excerpts match the exact accepted files.

Two earlier runner failures remain under `attempt-1/` and `attempt-2/`. The first
assumed compact-JSON tree hashing for the accounting peer, which explicitly uses
sorted per-member lines. Honoring that declared algorithm fixed the custody
assertion without relaxing member checks. The second used wrapper line 138 from
the review; the exact token check found line 137. Both failures, runner sources,
commands, completed controls and cleanup are retained. No model or data-test
expectation was weakened to repair these runner mistakes.

The old exact prototype/compiler-case sources and 144 accepted source members
remain unchanged. `controls/inherited-compiler-attribution.json` binds the 28
prior prototype cases (two positive, 26 negative; Debug/optimized) to their
exact old sources and receipts. It also attributes the independent review's two
production builds/nine external negatives. Neither is fresh compilation here.
No compiler, native/device/simulator/emulator, UI/capture, process inventory,
Android stopped work, hosted inspector or other active lane output is used.
All owned Python children are reaped. No compiler products, scratch or bytecode
are created. Only this correction directory is written.

Original 300,000 refusal and 400,000 refusal-only evidence are unchanged. The
separate work/deadline/cancellation and storage design lane remains pending;
this packet neither reads its active outputs nor accepts that design. Exporter
implementation, actual same-owner runtime/WASI reads, fresh layouts/admission,
all-eight behavior, consuming cleanup, File close/name/hash custody, semantic
context/FSM/full workload, canonical integration, FieldLog separate-repository
immutable published packages, physical/native checks, signing/store/customer/
operational and GA gates remain pending. Zero GA gates are verified.
