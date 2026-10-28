"""One-shot selection and metadata update for the root-authorized timestamp slice."""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
BASE = "dfd0e3196543cc1749c9cc924cc7accf28c9dc25"
BASE_TREE = "3cc58d6744649fdd138b9d3963b436db62480ecf"
CANONICAL = {
    "hosted/scripts/test-identity-network.py": "d9d750256b2734c80577f58b4eb9c8cfd0adf177ba12a453ecb1c050d0942c0e",
    "hosted/scripts/test_identity_network_collector.py": "8d3b37474fc132aa91d02f643956f87cfa2d177305aee167819ce3c5edd68691",
    "docs/hosted-identity-production-network-ci-contract.md": "37d2b3679bdedf9fbc7621f8ebaec81b27bb0d6de18b4d1dea0d3cfe3fc631db",
}
PROTECTED = {
    ".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
    "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
}

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def save(name, data):
    with (OUT / name).open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")

assert not (OUT / "selection.json").exists(), "One-shot; do not replay"
for path, digest in {**CANONICAL, **PROTECTED}.items():
    assert row(ROOT / path)["sha256"] == digest, path
independent = ROOT / "verification/identity-network-timestamp-independent"
manifest = read(independent / "packet-manifest.json")
packet_digest = hashlib.sha256(json.dumps(manifest["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
assert packet_digest == manifest["packet"] == "4ee4d1131272778e5e711bf69f859237364f35693413a1a08addfcbbc83c74a9"
for relative, expected in manifest["files"].items():
    assert not Path(relative).is_absolute() and ".." not in Path(relative).parts
    actual = row(independent / relative)
    assert {key: actual[key] for key in ("bytes", "sha256")} == expected, relative
readset = read(independent / "readset.json")
for relative, expected in readset["files"].items():
    actual = row(ROOT / relative)
    assert {key: actual[key] for key in ("bytes", "sha256")} == expected, relative
producer = ROOT / "verification/identity-network-jose-compile-investigation"
producer_members = sorted(path for path in producer.rglob("*") if path.is_file())
assert len(producer_members) == 5
assert {row(path)["path"] for path in producer_members} <= set(readset["files"])
assert read(producer / "receipt.json")["pure_controls_passed"] == 129
assert read(independent / "receipt.json")["tests_passed"] == 6

raw = ROOT / "verification/github-delivery-source-pair-and-rebar/ci-review"
assert row(raw / "packet-manifest.json")["sha256"] == "48d6355c9cc0ef37f2a4a2c08f5e03ce1ae50b1a46cddd95fe39b01f9f3af62b"
raw_manifest = read(raw / "packet-manifest.json")
assert raw_manifest["tree_digest_sha256"] == "07897c7721697313af70f814cea618128ca167c7d64e38a82dfea7d74bd2771d"
small_names = ["decision.json", "source-pair-review.json", "secondary-review.json", "cache-fixture-review.json"]
for name in small_names:
    actual = row(raw / name)
    assert {key: actual[key] for key in ("bytes", "sha256")} == raw_manifest["files"][name], name
decision = read(raw / "decision.json")
source_pair = read(raw / "source-pair-review.json")
secondary = read(raw / "secondary-review.json")
cache = read(raw / "cache-fixture-review.json")
prior = {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "scope": "Sanitized summaries imported from the root-accepted independent exact-8888 CI review; large raw evidence remains local and is not part of this delivery.",
    "source_revision": decision["source_revision"], "source_tree": decision["source_tree"],
    "verdict": decision["verdict"], "workflows": decision["workflows"],
    "network": {"run": 40766689512, "Rebar_DAG_capture_passed": True, "DAG_bytes": 895,
                "DAG_sha256": "680833a6cc7928d70c0a40fc29e86be79df92ac57d403eeb692121ee95d7ab1d",
                "methods_invoked": 2, "methods_passed": 0, "methods_failed": 2,
                "failure": ":jose_jwk.generate_key/1 unavailable", "all_three_exact_CIDs_cleanup_verified": True},
    "source_pair": source_pair, "secondary_observed_scope": secondary["observed_scope"],
    "cache_fixture": cache, "cleanup": decision["cleanup"], "limitations": decision["limitations"],
    "raw_evidence": {"availability": "local-only; not published in this delivery", "directory": str(raw.relative_to(ROOT)),
                     "manifest": row(raw / "packet-manifest.json"), "tree_digest_sha256": raw_manifest["tree_digest_sha256"],
                     "files": len(raw_manifest["files"]), "bytes": sum(item["bytes"] for item in raw_manifest["files"].values()),
                     "small_summary_bindings_rechecked": [row(raw / name) for name in small_names],
                     "complete_raw_packet_rehashed_by_this_delivery": False},
}
save("prior-ci-observation.json", prior)

fieldlog_source = Path("/Users/andreyyurlov/Documents/dev/fieldlog/.codex-public-fields-ci-review/sanitized-summary-candidate.json")
fieldlog_bytes = fieldlog_source.read_bytes()
assert hashlib.sha256(fieldlog_bytes).hexdigest() == "e2e69d26f742000fce583860d7c0f73dc6235a5791761b6d6bf886c7247976f3"
fieldlog = json.loads(fieldlog_bytes)
assert fieldlog["runID"] == 40765792113 and fieldlog["failedTests"] is None
assert fieldlog["buildCompletedObserved"] is False and fieldlog["commandStopReason"] == "execution-timeout"
assert fieldlog["remoteCommandCleanupVerified"] == 16 and fieldlog["rawFieldLogEvidenceIsSeparate"] is True
with (OUT / "fieldlog-public-fields-observation.json").open("xb") as stream:
    stream.write(fieldlog_bytes)

architecture = read(ROOT / "verification/github-delivery-architecture-comparison/dispatch-observation.json")
assert architecture["run"]["id"] == 40768719255 and architecture["run"]["head"] == BASE
assert architecture["run"]["status"] == "in_progress"
save("architecture-saved-observation.json", {"schema": 1, "scope": "Saved observation only; no new API query or result inference", **architecture})

selection = {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(), "basisRevision": BASE, "basisTree": BASE_TREE,
    "status": "Root-selected minimal positive prepared timestamp correction for fresh isolated CI; runtime pending",
    "canonical": [row(ROOT / path) for path in CANONICAL], "protected": PROTECTED,
    "producer_packet": [row(path) for path in producer_members],
    "independent_manifest": row(independent / "packet-manifest.json"), "independent_packet_map_digest": packet_digest,
    "independent_members_rehashed": len(manifest["files"]), "independent_readset_members_rehashed": len(readset["files"]),
    "pure_controls": {"producer": 129, "independent": 6, "original_bodies_unchanged": 126, "rerun_by_delivery": False},
    "source_derived_cause": "Mix1.20.4 missing target mtime0 plus source/header mtime0 falsely nonstale;16of113 JOSE Erlang modules compiled match OTP-external header closure;97omitted.",
    "correction": "Prepared archive entries fixed at POSIXmtime1 and fail-closed host admission; initial source-only transfer retainsmtime0.",
    "payload_entries_unchanged": 1232, "product_files_unchanged": 177,
    "named_unlock": "One fresh ordinary isolated identity-production-network CI run must establish complete dependencies and both unchanged product methods with exact isolation, semantic and cleanup evidence.",
    "runtime_or_GA_accepted": False, "new_manual_dispatch_or_retry_selected": False,
    "holds_preserved": "Native/UI/capture pause; local custody, UnitA, broad hosted and FieldLog compiler holds; no held-group probes.",
    "excluded": ["Other active lanes", "FieldLog app source and raw evidence", "3016-file214547334-byte raw CI review", ".wrangler", ".codex", *PROTECTED],
}
save("selection.json", selection)

metadata_paths = ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]
before = [row(ROOT / path) for path in metadata_paths]
w, g = read(ROOT / "work-graph.json"), read(ROOT / "gates/ga.json")
assert w["packages"][13]["identityProductionNetworkCI"] == g["gates"][21]["identityProductionNetworkCI"]
assert w["packages"][7]["empiricalCacheDeadlineCampaign"] == g["gates"][1]["empiricalCacheDeadlineCampaign"]
network = w["packages"][13]["identityProductionNetworkCI"]
network["positive_timestamp_source_selection"] = {"selection": row(OUT / "selection.json"), "producer_controls": 129, "independent_controls": 6, "remote_execution_selected": True, "actual_corrected_methods_passed": None, "runtime_or_GA_accepted": False}
network["latest_actual_8888_result"].update({"review_seal_pending": False, "review_availability": "raw packet retained local-only; sanitized published summary", "review": row(OUT / "prior-ci-observation.json"), "source_correction": "Independently accepted preparedmtime1 correction selected for fresh ordinary isolated CI; actual corrected runtime pending."})
network["current_Swift_host_CI"] = {"revision": prior["source_revision"], "run": 40766689541, "job": 123092607807, "status": "source-pair5 host admission and generated-consumer cross-compilation accepted", "observed": source_pair["observed"], "review": row(OUT / "prior-ci-observation.json"), "native_runtime_or_GA_accepted": False}
network["current_Engine_CI"] = {"revision": prior["source_revision"], "run": 40766689541, "status": "failure", "passed_jobs": 5, "failed_jobs": 1, "first_failure": cache["first_failure"], "cleanup": cache["cleanup"], "review": row(OUT / "prior-ci-observation.json"), "cause_inferred": False}
network["current_Phoenix_CI"] = {"revision": prior["source_revision"], "run": 40766689598, **secondary["observed_scope"]["phoenix"], "review": row(OUT / "prior-ci-observation.json"), "GA_accepted": False}
g["gates"][21]["identityProductionNetworkCI"] = copy.deepcopy(network)
campaign = w["packages"][7]["empiricalCacheDeadlineCampaign"]
campaign["architecture_comparison"].update({"status": "manual run in progress at saved21:05UTC observation; actual full results unknown", "saved_observation": row(OUT / "architecture-saved-observation.json"), "actual_full_attempts": None, "actual_full_attempt_count_observed": False, "compiled_or_runtime_acceptance": False})
g["gates"][1]["empiricalCacheDeadlineCampaign"] = copy.deepcopy(campaign)
flow = w["packages"][16]["activePublicSDKFlow"]
flow["current_public_fields_result"] = {"observation": row(OUT / "fieldlog-public-fields-observation.json"), "run": 40765792113, "app_revision": fieldlog["appRevision"], "status": "480s swift-test command timeout after pinned SDK resolution; no observed Buildcomplete or test start", "expected_tests": 38, "tests_started_observed": 0, "tests_passed_observed": 0, "tests_failed": None, "all16_remote_command_groups_cleanup_verified": True, "remote_SIGTERM_count": 1, "post_test_consumed_SDK_and_after_lock": "unreached", "next": "Same-pin phase-split diagnostic under preparation; not selected or pushed; no timeout increase or sparse fix inferred", "native_or_published_package_or_GA_accepted": False}
flow["current_public_fields_delivery"]["historical_observation"] = True
w["fieldlogRepository"]["remoteDelivery"].update({"hostTestsExecuted": None, "observedTestStarts": 0, "failedHostTests": None, "state": flow["current_public_fields_result"]["status"], "sanitizedStatusReceipt": row(OUT / "fieldlog-public-fields-observation.json")})
assert [sum(item["status"] == state for item in g["gates"]) for state in ("running", "planned", "verified")] == [8, 30, 0]
paragraph = "Current delivery addendum: the minimal positive prepared-archive timestamp correction is independently accepted for fresh isolated CI after 129 producer and six independent pure controls; all 126 original test bodies, 1,232 payload entries and 177 product files remain unchanged. Mix 1.20.4 treats a missing target as time zero, so epoch-zero inputs omitted 97 of JOSE's 113 Erlang modules. The prior exact `8888d8e2` network run `40766689512` passed the 895-byte Rebar capture but failed both product methods with `:jose_jwk` unavailable; all three container cleanups passed. Corrected compilation and both product methods remain pending. Source-pair5 now has actual host evidence: 132 Swift Testing SDK tests plus eight XCTest tests, 69 update tests, 31 CLI tests and 30 Python CLI tests passed, including ten source-pair methods. Negative cases use actual rendered children; the positive tool-order sentinel is in process and proves no Android child build. The generated consumer passed four host tests and an iOS simulator-target cross-build with no simulator boot. Engine run `40766689541` still failed the 60-second `context_schema_scalar_reserved_and_lengths` cache-fixture test; five other jobs passed and cleanup completed. Phoenix run `40766689598` passed 697 tests with two skips plus 45 protocol, 24 storage and one migration checks. Architecture run `40768719255` at `dfd0e319` was in progress at the saved 21:05 UTC observation after pure controls and compiler installation; actual full results remain unknown, with two maximum attempts and no retry. FieldLog public `4d17c926` run `40765792113` timed out its `swift-test` command at 480 seconds after pinned SDK resolution, with no observed build completion or test start; failure count is unavailable, all 16 remote groups closed and one SIGTERM was used. Post-test SDK and lock checks were unreached. Its same-pin phase-split diagnostic is under preparation and has not been selected or pushed. The large raw CI review stays local; [published summaries and timestamp selection](verification/github-delivery-positive-timestamp/selection.json) bind its metadata and hashes. Native/UI/capture, disconnected-phone and all local custody/UnitA holds remain; gates stay 8 running, 30 planned, 0 verified."
for name in ("PLAN.md", "STATUS.md"):
    path = ROOT / name
    text = path.read_text()
    start = text.index("Current delivery addendum:")
    end = text.index("\n\n", start)
    path.write_text(text[:start] + paragraph + text[end:])
for name, data in (("work-graph.json", w), ("gates/ga.json", g)):
    (ROOT / name).write_text(json.dumps(data, indent=2) + "\n")
save("metadata-checkpoint.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "before": before, "after": [row(ROOT / path) for path in metadata_paths], "mirrors_verified": True, "gate_counts": {"running": 8, "planned": 30, "verified": 0}, "runtime_or_GA_promoted": False})
print(json.dumps({"selection": "ready", "producer_files": len(producer_members), "independent_sealed_members": len(manifest["files"]), "readset_members_rehashed": len(readset["files"]), "gate_counts": [8, 30, 0]}))
