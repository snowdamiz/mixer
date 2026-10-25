# Controller Linux hard-restart harness repair

The controller job for revision `908b0d953c35389a6b12900f8875b0bf3f88d4a1`
failed in [Linux CI run 40158540132](https://github.com/snowdamiz/mixer/actions/runs/40158540132)
after 24 original groups. Its first hard restart threw
`owned_workerd_identity_ambiguous`. The immutable Linux logs and command receipt
remain under `verification/github-ci-908b0d95-controller/`; the repair packet
binds their hashes in `diagnosis.json`.

The harness compared `ps comm` with the installed full workerd path. The
[procps manual](https://gitlab.com/procps-ng/procps/-/blob/master/man/ps.1)
defines Linux `comm` as the executable name. This documented platform difference
explains the failed selection; that run did not capture a process-table snapshot.
The [Linux kernel documentation](https://www.kernel.org/doc/html/latest/filesystems/proc.html)
identifies `/proc/PID/exe` as the process executable link.

`test/owned-workerd-identity.mjs` now reads direct children of the current Node
owner from a numeric process table. On Linux it resolves each child's
`/proc/PID/exe` and the installed workerd path, requires exact canonical path and
device/inode equality, and requires exactly one matching child. An unreadable
installed path or direct child's executable identity fails closed. The
synchronous `ps` observer is excluded only by its exact spawn PID. Selection is
repeated immediately before sending `SIGKILL`; both observations must agree.
There is no basename kill or process-group kill in this helper.

macOS retains the existing direct-parent and exact full-path `ps comm` check,
with the added recheck. Apple's
[ps implementation](https://raw.githubusercontent.com/apple-oss-distributions/adv_cmds/main/ps/print.c)
derives this field from `argv[0]`. That behavior remains suitable only for this
trusted local harness; this repair does not qualify adversarial Darwin process
identity. The synchronous recheck also does not claim an OS pidfd guarantee.

`acceptance-driver.mjs` still kills the selected original workerd before
disposing and replacing Miniflare. The replacement uses the same captured
SQLite persistence directory. Original restart assertions, frozen regression
assertions, production source and dependencies remain unchanged. Root added the
durable identity controls to `test/check.mjs`; its recursive source inventory
automatically binds both new helper files.

One complete pinned Node 22.23.3/npm 10.9.9 host run passed on macOS 27.0.1 arm64:

| Check | Observed result |
| --- | --- |
| Identity controls | 20 passed, including injected Linux refusal cases, recheck changes and a live exact direct-child kill/reap. |
| Existing controller suites | 28 original, seven exact regressions and 36 focused groups passed: all 71 unchanged groups. |
| Actual workerd restart controls | Eight `SIGKILL` receipts; the unchanged SQLite recovery assertions passed. |
| Build and production closure | Passed; nine production files, only `cloudflare:workers` external, no test bundle. |
| Cleanup | All six runner command groups empty, pipe EOF observed, scratch removed; all 153 recorded persistence paths absent. |

The tested source digest is
`1570f0bf9c0c8e30e9eca1a2356651da5b13f01fd619a26af5563362681b97b4`.
Exact argv, tool versions, source snapshots, output hashes and cleanup receipts
are in `verification/hosted-worker-controller-linux-restart/host-run/`.
`receipt.json`, `protected-inputs.json` and `repair.diff` in the parent packet
summarize the repair and preserve the exact diff.

Actual Linux execution of the repaired helper and all restart cases remains
pending Root's next CI run. Injected Linux observations on macOS are not Linux
runtime evidence. This slice qualifies only the local workerd/SQLite test
harness with synthetic clock/provider; cloud, provider, native device, signing,
store, immutable dogfood release and GA gates remain outside its evidence.
