#!/usr/bin/env python3
"""Read-only source/class/log/row reconciliation of the released partial replay."""
from collections import Counter
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import sys

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
P = ROOT / "verification/android-editor-membership-compiled-boundary-qualification/state-replay-candidate-v2"
EXPECTED = "997ffefd7eaad9ba8e0f6ddb0aa8654a5cee37304be8f49927874229e3f73a30"


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(path.read_bytes())


def category(path):
    name = path.name
    if name.startswith("boundary-"): return "historical_callbacks"
    if name == "direct-close.rows.jsonl.gz": return "close"
    if name == "direct-finite-38.rows.jsonl.gz": return "finite_exact38"
    if name.startswith("direct-"): return "direct_callbacks_and_refusal_states"
    if name.startswith("query-"): return "queries"
    if name.startswith("field-finite"): return "field_finite"
    if name.startswith("unsupported-callbacks"): return "external_unsupported_callbacks"
    raise AssertionError(str(path))


def main():
    assert identity(P / "seal.json")["sha256"] == EXPECTED
    seal = read(P / "seal.json")
    for name, expected in seal["members"].items():
        path = Path(name)
        assert not path.is_absolute() and ".." not in path.parts and not (P / path).is_symlink()
        assert identity(P / path) == expected
    assert {p.relative_to(P).as_posix() for p in P.rglob("*") if p.is_file()} == set(seal["members"]) | {"seal.json"}
    context = read(P / "product-context.json")
    assert len(context["source_map"]) == 16 and len(context["class_map"]) == 209
    assert hashlib.sha256(json.dumps({"source_map": context["source_map"], "class_map": context["class_map"]}, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == context["context_id"]
    counts, statuses = Counter(), Counter()
    rowfiles, runrecords, historical_states = [], [], {}
    source_prefix = "verification/android-editor-membership-compiled-boundary-qualification/"
    for run_name, command_count in (("run-12", 214), ("run-14", 4), ("run-16", 4)):
        run = P / run_name
        commands, classes, source = read(run / "commands.json"), read(run / "class-map.json"), read(run / "source-freeze.json")
        assert len(commands) == command_count
        for command in commands:
            assert command["exit"] == 0 and not command["timeout"] and command["reaped"]
            for stream in ("stdout", "stderr"):
                assert identity(run / (command["label"] + "." + stream)) == command[stream]
        for name, expected in classes.items():
            assert identity(run / "classes" / name) == expected
        assert all(classes[name] == expected for name, expected in context["class_map"].items())
        assert source["product_context_id"] == context["context_id"]
        for entry in source["sources"]:
            assert entry["path"].startswith(source_prefix)
            relative = entry["path"][len(source_prefix):]
            assert identity(run / "source-closure" / relative) == {"bytes": entry["bytes"], "sha256": entry["sha256"]}
        for name, expected in context["source_map"].items():
            assert identity(run / "source-closure/passive-return-probe-v3/inputs/source" / name) == expected
        assert identity(run / "source-closure/state-qualification/final-selected-support/NativeOwnerV2ConcreteHostTests.java")["sha256"] == "9dda45ef21a83183f2f61bc4a8ba864d868acd9be3683a3c147acdfa7668bc3e"
        receipt = read(run / "receipt.json")
        assert receipt["cleanup"]["scratch_removed"] and receipt["cleanup"]["all_children_reaped"]
        files = sorted(run.glob("*.rows.jsonl.gz"))
        for path in files:
            group = category(path)
            count, uncompressed = 0, 0
            with gzip.open(path, "rb") as stream:
                while True:
                    line = stream.readline(64 * 1024 * 1024 + 1)
                    if not line: break
                    assert len(line) <= 64 * 1024 * 1024 and line.endswith(b"\n")
                    count += 1
                    uncompressed += len(line)
                    assert count <= 1000 and uncompressed <= 512 * 1024 * 1024
                    row = json.loads(line)
                    assert row.get("validation_failure") is None
                    statuses[row["status"]] += 1
                    if group == "historical_callbacks":
                        historical_states.setdefault(row["historical_id"], []).append(row["state"])
                    if group == "field_finite":
                        assert row["actual_outcome"] == row["expected_outcome"]
                        assert row["actual_fields"] == row["expected_fields"]
                        assert row["native_events"] == row["native_outcomes"] == 0 and row["attempt_clean_latched"]
                    if group == "external_unsupported_callbacks":
                        assert row["actual_callbacks"] == row["expected_callbacks"]
                        assert row["actual_enclosing_outcome"] == row["expected_enclosing_outcome"]
                        assert row["native_unsupported_forward_count"] == 0 and row["attempt_clean_latched"]
            counts[group] += count
            rowfiles.append({"path": str(path.relative_to(P)), "rows": count, "uncompressed_bytes": uncompressed})
        runrecords.append({"run": run_name, "commands": len(commands), "source_files": len(source["sources"]),
                           "all_emitted_classes": len(classes), "exact_product_classes": 209, "row_files": len(files), "cleanup": receipt["cleanup"]})
        print(json.dumps({"run": run_name, "commands_verified": len(commands), "row_files_parsed": len(files)}), flush=True)
    declared = read(P / "evidence-summary.json")["declared_producer_row_counts"]
    assert dict(counts) == {k: v for k, v in declared.items() if k != "five_separate_v1"}
    states = read(P / "evidence-summary.json")["canonical_seven_states"]
    assert len(historical_states) == 180
    assert all(len(values) == 7 and set(values) == set(states) for values in historical_states.values())
    result = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, "-B", str(Path(__file__))], "script": identity(Path(__file__)),
        "packet_seal_sha256": EXPECTED, "members_reverified": 2597, "source_context": context["context_id"],
        "runs": runrecords, "independently_parsed_row_counts": dict(counts), "rows_total": sum(counts.values()),
        "statuses": dict(statuses), "historical_subjects_with_exact_seven_states": 180, "row_files": rowfiles,
        "five_V1_positives": "Separate already-selected five-site witnesses remain required; their fresh commands are counted, their outcomes are not part of this compressed-row audit.",
        "scope": "Independent data/source/class/log reconciliation only. Expected-field equality does not independently prove source semantics. Legacy outcome-review-required rows remain pending helper outcome proof; two TextAttribute native-return gaps, complete280 applicability and trusted execution closure remain open.",
        "fresh_runtime_replay_full_matrix_canonical_native_OTA_GA_accepted": False}
    target = D / "compiled-state-replay-v2-data-audit.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "data-audit-passed", "rows": sum(counts.values()), "statuses": dict(statuses), "receipt": identity(target)}))


if __name__ == "__main__":
    main()
