**ACCEPT the exact Rust 1.99.1 ordinary-CI host-fixture profile. Zero blocking findings or missing required actual observations within this scope.**

Independently audited run `42419571138`, cache job `128544871831`, artifact
`13593027379`, at revision `df7b67ace3441707049d47c289cefaed83dcdc6c`
and tree `c78ef17a48852e31f70da4dbf9b84a11926164fa`. GitHub identifiers,
reported job success, and the GitHub ZIP digest were supplied by the parent;
this review made no network requests. The verdict comes from actual retained
data and the reviewed source closure, independently of the reported green job.

- **Artifact custody:** independently hashed the 1,769,375-byte ZIP as
  `300fc4ca7d071e50d69b316fa3a9811b832889034b17e32bcef6aca5f7e1b093`.
  All 840 extracted files match ZIP bytes, with identical rosters. The extraction
  contains 46,981,459 bytes and remained unchanged through the audit.
- **Exact selection:** raw verbose output matches Rust 1.99.1, commit
  `58cf8f9c35b355199727627d07ae34a4e2846d67`, date `2026-10-13`, host
  `aarch64-apple-darwin`, LLVM `23.1.1`. Admission and terminal postflight record
  compiler SHA-256
  `1ba7bb8e273bd64125f4048d2ecce530e0a6470e565ab1b3aecf0b82b532f7b1`.
  The launcher/sysroot/resolved compiler join, selection snapshots, current
  invocation, and successful selection postflight agree.
- **Reviewed closure:** bound all 169 prospective review inputs: 79 directly to
  artifact bytes, 86 original base members through their unchanged uploaded
  manifest, and four preserved historical inputs to their actual local bytes.
  Checked the 16-member historical seal and 137-member dependency manifest.
  The entire installed workflow equals the independently reviewed prospective
  workflow. The unchanged runner and executed snapshot hash to
  `5b29269988838c8af4fdfd4858645b17837bddd8812a133ef4e6aaa709ba55ad`.
  The 86-member effective pack and exact 19-member derivative match their bytes,
  including the append-only private control source.
- **Complete workload:** reconstructed and matched all 103 commands in order,
  including their argv, working directories, environment overrides, exits,
  stdout/stderr hashes, and separate command records. There is one admitted
  fixture invocation, both modes, and all 18 original producer Debug partitions.
- **Observed behavior:** per mode, all 84 host, 108 producer, 98 independent, and
  94 control methods execute with exact inventories and terminal success:
  768 method executions total, with no ignored or failed methods. These totals
  include overlapping methods across lanes; they are not 768 unique tests.
  Both producer context traces contain 16 records ending at 1003/1003, and
  terminal test success is separately present. All 124 four-File captures
  (31 original cases in each of four lane/mode combinations) match input bytes,
  report bytes, complete aggregate/error text and input stamps: 116 aggregates,
  eight outer errors, 620 captured files. All 92 layout observations and the
  ten private control markers per mode match; private controls gain no public
  reachability credit.
- **API controls:** all four positive compilations execute successfully. All
  46 negative compilations return clean exit 1, emit no recorded product, and
  match the required diagnostic codes, messages, and all 76 exact primary target
  spans. Unexpected nested/unclassified errors are rejected by the audit.
- **Original bounds and cleanup:** the original 60-second child, 600-second
  active, 60-second cleanup and 8 MiB stream caps remain. Recorded active time
  is 191.219232 seconds, cleanup 2.206556 seconds, and longest child 37.994088
  seconds. All 103 children/groups have terminal facts, without timeout,
  output cap or custody hold. The runner records hashing 916 scratch files,
  retaining 901 nonproduct files, hashing/removing 14 compiler products and its
  ownership marker, and then removing owned scratch. All retained bytes and
  product-hash joins agree. The ten source/tool/ownership postflights pass,
  including unchanged revision and tree before and after.
- **Current control evidence:** retained current-CI logs show 16 adoption,
  nine materializer, 36 runner, and 16 exact-selection controls passing
  (77 recorded tests). Expected injected deadline failures remain failures,
  preserve scratch at assertion, and record test teardown. The descendant
  timeout control records child return and group disappearance. These controls
  were inspected as data, not rerun by this reviewer.

`audit_actual.py` passed **14/14 data-audit groups**, including eight independent
in-memory rejection controls. It uses standard-library data operations and
blocks child execution, process signalling, network calls and writes outside
this directory. There were zero guard denials and no compiler, imported runner,
native runtime, process probe, child agent, CI poll, commit or push. The audit
ran on Python 3.14.8; the fixture and current-CI controls ran on Python 3.15.2
on macOS 15.8.2 arm64. These environments remain explicitly distinct.

The compact frozen packet contains 515 files / 3,347,750 bytes, including raw
command evidence, receipts, original inventories, current control logs, all 124
case result texts, selected source evidence and a hash manifest for every
extracted file. Large input/report blobs and full source packs are not copied;
the pinned original ZIP supplies them for a complete rerun. `frozen-manifest.json`
binds the compact packet. `audit-output.json` is the machine-readable verdict.

Reproduce from the repository root using the original extraction and ZIP:

```sh
python3 -I -B -S verification/plan-continuation-2026-11-07/cache-actual-review/audit_actual.py --review-root verification/plan-continuation-2026-11-07/cache-actual-review/evidence/reviewed
```

That rerun passed and matched every audit field from the freeze run except the
freeze-only packet metadata. Its output is retained as
`reproduction-output.json`; both stderr files are empty. Use `--artifact-root`
and `--zip` if the unchanged original files have moved. No extraction or runner
execution occurs. `--freeze` additionally saves/validates the compact packet.

The prior run `40974383080` remains **failed after two identity/sysroot
commands**. Its selected policy was 1.98.1; its actual hosted compiler already
reported 1.99.1 and was refused. Its unchanged receipt SHA-256 remains
`225732b76d54f583a2570ca1692e6c397c98c4124dce4c0d6d43edc3032f7491`.
The fresh exact 1.99.1 admission and full successful fixture do not rewrite that
baseline. The original full Debug timeout also remains failed.

This acceptance covers this exact source, compiler identity/hash and host
fixture. Compiler/interpreter binaries and removed products are not uploaded;
their hashes and cleanup are observations made by the hash-bound trusted CI
runner, not live observations repeated on the remote machine. Original raw base
members omitted by upload bind through their reviewed manifest; the complete
effective run pack is directly checked. Quiescent trusted-checkout assumptions
remain; there is no adversarial custody guarantee. No blanket envelope,
performance equivalence, full replay, native/device, FieldLog package/dogfood,
release, operational or GA qualification follows. All physical-phone,
specifically held historical process/v5 startup, and frozen-hosted-lane holds
remain untouched. Source proposal flags remain false and were not edited.
