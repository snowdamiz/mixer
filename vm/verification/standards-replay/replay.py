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
MEMORY_GROW = "memory_grow.wast"
MEMORY_GROW_HASH = "8ab4f6e3343f46b4b5aa988de1b102d442228807073838b79563e6b34e2ef0aa"
MEMORY_COPY = "memory_copy.wast"
MEMORY_COPY_HASH = "059813c4cd9e79cf3a287409842b9212f6f48b4a6a5f597f22c81631e7b55d08"
MEMORY_COPY_WASM_HASH = "6e10196de6875cc788a2a0426cda6b733b99c66af7448a2a5458316083e7c14d"
MEMORY_FILL = "memory_fill.wast"
MEMORY_FILL_HASH = "b8a7dccdf72878d11497a5d13ca3c628552b690f5386ef56b0a46c5dd711ad1f"
MEMORY_FILL_WASM_HASH = "3516438ef6b98d2644bf52f43971d21bf102139418fb46d0161dba071bf83c7b"
BR_TABLE_MODULE_LINE = 3
BR_TABLE_FUNCTION_LINES = (86, 105)
BR_TABLE_ASSERTION_LINES = range(1305, 1315)
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
    "elem": {
        "sha256": "ed7c26cb97594adca2ffc3aee436619b6b6d008ead63541e850dc028f88d41fd",
        "modules": {134: "unsupported", 545: "unsupported", 573: "unsupported"},
        "actions": {
            148: ("assert_return", "call-7"),
            149: ("assert_return", "call-9"),
            556: ("assert_return", "call-overwritten"),
            593: ("assert_trap", "call-7"),
            594: ("assert_return", "call-8"),
            595: ("assert_return", "call-9"),
        },
        "invalid": {},
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
    "uninitialized element": "indirect_call_null",
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
                    and action.get("field") == field and module is not None
                    and module["line"] in fixture["modules"]
                    and ("module" not in action
                         or ("name" in module and action["module"] == module["name"])),
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


def expected_return(row, context):
    values = row["expected"]
    require(len(values) <= 1, f"{context}: selected result is outside the scalar subset")
    return value_bits(values[0]) if values else None


def check_native_invocation(report, row, context):
    trap = TRAPS[row["text"]] if row["type"] == "assert_trap" else None
    expect_report(report, 2 if trap else 0, trap or "", context)
    require(report["fuel_used"] > 0, f"{context}: invocation consumed no fuel")
    if trap:
        return

    kind = VALUE_TYPES[report["value_type"]] if report["value_type"] else None
    installed = None
    if kind:
        # The C report carries signed integers, zero-extended f32, or raw f64 bits.
        width = 64 if kind == "f32" else WIDTHS[kind]
        installed = kind, report["value"] % (1 << width)
    expected = expected_return(row, context)
    require(installed == expected, f"{context}: expected {expected}, C={report}")


def validate(commands, label, core, client, validator, wasm, *, invalid, guest_code,
             profile_rejection=""):
    wabt_diagnostic, core_code, guest_code = invalid or ("", profile_rejection, guest_code)
    rejected = bool(core_code)
    raw = commands.run(f"{label}-wabt", [validator, wasm], expected=int(bool(invalid)))
    if invalid:
        require(wabt_diagnostic in raw.decode(), f"{label}: unexpected WABT rejection: {raw!r}")
    core_report = json.loads(commands.run(
        f"{label}-core-validate", [core, "--profile", PROFILE, "validate", wasm],
        expected=2 if rejected else 0,
    ))
    require(core_report["profile"] == PROFILE and core_report["valid"] is (not rejected),
            f"{label}: unexpected core validation: {core_report}")
    require(core_report["error"] is None if not rejected else
            core_report["error"]["code"] == core_code,
            f"{label}: wrong core validation reason: {core_report}")
    reports = native_reports(commands.run(f"{label}-c-validate", [client, wasm]),
                             ("validate", "guest_ui_v1_validate"))
    expect_report(reports["validate"], int(rejected), core_code, label)
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
    check_native_invocation(reports["invoke"], row, f"{label} invoke")

    if trap:
        require(core_report["ok"] is False and core_report["error"]["code"] == trap,
                f"{label}: wrong core trap: {core_report}")
    else:
        expected = expected_return(row, label)
        require(core_report["ok"] is True and core_report["profile"] == PROFILE
                and core_report["export"] == field and core_report["host_calls_used"] == 0
                and core_result(core_report["result"]) == expected,
                f"{label}: expected {expected}, core={core_report}")
    return {"core": core_report, "installed_c": reports}


def translate_stateful(commands, scratch, translator, record, fixture, fixture_hash):
    label = Path(fixture).stem.replace("_", "-")
    directory = scratch / label
    directory.mkdir()
    source = directory / fixture
    url = f"{SPEC_URL}/{fixture}"
    record["fixtures"][fixture] = {
        "url": url, "sha256": fetch(commands, f"{label}-fetch", url, source,
                                    fixture_hash, 512 * 1024),
    }
    manifest = directory / "commands.json"
    commands.run(f"{label}-translate", [translator, source, "-o", manifest])
    return directory, json.loads(manifest.read_text())


def select_stateful_block(script, module_line, filename, lines, *, mutation_line=None):
    commands = script["commands"]
    starts = [index for index, row in enumerate(commands)
              if row["type"] == "module" and row["line"] == module_line]
    require(len(starts) == 1, f"expected one stateful module at line {module_line}")
    start = starts[0]
    module = commands[start]
    require(module["filename"] == filename, f"unexpected translated filename at line {module_line}")
    end = next((index for index in range(start + 1, len(commands))
                if commands[index]["type"] == "module"), len(commands))
    block = commands[start + 1:end]
    selected = [index for index, row in enumerate(block) if row["line"] in lines]
    require(len(selected) == len(lines), f"missing or duplicate stateful lines for {module_line}")
    rows = block[selected[0]:selected[-1] + 1]
    require([row["line"] for row in rows] == list(lines),
            f"stateful lines for {module_line} are out of order or not adjacent")
    for row in rows:
        action = row.get("action", {})
        if row["line"] == mutation_line:
            require(row["type"] == "action" and action == {
                "type": "invoke", "field": "test", "args": [],
            } and row["expected"] == [], f"unexpected mutation at line {mutation_line}")
        else:
            require(row["type"] == "assert_return" and action.get("type") == "invoke"
                    and "module" not in action, f"unexpected assertion at line {row['line']}")
    return module, rows


def replay_reference(commands, directory, script, rows, reference, record):
    manifest = {**script, "commands": rows}
    reference_script = directory / "selected.json"
    reference_script.write_text(json.dumps(manifest))
    record["reference_manifest_sha256"] = digest(reference_script.read_bytes())
    output = commands.run(
        f"{directory.name}-reference", [reference, reference_script],
    ).decode().splitlines()
    record["reference_output"] = output
    count = len(rows)
    require(output[-1:] == [f"{count}/{count} tests passed."],
            f"{directory.name}: incomplete WABT run: {output}")


def replay_br_table(commands, source, script, translator, reference, validator, core, client, record):
    directory = source.parent
    lines = BR_TABLE_ASSERTION_LINES
    selection = {
        "modules": {BR_TABLE_MODULE_LINE: "unsupported"},
        "actions": dict.fromkeys(lines, ("assert_return", "multiple-value")),
        "invalid": {},
    }
    full_cases = list(selected_cases(source.name, script["commands"], selection))
    full_module = full_cases[0][0]
    require(full_module["filename"] == "commands.0.wasm"
            and [row["line"] for _, row in full_cases] == list(lines),
            "br_table: unexpected original module or assertion order")
    full_wasm = directory / full_module["filename"]
    boundary = record["upstream_module"] = {
        "line": full_module["line"], "wasm_sha256": digest(full_wasm.read_bytes()),
        "validation": validate(
            commands, "br-table-upstream-module", core, client, validator, full_wasm,
            invalid=None, guest_code="unsupported", profile_rejection="unsupported",
        ),
    }
    upstream_rows = [row for _, row in full_cases]
    replay_reference(commands, directory, script, [full_module, *upstream_rows], reference, boundary)

    first, last = BR_TABLE_FUNCTION_LINES
    upstream = source.read_bytes().splitlines(keepends=True)
    function = b"".join(upstream[first - 1:last])
    assertions = b"".join(upstream[lines.start - 1:lines.stop - 1])
    # Keep the original source line numbers so the WABT assertion rows can match exactly.
    standalone = (b"\n" * (BR_TABLE_MODULE_LINE - 1) + b"(module\n"
                  + b"\n" * (first - BR_TABLE_MODULE_LINE - 1) + function + b")\n"
                  + b"\n" * (lines.start - last - 2) + assertions)
    excerpt_dir = directory / "br-table-excerpt"
    excerpt_dir.mkdir()
    excerpt = excerpt_dir / source.name
    excerpt.write_bytes(standalone)
    manifest = excerpt_dir / "commands.json"
    commands.run("br-table-excerpt-translate", [translator, excerpt, "-o", manifest])
    translated = json.loads(manifest.read_text())
    module, *rows = translated["commands"]
    require(module == full_module and rows == upstream_rows,
            "br_table: standalone module row or upstream assertions changed")
    wasm = excerpt_dir / module["filename"]
    positive = record["standalone_excerpt"] = {
        "function_lines": [first, last], "assertion_lines": [lines.start, lines.stop - 1],
        "function_sha256": digest(function), "assertions_sha256": digest(assertions),
        "wast_sha256": digest(standalone), "wasm_sha256": digest(wasm.read_bytes()),
        "validation": validate(commands, "br-table-excerpt", core, client, validator, wasm,
                               invalid=None, guest_code="unsupported"),
    }
    replay_reference(commands, excerpt_dir, translated, [module, *rows], reference, positive)
    positive["cases"] = [
        {"upstream": row,
         **invoke(commands, f"br-table-excerpt-{row['line']}", core, client, wasm, row)}
        for row in rows
    ]


def replay_stateful(commands, directory, script, module, sequence, reference, client, record):
    label = directory.name
    wasm = directory / module["filename"]
    # The stock C sequence client repeats its first call in a fresh session.
    reset = sequence[0]
    argv = [client, wasm, "--sequence"]
    for index, row in enumerate(sequence):
        action = row["action"]
        if index:
            argv.append("--")
        argv.extend([action["field"], *(invocation_arg(value) for value in action["args"])])

    record.update(
        module=module, wasm_sha256=digest(wasm.read_bytes()), wasm_bytes=wasm.stat().st_size,
        reset_upstream_line=reset["line"],
    )
    replay_reference(commands, directory, script, [module, *sequence, module, reset],
                     reference, record)

    phases = tuple(f"invoke-{index}" for index in range(len(sequence)))
    reports = native_reports(commands.run(f"{label}-c-sequence", argv),
                             ("create", *phases, "close", "reset-create", "reset-invoke", "reset-close"))
    record["installed_c"] = reports
    for phase in ("create", "close", "reset-create", "reset-close"):
        expect_report(reports[phase], 0, "", f"{label} {phase}")
    for phase, row in zip(phases, sequence, strict=True):
        check_native_invocation(reports[phase], row, f"{label} {phase} line {row['line']}")
    check_native_invocation(reports["reset-invoke"], reset, f"{label} reset")


def replay_memory_growth(commands, scratch, translator, reference, client, record):
    directory, script = translate_stateful(
        commands, scratch, translator, record, MEMORY_GROW, MEMORY_GROW_HASH,
    )
    module, rows = select_stateful_block(script, 1, "commands.0.wasm", range(19, 24))
    stateful = record["stateful"] = {"fixture": MEMORY_GROW, "upstream": rows}
    # Repeating the first grow assertion returns the fresh instance's previous size.
    replay_stateful(commands, directory, script, module, rows, reference, client, stateful)


def replay_memory_copy(commands, scratch, translator, reference, validator, core, client, record):
    directory, script = translate_stateful(
        commands, scratch, translator, record, MEMORY_COPY, MEMORY_COPY_HASH,
    )
    module, rows = select_stateful_block(
        script, 258, "commands.6.wasm", (267, *range(269, 299)), mutation_line=267,
    )
    wasm = directory / module["filename"]
    require(digest(wasm.read_bytes()) == MEMORY_COPY_WASM_HASH, "memory-copy: module SHA-256 mismatch")
    # Address 12 starts at 7 and the upstream post-copy assertion expects 2.
    changed = next(row for row in rows if row["line"] == 281)
    require(changed["action"] == {
        "type": "invoke", "field": "load8_u", "args": [{"type": "i32", "value": "12"}],
    } and changed["expected"] == [{"type": "i32", "value": "2"}],
        "memory-copy: unexpected reset witness")
    reset = {**changed, "expected": [{"type": "i32", "value": "7"}]}
    stateful = record["memory_copy"] = {
        "fixture": MEMORY_COPY, "upstream": rows,
        "initial_and_reset_control": {
            "action_from_upstream_line": reset["line"], "action": reset["action"],
            "expected": reset["expected"],
        },
    }
    stateful["validation"] = validate(
        commands, "memory-copy-258", core, client, validator, wasm,
        invalid=None, guest_code="capability_export",
    )
    replay_stateful(
        commands, directory, script, module, [reset, *rows], reference, client, stateful,
    )
    output = stateful["reference_output"]
    require(output[:-1] == ["test() =>"], f"memory-copy: unexpected WABT mutation output: {output}")


def replay_memory_fill(commands, scratch, translator, reference, validator, core, client, record):
    directory, script = translate_stateful(
        commands, scratch, translator, record, MEMORY_FILL, MEMORY_FILL_HASH,
    )
    module, rows = select_stateful_block(
        script, 145, "commands.7.wasm", (162, 164, 166, 168, 170, 172), mutation_line=162,
    )
    wasm = directory / module["filename"]
    require(digest(wasm.read_bytes()) == MEMORY_FILL_WASM_HASH, "memory-fill: module SHA-256 mismatch")
    overwritten = rows[3]
    action = overwritten["action"]
    require(action == {
        "type": "invoke", "field": "checkRange",
        "args": [{"type": "i32", "value": value} for value in ("21", "25", "170")],
    } and overwritten["expected"] == [{"type": "i32", "value": "4294967295"}],
        "memory-fill: unexpected overwritten range")
    # The same overwritten range must be zero before the fill and on fresh reopen.
    reset = {**overwritten, "action": {
        **action, "args": [*action["args"][:2], {"type": "i32", "value": "0"}],
    }}
    stateful = record["memory_fill"] = {
        "fixture": MEMORY_FILL, "upstream": rows, "initial_and_reset_control": reset,
        "validation": validate(commands, "memory-fill-145", core, client, validator, wasm,
                               invalid=None, guest_code="capability_export"),
    }
    replay_stateful(commands, directory, script, module, [reset, *rows], reference, client, stateful)


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
    tools = [Path("wabt-1.0.37/bin") / name
             for name in ("wast2json", "wasm-validate", "spectest-interp")]
    commands.run("extract-wabt", ["/usr/bin/tar", "-xzf", wabt_archive, *tools])
    translator, validator, reference = (scratch / tool for tool in tools)
    for tool in (translator, validator, reference):
        record["tools"][tool.name] = commands.run(tool.name, [tool, "--version"]).decode().strip()

    replay_memory_growth(commands, scratch, translator, reference, client, record)
    replay_memory_copy(commands, scratch, translator, reference, validator, core, client, record)
    replay_memory_fill(commands, scratch, translator, reference, validator, core, client, record)
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
        reference_rows = []
        translated = json.loads(manifest.read_text())
        if script == "br_table":
            replay_br_table(commands, source, translated, translator, reference, validator,
                            core, client, record["fixtures"][source.name])
        for module, row in selected_cases(script, translated["commands"], fixture):
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
                reference_rows.extend((module, row))
                case.update(invoke(commands, f"{script}-{line}", core, client, wasm, row))
            record["cases"].append(case)
        if reference_rows:
            # Match the CLI and installed client, which start fresh for each assertion.
            replay_reference(commands, directory, translated, reference_rows, reference,
                             record["fixtures"][source.name])


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
        "guest_ui_v1": "admission refusal for original modules and the branch-table excerpt",
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
