# Explicit controller environment after prelaunch refusal

Root's direct task message reports that the first launch of runner-1 stopped at
the exact controller-environment guard in `prepare()`. OUT, command/tmp, Popen,
candidate imports and candidate tests had not started. That attempt consumed
**zero candidate test invocations**, and supplies no passing runtime evidence.
Root separately ran one isolated `env -i` diagnostic with the pinned Python
`-B`, using stdlib `os` and `json` only. Its actual environment contained the
base plan's seven keys plus the macOS-added key/value:

```text
__CF_USER_TEXT_ENCODING=0x1F5:0x0:0x0
```

Those runtime facts are supplied by root, which records the refusal and
diagnostic separately. This preparation has not executed a diagnostic,
controller, candidate module, candidate test, syntax check, or process probe.
It makes no independent runtime observation. Root's frozen prior artifacts stay
unchanged:

| Prior artifact | SHA-256 |
| --- | --- |
| runner-1/run-synthetic16.py | `f4b2385fd5a2a86fafb44a65855a64879185c8666808a96811243bf5177adc34` |
| runner-1/manifest.json | `5210e48b28f095a5d820d7db35670884c4a69433a74e3ee5ef82d9246b2e73bf` |
| root dispatch-physical-verifier-v2-host-release.json | `1fb9d71a94ce87d83c7800ebdf4744cb50d89458cf814a9812845dbb3ce53aa2` |

The new local `host-test-plan.json` is copied from the base plan SHA-256
`83fdb4bae803e4f0374307f1302e2ecf4a67c5b37edfbcbc5f97faef1e44786e`.
Its SHA-256 is
`49348e2c66677933bca0028324bab7a52e639a894512c62b81bd367ea8f7d475`.
Only two deep plan paths differ:

| Path | Exact amendment |
| --- | --- |
| `/controller_environment` | Add an eight-key object equal to the base seven-key environment plus the observed CF key/value above. |
| `/root_release_required/path` | Change to `verification/swift-semantic-adapter-root-review/dispatch-physical-verifier-v2-host-release-2.json`. |

The controller requires that exact recursive deep diff, including exact types
and values, and compares the complete actual `os.environ` to the amended
eight-key object. It never strips or silently normalizes keys. The environment
argument provided to the test child remains the base plan's exact seven keys.
The child argv, cwd, interpreter/source/input pins, synthetic16 roster, output
checks, custody/cleanup sequence, bounds and all acceptance limitations remain
unchanged.

The source packet seal
`866d0058d5f54116f3459bc0fcf4a3afe6437e30f796c69d3759d2de8893bedc`
and independent source-review seal
`0ca1c7d76fa013bbf0a93b3f1c9231722822d70de38ce109f1563b268d379f18`
continue to bind the base plan. The new external root release must separately
bind both the amended plan and `base_plan_sha256`, the new controller and
manifest, and the original exact packet/review/source map. Both plans and all
those source/control/tool pins are checked before and after the future command.

Root manually selects and reviews this new source-corrected attempt. Preparing
it neither executes it nor releases it. Automatic retries remain zero; exactly
one test invocation is permitted by a future release. Native device,
simulator/emulator, UI, capture, actual saved-input parsing and unrelated local
custody controls stay held. All results remain local geometry only, and
`complete_capacity_accepted` remains false.
