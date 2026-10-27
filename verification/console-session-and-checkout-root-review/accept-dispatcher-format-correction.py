"""Preserve the failed remote format gate and accept its formatting-only repair."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / "verification/console-fixed-dispatcher-format-correction"
CI = ROOT / "verification/github-delivery-fixed-dispatcher-android-checkout"
DEST = OUT / "fixed-dispatcher-format-acceptance.json"


def read(path):
    return json.loads(path.read_bytes())


def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


assert not DEST.exists(), "One-shot; do not replay"
assert row(PACKET / "seal.sha256")["sha256"] == "044a8823348612cd068c5bc3739b7c51f9657eb6bd9a6909a7bd00311509b99a"
members = []
for line in (PACKET / "seal.sha256").read_text().splitlines():
    digest, name = line.split("  ", 1)
    assert not Path(name).is_absolute() and ".." not in Path(name).parts
    member = row(PACKET / name)
    assert member["sha256"] == digest
    members.append(member)
assert len(members) == 56
assert len([p for p in PACKET.rglob("*") if p.is_file()]) == 57
r = read(PACKET / "receipt.json")
assert r["status"] == "passed" and r["failure"] is None
assert all(c["exit_code"] == 0 and not c["timed_out"] and c["direct_child_reaped"] for c in r["commands"])
after = read(PACKET / "source-after.json")
assert len(after["sha256"]) == 6 and len(r["changed_canonical_files"]) == 4
for name, digest in {**after["sha256"], **after["protected_sha256"]}.items():
    assert row(ROOT / name)["sha256"] == digest
for name in after["sha256"]:
    original = subprocess.check_output(["git", "show", "HEAD:" + name], cwd=ROOT, timeout=10)
    assert original == (PACKET / "before" / name).read_bytes()
ast_rows = (PACKET / "commands/normalized-ast-equivalence.stdout").read_text().splitlines()
assert len(ast_rows) == 6
for line in ast_rows:
    name, before_hash, after_hash, equality = line.split("\t")
    assert name in after["sha256"] and before_hash == after_hash and equality == "equal"
ci = read(CI / "ci-jobs-4.stdout")
assert ci["headSha"] == "d04fd5cc71bc72061f18203e414b90869129b4ca"
assert ci["databaseId"] == 40567963706 and ci["attempt"] == 1 and ci["conclusion"] == "failure"
job = ci["jobs"][0]
assert len(ci["jobs"]) == 1 and len(job["steps"]) == 13
failed = [s for s in job["steps"] if s["conclusion"] == "failure"]
assert len(failed) == 1 and failed[0]["name"] == "Phoenix and disposable PostgreSQL host checks"
terminal = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
            "commit": ci["headSha"], "run_id": ci["databaseId"], "attempt": 1,
            "conclusion": "failure", "failed_step": failed[0]["name"],
            "failure": "mix format --check-formatted failed on dispatcher.ex and three new tests before compile or behavioral tests",
            "job_url": job["url"], "steps_passed": sum(s["conclusion"] == "success" for s in job["steps"]),
            "steps_failed": 1, "steps_skipped": sum(s["conclusion"] == "skipped" for s in job["steps"]),
            "raw_observation": row(CI / "ci-jobs-4.stdout"), "raw_log": row(CI / "phoenix-failed-log-1.stdout"),
            "exact_remote_artifacts_preserved_in": str(PACKET.relative_to(ROOT)),
            "new_Phoenix_test_pass_claimed": False, "remote_cleanup_reported": True}
value = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
         "command": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))], "python": sys.version,
         "status": "accepted-formatting-only-correction-awaiting-delivery-and-remote-CI",
         "packet_seal": row(PACKET / "seal.sha256"), "packet_members": members,
         "source_revision": r["source_revision"], "receipt": row(PACKET / "receipt.json"),
         "six_file_after_tree": after["tree_digest_sha256"],
         "canonical_files": [row(ROOT / name) for name in after["sha256"]],
         "changed_canonical_files": r["changed_canonical_files"], "syntax_and_normalized_AST_equal": True,
         "explicit_six_file_formatter_check_passed": True,
         "root_review": "Reviewed complete four-file diff, official formatter argv and configuration, normalized AST checker and six equal results. Only formatting changes. No behavior test replay required for this low-impact correction.",
         "original_CI_failure": terminal, "prior_component_tests_remain_prior_evidence": True,
         "behavioral_tests_rerun": False, "protected_inputs_unchanged": True,
         "remote_CI_passed": False, "GA_accepted": False}
w = read(ROOT / "work-graph.json"); g = read(ROOT / "gates/ga.json")
assert w["packages"][7]["fixtureCacheStateContractCandidate"] == g["gates"][1]["fixtureCacheStateContractCandidate"]
assert w["packages"][4]["privateOwnerEffectContractCandidate"] == g["gates"][4]["privateOwnerEffectContractCandidate"]
save(CI / "terminal-phoenix-format-failure.json", terminal)
save(DEST, value)
entry = {"status": value["status"], "root_acceptance": row(DEST), "packet_seal": value["packet_seal"],
         "changed_canonical_files": r["changed_canonical_files"], "six_normalized_ASTs_equal": True,
         "explicit_formatter_check_passed": True, "delivery_pending": True, "remote_CI_passed": False}
for target in [w["packages"][13], g["gates"][21]]:
    target["fixedWorkspaceDispatcher"]["format_correction"] = copy.deepcopy(entry)
    target["fixedWorkspaceDispatcher"]["delivery"].update({
        "status": "pushed-Phoenix-format-failed-Engine-pending",
        "terminal_Phoenix": row(CI / "terminal-phoenix-format-failure.json")})
for target in [w["packages"][4], g["gates"][4]]:
    target["ownerHostSparseCheckout"]["delivery"].update({
        "status": "pushed-Android-job-passed-Phoenix-format-failed-full-Engine-pending",
        "terminal_Phoenix": row(CI / "terminal-phoenix-format-failure.json")})
for name, data in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + "\n")
for name in ["PLAN.md", "STATUS.md"]:
    path = ROOT / name; text = path.read_text()
    old = "The Android owner job passes all eight steps on attempt one with a three-second checkout; full Engine and Phoenix CI remain pending."
    new = "The Android owner job passes all eight steps on attempt one with a three-second checkout; full Engine remains pending. Phoenix fails its formatter gate before compilation or behavior tests. A formatting-only correction changes the four reported files, passes the explicit six-file formatter check and preserves all six parsed ASTs; delivery and new CI remain pending. The original remote failure is retained."
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
subprocess.run(["git", "diff", "--check", "--", *r["changed_canonical_files"], "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"], cwd=ROOT, timeout=10, check=True)
print(json.dumps({"format_correction_accepted": True, "files_changed": 4,
                  "normalized_ASTs_equal": 6, "packet_members": 56, "remote_CI_pending": True}))
