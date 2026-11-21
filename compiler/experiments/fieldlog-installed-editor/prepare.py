#!/usr/bin/env python3
"""Build the compact Swift guests and the exact historical editor oracles."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys

HERE = Path(__file__).resolve().parent
MIXER = HERE.parents[2]
HISTORICAL = HERE.parent / "fieldlog-embedded-editor"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("historical", HISTORICAL / "replay.py")
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)


def prepare(work, fieldlog, tools, wasm_sdk, rejection_controls):
    shared_report = {"commands": []}
    shared = work / "tools"
    shared.mkdir()
    run = previous.Campaign(shared, shared_report).run
    imports = work / "Imports.o"
    unicode_tables = tools / "lib/swift/embedded/wasm32-unknown-none-wasm/libswiftUnicodeDataTables.a"
    libc = wasm_sdk / "WASI.sdk/lib/wasm32-wasip1/libc.a"
    try:
        run("imports", tools / "bin/clang", "--target=wasm32-unknown-none-wasm", "-Os",
            "-c", HERE / "Imports.c", "-o", imports)
        mac_sdk = run("mac-sdk", "/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path")
    finally:
        (work / "tools.json").write_text(json.dumps(shared_report, indent=2))

    def variant(label, pin):
        directory = work / label
        directory.mkdir()
        report = {"commands": [], "source": {}}
        campaign = previous.Campaign(directory, report)
        run = campaign.run

        def material(path, oid):
            raw = run(Path(path).stem, "git", "-C", fieldlog, "show", pin["fieldlog"] + ":" + path, binary=True)
            if hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != oid:
                raise RuntimeError(f"{label}: historical blob changed for {path}")
            report["source"][path] = previous.digest(raw)
            (directory / Path(path).name).write_bytes(raw)
            return raw

        try:
            opts = ("-D", "FIELDLOG_F06") if label == "F06" else ()
            def build_guest(name, extra_flags=()):
                run(f"compile-{name}", tools / "bin/swiftc", "-target", "wasm32-unknown-none-wasm",
                    "-enable-experimental-feature", "Embedded", "-enable-experimental-feature", "Extern",
                    "-whole-module-optimization", "-Osize", "-parse-as-library", "-Xfrontend",
                    "-disable-stack-protector", *opts, *extra_flags, "-emit-object", HISTORICAL / "EditorBoundary.swift",
                    *(HERE / (part + ".swift") for part in ("Reduction", "EditorWire", "Document", "Guest")),
                    "-o", directory / f"{name}.o")
                exports = ("mixer_guest_ui_start_v1", "mixer_guest_ui_event_v1", "mixer_guest_capability_ready_v1")
                run(f"link-{name}", tools / "bin/wasm-ld", "--fatal-warnings", "--no-entry", "--gc-sections",
                    "--strip-all", "-z", "stack-size=32768", "--max-memory=4194304",
                    *("--export=" + export for export in exports), directory / f"{name}.o", imports, unicode_tables, libc,
                    "-o", directory / f"{name}.wasm")
                payload = (directory / f"{name}.wasm").read_bytes()
                return {"bytes": len(payload), "sha256": previous.digest(payload)}

            report["guest"] = build_guest("editor")
            if rejection_controls and label == "F06":
                report["rejectionControls"] = {
                    name: build_guest(name, ("-D", flag))
                    for name, flag in (("absent-saving", "FIELDLOG_EDITOR_TEST_ABSENT_SAVING"),
                                       ("rejected-saving", "FIELDLOG_EDITOR_TEST_REJECTED_SAVING"))
                }

            for path, oid in {
                **pin["files"],
                "Sources/FieldLogModels/Workspace.swift": previous.MODEL,
                "Sources/FieldLogStorage/WorkspaceRepository.swift": previous.STORAGE,
                previous.FEATURE + "TaskEditor.swift": previous.EDITOR,
            }.items():
                raw = material(path, oid)
                if path == "Package.swift" and pin["sdk"].encode() not in raw:
                    raise RuntimeError(f"{label}: FieldLog SDK pin mismatch")
            if run("sdk-tree", "git", "-C", MIXER, "rev-parse", pin["sdk"] + ":sdk") != pin["sdkTree"]:
                raise RuntimeError(f"{label}: historical SDK tree mismatch")
            report["pins"] = pin
            report["sdkArchiveSHA256"] = campaign.archive("sdk-source", pin["sdk"], directory,
                                                          "sdk/Sources/MixerCore", "sdk/Sources/MixerUI")
            app_modules = {"FieldLogModels": "Workspace.swift", "FieldLogStorage": "WorkspaceRepository.swift"}
            objects = []
            swift = ("/usr/bin/swiftc", "-target", f"{platform.machine()}-apple-macos14.0", "-sdk", mac_sdk,
                     "-swift-version", "6", "-whole-module-optimization",
                     "-parse-as-library", "-package-name", "Mixer", "-I", directory)
            for name in ("MixerCore", "MixerUI", *app_modules):
                files = ([directory / app_modules[name]] if name in app_modules else
                         sorted((directory / "sdk/Sources" / name).glob("*.swift")))
                obj = directory / (name + ".o")
                run(name, *swift, "-module-name", name, "-emit-module", "-emit-module-path",
                    directory / (name + ".swiftmodule"), "-emit-object", *files, "-o", obj)
                objects.append(obj)
            run("build-oracle", *swift, directory / "TaskEditor.swift", directory / "TaskEditorPresentation.swift",
                HERE / "Oracle.swift", *objects, "-o", directory / "oracle")
            run("oracle", directory / "oracle", directory / "trace.json", timeout=20)
            report["traceSHA256"] = previous.digest((directory / "trace.json").read_bytes())
        finally:
            (work / (label + ".json")).write_text(json.dumps(report, indent=2))

    with ThreadPoolExecutor(max_workers=len(previous.HISTORY)) as executor:
        jobs = [executor.submit(variant, label, pin) for label, pin in previous.HISTORY.items()]
        failures = [job.exception() for job in jobs]
        if any(failures):
            raise RuntimeError(" / ".join(str(error) for error in failures if error))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--fieldlog", required=True, type=Path)
    parser.add_argument("--tools", required=True, type=Path)
    parser.add_argument("--wasm-sdk", required=True, type=Path)
    parser.add_argument("--rejection-controls", action="store_true", help="also build the negative F06 test inputs")
    args = parser.parse_args()
    prepare(args.work.resolve(), args.fieldlog.resolve(), args.tools.resolve(), args.wasm_sdk.resolve(),
            args.rejection_controls)
