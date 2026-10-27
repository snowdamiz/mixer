"""Deterministic frozen custody/source mapping only; imports no old executable code."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P = "verification/swift-guarded-snapshot-owned-binding-provider/proposed-overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs"
L = "verification/swift-guarded-snapshot-host-composition/overlay/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs"
S = "verification/swift-guarded-snapshot-scoped-binding-source/source/vm/src/experimental/swift.rs"
A = "verification/swift-guarded-snapshot-scoped-binding-source/source/vm/src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs"
PACKETS = (
    ("verification/swift-guarded-snapshot-prepaid-input-owner-affine-refusal", "2270f59809b80c49df907a7ea9c20faf4dd45735cabad275ae61065efc19c50b"),
    ("verification/swift-guarded-snapshot-prepaid-affine-refusal-independent", "25eb5a5f02059ab38953f9435bef2e308e2e946290c231ebd922459e20dd679d"),
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def row(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def tree(rows):
    return sha(canonical(rows))


def frozen_inputs():
    paths = set()
    for base_name, expected in PACKETS:
        base = ROOT / base_name
        seal_path = base / "seal.json"
        assert sha(seal_path.read_bytes()) == expected
        seal = json.loads(seal_path.read_bytes())
        members = seal["members"]
        assert len(members) == seal["member_count"]
        assert sum(m["bytes"] for m in members) == seal["member_bytes"]
        assert tree(members) == seal["tree_sha256"]
        assert {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file() and p != seal_path} == {m["path"] for m in members}
        for item in members:
            path = base / item["path"]
            actual = row(path)
            assert (actual["bytes"], actual["sha256"]) == (item["bytes"], item["sha256"])
            paths.add(path)
        paths.add(seal_path)
    inherited = json.loads((ROOT / PACKETS[0][0] / "final-custody.json").read_bytes())
    assert inherited["before"] == inherited["after"] and inherited["unchanged"]
    assert len(inherited["before"]) == 479
    for item in inherited["before"]:
        path = ROOT / item["path"]
        assert row(path) == item, str(path)
        paths.add(path)
    provider = ROOT / "verification/swift-guarded-snapshot-owned-binding-provider"
    manifest_path = provider / "proposed-source-manifest.json"
    custody_path = provider / "proposed-source-custody.json"
    manifest = json.loads(manifest_path.read_bytes())
    custody = json.loads(custody_path.read_bytes())
    assert len(custody) == manifest["member_count"] == 146
    assert tree(manifest["members"]) == manifest["tree_sha256"] == "acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d"
    for expected, item in zip(manifest["members"], custody):
        assert expected == {k: item[k] for k in ("path", "bytes", "sha256")}
        path = ROOT / item["origin"]
        actual = row(path)
        assert (actual["bytes"], actual["sha256"]) == (expected["bytes"], expected["sha256"])
        paths.add(path)
    host_manifest_path = ROOT / "verification/swift-guarded-snapshot-host-composition/host-support-manifest.json"
    host = json.loads(host_manifest_path.read_bytes())
    assert len(host["members"]) == host["member_count"] == 11
    assert tree(host["members"]) == host["tree_sha256"] == "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2"
    for item in host["members"]:
        path = ROOT / "verification/swift-real-profile-loader-binding/host" / item["path"]
        actual = row(path)
        assert (actual["bytes"], actual["sha256"]) == (item["bytes"], item["sha256"])
        paths.add(path)
    paths.update([manifest_path, custody_path, host_manifest_path, ROOT / L])
    assert row(ROOT / P)["sha256"] == "d6bc88db29843ce9bb7fcc8ab541381815071b324022f9f62dee0439c2842141"
    assert row(ROOT / L)["sha256"] == "ebe88f37d2721c41371c9f726aeefaf533451cc9b6309b296053bc3b327240b9"
    return sorted((row(p) for p in paths), key=lambda item: item["path"])


def span(path, label, start, end, decision):
    raw = (ROOT / path).read_text()
    assert raw.count(start) == 1, (label, start)
    at = raw.index(start)
    stop = raw.index(end, at) + len(end)
    excerpt = raw[at:stop]
    return dict(label=label, source=row(ROOT / path), start_line=raw[:at].count("\n") + 1,
                end_line=raw[:stop].count("\n") + 1, exact_excerpt=excerpt,
                excerpt_sha256=sha(excerpt.encode()), selected_change=decision)


def source_map():
    specs = [
        (P,"setup_opens","    fn setup_files_once_v1(","    fn copy_claims_v1(","unchanged existing3 input and2 create_new output opens"),
        (P,"preleaf_insertion","        let LoaderOutcomeV1 { selected, files, usage }", "        // No diagnostic flattening", "replace direct destructure with owning typed correlation; leaf only on affine success"),
        (P,"result_carrier","    enum PrimaryOutcomeV1 {", "    fn run_one_fixture_v1", "add correlation refusal preserving selected proof and original diagnostic"),
        (P,"borrowed_binding","    struct ImmutableIdentityPreimageV1", "    enum OriginalObservationV1", "borrow actual owned backing; selected request remains Pending"),
        (P,"existing_provider","mod existing_owner_candidate_v1 {", "    pub(super) enum CandidateShapeRefusalV1", "unqualified22-backing description remains unqualified"),
        (P,"provider_borrow_check","    pub(super) fn describe_existing_owner_candidate_v1", "        use PendingUpstreamRequirementV1", "preserve12+5+5 no alias credit and original claims/budgets"),
        (P,"outer_retirement","        let original_observation = {", "        let after_retirement", "end all borrows before consuming original child and outer owner"),
        (L,"selected_and_Files","/// All actual File owners return", "#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]\nstruct FileIdentityV1", "whole LoaderOutcome with selected proof plus3+optional1 Files andusage enters carrier"),
        (L,"full_identity","struct FileIdentityV1 {", "#[derive(Clone, Copy)]\nstruct Section", "all8 fields; signed timestamp comparison preserved"),
        (L,"binary_parsers","fn parse_build(", "/// Complete every block", "unchanged production format146+11/all limits;never synthetic JSON"),
        (L,"actual_read_allocation","fn retained(", "#[cfg(target_os = \"macos\")]\nmod platform", "existing loader allocation/read/metadata semantics unchanged;new acquisition needs own pre-call allocator bound"),
        (L,"loader_full_checks","fn load_inner(", "// Metadata errors retain", "all existing process/hash/identity/validator checks unchanged"),
        (L,"executable_drop","    drop(executable);", "    let input = retained(", "preserve actual executable Vec drop before input/proof"),
        (L,"proof_overlap","    let validation = validate_swift_reactor", "    usage.source_equality_bytes", "charge live build/session/input/validator proof-source copy+metadata"),
        (L,"final_provenance","    final_metadata_recheck_v1(files, &identities)?;", "// Metadata errors retain", "all4 final same-handle rechecks precede authentic selected proof"),
        (L,"loader_return","pub(super) fn load_selected_retained_profile_v1(", "// Test-only", "complete actual outcome;local Vecs not returned"),
        (S,"proof_owned_backing","pub struct ValidatedSwiftReactor {", "    pub fn policy_identity", "Box source andmetadata retained in proof;borrow ends with owner"),
        (S,"validator_copy","    meter.reserve(Resource::Source, input.len(), cursor)?;", "    let mut metadata: SwiftMetadata", "separate Vec copy thenBox;no input/proof alias storage credit"),
        (A,"original_pending_selectors","pub(super) fn selected_whole_quote_v1()", "pub(super) struct TrustedHostAccountV1", "unchanged Pending selectors andno new root authority"),
        (A,"original_child_retirement","pub(super) struct PrepaidOwnedV1", "#[cfg(test)]", "unchanged child destroy token;new acquisition needs independent complete-retirement gate"),
    ]
    return dict(schema=1, method="exact frozen text anchors only;no release authority or compiled semantics claimed",
                source146="acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d",
                host11="027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2",
                anchors=[span(*spec) for spec in specs])


def check_seal():
    seal = json.loads((HERE / "seal.json").read_bytes())
    members = [{"path": str(p.relative_to(HERE)), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())}
               for p in sorted(HERE.rglob("*")) if p.is_file() and p.name != "seal.json"]
    assert members == seal["members"]
    assert tree(members) == seal["tree_sha256"]
    print(json.dumps(dict(seal_sha256=sha((HERE / "seal.json").read_bytes()), members=len(members), tree_sha256=tree(members)), sort_keys=True))


if __name__ == "__main__":
    if sys.argv[1:] == ["--check-seal"]:
        check_seal()
    else:
        assert sys.argv[1:] == ["--source-map"]
        before = frozen_inputs()
        selection = json.loads((HERE / "selection.json").read_bytes())
        plan = json.loads((HERE / "host-test-plan.json").read_bytes())
        assert selection["source_ownership"]["new_distribution_member_count"] == 146
        assert len(selection["private_source_changes"][3]["groups"]) == 9
        assert selection["preserved"]["policy_fields"] == 17 and selection["preserved"]["Pending_upstream"] == 6
        assert plan["minimum_proposed_budget"]["compiler_invocations"] == 11
        assert not any(selection["executed_here"].values())
        mapped = source_map()
        after = frozen_inputs()
        assert before == after
        print(json.dumps(dict(schema=1, custody_members=len(before), input_tree_sha256=tree(before),
                              before=before, after=after, unchanged=True, source_map=mapped,
                              deterministic_source_map_only=True, Rust_or_native_tests=False), sort_keys=True, indent=2))
