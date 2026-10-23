#!/usr/bin/env python3
"""Bound a proposal audit to current source and compiler layouts; no Wasm admission."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUSTC = Path("/opt/homebrew/opt/rustup/bin/rustc")
TARGET = ROOT / "compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm"
DIAGNOSTICS = ROOT / "verification/swift-reactor-function-diagnostics/2026-10-23-reactor-final-v2"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command, name, env=None):
    value = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=60)
    (OUT / f"{name}.stdout").write_bytes(value.stdout)
    (OUT / f"{name}.stderr").write_bytes(value.stderr)
    if value.returncode:
        raise RuntimeError(f"{name} failed: {value.returncode}")
    return {"command": [str(x) for x in command], "exitCode": value.returncode,
            "stdout": {"path": f"{name}.stdout", "sha256": sha(OUT / f"{name}.stdout")},
            "stderr": {"path": f"{name}.stderr", "sha256": sha(OUT / f"{name}.stderr")}}


def section_payload_bytes(path):
    # A bounded framing diagnostic only. No section contents, bodies or types are validated.
    data = path.read_bytes()
    if data[:8] != b"\0asm\x01\0\0\0":
        raise ValueError("header")
    at, total = 8, 0
    records = []
    while at < len(data):
        section_id = data[at]
        at += 1
        size = 0
        for index in range(5):
            if at >= len(data):
                raise ValueError("truncated section length")
            byte = data[at]
            at += 1
            if index == 4 and byte & 0xF0:
                raise ValueError("section length overflow")
            size |= (byte & 127) << (7 * index)
            if byte & 128 == 0:
                break
        else:
            raise ValueError("unterminated section length")
        if at + size > len(data):
            raise ValueError("section extent")
        records.append({"id": section_id, "offset": at, "bytes": size})
        total += size
        at += size
    return total, records


def main():
    (OUT / "local/layout").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, RUSTC_BOOTSTRAP="1", RUSTUP_AUTO_INSTALL="0")
    compiler = [str(RUSTC), "--edition=2021", "--crate-type", "rlib"]
    for feature in ("experimental-stream-validation", "experimental-function-cache",
                    "experimental-span-execution", "experimental-swift-wasi"):
        compiler += ["--cfg", f'feature="{feature}"']
    compiler += ["-Zprint-type-sizes", "--out-dir", str(OUT / "local/layout"), "vm/src/lib.rs"]
    commands = [run([str(RUSTC), "--version"], "rustc-version"), run(compiler, "layout", env)]
    raw = (OUT / "layout.stdout").read_text()
    # Compiler diagnostic parsing is used only for arithmetic, never guest admission.
    layouts = {name: int(size) for name, size in re.findall(
        r"^print-type-size type: `([^`]+)`: ([0-9]+) bytes, alignment: [0-9]+ bytes$", raw, re.M)}
    needed = ["Type", "std::option::Option<Type>", "Value", "experimental::ValidatedSpans",
              "experimental::Failure", "experimental::metadata::Signature",
              "experimental::metadata::Import", "experimental::metadata::Function",
              "experimental::metadata::Global", "experimental::metadata::Export",
              "experimental::metadata::Segment", "experimental::validate::Control",
              "experimental::validate::BodyState", "experimental::account::Meter<'_>",
              "experimental::account::Buffer<u32>", "experimental::reader::Reader<'_>",
              "experimental::cache::decode::Patch", "experimental::cache::decode::PassState",
              "experimental::cache::DecodedInstruction", "experimental_wasi::WasiContext"]
    selected = {name: layouts[name] for name in needed}
    (OUT / "layout-sizes.json").write_text(json.dumps(selected, indent=2) + "\n")
    receipt = json.loads((DIAGNOSTICS / "receipt.json").read_text())
    stats = json.loads((DIAGNOSTICS / "statistics.json").read_text())
    descriptors_path = ROOT / "compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/descriptors.json"
    descriptors = json.loads(descriptors_path.read_text())
    observed = receipt["observed"]
    assert receipt["valid"] is False and stats["valid"] is False
    assert TARGET.stat().st_size == 53_777_114
    assert sha(TARGET) == receipt["artifact"]["sha256"] == "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"
    assert observed["functions"] == stats["function_count"] == 79_832
    assert observed["functions"] + observed["imports"] == descriptors["functionCount"] == 79_866
    payload_bytes, sections = section_payload_bytes(TARGET)
    size = lambda label: selected["experimental::metadata::" + label]
    retained_parts = {
        "fixed_current_wrapper": selected["experimental::ValidatedSpans"],
        "signatures": observed["types"] * size("Signature"),
        "parameters_capacity": 8192 * selected["Type"],
        "imports": observed["imports"] * size("Import"),
        "functions": observed["functions"] * size("Function"),
        "globals": observed["globals"] * size("Global"),
        "exports": observed["exports"] * size("Export"),
        "data": observed["data_segments"] * size("Segment"),
        "elements": observed["element_segments"] * size("Segment"),
    }
    # Buffer::push doubles parameters 4096 -> 8192; other metadata arrays reserve exact counts.
    metadata_envelope_parts = {
        "current_fixed_wrapper": selected["experimental::ValidatedSpans"],
        "signatures": 512 * size("Signature"),
        "parameter_growth_overlap": (4096 + 8192) * selected["Type"],
        "total_function_metadata_upper": 80_000 * max(size("Import"), size("Function")),
        "globals": 8192 * size("Global"),
        "exports": 4096 * size("Export"),
        "segments": 2 * 4096 * size("Segment"),
    }
    fixed = (selected["experimental::account::Meter<'_>"]
             + 3 * selected["experimental::reader::Reader<'_>"]
             + selected["experimental::validate::BodyState"]
             + selected["experimental::account::Buffer<u32>"]
             + 2 * selected["experimental::Failure"] + 128)
    scratch_parts = {"current_fixed": fixed,
                     "locals_growth_overlap": (128 + 256) * selected["Type"],
                     "operands_growth_overlap": (64 + 128) * selected["std::option::Option<Type>"],
                     "controls_growth_overlap": (256 + 512) * selected["experimental::validate::Control"],
                     "export_sort_scratch": 4096 * 4}
    mib = 1024 * 1024
    arithmetic = {
        "scope": "Current representation arithmetic under proposed counts, not future measured peaks or complete validation.",
        "retained_current_metadata_parts": retained_parts,
        "retained_current_metadata_bytes": sum(retained_parts.values()),
        "current_representation_metadata_envelope_parts": metadata_envelope_parts,
        "current_representation_metadata_envelope_upper_bytes": sum(metadata_envelope_parts.values()),
        "current_representation_scratch_parts": scratch_parts,
        "current_representation_scratch_conservative_sum_bytes": sum(scratch_parts.values()),
        "source_copy_plus_top_payload_lower_work": TARGET.stat().st_size + payload_bytes,
        "top_sections": sections,
        "maximum_successful_positive_growth_old_new_bytes": (767 + 768) * 65536,
        "loose_twice_maximum_memory_bytes": 2 * 768 * 65536,
        "maximum_stage_partition_sum_after_external_input_drop_bytes":
            (64 + 16 + 16 + 128) * mib + 4 * 65536 + selected["experimental_wasi::WasiContext"],
        "maximum_validation_partition_sum_including_one_64mib_input_bytes": (64 + 64 + 16 + 1) * mib,
        "combined_limit_bytes": 256 * mib,
        "future_complete_validation_work_512m_fit": "unknown",
        "future_complete_validation_metadata_16mib_and_scratch_1mib_fit":
            "not measured; source arithmetic gives large headroom for current representation only",
        "future_runtime_envelope_fit": "unknown",
    }
    assert arithmetic["source_copy_plus_top_payload_lower_work"] == 107_554_182
    assert arithmetic["current_representation_metadata_envelope_upper_bytes"] < 16 * mib
    assert arithmetic["current_representation_scratch_conservative_sum_bytes"] < mib
    paths = [ROOT / "AGENTS.md", ROOT / "vm/Cargo.toml", ROOT / "vm/src/lib.rs",
             ROOT / "vm/src/execute.rs", ROOT / "docs/swift-reactor-owned-profile-design.md",
             ROOT / "docs/swift-wasi-adapter-design.md", ROOT / "docs/span-execution-design.md",
             DIAGNOSTICS / "receipt.json", DIAGNOSTICS / "statistics.json", descriptors_path,
             Path(__file__).resolve(), OUT / "review.md"]
    paths += sorted((ROOT / "vm/src/experimental").rglob("*.rs"))
    paths += sorted((ROOT / "vm/src/experimental_wasi").rglob("*.rs"))
    manifest = [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                 "sha256": sha(path)} for path in paths]
    result = {"schema": 1, "status": "proposal-audit-arithmetic-only", "authorization": False,
              "valid": False, "scope": "Source review and bounded compiler layout/framing probe only; no engine changes, Wasm body validation, cache decode, execution, device, publication or GA evidence.",
              "observedUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "command": [sys.executable, "-B", str(Path(__file__).resolve())],
              "pythonVersion": sys.version, "pythonExecutableSHA256": sha(Path(sys.executable).resolve()),
              "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "dirtyTree": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
              "rustcExecutable": {"path": str(RUSTC), "sha256": sha(RUSTC.resolve())},
              "compilerDiagnosticEnvironment": {"RUSTC_BOOTSTRAP": "1", "RUSTUP_AUTO_INSTALL": "0"},
              "commands": commands, "layouts": selected, "arithmetic": arithmetic,
              "artifact": {"path": str(TARGET.relative_to(ROOT)), "bytes": TARGET.stat().st_size, "sha256": sha(TARGET)},
              "sourceManifest": manifest,
              "sourceManifestDigest": hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
    (OUT / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "valid": False, "authorization": False,
                      "sourceManifestDigest": result["sourceManifestDigest"], "arithmetic": arithmetic}, indent=2))


if __name__ == "__main__":
    main()
