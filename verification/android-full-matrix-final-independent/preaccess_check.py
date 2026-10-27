#!/usr/bin/env python3
"""Read only explicitly released preaccess contracts; never import producer code."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CONTEXT = "1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd"
PINNED = {
    "verification/android-editor-boundary-root-review/delegated-receiver-v2-selection.json": "48c4c286b048934092baf4defeeaa787a6ba6273aed1999bc6221a67dfbcc7a4",
    "verification/android-editor-boundary-root-review/editor-typed-join-correction-selection.json": "c1f8609d05e3c66dc5cd16b53711ef39160311aeab6a111314ddf8ef90b55111",
    "verification/android-editor-boundary-root-review/field-observation-host-acceptance.json": "a13a548a9ebd2cb8398719013e4aff7dc51ac0deab7de9dc5679c3c0a0f2768b",
    "verification/android-editor-membership-compiled-boundary-qualification/delegated-overload-association-v2/seal.json": "4fec770228b4420a56bd1ab0c48446a09bfac8037b80c498c412f627abfb81cf",
    "verification/android-editor-subject-typed-join-validator-correction/seal.json": "18fd1576d22572e6cb8e9a68c5d0d83a3042f4b465d2b258fb53a9c930de71c9",
    "verification/android-field-preservation-observation-controls/seal.json": "02f4a046dd7f10266e17b804c6b86bd857f19807306bcf17214f9d5914e81250",
    "verification/android-field-preservation-observation-independent/review-seal.json": "c17e30c16cb83cd6d7b19fb3a180f20243b44e3c2161a544491cab416cf71728",
    "verification/android-field-preservation-observation-controls/inputs/original-280-obligations.json": "8f6ec3cf034c3b07361bcb1f17a7a1ba38344d951803c625d03be67cbc14f112",
}

def check(value, message):
    if not value:
        raise ValueError(message)

def read_exact(relative, expected):
    path = REPO / relative
    check(not path.is_symlink(), "symlink: " + relative)
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    check(digest == expected, "digest: " + relative)
    return data, {"path": relative, "bytes": len(data), "sha256": digest}

def main():
    documents, verified = {}, []
    for relative, expected in PINNED.items():
        data, item = read_exact(relative, expected)
        documents[relative] = json.loads(data)
        verified.append(item)
    selected_members = {
        "verification/android-editor-membership-compiled-boundary-qualification/delegated-overload-association-v2/seal.json": ["delegated_raw_v2.py", "policy.json", "README.md"],
        "verification/android-editor-subject-typed-join-validator-correction/seal.json": ["typed_join.py"],
        "verification/android-field-preservation-observation-controls/seal.json": ["inputs/exact-four-subject-contracts.json", "finite-facet-joins.json"],
    }
    for seal_name, names in selected_members.items():
        members = {item["path"]: item for item in documents[seal_name]["members"]}
        base = str(Path(seal_name).parent)
        for name in names:
            expected = members[name]
            data, item = read_exact(base + "/" + name, expected["sha256"])
            check(len(data) == expected["bytes"], "member size: " + name)
            verified.append(item)
            if name.endswith(".json"):
                documents[base + "/" + name] = json.loads(data)
    baseline = documents["verification/android-field-preservation-observation-controls/inputs/original-280-obligations.json"]
    check(baseline["context_id"] == CONTEXT, "original source context")
    original = {subject["id"]: subject for subject in baseline["subjects"]}
    check(len(original) == len(baseline["subjects"]) == 280, "original subject identities")
    four = documents["verification/android-field-preservation-observation-controls/inputs/exact-four-subject-contracts.json"]
    check(four["source_context"] == CONTEXT and len(four["subjects"]) == 4, "four subject context/count")
    for subject in four["subjects"]:
        check(subject == original[subject["id"]], "complete original subject retained: " + subject["id"])
        check(len(subject["required_semantic_cases"]) == 8, "eight original cases")
    for relative in selected_members:
        if "qualified" in documents[relative]:
            check(documents[relative]["qualified"] is False, "utility is unqualified")
    script_bytes = Path(__file__).read_bytes()
    report = {
        "schema": 1,
        "status": "preaccess-contracts-verified-final-freeze-required",
        "command": [sys.executable, "-B", str(Path(__file__).resolve())],
        "python": sys.version,
        "platform": platform.platform(),
        "source_revision_context": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip(),
        "review_script": {"bytes": len(script_bytes), "sha256": hashlib.sha256(script_bytes).hexdigest()},
        "verified_released_files": verified,
        "original_subjects": 280,
        "four_whole_original_subjects_equal": True,
        "eight_original_cases_each_retained": True,
        "active_author_candidate_accessed": False,
        "product_or_producer_code_executed": False,
        "native_UI_capture_or_process_inventory": False,
        "final_matrix_accepted": False,
        "qualified": False,
        "stdout": "PASS: 14 released file identities; original280 and four whole original records retained; final freeze required",
    }
    check(len(verified) == 14, "exact preaccess verified-file count")
    (OUT / "preaccess-receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["stdout"])

if __name__ == "__main__":
    main()
