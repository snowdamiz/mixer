# Independent guarded snapshot export contract review

Disposition: contract corrections required before implementation selection. Root
is final selector. This review accepts neither an exporter nor runtime behavior.
The immutable producer remains unchanged.

The independent requirements were frozen before candidate access:
`preaccess-freeze.json` SHA256
`716d8c93a5f5dd3ee7e0b5caafb1848e1c4697e2e21a03a77f5ded6ddab4a893`.
After root explicitly released the producer, this lane verified its closed
639-member /22,970,241-byte packet and copied it under `candidate/`. The released
seal is `7787c8bbd9164ebdd360186f79c5d696739e89d6b08cd2f7cfbc71e9c156a1fe`;
the candidate tree is
`659a65c7ed097bf2825b9f54509825ac4a966215376cb1fc291fb89644304bd9`.
The 144 accepted source members remain tree
`9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb`.
Frozen preaccess requirement 7 used "six 32-byte digests" as inventory shorthand.
The actual six retained values are five digests plus the 32-byte nonce; the nonce
is copied as bytes and grants no digest/signature authority. The frozen preaccess
file is preserved, and the field coverage requirement is unchanged.

## R1: Specify and enforce the duplicated immutable-field joins

Priority P1 for the contract/model correction. The proposed format carries the
same immutable values in multiple places, but the data decoder admits direct
contradictions. The contract's `candidate/contract.md:164` requires derivation
from one immutable view and rejection of internal disagreement. In
`candidate/format_model.py:122`, metadata memory/table words receive local checks
without comparison to their observation counterparts. At line 132 the runtime
record is parsed but only its source extent is joined to the outer record.

The independently built 4,168-byte synthetic positive fixture is accepted. Each
of these single logical mutations remains accepted by the candidate decoder and
is rejected by the independent envelope's corresponding equality check:

| Retained fixture | Mutation | Required equality |
|---|---|---|
| `controls/fixtures/bad-memory-minimum-duplicate.bin` | metadata memory minimum 1 ->2 | metadata memory minimum = observation memory minimum |
| `controls/fixtures/bad-memory-host-duplicate.bin` | metadata host maximum 768 ->767 | metadata memory host maximum = observation memory host maximum |
| `controls/fixtures/bad-table-minimum-duplicate.bin` | metadata table minimum 1 ->2 | metadata table minimum = observation table minimum |
| `controls/fixtures/bad-table-max-option-duplicate.bin` | metadata declared maximum Some(65536) ->None | metadata declaration maximum presence/value = observation maximum presence/value |
| `controls/fixtures/bad-runtime-type-count-duplicate.bin` | runtime guard type count 1 ->2 | original guard type_count = snapshot observation types |

Freeze an explicit source-backed equality table for all direct duplicates,
including the memory declaration pair and original guard scalars that repeat
control budget fields. Apply those equations in the model and future serializer,
and retain these five negatives. The five failures remain genuine failures in
this packet; this review does not silently update the model or turn the expected
outcomes into passes.

These are data-contract/model defects. Synthetic decoding still grants no proof,
Wasm validation, provenance, replay or OTA authority. This review makes no claim
that a working exporter is vulnerable: no working exporter exists in the packet.

## R2: Correct the actual MIXLSE01 first-section role

Priority P2 for the contract correction. `candidate/contract.md:44` calls the
first 64-byte session section an executable identity. In the accepted source,
`retained_profile_loader_v1.rs:932` places Source in `identities[0]`, and line
1045 compares `s.sections[0].bytes` with `identities[0].encode()` and its source
extent. Executable is `identities[3]`. Change the description to Source identity;
do not alter actual loader bytes, reorder retained provenance identities, or
rename `MIXLBD01`/`MIXLSE01`. The proposed MIXLPR01 identity order is already
Source/Build/Session/Executable.

## R3: Mark the original cache prepare entry as existing

Priority P2 for source-roster correction. `candidate/source-roster.json` marks
the `pub(crate) fn prepare(` fact as `line:null` and "planned accessor absent in
actual source". The accepted `cache.rs:1473` already defines
`pub(crate) fn prepare<'a>(...)`; `initial_profile_v1.rs:138` already invokes it.
Use its actual generic signature/token and source line, and mark the original
shared construction entry as existing. The source-role statement is relevant to
admission sequencing; the candidate's syntax search must not turn the existing
owner/admission entry into a planned alternate. This is a source-roster defect;
no cache implementation change is needed.

## Required implementation-selection decisions, separately pending

The concrete pre-guard work formula and read-only deadline/cancellation contract
remain expressly unresolved at `candidate/contract.md:255`. Root must select
the source-backed allowance, failure observation and original-control interaction
before implementing them. The same applies to the full outer result/storage
roster, actual same-owner runtime/WASI reads, fresh unit/production layouts,
simultaneous admission and consuming cleanup. These are honestly declared
prerequisites, not failed implementation evidence or a reason to run phones.

The 366,896-unit /366,312-production accepted foundation and original 300,000
refusal remain unchanged. The historical 400,000 fixture stays refusal-path-only.
A positive exporter host grant must be separately named and selected after fresh
measurement of the actual implementation. 4,096-byte continuous transfers and
32 attempts per transfer remain unchanged.

## Fresh finite controls

`review_controls.py` ran twelve groups with 37 subcases. Ten groups passed;
F03 and F05 failed in the five mutations above. There were no other failed
subcases. F01 independently recomputed the 69,765,152-byte cap and deterministic
envelope. F02/F04/F06 exercised exact tags/options/reserved bytes, truncated or
extra extents, gaps/identities, ceiling and overflow refusal.

P01 performed two actual ordinary-production accepted-source metadata builds,
Debug and optimized, with no test/host authority configuration. P02-P06 performed
nine external negative compiler controls against that exact accepted source:
private proof fields, non-Clone/source immutability, private guard construction
path, lifetime/use-after-move, and private selected/runtime paths. Every negative
had the intended diagnostic code and no unrelated error code. These controls
prove baseline external privacy, not the future crate-private guard bridge or
writer. The producer's prototype and 28 compiler cases were reviewed as immutable
preparation evidence and were not rerun or claimed as fresh independent runs.

The command was `python3 -B verification/swift-guarded-snapshot-export-contract-independent/review_controls.py`.
It exited 1 because F03/F05 correctly exposed unresolved refusal expectations.
Python is 3.14.8; rustc is 1.99.0 (`b940084d7`, aarch64-apple-darwin). Exact command
arguments, outputs, error codes, durations, source manifest and fixture hashes
are retained under `controls/`; `controls-result.json` records the runner hash.
The accepted source revision context is `606c42876855897c315ee279dcd38fabaeb561ad`;
the verified source tree, rather than a changing checkout HEAD, identifies the
compiled bytes.

No producer wrapper, adoption suite, broad harness, native/device/simulator,
emulator, UI, capture, process inventory, hosted inspector, stopped Android or
rejected-worker material was used. All owned compiler children were reaped and
compiler products/scratch were removed. No canonical files, metadata, Git or
product source were changed by this lane. Native checks remain paused. Loader
operational storage/IO, File-close/name/hash custody, semantic context/FSM/full
workload, FieldLog published-package, signed-package/store/customer/operational
and GA acceptance remain pending. Zero GA gates are verified by this review.

## Separately frozen peer reviews

After explicit release, this lane verified and copied the binding review's six
members/29,641 bytes at seal
`7d3faabd2f930d2daac9865f27dbbb3bc9a661097e6a7834584a93d0527b1cf0`.
Its nine bounded source/data groups support R2 and confirm the retained field and
34-import mapping inventory; they are not added to the twelve fresh main groups.

The separately released accounting review's 29 members/556,384 bytes are verified
at seal `c638a996d2fa1f54c62f739758c5219f23439541b249e480b0084d1038112068`.
Its eight source/data arithmetic groups support the cap/inventory/accounting
scope and R3; it claims no new layout or admission. The review confirms that work
and `check` mutate the original control, while a bounded read-only stop contract
is still pending. Each peer retains its own command/source attribution and scope
under `peer-inputs/`; neither producer nor peer wrapper was rerun.
