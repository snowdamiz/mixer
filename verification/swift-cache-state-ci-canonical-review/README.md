# Canonical closed fixture relocation review

Accepted for exact relocation and workflow integration within this review's
scope. No product engine code, runner, focused controls, pack expectation,
workflow, Git state, or root metadata was changed by this lane. The only writes
outside this review directory were root-coordinated creation of canonical
ignored `logs/` and the two exact deadline-control JSON outputs required by the
unmodified focused suite. Their byte-exact copies and hashes are retained here.

`inspection.json` verifies all 90 root-selected canonical members by size and
SHA-256, including the exact two-rule `.gitignore`. All 89 runner/test/pack files
also compare byte for byte against the selected corrected source packet. The
closed pack independently matches all 86 manifest members, its 87 physical
files including the manifest, total bytes, and complete tree digest. The
relocated runner's own read-only pack verifier agrees. Its `HERE`, `ROOT`,
`PACK`, and `RUNS` resolve to the canonical directory, original repository root,
canonical pack, and fixed canonical runs directory respectively; fixed limits
remain 600 active / 60 cleanup / 60 child seconds.

Canonical `.github/workflows/verify.yml` is byte-identical to the reviewed full
proposal, with the complete original workflow as its exact byte prefix. Ruby/
Psych also confirms all five original jobs and 40 step objects are unchanged,
along with top-level configuration. The sole additional independent job retains
the shallow exact-directory sparse checkout, existing launcher selection,
installation prohibition, fixed output layout, and complete hidden-file upload.
The workflow SHA-256 is
`7f3ab7ef5ec94379a969c91e9f2348cecd2e80908c8a7330aef845f133f38e62`.

The exact relocated focused command ran once: 29/29 passed. Selected source
members were identical before and after. The two deliberate cleanup-deadline
failures each recorded zero child commands, terminal deadline expiry, no work
after expiry, and scratch preserved at the assertion. Test teardown subsequently
removed their owned temporary directories. Canonical ignored deadline outputs
remain as evidence; copies are frozen in this review.

The first existing CI-regression command ran all 63 methods with one error
(62 passes): this lane placed its owned temporary root under `verification/`,
which caused an existing envelope output-location guard to correctly reject
one test's expected fresh output. The original command, environment, traceback,
and raw outputs remain unchanged as `ci-regressions.*`. Root coordinated one
corrected rerun with a fresh owned `/private/tmp/` root outside the repository.
All 63 regressions passed with no test/source/control relaxation; that temporary
root was empty and removed. See `ci-regressions-corrected.*`. This was a harness
location correction, not a product or policy change.

Root's README was reviewed separately from the selected source roster. Root
corrected its focused-control example to create ignored `logs/` first and
replaced its custody wording with the actual quiescent-trusted-checkout identity
scope. The corrected byte-exact documentation snapshot is retained as
`canonical-README-reviewed.md`; it is not part of the 90-member source selection.

The canonical runner SHA-256 remains
`e531311facb7b38967d3b904b26e92ff3f6c4dc7444c856cd799b70a1d91373b`.
The pack manifest SHA-256 remains
`6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857`.
The original proposal's historical 28-control description is superseded by
the actual corrected 29-control suite; this review does not edit that frozen
proposal.

No new full Rust fixture invocation was run here. The existing independently
accepted full invocation remains separate evidence selected by root. Actual
Actions execution and Rust 1.98.1 qualification remain pending. This review adds
no arbitrary public File admission, source-work/lifetime/performance proof,
live interpreter/VM integration, target ABI/stack/RSS, native runtime,
simulator/emulator, UI, capture, physical-phone, signing/store,
separate-repository immutable published-package FieldLog, customer/operational,
or GA qualification. No such runtime or capture processes were started, and no
global process inventory was performed. Owned Python child groups and temporary
directories were bounded and cleaned by the exercised host controls.

`verify_integration.py` is the read-only inspection source used for the retained
inspection result. It can be rerun against this checkout, but writes its own
receipt; do not rerun it inside this frozen review. Use
`python3 -B verification/swift-cache-state-ci-canonical-review/verify_seal.py`
for read-only verification of this packet. No additional tests are necessary
for the documentation corrections.
