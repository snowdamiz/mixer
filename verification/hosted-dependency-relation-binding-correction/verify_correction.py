#!/usr/bin/env python3
"""Bounded source/JSON/lock-byte audit; no Mix/compiler/database/runtime."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys
import time

START = time.monotonic()
OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
OLD = "59e6fe5d6bc76ae0057745fe7eb3fb292f225b6a37cd1c99c214f9447c60ff8a"
NEW = "1eada39dcaf4863d02d39f51e218d2bad8908b36a0cba47ff2d16037b7bcf837"
MODULE = "hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex"
EXPECTED = {16: "079b8cdeb3c039284b3ae402664230f6abc01782ab5e7f08219a06067e22cadf",
            17: "100df9346930b778611b46e821484db025671819b3bb966cfcb496014ce42785"}


def sha(path):
    assert time.monotonic() - START < 55
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def stable_json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def entry_lines(path):
    raw = path.read_bytes().splitlines(keepends=True)
    assert raw[0] == b"%{\n" and raw[-1] == b"}\n" and len(raw) == 23
    result = {}
    for line in raw[1:-1]:
        match = re.match(rb'  "([a-z0-9_]+)": \{:hex, :[a-z0-9_]+, "([0-9.]+)"', line)
        assert match and match[1].decode() not in result
        result[match[1].decode()] = {"version": match[2].decode(), "raw": line,
                                  "entry_sha256": hashlib.sha256(line).hexdigest()}
    assert len(result) == 21
    return result


def main():
    preflight = read(OUT / "preflight.json")
    receipt = read(OUT / "ci-evidence/receipt.json")
    assert receipt["status"] == "failed"
    assert sha(OUT / "ci-evidence/receipt.json") == preflight["ci_receipt_sha256"] == "4a9460ce6bf3f7c33d0d0e3b3c1d3596083eecbc2e909d365ab9cf2cca792245"
    assert sha(OUT / "ci-evidence/compile.log") == preflight["ci_compile_log_sha256"] == "cbd78e2de3a3cb37c8b338f0100845e5303d3c0db8958e9e55b568dfa34a5cc1"
    assert "unreviewed relation source" in (OUT / "ci-evidence/compile.log").read_text()
    assert [(c["label"], c["exit_code"]) for c in receipt["commands"]] == [("revision",0),("elixir-version",0),("postgres-version",0),("format",0),("compile",1)]
    assert (OUT / "ci-evidence/revision.log").read_text().strip() == preflight["source_revision"] == "d87ce0a1b05a9ad42cd2118bbf2ccc5491499663"
    provenance = REPO / "verification/hosted-dependency-advisory-correction-independent/runtime-review-1"
    assert sha(provenance / "review-seal.json") == "3efc908cedcff554909b2f3e64a783c2c0259be728ea224285b80507770890f6"
    for pin in read(provenance / "review-seal.json")["files"]:
        assert sha(provenance / pin["path"]) == pin["sha256"]
    actual_lock = REPO / "verification/hosted-dependency-advisory-correction/resolution-v4/attempts/fe41774456c8435e841b30f9b48cb7ec/actual-mix.lock"
    assert sha(actual_lock) == sha(OUT / "lock-provenance/new-mix.lock") == sha(REPO / "hosted/mix.lock") == NEW
    assert sha(OUT / "lock-provenance/old-mix.lock") == OLD
    before_lock = entry_lines(OUT / "lock-provenance/old-mix.lock")
    after_lock = entry_lines(OUT / "lock-provenance/new-mix.lock")
    assert before_lock.keys() == after_lock.keys()
    changed = sorted(name for name in before_lock if before_lock[name]["raw"] != after_lock[name]["raw"])
    assert changed == ["bandit", "jose"]
    assert after_lock["bandit"]["version"] == "1.14.0" and after_lock["jose"]["version"] == "1.11.13"
    relation_dependencies = ["db_connection", "decimal", "ecto", "ecto_sql", "oban", "postgrex"]
    unchanged = {name: after_lock[name]["entry_sha256"] for name in before_lock if name not in changed}
    assert len(unchanged) == 19
    for name in relation_dependencies:
        assert before_lock[name]["raw"] == after_lock[name]["raw"]
    snapshots, reports, after_bindings = {}, {}, []
    module_before = (OUT / "beforeimages" / MODULE).read_bytes()
    expected_module = module_before
    for major in [16,17]:
        name = f"hosted/priv/browser_auth/relation_surface_v1_pg{major}.json"
        before_path, after_path = OUT / "beforeimages" / name, REPO / name
        before_bytes, after_bytes = before_path.read_bytes(), after_path.read_bytes()
        assert sha(before_path) == receipt["inputs"][name] == preflight["beforeimages"][name]
        assert before_bytes.count(OLD.encode()) == 1
        assert after_bytes == before_bytes.replace(OLD.encode(), NEW.encode())
        assert sha(after_path) == EXPECTED[major]
        before, after = read(before_path), read(after_path)
        assert before["source_bindings"]["hosted/mix.lock"] == OLD and after["source_bindings"]["hosted/mix.lock"] == NEW
        expected_map = dict(before["source_bindings"], **{"hosted/mix.lock": NEW})
        assert after["source_bindings"] == expected_map and len(expected_map) == 29
        after_bindings.append(expected_map)
        for key in before.keys() - {"source_bindings"}:
            assert after[key] == before[key]
        observed = {relative: sha(REPO / relative) for relative in expected_map}
        assert observed == expected_map
        assert preflight["bindings"][str(major)]["unchanged_other_bindings"] == {key:value for key,value in observed.items() if key != "hosted/mix.lock"}
        reports[str(major)] = {"before_sha256": sha(before_path), "after_sha256": sha(after_path),
            "before_binding_mismatch": preflight["bindings"][str(major)]["preexisting_mismatches"],
            "after_binding_mismatches": {}, "unchanged_source_bindings": 28,
            "unchanged_nonbinding_sections": {key:stable_json_hash(after[key]) for key in sorted(after.keys() - {"source_bindings"})},
            "unchanged_check_keys":len(after["check_keys"]),"unchanged_check_expressions":len(after["expressions"]["checks"]),
            "unchanged_relations":len(after["structure"]["relations"]),"unchanged_trigger_sources":len(after["trigger_sources"]),
            "unchanged_reviewed_input_refs":len(after["reviewed_inputs"])}
        expected_module = expected_module.replace(sha(before_path).encode(), EXPECTED[major].encode())
        snapshots[name] = {"before":sha(before_path),"after":sha(after_path)}
        target = OUT / "afterimages" / name
        assert target.read_bytes() == after_bytes
    assert after_bindings[0] == after_bindings[1]
    assert sha(OUT / "beforeimages" / MODULE) == receipt["inputs"][MODULE] == preflight["beforeimages"][MODULE]
    assert (REPO / MODULE).read_bytes() == expected_module
    assert (OUT / "afterimages" / MODULE).read_bytes() == expected_module
    snapshots[MODULE] = {"before":sha(OUT / "beforeimages" / MODULE),"after":sha(REPO / MODULE)}
    patch = "".join("".join(difflib.unified_diff((OUT / "beforeimages" / name).read_text().splitlines(keepends=True), (REPO / name).read_text().splitlines(keepends=True), fromfile="a/"+name, tofile="b/"+name)) for name in sorted(snapshots))
    assert len([line for line in patch.splitlines() if line.startswith("-") and not line.startswith("---")]) == 4
    assert len([line for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")]) == 4
    assert (OUT / "selected-correction.diff").read_text() == patch
    tree_members = {name:sha(REPO / name) for name in sorted(after_bindings[0].keys() | {MODULE, "hosted/priv/browser_auth/relation_surface_v1_pg16.json", "hosted/priv/browser_auth/relation_surface_v1_pg17.json"})}
    tree_sha = hashlib.sha256("".join(f"{pin}  {name}\n" for name,pin in tree_members.items()).encode()).hexdigest()
    result = {"schema":1,"status":"source-correction-verified-pending-root-review-and-remote-CI",
        "created_at":datetime.now(timezone.utc).isoformat(),"python":sys.version,
        "command":"python3 -B verification/hosted-dependency-relation-binding-correction/verify_correction.py",
        "script_sha256":sha(Path(__file__)),"source_revision":preflight["source_revision"],
        "failed_CI_tree_sha256":receipt["source_tree_sha256"],"reviewed_source_tree_sha256":tree_sha,"reviewed_source_tree_members":tree_members,
        "CI_status":"compile failed before tests; original retained evidence preserved",
        "CI_compile_log_sha256":preflight["ci_compile_log_sha256"],"CI_receipt_sha256":preflight["ci_receipt_sha256"],
        "canonical_delta":snapshots,"manifest_reports":reports,
        "old_whole_lock_sha256":OLD,"reviewed_generated_whole_lock_sha256":NEW,
        "changed_lock_packages":{"bandit":{"before":"1.13.1","after":"1.14.0"},"jose":{"before":"1.11.12","after":"1.11.13"}},
        "nineteen_other_complete_lock_entry_hashes_unchanged":unchanged,
        "relation_driving_dependencies_byte_identical":{name:{"version":after_lock[name]["version"],"entry_sha256":after_lock[name]["entry_sha256"]} for name in relation_dependencies},
        "module_logic_byte_identical_except_two_expected_hash_constants":True,
        "fail_closed_manifest_hash_and_cross_major_and_all_source_checks_preserved":True,
        "canonical_files_changed":3,"digest_line_replacements":4,"unapproved_product_or_workflow_edits":0,
        "new_Mix_compile_DB_catalog_callback_or_runtime_invocations":0,
        "remote_CI_validation_pending":True,"relation_catalog_callback_or_GA_acceptance":False,
        "scope":"Trusted whole-lock binding refresh after reviewed Bandit/JOSE patch pins only; no SQL/catalog shape or relation-driving dependency change, no new relation qualification.",
        "elapsed_seconds":round(time.monotonic()-START,6)}
    (OUT / "audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({key:value for key,value in result.items() if key not in {"reviewed_source_tree_members","nineteen_other_complete_lock_entry_hashes_unchanged"}},indent=2))


if __name__ == "__main__":
    main()
