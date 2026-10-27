#!/usr/bin/env python3
"""Twelve bounded independent format/production privacy control groups.

No producer runner, adoption suite, runtime, process inventory, or network use.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone

OWN = Path(__file__).resolve().parent
REPO = OWN.parents[1]
CANDIDATE = OWN / "candidate"
SOURCE = CANDIDATE / "inputs/accepted-source/vm"
RUSTC = Path("/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc")
OUT = OWN / "controls"
WORK = OWN / "owned-work"
HEADER = 2560
CAPS = [67108864, 512, 8192, 34, 79966, 8192, 4096, 4096, 4096]
WORDS = [0, 3, 1, 5, 3, 4, 4, 4, 4]
NATIVE = [1, 12, 1, 20, 12, 12, 16, 16, 16]
U64 = (1 << 64) - 1
GROUPS = []

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def packed(values):
    return struct.pack("<" + "Q" * len(values), *values)

def put(data, offset, *values):
    data[offset:offset + 8 * len(values)] = packed(values)

def word(data, offset):
    return struct.unpack_from("<Q", data, offset)[0]

def fixture():
    """Independent synthetic bytes; never calls candidate fixture builder."""
    payloads = [bytes(range(64)), packed([0, 1, 1]), packed([1]),
                packed([0, 1, 1, 1, 0]) * 34, packed([2, 2, 0]),
                packed([1, 0, 4, 1]), packed([5, 1, 0, 0]),
                packed([6, 2, 0, 2]), packed([8, 2, 0, 2])]
    data = bytearray(HEADER)
    data[:8] = b"MIXSNB02"
    put(data, 8, 2, HEADER, HEADER + sum(map(len, payloads)), 9, 1, 1, 34, 64, 7, 8, 664)
    limits = [67108864, 16777216, 1048576, 512000000, 120000]
    put(data, 96, *limits)
    observations = [1, 1, 34, 1, 1, 7, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 768, 1, 1, 65536]
    put(data, 224, *observations)
    put(data, 384, 1, 1, 768, 1, 1, 65536, 0, 0, 1, 65536, 0, 0, 7)
    data[512:520] = b"MIXLPR01"
    put(data, 520, 1, 576, 64, *limits)
    for i in range(6):
        data[584 + 32 * i:616 + 32 * i] = bytes([40 + i]) * 32
    for i in range(4):
        put(data, 776 + 64 * i, i + 10, i + 20, [64, 512, 512, 1000][i], 0o100600, U64, 999999999, 0, 0)
    data[1088:1096] = b"MIXRTB01"
    put(data, 1096, 1, 512, 0, 1)
    put(data, 1128, 67108864, 16777216, 16777216, 8388608, 1, 1, 64000000,
        64, 16384, 4096, 768, 134217728, 268435456, 100000000, 1000000000, 32768, 30000)
    put(data, 1360, 64, 1, 1, 1, 1, 95152, 16777216, 8388608)
    offset, charged = HEADER, 664
    for sid, body in enumerate(payloads):
        count = len(body) if sid == 0 else len(body) // (WORDS[sid] * 8)
        put(data, 1600 + 64 * sid, sid, count, count, NATIVE[sid], count * NATIVE[sid], 1 if sid == 0 else 2, offset, len(body))
        if sid:
            charged += count * NATIVE[sid]
        offset += len(body)
    put(data, 144, 64, 64, charged, 0, charged, 0, charged, 100, 1, 120000)
    put(data, 2176, *range(1, 35))
    return bytes(data) + b"".join(payloads)

def independent_envelope(data):
    """Independent field/extent checks; no proof or full Wasm semantics."""
    assert data[:8] == b"MIXSNB02"
    assert [word(data, p) for p in range(8, 64, 8)] == [2, HEADER, len(data), 9, 1, 1, 34]
    assert len(data) <= HEADER + sum(cap if i == 0 else 8 * WORDS[i] * cap for i, cap in enumerate(CAPS))
    at = HEADER
    rows = []
    for sid in range(9):
        row = [word(data, 1600 + 64 * sid + i * 8) for i in range(8)]
        ident, count, capacity, native, charge, category, offset, extent = row
        assert ident == sid and count <= CAPS[sid] and count <= capacity
        assert native == NATIVE[sid] and charge == capacity * native
        assert category == (1 if sid == 0 else 2)
        assert offset == at and extent == count * (1 if sid == 0 else 8 * WORDS[sid])
        rows.append(row)
        at += extent
    assert at == len(data)
    assert rows[0][1] == word(data, 64) == word(data, 536) == word(data, 1360)
    assert word(data, 1368) == word(data, 224), "runtime type_count differs from immutable snapshot"
    assert word(data, 392) == word(data, 328), "memory minimum duplicates differ"
    assert word(data, 400) == word(data, 352), "memory host maximum duplicates differ"
    assert word(data, 416) == word(data, 360), "table minimum duplicates differ"
    assert [word(data, 432), word(data, 440)] == [word(data, 336), word(data, 344)], "memory declared maximum duplicates differ"
    assert [word(data, 448), word(data, 456)] == [word(data, 368), word(data, 376)], "table declared maximum duplicates differ"
    return rows

def group(ident, name, subcases):
    value = {"id": ident, "name": name, "subcases": subcases,
             "expectation_met": all(c["expectation_met"] for c in subcases)}
    GROUPS.append(value)
    write(OUT / (ident + ".json"), value)
    print(ident, "PASS" if value["expectation_met"] else "FAIL", flush=True)

def format_case(model, name, data, accept):
    path = OUT / "fixtures" / (name + ".bin")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    try:
        result = model.parse(data)
        accepted, refusal = True, None
    except model.Refused as e:
        accepted, refusal = False, str(e)
    try:
        independent_envelope(data)
        independent, detail = True, None
    except (AssertionError, struct.error) as e:
        independent, detail = False, str(e)
    return {"name": name, "fixture_sha256": sha(data), "bytes": len(data),
            "expected_candidate_acceptance": accept, "candidate_accepted": accepted,
            "candidate_refusal": refusal, "independent_envelope_accepted": independent,
            "independent_detail": detail, "expectation_met": accepted == accept}

def changed(base, offset, value):
    data = bytearray(base)
    put(data, offset, value)
    return bytes(data)

def formats():
    spec = importlib.util.spec_from_file_location("owned_candidate_format_model", CANDIDATE / "format_model.py")
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    base = fixture()
    cap = HEADER + CAPS[0] + sum(8 * WORDS[i] * CAPS[i] for i in range(1, 9))
    group("F01", "independent maximum and deterministic envelope", [
        {"name": "cap-derived-from-accepted-policy", "derived_cap": cap, "candidate_cap": model.SNAPSHOT_CAP, "expectation_met": cap == 69765152 == model.SNAPSHOT_CAP},
        format_case(model, "independent-positive", base, True),
        {"name": "fixture-deterministic", "expectation_met": base == fixture()}])
    group("F02", "exact scalar optional enum and reserved grammar", [
        format_case(model, "bad-reserved", changed(base, 136, 1), False),
        format_case(model, "bad-option-tag", changed(base, 336, 2), False),
        format_case(model, "bad-absent-option-payload", changed(base, 344, 1), False),
        format_case(model, "bad-resolved-import", changed(base, 2176, 35), False)])
    group("F03", "buffer coverage and duplicated immutable metadata", [
        format_case(model, "bad-buffer-charge", changed(base, 1600 + 64 + 32, 13), False),
        format_case(model, "bad-memory-minimum-duplicate", changed(base, 392, 2), False),
        format_case(model, "bad-memory-host-duplicate", changed(base, 400, 767), False),
        format_case(model, "bad-table-minimum-duplicate", changed(base, 416, 2), False),
        format_case(model, "bad-table-max-option-duplicate", changed(changed(base, 448, 0), 456, 0), False)])
    group("F04", "truncated trailing gap duplicate and reordered sections", [
        format_case(model, "truncation", base[:-1], False),
        format_case(model, "trailer", base + b"x", False),
        format_case(model, "gap", changed(base, 1600 + 64 + 48, word(base, 1600 + 64 + 48) + 1), False),
        format_case(model, "duplicate-id", changed(base, 1664, 0), False)])
    some = changed(base, 1112, 1)
    group("F05", "provenance signed identities and contextual runtime duplicates", [
        format_case(model, "signed-identity-preserved", base, True),
        {"name": "signed-mtime-decoded-exactly", "signed_mtime": struct.unpack_from("<q", base, 808)[0], "expectation_met": struct.unpack_from("<q", base, 808)[0] == -1},
        format_case(model, "some-wasi-zero-distinct-from-none", some, True),
        format_case(model, "bad-runtime-type-count-duplicate", changed(base, 1368, 2), False),
        format_case(model, "bad-source-provenance-duplicate", changed(base, 536, 63), False)])
    group("F06", "ceiling overflow and unknown tags fail closed", [
        format_case(model, "bad-run-ceiling", changed(base, 1128, CAPS[0] + 1), False),
        format_case(model, "overflow-capacity", changed(base, 1600 + 64 + 16, U64), False),
        format_case(model, "unknown-policy", changed(base, 40, 2), False),
        format_case(model, "unknown-version", changed(base, 8, 3), False),
        format_case(model, "unknown-section-id", changed(base, 1600 + 64 * 8, 9), False)])

def manifest(root):
    members = [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())}
               for p in sorted(root.rglob("*")) if p.is_file()]
    return {"members": members, "member_count": len(members),
            "tree_sha256": sha(json.dumps(members, sort_keys=True, separators=(",", ":")).encode())}

def compile_command(name, argv, expected=None):
    folder = OUT / "compiler" / name
    folder.mkdir(parents=True)
    start = time.monotonic()
    env = os.environ.copy()
    env["CARGO_MANIFEST_DIR"] = str(WORK / "source")
    env["TMPDIR"] = str(WORK / "tmp")
    try:
        completed = subprocess.run([str(v) for v in argv], cwd=OWN, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=50)
        code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
        timed_out = False
    except subprocess.TimeoutExpired as e:
        code, stdout, stderr, timed_out = 124, e.stdout or b"", e.stderr or b"", True
    (folder / "stdout").write_bytes(stdout)
    (folder / "stderr").write_bytes(stderr)
    errors = []
    for line in stderr.decode(errors="replace").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("level") == "error" and d.get("code"):
            errors.append(d["code"]["code"])
    met = code == 0 if expected is None else (code != 0 and set(errors) == {expected} and not timed_out)
    value = {"name": name, "argv": [str(v) for v in argv], "cwd": str(OWN),
             "environment": {k: env[k] for k in ["CARGO_MANIFEST_DIR", "TMPDIR"]},
             "exit_code": code, "elapsed_seconds": time.monotonic() - start,
             "expected_error": expected, "error_codes": errors, "expectation_met": met,
             "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr),
             "timeout_seconds": 50, "timed_out": timed_out, "child_reaped": True}
    write(folder / "receipt.json", value)
    return value

def compilers():
    assert not WORK.exists()
    WORK.mkdir()
    (WORK / "tmp").mkdir()
    shutil.copytree(SOURCE, WORK / "source")
    before = manifest(WORK / "source")
    assert before["member_count"] == 144 and before["tree_sha256"] == "9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb"
    write(OUT / "production-source-manifest.json", before)
    features = ["experimental-swift-reactor", "experimental-swift-wasi", "experimental-stream-validation", "experimental-function-cache"]
    common = [RUSTC, "--edition=2021", "--target", "aarch64-apple-darwin", "--error-format=json", "-C", "overflow-checks=yes"]
    for feature in features:
        common += ["--cfg", 'feature="' + feature + '"']
    builds = []
    for mode, opt in [("debug", "0"), ("optimized", "3")]:
        builds.append(compile_command("baseline-" + mode, common + ["--crate-name", "mixer_vm", "--crate-type", "lib", "--emit=metadata", "-C", "opt-level=" + opt, WORK / "source/src/lib.rs", "-o", WORK / ("libmixer_vm_" + mode + ".rmeta")]))
    group("P01", "ordinary production accepted source compiles", builds)
    cases = {
        "P02": ("proof private construction and fields", [
            ("private-proof-field", "E0616", "fn f(p:&mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor){let _=&p.metadata;}"),
            ("private-proof-source-field", "E0616", "fn f(p:&mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor){let _=&p.source;}")]),
        "P03": ("nonclone proof and immutable source", [
            ("proof-clone", "E0599", "fn f(p:mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor){let _=p.clone();}"),
            ("source-mutation", "E0594", "fn f(p:mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor){p.source()[0]=1;}")]),
        "P04": ("external guard construction module private", [
            ("private-guard-path", "E0603", "use mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::InitialProfileBorrowV1;")]),
        "P05": ("owned proof borrow and move escapes", [
            ("source-lifetime-escape", "E0515", "fn f(p:mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor)->&'static[u8]{p.source()}"),
            ("proof-use-after-move", "E0382", "fn f(p:mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor){drop(p);let _=p.source();}")]),
        "P06": ("provenance and runtime private mint routes", [
            ("private-provenance-path", "E0603", "use mixer_vm::experimental_swift_reactor::retained_profile_loader_v1::SelectedValidatedProfileV1;"),
            ("private-control-path", "E0603", "use mixer_vm::experimental_swift_reactor::control::RuntimeControl;")]),
    }
    for ident, (name, entries) in cases.items():
        records = []
        for label, error, source in entries:
            p = OUT / "compiler-cases" / (label + ".rs")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("#![allow(dead_code,unused_imports)]\n" + source + "\n")
            records.append(compile_command(label, common + ["--crate-name", "independent_case", "--crate-type", "lib", "--emit=metadata", "--extern", "mixer_vm=" + str(WORK / "libmixer_vm_debug.rmeta"), p, "-o", WORK / "case.rmeta"], error))
        group(ident, name, records)
    assert manifest(WORK / "source") == before

def main():
    assert not OUT.exists(), "Never overwrite controls/failures"
    OUT.mkdir()
    started = datetime.now(timezone.utc).isoformat()
    try:
        formats()
        compilers()
    finally:
        if WORK.exists():
            shutil.rmtree(WORK)
        result = {"schema": 1, "started": started, "at": datetime.now(timezone.utc).isoformat(),
                  "runner_sha256": sha(Path(__file__).read_bytes()), "candidate_seal_sha256": sha((CANDIDATE / "seal.json").read_bytes()),
                  "source_tree_sha256": "9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb",
                  "groups": GROUPS, "group_count": len(GROUPS),
                  "passed_groups": sum(g["expectation_met"] for g in GROUPS),
                  "failed_groups": [g["id"] for g in GROUPS if not g["expectation_met"]],
                  "scope": "Independent synthetic format contradictions and accepted baseline ordinary-production privacy; not proposed exporter behavior or bridge implementation.",
                  "producer_runner_replayed": False, "adoption_suites_replayed": False,
                  "cleanup": {"owned_work_removed": not WORK.exists(), "compiler_products_retained": False,
                              "owned_children_reaped": True, "native_UI_capture_process_inventory": False}}
        write(OWN / "controls-result.json", result)
        print(json.dumps({k: result[k] for k in ["group_count", "passed_groups", "failed_groups", "cleanup"]}), flush=True)
    return 0 if len(GROUPS) == 12 and all(g["expectation_met"] for g in GROUPS) else 1

if __name__ == "__main__":
    sys.exit(main())
