"""Bounded stdlib-only saved-source inspection. Does not invoke Rust or tests."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

ROOT = Path("/Users/andreyyurlov/Documents/dev/mixer")
OWN = ROOT / "verification/swift-physical-source-reachability"
SOURCE = ROOT / "verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm"
MANIFEST = ROOT / "verification/swift-guarded-snapshot-root-result-lifetime-implementation/source-manifest.json"
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_METADATA_BYTES = 2 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_bounded(path, bound):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > bound:
        raise ValueError(f"unsupported input: {path.relative_to(ROOT)}")
    return path.read_bytes()


def pin(path, bound=MAX_METADATA_BYTES):
    data = read_bounded(path, bound)
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


manifest_bytes = read_bounded(MANIFEST, MAX_METADATA_BYTES)
manifest = json.loads(manifest_bytes)
if sha(manifest_bytes) != "5f20215aef11436b0a3cde511c0820450f37a613de20e74d810728bd5efa8249":
    raise ValueError("source manifest changed from the selected capture")
if manifest["member_count"] != 146 or len(manifest["members"]) != 146:
    raise ValueError("unexpected source member count")
if manifest["tree_sha256"] != "91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f":
    raise ValueError("unexpected declared source tree digest")

source_data = {}
total_source_bytes = 0
for member in manifest["members"]:
    path = Path(member["path"])
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("unsupported source path")
    data = read_bounded(SOURCE / path, MAX_SOURCE_BYTES)
    total_source_bytes += len(data)
    if total_source_bytes > MAX_SOURCE_BYTES:
        raise ValueError("source total byte bound exceeded")
    if len(data) != member["bytes"] or sha(data) != member["sha256"]:
        raise ValueError(f"source member changed: {path}")
    source_data[str(path)] = data
actual_members = sorted(str(path.relative_to(SOURCE)) for path in SOURCE.rglob("*") if path.is_file())
if actual_members != sorted(source_data):
    raise ValueError("source file roster changed")

metadata_paths = [
    "AGENTS.md",
    "verification/swift-physical-map-independent/review-result.json",
    "verification/swift-semantic-adapter-root-review/dispatch-physical-mapping-selection.json",
    "verification/swift-root-bound-dispatch-physical-plan/target-frontier.json",
    "verification/swift-root-bound-dispatch-physical-capture-v1/plan.json",
    "verification/swift-guarded-snapshot-root-result-lifetime-implementation/source-manifest.json",
]
metadata = [pin(ROOT / path) for path in metadata_paths]
plan = json.loads(read_bounded(ROOT / metadata_paths[4], MAX_METADATA_BYTES))
argv = plan["argv"]
selected_cfgs = [argv[i + 1] for i, item in enumerate(argv[:-1]) if item == "--cfg"]

needles = [
    "trusted_local_host_account_entry_v1",
    "consume_admitted_owner_once_v1",
    "run_one_admitted_fixture_v1",
    "run_prepaid_admitted_fixture_v1",
    "run_selected_one_fixture_outer_v1",
    "mixer_ir02_probe_cache_v1",
]
occurrences = {needle: [] for needle in needles}
for path, data in sorted(source_data.items()):
    if not path.endswith(".rs"):
        continue
    for line_no, line in enumerate(data.decode("utf-8").splitlines(), 1):
        for needle in needles:
            if needle in line:
                occurrences[needle].append({"path": path, "line": line_no, "text": line})

INITIAL = "src/experimental_swift_reactor/cache/initial_profile_v1.rs"
HOST = "src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs"
LOADER = "src/experimental_swift_reactor/retained_profile_loader_v1.rs"
anchor_specs = [
    ("reactor_feature", "src/lib.rs", 12, 15),
    ("private_cache", "src/experimental_swift_reactor/mod.rs", 5, 11),
    ("private_initial_profile", "src/experimental_swift_reactor/cache.rs", 4851, 4859),
    ("other_host_cfgs", INITIAL, 125, 129),
    ("layout_export_disabled_cfg", INITIAL, 585, 587),
    ("trusted_module_cfg", INITIAL, 690, 714),
    ("exact_caller_closure_body", INITIAL, 843, 889),
    ("test_and_probe_roots_not_selected", INITIAL, 891, 904),
    ("private_outer_module", INITIAL, 919, 930),
    ("request_selector", INITIAL, 975, 989),
    ("private_admitted_outer_caller", INITIAL, 1175, 1206),
    ("retirement_and_test_cfg", INITIAL, 1217, 1227),
    ("pending_quote_and_account", HOST, 70, 85),
    ("generic_dispatch", HOST, 126, 147),
    ("bootstrap_policy_pending", LOADER, 1456, 1465),
    ("native_startup_pending", LOADER, 1777, 1787),
    ("admission_always_refuses", LOADER, 1938, 1952),
]
anchors = []
for label, path, begin, end in anchor_specs:
    data = source_data[path]
    lines = data.splitlines(keepends=True)
    span = b"".join(lines[begin - 1:end])
    anchors.append({"id": label, "path": str((SOURCE / path).relative_to(ROOT)),
                    "line_begin": begin, "line_end_inclusive": end,
                    "file_sha256": sha(data), "span_sha256": sha(span),
                    "text": span.decode("utf-8")})

# Confirm the already-pinned source bytes again after inspection. No source is written.
for member in manifest["members"]:
    data = read_bounded(SOURCE / member["path"], MAX_SOURCE_BYTES)
    if len(data) != member["bytes"] or sha(data) != member["sha256"]:
        raise ValueError("source changed during inspection")

result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "SOURCE_ONLY_NO_SELECTED_ROOT_AND_REFUSAL_BLOCKS_EXACT_ACTION_PATH",
    "command": [str(Path(sys.executable)), "-B", str(OWN / "inspect_saved_source.py")],
    "tool_version": {"queried": False, "saved_capture_plan_label_only": plan["python_version_from_this_preparation"]},
    "script_sha256": sha(Path(__file__).read_bytes()),
    "scope": "Bounded stdlib/text read of exact source146 manifest and six saved metadata files; no Rust parsing/type/codegen proof.",
    "source": {"manifest": pin(MANIFEST), "declared_tree_sha256": manifest["tree_sha256"],
               "all_146_member_hashes_checked_before_and_after": True,
               "exact_file_roster_checked": True, "total_bytes": total_source_bytes,
               "aggregate_tree_hash_algorithm_not_reimplemented": True},
    "metadata": metadata,
    "selected_cfgs": selected_cfgs,
    "selected_argv": argv,
    "source_spelling_occurrences": occurrences,
    "anchors": anchors,
    "findings": [
        {"id": "cfg", "kind": "source_fact", "finding": "Selected reactor feature and mixer_bootstrap_one_fixture_v1 include all four target source definitions. test, mixer_ir02_probe_cache_v1, mixer_snapshot_encoder_host, mixer_initial_profile_component_host and mixer_snapshot_composition_layout are not selected in argv. Cargo binaries/integration tests are not the crate root of the direct lib.rs rlib command."},
        {"id": "roots", "kind": "bounded_source_fact", "finding": "The target family has private enclosing modules and no exported/used/static reference root. Caller incoming spellings are its cfg(test) helper and the private admitted outer function. The latter has only its definition across all source146 Rust members. Body has only its definition and the exact861 closure invocation. This is a textual source reference census, not proof about arbitrary compiler representations."},
        {"id": "refusal", "kind": "source_semantics", "finding": "Every normal invocation of the unchanged Caller returns selected_whole_quote_v1 Err(WholeQuotePending) before reservation/closure invocation. A hypothetical direct call to Caller cannot execute Closure/Dispatch/Body under these selector bodies. The private admitted outer additionally cannot pass selected_parent_account_v1; actual owner acquisition/admission/root selection also remain pending in separate source."},
        {"id": "instantiation", "kind": "source_fact_and_limited_inference", "finding": "Dispatch is generic over output T and the impl FnOnce closure type. The only exact target instantiation expression is line861. It exists for source/type/MIR purposes but no selected source root demands it and the action path is semantically refused. Source inspection cannot certify native monomorphization or attribute the capture nonidentification to DCE, linkage, cfg, renaming or toolchain behavior."},
        {"id": "feasibility", "kind": "design_assessment", "finding": "The current unchanged-source rlib contract does not supply a source execution/root contract for four native targets. Repeating its capture has no source-bound reason to resolve this. Full exact-chain executable geometry needs a separately selected source/build contract; lookalike closure/dispatch wrappers create different identities, and bypassing the quote or inventing admitted owners changes behavior."}
    ],
    "options": [
        {"id": "preserve", "source_edits": False, "description": "Keep the frozen incomplete capture as the result for this exact build. Record that actual selected normal behavior remains refusal; continue unrelated implementation/source work without geometry or capacity claims."},
        {"id": "retention_only_experiment", "source_edits": "separate future selection only", "description": "If geometry of dormant original bodies is independently useful, first choose an explicit retention/instantiation experiment with official compiler support and bind its changed build/source. Preserve the original function bodies and exact861 closure; do not promise that exporting only Caller forces all four bodies. A new closure expression is a different closure. Retained counterfactual bodies would qualify only that experiment, not operational admitted execution or this saved capture."},
        {"id": "actual_path", "source_edits": "separate future selected implementation", "description": "For actual admitted-route geometry, implement the real private root/startup/custody/account/whole-quote contract with authentic immutable inputs, preserve original typed owners and post-destruction charge rules, then map the resulting build. Prices currently depend on pending geometry and ownership evidence, so this is not a one-line export or safe fixed-budget shortcut. A narrowly selected retention experiment can break the evidence dependency without asserting execution, funding or capacity."}
    ],
    "not_executed": ["compiler", "rustfmt", "version query", "native/UI/capture", "test", "model", "geometry verifier", "raw artifact recapture", "global process probe"],
    "source_flag_or_wrapper_changes": 0,
    "canonical_or_frozen_packet_writes": 0,
    "actual_geometry_capacity_or_GA_accepted": False,
    "capture_cause_proved": False,
    "automatic_recapture_authorized": False,
}
OWN.mkdir(exist_ok=True)
(OWN / "inspection.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": result["status"], "source_members_checked": 146,
                  "source_total_bytes": total_source_bytes, "source_unchanged": True,
                  "output": str(OWN / "inspection.json"), "compiler_actions": 0,
                  "geometry_or_capacity_accepted": False}, sort_keys=True))
