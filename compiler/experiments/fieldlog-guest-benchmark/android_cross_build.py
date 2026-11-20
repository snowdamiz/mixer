#!/usr/bin/env python3
"""Build the pinned D3 Android shell fixture in one private, offline campaign."""

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import tarfile
import tempfile
from types import ModuleType

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = "0151489ca628de071385f0afbe4017a57c784cdc"
BENCH = "compiler/experiments/fieldlog-guest-benchmark/"
MODEL = "compiler/experiments/fieldlog-installed-guest/"
RUNTIME = "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/"
RECEIPT = "verification/receipts/l03-d3-taskcompletion-signed-size-a55f5a55.json"
D3 = "verification/receipts/l03-d3-task-review-event-trap-7b61fe1c.json"
NOTICES = "cli/Sources/MixerBuild/Resources/android-build.py"
SOURCE = [MODEL + "TaskCompletion.swift", BENCH + "MatchedTask.swift",
          *(RUNTIME + name + ".swift" for name in ("Types", "Failure", "GuestDebugLines"))]
TARGET = "aarch64-unknown-linux-android28"
WASM_SHA = "78332ea7cbe69760f605cc980a9c0c29d82d8376598a8451514ce1b96ce12a3e"
MODES = ("native", "guest", "native-control", "guest-control", "guest-profile")
ENV = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C",
       "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(path):
    with path.open("rb") as source:
        return {"bytes": path.stat().st_size, "sha256": hashlib.file_digest(source, "sha256").hexdigest()}


def read_json(path):
    return json.loads(path.read_text())


def run_base():
    # Reuse the pinned host replay's bounded POSIX spawn, wait4 and exact group
    # absence check. Its module only defines functions when loaded this way.
    rel = BENCH + "matched_task.py"
    source = subprocess.check_output(
        ["/usr/bin/git", "-C", ROOT, "show", f"{PIN}:{rel}"], env=ENV, timeout=10)
    module = ModuleType("pinned_matched_task")
    module.__file__ = str(ROOT / rel)
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module.Run


def check_wasm(run, tools, wasm, model):
    data = wasm.read_bytes()
    require(data[:8] == b"\0asm\1\0\0\0", "wrong Wasm header")

    def uint(position):
        value = 0
        for shift in range(0, 35, 7):
            byte = data[position]
            position += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value, position
        raise ValueError("invalid unsigned Wasm LEB")

    sections = {}
    cursor = 8
    while cursor < len(data):
        section = data[cursor]
        size, payload = uint(cursor + 1)
        require(payload + size <= len(data), "truncated Wasm section")
        if section:
            require(section not in sections, "duplicate Wasm section")
            sections[section] = payload
        cursor = payload + size
    require(2 not in sections, "Wasm has imports")
    code = sections[10]
    count, cursor = uint(code)
    require(count > 7, "missing function 7")
    for _ in range(7):
        size, body = uint(cursor)
        cursor = body + size
    size, body = uint(cursor)
    offset = 1869
    require(body <= offset < body + size and data[offset] == 0, "wrong Wasm trap coordinate")
    address = f"{offset - code:x}"
    disassembly = run.command("wasm-disassembly", tools / "llvm-objdump", "-d", wasm)[0]
    require(re.search(rf"^\s+{address}:\s+00\s+unreachable\s*$", disassembly, re.M),
            "Wasm trap is not an unreachable instruction")
    lines = run.command("wasm-debug-line", tools / "llvm-dwarfdump", "--debug-line", wasm)[0]
    file = re.search(r'file_names\[\s*1\]:\s*name: "TaskCompletion.swift"', lines)
    row = re.search(rf"^0x0*{address}\s+94\s+9\s+1\s", lines, re.M)
    require(file and row and model.read_text().splitlines()[93].strip() ==
            "precondition(count < destination.count)", "Wasm line table or pinned trap source differs")
    return {"functionIndex": 7, "absoluteWasmOffset": offset, "codeRelativeOffset": offset - code,
            "source": "TaskCompletion.swift:94:9", "instruction": "unreachable"}


def inspect_elf(run, tools, executable, output, sdk, ndk, target_libraries):
    system = read_json(ndk / "meta/system_libs.json")
    runtime = sdk / "swift-resources/usr/lib/swift-aarch64/android"
    api_libraries = target_libraries / "28"
    pending = [executable]
    dependencies = {}
    origins = {}
    while pending:
        elf = pending.pop(0)
        report = run.command("elf-" + elf.name, tools / "llvm-readelf", "-h", "-l", "-d", "-n", elf)[0]
        require("ELF64" in report and "little endian" in report and "AArch64" in report,
                f"wrong ELF ABI for {elf.name}")
        loads = re.findall(r"^\s+LOAD\s+.*\s(0x[0-9a-f]+)\s*$", report, re.M)
        require(loads and all(int(alignment, 16) >= 16384 for alignment in loads),
                f"LOAD alignment below 16 KiB for {elf.name}")
        require(re.search(r"Type:\s+DYN\b", report), f"wrong ELF type for {elf.name}")
        search_paths = re.findall(r"\((?:RPATH|RUNPATH)\).*?\[([^\]]+)\]", report)
        require(not re.search(r"\(TEXTREL\)", report)
                and search_paths in ([], ["$ORIGIN"] if elf != executable else []),
                f"unexpected runtime search path or text relocations in {elf.name}")
        interp = re.findall(r"Requesting program interpreter: ([^\]]+)", report)
        expected = ["/system/bin/linker64"] if elf == executable else []
        require(interp == expected, f"wrong ELF interpreter for {elf.name}: {interp}")
        if elf == executable:
            require(re.search(r"Entry point address:\s+0x[1-9a-f][0-9a-f]*", report),
                    "ELF entry point missing")
            require(re.search(r"Android\s+0x[0-9a-f]+\s+NT_ANDROID_TYPE_IDENT\n"
                              r"\s+description data: 1c 00 00 00", report),
                    "missing Android API 28 identity note")
        else:
            require(re.findall(r"\(SONAME\).*?\[([^\]]+)\]", report) == [elf.name],
                    f"unexpected SONAME for {elf.name}")
        build_id = re.findall(r"Build ID:\s+([a-f0-9]+)", report)
        require(len(build_id) == 1, f"missing build ID for {elf.name}")
        needed = re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", report)
        dependencies[elf.name] = {"needed": needed, "buildID": build_id[0],
                                  "loadAlignments": loads, "searchPaths": search_paths, **identity(elf)}
        for name in needed:
            require(re.fullmatch(r"lib[\w.+-]+\.so", name), f"invalid DT_NEEDED {name!r}")
            if name in system:
                require(int(system[name]) <= 28 and (api_libraries / name).is_file(),
                        f"system library unavailable at API 28: {name}")
            elif name not in origins:
                candidates = [source / name for source in (runtime, target_libraries)
                              if (source / name).is_file()]
                require(len(candidates) == 1, f"ambiguous or unresolved DT_NEEDED {name}")
                origin = candidates[0]
                destination = output / "lib" / name
                shutil.copy2(origin, destination)
                origins[name] = origin
                pending.append(destination)
        (output / "evidence" / (elf.name + ".readelf.txt")).write_text(report)
    return dependencies, origins, sorted({name for row in dependencies.values()
                                           for name in row["needed"] if name in system})


def add_notices(output, source, sdk, ndk, rust, origins):
    notices = output / "notices"
    notices.mkdir()
    swift_notice = sdk / "swift-resources/usr/share/swift/LICENSE.txt"
    for name, path in (("Swift-SDK-LICENSE.txt", swift_notice),
                       ("Android-NDK-NOTICE.txt", ndk / "NOTICE"),
                       ("Android-NDK-NOTICE.toolchain.txt", ndk / "NOTICE.toolchain")):
        shutil.copy2(path, notices / name)
    rust_docs = rust.parent / "share/doc/rust"
    shutil.copy2(rust_docs / "COPYRIGHT-library.html", notices)
    shutil.copytree(rust_docs / "licenses", notices / "licenses")
    shutil.copy2(sdk.parent / "sbom.spdx.json", notices / "Swift-SDK-sbom.spdx.json")
    icu = origins.get("lib_FoundationICU.so")
    if icu:
        require(identity(icu)["sha256"] ==
                "41171d3eed0f99b2057b9b528c14a4ad27d07f1e102d106facfcd0db8faf2a4a",
                "Foundation ICU differs from the pinned Starter notice binding")
        tree = ast.parse((source / NOTICES).read_text())
        license_text, = [ast.literal_eval(node.value) for node in tree.body
                         if isinstance(node, ast.Assign)
                         and any(isinstance(target, ast.Name) and target.id == "APPLE_ICU_LICENSE"
                                 for target in node.targets)]
        (notices / "Apple-ICU-76.1-LICENSE.txt").write_text(license_text)
    (notices / "source-links.txt").write_text(
        f"Mixer sources https://github.com/snowdamiz/mixer/tree/{PIN}\n"
        "Rust standard library and notices https://github.com/rust-lang/rust/tree/b940084d7eb6a299eb4bfeb8e34901bc051e7ac4/library\n"
        "Rust compiler-builtins https://github.com/rust-lang/rust/tree/b940084d7eb6a299eb4bfeb8e34901bc051e7ac4/library/compiler-builtins\n"
        "Swift Android Foundation https://github.com/swiftlang/swift-corelibs-foundation/tree/swift-6.3.3-RELEASE\n"
        "Swift and standard library https://github.com/swiftlang/swift/tree/swift-6.3.3-RELEASE\n"
        "Swift Foundation https://github.com/swiftlang/swift-foundation/tree/swift-6.3.3-RELEASE\n"
        "Dispatch https://github.com/swiftlang/swift-corelibs-libdispatch/tree/swift-6.3.3-RELEASE\n"
        "Swift SDK ICU https://github.com/apple/icu/tree/icu-76.1\n"
        "Android NDK release https://github.com/android/ndk/wiki/Changelog-r27\n")


def campaign(run, wasm_input, sdk, swift, rust):
    run.env.update(ENV)
    run.env["PATH"] = f"{rust}:" + ENV["PATH"]
    run.env["RUSTC"] = str(rust / "rustc")
    run.env["DEVELOPER_DIR"] = "/Applications/Xcode_26.6.app/Contents/Developer"
    work = run.scratch
    output = work / "packet"
    for folder in ("lib", "evidence"):
        (output / folder).mkdir(parents=True)
    ndk = sdk / "android-ndk-r27d"
    tools = ndk / "toolchains/llvm/prebuilt/darwin-x86_64/bin"
    target_libraries = tools.parent / "sysroot/usr/lib/aarch64-linux-android"
    run.env["CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER"] = str(tools / "aarch64-linux-android28-clang")
    run.env["RUSTFLAGS"] = "-C link-arg=-Wl,-z,max-page-size=16384"
    cmd = run.command
    git = ("/usr/bin/git", "-C", ROOT)
    tree = cmd("tree", *git, "rev-parse", PIN + "^{tree}")[0].strip()
    vm_tree = cmd("vm-tree", *git, "rev-parse", PIN + ":vm")[0].strip()
    tar = work / "source.tar"
    paths = ["vm/src", "vm/include", "vm/examples/taskeditor_owned_command.rs",
             "vm/Cargo.toml", "vm/Cargo.lock", RECEIPT, D3, NOTICES, *SOURCE]
    cmd("pin-export", *git, "archive", "--format=tar", f"--output={tar}", PIN, "--", *paths)
    source = work / "source"
    with tarfile.open(tar) as archive:
        archive.extractall(source, filter="data")
    receipt = read_json(source / RECEIPT)
    historical = read_json(source / D3)
    wasm = output / "raw.wasm"
    shutil.copyfile(wasm_input, wasm)
    require(identity(wasm) == receipt["update"]["raw.wasm"] == {"bytes": 5263, "sha256": WASM_SHA},
            "signed-size raw Wasm differs from pin")
    require([row["sha256"] for row in receipt["frames"]] == [row["sha256"] for row in historical["frames"]],
            "signed-size and historical D3 frame digests differ")
    hashes = {path: identity(source / path)["sha256"] for path in SOURCE}
    require(all(receipt["sourceSHA256"][path] == digest for path, digest in hashes.items()),
            "benchmark source differs from the signed-size receipt")
    metadata = {"swift-sdk.json": "e81f3f2142bce0a795cdec567ad24434db3a7b02c288eb2eef2041d2066111dc",
                "swift-toolset.json": "0f9e3a784a4e60bf4c816460dae0ed64e0a723167af111fc05bac8a010b0e065"}
    require(all(identity(sdk / file)["sha256"] == digest for file, digest in metadata.items()),
            "Android SDK metadata differs from the admitted Linux Android target")
    require("Pkg.Revision = 27.3.13750724" in (ndk / "source.properties").read_text(),
            "NDK r27d required")
    sdk_target = read_json(sdk / "swift-sdk.json")["targetTriples"][TARGET]
    sysroot = sdk / sdk_target["sdkRootPath"]
    require((sysroot / "usr/lib/aarch64-linux-android").resolve() == target_libraries.resolve()
            and (sysroot / "usr/include").resolve() == (tools.parent / "sysroot/usr/include").resolve(),
            "SDK sysroot and pinned NDK disagree")
    swift_resources = sdk / sdk_target["swiftResourcesPath"]
    versions = {name: cmd(name, tool, "--version")[0].strip() for name, tool in
                (("swift", swift / "swiftc"), ("clang", tools / "aarch64-linux-android28-clang"),
                 ("readelf", tools / "llvm-readelf"), ("rustc", rust / "rustc"), ("cargo", rust / "cargo"))}
    require("Swift version 6.3.3 (swift-6.3.3-RELEASE)" in versions["swift"]
            and "rustc 1.99.0 (b940084d7 " in versions["rustc"]
            and "Android (13691557," in versions["clang"], "selected tools differ from pins")
    rust_identity = cmd("rustc-identity", rust / "rustc", "-vV")[0].strip()
    require("commit-hash: b940084d7eb6a299eb4bfeb8e34901bc051e7ac4" in rust_identity,
            "Rust compiler commit differs from the pin")
    versions["rustc"] = rust_identity
    debug = check_wasm(run, tools, wasm, source / SOURCE[0])
    target = work / "rust"
    cmd("vm-build", rust / "cargo", "build", "--offline", "--locked", "--release", "--lib", "--jobs", "2",
        "--no-default-features", "--features", "experimental-capability-native",
        "--target", "aarch64-linux-android",
        "--manifest-path", source / "vm/Cargo.toml", "--target-dir", target, bound=125)
    archive = target / "aarch64-linux-android/release/libmixer_vm.a"
    headers = cmd("vm-elf", tools / "llvm-readelf", "-h", archive, bound=20)[0]
    require("mixer_vm." in headers and
            set(re.findall(r"Machine:\s+(.+)", headers)) == {"AArch64"} and
            set(re.findall(r"Class:\s+(.+)", headers)) == {"ELF64"} and
            set(re.findall(r"Type:\s+(\w+)", headers)) == {"REL"}, "VM archive ELF identity differs")
    archive_identity = {**identity(archive), "target": "aarch64-linux-android",
                        "objectCount": headers.count("ELF Header:"),
                        "memberClass": "ELF64", "memberMachine": "AArch64", "memberType": "REL",
                        "cargoLock": identity(source / "vm/Cargo.lock")}
    (work / "module.modulemap").write_text(
        f'module CMixerVMCapability {{ header "{source}/vm/include/mixer_vm_guest_ui.h" export * }}\n')
    matched = output / "matched"
    cmd("matched-build", swift / "swiftc", "-v", "-j", "2", "-swift-version", "6",
        "-parse-as-library", "-target", TARGET, "-sdk", sysroot, "-resource-dir", swift_resources,
        "-tools-directory", tools,
        "-module-cache-path", work / "modules", "-I", work, "-O", "-whole-module-optimization",
        "-gline-tables-only", "-debug-prefix-map", f"{source}=.", "-debug-prefix-map", f"{work}=./fixture",
        "-Xclang-linker", "-fuse-ld=lld", "-Xlinker", "-z", "-Xlinker", "max-page-size=16384",
        "-Xlinker", "--build-id=sha1", *(source / path for path in SOURCE), archive, "-o", matched, bound=90)
    libs, origins, system = inspect_elf(run, tools, matched, output, sdk, ndk, target_libraries)
    native_lines = cmd("native-debug-line", tools / "llvm-dwarfdump", "--debug-line", matched)[0]
    require(re.search(r'name: "TaskCompletion.swift"', native_lines), "missing native task line table")
    (output / "evidence/native-task-line-table.txt").write_text(native_lines)
    (output / "evidence/matched-build.log").write_bytes((work / "matched-build.err").read_bytes())
    add_notices(output, source, sdk, ndk, rust, origins)
    launch = {"cwd": "packet directory", "environment": {"LD_LIBRARY_PATH": "./lib"},
              "argvByMode": {mode: ["./matched", mode, "./raw.wasm"] for mode in MODES}}
    summary = {
        "scope": "Private cross-build and host-side identity checks for the shared D3 shell fixture.",
        "observedUTC": datetime.now(timezone.utc).isoformat(),
        "publicRevision": PIN, "publicTree": tree, "vmTree": vm_tree,
        "sourceSHA256": hashes, "buildScript": identity(Path(__file__)),
        "signedSizeReceipt": identity(source / RECEIPT), "historicalD3Receipt": identity(source / D3),
        "wasm": identity(wasm), "expectedFrames": receipt["frames"],
        "expectedGuestDiagnostic": receipt["parity"]["guestDiagnostic"],
        "staticWasmDiagnostic": debug, "expectedControlRefusalsPerPath": 2,
        "expectedGuestCloseAndStaleHandleRefusal": True,
        "toolVersions": versions, "androidTarget": TARGET, "swiftSDKMetadataSHA256": metadata,
        "ndkMetadata": identity(ndk / "source.properties"), "vmArchive": archive_identity,
        "elfInterpreter": "/system/bin/linker64", "elfDependencies": libs,
        "systemLibraries": system, "sharedLibraryOrigins": {name: str(path.relative_to(sdk))
                                                            for name, path in origins.items()},
        "launch": launch,
        "timing": "Three prepared events through materialized frame. Includes acceptance and render, "
                  "plus VM write, invoke, result, header checks and frame read on guest. "
                  "Startup, first frame, refusal and trap controls, close and JSON are outside the timer.",
        "runtimeVerification": "Pending root-owned API 36 emulator run, including whole-process RSS.",
        "buildEnvironment": {key: run.env[key].replace(str(Path.home()), "$USER_HOME") for key in
                             ("CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER", "RUSTFLAGS", "DEVELOPER_DIR")},
        "commands": run.commands,
        "custody": {"directReapedAndGroupsObservedAbsent": len(run.commands),
                    "unknown": 0, "observedPeakScratchBytes": run.peak_scratch,
                    "scratchLimitBytes": 3 * 1024**3},
    }
    (output / "receipt.json").write_text(json.dumps(summary, indent=2) + "\n")
    files = sorted(path for path in output.rglob("*") if path.is_file())
    (output / "SHA256SUMS").write_text("".join(
        f"{identity(path)['sha256']}  {path.relative_to(output).as_posix()}\n" for path in files))
    require(run.check_space(), "final packet exceeds scratch limit")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    home = Path.home()
    parser.add_argument("--swift", type=Path, default=home /
                        "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin")
    parser.add_argument("--sdk", type=Path, default=home /
                        ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android")
    parser.add_argument("--rust", type=Path, default=home /
                        ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin")
    args = parser.parse_args()
    require((os.uname().sysname, os.uname().machine) == ("Darwin", "arm64"), "requires arm64 Darwin")
    output = args.output.resolve()
    local = ROOT / "verification/local"
    require(output.parent == local and not args.output.is_symlink(),
            "output must be a new immediate child of verification/local")
    require(not output.exists(), "output already exists")
    run_type = run_base()
    local.mkdir(exist_ok=True)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
    scratch = Path(tempfile.mkdtemp(prefix="l03-matched-android-build-", dir=local))
    run = run_type(scratch)
    print(f"Build scratch {scratch}", flush=True)
    try:
        packet = campaign(run, args.wasm.resolve(), args.sdk.resolve(), args.swift.resolve(), args.rust.resolve())
        packet.rename(output)
    except (RuntimeError, ValueError) as error:
        # Keep the completed failure summary without retaining transient products.
        if run.active is None:
            print(json.dumps({"failure": str(error), "commands": run.commands}), flush=True)
        raise
    finally:
        if run.active is None:
            shutil.rmtree(scratch)
        else:
            hold = {"custody": "UNKNOWN", "active": run.active, "scratch": str(scratch)}
            (local / (scratch.name + "-HOLD.json")).write_text(json.dumps(hold, indent=2) + "\n")
            raise RuntimeError(f"unresolved command custody, preserve {scratch}: {run.active}")
    print(output, flush=True)


if __name__ == "__main__":
    main()
