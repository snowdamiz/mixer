# Independent experimental archive-builder review

`test_public_builder.py` runs original negative cases through a byte-for-byte copy
of the public CLI in isolated Git repositories. It checks normal and optimized
Python, frozen input guards, output/cache containment, and descendant cleanup on
output overflow. Its minimal Rust source and controlled compiler selector are
negative test fixtures; they never qualify a real build. Successful cross-build
artifacts and their exact immutable source/header/tool receipts are audited
separately after the builder candidate is frozen.

The frozen candidate `e7e34079d7af7d26162ccfc0c43cc6d269fb500ed42bd5e1aef91765e2fee076`
passed 13 independent public CLI test functions, each in normal and optimized
Python (26 mode executions). `final-public-cli.log` records the candidate/harness
hashes and successful outcome. `initial-public-cli.log` is retained preliminary
work and is not the final qualification.

`audit_artifacts.py` independently matched the final implementation receipt,
five frozen qualification inputs, 22 outer command logs, 63 evidence files, all
four target archives/headers/client binaries, exact source exports and tar
members against 81 Git blobs from native commit
`b25e3b7de2391a80d12e7fd75e60903495bec120`, the recorded installed tool binaries,
27 public symbols per archive, and the retained failed fixture/LLVM attempts.
See `receipt.json`. The real host C clients passed 27 smoke and 52 shared-registry
checks. iOS, simulator and Android artifacts were compiled and linked only.

Review changes included discovering the Rust selector instead of hardcoding it,
rejecting implicit build scripts, killing and observing child process groups,
quarantining interrupted or unconfirmed cleanup, and checking quarantine after
acquiring the owned cache lock. The cache and installed tools are trusted; the
builder does not isolate hostile processes running as the same user. This is
scoped development build evidence, with no Swift bridge, release identity,
signed activation, binary reproducibility or distribution qualification.
No device, trust-store, credential or production changes are part of this review.
