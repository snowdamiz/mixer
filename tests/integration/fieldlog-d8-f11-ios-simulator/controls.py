"""Compile the actual SDK and consumer across the three profile boundaries."""
from pathlib import Path
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def execute(argv):
    return subprocess.run(argv, text=True, capture_output=True, timeout=35)


def check(work):
    source = work / "export/source"
    rows = {}
    for label, sdk, target, defines, expected in [
        ("stock-simulator", "iphonesimulator", "arm64-apple-ios26.0-simulator", [], 1),
        ("f11-simulator", "iphonesimulator", "arm64-apple-ios26.0-simulator", ["MIXER_F11_IOS_FIXTURE"], 0),
        ("generic-device-explicit-define", "iphoneos", "arm64-apple-ios26.0", ["MIXER_F11_IOS_FIXTURE"], 1),
        ("macos-private", "macosx", "arm64-apple-macosx14.0", ["MIXER_PRIVATE_FIELDLOG_EDITOR"], 0),
    ]:
        folder = work / "controls" / label
        folder.mkdir(parents=True)
        sdk_root = subprocess.check_output(["xcrun", "--sdk", sdk, "--show-sdk-path"], text=True).strip()
        command = ["xcrun", "swiftc", "-target", target, "-sdk", sdk_root, "-swift-version", "6",
                   "-I", folder, "-module-cache-path", folder / "cache"]
        for define in defines:
            command += ["-D", define]
        for module, root in [("Crypto", source / "swift-crypto/Sources/Crypto"),
                             *((name, source / "sdk/Sources" / name) for name in ("MixerCore", "MixerUI", "MixerGuest"))]:
            args = ["-package-name", "mixer"]
            if module == "Crypto":
                args = ["-package-name", "swift_crypto", "-D", "CRYPTO_IN_SWIFTPM",
                        "-enable-experimental-feature", "CheckImplementationOnly"]
            result = execute(command + args + ["-parse-as-library", "-emit-module",
                "-module-name", module, "-emit-module-path", folder / (module + ".swiftmodule"),
                *sorted(root.rglob("*.swift"))])
            if result.returncode:
                raise RuntimeError(f"{label}/{module}: {result.stderr}")
        control = ["-typecheck", HERE / "ExchangeConstructor.swift"]
        stock = execute(command + ["-D", "F11_CONTROL_STOCK"] + control)
        private = execute(command + control)
        if stock.returncode or private.returncode != expected or (expected and
                ("fieldLogNoteFixtureGeneration" not in private.stderr or "argument label" not in private.stderr)):
            raise RuntimeError(f"{label}: stock={stock.stderr}, private={private.stderr}")
        rows[label] = {"target": target, "defines": defines, "stockConstructorExit": stock.returncode,
                       "privateConstructorExit": private.returncode,
                       "privateDiagnostic": private.stderr.splitlines()[0] if expected else None}
        print(json.dumps(rows[label]), flush=True)
    return rows


if __name__ == "__main__":
    work = Path(sys.argv[1]).resolve(strict=True)
    (work / "controls-result.json").write_text(json.dumps(check(work), indent=2) + "\n")
