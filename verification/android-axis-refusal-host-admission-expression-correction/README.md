# Isolated Android axis workflow expression correction

This source-only sibling corrects the concrete GitHub validation failure in the
preserved `android-axis-refusal-host-admission-result-correction` packet. Root
reported delivery revision `c89b4d1657fc46581d8788169f9c961a2413c4f4`, tree
`507ff501dbb8130ce37632eb3b207f5990f3689c`, and installed workflow SHA256
`ff3f4f99a8e99794b881fe34b8a4b4b3ac5491b98144b2df0cfc7763916bbf64`.
[GitHub run 40883832500](https://github.com/snowdamiz/mixer/actions/runs/40883832500)
failed validation on push, attempt 1, with zero jobs: line 30, column 23 used
`runner.temp` in job-level `env`, where that context is unavailable. This was
not a manual axis dispatch and did not execute any of the nineteen tests.
The original packet, installed workflow and failure evidence remain unchanged.

The [official GitHub context availability table](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability)
allows `inputs` and `github` in job `env`, while `runner` is available in step
`env`, `run` and `with`. The smallest correction here removes the job-level
output assignment and initializes it in the existing first shell/data step:

```bash
export MIXER_AXIS_OUT="$RUNNER_TEMP/android-axis-refusal-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
case "$MIXER_AXIS_OUT" in
  *$'\n'*|*$'\r'*) printf 'Invalid output path line break\n' >&2; exit 1 ;;
esac
printf 'MIXER_AXIS_OUT=%s\n' "$MIXER_AXIS_OUT" >> "$GITHUB_ENV"
```

The export supplies the current preflight process. The quoted `GITHUB_ENV`
append supplies subsequent steps; refusing both line breaks protects its
single-line record format. The output remains the same runner temporary
directory and run/attempt suffix. The upload step retains its original exact
`runner.temp` expression in valid step `with` scope, so it can still attempt to
retain evidence even when initialization or preflight fails. No new step,
custody mechanism, retry, limit increase or runtime authority is introduced.

The complete draft has four explicit expression-bearing lines containing eight
expressions: two `inputs` uses in job `env`; three `github` uses in artifact
`with.name`; and `runner` plus two `github` uses in artifact `with.path`.
The job's implicit `github` condition and all three `always()` step conditions
are preserved byte for byte. This placement review is source evidence, not a
general YAML/schema-validation result. GitHub must validate the later installed
workflow before any hosted execution can be claimed.

The only other executable-source change is the verifier's `admissionRelative`
and the workflow's corresponding sibling paths. `verify.mjs` otherwise retains
the corrected parser and all source/result guards byte for byte. The required
test roster, file-limit helper and inherited `controls.mjs` are exact copies.
The inherited forty-seven passing synthetic parser controls belong to the prior
packet and were **not rerun for this sibling**. `expression-controls.mjs` adds
eighteen reviewable pure source/data controls, including the actual old failure,
export/persistence/line-break/path regressions and unchanged command, limits,
event, attempt, template and verifier boundaries. That script is **UNRUN** and
requires root review before execution under the existing active-API guard.
No new harness is supplied or invoked.

The package is still the exact 27 files and 284,605 bytes in
`verification/android-axis-refusal-host-preparation/package`, pinned by manifest
`601b9722df4f42c6649f0e0b6943fe5e3ad96bc6ebeeeecc186da475875e5782`
and projection
`257ed4dfa93d43b15d4bfe2d51372d261e4fec5fd9e80c3f1ca62b1967a3a793`.
The unchanged design selects macOS 15, Xcode 26.3 build 17C529 and the exact
existing Apple tool verifier. It retains `ulimit -f 65536`, the required
67,108,864-byte soft/hard readback, 8,388,608-byte accepted cap per stream,
one unfiltered SwiftPM test command with `--jobs 2`, the original time bounds,
exact pre/post source identities, eight XCTest methods, eleven Swift Testing
methods and both separate framework summaries. Scratch remains retained;
successful host execution cannot establish owned process-group absence,
separate pipe EOF, descendant custody or runner disposal.

`source-delta.json` records the narrow transformation. `source-checks.json`
records fs/crypto-only source comparisons and the unchanged installed/prior
bytes. `admission-manifest.json` covers its explicitly listed payload files;
it excludes itself and `receipt.json` so the closure has no circular hash.
The receipt binds that final manifest. The false root template binds the final
workflow hash while source revision and run ID remain null; no committed hash
tries to contain its own source revision.

Root owns the next integration: finish the independent package continuation,
review this source correction, deliver the selected sibling, and install
`workflow.draft.yml` byte for byte only when that delivery boundary permits.
After the push, root must inspect GitHub's actual validation, bind the delivered
revision in selected dispatch data, and decide the sole bounded manual axis
dispatch. Attempt 1 and the one-dispatch ceiling remain unchanged. All nineteen
real host tests are still **UNRUN**. Source/schema review cannot substitute for
their compiler, discovery and actual result evidence. SDK/engine integration,
Java/Android, native/UI/capture, disconnected phones, immutable external FieldLog,
OTA, production/store/customer and GA checks retain their existing holds.
