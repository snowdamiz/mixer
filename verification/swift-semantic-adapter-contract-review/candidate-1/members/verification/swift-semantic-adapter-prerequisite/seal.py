"""Seal only this source-only proposal; never touch another lane's files."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def dump(path, data):
    with path.open("x") as output:
        json.dump(data, output, indent=2, sort_keys=True)
        output.write("\n")

def main():
    if (BASE / "seal.json").exists() or (BASE / "final-receipt.json").exists():
        raise SystemExit("Refuse to overwrite sealed/final evidence")
    attempts = sorted((BASE/"commands").glob("run-*/receipt.json"),
                      key=lambda p:int(p.parent.name.split("-")[1]))
    receipt_path = attempts[-1]
    receipt = json.loads(receipt_path.read_text())
    if not receipt["passed"] or not receipt["source_rows_before_equal_after"]:
        raise SystemExit("Latest own source checks did not pass")
    before = json.loads((receipt_path.parent/"source-before.json").read_text())
    for row in before:
        raw = (ROOT/row["path"]).read_bytes()
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise SystemExit("Authored source drift: "+row["path"])
    for row in receipt["commands"]:
        matches = [p for p in receipt_path.parent.glob("*.json")
                   if p.name not in {"receipt.json","source-before.json","source-after.json"}
                   and json.loads(p.read_text()) == row]
        if len(matches) != 1:
            raise SystemExit("Command identity is missing or ambiguous")
        stem = matches[0].stem
        for suffix in ("stdout","stderr"):
            raw = (receipt_path.parent/(stem+"."+suffix)).read_bytes()
            if sha(raw) != row[suffix+"_sha256"] or len(raw) != row[suffix+"_bytes"]:
                raise SystemExit("Command stream drift")
    final = {
        "schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status":"sealed source-only next-step proposal; unselected; independent review pending",
        "owned_document":"docs/swift-semantic-adapter-prerequisite.md",
        "owned_directory":str(BASE.relative_to(ROOT)),
        "model_task_contract":{"model":"gpt-6.1-sol","reasoning_effort":"xhigh","context":"fresh bounded delegation"},
        "command":sys.argv,"qualification_receipt":str(receipt_path.relative_to(ROOT)),
        "qualification_receipt_sha256":sha(receipt_path.read_bytes()),
        "source_checks_per_mode":12,"normal_and_optimized_passed":True,
        "future_test_design_cases":52,"future_semantic_tests_executed":0,
        "accepted_pack_members_byte_verified":86,
        "consulted_source_members":30,"consulted_source_tree_sha256":receipt["consulted_source_tree_sha256"],
        "context_revision":"0b8e3fd8bdd86902f7d9d28e0cba01bcdbb5ce1c",
        "all_new_debits_layouts_and_complete_lifetimes_provisional":True,
        "source_or_contract_implementation_selection":False,
        "fullReplayAccepted":False,"storedPrefixValidated":False,"semantic_metrics_valid":False,
        "CI_40273904826_pass_claim":False,
        "pending":["independent contract and actual-source accounting","root selection","new Rust source, compiler layouts, Result/caller lifetime proof and independent tests","real profile/source/selection/original result/ledger/failure applicability/crypto/custody/CLI/target","native/device, signing/store/customer/operations, published FieldLog and GA"],
        "authoring_failures_preserved":["authoring-failure-1.json","authoring-failure-2.json"],
        "cleanup":receipt["cleanup"],"commit_or_push_by_lane":False,
    }
    dump(BASE/"final-receipt.json",final)
    paths = [ROOT/"docs/swift-semantic-adapter-prerequisite.md"]
    paths += [p for p in BASE.rglob("*") if p.is_file() and p.name not in {"seal.json","seal.sha256"}]
    rows = []
    for path in sorted(paths):
        raw = path.read_bytes()
        rows.append({"path":str(path.relative_to(ROOT)),"bytes":len(raw),"sha256":sha(raw)})
    seal = {"schema":1,"scope":"only owned proposal document/directory", "members":rows,
            "member_count":len(rows),"member_bytes":sum(r["bytes"] for r in rows),
            "excluded":[str((BASE/"seal.json").relative_to(ROOT)),str((BASE/"seal.sha256").relative_to(ROOT))]}
    dump(BASE/"seal.json",seal)
    value = sha((BASE/"seal.json").read_bytes())
    (BASE/"seal.sha256").write_text(value+"  "+str((BASE/"seal.json").relative_to(ROOT))+"\n")
    print(json.dumps({"seal_sha256":value,"members":len(rows),"bytes":seal["member_bytes"],
                      "document_sha256":sha((ROOT/"docs/swift-semantic-adapter-prerequisite.md").read_bytes()),
                      "contract_sha256":sha((BASE/"contract.json").read_bytes()),
                      "source_seams_sha256":sha((BASE/"source-seams.json").read_bytes()),
                      "test_design_sha256":sha((BASE/"test-design.json").read_bytes()),
                      "final_receipt_sha256":sha((BASE/"final-receipt.json").read_bytes())}))

if __name__ == "__main__":
    main()
