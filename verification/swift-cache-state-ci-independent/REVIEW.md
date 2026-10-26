# Independent review: revision required

The frozen candidate runner
`92bf2c0ca453ad9cae8ad6274d2248870af1cad4f4044039afde28f806d4392d`
needs two repairs before an independent full qualification run. The original
producer packet remains unchanged. Root explicitly instructed this review to
stop short of the full normal run after the first required-contract failure.

1. Every child must receive owned temporary directories. `environment({})`
   removes TMPDIR, TMP and TEMP; command calls without overrides never replace
   them. This affects tool selection, compilation, API compilation/execution and
   Git identity commands. An actual Python child through the exact copied
   Commands implementation observed all three variables as null, with exit 0
   and its owned group returned. Bind Commands to an existing owned scratch
   directory, provide all three variables for every child, and reject temporary
   overrides outside that binding. Preserve the fixture tests' owned overrides.
   Evidence: `evidence/candidate-temporary-environment-gap/receipt.json`.

2. Cleanup expiry must terminate remaining postflight/retention work. The one-shot
   SIGALRM raises TimeoutError inside postflight `check()`, which catches
   BaseException and continues after the timer has expired. A focused control
   lowered only its test cleanup allowance to 0.05 seconds, delayed the first
   postflight check, and observed a further 0.25 seconds of cleanup after that
   TimeoutError was collected. No Rust, Git or native child ran in this control.
   Use a distinct terminal deadline exception, propagate it past collectors,
   track absolute remaining cleanup time, and preserve recoverable scratch when
   expiry prevents retention/removal. Evidence:
   `evidence/candidate-cleanup-deadline-gap.json` and
   `candidate-copy/runs/cleanup-deadline-control/receipt.json`.

Independent custody verification covered all 2,434 producer members and
156,179,074 bytes, plus the closed 86-member / 8,836,866-byte pack. All 17 source
and oracle files and all 25 API sources match accepted frozen bytes. Independently
derived methods, partitions, complete result first lines, raw File hashes,
complete32 projections and 23 complete accounting layouts match the candidate
expectations. The test-only derivative is the exact source plus the two fixed
cfg(test) declarations and control sources; no product implementation changed.

Before candidate access, actual Rust1.99.0 / macOS arm64 independently passed
50 API dispositions across Debug and optimized mode: four positive executions
and 76 intended primary error spans. The exact candidate diagnostic, method,
layout, pack/path and case validators then rejected 919 deliberate negative
controls. That audit revalidated 46 independently captured actual API errors;
eight listing and 25 execution parser baselines were read from sealed producer
history, and case-boundary controls used 31 explicitly synthetic small cases.
These validator checks receive no fresh normal-suite or public File credit.

The setup/expectation authoring errors and one case-order audit mistake are
retained separately. The case-order correction joins identical cases by unique
identity; it changes no expected bytes. Every child started by this review is
reaped, all compiler products were hashed before deletion, and disposable control
scratch is removed. Retained source/evidence snapshots remain available.

The original full producer Debug60s timeout stays failed. General public File,
Rust1.98.1, canonical CI/workflow placement, live target/native runtime, phones,
signing/store, separate-repository immutable-package FieldLog, operational and
GA qualification remain pending. This review uses a trusted quiescent checkout
and makes no adversarial filesystem claim. A corrected runner requires its own
frozen source review, focused controls and complete fresh host invocation.
