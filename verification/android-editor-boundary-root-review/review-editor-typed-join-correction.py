"""One-shot scoped root review of a frozen correction, never runtime qualification."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def identity(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def packet(name, expected):
    folder = ROOT / "verification" / name
    assert identity(folder / "seal.json")["sha256"] == expected
    seal = json.loads((folder / "seal.json").read_bytes())
    names = set()
    for row in seal["members"]:
        name = row["path"]
        p = PurePosixPath(name)
        assert not p.is_absolute() and ".." not in p.parts and name not in names
        names.add(name)
        assert identity(folder / name) == {k: row[k] for k in ("bytes", "sha256")}
    for path in folder.rglob("*"):
        assert not path.is_symlink()
    assert {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()} == names | {"seal.json"}
    return folder, {"path": str(folder.relative_to(ROOT)), "seal_sha256": expected,
                    "member_count": len(names), "member_bytes": sum(r["bytes"] for r in seal["members"])}

assert __debug__ and not (OUT / "editor-typed-join-correction-selection.json").exists()
base, base_id = packet("android-editor-subject-typed-join-validator", "fed4e7f14c82d1f17b69a4ef2a6809e34edfba0adc67b5c773944e809b839c5d")
candidate, candidate_id = packet("android-editor-subject-typed-join-validator-correction", "18fd1576d22572e6cb8e9a68c5d0d83a3042f4b465d2b258fb53a9c930de71c9")
assert identity(candidate / "policy.json") == identity(base / "policy.json")
assert identity(candidate / "test_typed_join.py") == identity(base / "test_typed_join.py")
assert identity(candidate / "root-findings.json") == identity(OUT / "editor-typed-join-root-findings.json")
policy = json.loads((candidate / "policy.json").read_bytes())
semantic = ROOT / "verification/android-editor-membership-compiled-boundary-qualification/semantic-review-candidate-v1"
assert identity(semantic / "seal.json")["sha256"] == "361412b6ee2124ace685a2242390ece375d0327b119876b13db27dc95ea3f5e6"
members = {r["path"]: r for r in json.loads((semantic / "seal.json").read_bytes())["members"]}
for name in ("active-semantic-obligations.json", "historical189-current-bindings.json"):
    assert identity(semantic / name) == {k: members[name][k] for k in ("bytes", "sha256")}
original = json.loads((semantic / "active-semantic-obligations.json").read_bytes())["subjects"]
selected = {s["id"]: s for s in original if s["class"] in policy["class_counts"]}
assert len(selected) == 103 and {s["id"] for s in policy["subjects"]} == set(selected)
for subject in policy["subjects"]:
    old = selected[subject["id"]]
    for key in ("id", "class", "method", "descriptor", "source_sha256", "class_sha256", "categories", "required_semantic_cases"):
        assert subject[key] == old[key]
    expected = [{**{k: old[k] for k in ("class", "method", "descriptor", "source_sha256", "class_sha256")},
                 "bci": i["bci"], "opcode": i["opcode"], "mnemonic": i["mnemonic"], "callee": i["target"]} for i in old["invocations"]]
    assert subject["exact_invocations"] == expected
history = json.loads((semantic / "historical189-current-bindings.json").read_bytes())["records"]
assert policy["historical189_ids"] == [r["historical_id"] for r in history]
assert len(policy["historical9_replacements"]) == 9 and len(policy["out_of_scope_replacement_links"]) == 1
commands = []
for name, script in (("retained42", "test_typed_join.py"), ("correction15", "test_corrections.py")):
    argv = [sys.executable, "-B", str(candidate / script)]
    start = time.monotonic()
    result = subprocess.run(argv, cwd=candidate, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    paths = {}
    for suffix, data in (("stdout", result.stdout), ("stderr", result.stderr)):
        path = OUT / ("editor-typed-join-correction-" + name + "." + suffix)
        with path.open("xb") as stream:
            stream.write(data)
        paths[suffix] = {"path": str(path.relative_to(ROOT)), **identity(path)}
    commands.append({"argv": argv, "cwd": str(candidate), "exit": result.returncode,
                     "elapsed_seconds": time.monotonic() - start, "child_reaped": True, **paths})
    result.check_returncode()
packet(base_id["path"].removeprefix("verification/"), base_id["seal_sha256"])
packet(candidate_id["path"].removeprefix("verification/"), candidate_id["seal_sha256"])
receipt = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "status": "accepted-corrected-isolated-typed-consistency-utility-only", "base": base_id, "correction": candidate_id,
    "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "python": platform.python_version(), "script": identity(Path(__file__)), "commands": commands,
    "original_103_subject_identity_categories_cases_invocations_preserved": True,
    "all_189_history_ids_and_nine_editor_replacements_preserved": True,
    "unchanged_policy": identity(candidate / "policy.json"), "selected_module": identity(candidate / "typed_join.py"),
    "fresh_retained_tests": 42, "fresh_correction_tests": 15, "four_exact_root_findings_now_refused": True,
    "source_review": "Strict recursive type-preserving tuple/policy/result equality; consistent public and subject refusal outcomes; native tuple validated even without native outcome; forbidden native calls rejected on refusal paths.",
    "base_and_correction_unchanged_after": True, "all_results_remain_unqualified": True,
    "pending": ["mandatory composed delegated raw-event checker", "complete subject/case/state behavior", "missing body and native exception outcomes", "execution-source closure", "canonical integration", "native runtime", "OTA and GA"],
    "native_UI_capture_process_inventory_started": False, "full_matrix_native_OTA_GA_accepted": False}
with (OUT / "editor-typed-join-correction-selection.json").open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
print(json.dumps({"status": receipt["status"], "tests": 57, "receipt": identity(OUT / "editor-typed-join-correction-selection.json")}))
