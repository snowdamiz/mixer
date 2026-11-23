"""S3 host-only replay. Preserve exact run scratch if command custody is uncertain."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRATCH = ROOT / "verification/local"
TOOLCHAIN = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
SDK = Path.home() / ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_wasm.artifactbundle/swift-6.3.3-RELEASE_wasm/wasm32-unknown-wasip1"
SOURCES = [
    HERE / name for name in
    ("StateRuntime.swift", "FrameRuntime.swift", "Views.swift", "SharedScreen.swift", "Journey.swift", "Replay.swift")
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apple-typecheck", action="store_true", help="Compile Apple sources without a device")
    options = parser.parse_args()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="swiftui-s3-", dir=SCRATCH))
    work = run / "work"
    work.mkdir()
    environment = os.environ | {"TMPDIR": str(work), "CLANG_MODULE_CACHE_PATH": str(work / "modules")}
    commands = {}
    custody_uncertain = False
    inputs = [*SOURCES, HERE / "oracle.mjs", Path(__file__)]
    scope = {"S3n": "macOS Swift executable", "S3g": "full Swift WASI reactor on Node"}
    if options.apple_typecheck:
        inputs += [HERE / "AppleApp.swift", HERE / "AppleUITests.swift",
                   HERE / "AppleDifferential.xcodeproj/project.pbxproj"]
        scope = {"Apple": "arm64 iOS Simulator SDK typecheck at deployment target 17.0"}
    receipt = {
        "base": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "sources": {file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                    for file in inputs},
        "commands": commands,
        "scope": scope
    }
    print(run, flush=True)

    def save():
        (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def hold(reason):
        receipt["hold"] = reason
        save()
        print(reason, flush=True)
        os._exit(74)

    def call(name, *argv):
        nonlocal custody_uncertain
        arguments = list(map(str, argv))
        command = {"argv": arguments, "timeoutSeconds": 90}
        commands[name] = command
        save()
        with (run / f"{name}.log").open("wb") as log:
            custody_uncertain = True
            try:
                process = subprocess.Popen(arguments, cwd=work, env=environment, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
            except (OSError, subprocess.SubprocessError) as error:
                hold(f"No admitted process identity for {name}: {error}")
            command.update(pid=process.pid, pgid=process.pid)
            save()
            try:
                command["exit"] = process.wait(timeout=90)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                hold(f"Interrupted with unconfirmed terminal custody for {name}")
        try:
            os.killpg(process.pid, 0)
        except OSError as error:
            if error.errno != errno.ESRCH:
                hold(f"Could not establish owned group absence for {name}: {error}")
        else:
            hold(f"Owned group still present after {name}")
        command["groupAbsent"] = True
        custody_uncertain = False
        save()
        if command["exit"] != 0:
            raise SystemExit(f"{name} returned {command['exit']}; see {run / (name + '.log')}")
        return (run / f"{name}.log").read_bytes()

    try:
        call("host-version", "/usr/bin/swiftc", "--version")
        if options.apple_typecheck:
            call("xcode-version", "/usr/bin/xcodebuild", "-version")
            sdk = Path(call("ios-sdk", "/usr/bin/xcrun", "--sdk", "iphonesimulator", "--show-sdk-path").decode().strip())
            frameworks = sdk.parents[1] / "Library/Frameworks"
            swift = ["/usr/bin/swiftc", "-target", "arm64-apple-ios17.0-simulator", "-sdk", sdk,
                     "-swift-version", "6", "-module-cache-path", work / "modules", "-typecheck"]
            call("apple-app", *swift, "-DAPPLE_SWIFTUI", "-parse-as-library",
                 HERE / "AppleApp.swift", HERE / "SharedScreen.swift")
            call("apple-journey", *swift, "-F", frameworks, HERE / "AppleUITests.swift", HERE / "Journey.swift")
            call("apple-project", "/usr/bin/plutil", "-lint", HERE / "AppleDifferential.xcodeproj/project.pbxproj")
            print("Apple app and UI test source typechecks and project plist lint passed.")
            return
        host = work / "s3-host"
        call("s3n-build", "/usr/bin/swiftc", "-swift-version", "6", "-parse-as-library",
             "-module-cache-path", work / "modules", *SOURCES, "-o", host)
        native = call("s3n-run", host)
        print(native.decode(), end="")
        call("guest-version", TOOLCHAIN / "swiftc", "--version")
        call("linker-version", TOOLCHAIN / "wasm-ld", "--version")
        call("node-version", "node", "--version")
        resource = SDK / "swift.xctoolchain/usr/lib/swift_static"
        guest = work / "s3.wasm"
        call("s3g-build", TOOLCHAIN / "swiftc", "-swift-version", "6", "-target", "wasm32-unknown-wasip1",
             "-sdk", SDK / "WASI.sdk", "-resource-dir", resource,
             "-module-cache-path", work / "modules",
             "-Xclang-linker", "-resource-dir", "-Xclang-linker", resource / "clang",
             "-static-stdlib", "-parse-as-library", "-Osize", "-gnone", "-DS3_GUEST",
             "-Xclang-linker", "-mexec-model=reactor", "-Xlinker", "--export=mixer_s3_replay",
             "-Xlinker", "--strip-all", *SOURCES, "-o", guest)
        wasm = call("s3g-run", "node", "--no-warnings", HERE / "oracle.mjs", guest)
        expected_lines = 15
        if native != wasm or len(wasm.splitlines()) != expected_lines:
            raise SystemExit(f"Native and guest traces differ or are incomplete. See {run}.")
        receipt["trace"] = {"lines": expected_lines, "identical": True, "sha256": hashlib.sha256(wasm).hexdigest()}
        receipt["guestArtifact"] = {"bytes": guest.stat().st_size, "sha256": hashlib.sha256(guest.read_bytes()).hexdigest()}
        print(f"S3n and S3g emitted {expected_lines} identical lines.")
    finally:
        if not custody_uncertain:
            shutil.rmtree(work)
            receipt["disposableWorkRemoved"] = True
            save()


if __name__ == "__main__":
    main()
