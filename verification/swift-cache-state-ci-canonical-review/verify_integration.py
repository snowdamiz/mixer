#!/usr/bin/env python3
"""Read-only canonical relocation inspection; output belongs to this review."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import platform
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANONICAL = ROOT / "verification/swift-cache-state-ci"
CORRECTED = ROOT / "verification/swift-cache-state-ci-root-correction-2"
PROPOSAL = ROOT / "verification/swift-cache-state-ci-workflow-review"
SELECTION = ROOT / "verification/swift-cache-state-ci-workflow-root-review/selection.json"


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    for component in [*path.parents, path]:
        need(not component.is_symlink(), "Symlink refused: " + str(component))
    need(stat.S_ISREG(path.stat().st_mode), "Regular file required: " + str(path))
    return path.read_bytes()


def row(path, relative_to):
    data = regular(path)
    return {"path": path.relative_to(relative_to).as_posix(), "bytes": len(data), "sha256": sha(data)}


def yaml(path):
    parser = "require 'json'; require 'psych'; puts JSON.generate(Psych.safe_load(File.read(ARGV[0]), aliases: false))"
    return json.loads(subprocess.check_output(["ruby", "-e", parser, str(path)], text=True, timeout=10))


selection_data = regular(SELECTION)
selection = json.loads(selection_data)
selected = selection["canonical_source_members"]
need(len(selected) == 90, "Root-selected canonical member count differs")
need(len({r["path"] for r in selected}) == 90, "Duplicate root-selected member")
actual_selected = [row(ROOT / r["path"], ROOT) for r in selected]
need(actual_selected == selected, "Canonical source bytes differ from root selection")

actual_source_paths = []
excluded_generated_or_readme = []
for path in sorted(CANONICAL.rglob("*")):
    need(not path.is_symlink(), "Canonical symlink refused")
    if not path.is_file():
        continue
    relative = path.relative_to(CANONICAL)
    if relative.parts[0] in {"logs", "runs"} or relative.as_posix() == "README.md":
        excluded_generated_or_readme.append(relative.as_posix())
    else:
        actual_source_paths.append(path.relative_to(ROOT).as_posix())
need(actual_source_paths == sorted(r["path"] for r in selected), "Unexpected/missing canonical source members")

corrected_seal_data = regular(CORRECTED / "source-seal.json")
need(sha(corrected_seal_data) == selection["inputs"][0]["sha256"], "Selected corrected source seal differs")
corrected_seal = json.loads(corrected_seal_data)
corrected_rows = [r for r in corrected_seal["members"] if r["path"].startswith("pack/") or r["path"] in {"check_cache_state.py", "test_runner.py"}]
need(len(corrected_rows) == 89, "Expected 89 corrected runner/test/pack files")
corrected_exact = []
for expected in corrected_rows:
    source, target = CORRECTED / expected["path"], CANONICAL / expected["path"]
    source_bytes, target_bytes = regular(source), regular(target)
    need(len(source_bytes) == expected["bytes"] and sha(source_bytes) == expected["sha256"], "Corrected sealed source differs")
    need(source_bytes == target_bytes, "Canonical relocation changed bytes: " + expected["path"])
    corrected_exact.append(expected)
need(regular(CANONICAL / ".gitignore") == regular(PROPOSAL / "proposed.gitignore") == b"/logs/\n/runs/\n", "Output ignore rules differ")

manifest_data = regular(CANONICAL / "pack/manifest.json")
need(sha(manifest_data) == selection["pack_manifest_sha256"] == "6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857", "Pack manifest differs")
manifest = json.loads(manifest_data)
pack_rows = [row(p, CANONICAL / "pack") for p in sorted((CANONICAL / "pack").rglob("*")) if p.is_file() and p != CANONICAL / "pack/manifest.json"]
need(pack_rows == manifest["members"], "Independent pack roster/digests differ")
need(len(pack_rows) == manifest["member_count"] == 86, "Pack member count differs")
need(sum(r["bytes"] for r in pack_rows) == manifest["total_bytes"], "Pack byte total differs")
tree_digest = sha(json.dumps(pack_rows, sort_keys=True, separators=(",", ":")).encode())
need(tree_digest == manifest["tree_sha256"], "Independent pack tree digest differs")

spec = importlib.util.spec_from_file_location("canonical_cache_state_review", CANONICAL / "check_cache_state.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
need(runner.HERE == CANONICAL and runner.ROOT == ROOT and runner.PACK == CANONICAL / "pack" and runner.RUNS == CANONICAL / "runs", "Canonical HERE/ROOT/PACK/RUNS relocation differs")
need((runner.ACTIVE_SECONDS, runner.CLEANUP_SECONDS, runner.CHILD_SECONDS) == (600, 60, 60), "Runner fixed bounds differ")
need(runner.verify_pack(runner.PACK) == manifest, "Relocated read-only runner pack verification differs")

workflow_data = regular(ROOT / ".github/workflows/verify.yml")
baseline_data = regular(PROPOSAL / "baseline.verify.yml")
need(workflow_data == regular(PROPOSAL / "proposed.verify.yml"), "Canonical workflow differs from exact reviewed proposal")
need(sha(workflow_data) == selection["workflow_sha256"] == "7f3ab7ef5ec94379a969c91e9f2348cecd2e80908c8a7330aef845f133f38e62", "Workflow hash differs")
need(workflow_data == baseline_data + regular(PROPOSAL / "job.yml"), "Existing workflow is not the exact byte prefix")
baseline, workflow = yaml(PROPOSAL / "baseline.verify.yml"), yaml(ROOT / ".github/workflows/verify.yml")
need(len(baseline["jobs"]) == 5 and sum(len(j["steps"]) for j in baseline["jobs"].values()) == 40, "Expected original five jobs/40 steps")
need(all(workflow["jobs"][name] == value for name, value in baseline["jobs"].items()), "Existing job/step objects differ")
new_job = workflow["jobs"].pop("swift-cache-state-fixture")
need(workflow == baseline, "Non-job workflow fields differ")
need(new_job["runs-on"] == "macos-15" and new_job["timeout-minutes"] == 30 and new_job["env"] == {"RUSTUP_AUTO_INSTALL": "0"}, "New independent job contract differs")
need(set(new_job) == {"runs-on", "timeout-minutes", "env", "steps"}, "New dependencies or job behavior introduced")
need(new_job["steps"][0]["with"] == {"fetch-depth": 1, "sparse-checkout-cone-mode": False, "sparse-checkout": "/verification/swift-cache-state-ci/"}, "Sparse checkout closure differs")
artifact = new_job["steps"][-1]
need(artifact["if"] == "always()" and artifact["with"]["include-hidden-files"] is True and artifact["with"]["retention-days"] == 14 and artifact["with"]["path"] == "${{ github.workspace }}/verification/swift-cache-state-ci/", "Complete artifact retention differs")

git_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=runner.ROOT, text=True).strip()
git_tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=runner.ROOT, text=True).strip()
receipt = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": sys.argv, "python": platform.python_version(),
    "scope": "Independent exact canonical relocation/closed pack/workflow inspection; read-only except this receipt.",
    "source_revision": git_revision, "source_tree": git_tree,
    "root_selection_sha256": sha(selection_data), "corrected_source_seal_sha256": sha(corrected_seal_data),
    "all90_root_selected_members_exact": True, "all89_runner_test_pack_members_byte_equal_to_corrected_source": True,
    "selected_members": actual_selected,
    "closed_pack": {"manifest_sha256": sha(manifest_data), "manifest_members": len(pack_rows), "physical_files_with_manifest": len(pack_rows) + 1, "member_bytes": manifest["total_bytes"], "tree_sha256": tree_digest, "selected_source_count": manifest["selected_source_count"]},
    "relocation": {"HERE": str(runner.HERE), "ROOT": str(runner.ROOT), "PACK": str(runner.PACK), "RUNS": str(runner.RUNS), "RUNS_exists": runner.RUNS.exists(), "fresh_output_behavior": "CI preparation creates fixed runs; relocated focused controls validate direct-child freshness and refusal under mocked owned runs; no canonical full run started."},
    "fixed_runner_limits_seconds": {"active": 600, "cleanup": 60, "child": 60},
    "workflow_sha256": sha(workflow_data), "existing_jobs_byte_prefix_and_parsed_equal": 5, "existing_steps_parsed_equal": 40,
    "canonical_generated_or_readme_exclusions": excluded_generated_or_readme,
    "new_full_Rust_invocation": False, "actual_Actions_qualified": False, "actual_Rust1_98_1_qualified": False,
    "native_UI_capture_device_or_GA_qualified": False,
}
(HERE / "inspection.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"canonical_members": 90, "byte_equal_corrected_members": 89, "pack_manifest_members": 86, "existing_jobs": 5, "existing_steps": 40, "workflow_sha256": sha(workflow_data), "source_revision": git_revision}))
