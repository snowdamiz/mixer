"""Single in-process, host-only test receipt. No compiler/child/native launch."""
from pathlib import Path
import contextlib
import datetime
import hashlib
import io
import json
import os
import platform
import sys
import time
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = ("input_model.py", "test_input_model.py", "existing-owner-candidate.inc.rs", "run_offline_once.py")
INPUTS = (
    "AGENTS.md", "mixer-product-plan.md",
    "verification/swift-guarded-snapshot-outer-parent-source/source-custody.json",
    "verification/swift-guarded-snapshot-outer-parent-source/source-manifest.json",
    "verification/swift-guarded-snapshot-outer-parent-source/outer-parent.inc.rs",
    "verification/swift-guarded-snapshot-outer-parent-source/overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs",
    "verification/swift-guarded-snapshot-outer-parent-source/contracts.json",
    "verification/swift-guarded-snapshot-outer-parent-independent/README.md",
    "verification/swift-guarded-snapshot-outer-parent-work-storage/required-input-contracts.json",
    "verification/swift-guarded-snapshot-outer-parent-work-storage/candidate.json",
    "verification/swift-guarded-snapshot-outer-parent-work-storage-independent/README.md",
    "verification/swift-guarded-snapshot-host-composition/overlay/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs",
    "verification/swift-guarded-snapshot-host-composition/host-support-manifest.json",
    "verification/swift-guarded-snapshot-host-composition/prepare.py",
    "verification/swift-guarded-snapshot-host-composition/run.py",
    "verification/swift-real-profile-loader-binding/run_checks.py",
    "verification/swift-real-profile-loader-binding/source-preimages/genuine.wasm",
    "verification/swift-real-profile-loader-binding/build-preimage-optimized.bin",
)


def row(path, relative_to):
    data = path.read_bytes()
    return dict(path=path.relative_to(relative_to).as_posix(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    if len(sys.argv) != 2 or not sys.argv[1].replace("-", "").isalnum():
        raise SystemExit("usage: run_offline_once.py unique-attempt-label")
    attempt = HERE / "attempts" / sys.argv[1]
    attempt.mkdir(parents=True, exist_ok=False)
    source_before = [row(HERE / name, HERE) for name in SOURCES]
    inputs = [row(ROOT / name, ROOT) for name in INPUTS]
    write(attempt / "source-manifest.json", source_before)
    write(attempt / "input-custody.json", inputs)
    # Preserve exact sources for failed harness investigations and later replay.
    for name in SOURCES:
        (attempt / name).write_bytes((HERE / name).read_bytes())
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    start = time.monotonic()
    output = io.StringIO()
    result = None
    error = None
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_input_model.py")
            result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    except BaseException as caught:
        error = repr(caught)
    source_after = [row(HERE / name, HERE) for name in SOURCES]
    same = source_before == source_after
    data = output.getvalue().encode()
    (attempt / "stdout").write_bytes(data)
    (attempt / "stderr").write_bytes((error or "").encode())
    success = error is None and result is not None and result.wasSuccessful() and same
    receipt = dict(
        schema=1, status="host-only-input-model-pass" if success else "host-only-input-model-failure",
        started_utc=started, elapsed_seconds=time.monotonic() - start,
        argv=[sys.executable, *sys.argv], cwd=os.getcwd(), tool="CPython standard library unittest/hashlib",
        python_version=sys.version, python_executable=dict(path=str(Path(sys.executable).resolve()),
            bytes=Path(sys.executable).resolve().stat().st_size,
            sha256=hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()),
        platform=platform.platform(), source_tree_digest=hashlib.sha256(json.dumps(source_before, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        base_source146_tree="27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3",
        source_unchanged_during_run=same, tests_run=None if result is None else result.testsRun,
        failures=None if result is None else len(result.failures), errors=None if result is None else len(result.errors),
        skipped=None if result is None else len(result.skipped), exception=error, exit_code=0 if success else 1,
        stdout=row(attempt / "stdout", attempt), stderr=row(attempt / "stderr", attempt),
        scope="in-process immutable-byte/format model and frozen source custody only",
        synthetic_records_not_product_inputs=True, Rust_fragment_compiled=False,
        compiler_or_actual_loader_or_executable_launched=False, owned_child_processes_started=0,
        runtime_UI_capture_native_simulator_emulator_device_started=False,
        global_process_inventory_taken=False, cleanup="no child/native/scratch resources created",
        all_three_selectors="Pending", operational_grant=False, GA=False)
    write(attempt / "receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "tests_run", "failures", "errors", "elapsed_seconds", "source_tree_digest", "operational_grant")}))
    if not success:
        print(output.getvalue())
        if error:
            print(error)
    raise SystemExit(receipt["exit_code"])


if __name__ == "__main__":
    main()
