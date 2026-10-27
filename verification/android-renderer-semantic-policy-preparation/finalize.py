"""Give each actual callback tuple its own typed obligation, then freeze."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
assert __debug__ and not (ROOT / "seal.json").exists()


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")


raw = (ROOT / "proposal.json").read_bytes()
assert digest(raw)["sha256"] == "f75dd6fcdf8f8b459bcce65f4926ff01bed0e3d16ddd1dab33e9d0a4966eeb0f"
(ROOT / "draft-v2.json").write_bytes(raw)
proposal = json.loads(raw)
for subject in proposal["subjects"]:
    expanded = []
    for case in subject["required_cases"]:
        if case["kind"] != "callback-state":
            expanded.append(case)
            continue
        for site in subject["native_sites"]:
            if site["id"] not in case["applicable_native_site_ids"]:
                continue
            single = copy.deepcopy(case)
            single["id"] = "renderer-native-bci-" + str(site["bci"])
            single["applicable_native_site_ids"] = [site["id"]]
            single["oracle"]["typed_result"] = site["typed_result_oracle"]
            single["oracle"]["independent_expected_fixture"] = site["oracle_independence"]
            single["expected_outcome_scope"] = "actual-enclosing-typed-outcome" if site["callee"]["descriptor"].endswith(")V") else "native-return"
            single["pending_reason"] += " A void leaf needs exact output-argument state and normal/throwing enclosing typed completion; no nonvoid return is invented."
            expanded.append(single)
    subject["required_cases"] = expanded
    for disposition in subject["original_case_dispositions"]:
        disposition["required_by"] = [case["id"] for case in expanded]
    assert all(case["execution_join"] is None for case in expanded)
    assert len({case["id"] for case in expanded}) == len(expanded)
proposal["final_refinement"] = {
    "input_draft_sha256": digest(raw)["sha256"],
    "scope": "Each exact callback tuple now has its own independent typed oracle. Void getLocationInWindow uses output-argument plus actual enclosing outcome, not a fabricated nonvoid result.",
    "finalizer": digest(Path(__file__).read_bytes()), "python": sys.version,
}
save("proposal.json", proposal)
selected = {row["id"] for row in proposal["subjects"]}
roster = json.loads((ROOT / "inputs/complete-280-checklist.json").read_bytes())
assert len(selected) == 24 and selected <= {row["id"] for row in roster["subjects"]}
for subject in proposal["subjects"]:
    old = next(row for row in roster["subjects"] if row["id"] == subject["id"])
    assert old["categories"] == subject["original_categories"]
    assert old["required_semantic_cases"] == subject["original_required_case_ids"]
    assert [row["id"] for row in subject["original_case_dispositions"]] == old["required_semantic_cases"]
    assert digest((ROOT / "inputs/NativeRenderer.java").read_bytes())["sha256"] == subject["source_sha256"]
    assert digest((ROOT / "inputs/classes" / (subject["class"] + ".class")).read_bytes())["sha256"] == subject["class_sha256"]
summary = {
    "subjects": len(selected), "required_cases": sum(len(row["required_cases"]) for row in proposal["subjects"]),
    "direct_native_sites": sum(len(row["native_sites"]) for row in proposal["subjects"]),
    "callback_cases": sum(case["kind"] == "callback-state" for row in proposal["subjects"] for case in row["required_cases"]),
    "runtime_joins": 0, "policy_or_behavior_accepted": False,
    "proposal": digest((ROOT / "proposal.json").read_bytes()),
}
save("validation.json", summary)
members = []
for path in sorted(ROOT.rglob("*")):
    assert not path.is_symlink(), str(path)
    if path.is_file():
        members.append({"path": path.relative_to(ROOT).as_posix(), **digest(path.read_bytes())})
save("seal.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "scope": "Exact24 renderer semantic obligation proposal; source/case identity only, all fresh runtime joins pending",
                   "members": members, "member_count": len(members), "member_bytes": sum(row["bytes"] for row in members),
                   "summary": summary, "full_matrix_canonical_native_OTA_GA_accepted": False})
print(json.dumps(summary | {"seal_sha256": digest((ROOT / "seal.json").read_bytes())["sha256"], "members": len(members)}))
