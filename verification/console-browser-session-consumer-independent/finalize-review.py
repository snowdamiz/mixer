"""Freeze independent review evidence and remove only this lane's emitted scratch."""
from __future__ import annotations
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[1]
def sha(data): return hashlib.sha256(data).hexdigest()
def item(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(raw), "sha256": sha(raw)}

oracle_sha = "58969cf14bb489ff3d3ddce7b2963ee3d762b153facc344beb4bd933a9491f36"
assert sha((OWN / "preaccess-oracles.md").read_bytes()) == oracle_sha
release_path = ROOT / "verification/console-session-and-checkout-root-review/session-consumer-frozen-release.json"
release = json.loads(release_path.read_bytes())
source_manifest_path = ROOT / release["source_manifest"]["path"]
assert sha(source_manifest_path.read_bytes()) == release["source_manifest"]["sha256"]
manifest = json.loads(source_manifest_path.read_bytes())
for source in manifest["files"]:
    raw = (ROOT / source["path"]).read_bytes()
    assert len(raw) == source["bytes"] and sha(raw) == source["sha256"]
baseline = json.loads((OWN / "preaccess-custody.json").read_bytes())
canonical = []
for source in baseline["canonical_inputs"]:
    match = sha((ROOT / source["path"]).read_bytes()) == source["sha256"]
    canonical.append({"path": source["path"], "preaccess_sha256": source["sha256"], "matches_current": match})
    assert match

rows = []
protocol_notes = {
    "CL01": "Exact request and frozen authenticated/unauthenticated scalar copies.",
    "CL02": "Unknown symbol/nonenumerable own options, invalid values, timeout boundaries.",
    "CL03": "Representative non200 branches plus HTML200; no body reads on non200.",
    "CL04": "Redirect flag, media/charset/parameter grammar and permitted ASCII case/whitespace.",
    "CL05": "Directive token/quoted text/malformed list and valid separate no-store.",
    "CL06": "Canonical decimal length header, safe/size bound, independently counted data.",
    "CL07": "Complete 4096 success, single/cumulative4097 overflow, cancel/release.",
    "CL08": "4096 calls including final done; empty chunks consume budget.",
    "CL09": "Missing stream, invalid/split UTF8, BOM, nonASCII and trailing junk/whitespace.",
    "CL10": "Flat object, duplicate/escaped keys and values, unknown/missing/nested/trailing JSON.",
    "CL11": "Independent base64url fixtures, final sextet unused bits and closed string forms.",
    "CL12": "Signed/fraction/exponent/leading zero/string/unsafe token rejection and safe seconds.",
    "CL13": "Caller/deadline while fetch/read stalls; stalled cancel; late resolve/reject; preabort.",
    "CL14": "Private fetch/header/read/cleanup exceptions map closed; unhandled rejection monitor.",
    "CL15": "Decode advances clock or aborts caller before final publication fence.",
    "CO01": "Idle constructor, initial frozen state, subscriptions and exact public surface.",
    "CO02": "Synchronous unavailable before current workspace abort handler observes state.",
    "CO03": "Out-of-order three operations; equal/different generation fresh capability and stale failure.",
    "CO04": "Captured wrapper organizations/projects block dispatch after six epoch-removal causes.",
    "CO05": "Session latency consumes lifetime, exact deadline denial,900second monotonic cap.",
    "CO06": "Invalid wall/mono samples and seconds multiplication/sum overflow fail closed.",
    "CO07": "Independent wall/mono equality and rollback on getSession/delegate; result fence in CO12.",
    "CO08": "Controlled delivery of actual owned timer clears ready, no automatic retry; explicit retry.",
    "CO09": "Actual cookie client/parser fixed encoded org/project query and headers; invalid page.",
    "CO10": "Concurrent operations, caller-scoped abort, outer abort of all, already-aborted dispatch fence.",
    "CO11": "Actual current401 outer invalidation,403/404/503scoping and forged error fallback.",
    "CO12": "Postawait success/failure expiry fence and late stale401 cannot remove new ready.",
    "CO13": "Independent runtime: synchronous subscriber exception, unsubscription and nested revalidate. Async rejecting observer is source/producer-only evidence; no expanded API requirement imposed.",
    "CO14": "Abort-triggered nested revalidate ownership and abort-triggered disposal terminality.",
    "CO15": "Pending session disposal, late completion, no subscribers/new work after idempotent dispose.",
}
for prefix in ["CL", "CO"]:
    for number in range(1, 16):
        identifier = f"{prefix}{number:02}"
        rows.append({"id": identifier, "status": "checked-independent-host", "run": "run-protocol", "scope": protocol_notes[identifier]})
solid_notes = {
    "SO01": "Visible exact startup/coalescing; hidden waits; real Solid owner.",
    "SO02": "Same-turn foreground coalesces and replaces/aborts older pending metadata.",
    "SO03": "Hidden without event, pure read/action fence, real workspace rows and pending project abort.",
    "SO04": "Pagehide while visible withholds pending metadata and captured old client.",
    "SO05": "Pageshow/focus visibility fresh epoch, clears selection and starts first page.",
    "SO06": "Only exact plain data invalidation, descriptor/symbol/extra checks, no rebroadcast.",
    "SO07": "Local fixed signal; hidden no read; missing/throwing channel retains foreground.",
    "SO08": "Queued cross-tab/foreground plus hidden/dispose fences, late metadata withheld.",
    "SO09": "Actual cookie+Solid workspace join, equal/different epochs, selection/cursor and pure action fence, current401. Corrected fixture targeted run only.",
    "SO10": "Owned cleanup preserves separately installed listeners; no queued/action revival.",
    "SO11": "Source-only structural assertions of reactive main/App seam and owner guard. Actual DOM/browser entry not executed independently.",
    "SO12": "404/503/HTML200/missing no-store host fixtures remain unavailable with no workspace fetch.",
}
for number in range(1, 13):
    identifier = f"SO{number:02}"
    rows.append({"id": identifier, "status": "checked-independent-host-and-source" if number == 11 else "checked-independent-host", "run": "run-solid-so09" if number == 9 else "run-solid", "scope": solid_notes[identifier]})
pending = [
    {"scope": "Actual main/App rendered DOM", "status": "not-independently-executed", "observed_evidence": "reactive source assertion; frozen producer build/SSR attributed to producer"},
    {"scope": "Async-returning subscriber rejection", "status": "source-and-producer-evidence-reviewed-no-independent-replay", "observed_evidence": "controller line65 consumes returned-promise rejection; producer test line232 includes rejecting async observer; independentCO13tests synchronous throws/reentry"},
    {"scope": "Real Endpoint/default verifier/default Repo join", "status": "pending", "observed_evidence": "released selection says canonical session/cookie endpoints absent; host404/HTMLfixtures fail closed"},
    {"scope": "Provider/OIDC/callback/activation/logout/revocation/startup/custody", "status": "pending-not-replayed", "observed_evidence": "no backend/stopped harness execution"},
    {"scope": "Browser cookie/visibility/BroadcastChannel/bfcache/accessibility/UI", "status": "pending-paused", "observed_evidence": "synthetic EventTargets and channel with real Solid runtime only"},
    {"scope": "Ingress/CDN/private cache isolation", "status": "pending", "observed_evidence": "client no-store directive checks do not qualify isolation"},
    {"scope": "Customer/FieldLog immutable-package dogfood and GA", "status": "pending", "observed_evidence": "no customer/published package/gate acceptance"},
    {"scope": "Native simulator/emulator/phones", "status": "pending-paused", "observed_evidence": "no native process started"},
]
(OWN / "checked-pending-matrix.json").write_text(json.dumps({"schema": 1, "unique_roster_ids": 42, "rows": rows, "pending_and_attribution_limits": pending}, indent=2) + "\n")

original = (OWN / "solid.test.mjs.before-so09-correction").read_text().splitlines(keepends=True)
corrected = (OWN / "solid.test.mjs").read_text().splitlines(keepends=True)
(OWN / "fixture-correction.patch").write_text("".join(difflib.unified_diff(original, corrected, fromfile="solid.test.mjs.before-so09-correction", tofile="solid.test.mjs")))
scratch = OWN / "scratch"
assert scratch.resolve() == OWN / "scratch"
assert (scratch / "node_modules").is_symlink()
scratch_files = [item(path) for path in sorted((scratch / "modules").rglob("*.js"))]
shutil.rmtree(scratch)
assert not scratch.exists()
runs = [json.loads((OWN / f"run-{phase}/receipt.json").read_bytes()) for phase in ["compile", "protocol", "solid", "solid-so09"]]
assert [run["exit_code"] for run in runs] == [0, 0, 1, 0]
assert all(run["captured_group_absent"] and run["unchanged"] for run in runs)
head = subprocess.run(["git", "rev-parse", "HEAD", "HEAD^{tree}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
receipt = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))], "python": sys.version,
    "status": "independent-source-and-host-review-complete-no-actionable-product-findings-root-acceptance-pending",
    "source_revision": manifest["revision"], "tracked_tree": manifest["tracked_tree"], "observed_head_tree_at_finalization": head,
    "source_digest": manifest["source_digest_sha256"], "source_manifest": item(source_manifest_path), "root_release": item(release_path),
    "selected_files_checked_each_command": 65, "preaccess_oracles": item(OWN / "preaccess-oracles.md"), "preaccess_custody": item(OWN / "preaccess-custody.json"),
    "canonical_baseline_comparison": canonical, "source_files_and_product_unchanged": True,
    "runs": runs, "unique_probe_ids_with_final_successful_observation": 42,
    "count_attribution": {"protocol": {"pass": 30, "fail": 0}, "original_solid": {"pass": 11, "fail": 1, "failure": "independent SO09 fixture scheduling error"}, "corrected_targeted_SO09": {"pass": 1, "fail": 0}, "no_12_of_12_same_run_claim": True},
    "harness_correction": {"original": item(OWN / "solid.test.mjs.before-so09-correction"), "corrected": item(OWN / "solid.test.mjs"), "patch": item(OWN / "fixture-correction.patch"), "product_delta": []},
    "tools": {"node": "v22.23.3 as emitted by each independent runtime", "typescript": "5.9.3 from installed package manifest", "solid": "1.9.17 from installed package manifest", "platform": "darwin arm64"},
    "budget": {"compiler_commands": 1, "allocated_initial_node_runs": 2, "additional_root_selected_targeted_node_runs": 1, "unused_compiler_allowance": 1, "no_further_execution": True},
    "cleanup": {"captured_groups_absent": True, "scratch_removed": True, "scratch_node_modules_symlink_removed_without_touching_target": True, "emitted_files_before_removal": scratch_files, "test_owned_timers_listeners_channels": "asserted cleaned", "unhandled_rejections": "none observed in each harness", "global_inventory": False},
    "prohibited_activity": {"git_mutations": False, "new_dependencies": False, "hosted_changes": False, "browser_ui_capture_native": False, "stopped_callback_or_android_retry": False, "publication_customer_credentials": False},
    "pending": pending, "actionable_product_findings": [], "root_implementation_accepted": False, "GA_gates_verified": 0,
}
(OWN / "review-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
files = [item(path) for path in sorted(OWN.rglob("*")) if path.is_file() and path.name != "review-seal.json"]
raw = json.dumps(files, separators=(",", ":"), sort_keys=True).encode()
seal = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "frozen-independent-review-packet", "members": files, "content_digest_sha256": sha(raw), "source_digest": manifest["source_digest_sha256"], "preaccess_oracle_sha256": oracle_sha, "root_acceptance_pending": True, "GA_gates_verified": 0}
(OWN / "review-seal.json").write_text(json.dumps(seal, indent=2) + "\n")
print(json.dumps({"status": receipt["status"], "unique_probe_ids": 42, "original_solid": receipt["count_attribution"]["original_solid"], "corrected_targeted_SO09": receipt["count_attribution"]["corrected_targeted_SO09"], "canonical_inputs_unchanged": len(canonical), "scratch_removed": True, "members": len(files), "seal_content_digest": seal["content_digest_sha256"], "GA_gates_verified": 0}))
