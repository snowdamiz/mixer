#!/usr/bin/env python3
"""Compare the historical FieldLog title/cancel transition in macOS Swift and Mixer VM."""

import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time


HERE = Path(__file__).resolve().parent
MIXER = HERE.parents[2]
PUBLIC = "2acaac67605c369ff1667e3ccc3eb56d376e536e"
PUBLIC_TREE = "d995f414d76ee7ec709594521e071618dd088dda"
VM_TREE = "ec1ddb74b7c6c2eabd91d1f60ed243ffc69ce6f4"
EDITOR = "6ea3c41c0c50353ca56d1a62c1dfc9cced65dedf"
MODEL = "91615788bea186663fbb8a23231e304802366f8a"
FEATURE = "Sources/FieldLogFeatures/"
MAX_WASM = 4 * 1024 * 1024
EXPORTS = ("fieldlog_editor_open", "fieldlog_editor_send", "fieldlog_editor_snapshot")
HISTORY = {
    "F05": {
        "fieldlog": "70f3aa1d28f29e7c327a17fd46199480d41ca749",
        "sdk": "d8c6965a277ca21e685f3ef9e0f68a7d59b46156",
        "sdkTree": "fa1a446b6fa6f4b1b5e79fa3b19284e0c1013dba",
        "axis": "horizontal",
        "files": {
            "Package.swift": "5cc35eceb897ee5de1edda0ec42cd593acc8504a",
            FEATURE + "TaskEditorPresentation.swift": "67caf99cd93fe76250735eee9b96f15661aa50e9",
        },
    },
    "F06": {
        "fieldlog": "4d17c92656d3a7574506f06414bc2f08af469122",
        "sdk": "56ff14c925168284761c5aca4f0bd4129cf3c995",
        "sdkTree": "ab7fdd557af1278e5127fe7ff59ff0df7d7820f0",
        "axis": "vertical",
        "files": {
            "Package.swift": "072b7be9626de4c38ab4bff95967f0e502ab3956",
            FEATURE + "TaskEditorPresentation.swift": "2988fb76f35e807a1b9d99890fa322280336cbb3",
            FEATURE + "TaskEditorAppleFieldsHost.swift": "6ddd3e6284b008c9b86ba8ad6d40163011d7cd46",
        },
    },
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Campaign:
    def __init__(self, work, receipt):
        self.work = work
        self.receipt = receipt
        self.held = False
        self.deadline = time.monotonic() + 360
        self.env = {
            **os.environ, "TMPDIR": str(work / "tmp"), "GIT_TERMINAL_PROMPT": "0",
            "CLANG_MODULE_CACHE_PATH": str(work / "modules"), "LC_ALL": "C",
        }
        (work / "tmp").mkdir()

    def run(self, name, *argv, accepted=0, binary=False, timeout=60):
        argv = list(map(str, argv))
        remaining = min(timeout, self.deadline - time.monotonic())
        require(remaining > 0, "campaign wall deadline reached before launch")
        log = self.work / (name + ".stdout")
        error = self.work / (name + ".stderr")
        row = {"name": name, "argv": [arg.replace(str(self.work), "$WORK") for arg in argv]}
        self.receipt["commands"].append(row)
        with log.open("xb") as out, error.open("xb") as err:
            process = subprocess.Popen(argv, cwd=self.work, env=self.env, stdout=out, stderr=err,
                                       start_new_session=True)
            try:
                row["exit"] = process.wait(timeout=remaining)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as interruption:
                row["timedOut"] = isinstance(interruption, subprocess.TimeoutExpired)
                row["interrupted"] = isinstance(interruption, KeyboardInterrupt)
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except OSError:
                    self.hold(row, process.pid)
                    raise
                try:
                    row["exit"] = process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.hold(row, process.pid)
                    raise
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                row["groupAbsent"] = True
            except OSError:
                self.hold(row, process.pid)
                raise
            else:
                self.hold(row, process.pid)
                raise RuntimeError(f"{name} left a live process group")
        stdout, stderr = log.read_bytes(), error.read_bytes()
        row.update(stdoutSHA256=digest(stdout), stderrSHA256=digest(stderr))
        require(not row.get("timedOut") and not row.get("interrupted") and row["exit"] == accepted,
                f"{name} exited {row['exit']}\n{stdout[-3000:].decode(errors='replace')}\n"
                f"{stderr[-5000:].decode(errors='replace')}")
        return stdout if binary else (stdout + stderr).decode(errors="replace").strip()

    def hold(self, row, pgid):
        self.held = True
        row.update(groupAbsent=False, unresolvedPGID=pgid)

    def archive(self, name, revision, destination, *paths):
        archive = self.run(name, "git", "-C", MIXER, "archive", revision, *paths, binary=True)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(destination, filter="data")
        return digest(archive)


def wasm_memory(wasm):
    """Read back the link limits. The existing VM performs executable validation."""
    source = io.BytesIO(wasm)

    def uleb(stream):
        result = 0
        for shift in range(0, 35, 7):
            byte = stream.read(1)
            require(byte, "truncated Wasm LEB")
            result |= (byte[0] & 127) << shift
            if byte[0] < 128:
                return result
        raise RuntimeError("invalid Wasm u32")

    require(source.read(8) == b"\0asm\x01\0\0\0", "invalid Wasm header")
    memories = None
    while section := source.read(1):
        length = uleb(source)
        payload = source.read(length)
        require(len(payload) == length, "truncated Wasm section")
        fields = io.BytesIO(payload)
        if section == b"\x02":
            require(uleb(fields) == 0 and not fields.read(1), "guest imports are forbidden")
        if section == b"\x05":
            require(memories is None and uleb(fields) == 1 and uleb(fields) == 1,
                    "expected exactly one bounded memory")
            memories = (uleb(fields), uleb(fields))
            require(not fields.read(1), "extra memory payload")
    require(memories is not None and memories[0] <= memories[1] == 64, "memory limits differ")
    return memories


def replay(args, campaign, receipt):
    run = campaign.run
    work = campaign.work
    swift = args.swift_toolchain / "bin/swiftc"
    linker = args.swift_toolchain / "bin/wasm-ld"
    unicode_tables = args.swift_toolchain / "lib/swift/embedded/wasm32-unknown-none-wasm/libswiftUnicodeDataTables.a"
    libc = args.wasm_sdk / "WASI.sdk/lib/wasm32-wasip1/libc.a"
    mac_sdk = run("mac-sdk", "/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path")
    receipt["tools"] = {
        "guestSwift": run("swift-version", swift, "--version"),
        "hostSwift": run("host-swift-version", args.host_swiftc, "--version"),
        "linker": run("lld-version", linker, "--version"),
        "rust": run("rust-version", args.rustc, "--version"), "macOS": run("host-version", "/usr/bin/sw_vers"),
        "unicodeArchiveSHA256": digest(unicode_tables.read_bytes()), "libcSHA256": digest(libc.read_bytes()),
    }
    require(run("public-tree", "git", "-C", MIXER, "rev-parse", PUBLIC + "^{tree}") == PUBLIC_TREE,
            "public revision tree mismatch")
    require(run("public-vm-tree", "git", "-C", MIXER, "rev-parse", PUBLIC + ":vm") == VM_TREE,
            "VM source tree mismatch")
    if args.fieldlog is None:
        fieldlog = work / "fieldlog"
        run("clone-fieldlog", "git", "-c", "credential.helper=", "clone", "--no-tags", "--no-checkout",
            "https://github.com/snowdamiz/fieldlog.git", fieldlog, timeout=30)
    else:
        fieldlog = args.fieldlog

    def blob(label, revision, name, oid):
        data = run(label, "git", "-C", fieldlog, "show", revision + ":" + name, binary=True)
        git_header = f"blob {len(data)}\0".encode()
        require(hashlib.sha1(git_header + data).hexdigest() == oid, f"{name}: historical Git blob mismatch")
        return data

    before = "82192341e6dd8c7ac2435dcf7cc4541f0af71e1f"
    editor = blob("parent-editor", before, FEATURE + "TaskEditor.swift", EDITOR)
    original_editor = work / "TaskEditor.swift"
    original_editor.write_bytes(editor)
    flags = (swift, "-target", "wasm32-unknown-none-wasm", "-enable-experimental-feature", "Embedded",
             "-whole-module-optimization", "-Osize", "-parse-as-library", "-Xfrontend", "-disable-stack-protector")
    refusal = run("untouched-editor", *flags, "-emit-object", original_editor, "-o", work / "untouched.o", accepted=1)
    require("no such module 'Foundation'" in refusal, "different untouched editor compile error")
    receipt["untouchedEditorRefusal"] = "TaskEditor.swift:1:8: no such module 'Foundation'"
    # The case returns an empty effect list. The title-only boundary has no effect
    # type, so its version of the early exit returns Void.
    case = editor.decode().split("      case .title(let title):\n", 1)[1].split("      case .responsible(", 1)[0]
    require(case == "        guard !state.saving && !state.saved else { return [] }\n"
                    "        state.title = title; state.failure = nil\n", "historical title case changed")
    reduction = work / "TitleReduction.swift"
    reduction.write_text("extension TitleState {\n    mutating func changeTitle(_ title: String) {\n"
                         + case.replace("state.", "self.").replace("return []", "return")
                         + "    }\n}\n")
    receipt["titleReductionSHA256"] = digest(reduction.read_bytes())

    guest = work / "editor.wasm"
    run("build-embedded", *flags, "-emit-object", HERE / "EditorBoundary.swift", reduction, HERE / "Guest.swift",
        "-o", work / "editor.o")
    run("link-embedded", linker, "--fatal-warnings", "--no-entry", "--gc-sections", "--strip-all",
        "-z", "stack-size=32768", f"--max-memory={MAX_WASM}", *(f"--export={name}" for name in EXPORTS),
        work / "editor.o", unicode_tables, libc, "-o", guest)
    wasm = guest.read_bytes()
    require(len(wasm) <= MAX_WASM, "authenticated payload byte ceiling exceeded")
    initial, maximum = wasm_memory(wasm)
    receipt["guest"] = {"bytes": len(wasm), "sha256": digest(wasm), "imports": [],
                        "initialPages": initial, "maximumPages": maximum, "stackBytes": 32768}

    receipt["vmArchiveSHA256"] = campaign.archive("archive-vm", PUBLIC, work, "vm")
    vm = work / "vm"
    library = work / "libmixer_vm.a"
    run("build-owned-vm", args.rustc, "--edition=2021", "--crate-name", "mixer_vm", "--crate-type", "staticlib",
        "-C", "opt-level=3", "-C", "overflow-checks=on", vm / "src/lib.rs", "-o", library)
    receipt["vmLibrarySHA256"] = digest(library.read_bytes())
    include = vm / "include"
    (include / "module.modulemap").write_text('module OwnedVM { header "mixer_vm.h" export * }\n')

    for label, pins in HISTORY.items():
        variant = work / label
        variant.mkdir()
        files = {**pins["files"], "Sources/FieldLogModels/Workspace.swift": MODEL,
                 FEATURE + "TaskEditor.swift": EDITOR}
        row = {**pins, "files": {}, "beforeEditor": {"revision": before, "blob": EDITOR}}
        receipt["history"][label] = row
        for name, oid in files.items():
            data = blob(f"{label}-{Path(name).stem}", pins["fieldlog"], name, oid)
            (variant / Path(name).name).write_bytes(data)
            row["files"][name] = {"blob": oid, "sha256": digest(data)}
        require(pins["sdk"].encode() in (variant / "Package.swift").read_bytes(), "FieldLog SDK pin mismatch")
        require(run(f"{label}-sdk-tree", "git", "-C", MIXER, "rev-parse", pins["sdk"] + ":sdk") == pins["sdkTree"],
                "historical SDK tree mismatch")
        row["sdkArchiveSHA256"] = campaign.archive(f"{label}-archive-sdk", pins["sdk"], variant,
                                                  "sdk/Sources/MixerCore", "sdk/Sources/MixerUI")
        modules = []
        for name in ("MixerCore", "MixerUI", "FieldLogModels"):
            files = [variant / "Workspace.swift"] if name == "FieldLogModels" else sorted(
                (variant / "sdk/Sources" / name).glob("*.swift"))
            obj = variant / (name + ".o")
            run(f"{label}-build-{name}", args.host_swiftc, "-sdk", mac_sdk, "-swift-version", "6", "-whole-module-optimization",
                "-parse-as-library", "-package-name", "Mixer", "-module-name", name, "-I", variant,
                "-emit-module", "-emit-module-path", variant / (name + ".swiftmodule"),
                "-emit-object", *files, "-o", obj)
            modules.append(obj)
        executable = variant / "oracle"
        run(f"{label}-build-oracle", args.host_swiftc, "-sdk", mac_sdk, "-swift-version", "6", "-parse-as-library", "-package-name", "FieldLog",
            "-I", variant, "-I", include, *modules, library, variant / "TaskEditor.swift",
            variant / "TaskEditorPresentation.swift", HERE / "Replay.swift", HERE / "EditorBoundary.swift", reduction,
            "-o", executable)
        trace = variant / "state-trace"
        stdout = run(f"{label}-differential", executable, guest, pins["axis"], trace, timeout=20)
        row["trace"] = {"bytes": trace.stat().st_size, "sha256": digest(trace.read_bytes())}
        row["observations"] = stdout.splitlines()
    require(receipt["history"]["F05"]["trace"] == receipt["history"]["F06"]["trace"],
            "F05 and F06 shared reducer traces differ")
    receipt["remainingGap"] = {
        label: [line for line in row["observations"] if "fuel_exhausted" in line]
        for label, row in receipt["history"].items()
    }
    receipt["status"] = "PASS_BOUNDED_EDITOR_STATE_DIFFERENTIAL"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swift-toolchain", type=Path, required=True, help="Swift 6.3.3 toolchain usr directory")
    parser.add_argument("--wasm-sdk", type=Path, required=True, help="Swift 6.3.3 wasm32-unknown-wasip1 SDK directory")
    parser.add_argument("--rustc", type=Path, required=True)
    parser.add_argument("--host-swiftc", type=Path, default=Path("/usr/bin/swiftc"),
                        help="macOS Swift compiler matching xcrun's SDK")
    parser.add_argument("--fieldlog", type=Path, help="optional local object database; otherwise clone public FieldLog")
    parser.add_argument("--receipt", type=Path, required=True, help="new file outside disposable scratch")
    args = parser.parse_args()
    for name in ("swift_toolchain", "wasm_sdk", "rustc", "host_swiftc", "receipt", "fieldlog"):
        if path := getattr(args, name):
            setattr(args, name, path.resolve())
    receipt = {
        "schema": 1, "status": "FAILED", "publicRevision": PUBLIC, "publicTree": PUBLIC_TREE, "vmTree": VM_TREE,
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Unsigned host-only F05/F06 title, event admission and cancel state parity via owned table-memory-v3.",
        "limits": {"moduleBytes": MAX_WASM, "memoryPages": 64, "fuelPerInvocation": 1_000_000},
        "sources": {p.name: digest(p.read_bytes()) for p in sorted(HERE.glob("*.swift"))}
                   | {"replay.py": digest(Path(__file__).read_bytes())},
        "commands": [], "history": {}, "localGatesPassed": [], "gaGatesPassed": [],
    }
    with args.receipt.open("x") as destination:
        work = Path(tempfile.mkdtemp(prefix="mixer-fieldlog-embedded-editor-")).resolve()
        campaign = Campaign(work, receipt)
        _, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 * 1024, hard))
        try:
            replay(args, campaign, receipt)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            receipt["failure"] = str(error)
        finally:
            if campaign.held:
                receipt["retainedScratch"] = str(work)
            else:
                shutil.rmtree(work)
            receipt["scratchRemoved"] = not work.exists()
            json.dump(receipt, destination, indent=2)
            destination.write("\n")
    print(receipt.get("failure", receipt["status"]), flush=True)
    return int(receipt["status"] == "FAILED")


if __name__ == "__main__":
    raise SystemExit(main())
