The isolated V3 candidate repairs only the SL13 test body selected by root. It
asserts the source-derived Cache ticket deltas `+1,+2,+0` and live decoded-entry
sequence `0,1,3,3`. The former second-call versus initialized ticket assertion
is removed. All other SL13 work, hit, miss, decode, eviction, resident-byte,
active-pin, instruction, execution-work, host-call, warm-ticket, deadline and
consuming-retirement checks remain. No engine, helper, hook, import, other test,
dependency, accounting limit or Frozen source changed.

Candidate source closure:
`93adb6ac2d00acab30c02df8d96e044452edc14d704a6738a58874b0968b5f38`.
The predecessor is the immutable V2 closure
`0fa7ae254ac2b3aa3390e6fbc935e920422fc9024db220256074ec6ef4e3cd56`,
sealed by `36d70c601ce2930ef18ca7adb58dcb96b4e3e3e15d816406c0b7df092e81d749`.
All 332 predecessor sealed files were checked before copying and are checked by
the read-only replay. V2's actual 22-pass/one-failure Swift Debug run remains
historical evidence; V3 has executed no test binary.

Four fresh pinned compiler-only unit queries passed: Swift Debug/Release and
all-feature Debug/Release. A fresh official compiler expansion preserved all
39 Frozen methods byte-for-byte. The compiler executable and every qualified
sysroot `bin/` and `lib/` file matched the predecessor before every command and
after cleanup. The exact retained metadata-only driver was restored into owned
scratch; no shared tool installation was modified. Full command lines, versions,
source archives/manifests, stdout/stderr, compiler executable/MIR artifacts and
raw metadata streams are retained in the packet's five `attempts/` folders.

The proof directly preserves ordered raw occurrences and multiplicities. It
compares all 160 selected complete executable MIR bodies, including allocation
payload bytes, alignment, offsets, relocations and full reference graphs; all
2,744 raw positions including 498 constant occurrences; all 11,760 full raw
four-role joins; and all 1,296 zero-byte function-item role joins. The 116 whole
carrier declarations, 2,330 actual type/layout graph records, 176 retained source
carrier witnesses and 256 precisely partitioned compiler array annotations are
also bound. Every raw position has both full records, its original query digest,
raw stream index, per-body ordinal and per-location occurrence index. The former
V2 dictionary omission cannot coalesce any of these occurrences.

Fourteen full MIR bodies differ only through the enumerated injective allocation
identifier maps. The full raw body/allocation bytes remain in evidence. There
are 134 numeric hygiene changes in local source information; exact source file
coordinates and scopes remain equal. Every other actual instruction, constant
value, stable type identity and full layout matches. The finite metadata rules
and annotation partition are exact predecessor code; no broader normalization
was introduced. Full macro expansion chains were not queried or claimed. Root
selection of these exact new finite maps remains pending; no numeric accounting
credit or runtime acceptance is claimed.

All five compiler targets and the metadata scratch were removed after empty
holder and process-group checks. Cleanup receipts retain the actual paths,
counts and logical bytes. No other project's native instance or process was
used or removed. No physical phone, native runtime, live VM, real 53 MB reactor,
Git, network, publication, customer or shared-tracker operation occurred.

The original authored coverage ledger and complete planned gaps are preserved
without edits in `authored-coverage.json`, `planned-matrix-unchanged.json` and the
receipt. No complete SL row is accepted. The 23-test four-context matrix and
broader Frozen/full-library/default/span regressions remain pending, as do all
remaining failure/checkpoint/budget/WASI variants, SL12 guest table mutation,
real full-reactor execution, physical phones, immutable separate-repository
FieldLog release and all D3/G07/G08/store/customer/operational/GA acceptance.

The prepared runner retains the predecessor's conditional 30-command plan,
explicit compiler/Node PATH and exact compiler/sysroot/Node/system pins. Before
the Node oracle it additionally checks the previously qualified Apple loader,
physical loaded files and complete dyld-cache file set. That oracle and these
live Node checks have not run for V3. Failure stops the matrix and retains all
outcomes with owned-target cleanup. The runner requires an explicit root
selection binding the candidate and this packet's pre-runtime freeze hash; it has not been
invoked to execute any tests.

Read-only replay, which regenerates the full proof from retained raw streams
and executes no compiler, test binary, subprocess or write:

```sh
python3 -B verification/swift-reactor-lifecycle-runtime-v3/verify_pre_runtime.py
```

After root selection, the prepared execution command is:

```sh
python3 -B verification/swift-reactor-lifecycle-runtime-v3/run_runtime.py \
  --representation-selection /absolute/path/to/root-selection.json \
  --selection-sha256 ROOT_SELECTION_SHA256
```

The selection schema is `mixer.swift-lifecycle-test-repair-runtime-selection.1`,
with the exact `candidateClosure`, `finiteRepresentationAccepted: true`,
`additionalAccountingCredit: 0`, `preRuntimeFreezeSHA256`, `preRuntimeSealSHA256` and three `selectedNext`
items covering the focused matrix, conditional broader regressions, and
failure retention/cleanup. `seal.json` binds every prepared packet file; the
receipt binds this document.
