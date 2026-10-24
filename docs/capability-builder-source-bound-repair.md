# Capability archive source export bound

CI on `df55f4a5` and `fb531a18` passed the VM and services jobs, then rejected
the Swift job's capability archive snapshot before compilation. The integrated
dispatch/accounting source is 9,253,942 bytes, exceeding the builder's 8-MiB
per-file limit. Its complete selected source is 139 files and 16,546,082 bytes.

The builder now permits at most 16 MiB per source file. The 64-MiB aggregate,
8,192-file and 512-MiB archive bounds remain unchanged, as do frozen Git input,
regular-file, header, dependency and output-ownership checks. Per-file and
aggregate failures now have separate diagnostics. This changes source export
capacity; it changes no guest runtime budget or VM source.

All 26 builder controls pass under normal and optimized Python. New controls
accept an exact-boundary Git blob, reject one byte over before creating output,
and verify aggregate rejection before reading the overflowing blob. The original
builder rejects the exact pushed source; the repaired builder accepts it.

A fresh macOS archive build preserves all 28 expected public symbols. The smoke,
mixed-registry and guest-UI C consumers compile and pass. All 100,761,083 bytes of
owned scratch were removed after an empty holder check. Source, tools, commands,
logs, hashes and cleanup are in
`verification/capability-builder-source-bound-repair/receipt.json`.

The failed CI results remain recorded in
`verification/github-ci-df55f4a5-engine/receipt.json` and
`verification/github-ci-fb531a18-engine/receipt.json`. Corrected pushed-source CI
is still required. These are host checks; no native, lifecycle, Linux resource
or GA acceptance is implied.
