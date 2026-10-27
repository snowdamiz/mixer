"""Bounded independent custody/source/data consistency check; no Rust execution."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys

from build_oracles import make

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SELECTION = ROOT / "verification/swift-guarded-snapshot-actual-owner-rust-selection"
ROOT_SELECTION = ROOT / "verification/swift-semantic-adapter-root-review/guarded-snapshot-actual-owner-Rust-implementation-selection.json"
ROOT_AMENDMENT = ROOT / "verification/swift-semantic-adapter-root-review/guarded-snapshot-actual-owner-Rust-contract-amendment.json"
EXPECTED_SEAL = "1b0c3234a22f559280f5eb461bab5bf367a2ee0b7acda45c744b1da92b10d0f7"
EXPECTED_ROOT = "9551f5e447c600af27aa96146a757ea1452027c465baf76fd3c1d8c31b88ce61"
EXPECTED_AMENDMENT = "b07ea4fc8cbd1e30581d2de7b2512c8e5a3057c101a24cd6ea26239fa92d0e5f"
FROZEN_REVISION = "9398732c23648a82097d5a72b02b1c77af818e41"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def row(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(raw), "sha256": sha(raw)}


def read_frozen(path):
    assert path.is_relative_to(ROOT)
    assert "swift-guarded-snapshot-actual-owner-rust-implementation" not in path.parts
    return path.read_bytes()


def seal(base, expected=None):
    raw = read_frozen(base / "seal.json")
    if expected is not None:
        assert sha(raw) == expected, base
    selected = json.loads(raw)
    members = selected["members"]
    assert len(members) == selected["member_count"]
    assert sum(x["bytes"] for x in members) == selected["member_bytes"]
    assert sha(canonical(members)) == selected["tree_sha256"]
    names = {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file() and p != base / "seal.json"}
    assert names == {x["path"] for x in members}, base
    paths = [base / "seal.json"]
    for item in members:
        path = base / item["path"]
        data = read_frozen(path)
        assert (len(data), sha(data)) == (item["bytes"], item["sha256"]), path
        # Fully decode all selection JSON/stdout records, rather than reading
        # only the top-level present-day selection contract.
        if base == SELECTION and (path.suffix == ".json" or path.name == "stdout"):
            json.loads(data)
        paths.append(path)
    return selected, paths


def custody():
    selected, paths = seal(SELECTION, EXPECTED_SEAL)
    assert (selected["member_count"], selected["member_bytes"]) == (32, 1392587)
    paths = set(paths)
    assert sha(read_frozen(ROOT_SELECTION)) == EXPECTED_ROOT
    paths.add(ROOT_SELECTION)
    amendment = read_frozen(ROOT_AMENDMENT)
    assert len(amendment) == 4016 and sha(amendment) == EXPECTED_AMENDMENT
    assert json.loads(amendment)["immutable_selection"]["sha256"] == EXPECTED_ROOT
    paths.add(ROOT_AMENDMENT)
    before = json.loads(read_frozen(SELECTION / "commands/source-map-final/input-before.json"))
    after = json.loads(read_frozen(SELECTION / "commands/source-map-final/input-after.json"))
    assert before == after and len(before) == 584
    for item in before:
        path = ROOT / item["path"]
        raw = read_frozen(path)
        assert {"path": item["path"], "bytes": len(raw), "sha256": sha(raw)} == item
        paths.add(path)
    # Membership closure for every seal in original declared custody. No old
    # verifier/model/test/runner is imported or executed.
    inherited_seals = 0
    for item in before:
        if item["path"].endswith("/seal.json"):
            _, frozen_members = seal((ROOT / item["path"]).parent, item["sha256"])
            assert set(frozen_members) <= paths
            inherited_seals += 1
    producer = json.loads(read_frozen(ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-affine-refusal/final-custody.json"))
    assert producer["before"] == producer["after"] and producer["unchanged"]
    assert len(producer["before"]) == 479
    provider = ROOT / "verification/swift-guarded-snapshot-owned-binding-provider"
    source_manifest = json.loads(read_frozen(provider / "proposed-source-manifest.json"))
    source_custody = json.loads(read_frozen(provider / "proposed-source-custody.json"))
    assert len(source_custody) == source_manifest["member_count"] == 146
    assert sha(canonical(source_manifest["members"])) == source_manifest["tree_sha256"] == "acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d"
    for expected, origin in zip(source_manifest["members"], source_custody):
        assert expected == {k: origin[k] for k in ("path", "bytes", "sha256")}
        path = ROOT / origin["origin"]
        assert path in paths
        raw = read_frozen(path)
        assert (len(raw), sha(raw)) == (origin["bytes"], origin["sha256"])
    host = json.loads(read_frozen(ROOT / "verification/swift-guarded-snapshot-host-composition/host-support-manifest.json"))
    assert host["member_count"] == len(host["members"]) == 11
    assert sha(canonical(host["members"])) == host["tree_sha256"] == "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2"
    for item in host["members"]:
        path = ROOT / "verification/swift-real-profile-loader-binding/host" / item["path"]
        assert path in paths
        raw = read_frozen(path)
        assert (len(raw), sha(raw)) == (item["bytes"], item["sha256"])
    return sorted((row(p) for p in paths), key=lambda x: x["path"]), inherited_seals


def check_anchors():
    mapped = json.loads(read_frozen(SELECTION / "source-map.json"))
    anchors = []
    for item in mapped["anchors"]:
        raw = read_frozen(ROOT / item["source"]["path"])
        text = raw.decode()
        assert (len(raw), sha(raw)) == (item["source"]["bytes"], item["source"]["sha256"])
        excerpt = item["exact_excerpt"]
        assert sha(excerpt.encode()) == item["excerpt_sha256"]
        assert text.count(excerpt) == 1
        start = text.index(excerpt)
        assert text[:start].count("\n") + 1 == item["start_line"]
        assert text[:start + len(excerpt)].count("\n") + 1 == item["end_line"]
        anchors.append({k: v for k, v in item.items() if k != "exact_excerpt"})
    assert len(anchors) == 20
    by = {x["label"]: x["exact_excerpt"] for x in mapped["anchors"]}
    loader = by["loader_full_checks"]
    assert loader.index("drop(executable);") < loader.index("let input = retained(") < loader.index("let validation = validate_swift_reactor")
    assert loader.index("source_bytes_equal") < loader.index("final_metadata_recheck_v1") < loader.index("Ok(SelectedValidatedProfileV1")
    assert "source: Box<[u8]>" in by["proof_owned_backing"]
    assert "let source = source.into_boxed_slice();" in by["validator_copy"]
    assert "source: File" in by["selected_and_Files"] and "executable: Option<File>" in by["selected_and_Files"]
    assert "mtime: i64" in by["full_identity"] and "ctime_ns: i64" in by["full_identity"]
    return anchors


def check_complete_typed_fields(contract):
    preserved = contract["preserved"]
    pairs = [
        ("verification/swift-guarded-snapshot-scoped-binding-source/source/vm/src/experimental_swift_reactor/control.rs", "pub struct SwiftRunBudget {", preserved["product_fields"]),
        ("verification/swift-guarded-snapshot-scoped-binding-source/source/vm/src/experimental/swift.rs", "pub struct SwiftValidationBudget {", preserved["validation_fields"])
    ]
    result = []
    for name, marker, expected in pairs:
        raw = read_frozen(ROOT / name)
        text = raw.decode()
        at = text.index(marker)
        stop = text.index("\n}", at) + 2
        excerpt = text[at:stop]
        fields = [line.strip().split(":", 1)[0].removeprefix("pub ")
                  for line in excerpt.splitlines()[1:-1]]
        assert fields == expected
        result.append({"source": row(ROOT / name), "start_line": text[:at].count("\n") + 1,
                       "end_line": text[:stop].count("\n") + 1,
                       "excerpt_sha256": sha(excerpt.encode()), "fields": fields})
    assert len(preserved["product_fields"]) == 17
    assert len(preserved["validation_fields"]) == 5
    assert len(preserved["claim_fields"]) == len(preserved["identity_fields"]) == 8
    profile = read_frozen(ROOT / "verification/swift-guarded-snapshot-owned-binding-provider/proposed-overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs").decode()
    claim_at = profile.index("struct UnverifiedProfileDigestBytesV1 {")
    claim_end = profile.index("\n}", claim_at)
    claim_excerpt = profile[claim_at:claim_end]
    for name in preserved["claim_fields"]:
        assert f"{name}:[u8;32]" in claim_excerpt
    return result


def check_oracles(data):
    u64 = lambda raw, at: struct.unpack_from("<Q", raw, at)[0]
    for name, vector in data["binary"].items():
        raw = bytes.fromhex(vector["bytes_hex"])
        assert sha(raw) == vector["sha256"]
        assert raw[:8] == name.encode() and u64(raw, 8) == 1
        if name == "MIXPTH01":
            assert u64(raw, 16) == len(raw)
            sections = [bytes.fromhex(x) for x in vector["paths_hex"]]
            assert raw[64:] == b"".join(sections)
            assert [u64(raw, 24 + i * 8) for i in range(5)] == list(map(len, sections))
            assert all(section and b"\0" not in section for section in sections)
            assert sections[3].endswith(b"\xff") and sections[4].endswith(b"\xfe")
            long = bytes.fromhex(vector["long_path_positive_hex"])
            assert u64(long, 24) == 4097 and u64(long, 16) == len(long)
            assert vector["long_path_test_caps"][0] == 4097
        else:
            assert u64(raw, 16) == 512 and u64(raw, 24) == len(raw)
            sections = [bytes.fromhex(x) for x in vector["section_hex"]]
            assert raw[512:] == b"".join(sections)
            length_at = 48 if name == "MIXLBD01" else 40
            assert [u64(raw, length_at + i * 8) for i in range(4)] == list(map(len, sections))
            if name == "MIXLBD01":
                assert (u64(raw, 32), u64(raw, 40)) == (146, 11)
                assert raw[88:108] == b"aarch64-apple-darwin" and not any(raw[108:152])
                assert not any(raw[344:512])
                digest_at = 152
            else:
                assert len(sections[0]) == 64
                assert [u64(raw, 72 + i * 8) for i in range(5)] == [1947, 1000000, 65536, 1000000, 10000]
                assert not any(raw[368:512])
                digest_at = 240
            for i, section in enumerate(sections):
                assert raw[digest_at + i * 32:digest_at + (i + 1) * 32] == hashlib.sha256(section).digest()
        for mutation in vector["mutations"]:
            changed = bytearray(raw)
            value = bytes.fromhex(mutation["replace_hex"])
            at = mutation["offset"]
            changed[at:at + len(value)] = value
            assert changed != raw and sha(changed) == mutation["result_sha256"]
    identity = data["signed_identity64"]
    raw_identity = bytes.fromhex(identity["bytes_hex"])
    assert len(raw_identity) == 64
    assert list(struct.unpack("<QQQQqqqq", raw_identity)) == identity["values"]
    assert identity["values"][4:] == [-(1 << 63), -1, 0, (1 << 63) - 1]
    baseline = data["correlation_baseline"]
    assert len(baseline) == 9
    changes = data["correlation_mutations"]
    assert len(changes) == 230 and len({x["id"] for x in changes}) == 230
    fields = set()
    for change in changes:
        varied = copy.deepcopy(baseline)
        cursor = varied
        for element in change["path"][:-1]:
            cursor = cursor[element]
        key = change["path"][-1]
        assert cursor[key] != change["replacement"]
        cursor[key] = change["replacement"]
        assert varied != baseline
        fields.add(tuple(change["path"]))
    assert sum(path[0] == "identities" for path in fields) == 32
    assert sum(path[0] == "validation_budget" for path in fields) == 5
    assert sum(len(path) == 1 for path in fields) == 7
    for schedule in data["read_schedules"][:4]:
        assert schedule["expected_calls"] == 32 * ((schedule["extent"] + 4095) // 4096 + 1)
        assert len(schedule["responses"]) == schedule["expected_calls"]
        assert sum(x for x in schedule["responses"] if type(x) is int) == schedule["extent"]
    assert not data["production_authority"]
    return {"binary_baselines": 3, "binary_mutations": sum(len(x["mutations"]) for x in data["binary"].values()),
            "correlation_mutations": len(changes), "distinct_identity_fields": 32,
            "distinct_limit_fields": 5, "digest_byte_mutations": 192,
            "read_schedules": len(data["read_schedules"]), "signed_identity_bytes": 64}


def main():
    assert len(sys.argv) == 2
    out = Path(sys.argv[1]).resolve()
    assert out.is_relative_to(HERE / "commands") and out.is_dir()
    before, seals = custody()
    anchors = check_anchors()
    contract = json.loads((HERE / "contract.json").read_bytes())
    typed_fields = check_complete_typed_fields(contract)
    cases = json.loads((HERE / "cases.json").read_bytes())
    probes = json.loads((HERE / "compiler-cases.json").read_bytes())
    assert [x["id"] for x in cases["cases"]] == [f"H{i:02}" for i in range(1, 14)]
    assert [x["id"] for x in probes["cases"]] == [f"C{i:02}" for i in range(1, 9)]
    assert [x["id"] for x in contract["amendments"]] == [f"PA{i:02}" for i in range(1, 7)]
    labels = {x["label"] for x in anchors}
    assert all(set(case["anchors"]) <= labels for case in cases["cases"])
    assert probes["budget"]["preaccess_invocations"] == 0
    assert contract["producer_source_accessed"] is False
    assert contract["preserved"]["product_policy_fields"] == 17
    assert contract["preserved"]["unverified_claims"] == 8
    assert contract["preserved"]["Pending_upstream"] == 6
    oracles = make()
    counts = check_oracles(oracles)
    after, seals_after = custody()
    assert before == after and seals == seals_after
    changes = {}
    for name in ("selection.json", "host-test-plan.json", "README.md", "run_check.py"):
        old = (SELECTION / "commands/source-map-001" / name).read_bytes()
        new = (SELECTION / name).read_bytes()
        changes[name] = {"historical_sha256": sha(old), "selected_sha256": sha(new), "equal": old == new}
    result = {
        "schema": 1, "status": "independent preaccess source/custody/oracle consistency passed",
        "scope": "preaccess consistency only; no actual Rust semantic verification",
        "candidate_source_read": False, "actual_Rust_behavior_tested": False,
        "Rust_compiler_invocations": 0, "old_models_tests_runners_imported_or_executed": False,
        "frozen_input_members": len(before), "frozen_input_tree_sha256": sha(canonical(before)),
        "all_inputs_before_after_unchanged": True,
        "selection_seal_sha256": EXPECTED_SEAL, "root_amendment_sha256": EXPECTED_AMENDMENT,
        "selection_members": 32, "selection_member_bytes": 1392587,
        "inherited_complete_seals": seals, "original_declared_custody": 479,
        "source_members": 146, "host_members": 11, "verified_original_anchors": len(anchors),
        "host_cases_specified": 13, "compiler_categories_specified": 8,
        "complete_actual_product_fields": 17, "complete_actual_validation_fields": 5,
        "complete_actual_claim_fields": 8, "additional_type_definition_spans": 2,
        "preaccess_amendments": 6, "oracle_data_consistency": counts,
        "selection_history_fully_read": changes,
        "historical_revision_only": FROZEN_REVISION,
        "native_startup_allocator_source_policy_manifest_authority_root_funding": "Pending",
        "actual_implementation_compiler_File_runtime_FieldLog_OTA_GA": "Pending",
        "GA_gate_verified": False
    }
    for name, value in [("input-before.json", before), ("input-after.json", after),
                        ("result.json", result)]:
        (out / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    (HERE / "frozen-anchors.json").write_text(json.dumps(anchors, sort_keys=True, indent=2) + "\n")
    (HERE / "complete-field-contracts.json").write_text(json.dumps(typed_fields, sort_keys=True, indent=2) + "\n")
    (HERE / "oracles.json").write_text(json.dumps(oracles, sort_keys=True, indent=2) + "\n")
    data_dir = HERE / "data"
    data_dir.mkdir(exist_ok=True)
    for label, vector in oracles["binary"].items():
        (data_dir / (label + ".bin")).write_bytes(bytes.fromhex(vector["bytes_hex"]))
    (data_dir / "identity64.bin").write_bytes(bytes.fromhex(oracles["signed_identity64"]["bytes_hex"]))
    (data_dir / "MIXPTH01-long.bin").write_bytes(bytes.fromhex(oracles["binary"]["MIXPTH01"]["long_path_positive_hex"]))
    data_rows = [row(path) for path in sorted(data_dir.iterdir())]
    assert len(data_rows) == 5
    (HERE / "data-manifest.json").write_text(json.dumps(data_rows, sort_keys=True, indent=2) + "\n")
    (HERE / "report.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
