#!/usr/bin/env python3
"""Build both localized Wasm guests and drive the selected-task fixture on macOS."""
import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RECIPE = Path(__file__).resolve().parent
REPO = RECIPE.parents[3]
PAIR = RECIPE.parents[1] / "fieldlog-android-engine-pair"
PINS = json.loads((RECIPE / "pins.json").read_bytes())
MIB = 1024 ** 2
SWIFT = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
RUST = Path.home() / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
DEVELOPER = Path("/Applications/Xcode_26.6.app/Contents/Developer")
SDK = DEVELOPER / "Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory(paths):
    lines = (f"{sha(path)}  {name}\n" for name, path in sorted(paths.items(), key=lambda item: Path(item[0])))
    return hashlib.sha256("".join(lines).encode()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def run(*argv, cwd=None, env=None):
    subprocess.run(argv, cwd=cwd, env=env, check=True)


def output(*argv, cwd=None, env=None):
    return subprocess.check_output(argv, cwd=cwd, env=env, text=True).strip()


def source_binding(campaign):
    scratch = campaign / "scratch"
    app = scratch / "app"
    guest = scratch / "guest-source"
    vm = scratch / "pair-new/vm"
    # Reproduce the final, source-only sed step in the maintained Java recipe.
    manifest = app / "fieldlog/Integrations/GeneratedReport/Platforms/Android/AndroidManifest.xml"
    base = manifest.read_bytes().replace(b"<uses-sdk", b'<uses-permission android:name="android.permission.INTERNET" />\n  <uses-sdk')
    base = base.replace(b"<application ", b'<application android:networkSecurityConfig="@xml/checklist_network" ')
    (app / "manifest-base.xml").write_bytes(base)
    paths = [app / name for name in ("android-package/Package.swift", "android-package/Package.resolved",
                                     "compile-android-java.sh", "offline-env.sh", "manifest-base.xml")]
    for directory in ("fieldlog/Integrations/GeneratedReport", "fieldlog/Integrations/InstalledGuest",
                      "mixer/sdk", "mixer/capability-activation", "mixer/runtime-identity", "mixer/updates",
                      "mixer/experimental-capability-runtime", "mixer/native/android",
                      "mixer/verification/android-binding-stage4/host-bridge", "mixer/vm/include", "prepared"):
        paths.extend(path for path in (app / directory).rglob("*") if path.is_file())
    observed = {"fileCount": len(paths), "sha256": inventory({str(path.relative_to(app)): path for path in paths})}
    require(observed == PINS["consumer"], f"consumer source drift: {observed}")

    sources = {path.name: path for path in guest.iterdir() if path.is_file()}
    sources["selected-task.patch"] = PAIR / "overlays/selected-task.patch"
    require(inventory(sources) == PINS["selectedGuestSHA256"], "selected-task source drift")
    patch = RECIPE / "localized-guest.patch"
    env = os.environ | {"GIT_CEILING_DIRECTORIES": str(scratch), "GIT_NO_LAZY_FETCH": "1"}
    run("/usr/bin/git", "apply", "--whitespace=error", patch, cwd=guest, env=env)
    sources[patch.name] = patch
    require(inventory(sources) == PINS["localizedGuestSHA256"], "localized source drift")

    engine_revision, vm_tree = (scratch / "engine-new.txt").read_text().splitlines()
    engine = PINS["engine"]
    require((engine_revision, vm_tree) == (engine["revision"], engine["vmTree"]), "VM source drift")
    write(campaign / "binding.json", {
        "consumer": observed, "selectedGuestSHA256": PINS["selectedGuestSHA256"],
        "localizedGuestSHA256": PINS["localizedGuestSHA256"],
        "localizedGuestFiles": {name: sha(path) for name, path in sorted(sources.items())},
        "storageAdapterSHA256": sha(app / "fieldlog/Integrations/InstalledGuest/TaskStorage.swift"),
        "rendererSHA256": sha(app / "fieldlog/Integrations/GeneratedReport/Platforms/Android/Java/dev/fieldlog/generatedr90/androidhost/ChecklistPanel.java"),
        "vmHeaderSHA256": sha(vm / "include/mixer_vm_guest_ui_deferred.h"),
    })


def build(campaign):
    scratch = campaign / "scratch"
    guest = scratch / "guest-source"
    host = scratch / "host-probe"
    vm = scratch / "pair-new/vm"
    app = scratch / "app"
    host.mkdir()
    swift = SWIFT / "swiftc"
    cache = scratch / "module-cache"
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("SWIFT", "CARGO_", "RUST", "DYLD_", "XCRUN_", "LLVM_"))
           and key not in {"SDKROOT", "TOOLCHAINS", "MACOSX_DEPLOYMENT_TARGET"}}
    env.update(DEVELOPER_DIR=str(DEVELOPER), SDKROOT=str(SDK), CLANG_MODULE_CACHE_PATH=str(cache),
               XDG_CACHE_HOME=str(scratch / "xdg-cache"), CARGO_HOME=str(scratch / "cargo-home"),
               RUSTC=str(RUST / "rustc"), CARGO_INCREMENTAL="0",
               SWIFT_DRIVER_SWIFT_FRONTEND_EXEC=str(SWIFT / "swift-frontend"))

    tools = {}
    for name, pin in PINS["tools"].items():
        sdk_descriptor = name == "macOS26.5 SDKSettings.json"
        path = SDK / "SDKSettings.json" if sdk_descriptor else (RUST if name in ("rustc", "cargo") else SWIFT) / name
        require(sha(path) == pin, f"tool digest differs: {path}")
        version = json.loads(path.read_bytes())["Version"] if sdk_descriptor else output(path, "--version", env=env)
        tools[name] = {"file": path.resolve().name, "sha256": pin, "version": version}
    tools["macOS"] = output("/usr/bin/sw_vers")
    tools["git"] = output("/usr/bin/git", "--version")
    tools["python"] = output(sys.executable, "--version")
    write(campaign / "tools.json", tools)

    run(SWIFT / "clang", "--target=wasm32-unknown-none", "-Oz", "-c", "CapabilityImports.c",
        "-o", scratch / "capability.o", cwd=guest, env=env)
    for label, pin in PINS["payloads"].items():
        obj = scratch / f"{label}.o"
        wasm = campaign / f"{label}.wasm"
        defines = ["-D", "REQUIRE_REVIEW"] if label == "reviewed" else []
        run(swift, "-target", "wasm32-unknown-none-wasm", "-enable-experimental-feature", "Embedded",
            "-enable-experimental-feature", "Extern", "-whole-module-optimization", "-Osize", "-parse-as-library",
            "-Xfrontend", "-disable-stack-protector", "-Xfrontend", "-disable-incremental-llvm-codegen",
            "-module-cache-path", cache, *defines, "-emit-object", "Guest.swift", "TaskWire.swift", "-o", obj,
            cwd=guest, env=env)
        run(SWIFT / "wasm-ld", "--no-entry", "--gc-sections", "--strip-all", "-z", "stack-size=16384",
            "--max-memory=65536", "--export=mixer_guest_ui_start_v1", "--export=mixer_guest_ui_hydrate_v1",
            "--export=mixer_guest_ui_event_v1", "--export=mixer_guest_capability_ready_v1",
            obj, scratch / "capability.o", "-o", wasm, env=env)
        require({"sha256": sha(wasm), "bytes": wasm.stat().st_size} == pin, f"unexpected bytes: {wasm}")

    target = scratch / "vm-build"
    run(RUST / "cargo", "build", "--manifest-path", vm / "Cargo.toml", "--offline", "--locked", "--release",
        "--jobs", "4", "--features", "experimental-capability-native", "--lib", "--target-dir", target, env=env)
    archive = target / "release/libmixer_vm.a"
    require(sha(archive) == PINS["engine"]["hostArchiveSHA256"], "host VM archive drift")

    sdk_sources = app / "mixer/sdk/Sources"
    fieldlog = app / "fieldlog/Integrations"
    fieldlog_sources = fieldlog / "GeneratedReport/Sources"
    io = sdk_sources / "MixerCapabilities/NativeIO"
    maps = {"MixerCapabilityIO": io / "include/MixerCapabilityIO.h",
            "MixerVM": vm / "include/mixer_vm_guest_ui_deferred.h"}
    for name, header in maps.items():
        (host / name).mkdir()
        (host / name / "module.modulemap").write_text(f'module {name} {{ header "{header}" export * }}\n')
    lock = host / "lock.o"
    host_target = "arm64-apple-macosx26.0"
    run(SWIFT / "clang", "-target", host_target, "-isysroot", SDK, "-I", io / "include",
        "-c", io / "lock.c", "-o", lock, cwd=host, env=env)
    flags = ["-sdk", SDK, "-target", host_target, "-swift-version", "6", "-module-cache-path", cache,
             "-I", host, "-I", host / "MixerVM", "-I", host / "MixerCapabilityIO"]
    libraries = []
    for module, parent in (("MixerCore", sdk_sources), ("MixerCapabilities", sdk_sources),
                           ("FieldLogModels", fieldlog_sources), ("FieldLogStorage", fieldlog_sources)):
        library = host / f"lib{module}.a"
        run(swift, *flags, "-emit-module", "-emit-library", "-static", "-module-name", module,
            *sorted((parent / module).glob("*.swift")), "-o", library, cwd=host, env=env)
        libraries.append(library)
    run(swift, *flags, "-parse-as-library", RECIPE / "ChecklistProbe.swift",
        fieldlog / "InstalledGuest/TaskStorage.swift", lock, *libraries, archive, "-framework", "Security",
        "-o", campaign / "probe", cwd=host, env=env)


def replay(export_dir):
    base = PINS["mixerBase"]
    git = ("/usr/bin/git", "-C", REPO)
    env = os.environ | {"GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0"}
    require(output(*git, "rev-parse", f"{base}^{{tree}}", env=env) == PINS["mixerBaseTree"], "Mixer base drift")
    require(output(*git, "rev-parse", f"{base}:{PAIR.relative_to(REPO)}", env=env) ==
            PINS["maintainedPairTree"], "maintained pair tree drift")
    run(*git, "diff", "--quiet", base, "--", PAIR.relative_to(REPO), env=env)

    # Reuse the maintained runner's bounded process and cleanup contract.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("fieldlog_pair_runner", PAIR / "run.py")
    pair = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pair)
    os.umask(0o077)
    parent = REPO / "verification/local"
    parent.mkdir(parents=True, exist_ok=True)
    initial_free = shutil.disk_usage(parent).free
    require(initial_free >= pair.STOP_FREE + 600 * MIB, "insufficient disk for bounded local fixture")
    campaign = Path(tempfile.mkdtemp(dir=parent, prefix="fieldlog-android-localized."))
    custody = pair.Custody()
    commands = {}
    observations = {}
    largest_scratch_bytes = 0
    interrupted_compiler = False
    try:
        (campaign / "scratch/tmp").mkdir(parents=True)
        script = [sys.executable, "-B", __file__]
        steps = [
            ("prepare", ["/bin/bash", PAIR / "replay/prepare.sh", PAIR, REPO, campaign], 180),
            ("bind", [*script, "--phase", "bind", campaign], 30),
            ("build", [*script, "--phase", "build", campaign], 120),
            *((label, [campaign / "probe", label, campaign / f"{label}.wasm",
                       campaign / f"scratch/{label}-workspace"], 20) for label in PINS["payloads"]),
        ]
        for label, argv, deadline in steps:
            command_receipt = campaign / f"{label}.json"
            try:
                with redirect_stdout(sys.stderr):
                    pair.run(campaign, custody, label, argv, deadline)
            except BaseException:
                if label == "build":
                    # Swift may leave compiler work after an interrupted driver.
                    interrupted_compiler = True
                    if command_receipt.is_file():
                        exit_code = json.loads(command_receipt.read_bytes()).get("exit")
                        interrupted_compiler = exit_code is None or exit_code < 0
                raise
            result = json.loads(command_receipt.read_bytes())
            result["deadlineSeconds"] = deadline
            for key in ("minimumFreeBytes", "pid", "pgid"):
                result.pop(key)
            result["command"] = [arg.replace(str(campaign), "$WORK").replace(str(REPO) + "/", "") for arg in result["command"]]
            commands[label] = result
            largest_scratch_bytes = max(largest_scratch_bytes, sum(
                path.lstat().st_blocks * 512 for path in campaign.rglob("*") if path.is_file() and not path.is_symlink()))
            require(largest_scratch_bytes < 600 * MIB, "scratch exceeded budget")
            if label in PINS["payloads"]:
                observation = json.loads((campaign / f"{label}.log").read_bytes())
                # Retain rendered roles and strings without repeating the full UI tree.
                observation["frames"] = [
                    {"revision": frame["revision"],
                     **{node["id"]: next(iter(node["properties"].values())) for node in frame["root"]["children"]}}
                    for frame in observation["frames"]
                ]
                observations[label] = observation

        source = json.loads((campaign / "binding.json").read_bytes())
        recipe_files = {name: RECIPE / name for name in
                        ("README.md", "ChecklistProbe.swift", "localized-guest.patch", "pins.json", "replay.py")}
        receipt = {
            "requirement": "L02 / L08 §22.2.5",
            "status": "passed",
            "scope": "macOS host fixture: actual Mixer Wasm VM and public FieldLog repository/selected-task adapter",
            "observedUTC": datetime.now(timezone.utc).isoformat(),
            "recipeSHA256": inventory(recipe_files),
            "pins": {name: value for name, value in PINS.items() if name not in source.keys() | {"tools", "payloads"}},
            "source": source,
            "toolchain": json.loads((campaign / "tools.json").read_bytes()),
            "probeSHA256": sha(campaign / "probe"),
            "commands": commands,
            "payloads": PINS["payloads"],
            "observations": observations,
            "maxSampledAllocatedFileBytes": largest_scratch_bytes,
            "diskBudgetBytes": 600 * MIB,
            "pending": ["single signed APK and two same-runtime signed assignments", "Android 1x LTR / 1x RTL / 2x RTL",
                        "native tap and offline reopen", "independent review"],
        }
        if export_dir:
            export_dir.mkdir(mode=0o700)
            try:
                for label in PINS["payloads"]:
                    shutil.copyfile(campaign / f"{label}.wasm", export_dir / f"{label}.wasm")
                write(export_dir / "binding.json", {"recipeSHA256": receipt["recipeSHA256"],
                                                    "payloads": PINS["payloads"], **source})
            except BaseException:
                shutil.rmtree(export_dir)
                raise
    except BaseException:
        if custody.pending is None and not interrupted_compiler:
            for log in campaign.glob("*.log"):
                with log.open("rb") as stream:
                    stream.seek(max(0, log.stat().st_size - 3000))
                    print(f"{log.name}\n{stream.read().decode(errors='replace')}", file=sys.stderr)
        raise
    finally:
        if custody.pending is None and not interrupted_compiler:
            shutil.rmtree(campaign)
        else:
            stage = custody.pending or "interrupted host compiler"
            print(f"Retained {campaign}: terminal custody unresolved for {stage}", file=sys.stderr)
    receipt["cleanup"] = "owned command groups proved absent and scratch removed"
    print(json.dumps(receipt, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, help="fresh directory for an explicit Wasm handoff")
    parser.add_argument("--phase", choices=["bind", "build"], help=argparse.SUPPRESS)
    parser.add_argument("work", type=Path, nargs="?", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.phase:
        {"bind": source_binding, "build": build}[args.phase](args.work)
    else:
        replay(args.export_dir)
