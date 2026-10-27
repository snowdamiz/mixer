"""Seal this bounded proposal packet only; no Git/compiler/native commands."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
SEAL = HERE / "seal.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def main():
    rows = []
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path == SEAL:
            continue
        assert "__pycache__" not in path.parts
        data = path.read_bytes()
        rows.append(dict(path=path.relative_to(HERE).as_posix(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    receipt = json.loads((HERE / "attempts/offline-input-model-attempt4/receipt.json").read_bytes())
    assert receipt["exit_code"] == 0 and receipt["tests_run"] == 18 and receipt["skipped"] == 0
    for item in json.loads((HERE / "attempts/offline-input-model-attempt4/source-manifest.json").read_bytes()):
        data = (HERE / item["path"]).read_bytes()
        assert (len(data), hashlib.sha256(data).hexdigest()) == (item["bytes"], item["sha256"])
    contract = json.loads((HERE / "source-contract.json").read_bytes())
    seal = dict(schema=1, status="frozen-source-and-offline-protocol-proposal-requires-root-independent-review",
                member_count=len(rows), member_bytes=sum(row["bytes"] for row in rows), members=rows,
                tree_sha256=hashlib.sha256(canonical(rows)).hexdigest(),
                conditional_source146_base=contract["base_source146_tree"],
                proposed_source146_tree=contract["proposed_source146_tree"],
                actual_selected_source_bytes=1947, host_only_test_methods=18,
                original_harness_failures_preserved=2, compiler_invocations=0,
                existing_admitted_owner_interface="unresolved", provider_or_upstream_funding="pending",
                all_three_selectors="Pending", operational_grant=False,
                actual_loader_or_fixture_or_executable_launched=False, native_or_FieldLog_or_OTA_or_GA=False)
    if SEAL.exists():
        assert json.loads(SEAL.read_bytes()) == seal
    else:
        SEAL.write_text(json.dumps(seal, sort_keys=True, indent=2) + "\n")
    print(json.dumps(dict(seal_sha256=hashlib.sha256(SEAL.read_bytes()).hexdigest(), member_count=len(rows),
                         member_bytes=seal["member_bytes"], proposed_source146_tree=seal["proposed_source146_tree"],
                         compiler_invocations=0, operational_grant=False)))


if __name__ == "__main__":
    main()
