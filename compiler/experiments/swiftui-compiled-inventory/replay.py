#!/usr/bin/env python3
"""Inventory the compiled S1 and S2 fixtures for the UP5 Section 7.2 experiment."""
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import sys
import tempfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
S1 = HERE.parent / "swiftui-module-naming"
S2 = HERE.parent / "swiftui-full-guest"
sys.path.insert(0, str(ROOT / "compiler"))
from qualification_support import CommandRecorder, clean_environment, digest, strict_json

TRIPLE = "wasm32-unknown-wasip1"
PIN = ROOT / "release/toolchain-candidate.json"
ANDROID_PIN = ROOT / "tests/integration/fieldlog-task-calculation/android-packaging/toolchain-pins.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def scan_graph(path):
    """Keep module kinds and edges, including Swift and Clang names that coincide."""
    scan = strict_json(path.read_text())
    rows = scan["modules"]
    modules = []
    for identity, details in zip(rows[::2], rows[1::2], strict=True):
        kind, = identity
        inputs = details["details"][kind]
        modules.append({
            "id": identity,
            "modulePath": details["modulePath"],
            "directDependencies": details["directDependencies"],
            "inputs": {key: inputs[key] for key in ("moduleInterfacePath", "moduleMapPath")
                       if key in inputs},
        })
    require(modules and modules[0]["id"] == {"swift": scan["mainModuleName"]},
            f"Unexpected root in dependency scan {path.name}")
    identities = {tuple(module["id"].items()) for module in modules}
    require(len(identities) == len(modules) and all(
        tuple(dep.items()) in identities for module in modules for dep in module["directDependencies"]
    ), f"Duplicate or unresolved dependency in {path.name}")
    return {"root": modules[0]["id"], "modules": modules}


def direct_imports(graph):
    return {name for entry in graph["modules"][0]["directDependencies"] for name in entry.values()}


def source_imports(*paths):
    # Deliberately lexical baseline over these exact fixture files.
    return sorted({name for path in paths for name in
                   re.findall(r"^import ([A-Za-z_][\w]*)", path.read_text(), re.MULTILINE)})


def execute(run, logs, work, report):
    s1 = runpy.run_path(str(S1 / "replay.py"))
    pin = strict_json(PIN.read_text())
    swift_pin = pin["swift"]
    version = swift_pin["version"]
    cross_toolchain = Path.home() / f"Library/Developer/Toolchains/swift-{version}-RELEASE.xctoolchain"
    cross_swift = cross_toolchain / "usr/bin/swiftc"
    apple = Path("/Applications/Xcode.app/Contents/Developer")
    cross = Path("/Applications/Xcode_26.6.app/Contents/Developer")
    apple_swift = apple / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc"
    apple_env = {"DEVELOPER_DIR": str(apple)}
    cross_env = {"DEVELOPER_DIR": str(cross)}
    xcrun = ("/usr/bin/xcrun", "--no-cache")
    versions = report["versions"] = {
        "revision": run("revision", "/usr/bin/git", "rev-parse", "HEAD").strip(),
        "tree": run("tree", "/usr/bin/git", "rev-parse", "HEAD^{tree}").strip(),
        "macOS": run("host", "/usr/bin/sw_vers").strip(),
        "crossSwift": run("cross-swift", cross_swift, "--version", env=cross_env).strip(),
        "appleSwift": run("apple-swift", apple_swift, "--version", env=apple_env).strip(),
        "appleXcode": run("apple-xcode", "/usr/bin/xcodebuild", "-version", env=apple_env).strip(),
        "crossMacOSSDK": run("cross-sdk-version", *xcrun, "--sdk", "macosx", "--show-sdk-version",
                             env=cross_env).strip(),
    }
    require(f"Swift version {version} (swift-{version}-RELEASE)" in versions["crossSwift"],
            "Cross compiler does not match release toolchain pin")
    require(versions["crossMacOSSDK"] == pin["crossCompilerHostSDK"]["macOSSDK"], "Wrong host SDK")
    ios_sdk = run("ios-sdk", *xcrun, "--sdk", "iphoneos", "--show-sdk-path", env=apple_env).strip()
    mac_sdk = run("macos-sdk", *xcrun, "--sdk", "macosx", "--show-sdk-path", env=cross_env).strip()
    node = shutil.which("node")
    require(node, "Node is required for the existing S2 WebAssembly oracle")
    versions["node"] = run("node", node, "--version").strip()
    versions["wasmLinker"] = run("wasm-linker", cross_toolchain / "usr/bin/wasm-ld", "--version",
                                 env=cross_env).strip()

    sdks = Path.home() / "Library/org.swift.swiftpm/swift-sdks"
    wasi_id = swift_pin["wasmSDK"]
    wasi = sdks / f"{wasi_id}.artifactbundle" / wasi_id / TRIPLE
    android = sdks / f"{swift_pin['androidSDK']}.artifactbundle/swift-android"
    android_toolset = android / "swift-toolset.json"
    pins = strict_json(ANDROID_PIN.read_text())["swiftAndroidSDK"]
    for file in (android / "swift-sdk.json", android_toolset):
        require(digest(file) == pins[f"swift-android/{file.name}"], f"Android SDK pin mismatch: {file}")
    ndk = android / "android-ndk-r27d"
    require("Pkg.Revision = 27.3.13750724" in (ndk / "source.properties").read_text(), "Wrong Android NDK")
    ndk_tools = ndk / "toolchains/llvm/prebuilt/darwin-x86_64/bin"

    def sdk_inputs(sdk, triple):
        target = strict_json((sdk / "swift-sdk.json").read_text())["targetTriples"][triple]
        return sdk / target["sdkRootPath"], sdk / target["swiftResourcesPath"]

    android_sdk, android_resources = sdk_inputs(android, s1["ANDROID"])
    wasi_sdk, wasi_resources = sdk_inputs(wasi, TRIPLE)
    wasi_tools = wasi / strict_json((wasi / "toolset.json").read_text())["rootPath"]
    wasm_flags = ("-target", TRIPLE, "-sdk", wasi_sdk, "-resource-dir", wasi_resources, "-static-stdlib")
    wasm_link = ("-Xclang-linker", "-resource-dir", "-Xclang-linker", wasi_resources / "clang")
    plugin = cross_toolchain / "usr/lib/swift/host/plugins/libObservationMacros.dylib"
    inputs = [PIN, ANDROID_PIN, *sorted(s1["FIXTURE"].rglob("*.swift")), S1 / "replay.py",
              *(S2 / name for name in ("FieldLog.swift", "Command.swift", "Reactor.swift", "oracle.mjs", "replay.py")),
              HERE / "replay.py", HERE / "ObservationControl.swift", wasi / "swift-sdk.json", wasi / "toolset.json",
              android / "swift-sdk.json", android_toolset, plugin, cross_swift.with_name("swift-frontend"),
              apple_swift.with_name("swift-frontend"),
              *(wasi_resources / f"wasi/{name}" for name in
                ("libswiftCore.a", "libswift_Concurrency.a", "libswiftObservation.a", "libFoundationEssentials.a"))]
    report["inputSHA256"] = {str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path):
                            digest(path) for path in inputs}

    def wasm_inventory(label, binary):
        run(f"{label}-wasm-inventory", node, "--no-warnings", S2 / "oracle.mjs", "inspect", binary)
        output = strict_json((logs / f"{label}-wasm-inventory.stderr").read_text())
        return {"imports": output["imports"], "exports": output["exports"]}

    def macho_libraries(label, binary, env):
        return run(f"{label}-otool", *xcrun, "otool", "-L", binary, env=env).splitlines()[1:]

    adapter = SimpleNamespace(work=work, checked=run)
    fixture = s1["FIXTURE"]
    build = s1["build"]
    report["S1"] = naming = {}
    naming["ios"] = build(adapter, "s1-ios", fixture, "ios", apple_swift,
                          ("-target", s1["IOS"], "-sdk", ios_sdk), apple_env,
                          lambda label, binary: macho_libraries(label, binary, apple_env))
    naming["android"] = build(adapter, "s1-android", fixture, "android", cross_swift,
                              ("-target", s1["ANDROID"], "-sdk", android_sdk, "-resource-dir", android_resources,
                               "-tools-directory", ndk_tools), cross_env,
                              lambda label, binary: run(f"{label}-readelf", ndk_tools / "llvm-readelf", "-d", binary,
                                                        env=cross_env).splitlines(),
                              ("-Xclang-linker", "-fuse-ld=lld"))
    naming["wasi"] = build(adapter, "s1-wasi", fixture, "wasi", cross_swift,
                           (*wasm_flags, "-tools-directory", wasi_tools), cross_env, wasm_inventory, wasm_link)
    for platform, result in naming.items():
        result["graphs"] = {path.name.removesuffix(".scan.json"): scan_graph(path)
                            for path in sorted((work / f"s1-{platform}").glob("*.scan.json"))}
        feature = result["graphs"]["SharedFeature"]
        engine = {"swiftPrebuiltExternal": "MixerSwiftUI" if platform == "ios" else "SwiftUI"}
        intermediates = next(module["directDependencies"] for module in feature["modules"] if module["id"] == engine)
        require(engine in feature["modules"][0]["directDependencies"]
                and {"swiftPrebuiltExternal": "TitleSupport"} in intermediates,
                f"S1 {platform}: SharedFeature did not resolve TitleSupport through the engine")

    report["S2"] = fieldlog = {}
    fieldlog_source = S2 / "FieldLog.swift"
    s2_common = ("-module-name", "FieldLogSpike", "-Osize", "-parse-as-library")
    native_flags = ("-target", "arm64-apple-macosx14.0", "-sdk", mac_sdk, *s2_common,
                    "-module-cache-path", work / "s2-native-cache")
    guest_flags = (*wasm_flags, *s2_common, "-gnone", "-module-cache-path", work / "s2-wasi-cache")
    for label, flags, entry in (("native", native_flags, "Command.swift"), ("wasi", guest_flags, "Reactor.swift")):
        scan = work / f"s2-{label}.scan.json"
        sources = (fieldlog_source, S2 / entry)
        run(f"s2-{label}-scan", cross_swift, *flags, "-whole-module-optimization", "-scan-dependencies",
            *sources, "-o", scan, env=cross_env)
        fieldlog[label] = {"graph": scan_graph(scan), "sourceImportSpellings": source_imports(*sources)}

    graphs = {f"S1-{platform}": result["graphs"]["SharedFeature"] for platform, result in naming.items()}
    graphs.update({f"S2-{platform}": result["graph"] for platform, result in fieldlog.items()})
    report["stdlibInterfaces"] = {}
    for label, graph in graphs.items():
        swift = next(module for module in graph["modules"] if module["id"] == {"swift": "Swift"})
        interface = Path(swift["inputs"]["moduleInterfacePath"])
        report["stdlibInterfaces"][label] = {"path": str(interface), "sha256": digest(interface)}

    native = work / "fieldlog-native"
    run("s2-native-build", cross_swift, *native_flags, fieldlog_source, S2 / "Command.swift",
        "-o", native, env=cross_env)
    fieldlog["native"].update(sha256=digest(native), libraries=macho_libraries("s2-native", native, cross_env))
    reactor = work / "fieldlog-reactor.wasm"
    link_map = reactor.with_suffix(".map")
    run("s2-reactor-build", cross_swift, *guest_flags, *wasm_link, "-Xlinker", "--strip-all",
        "-Xlinker", f"-Map={link_map}", "-Xclang-linker", "-mexec-model=reactor",
        "-Xlinker", "--export=mixer_guest_ui_start_v3", "-Xlinker", "--export=mixer_guest_ui_event_v3",
        "-Xlinker", "--export=mixer_guest_ui_ready_v3", fieldlog_source, S2 / "Reactor.swift",
        "-o", reactor, env=cross_env)
    archives = sorted(set(re.findall(r"/wasi/([^/\s()]+\.a)\(", link_map.read_text())))
    fieldlog["wasi"].update(sha256=digest(reactor), bytes=reactor.stat().st_size, runtimeArchives=archives,
                            **wasm_inventory("s2-reactor", reactor))

    control = HERE / "ObservationControl.swift"
    run("s2-macro-control", cross_swift, *guest_flags, "-typecheck", "-Xfrontend", "-dump-macro-expansions",
        fieldlog_source, control, env=cross_env)
    expansion = (logs / "s2-macro-control.stderr").read_text()
    macro_lines = ["extension InventoryObservation: nonisolated Observation.Observable",
                   "Observation.ObservationRegistrar()", "access(keyPath: \\.record)",
                   "withMutation(keyPath: \\.record)"]
    control_text = control.read_text()
    macro = report["macroControl"] = {"target": TRIPLE, "expansion": expansion}
    require(all(line in expansion and line not in control_text for line in macro_lines),
            "Observation control did not expose synthesized conformance, registrar and accessors")
    macro["generatedFragments"] = macro_lines
    without_macro = work / control.name
    without_macro.write_text(control_text.replace("@Observable\n", "", 1))
    run("s2-macro-removed-control", cross_swift, *guest_flags, "-typecheck", fieldlog_source,
        without_macro, env=cross_env, expected=(1,))
    diagnostic = (logs / "s2-macro-removed-control.stderr").read_text()
    macro["withoutAttributeDiagnostic"] = diagnostic
    require("cannot convert return expression of type '(InventoryObservation, TaskRecord?)' "
            "to return type '(any Observable, TaskRecord?)'" in diagnostic,
            "Removing @Observable did not reproduce the expected conformance error")

    feature = fixture / "Sources/SharedFeature/Title.swift"
    feature_imports = source_imports(feature)
    ios_imports = direct_imports(naming["ios"]["graphs"]["SharedFeature"])
    report["sourceOnlyControls"] = {
        "s1FeatureImportSpellings": feature_imports,
        "s1ResolvedIOSFeatureImports": sorted(ios_imports),
        "s2EmittedImportAbsentFromSource": "wasi_snapshot_preview1.clock_time_get",
    }
    require(feature_imports == ["SwiftUI"] and "MixerSwiftUI" in ios_imports and "SwiftUI" not in ios_imports,
            "S1 source spelling did not differ from compiler alias resolution")
    require("SwiftUI.framework/SwiftUI" in "\n".join(naming["ios"]["observation"]),
            "S1 iOS artifact omitted the Apple SwiftUI framework")
    require("Foundation" in direct_imports(fieldlog["native"]["graph"])
            and "FoundationEssentials" in direct_imports(fieldlog["wasi"]["graph"])
            and "Foundation" not in direct_imports(fieldlog["wasi"]["graph"]),
            "S2 compiler scans did not resolve the expected conditional Foundation imports")
    require("libswiftObservation.a" in archives and "libFoundationEssentials.a" in archives,
            "S2 linker map omitted the Observation or FoundationEssentials archive")
    require({"module": "wasi_snapshot_preview1", "name": "clock_time_get", "kind": "function"}
            in fieldlog["wasi"]["imports"] and
            all(not re.search(r"\bclock_time_get\b", path.read_text())
                for path in (fieldlog_source, S2 / "Reactor.swift")),
            "S2 emitted-import control did not differ from authored source")
    require({"name": "mixer_guest_ui_start_v3", "kind": "function"} in fieldlog["wasi"]["exports"],
            "S2 reactor omitted its UI start export")


def main():
    local = ROOT / "verification/local"
    local.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="up5-compiled-inventory-", dir=local))
    scratch = output / "scratch"
    work, logs, tmp = (scratch / name for name in ("work", "logs", "tmp"))
    for path in (work, logs, tmp):
        path.mkdir(parents=True)
    report = {"scope": "UP5 Section 7.2 host compiler experiment", "commands": []}
    recorder = CommandRecorder(logs, report["commands"], ROOT)
    environment = clean_environment() | {
        "TMPDIR": str(tmp), "CLANG_MODULE_CACHE_PATH": str(work / "clang-cache"),
        "XDG_CACHE_HOME": str(work / "xdg-cache"), "MACOSX_DEPLOYMENT_TARGET": "14.0",
    }

    def run(label, *command, env=None, expected=(0,)):
        active_env = environment | (env or {})
        try:
            return recorder.run(label, command, env=active_env, timeout=120, expected=expected)
        finally:
            if report["commands"] and report["commands"][-1]["name"] == label:
                event = report["commands"][-1]
                event["environment"] = {key: value for key, value in active_env.items()
                                        if key not in ("HOME", "USER", "LOGNAME")}
                if event["terminalCustody"] == "TERMINAL" and event["exitCode"] not in expected:
                    with (logs / f"{label}.stderr").open("rb") as stream:
                        event["diagnosticExcerpt"] = stream.read(4096).decode(errors="replace")

    print(output / "receipt.json", flush=True)
    try:
        execute(run, logs, work, report)
        report["completed"] = True
    except BaseException as error:
        report["completed"] = False
        report["error"] = str(error)
        raise
    finally:
        unresolved = [item for item in report["commands"] if item["terminalCustody"] == "UNKNOWN"]
        if unresolved:
            (output / "HOLD.json").write_text(json.dumps(unresolved, indent=2) + "\n")
            report["cleanup"] = "Preserved scratch because command custody is unknown."
        else:
            shutil.rmtree(scratch)
            report["cleanup"] = "Removed owned scratch after observing terminal command groups."
        (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
