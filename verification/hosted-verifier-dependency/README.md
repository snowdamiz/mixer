# Hosted verifier dependency evidence

This lane owns only this directory and docs/hosted-verifier-dependency.md.
It did not modify hosted source, root lockfiles, THIRD_PARTY, trackers or runtime
lanes. The user's pause ended experimentation after the running collector exited.

- qualification.mix.exs, qualification_test.exs, qualified.mix.lock: exact retained
  standalone Mix inputs; fixture keys are generated only in memory.
- run-1/: observed 21-test host run, command logs, runtime, input/dependency hashes.
- sources/, sources.json: official Hex/GitHub metadata and advisory snapshots.
- notices/: selected package license notices.
- attempts.json: initial nonpassing attempts, recorded from tool outputs.
- closeout.json: cleanup and pause boundary after the immutable run receipt.
- sealed-files.json: hashes of delivered evidence and recommendation.

The ignored scratch tree was removed after capture. No listeners or native
runtimes were started. Linux image, HTTP/JWKS transport/cache, real provider,
database/authorization and GA checks remain pending.

When the user resumes, the collector reconstructs a scratch Mix project and runs
retrieval/compilation, ExUnit and advisory checks. It refuses to overwrite run-1;
select a new output directory in a reviewed copy before another run. No new run
is authorized by this pause handoff.
