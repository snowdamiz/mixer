#!/usr/bin/env python3
"""Offline input custody audit only; does not run any Mixer or Elixir code."""
import datetime
import ast
import hashlib
import json
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / "verification/console-key-owner-dead-supervisor-correction"
EXPECTED_MANIFEST = "08598168a371c8e635136f25c1e493c5a6b14be67e8cbb64a0bc18a015af4e18"
EXPECTED_TREE = "417ba3eb32cbacaff13dfd0ab73c97edd38c98e354208a27ce766959b52f4178"
EXPECTED_HEAD = "41af4a3bc14f62e477c66c9553fd4ff559d19590"
EXPECTED_DECISION = "93038ad2e558da7f88e8debfad5187a03c2ffd0174c8dce07506526147d70ad7"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pairs(rows):
    result = {}
    for key, value in rows:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def pin(path):
    path = Path(path)
    assert not path.is_symlink(), path
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": digest(data)}


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True)
    return result.stdout


manifest_path = PACKET / "packet-manifest.json"
assert digest(manifest_path.read_bytes()) == EXPECTED_MANIFEST
manifest = load(manifest_path)
rows = manifest["members"]
assert len(rows) == 35
names = [row["path"] for row in rows]
assert names == sorted(names) and len(set(names)) == len(names)
assert set(names) == {
    str(path.relative_to(PACKET)) for path in PACKET.rglob("*")
    if path.is_file() and path != manifest_path
}
for row in rows:
    relative = Path(row["path"])
    assert not relative.is_absolute() and ".." not in relative.parts
    path = PACKET / relative
    assert all(not parent.is_symlink() for parent in [path, *path.parents])
    data = path.read_bytes()
    assert len(data) == row["bytes"] and digest(data) == row["sha256"], relative
tree = digest("".join(f'{row["sha256"]}  {row["path"]}\n' for row in rows).encode())
assert tree == EXPECTED_TREE == manifest["tree_digest_sha256"]
assert git("rev-parse", "HEAD").decode().strip() == EXPECTED_HEAD

freeze = load(PACKET / "source-freeze.json")
source_bindings = []
for row in freeze["candidate_sources"]:
    before = (PACKET / "inputs" / row["path"]).read_bytes()
    candidate = (PACKET / row["snapshot"]).read_bytes()
    current = (ROOT / row["path"]).read_bytes()
    assert digest(before) == row["before_sha256"]
    assert git("show", f'{EXPECTED_HEAD}:{row["path"]}') == before
    assert candidate == current and digest(current) == row["after_sha256"]
    source_bindings.append(pin(ROOT / row["path"]))
for row in freeze["unchanged_inputs"]:
    assert digest((ROOT / row["path"]).read_bytes()) == row["sha256"], row["path"]
    assert (PACKET / "inputs" / row["path"]).read_bytes() == (ROOT / row["path"]).read_bytes()

terminal_path = ROOT / "verification/console-key-owner-inflight-lifecycle-independent/remote-ci-terminal-review-1/decision.json"
assert digest(terminal_path.read_bytes()) == EXPECTED_DECISION
terminal = load(terminal_path)
remote = ROOT / "verification/github-delivery-http2-inflight/phoenix-remote-artifact"
for name in ("KOL08-GRACEFUL", "KOL09-KILL"):
    assert (remote / f"identity-lifecycle/{name}-observation.json").read_bytes() == (
        PACKET / "inputs/verification/github-delivery-http2-inflight/phoenix-remote-artifact" /
        f"identity-lifecycle/{name}-observation.json"
    ).read_bytes()
assert terminal["evidence_identity"]["delivered_commit"] == EXPECTED_HEAD
assert terminal["KOL09_KILL"]["actual_failed_assertion"].endswith("old_resources_down_before_replacement")
assert terminal["KOL09_KILL"]["callback_clean"] is False
assert digest((remote / "tests.log").read_bytes()) == terminal["evidence_identity"]["tests_log"]["sha256"]

relation_results = []
relation_bindings = []
for major, expected in [(16, "079b8cdeb3c039284b3ae402664230f6abc01782ab5e7f08219a06067e22cadf"),
                        (17, "100df9346930b778611b46e821484db025671819b3bb966cfcb496014ce42785")]:
    path = ROOT / f"hosted/priv/browser_auth/relation_surface_v1_pg{major}.json"
    assert digest(path.read_bytes()) == expected
    bindings = load(path)["source_bindings"]
    relation_bindings.append(bindings)
    for relative, expected_digest in bindings.items():
        assert digest((ROOT / relative).read_bytes()) == expected_digest, relative
    assert not {row["path"] for row in freeze["candidate_sources"]} & set(bindings)
    relation_results.append({**pin(path), "source_binding_count": len(bindings),
                             "all_source_bindings_current": True,
                             "candidate_sources_bound": False})
assert relation_bindings[0] == relation_bindings[1]

collector_path = ROOT / "hosted/test/mixer_hosted/browser_auth/run_callback_fixture.py"
collector_ast = ast.parse(collector_path.read_bytes())
collector_pins = next(ast.literal_eval(node.value) for node in collector_ast.body
                      if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "RELATION_PINS"
                              for target in node.targets))
callback_pin_results = []
for relative, expected in collector_pins.items():
    path = ROOT / relative
    actual = digest(path.read_bytes())
    assert git("show", f"{EXPECTED_HEAD}:{relative}") == path.read_bytes()
    callback_pin_results.append({"path": relative, "collector_expected_sha256": expected,
                                 "current_and_HEAD_sha256": actual,
                                 "matches": expected == actual})
assert [row["path"] for row in callback_pin_results if not row["matches"]] == [
    "hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex"
]
assert git("ls-files", "--", str(collector_path.relative_to(ROOT))) == b""
committed_workflow = git("show", f"{EXPECTED_HEAD}:.github/workflows/hosted.yml")
committed_workflow_snapshot = OUT / "inputs/committed-workflow-hosted.yml"
committed_workflow_snapshot.parent.mkdir(parents=True, exist_ok=True)
committed_workflow_snapshot.write_bytes(committed_workflow)
assert b"run_callback_fixture.py" not in committed_workflow
assert b"scripts/test-local.py" in committed_workflow

extra = [
    "hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex",
    "hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex",
    "hosted/test/mixer_hosted/browser_auth/run_callback_fixture.py",
    "verification/hosted-browser-callback-ci/attempts/20261025T214714.739971Z-5f9bffc5-8479-49c1-b490-c50947ab0170/inputs/hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex",
    "verification/console-key-owner-inflight-lifecycle-contract/contract.md",
    "verification/console-key-owner-inflight-lifecycle-independent/PREACCESS.md",
]
bindings = [pin(manifest_path), pin(terminal_path), pin(committed_workflow_snapshot), *source_bindings,
            *[pin(ROOT / row["path"]) for row in freeze["unchanged_inputs"]],
            *[pin(ROOT / path) for path in extra],
            *[pin(ROOT / row["path"]) for row in relation_results]]
bindings = sorted({row["path"]: row for row in bindings}.values(), key=lambda row: row["path"])
review_tree = digest("".join(f'{row["sha256"]}  {row["path"]}\n' for row in bindings).encode())
result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope": "offline file, JSON, source and Git object inspection only",
    "review_command": "python3 verification/console-key-owner-dead-supervisor-correction-independent/audit.py",
    "tools": {"python": platform.python_version(), "git": git("--version").decode().strip()},
    "head": EXPECTED_HEAD,
    "packet": {**pin(manifest_path), "members_verified": len(rows), "tree_digest_sha256": tree},
    "candidate_beforeimages_match_HEAD": True,
    "canonical_candidates_match_packet": True,
    "unchanged_inputs_verified": len(freeze["unchanged_inputs"]),
    "original_remote_decision_verified": pin(terminal_path),
    "relation_manifest": relation_results,
    "callback_collector_relation_pins": callback_pin_results,
    "callback_collector_existing_held_lane_limitation": "Current untracked collector rejects the current and HEAD RelationManifest source hash before any selected methods. The current dirty workflow invokes it before Phoenix. Root identifies both as a separately HELD UnitA lane and excludes them from this correction and committed ordinary CI. No callback replay is selected; this does not block the two-file correction. No held-lane edit is authorized by this review.",
    "ordinary_committed_workflow": {**pin(committed_workflow_snapshot),
                                    "git_object": f"{EXPECTED_HEAD}:.github/workflows/hosted.yml",
                                    "selected_callback_collector_invocation": False,
                                    "ordinary_full_Phoenix_collector_invocation": True,
                                    "differs_from_protected_dirty_workflow": committed_workflow != (ROOT / ".github/workflows/hosted.yml").read_bytes()},
    "review_input_manifest_encoding": "sorted sha256 + two spaces + repository-relative path + newline",
    "review_input_tree_digest_sha256": review_tree,
    "review_inputs": bindings,
    "product_runtime_compiler_formatter_tests_TLS_process_probes": 0,
    "result": "integrity verified; source correctness decision is separate; no behavior acceptance"
}
(OUT / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: result[key] for key in ("head", "packet", "unchanged_inputs_verified", "review_input_tree_digest_sha256", "result")}, indent=2))
