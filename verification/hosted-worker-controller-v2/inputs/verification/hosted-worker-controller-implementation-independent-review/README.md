# Frozen independent review packet

Outcome: rejected for two correctness findings. The unchanged producer suite
passes; independent authority/clock regressions intentionally exit 1 on the
reviewed source. See the owned report in `docs/` and `receipt.json`.

No packages were installed. Reuse exactly the sealed producer dependency bytes;
any later reinstall must use `npm ci --ignore-scripts --no-audit --no-fund` with
the already pinned versions and must be separately recorded. No global install,
cloud/provider call, Git, native runtime or deployment is part of this packet.

From `/Users/andreyyurlov/Documents/dev/mixer`, the exact replay sequence is:

```sh
python3 verification/hosted-worker-controller-implementation-independent-review/verify_and_copy.py
python3 verification/hosted-worker-controller-implementation-independent-review/run_command.py build-replay build.mjs
python3 verification/hosted-worker-controller-implementation-independent-review/run_command.py producer-replay test/run.mjs
python3 verification/hosted-worker-controller-implementation-independent-review/run_command.py independent-regressions /Users/andreyyurlov/Documents/dev/mixer/verification/hosted-worker-controller-implementation-independent-review/regressions.mjs
python3 verification/hosted-worker-controller-implementation-independent-review/prepare_noncooperative.py
python3 verification/hosted-worker-controller-implementation-independent-review/run_command.py build-noncooperative-fixture build.mjs
python3 verification/hosted-worker-controller-implementation-independent-review/run_command.py noncooperative-regression /Users/andreyyurlov/Documents/dev/mixer/verification/hosted-worker-controller-implementation-independent-review/noncooperative.mjs
python3 verification/hosted-worker-controller-implementation-independent-review/run_command.py independent-closure /Users/andreyyurlov/Documents/dev/mixer/verification/hosted-worker-controller-implementation-independent-review/closure.mjs
python3 verification/hosted-worker-controller-implementation-independent-review/finish.py
python3 verification/hosted-worker-controller-implementation-independent-review/verify_final.py
```

Preserve this packet before replaying: these commands write current independent
outputs in this owned directory. `run_command.py` sets a separate absolute
`MIXER_CONTROLLER_TEST_REPORT`, so no test overwrites producer evidence.
The first regression attempt is retained with relocation bindings because its
original output names were subsequently reused by the expanded regression run.
That run's source is `regressions-attempt-1.mjs`; the final run's source is
`regressions.mjs`. Both run against unchanged frozen product/test bytes.

`reviewed-source-snapshot.tar.gz` is a byte-identical copy of the reviewed
producer archive. `review-fixtures.tar.gz` preserves the review scripts, exact
independent fixtures and report. The final collector verifies every producer
binding again, verifies scratch production source/outputs/dependency bytes,
checks exact owned process identity and all recorded temporary storage paths,
then removes only its owned scratch. It never kills a broad process name or
touches another project's state. Cleanup and failures remain in the receipt.
