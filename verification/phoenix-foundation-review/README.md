# Independent foundation review evidence

`reviewed-source.tar.gz` is the unchanged owner candidate-2 archive, verified
against `owner-candidate-2-receipt.json`. `review.py` extracts it to a disposable
scratch checkout, verifies every source hash, reuses only the locally present
pinned dependencies, builds separately, starts its own loopback PostgreSQL and
runs `probes/foundation_adversarial_test.exs`. It stops that instance in `finally`
and removes only its own scratch after shutdown.

Reproduce from repository root with
`python3 verification/phoenix-foundation-review/review.py`.

`receipt.json` and `commands/` hold the passing five-test run. The first failed
harness migration-path attempt is retained in `attempt-1-harness-path/`; it ran
zero tests and is not a pass. The corrected probe asserts and uses the exact
frozen source migration path. No root product source was changed to fix a test.

`current-product-inputs.json` compares all reviewed product/config/migration/lock
files to the active checkout separately from root's candidate-3 collector/docs/CI
work. `dependency-inspection.json` hashes the pinned Oban sources inspected for
the notifier/peer connection explanation. `review-summary.json` binds the final
review artifacts and their scope.

The environment is local PostgreSQL17.11 without TLS and synthetic test-only
credentials, plus actual Bandit HTTP and the installed Elixir/OTP toolchain. It
does not exercise hosted identity, RLS, Neon/Cloudflare, a real worker/signer,
production publishing or a GA gate. No native/UI/device activity occurred.
