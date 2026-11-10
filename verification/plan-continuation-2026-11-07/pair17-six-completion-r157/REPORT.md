# R157: PASS — actual local Pair17 six-consumer integration

The unchanged local checker completed all six consumers and 12 refusal cases in 89.09 seconds. Exactly two fresh producer builds ran with jobs=2; no harness correction or prebuilt substitution was used. Both fresh installed entry guards passed.

Source116: `fc2b86d54f8e813c42956f65f84882fef3795607816dd21bf0e8b36eeb0499b4`. R152 local snapshot revision `c24bca1a45d63b30d4e496f006f2ad587a341e64`, tree `3f14fdf1ae2e9e0cc5b56f1b3c81646ad8954a7d`. Owning manifests matched before and after; all 343 explicitly selected files matched in both canonical source and the reused snapshot. SDK24, adapter27, Java21, eight callers and the 32-member seal were admitted by the unchanged guards.

| Consumer | javac | D8 | Sources | Classes |
|---|---|---|---:|---:|
| debug-original | PASS | PASS | 21 | 230 |
| debug-relocated | PASS | PASS | 21 | 230 |
| debug-exported | PASS | PASS | 21 | 230 |
| release-original | PASS | PASS | 21 | 230 |
| release-relocated | PASS | PASS | 21 | 230 |
| release-exported | PASS | PASS | 21 | 230 |

Each result also passed verbose javap member inventory (5,537 references) and DEX descriptor checks. All six emitted consumer inventories were equal. Strict javac used `--release 17 -Xlint:all -Werror -proc:none`; D8 used `--min-api 28` and the installed Android37 jar.

| Refusal case | Debug | Release | Expected CLI code |
|---|---|---|---|
| sdk | PASS | PASS | `android.sdk-compatibility` |
| adapter | PASS | PASS | `android.sdk-compatibility` |
| descriptor | PASS | PASS | `android.sdk-compatibility` |
| extra-java | PASS | PASS | `android.sdk-compatibility` |
| profile | PASS | PASS | `android.sdk-profile-mismatch` |
| missing-lock | PASS | PASS | `android.sdk-profile-required` |

All 12 cases were exercised through both CLI and generated driver (24 expected exit-1 commands); none created `.mixer` staging. Raw refusals remain in `integration/receipt.json` and command stdout/stderr.

Tools: Swift 6.3.3; javac/javap 25.0.4.1; D8 9.2.4-dev (`084a89126ae0596c599143df57a654646af28313`); Xcode 26.6 (17F113), MacOSX26.5.sdk; Python 3.14.8. Apple paths were selected per command. The producer dependencies came from existing local SwiftPM caches and matched pinned revisions with clean postflight status; network Git protocols were disabled.

The original checker retained all process ownership and identity rules. The direct adapter used its existing command-budget parameters (720 active seconds, 60 cleanup seconds). `execution.json` records argv, selected environment and checker identity. The runner has no accepted prebuilt producer option, so the R152 CLI was preserved and two real Debug/Release builds were performed.

All 79 command records reached terminal custody; outer exec exited 0. The runner removed its exact generated scratch. Fresh R157 userdata was removed after terminal completion. The R152 snapshot and CLI remain preserved. No canonical source/metadata changes, remote publication, devices, signing or held-resource operations occurred.

Scope: local development integration only. Canonical Pair17 is not yet qualified on main. Hosted CI, immutable published packages, API28 floor/linkage, APK/runtime, physical-device and GA gates remain pending. All historical holds remain active.

Compact receipt: `result.json`. Raw evidence: `integration/receipt.json`, `integration/commands/`, six per-consumer receipts and class/DEX outputs. Before/after identities and cleanup are recorded beside this report.
