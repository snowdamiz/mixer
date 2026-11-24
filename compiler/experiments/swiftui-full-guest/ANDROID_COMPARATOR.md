# Matched API 28 FieldLog comparator

The private arm64 shell executable loads the same Swift runtime libraries in
all three modes. `native` runs the bundled Swift journey, `ui256` runs the
pinned 32-import reactor through the owned VM, and `fixed34` exercises legacy
admission. Each launch uses a fresh process. The baseline uses VM revision
`1ee170500c73e3da935e1d1cbb4bbba77d24e8d8`. The optional deadline-window
packet uses `66195b5d6cc161f39df6af04cc086f7d0bd1975f` with
`MIXER_SWIFT_UI_DEADLINE_BATCH=1` set at build time. Both use the original
30,000 ms owner deadline, UI256 geometry, exact WASI grants and unchanged
validation budgets. The previous standalone 60-second replay is separate
evidence. [Standalone API 28 VM receipt](../../../verification/receipts/ui-platform-pivot-s2b-api28-20261123.json)

## Cross-build and run macOS controls

From the repository root, supply the retained directory containing the exact
`reactor-base.wasm` and `oracle.json` from the standalone Android and matched
iOS comparisons. Use Swift 6.3.3 with its Android SDK, NDK r27d, Rust 1.99.0
with the `aarch64-linux-android` target, and Xcode 26.6 for macOS.

```sh
script=compiler/experiments/swiftui-full-guest/build_android_comparator.py
python3 -B "$script" build s2b-matched "$S2_PAYLOAD_DIR" --deadline-window
run=verification/local/s2b-matched
packet="$run/artifacts/baseline"
```

Omit `--deadline-window` to build the baseline alone. The builder validates
the API 28 ELF identity and resolves `DT_NEEDED` recursively against the NDK
and Swift SDK. It checks that the optional variant has the identical runtime
library closure. Each packet contains the ELF, payload, oracle, manifest, and
runtime libraries. The command receipt includes split logs, tool versions,
source and artifact hashes, and three macOS controls per variant. The Android
linker's libc++ diagnostics stay in stderr.

## Replay on the root-owned AVD

Use the private API 28 arm64 AVD and ADB server. Set `OWNED_ADB_PORT` and
`OWNED_SERIAL` to their exact values, and `REMOTE` to a new private directory
under `/data/local/tmp` whose path contains only shell-safe characters. Create
and push the packet once per variant. The guest uses the Wasm file in its
working directory.

```sh
adb_owned() { adb -P "$OWNED_ADB_PORT" -s "$OWNED_SERIAL" "$@"; }
adb_owned shell "mkdir -m 700 '$REMOTE'"
adb_owned push "$packet/fieldlog-s2b" "$packet/reactor-base.wasm" "$packet/lib" "$REMOTE/"
adb_owned shell "cd '$REMOTE' && chmod 700 ./fieldlog-s2b && sha256sum ./fieldlog-s2b ./reactor-base.wasm ./lib/*"
```

Match the device hashes to `packet.json` before launch. Capture stdout, stderr
and exit status separately. Run each command only after observing termination
of the preceding process. A matching terminal marker and command status are
inputs to the parser. Root also verifies exact process exit and AVD cleanup.

```sh
capture() {
    mode=$1
    status=0
    adb_owned shell "cd '$REMOTE' && LD_LIBRARY_PATH=./lib timeout 165 ./fieldlog-s2b '$mode'" \
        > "$run/$mode.stdout" 2> "$run/$mode.stderr" || status=$?
    printf '%s\n' "$status" > "$run/$mode.exit"
}

capture native
capture ui256
capture fixed34

python3 -B "$script" check "$packet" \
    --native "$run/native.stdout" "$run/native.stderr" "$(cat "$run/native.exit")" \
    --ui256 "$run/ui256.stdout" "$run/ui256.stderr" "$(cat "$run/ui256.exit")" \
    --fixed34 "$run/fixed34.stdout" "$run/fixed34.stderr" "$(cat "$run/fixed34.exit")" \
    > "$run/baseline-api28.json"
```

Keep separate output names and a separate remote directory for the optional
packet. Use the same AVD boot and record the run order and system fingerprint.
If collecting more pairs, alternate the native and guest launch order. Remove
the owned staging directory and retire the private device under the existing
cleanup procedure.

The parser checks every frame against the pinned oracle. If the owner hits
`swift_run_deadline`, the comparison records the exact matching frame prefix,
the failed turn and closed ledgers. A deadline failure has no completed
steady sample. The outer command timeout is a harness bound and supplies no
owner-deadline evidence. A successful run samples steady RSS after one idle
second with the populated journey retained. Android current RSS comes from
`VmRSS` in `/proc/self/status`. Peak RSS comes from `getrusage(RUSAGE_SELF)`
and converts KiB to bytes. Startup runs from a monotonic sample at C `main` to
the first matching snapshot checkpoint. One pair measures the offscreen
journey. Signed activation, rendered UI, and the Section 20.2 p95 budgets
require their own evidence.
