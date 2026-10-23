# Independent experimental streaming-validator review

Reviewed commit: `4ca99c581a0cdbf4a69e15623ae676ca73403262`, repository tree
`5644af5361d13828c74b19cb0dc1f9b7a13c0fc9`. The implementer's scoped VM source
manifest was independently reproduced as
`11e74f195e051317d8097953d8dd9193e29d3a0d66011fe00f29a36f34d5b8fe`.
Reviewer selection: `gpt-6.1-sol`, `xhigh`.

No actionable implementation defect was found in this bounded source review and
host experiment. No VM production source, implementation test, API, profile,
header, or root status file was edited. The review concerns the nondefault
Rust-only `experimental-stream-validation` feature. It supplies a validation-only
owned span representation; it supplies no C entry point, executable conversion,
activation path, larger profile ceiling, or admission of the full FieldLog input.

The final evidence is [2026-10-22-final/receipt.json](2026-10-22-final/receipt.json).
It records the full revision/tree, every committed VM/contract file hash, command
arguments, tool versions, outputs and their hashes, independent probe hashes,
observations, and remaining gates. Temporary absolute paths in the receipts are
the actual observed paths, not portable package dependencies.

## Reproduction and source isolation

From the Mixer repository, run:

```sh
python3 -B verification/stream-validator-review/run.py --name FRESH_NAME
```

The runner makes a private temporary shared-object Git clone, checks out the
immutable commit, verifies every original committed VM and relevant contract file
against that commit, and runs `vm/verify-stream-validation.py` in that export. It
then copies only the two original review probes into that export's `vm/tests/`.
It uses a separate Cargo target directory, executes the review probes in debug
and release, checks their formatting and Clippy, and rechecks original file
hashes. It neither changes nor tests the active working-tree implementation.
Cargo/Rust must be installed at the recorded rustup location or available on PATH;
Node and the macOS Clang/nm tools are required for this host receipt.

The observed run first cloned with `git clone --shared --no-checkout --quiet`,
then `git checkout --quiet --detach 4ca99c581a0cdbf4a69e15623ae676ca73403262`.
It executed `python3 -B vm/verify-stream-validation.py --name independent-baseline`.
The final review runner used `--reuse-export` to reuse that independently
completed baseline; it reverified the immutable files and baseline digest before
using the outputs. Its replay command and full path are in the final receipt.
The nested baseline receipt's `independent_review: false` is a constant emitted
by the implementer's runner, not a claim that its independently reproduced
commands were omitted. This directory's outer receipt records reviewer ownership.

`2026-10-22-host/` preserves the initial passing review run before the extra growth
overlap assertion was added. Its `probes/` directory retains the exact then-used
probe and runner bytes. The final run supersedes it and includes the explicit
overlap observation. There was no production failure or implementation fix
between these runs.

## Observed executable evidence

The independently reproduced baseline passed 87 default checks, 104 feature
checks in debug and release, and all nine explicitly invoked development oracle
functions in each build mode. The normal feature run reports nine ignored oracle
functions; the separate `--ignored` runs execute them. Both Rust compile-fail
ownership examples passed. Format and default/feature Clippy passed. Four C smoke
fixtures passed against each of the default and experimental builds, and the
public `mixer_vm_*` C symbol sets matched. The original production Rust files and
profile/session/header contracts matched frozen production
`64123c509e861ddd522631b293eadebdaca11341`, allowing only the new feature-gated
Rust module declaration in `lib.rs`.

The original review probes add eight test functions per build, with zero failed,
ignored, or skipped tests. Their Node comparisons are generated original
fixtures, executed without invoking guest code:

| Probe | Comparisons per build | Accepted / rejected |
| --- | ---: | ---: |
| Integer sequences through reachable, unreachable, and nested frames | 14,280 | 1,902 / 12,378 |
| Typed branch tables, loops, and if-arm joins | 680 | 34 / 646 |
| Memory, globals, indirect-call and bulk-operation context | 435 | 111 / 324 |
| Uncalled malformed/unsupported bodies | 7 | 0 / 7 |
| Padded/overflowing LEB and UTF-8 export names | 10 | 7 / 3 |
| Total | 15,412 | 2,054 / 13,358 |

All comparisons matched Node `WebAssembly.validate` and the frozen validator
within the deliberately generated supported subset. The integer sequence corpus
also matched the frozen decoder under all three selected profiles. Node is a
development reference, not a production dependency or a complete standards
suite. Profile-specific restrictions are not inferred from Node accepting a
broader standard feature.

Other independent assertions check rejection of every work allowance from 0
through 516 on a fixture needing 517 credits, exact/one-less metadata and scratch
boundaries, absolute body error positions with the correct uncalled function
index, caller-buffer destruction/mutation independence, stable span contents and
bounds after moving the owner, and out-of-range span lookups. The data-segment
fixture intentionally has destination `u32::MAX`; validation accepts that
declaration and does not promise that instantiation would succeed.

The single-thread allocation executable independently forced all 38 dynamic
allocation ordinals of a mixed metadata/scratch fixture to fail and cancelled at
each of those 38 allocation gates. Every call returned the expected static
failure/cancellation kind without a proof, retained no validator heap buffers,
used no realloc, and made one source-sized allocation on the successful path.
Its measured requested heap peak was 35,736 bytes versus 37,000 total reserved
bytes, identically in debug and release. This measures requested allocation
sizes, not allocator usable size, stack frames, RSS, or deployment memory.

A separate flat-signature growth probe retained 18,452 metadata bytes but reserved
a 26,644-byte metadata peak including old/new buffer overlap. Narrowing the
budget to the retained size correctly rejected the 26,644-byte attempted peak
before the last allocation: 13 allocation calls occurred versus 14 in the
successful run. Drop restored the allocator baseline in both paths. The baseline
runner additionally reproduced the implementer's eight larger allocation
fixtures, including its observed 5,251,097-byte requested heap peak and
5,252,361-byte reservation for the signature-heavy fixture.

## Source-review conclusions and limits

The reviewed parser validates section order/counts, cross references, allowed
imports, UTF-8/duplicate exports, initializer forms, and every declared function
body before publication. The streaming checker continues decoding/type checking
unreachable instructions and uncalled functions. It retains flat signature types
and current-body stacks; it does not retain instruction/branch-target arrays.
Private spans are constructed from checked source-bounded ranges. The successful
proof owns a private exact-length `Box<[u8]>`, exposes shared borrowed slices, and
cannot be constructed through deserialization or an executable conversion.

The meter checks before variable traversals and before growth, charges old and
new requested buffer capacities concurrently, and uses fallible exact-capacity
allocation. Final success checks cancellation again. The source copy and native
allocation calls remain bounded nonpreemptible operations; cancellation is
cooperative, with no hard wall-time guarantee. Error usage is a point-in-time
reservation snapshot, while the drop tests separately check actual cleanup.
Fixed metadata/scratch reservations are the documented accounting model, not a
measurement of compiler stack layout or all process memory.

The reproduced frozen-valid repeated 4,096-parameter-call fixture intentionally
exhausts the extra 64-million validation-work budget at attempted credit
64,000,001 and produces no proof. This is the explicitly allowed additional
resource rejection, not a semantic parity failure or an executable-profile
change. The unchanged source ceiling remains 4 MiB, metadata 4 MiB, scratch
64 KiB, with narrower caller budgets only.

The source analysis used the official WebAssembly
[validation algorithm](https://webassembly.github.io/spec/core/appendix/algorithm.html)
and [instruction typing rules](https://webassembly.github.io/spec/core/valid/instructions.html)
for supported numeric/control forms. No external engine implementation, fixture,
or library was copied. The current standard contains additional types/features;
this experiment continues rejecting unsupported forms.

This review is targeted host evidence, not exhaustive semantic equivalence or a
security audit. Full standards coverage, coverage-guided fuzzing, an external
audit, a cache/executable integration design, full Swift/FieldLog admission,
physical experimental validation, and OTA/GA acceptance remain open. Phones were
disconnected and no physical-device command was attempted. Existing production
qualification does not qualify this experimental API on devices.
