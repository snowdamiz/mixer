#!/usr/bin/env python3
"""Replay a fixed subset of upstream WebAssembly Core assertions on macOS."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import signal
import sys
import tarfile
import tempfile

sys.dont_write_bytecode = True
from commands import Commands, digest, preserve, publish_json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = "05ca4182176763112561ae20153975c12bd689e4"
SPEC_URL = f"https://raw.githubusercontent.com/WebAssembly/spec/{SPEC}/test/core"
WABT_URL = (
    "https://github.com/WebAssembly/wabt/releases/download/1.0.37/"
    "wabt-1.0.37-macos-14.tar.gz"
)
WABT_HASH = "a996907cbdf1bdcd56d66d382dd1b031450bb7326bbfd0f43a04486b620bed1c"
PROFILE = "mixer-table-memory-v3"
FEATURE = "experimental-capability-native"
MAX_EXPORT_BYTES = 32 * 1024 * 1024
CARGO_CWD = Path("/")
CLIENT = "verification/standards-replay/client.c"
HEADERS = (
    "mixer_vm.h", "mixer_vm_capability.h", "mixer_vm_guest_ui.h",
    "mixer_vm_guest_ui_deferred.h",
)

# Line selection pins both the assertion and, for an invoke, its module context.
# Unselected commands are never dispatched.
FIXTURES = {
    "unreached-valid": {
        "sha256": "15f2f0a2b2619fbc80324bf832cdb09b19123bb7003df89bc6ae76ddaa597405",
        "modules": {49: "unsupported"},
        "actions": {63: ("assert_trap", "meet-bottom")},
        "invalid": {},
    },
    "i32": {
        "sha256": "f3b7e8fd641893ea0989a8ab801fce0654d276d27b5cad9cf482291a422cffe8",
        "modules": {3: "unsupported"},
        "actions": {
            39: ("assert_return", "add"),
            41: ("assert_return", "add"),
            64: ("assert_trap", "div_s"),
            66: ("assert_trap", "div_s"),
            72: ("assert_return", "div_s"),
            220: ("assert_return", "rotl"),
            228: ("assert_return", "rotl"),
        },
        "invalid": {444: ("type mismatch", "validation", "unsupported")},
    },
    "memory": {
        "sha256": "9356ea6a84252e61421bbe7560a8244983accf0266f36986dbf94eaacfff80df",
        "modules": {92: "capability_export"},
        "actions": {
            180: ("assert_return", "data"),
            181: ("assert_return", "cast"),
            183: ("assert_return", "i32_load8_s"),
            184: ("assert_return", "i32_load8_u"),
            207: ("assert_return", "i64_load32_u"),
        },
        "invalid": {51: ("must be >= initial pages", "limit", "limit")},
    },
    "br_table": {
        "sha256": "e9106d4f8f7bb0c12f51b2cc4bb443166c1d033be7ced74047f3705b2441167d",
        "modules": {},
        "actions": {},
        "invalid": {
            1462: ("type mismatch in br_table", "validation", "unsupported"),
            1481: ("type mismatch in br_table", "validation", "unsupported"),
            1605: ("invalid depth", "validation", "unsupported"),
        },
    },
    "load": {
        "sha256": "2f69ef5634207e065d022d7c26c92016ff1d14a94c5c755927d37fe14e63e256",
        "modules": {},
        "actions": {},
        "invalid": {312: ("type mismatch", "validation", "validation")},
    },
}
TRAPS = {
    "unreachable": "unreachable",
    "integer divide by zero": "integer_divide_by_zero",
    "integer overflow": "integer_overflow",
}
VALUE_TYPES = {1: "i32", 2: "i64", 3: "f32", 4: "f64"}
WIDTHS = {"i32": 32, "i64": 64, "f32": 32, "f64": 64}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def fetch(commands, name, url, destination, expected_hash, maximum):
    commands.run(name, [
        "/usr/bin/curl", "-qfsSL", "--proto", "=https", "--proto-redir", "=https",
        "--max-time", "25", "--max-filesize", maximum, "-o", destination, url,
    ])
    require(destination.stat().st_size <= maximum, f"{name}: download exceeds byte cap")
    observed = digest(destination.read_bytes())
    require(observed == expected_hash, f"{name}: SHA-256 mismatch ({observed})")
    return observed


def selected_cases(script, rows, fixture):
    module = None
    actions = fixture["actions"]
    invalid = fixture["invalid"]
    seen = set()
    for row in rows:
        kind, line = row["type"], row["line"]
        if kind == "module":
            module = row
        if line in actions:
            expected_kind, field = actions[line]
            action = row.get("action", {})
            require(line not in seen and kind == expected_kind and action.get("type") == "invoke"
                    and action.get("field") == field and "module" not in action
                    and module is not None and module["line"] in fixture["modules"],
                    f"{script}:{line}: unexpected assertion or module context")
            seen.add(line)
            yield module, row
        if line in invalid:
            require(line not in seen and kind == "assert_invalid" and row["module_type"] == "binary",
                    f"{script}:{line}: expected a binary assert_invalid")
            seen.add(line)
            yield row, row
    require(seen == actions.keys() | invalid.keys(), f"{script}: selected lines missing")


def value_bits(value):
    kind = value["type"]
    width = WIDTHS[kind]
    bits = int(value["value"])
    require(0 <= bits < 1 << width, f"{kind}: expected a WABT unsigned bit value")
    return kind, bits


def invocation_arg(value):
    kind, bits = value_bits(value)
    require(kind in ("i32", "i64"), f"{kind}: selected argument must be integer")
    width = WIDTHS[kind]
    signed = bits if bits < 1 << (width - 1) else bits - (1 << width)
    return f"{kind}:{signed}"


def core_result(result):
    if result is None:
        return None
    kind = result["type"]
    if kind in ("f32", "f64"):
        return kind, int(result["bits"], 16)
    return kind, int(result["value"]) % (1 << WIDTHS[kind])


def native_reports(raw, phases):
    reports = {}
    for line in raw.decode().splitlines():
        phase, status, report_status, abi, kind, value, fuel, host_calls, code = line.split("\t")
        require(phase not in reports and int(status) == int(report_status) and int(abi) == 1,
                f"C ABI report mismatch in {phase}: {line}")
        reports[phase] = {
            "status": int(status), "code": code, "value_type": int(kind), "value": int(value),
            "fuel_used": int(fuel), "host_calls_used": int(host_calls),
        }
    require(tuple(reports) == phases, f"unexpected C ABI phases: {tuple(reports)}")
    return reports


def expect_report(report, status, code, context):
    require((report["status"], report["code"]) == (status, code),
            f"{context}: expected status/code {(status, code)}, got {report}")
    require(report["host_calls_used"] == 0, f"{context}: unexpected host calls")


def validate(commands, label, core, client, validator, wasm, *, invalid, guest_code):
    wabt_diagnostic, core_code, guest_code = invalid or ("", "", guest_code)
    raw = commands.run(f"{label}-wabt", [validator, wasm], expected=int(bool(invalid)))
    if invalid:
        require(wabt_diagnostic in raw.decode(), f"{label}: unexpected WABT rejection: {raw!r}")
    core_report = json.loads(commands.run(
        f"{label}-core-validate", [core, "--profile", PROFILE, "validate", wasm],
        expected=2 if invalid else 0,
    ))
    require(core_report["profile"] == PROFILE and core_report["valid"] is (not invalid),
            f"{label}: unexpected core validation: {core_report}")
    require(core_report["error"] is None if not invalid else
            core_report["error"]["code"] == core_code,
            f"{label}: wrong core validation reason: {core_report}")
    reports = native_reports(commands.run(f"{label}-c-validate", [client, wasm]),
                             ("validate", "guest_ui_v1_validate"))
    expect_report(reports["validate"], int(bool(invalid)), core_code, label)
    expect_report(reports["guest_ui_v1_validate"], 1, guest_code, label)
    return {
        "wabt": {"status": int(bool(invalid)), "diagnostic": raw.decode().splitlines()[:1]},
        "core": {"valid": core_report["valid"], "error": core_report["error"]},
        "installed_c": reports,
    }


def invoke(commands, label, core, client, wasm, row):
    action = row["action"]
    field, args = action["field"], [invocation_arg(value) for value in action["args"]]
    trap = TRAPS[row["text"]] if row["type"] == "assert_trap" else None
    core_report = json.loads(commands.run(
        f"{label}-core-invoke", [core, "--profile", PROFILE, "invoke", wasm, field, *args],
        expected=2 if trap else 0,
    ))
    reports = native_reports(commands.run(f"{label}-c-invoke", [client, wasm, field, *args]),
                             ("create", "invoke", "close"))
    for phase in ("create", "close"):
        expect_report(reports[phase], 0, "", f"{label} {phase}")
    invocation = reports["invoke"]
    expect_report(invocation, 2 if trap else 0, trap or "", f"{label} invoke")
    require(invocation["fuel_used"] > 0, f"{label}: invocation consumed no fuel")

    if trap:
        require(core_report["ok"] is False and core_report["error"]["code"] == trap,
                f"{label}: wrong core trap: {core_report}")
    else:
        expected = row["expected"]
        require(len(expected) <= 1, f"{label}: selected result is outside the scalar subset")
        expected = value_bits(expected[0]) if expected else None
        kind = VALUE_TYPES[invocation["value_type"]] if invocation["value_type"] else None
        installed = None
        if kind:
            # The C report carries signed integers, zero-extended f32, or raw f64 bits.
            width = 64 if kind == "f32" else WIDTHS[kind]
            installed = kind, invocation["value"] % (1 << width)
        require(core_report["ok"] is True and core_report["profile"] == PROFILE
                and core_report["export"] == field and core_report["host_calls_used"] == 0
                and core_result(core_report["result"]) == expected and installed == expected,
                f"{label}: expected {expected}, core={core_report}, C={invocation}")
    return {"core": core_report, "installed_c": reports}


def copy_install(scratch, release, source):
    include = scratch / "install/include"
    lib = scratch / "install/lib"
    include.mkdir(parents=True)
    lib.mkdir()
    archive = lib / "libmixer_vm_capability_experimental.a"
    shutil.copyfile(release / "libmixer_vm.a", archive)
    for header in HEADERS:
        shutil.copyfile(source / "include" / header, include / header)
    return include, archive


def export_vm(commands, root, scratch, record):
    git = ["/usr/bin/git", "--no-replace-objects", "-C", root]
    revision = commands.run("revision", [*git, "rev-parse", "HEAD^{commit}"]).decode().strip()
    tree = commands.run("vm-tree", [*git, "rev-parse", f"{revision}:vm"]).decode().strip()
    record.update(source_revision=revision, vm_tree=tree)
    listing = commands.run("vm-blobs", [*git, "ls-tree", "-rz", tree])
    expected = {}
    for entry in listing.rstrip(b"\0").split(b"\0"):
        metadata, name = entry.decode().split("\t", 1)
        mode, kind, blob = metadata.split()
        path = Path(name)
        require(kind == "blob" and mode in ("100644", "100755") and not path.is_absolute()
                and ".." not in path.parts and str(path) == name and path.parts,
                f"unsupported VM tree entry {name}")
        expected[name] = blob, mode

    archive = scratch / "vm.tar"
    commands.run("export-vm", [*git, "archive", "--format=tar", "--output", archive, tree])
    require(archive.stat().st_size <= MAX_EXPORT_BYTES, "VM export exceeds byte cap")
    source = scratch / "vm"
    source.mkdir()
    observed = set()
    with tarfile.open(archive, mode="r:") as bundle:
        for member in bundle:
            if member.isdir():
                continue
            name = member.name
            require(member.isfile() and name in expected and name not in observed
                    and 0 <= member.size <= MAX_EXPORT_BYTES, f"unexpected VM archive entry {name}")
            blob, mode = expected[name]
            with bundle.extractfile(member) as stream:
                data = stream.read()
            header = f"blob {len(data)}\0".encode()
            require(hashlib.sha1(header + data).hexdigest() == blob,
                    f"VM archive blob mismatch: {name}")
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
            path.chmod(int(mode[-3:], 8))
            observed.add(name)
    require(observed == expected.keys(), "VM archive omitted committed files")
    record["vm_export_files"] = len(observed)
    return source, {source / name for name in observed}


def require_absent(path, description):
    try:
        path.lstat()
    except FileNotFoundError:
        return
    raise RuntimeError(f"unexpected {description}: {path}")


def guard_cargo(source, cwd, cargo_home):
    config_directories = [cargo_home, *(directory / ".cargo" for directory in (cwd, *cwd.parents))]
    for directory in config_directories:
        for filename in ("config", "config.toml"):
            require_absent(directory / filename, "Cargo configuration")
    for directory in source.parents:
        require_absent(directory / "Cargo.toml", "Cargo ancestor manifest")


def build_vm(commands, source, files, rust, record):
    cargo_home = Path(commands.env["CARGO_HOME"])
    manifest = source / "Cargo.toml"
    cargo = [rust / "cargo", "--locked", "--offline"]
    guard_cargo(source, CARGO_CWD, cargo_home)
    metadata = json.loads(commands.run(
        "cargo-metadata", [*cargo, "metadata", "--no-deps", "--format-version", "1",
                           "--manifest-path", manifest], cwd=CARGO_CWD,
    ))
    packages = metadata["packages"]
    require(Path(metadata["workspace_root"]) == source and len(packages) == 1,
            "Cargo resolved an unexpected workspace")
    package = packages[0]
    require(Path(package["manifest_path"]) == manifest and not package["dependencies"]
            and all(Path(target["src_path"]) in files for target in package["targets"]),
            "Cargo resolved inputs outside the committed VM package")
    record["cargo_targets"] = [
        {"kind": target["kind"], "path": str(Path(target["src_path"]).relative_to(source))}
        for target in package["targets"]
    ]
    guard_cargo(source, CARGO_CWD, cargo_home)
    commands.run("build", [*cargo, "build", "--release", "--lib", "--bin", "mixer-vm",
                           "--no-default-features", "--features", FEATURE, "--manifest-path", manifest],
                 cwd=CARGO_CWD, timeout=90)
    guard_cargo(source, CARGO_CWD, cargo_home)


def replay(commands, scratch, rust, record):
    source, files = export_vm(commands, ROOT, scratch, record)
    guard_cargo(source, CARGO_CWD, Path(commands.env["CARGO_HOME"]))
    record["tools"] = {
        "python": sys.version.split()[0],
        "macos": commands.run("macos", ["/usr/bin/sw_vers"]).decode().strip(),
        "cargo": commands.run("cargo-version", [rust / "cargo", "--version"], cwd=CARGO_CWD).decode().strip(),
        "rustc": commands.run("rustc-version", [rust / "rustc", "--version"]).decode().strip(),
        "clang": commands.run("clang-version", ["/usr/bin/clang", "--version"]).decode().strip(),
        "curl": commands.run("curl-version", ["/usr/bin/curl", "--version"]).decode().splitlines()[0],
    }
    build_vm(commands, source, files, rust, record)
    release = scratch / "target/release"
    core = release / "mixer-vm"
    include, archive = copy_install(scratch, release, source)
    client = scratch / "client"
    commands.run("link-client", ["/usr/bin/clang", "-std=c11", "-Wall", "-Wextra", "-Werror",
                                 "-I", include, source / CLIENT, archive, "-o", client])
    record["artifacts_sha256"] = {
        path.name: digest(path.read_bytes()) for path in (core, archive, client, *include.iterdir())
    }

    wabt_archive = scratch / "wabt.tar.gz"
    fetch(commands, "download-wabt", WABT_URL, wabt_archive, WABT_HASH, 24 * 1024 * 1024)
    translator, validator = [Path("wabt-1.0.37/bin") / name for name in ("wast2json", "wasm-validate")]
    commands.run("extract-wabt", ["/usr/bin/tar", "-xzf", wabt_archive, translator, validator])
    translator, validator = scratch / translator, scratch / validator
    for tool in (translator, validator):
        record["tools"][tool.name] = commands.run(tool.name, [tool, "--version"]).decode().strip()

    for script, fixture in FIXTURES.items():
        directory = scratch / script
        directory.mkdir()
        source = directory / f"{script}.wast"
        url = f"{SPEC_URL}/{source.name}"
        record["fixtures"][source.name] = {
            "url": url, "sha256": fetch(commands, f"{script}-fetch", url, source,
                                        fixture["sha256"], 512 * 1024),
        }
        manifest = directory / "commands.json"
        commands.run(f"{script}-translate", [translator, source, "-o", manifest])
        validated = {}
        for module, row in selected_cases(script, json.loads(manifest.read_text())["commands"], fixture):
            line, module_line = row["line"], module["line"]
            filename = module["filename"]
            require(re.fullmatch(re.escape(manifest.stem) + r"\.\d+\.wasm", filename),
                    f"{script}:{line}: unsafe or unexpected translated filename {filename}")
            wasm = directory / filename
            if module_line not in validated:
                invalid = fixture["invalid"].get(line)
                validation = validate(
                    commands, f"{script}-{module_line}", core, client, validator, wasm,
                    invalid=invalid, guest_code=fixture["modules"].get(module_line),
                )
                validated[module_line] = digest(wasm.read_bytes())
                record["modules"].append({
                    "fixture": source.name, "line": module_line, "wasm_sha256": validated[module_line],
                    "wasm_bytes": wasm.stat().st_size, **validation,
                })
            case = {"fixture": source.name, "module_line": module_line, "upstream": row}
            if row["type"] != "assert_invalid":
                case.update(invoke(commands, f"{script}-{line}", core, client, wasm, row))
            record["cases"].append(case)


def finish(scratch, receipt, record):
    try:
        publish_json(receipt, record)
    except BaseException as error:
        preserve(scratch, "receipt-unpublished.json", {
            **record, "receipt_publication_error": str(error),
        })
        print(f"receipt publication failed for {receipt}: {error}", file=sys.stderr)
        return 74
    try:
        shutil.rmtree(scratch)
    except OSError as error:
        print(f"scratch cleanup failed for {scratch}: {error}", file=sys.stderr)
        return 1
    print(f"{record['status']} {receipt}")
    if record["status"] != "passed_scoped_replay":
        print(record["error"], file=sys.stderr)
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rust-bin", required=True, type=Path, help="toolchain bin containing cargo and rustc")
    parser.add_argument("--receipt", required=True, type=Path, help="new JSON receipt path")
    args = parser.parse_args()
    if sys.platform != "darwin" or platform.machine() != "arm64":
        parser.error("the pinned WABT package requires arm64 macOS")
    rust = args.rust_bin.resolve(strict=True)
    for name in ("cargo", "rustc"):
        if not os.access(rust / name, os.X_OK):
            parser.error(f"missing executable {rust / name}")
    receipt = args.receipt.absolute()
    if os.path.lexists(receipt) or not receipt.parent.is_dir():
        parser.error("--receipt must name a new file in an existing directory")

    home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True)
    scratch = Path(tempfile.mkdtemp(prefix=".mixer-vm-standards-", dir=home))
    env = {
        "HOME": str(scratch / "home"), "PATH": f"{rust}:/usr/bin:/bin:/usr/sbin:/sbin",
        "RUSTC": str(rust / "rustc"), "CARGO_HOME": str(scratch / "cargo-home"),
        "CARGO_TARGET_DIR": str(scratch / "target"), "TMPDIR": str(scratch / "tmp"),
        "MACOSX_DEPLOYMENT_TARGET": "14.0", "LANG": "C", "LC_ALL": "C",
        "GIT_NO_LAZY_FETCH": "1", "GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_ATTR_NOSYSTEM": "1",
    }
    commands = Commands(scratch, env)
    signal.signal(signal.SIGINT, commands.interrupt)
    signal.signal(signal.SIGTERM, commands.interrupt)
    record = {
        "status": "incomplete",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "runner_argv": sys.argv,
        "scratch": str(scratch),
        "scratch_cleanup": "after durable receipt publication and terminal process custody",
        "spec_revision": SPEC,
        "wabt_release": {"url": WABT_URL, "sha256": WABT_HASH},
        "profile": PROFILE,
        "installed_feature": FEATURE,
        "installed_execution": "legacy V3 session C ABI from the installed capability archive",
        "guest_ui_v1": "admission refusal only for unchanged upstream modules",
        "fixtures": {}, "modules": [], "cases": [],
    }
    record["command_environment"] = env
    try:
        for name in ("home", "cargo-home", "tmp"):
            (scratch / name).mkdir()
        record["runner_sha256"] = {p.name: digest(p.read_bytes()) for p in
                                   (HERE / "replay.py", HERE / "commands.py")}
        replay(commands, scratch, rust, record)
        commands.check_interrupt()
        record["status"] = "passed_scoped_replay"
    except (Exception, KeyboardInterrupt) as error:
        record["error"] = str(error)
    record["commands"] = commands.rows
    record["assertion_counts"] = dict(Counter(case["upstream"]["type"] for case in record["cases"]))
    return finish(scratch, receipt, record)


if __name__ == "__main__":
    sys.exit(main())
