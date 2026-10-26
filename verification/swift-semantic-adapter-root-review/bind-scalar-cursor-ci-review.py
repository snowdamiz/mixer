"""Admit independent review of the exact frozen closed fixture runner."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
BASE = ROOT / "verification/swift-cache-state-ci-preparation"
OUT = HERE / "scalar-cursor-ci-review-custody.json"

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def require(ok, why):
    if not ok:
        raise ValueError(why)

require(not OUT.exists(), "Immutable custody already recorded")
seal = BASE / "seal.json"
require(sha(seal) == "b22b11db7ce9dda9910117d730eed385793426fb220981fa15de71b9253b39f8", "Seal identity")
rows = json.loads(seal.read_text())["members"]
require(len(rows) == 2434, "Member count")
seen = set()
for row in rows:
    p = BASE / row["path"]
    require(p.resolve().is_relative_to(BASE.resolve()) and not p.is_symlink() and row["path"] not in seen, "Member path")
    seen.add(row["path"])
    require(p.stat().st_size == row["bytes"] and sha(p) == row["sha256"], row["path"])
require(sum(r["bytes"] for r in rows) == 156179074, "Member bytes")
runner = BASE / "check_cache_state.py"
require(sha(runner) == "92bf2c0ca453ad9cae8ad6274d2248870af1cad4f4044039afde28f806d4392d", "Runner identity")
pack = BASE / "pack/manifest.json"
require(sha(pack) == "6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857", "Pack identity")
require(sha(BASE / "pack/source/library/cache_state.rs") == "f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b", "Selected source identity")
context = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
require(context == "8ac624160a2cfff10d201d8063f69cf05f005edb", "Quiescent checkpoint")
receipt = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "argv": sys.argv, "python": sys.version, "selector_sha256": sha(pathlib.Path(__file__)),
    "context_revision": context, "seal": str(seal.relative_to(ROOT)), "seal_sha256": sha(seal),
    "members_verified": len(rows), "member_bytes": sum(r["bytes"] for r in rows),
    "runner_sha256": sha(runner), "pack_manifest_sha256": sha(pack),
    "selected_source_sha256": sha(BASE / "pack/source/library/cache_state.rs"),
    "decision": "Custody verified; authorize fresh independent code audit, owned-copy closed host execution and negative controls only",
    "owned_copy": "Copy exact check_cache_state.py and full pack into independent owned folder under original repository; create empty runs; no producer writes or source/hash overrides",
    "Git_context": "Read-only rev-parse calls via runner may discover original checkout from nested ROOT; no initialization/mutation/bypass. Root holds commits/index/delivery changes through independent complete invocation",
    "execution_bounds": {"active_seconds": 600, "cleanup_seconds": 60, "each_child_seconds": 60, "compiler": "already-installed actual Rust1.99.0 aarch64-apple-darwin", "new_compiler_installation": False},
    "producer_reported": {"commands": 103, "elapsed_seconds": 178.658114, "max_child_seconds": 38.150979, "distinct_methods_each_mode": 132, "method_invocations_each_mode": 384, "API_dispositions_each_mode": 25, "primary_API_spans_each_mode": 38, "distinct_File_cases_each_mode": 31, "layouts_each_mode": 23, "focused_runner_controls": 22},
    "retained_failures": ["First inherited API command path slash", "Superseded full success before final custody checks", "First final complete checks rejected root checkout change; unchanged rerun passed"],
    "pending": ["Independent actual source/runner review", "Rust1.98.1 actual CI qualification", "Canonical runner/pack/workflow selection and placement"],
    "canonical_runtime_native_or_GA_accepted": False,
}
OUT.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"path": str(OUT.relative_to(ROOT)), "sha256": sha(OUT), "members_verified": len(rows)}))
