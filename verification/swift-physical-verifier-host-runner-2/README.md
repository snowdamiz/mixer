# Synthetic16 host controller amendment, source preparation only

This directory prepares one root-released execution of the frozen Python v2
physical geometry verifier's sixteen synthetic test methods. No controller,
candidate verifier, candidate tests, syntax check, actual saved-input parse,
compiler, model, capture, process probe, or native runtime was executed while
preparing this directory. This is independent offline local geometry only.
`complete_capacity_accepted` is always false; physical capacity, prices, backing
bounds, root funding, product, and GA acceptance remain held.

Root reported that runner-1 stopped in preparation at its controller-environment
guard before creating OUT/command directories, Popen, candidate imports, or
tests: **zero candidate test invocations**. Root's separate pinned-Python `-B`
stdlib `os`/`json` diagnostic then observed the seven supplied environment keys
plus macOS-added `__CF_USER_TEXT_ENCODING=0x1F5:0x0:0x0`. `AMENDMENT.md` records
the provenance and narrow correction. This preparation performed no diagnostic
or runtime check. Runner-1 and release-1 remain immutable. Root manually selects
this new source-corrected attempt; no automatic retry is introduced.

The binding amended host plan is `host-test-plan.json` in this directory,
SHA-256 `49348e2c66677933bca0028324bab7a52e639a894512c62b81bd367ea8f7d475`.
The unchanged base host plan remains
`verification/swift-root-bound-dispatch-physical-evidence-v2/host-test-plan.json`,
SHA-256 `83fdb4bae803e4f0374307f1302e2ecf4a67c5b37edfbcbc5f97faef1e44786e`.
The original packet seal is
`866d0058d5f54116f3459bc0fcf4a3afe6437e30f796c69d3759d2de8893bedc`.
The independent v2 source-review seal is
`0ca1c7d76fa013bbf0a93b3f1c9231722822d70de38ce109f1563b268d379f18`;
the sealed `review-result.json` is
`fc0715c8fb230e383f86a2113f3a589bae4c014a3039436d887fe8a64d365bda`.
The original packet and review continue to bind that base plan. The controller
checks the review's recommendation, empty findings, source map, and those base
bindings. It also requires a recursive deep diff between the base and amended
plans with exactly two changed paths: `/controller_environment` and
`/root_release_required/path`. The first must equal the base child environment
plus exactly the observed CF key/value, and the second must name release-2.
Neither review nor this preparation claims passing candidate syntax or tests.

Root must first review `run-synthetic16.py` and write the external receipt at
`verification/swift-semantic-adapter-root-review/dispatch-physical-verifier-v2-host-release-2.json`
using `release-schema.json`. Populate `controller_sha256` and
`runner_manifest_sha256` from the exact reviewed files. The controller requires
this receipt, its amended-plan and base-plan bindings, and pins its complete
bytes before/after. Preparing this directory
does not create that release or authorize invocation. Root's source-only review
and separate release remain the runtime boundary.

After release only, run this exact command from the checkout root, using an
otherwise empty environment:

```sh
/usr/bin/env -i LANG=C LC_ALL=C PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 TMPDIR=/Users/andreyyurlov/Documents/dev/mixer/verification/swift-root-bound-dispatch-physical-evidence-v2/command/tmp TZ=UTC __CF_USER_TEXT_ENCODING=0x1F5:0x0:0x0 /opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14/bin/python3.14 -B /Users/andreyyurlov/Documents/dev/mixer/verification/swift-physical-verifier-host-runner-2/run-synthetic16.py
```

No arguments, retry, precreated runtime directory, or precreated command tree
are accepted. Root's controller creates fresh `runtime/` here, plus the frozen
v2 `command/` and its initially empty `tmp/`, without overwriting any file. It
requires and records the complete actual eight-key controller environment;
extra keys or different values fail, without normalization or omission. It
launches exactly the frozen Python `-B source/tests_region_certificate.py`
argv/cwd and the unchanged seven-key environment provided to Popen once. No CF
key is added to that child environment argument. It records the Python identity, packet tree,
source files, before/after source/control/tool pins, and complete successful
stdout/stderr. The expected output is empty stdout and standard verbose
unittest stderr containing each frozen method once, all sixteen `ok`, and only
the standard successful summary. Any extra method, skip, warning, traceback,
unexpected output, nonzero exit, or output truncation fails acceptance.

The bounded custody sequence adapts the successful
`verification/swift-semantic-adapter-root-review/run-dispatch-region-model-v4.py`
controller (SHA-256
`bc0806b2307ea2180cc7f99cac8cb30481a4077fec854154aea222ad351074ab`)
and its recorded runtime observations. It removes every Rust compile/model
operation. The only child starts a new session; root observes its exact PID,
PGID, and SID, observes completion with exact-child `WNOWAIT`, reaps only after
that proof, then observes owned-group absence. Normal completion sends no
signals. Cleanup can signal only a still-running, unreaped, custody-established
owned group; no active signal exists after observed completion or reaping.
Permission refusal is sticky, including Python's normally implicit destructor
polling: the controller disables that destructor and makes no later custody
syscall for that child. Ambiguous custody/group disappearance preserves the
command tree and fails the receipt. There is no global process inventory.

All offsets are cumulative from controller startup: test work 44 seconds,
owned cleanup/inventory/removal 49 seconds, all posthashes and the one-way
signal cutoff before 53.5 seconds, final writes before 55 seconds. Deadline
checks cover the bounded loops and file work; these are host-controller checks,
not a kernel-enforced filesystem or process sandbox. After known closure only,
the owned command inventory permits at most 64 members and 16 MiB of regular
file contents, refuses symlinks/special/shared-hard-link/bytecode remnants, hashes
files after membership/size checks, and removes the owned command tree. Runtime
evidence stays here. Uncertain closure defers command inventory and removal;
posthash failure or incomplete evidence cannot pass. No candidate actual-input
verification or claim of external-file absence is inferred from this bounded
owned-tree observation.

`runtime/observations.json` precedes `runtime/receipt.json`. All observation
hashes precede the reviewed one-way signal cutoff; the final receipt explicitly
limits signal coverage to observed/pending signals through that cutoff. A failed
observation hash yields a failed receipt with a null observation hash when final
writes remain possible. If a filesystem/deadline failure prevents finalization,
missing evidence is failure and surviving artifacts are retained; never rerun
this lane automatically. Root must reconcile any ambiguity separately.

`manifest.json` inventories the five prepared files and records this source-only
scope. It omits itself to avoid a self-hash cycle; the external root release pins
its bytes. No git, global metadata, unrelated custody controls, other projects'
processes, simulator/emulator, physical-device, UI, or capture action belongs to
this preparation or future synthetic host command.
