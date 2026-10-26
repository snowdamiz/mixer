"""Read-only audit of a retained accepted-runner output; never execute artifact code."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
RUNNER_SHA = "4c56beec330b8118f01be3a6e7460f9857e4b1e8b61f29b4a9bce16fb6c1130c"


def require(value, message):
    if not value:
        raise ValueError(message)


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field: " + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=strict_object)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(base, head, tree, release):
    base = base.absolute()
    runner = ROOT / "scripts/ci/check-analyzer-envelope.py"
    require(sha(runner) == RUNNER_SHA, "Accepted local validator differs")
    spec = importlib.util.spec_from_file_location("accepted_envelope_validator", runner)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Import only the hash-bound repository runner. No module from the artifact is loaded.
    inventory = module.inventory(base)
    require(len(inventory) <= 512, "Unexpected output member count")
    receipt = read_json(base / "receipt.json")
    require(receipt["status"] == "passed-host-fixture-check" and receipt["errors"] == []
            and receipt["active_checks_completed"] is True, "Runner did not finish successfully")
    for key in module.FLAGS:
        require(receipt[key] is False, "Unexpected authority flag: " + key)
    require(receipt["runner"]["sha256"] == sha(base / "executed-runner.py") == RUNNER_SHA,
            "Executed runner snapshot differs")
    require(receipt["revision_before"] == receipt["revision_after"] == head, "Wrong source revision")
    require(receipt["git_tree_before"] == receipt["git_tree_after"] == tree, "Wrong Git tree")
    require(receipt["source_tree_digest"] == module.PACK_TREE_SHA256, "Wrong fixture tree")
    manifest = module.verify_pack(base / "pack")
    require(receipt["pack_preflight"] == {
        "manifest_sha256": module.MANIFEST_SHA256, "tree_sha256": module.PACK_TREE_SHA256,
        "member_count": 86, "bytes": 8330464}, "Wrong pack preflight")
    require(all(v["passed"] is True for v in receipt["postflight"].values()), "Failed postflight")
    require(set(receipt["postflight"]) == {"compiler", "launcher", "pack", "python", "runner",
            "runner-snapshot", "snapshot", "snapshot-observed"}, "Incomplete postflight")
    expected_names = ["revision-before", "git-tree-before", "python-version", "compiler-sysroot-selection",
                      "rustc-verbose", "library-compile", "producer-compile", "producer-list", "producer-execute",
                      "independent-compile", "independent-list", "independent-execute", "api-positive",
                      *["api-negative-" + name for name in module.API_TARGETS], "revision-after", "git-tree-after"]
    require([row["name"] for row in receipt["commands"]] == expected_names, "Wrong command closure")
    streams = {}
    commands = {}
    for row in receipt["commands"]:
        name = row["name"]
        commands[name] = row
        require(read_json(base / "commands" / (name + ".json")) == row, "Command receipt differs")
        require(row["exit"] == (1 if name.startswith("api-negative-") else 0), "Unexpected exit: " + name)
        require(row["timed_out"] is False and row["child_returned"] is True and row["owned_group_gone"] is True
                and not row.get("descendants_outlived_direct_child"), "Abnormal child return: " + name)
        for stream in ("stdout", "stderr"):
            item = row[stream]
            require(item["path"] == "commands/" + name + "." + stream, "Wrong stream path")
            path = module.regular(base / item["path"])
            require(path.stat().st_size == item["bytes"] and sha(path) == item["sha256"], "Stream differs")
            streams[name, stream] = path.read_text()
    identity = module.rustc_identity(streams["rustc-verbose", "stdout"])
    require(identity == receipt["rustc"]["identity"], "Compiler receipt differs from raw identity")
    require(identity["host"] == "aarch64-apple-darwin" and identity["release"] == release, "Wrong actual compiler")
    require(receipt["compiler_target_selection"]["actual_release"] == release
            and receipt["compiler_target_selection"]["actual_host"] == identity["host"], "Wrong selected target")
    expected = read_json(base / "pack/inventories/expected-methods.json")
    for lane, key, count in [("producer", "producer", 78), ("independent", "independent_exact_source", 14)]:
        names = expected[key]["names"]
        require(len(names) == count, "Wrong expected test count")
        listed = module.verify_methods(streams[lane + "-list", "stdout"], names)
        executed = module.verify_methods(streams[lane + "-execute", "stdout"], names, executed=True)
        require(receipt["test_binaries"][lane]["listed"] == listed
                and receipt["test_binaries"][lane]["executed"] == executed, "Method receipt differs")
    layouts = module.verify_layouts(streams["producer-execute", "stdout"],
                                   read_json(base / "pack/inventories/expected-host-layouts.json"))
    require(receipt["host_layouts"] == layouts and len(layouts) == 32, "Layout receipt differs")
    output = streams["producer-execute", "stdout"]
    require(output.count("ENVELOPE_ORACLE_CASES=16170") == 1
            and output.count("CORRECTED_FINITE_BUDGET_CASES=5544") == 1
            and receipt["fresh_candidate_comparisons_against_reused_oracles"] == 21714, "Comparison counts differ")
    require(receipt["api"]["positive"] is True and set(receipt["api"]["negative"]) == set(module.API_TARGETS),
            "Incomplete API checks")
    for name in module.API_TARGETS:
        matches = module.verify_negative(name, streams["api-negative-" + name, "stderr"],
            base / "pack/api" / (name + ".rs"), base / ("api-negative-" + name), commands["api-negative-" + name])
        require(matches == receipt["api"]["negative"][name], "API receipt differs")
    retained = read_json(base / "retention.json")
    require(len(retained["test_files"]) == 92, "Wrong retained file count")
    for row in retained["test_files"].values():
        path = module.regular(base / module.member_path(row["path"]))
        require(path.stat().st_size == row["bytes"] and sha(path) == row["sha256"], "Retained bytes differ")
        require(row["encoding"] in ("identity", "gzip"), "Unknown retention encoding")
        opened = gzip.open if row["encoding"] == "gzip" else open
        count = 0
        digest = hashlib.sha256()
        with opened(path, "rb") as stream:
            for block in iter(lambda: stream.read(65536), b""):
                count += len(block)
                require(count <= row["original_bytes"], "Expanded retention exceeds declared size")
                digest.update(block)
        require(count == row["original_bytes"] and digest.hexdigest() == row["original_sha256"],
                "Original retained file differs")
    cleanup = receipt["cleanup"]
    require(cleanup["test_files"] == retained["test_files"]
            and cleanup["compiler_products"] == retained["compiler_products"], "Retention and cleanup differ")
    require(cleanup["removed"] is True and cleanup["children_and_owned_groups_returned"] is True
            and cleanup["unrelated_process_or_native_discovery"] is False, "Incomplete cleanup receipt")
    expected_paths = {"receipt.json", "retention.json", "output-ownership.json", "executed-runner.py", "pack/manifest.json"}
    expected_paths.update("pack/" + item["path"] for item in manifest["members"])
    expected_paths.update("commands/" + name + "." + stream for name in expected_names for stream in ("stdout", "stderr"))
    expected_paths.update("commands/" + name + ".json" for name in expected_names)
    expected_paths.update(item["path"] for item in retained["test_files"].values())
    require({row["path"] for row in inventory} == expected_paths, "Unexpected/missing artifact members")
    return {"status": "passed-retained-output-audit", "head": head, "tree": tree, "compiler": identity,
            "receipt_sha256": sha(base / "receipt.json"), "output_members": len(inventory),
            "commands": len(commands), "streams": len(streams), "methods": {"producer": 78, "independent": 14},
            "API_positive": 1, "API_negative": 8, "primary_targets": 23, "layouts": 32,
            "comparisons": 21714, "retained_files": 92, "artifact_code_executed": False,
            "remote_job_status_independently_required": True, "GA_qualified": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--head", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--release", required=True, choices=("1.98.1", "1.99.0"))
    args = parser.parse_args()
    print(json.dumps(audit(args.artifact, args.head, args.tree, args.release), indent=2))
