#!/usr/bin/env python3
"""Build and run the private, signed F05 editor against offline source projections."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "compiler"))
from qualification_support import CommandRecorder, clean_environment, digest

HISTORICAL = "70f3aa1d28f29e7c327a17fd46199480d41ca749"
FRAME = "bee22bb11b73e5f0b93d82c7e8e812eaae8f2b02537c5f1b4017b241a1bfe419"
LEGACY_RUNTIME = "a036a33ea17934eff13e16948aa210eab4f778887d95e0a950da980570ef4bf1"
LIMIT = 800 * 1024 * 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("output", "fieldlog", "frame"):
        parser.add_argument("--" + field, type=lambda path: Path(path).resolve(), required=True)
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("the F05 signed host probe requires macOS")
    if digest(args.frame) != FRAME:
        parser.error("frame must match the historical F05 corpus capture")
    os.umask(0o077)
    out = args.output
    out.mkdir()
    for child in ("logs", "tmp", "lib", "build", "host"):
        (out / child).mkdir()
    env = clean_environment()
    env.update(TMPDIR=str(out / "tmp"), SWIFTCI_USE_LOCAL_DEPS="1", GIT_TERMINAL_PROMPT="0",
               GIT_ALLOW_PROTOCOL="file", SWIFTPM_MODULECACHE_OVERRIDE=str(out / "modules"))
    tools = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
    rust = Path.home() / ".rustup/toolchains/stable-aarch64-apple-darwin/bin"
    env["PATH"] = str(rust) + ":" + env.get("PATH", "/usr/bin:/bin")
    git, swift = Path("/usr/bin/git"), Path("/usr/bin/swift")
    commands = []
    receipt = {"status": "FAILED", "commands": commands, "frameSHA256": FRAME, "fieldLogRevision": HISTORICAL}
    recorder = CommandRecorder(out / "logs", commands, out, log_limit=2 * 1024 * 1024)

    def run(name, *argv, timeout=60):
        return recorder.run(name, argv, env=env, timeout=timeout).strip()

    def capture(name, repo, revision, destination, *paths):
        tar = out / (name + ".tar")
        run(name, git, "-C", repo, "archive", "--format=tar", "-o", tar, revision, *paths)
        receipt.setdefault("projectionSHA256", {})[name] = digest(tar)
        destination.mkdir(exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(tar.read_bytes())) as archive:
            archive.extractall(destination, filter="data")
        tar.unlink()

    def measure():
        size = int(run("scratch-" + str(len(commands)), "/usr/bin/du", "-sk", out).split()[0]) * 1024
        receipt["maxObservedScratchBytes"] = max(receipt.get("maxObservedScratchBytes", 0), size)
        if size > LIMIT:
            raise RuntimeError("800 MiB scratch limit exceeded")

    try:
        revision = run("revision", git, "-C", ROOT, "rev-parse", "HEAD")
        receipt["mixerRevision"] = revision
        capture("mixer-projection", ROOT, revision, out, "sdk/Package.swift", "sdk/Sources",
                "updates/Package.swift", "updates/Sources", "experimental-capability-runtime/Package.swift",
                "experimental-capability-runtime/Sources", "vm/Cargo.toml", "vm/Cargo.lock", "vm/src", "vm/include",
                "vm/examples/taskeditor_owned_command.rs")
        capture("fieldlog-projection", args.fieldlog, HISTORICAL, out / "fieldlog", "Sources/FieldLogModels", "Sources/FieldLogStorage")
        paths = ROOT / "sdk/Package.resolved"
        for pin in json.loads(paths.read_bytes())["pins"]:
            name = pin["identity"]
            cache = Path.home() / "Library/Caches/org.swift.swiftpm/repositories"
            repo, = cache.glob(name + "-*")
            capture(name + "-projection", repo, pin["state"]["revision"], out / name)
        for relative in ("sdk/Package.swift", "updates/Package.swift"):
            path = out / relative
            contents = path.read_text()
            locator = '.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")'
            if contents.count(locator) != 1:
                raise RuntimeError("Unexpected Swift Crypto locator")
            path.write_text(contents.replace(locator, '.package(path: "../swift-crypto")'))

        receipt["experimentSHA256"] = {path.name: digest(path) for path in HERE.iterdir() if path.is_file()}
        run("private-exchange", git, "apply", "--unsafe-paths", HERE / "exchange.patch")
        shutil.copyfile(HERE / "Package.swift", out / "Package.swift")
        shutil.copyfile(HERE / "Host.swift", out / "host/Host.swift")
        receipt["tools"] = {
            "macOS": run("macos-version", "/usr/bin/sw_vers"),
            "swift": run("swift-version", swift, "--version"),
            "clang": run("clang-version", tools / "clang", "--version"),
            "rust": run("rust-version", rust / "rustc", "--version"),
            "linker": run("linker-version", tools / "wasm-ld", "--version"),
        }

        frame = args.frame.read_bytes()
        if frame.count(b'"accessibilityIdentifier":"task-title","disabled":false') != 1:
            raise RuntimeError("Historical task title anchor changed")
        vertical = frame.replace(b'"accessibilityIdentifier":"task-title","disabled":false',
                                 b'"accessibilityIdentifier":"task-title","axis":"vertical","disabled":false')
        run("compile-editor", tools / "clang", "--target=wasm32-unknown-unknown", "-std=c11", "-Oz",
            "-ffreestanding", "-fno-builtin", "-Wall", "-Wextra", "-Werror", "-c", HERE / "editor.c", "-o", out / "editor.o")
        receipt["guests"] = {}
        for name, raw in (("historical", frame), ("vertical", vertical)):
            (out / (name + ".json")).write_bytes(raw)
            (out / "editor-frame.json").write_bytes(raw)
            run("embed-" + name, tools / "clang", "--target=wasm32-unknown-unknown", "-c", HERE / "frame.s", "-o", out / "frame.o")
            payload = out / (name + ".wasm")
            run("link-" + name, tools / "wasm-ld", "--no-entry", "--strip-all", "-z", "stack-size=8192",
                "--initial-memory=65536", "--max-memory=65536", "--export=mixer_guest_ui_start_v1",
                "--export=mixer_guest_ui_event_v1", "--export=mixer_guest_capability_ready_v1",
                out / "editor.o", out / "frame.o", "-o", payload)
            receipt["guests"][name] = {"bytes": payload.stat().st_size, "sha256": digest(payload)}
        legacy = ROOT / "compiler/experiments/fieldlog-installed-guest"
        run("compile-legacy", tools / "swiftc", "-target", "wasm32-unknown-none-wasm",
            "-enable-experimental-feature", "Embedded", "-whole-module-optimization", "-Osize",
            "-parse-as-library", "-Xfrontend", "-disable-stack-protector", "-emit-object",
            legacy / "TaskCompletion.swift", legacy / "InstalledGuest.swift", "-o", out / "legacy.o")
        run("link-legacy", tools / "wasm-ld", "--no-entry", "--gc-sections", "--strip-all",
            "-z", "stack-size=16384", "--max-memory=65536", "--export=mixer_guest_ui_start_v1",
            "--export=mixer_guest_ui_event_v1", "--export=mixer_guest_capability_ready_v1",
            out / "legacy.o", "-o", out / "legacy.wasm")
        receipt["legacyControl"] = {
            "moduleSHA256": digest(out / "legacy.wasm"),
            "sourceSHA256": {name: digest(legacy / name) for name in ("TaskCompletion.swift", "InstalledGuest.swift")},
        }
        measure()

        run("owned-vm", rust / "cargo", "build", "--offline", "--locked", "--release", "--lib",
            "--features", "experimental-capability-native", "--manifest-path", out / "vm/Cargo.toml",
            "--target-dir", out / "rust", timeout=110)
        library = out / "rust/release/libmixer_vm.a"
        receipt["vmArchiveSHA256"] = digest(library)
        (out / "lib/libmixer_vm_capability_experimental.a").symlink_to(library)
        measure()

        flags = ["--package-path", out, "--scratch-path", out / "build", "--disable-dependency-cache",
                 "--jobs", "4", "-Xswiftc", "-gnone", "-Xcc", "-I" + str(out / "vm/include"),
                 "-Xlinker", "-L" + str(out / "lib")]
        run("host-build", swift, "build", *flags, timeout=150)
        measure()
        binary = Path(run("host-bin", swift, "build", *flags, "--show-bin-path")) / "EditorHost"
        identity = {key: receipt[key] for key in ("experimentSHA256", "projectionSHA256", "vmArchiveSHA256")}
        fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        receipt["observations"] = run("host-proof", binary, out, fingerprint, HISTORICAL, LEGACY_RUNTIME).splitlines()
        receipt["status"] = "PASS"
    finally:
        try:
            measure()
        finally:
            (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
