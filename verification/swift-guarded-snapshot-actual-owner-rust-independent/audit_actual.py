"""Independent read-only custody/source and complete retained production MIR audit."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACK = ROOT / "verification/swift-guarded-snapshot-actual-owner-rust-implementation"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def row(path, base=ROOT):
    data = path.read_bytes()
    return {"path": str(path.relative_to(base)), "bytes": len(data), "sha256": sha(data)}


def verify_seal():
    seal_bytes = (PACK / "seal.json").read_bytes()
    assert sha(seal_bytes) == "3592011c00794c12dcb76cecc41d4d2913e01a3d6e97612f3ce90f10cb4e5e23"
    seal = json.loads(seal_bytes)
    actual = [row(p, PACK) for p in sorted(PACK.rglob("*")) if p.is_file() and p.name != "seal.json"]
    # Nested files named seal.json are packet members too.
    actual = [row(p, PACK) for p in sorted(PACK.rglob("*")) if p.is_file() and p != PACK / "seal.json"]
    assert actual == seal["members"]
    assert len(actual) == 1799
    assert sum(r["bytes"] for r in actual) == 209640941
    assert sha(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()) == "43de4376805a601db9be4b0dcc94ede6d8b2a362487cd32a304df545d28919d7"
    return actual


def visible_mir(line):
    quoted = False
    escape = False
    for index, char in enumerate(line):
        if escape:
            escape = False
        elif char == "\\" and quoted:
            escape = True
        elif char == '"':
            quoted = not quoted
        elif not quoted and line[index:index+2] == "//":
            line = line[:index]
            break
    line = line.rstrip()
    line = re.sub(r"(<impl at [^>]+?\.rs):\d+:\d+: \d+:\d+>", r"\1:SPAN>", line)
    return re.sub(r"(\{closure@[^}]+?\.rs):\d+:\d+: \d+:\d+}", r"\1:SPAN}", line)


def mir_inventory(path):
    result = []
    counts = collections.Counter()
    header = None
    kind = None
    digest = None
    raw_digest = hashlib.sha256()
    observations = {}
    required = ["load_inner(", "read_owned_body_once_v1", "verify_actual_bodies_core_v1", "derive_provenance_v1", "correlate_core_v1", "correlate_admitted_loader_v1", "retire_acquired_owner_core_v1", "run_prepaid_admitted_fixture_v1", "consume_admitted_owner_once_v1"]
    selected = []
    pending = []
    with gzip.open(path, "rt") as source:
        for line in source:
            raw_digest.update(line.encode())
            candidate = None
            if line.startswith("fn "):
                candidate = "fn"
            elif line.startswith("const "):
                candidate = "const"
            elif line.startswith("static "):
                candidate = "static"
            elif re.match(r"^alloc\d+(?: |\t|\()", line):
                candidate = "allocation"
            elif line and not line[0].isspace() and line.rstrip().endswith(" = {") and ": " in line:
                candidate = "standalone_constant"
            elif line.strip() and not line[0].isspace() and not line.startswith(("//", "}")):
                raise AssertionError(("unrecognized top-level MIR", line[:160]))
            if candidate:
                if header is not None:
                    result.append({"kind": kind, "header": header, "sha256": digest.hexdigest()})
                    if selected:
                        observations[header] = pending
                kind = candidate
                counts[kind] += 1
                header = visible_mir(line)
                digest = hashlib.sha256()
                selected = [name for name in required if name in header]
                pending = []
            visible = visible_mir(line)
            if visible.strip():
                assert header is not None or line.startswith("//")
                if digest is not None:
                    digest.update((visible + "\n").encode())
            if selected and any(word in visible for word in ("drop(", "correlate", "retain_complete", "retire_acquired", "release_v1", "validate_swift_reactor", "retained(", "FinalRecheck", "CarrierCore", "into_selected", "invoke_loaded_leaf")):
                pending.append(visible.strip())
    assert header is not None
    result.append({"kind": kind, "header": header, "sha256": digest.hexdigest()})
    if selected:
        observations[header] = pending
    for name in required:
        assert any(name in r["header"] and r["kind"] == "fn" for r in result), name
    return {"counts": dict(counts), "items": result, "raw_sha256": raw_digest.hexdigest(), "focused_operations": observations}


before = verify_seal()
release = ROOT / "verification/swift-semantic-adapter-root-review/guarded-snapshot-actual-owner-Rust-frozen-release.json"
assert row(release)["sha256"] == "c0d68616f4f1d32901dc93877b8421085196531ab4ae956034cd0def83e23a1c"
origins = json.loads((PACK / "reconstruction.json").read_bytes())
originals = origins["source146"]
assert len(originals) == 146
changed = []
sources = []
for original in originals:
    old = ROOT / original["origin"]
    new = PACK / "source/vm" / original["path"]
    assert row(old)["sha256"] == original["sha256"]
    actual = row(new, PACK / "source/vm")
    sources.append(actual)
    if actual["sha256"] != original["sha256"]:
        changed.append(original["path"])
assert changed == ["src/experimental_swift_reactor/cache/initial_profile_v1.rs", "src/experimental_swift_reactor/retained_profile_loader_v1.rs"]
source_tree = sha(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode())
assert source_tree == "338ef290399450c712b140736fb714031a333891dc1acf5439c758ae97602564"
host = json.loads((ROOT / "verification/swift-guarded-snapshot-host-composition/host-support-manifest.json").read_bytes())
host_rows = [row(PACK / "source/host" / r["path"], PACK / "source/host") for r in host["members"]]
assert len(host_rows) == 11 and host_rows == host["members"]
loader_path = next(r for r in originals if r["path"].endswith("/retained_profile_loader_v1.rs"))
old_loader = (ROOT / loader_path["origin"]).read_bytes()
loader = (PACK / "source/vm" / loader_path["path"]).read_bytes()
assert loader.startswith(old_loader)
account = next(r for r in originals if r["path"].endswith("/host_account_v1.rs"))
assert row(PACK / "source/vm" / account["path"])["sha256"] == account["sha256"]
for command in ("production-final", "build-debug-proof-error", "build-opt-proof-error", "run-debug-proof-error", "run-opt-proof-error"):
    command_source = json.loads((PACK / "commands" / command / "source-manifest.json").read_bytes())
    expected = [{**r, "path": "host/" + r["path"]} for r in host_rows] + [{**r, "path": "vm/" + r["path"]} for r in sources]
    assert sorted(command_source["members"], key=lambda r: r["path"]) == sorted(expected, key=lambda r: r["path"]), command
    receipt = json.loads((PACK / "commands" / command / "receipt.json").read_bytes())
    assert receipt["exit"] == 0 and receipt["child_reaped"] and receipt["exact_owned_group_absent"]
    assert receipt["input_unchanged"] and receipt["source_unchanged"]
first = mir_inventory(PACK / "commands/production/full.mir.gz")
final = mir_inventory(PACK / "commands/production-final/full.mir.gz")
assert len(first["items"]) == len(final["items"]) == 6207
assert first["items"] == final["items"]
assert final["counts"] == {"fn": 2141, "const": 2059, "static": 7, "standalone_constant": 1, "allocation": 1999}
probe_observations = []
for number in range(1, 9):
    name = f"N{number:02}"
    probe = json.loads((PACK / "probes" / name / "probe.json").read_bytes())
    receipt = json.loads((PACK / "commands" / name / "receipt.json").read_bytes())
    stderr = (PACK / "commands" / name / "stderr").read_text()
    codes = sorted(set(re.findall(r"error\[(E\d+)\]", stderr)))
    assert receipt["exit"] != 0 and receipt["child_reaped"] and receipt["exact_owned_group_absent"]
    probe_observations.append({"id": name, "probe_source": probe["source"], "diagnostic_codes": codes, "stderr_sha256": sha(stderr.encode()), "independently_replayed": False})
after = verify_seal()
assert before == after
report = {"schema": 1, "status": "custody-and-source-invariants-confirmed-implementation-acceptance-pending-behavior", "producer_members": len(before), "producer_bytes": sum(r["bytes"] for r in before), "source146_tree": source_tree, "changed": changed, "host11_exact": True, "host_account_exact": True, "original_loader_prefix": {"bytes": len(old_loader), "sha256": sha(old_loader)}, "final_command_sources_match_exact_source_and_host": True, "complete_MIR_item_count": len(final["items"]), "complete_MIR_counts": final["counts"], "initial_and_final_candidate_MIR_equal_after_display_only_normalization": True, "historical_baseline_MIR_available": False, "final_full_MIR_raw_sha256": final["raw_sha256"], "compiler_negative_probe_observations": probe_observations, "revision_attribution": json.loads(release.read_bytes())["revision_attribution"], "focused_MIR_operations": final["focused_operations"], "fresh_independent_Rust_execution": False, "native_or_GA_authority": False}
(HERE / "source-mir-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
(HERE / "mir-item-inventory.json").write_text(json.dumps({"input": row(PACK / "commands/production-final/full.mir.gz"), "items": final["items"]}, indent=2, sort_keys=True) + "\n")
print(json.dumps({k: v for k, v in report.items() if k not in ("focused_MIR_operations", "compiler_negative_probe_observations")}, sort_keys=True))
