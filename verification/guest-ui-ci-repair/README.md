The repair changes only the C test consumer's loop braces/statement layout and
the two Swift test fixture builders' array assembly expressions. Byte order,
operands, exports, modes, and document contents are preserved.

`before/` contains exact `git show HEAD:<path>` snapshots taken before edits at
revision `5a0367d6c56bb288ddd45dccc44ddfe20f533781`. `before-source.json` records
that revision, Git tree, file paths, and SHA-256 values. These are this project's
independently authored fixtures; no external fixture or implementation was used.

Run from the repository root:

```sh
python3 verification/guest-ui-ci-repair/verify.py before
python3 verification/guest-ui-ci-repair/verify.py after
python3 verification/guest-ui-ci-repair/verify-tests.py
```

The first two commands compile and execute both Swift builders and the C builder
before and after the repair. All 167 complete byte arrays match. The domain is
all 12 runtime modes at initial revisions 0, 1, 2, 63, 64, 127, 128, 16383, 16384,
UInt32.max, UInt32.max + 1, Int64.max, and UInt64.max - 1; UInt64.max is additionally
tested for the two modes that do not increment it. Both default calls, all five
signed modes, and both C variants are included. This covers every revision value
used by the current tests, with additional boundaries, and is not an exhaustive
enumeration of UInt64. The original incrementing modes overflow at UInt64.max,
so the comparison intentionally does not invoke those overflowing test inputs.

The native archive is reused without rebuilding and checked against SHA-256
`4d3b6dc36ea034d5604299752d560cbbc0615002b6b5ef4e5c25bbb3cb7c6120`.
The edited C smoke test compiles with `-Wall -Wextra -Wmisleading-indentation
-Werror` and passes 42 checks. The existing runtime scratch graph recompiles the
edited fixture and passes 13 guest UI tests. The current activation test sources,
including the edited signed fixture, are relinked against the unchanged debug
candidate-4 library into this directory's ignored `.build/` and pass 113 tests.
The activation receipt records the reused library hash and every relinked source
hash. Original candidate-4 products and source snapshots are not overwritten.

Local tools are Apple Swift 6.4 and Apple clang 21. This is local host evidence;
the exact pinned Xcode 26.3 / Swift 6.2.4 and Ubuntu GCC CI checks remain pending.
No physical-device run was attempted. No release, GA, dogfood-package,
publication, signing, or store gate is asserted by this fixture-only receipt.

`receipt.json` indexes the source digest, command receipts, observed counts, and
pending checks. `before.json`, `after.json`, and `tests.json` contain exact
commands, output-log paths and hashes, source hashes, and execution scope.
Ignored `.build/` retains the local executables and raw compared Wasm outputs;
the checked-in source snapshots, runners, logs, and manifests reproduce them.
