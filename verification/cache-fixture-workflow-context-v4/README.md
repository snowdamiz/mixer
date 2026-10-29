# Fixture workflow context v4

The exact v3 dispatch was refused before a diagnostic job existed: HTTP 422,
line 22 column 20, `runner.temp` unavailable in job-level `env`. No v3 Rustup
installation, compiler execution or fixture result exists. The original failed
workflow and sealed packet remain unchanged. See `decision.json` for the bound
dispatch evidence and `selection.json` for the concrete replacement.

The correction moves the same isolated `RUSTUP_HOME` expression into `env` on
both the explicit provisioning step and the fixture step. The installer and
fixture shell bodies are byte-identical to v3. Rust 1.98.1-aarch64-apple-darwin,
official endpoints, `RUSTUP_AUTO_INSTALL=0`, the 120-second installation bound,
one installation, one fixture claim, and every v2 fixture safeguard remain fixed.
The next executable test unlocked is the original 103-command fixture: its
first commands establish sysroot and exact compiler identity, then all 1,003
context vectors run under the unchanged 60/600/60-second limits.

GitHub's [context availability table](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability)
excludes `runner` from job `env` and includes it in step `env`. The corresponding
`job-env` and `step-env` definitions in GitHub's
[workflow schema](https://github.com/actions/languageservices/blob/main/workflow-parser/src/workflow-v1.0.json)
confirm this distinction. `context-rules.json` freezes the relevant context
allowlists and schema relationships reviewed through the web tool.

Neither `/opt/homebrew/bin/actionlint` nor `/usr/local/bin/actionlint` exists.
No validator was installed, no broader executable search occurred, and no
actionlint pass is claimed. The available Python environment has no PyYAML;
the Node environment has no `yaml` module. The standard-library checker parses
the candidate's restricted mapping/sequence/scalar/literal-block subset,
checks its structure and every expression against the official context
allowlists, and rejects unsupported syntax. It is not an official or complete
YAML/Actions validator. GitHub service parsing and Bash execution remain pending.

Sixteen guarded pure controls pass, including reproduction of the original
job-env rejection, step-env acceptance, exact parsed v3-to-v4 transformation,
mutation rejection, immutable source closure, and synthetic installed-workflow
checks. Process creation, session/group access, signals, waits, sockets and
sleeps are denied; writes are restricted to this sibling. The initial local
preparation failure and its correction are preserved. Current outputs are in
`logs/pure-controls.json` and `logs/pure-controls.stdout`; those runtime paths
are excluded from the immutable source seal. Run:

```
python3 -B verification/cache-fixture-workflow-context-v4/test_context.py
```

Root may select delivery of the sealed sibling and the new canonical workflow
at `.github/workflows/cache-fixture-workflow-context-v4.yml`. Delivery must
first confirm the SHA in `selection.json` before removing the rejected
`.github/workflows/cache-fixture-compiler-admission-v3.yml`; its frozen source
and Git history are retained. The v4 verifier binds the original v3 and v2
packets, requires the unchanged canonical v2 workflow, and requires the rejected
canonical v3 workflow to be absent. The remote checkout adds only the thin v4
packet. It runs these 16 controls, the unchanged v3 admission controls and the
unchanged 45 v2 controls before the single explicit installation and fixture.

Rustup descendant reap and provider disposal of its isolated home remain
unverified, as in v3. No recursive deletion is added while custody could be
unknown. The install home is excluded from artifact upload. Fixture cleanup
and custody are unchanged. No local compiler, product runtime, native/UI/capture
process, inventory or held-process probe was started. All active holds remain.
This packet accepts no runtime release, performance result, customer milestone
or GA gate. Root alone selects any delivery and the single future dispatch.
