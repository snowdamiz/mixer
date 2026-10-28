# Ordinary remote Phoenix CI source compatibility

All nine canonical lifecycle methods can be selected by the existing ordinary
Phoenix suite without test-code changes. This is a source conclusion; no remote
run or success is claimed. The fresh checkout resolves the current locked
JOSE1.11.13, avoiding the stale shared local1.11.12 closure without local builds.

Mix discovers both *_test.exs files, compiles test/support under MIX_ENV=test, and
uses the existing --no-start alias. Both modules run asynchronously false with
distinct owner registrations. OTP29.1.1 and Elixir1.20.4-otp-29 match the selected
OTP record instrumentation. The tests have no hard-coded macOS runtime paths;
TLSFixture uses private loopback port0 and openssl in PATH. Actual Linux TLS,
loaded dependency versions and timing assertions still require the remote run.

For a reviewable lifecycle receipt, the host collector should create an
identity-lifecycle output directory and set MIXER_KEY_OWNER_LIFECYCLE_EVIDENCE.
The current collector sets a differently named identity metrics variable, so
ordinary tests execute but their dedicated JSON/resource/callback observations
are discarded. Existing artifact upload already retains the output tree.

For the new test-only supervisor seam, extend the existing production exclusion
check to assert its start_fixture/1 export is absent and fixture init fails closed
without starting children. No product behavior or test assertion needs changing.

Keep KOL09 adverse assertions intact; a concrete failure must retain its exact
callback reason and old-resource ordering. Ordinary broad CI and its PostgreSQL
fixture have different scope/bounds from the local55-second standalone plan and
do not qualify that harness custody protocol or its18 typed artifacts.

Only source reads/hashes/snapshots were performed. No CI, process probe, native
child, compiler, formatter, TLS or replacement dependency preparation ran.
