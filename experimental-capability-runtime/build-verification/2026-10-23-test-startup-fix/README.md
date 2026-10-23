# Subprocess fixture startup correction

CI run `39907419542` failed the old output-overflow subcase because its shared
250ms command deadline expired before the parent and descendant Python processes
finished startup and emitted the flood. The other 21 builder test functions and
VM/services jobs passed; the actual CI archive stage was skipped. Root retains the
provider logs under `verification/github-ci-eb5dd05/`. This local receipt is not a
claim that the corrected candidate has passed a new CI run.

Only `build-tests/test_builder.py` changes. `build-vm.py` remains exactly
`e7e34079d7af7d26162ccfc0c43cc6d269fb500ed42bd5e1aef91765e2fee076`; no native,
header, contract, compiler or archive change is involved. The earlier four-target
receipt and its recorded input hashes are historical evidence and remain intact.
The original test bytes from committed `eb5dd05e43fe3b6d77e3799cd317d7b64d4c58ea`
are preserved here as `baseline-test_builder.py`; final candidate bytes are
`candidate-test_builder.py`.

The corrected test keeps real child/descendant processes and the actual private
process session. A scoped proxy for the builder's subprocess module waits at most
10s for a descendant heartbeat and parent readiness, then releases a stdin barrier
and returns the real `Popen` object. The builder starts its normal real deadline
*after* `Popen` returns. The test restores its proxy in `finally`. The proxy owns
kill/reap/group-exit cleanup if its startup path throws before the builder receives
the child; a dedicated controlled startup-failure subcase checks this too.

The output subcase deliberately spends at least400ms in fixture startup, exceeding
the original250ms deadline. Only the timeout subcase still uses250ms; output,
nonzero and orphan cases have a5s scheduling ceiling because their exact failure
reason is the proof. Output must be `command output limit` with exactly1000
retained `x` bytes from a10000-byte flood. A timeout is never accepted as overflow.
The nonzero subcase must retain exit7; the successful parent/orphan must retain
exit0 plus the explicit descendant failure. Every descendant heartbeat must stop.
Writer lifetime is independently capped at30s, even if a test itself fails.

The final candidate SHA-256 is
`541169114d62b237844cf815b1b5495c540d59c3ff293533eec32f6ccfe51138`.
The new [receipt.json](receipt.json), SHA-256
`e174236cb205f24639277e3ac6191e4d5e55eca06d3ab172439271411519d9ad`,
records22 passing functions in normal Python and22 under `-O`, actual commands,
log hashes and source stability. Replay using the two command arrays in that
receipt. The candidate snapshot stored here is evidence; invoke the real test
path so its repository-relative builder lookup is correct.

This is a test fixture correction, with no new device, native runtime, release,
identity, full Swift or publication qualification.
