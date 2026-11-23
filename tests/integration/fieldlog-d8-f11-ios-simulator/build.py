"""Build the isolated unsigned target without booting a Simulator."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from prepare import checked_replace as replace

HERE = Path(__file__).resolve().parent
LIMIT_KIB = 1_572_864


def setup(work):
    activation = work / "export/source/capability-activation"
    swift = activation / "Sources/F11Vertical"
    recipe = work / "export/source/capability-activation/verification/f11-native/Witness"
    recipe.mkdir(parents=True, exist_ok=True)
    shutil.copytree(HERE / "F11NativeWitness.xcodeproj", recipe / "F11NativeWitness.xcodeproj", dirs_exist_ok=True)
    for name in ("WitnessApp.swift", "WitnessInput.swift", "WitnessUITests.swift"):
        shutil.copyfile(HERE / name, recipe / name)
    (recipe / "Storage.swift").write_text((swift / "Control.swift").read_text().split("\n@main struct Control")[0] + "\n")
    actions = (swift / "HostActions.swift").read_text().split("    static func exercise(")[0]
    actions = replace(actions, "    private init(", "    init(")
    actions = replace(actions, "    private func perform(", "    func perform(")
    (recipe / "HostActions.swift").write_text(actions + "}\n")
    public = recipe / "SealedInput"
    public.mkdir(exist_ok=True)
    manifest = activation / "Package.swift"
    original = manifest.read_text()
    history = 'package.products.append(.library(name: "F11History", targets: ["FieldLogFeatures", "FieldLogStorage"]))\n'
    if history not in original:
        manifest.write_text(original + "\n" + history)
    return recipe


def allocated_kib(work):
    usage = subprocess.run(["du", "-sk", work], capture_output=True)
    # A compiler may atomically rename an intermediate while du scans it.
    if usage.returncode and not (usage.stdout and usage.stderr and all(
            line.endswith(b": No such file or directory") for line in usage.stderr.splitlines())):
        usage.check_returncode()
    return int(usage.stdout.split()[0])


def build(work, seconds):
    source = work / "export/source"
    recipe = setup(work)
    vm = work / "rust/aarch64-apple-ios-sim/release/libmixer_vm.a"
    vm_link = work / "libmixer_vm_capability_experimental.a"
    if not vm_link.exists():
        vm_link.symlink_to(vm)
    env = {**os.environ, "TMPDIR": str(work / "export/tmp") + "/",
           "CFFIXED_USER_HOME": str(work / "xcode-home"), "SWIFTCI_USE_LOCAL_DEPS": "1"}
    argv = ["/usr/bin/xcodebuild", "build-for-testing", "-project", str(recipe / "F11NativeWitness.xcodeproj"),
            "-scheme", "F11NativeWitness", "-configuration", "Debug", "-sdk", "iphonesimulator",
            "-destination", "generic/platform=iOS Simulator", "-derivedDataPath", str(work / "derived"),
            "-clonedSourcePackagesDirPath", str(work / "packages"), "-scmProvider", "system",
            "-skipPackageUpdates", "-disablePackageRepositoryCache", "-jobs", "12",
            "ARCHS=arm64", "SWIFT_ENABLE_EXPLICIT_MODULES=NO", "ONLY_ACTIVE_ARCH=NO",
            "CODE_SIGNING_ALLOWED=NO", "CODE_SIGNING_REQUIRED=NO", "COMPILER_INDEX_STORE_ENABLE=NO",
            "ENABLE_TESTABILITY=YES", "DEBUG_INFORMATION_FORMAT=dwarf", "SWIFT_EMIT_LOC_STRINGS=NO",
            "OTHER_SWIFT_FLAGS=$(inherited) -D MIXER_F11_IOS_FIXTURE -Xcc -I" + str(source / "vm/include"),
            "HEADER_SEARCH_PATHS=$(inherited) " + str(source / "vm/include"),
            "LIBRARY_SEARCH_PATHS=$(inherited) " + str(work)]
    start = time.monotonic()
    peak = 0
    with (work / "xcode.log").open("wb") as log:
        process = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while process.poll() is None:
                peak = max(peak, allocated_kib(work))
                if peak > LIMIT_KIB or time.monotonic() - start > seconds:
                    raise RuntimeError("Build budget exceeded")
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    continue
        except BaseException:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(process.pid, sig)
                    process.wait(timeout=3)
                except ProcessLookupError:
                    break
                except subprocess.TimeoutExpired:
                    continue
        absent = False
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            absent = True
        (work / "xcode-result.json").write_text(json.dumps({
            "argv": argv, "exit": process.returncode, "groupAbsent": absent, "pgid": process.pid,
            "peakKiB": peak, "elapsed": round(time.monotonic() - start, 2),
        }, indent=2) + "\n")
        if not absent:
            raise RuntimeError(f"Build process group {process.pid} is unresolved. Preserve {work}.")
    return process.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("--seconds", type=int, required=True)
    args = parser.parse_args()
    raise SystemExit(build(args.work.resolve(strict=True), args.seconds))
