"""Build an isolated inline proposal from exact frozen bytes; no compiler/import."""
from pathlib import Path
import difflib
import hashlib
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / "verification/swift-guarded-snapshot-scoped-binding-source"
PROFILE = "src/experimental_swift_reactor/cache/initial_profile_v1.rs"
BASE_TREE = "69068367d2eaf334d6881a624cac9142a0b4ecfeed50f23382724ae29e51d5e7"
BASE_PROFILE = "23c2c169f993795ed7b89a5d4b4cf50946505007868347bff83d41a609e1d617"
BASE_SEAL = "84a9bf52a127f5fcebd5d6db3dedb9c0e65fc9ef9cfd57b432c8e1f65f8e5ed2"
ROOT_RELEASE = "verification/swift-semantic-adapter-root-review/guarded-snapshot-scoped-binding-source-frozen-release.json"
ROOT_RELEASE_SHA = "bcf7c5bc242f5d12ee404d9234ee5de88abf8ed07b8cfe8e7cbe69cd8200a8ae"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def describe():
    seal_bytes = (FROZEN / "seal.json").read_bytes()
    assert sha(seal_bytes) == BASE_SEAL
    seal = json.loads(seal_bytes)
    assert seal["member_count"] == len(seal["members"]) == 200
    for item in seal["members"]:
        data = (FROZEN / item["path"]).read_bytes()
        assert (len(data), sha(data)) == (item["bytes"], item["sha256"]), item["path"]
    release_bytes = (ROOT / ROOT_RELEASE).read_bytes()
    assert sha(release_bytes) == ROOT_RELEASE_SHA
    release = json.loads(release_bytes)
    assert release["accepted"] is False and release["independent_review_required"] is True
    manifest = json.loads((FROZEN / "source-manifest.json").read_bytes())
    assert manifest["member_count"] == len(manifest["members"]) == 146
    assert manifest["tree_sha256"] == sha(canonical(manifest["members"])) == BASE_TREE
    old = (FROZEN / "source/vm" / PROFILE).read_bytes()
    assert sha(old) == BASE_PROFILE and old.endswith(b"}\n}\n")
    fragment = (HERE / "existing-owner-candidate.inc.rs").read_bytes()
    marker = b"\n// Isolated unqualified existing-owner preparation proposal.\n"
    inserted = marker + fragment + b"\n"
    proposed = old[:-4] + inserted + old[-4:]
    assert proposed.replace(inserted, b"", 1) == old
    rows, custody = [], []
    for item in manifest["members"]:
        data = (FROZEN / "source/vm" / item["path"]).read_bytes()
        assert (len(data), sha(data)) == (item["bytes"], item["sha256"])
        changed = item["path"] == PROFILE
        origin = HERE / "proposed-overlay/vm" / PROFILE if changed else FROZEN / "source/vm" / item["path"]
        current = proposed if changed else data
        row = dict(path=item["path"], bytes=len(current), sha256=sha(current))
        rows.append(row)
        custody.append(row | dict(origin=origin.relative_to(ROOT).as_posix()))
    tree = sha(canonical(rows))
    return proposed, old, dict(schema=1, member_count=146, members=rows, tree_sha256=tree), custody, dict(
        schema=1, status="source-proposal-only-conditional-unaccepted-lifetime-base",
        base_seal_sha256=BASE_SEAL, root_frozen_release_sha256=ROOT_RELEASE_SHA,
        base_source146_tree=BASE_TREE, base_profile_sha256=BASE_PROFILE,
        proposed_source146_tree=tree, unchanged_source_members=145, changed_source_members=[PROFILE],
        input_fragment_sha256=sha(fragment), inline_append_only=True, exact_old_bytes_preserved=True,
        frozen_base_root_acceptance=False, compiler_invocations=0, Rust_tests_run=0,
        original_three_selectors_unchanged="Pending", authenticated_owner_interface="unresolved",
        upstream_acquisition_funding="pending-before-acquisition", complete_diagnostic_backing="pending",
        provider_pricing_or_layout_review=False, actual_provider_or_loader_execution=False,
        operational_grant=False, native_or_FieldLog_or_OTA_or_GA=False)


def main():
    assert not (HERE / "seal.json").exists(), "sealed packet is immutable"
    proposed, old, manifest, custody, contract = describe()
    target = HERE / "proposed-overlay/vm" / PROFILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(proposed)
    write("proposed-source-manifest.json", manifest)
    write("proposed-source-custody.json", custody)
    write("source-contract.json", contract)
    (HERE / "source-proposal.patch").write_text("".join(difflib.unified_diff(
        old.decode().splitlines(True), proposed.decode().splitlines(True),
        fromfile="frozen-scoped146/vm/" + PROFILE, tofile="unqualified-provider146/vm/" + PROFILE)))
    print(json.dumps({k: contract[k] for k in ("status", "proposed_source146_tree", "compiler_invocations", "operational_grant")}))


if __name__ == "__main__":
    main()
