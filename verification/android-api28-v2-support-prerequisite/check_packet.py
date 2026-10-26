#!/usr/bin/env python3
"""Finite source/spec consistency only. Never runs product code or native tools."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOC = "docs/android-api28-v2-support-prerequisite.md"
ACCEPT = "verification/android-private-owner-effect-integration-root-review/candidate-5-owner-acceptance.json"
ACCEPT_SHA = "b3d45bcdb04fbb9260ad81de554d163d1ff28f71b18b4fab4a1c2cd21d8b3822"
FLOORS = {
    "high-contrast": 36, "system-contrast": 34, "font-weight": 31,
    "typed-insets": 30, "cursor-handles": 29, "state-description": 30,
    "ime-consumption": 31, "text-attribute": 33, "handwriting-replace": 34,
    "collection-of": 30, "collection-copy": 31, "typeface-weight": 28,
    "fallback-spacing": 28, "dimension-conversion": 1,
}
POLICIES = {
    "resource-catalog": "reject-any-declaration",
    "bundled-font-either-theme": "reject",
    "font-fallback-none": "no-substitution",
    "unknown-accessibility": "reject",
    "nonneutral-accessibility": "reject",
    "api28-fields-and-selection": "reject-until-implemented",
    "pre30-required-accessibility-value": "reject-until-implemented",
    "unsupported-ime-extension": "reject-before-mutation",
    "v2-rejection": "no-v1-fallback",
    "uncertain-native-effect": "terminal-with-independent-cleanup",
}
PENDING = {
    "root-selection", "independent-implementation-review", "native-compiler",
    "native-runtime-effects", "physical-phones", "TalkBack", "design-parity",
    "public-v2-routing", "published-separate-repository-FieldLog", "OTA",
    "signing-store-operations", "accountable-GA",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(raw):
    return {"bytes": len(raw), "sha256": sha(raw)}


def read_json(name):
    return json.loads((HERE / name).read_text())


def validate_contract(contract, floors):
    require(contract["schema"] == 1, "schema")
    require(contract["proposal_only"] is True, "proposal must remain source only")
    for flag in ("implementation_selected", "public_v2_enabled", "ota_authorized", "new_rendering_contexts_admitted"):
        require(contract[flag] is False, "forbidden authority: " + flag)
    require(contract["recommended_slice"] == "guarded-observations-closed-pre36-admission", "slice")
    require(contract["policies"] == POLICIES, "fail-closed policy coverage")
    require(set(contract["gates"]) == PENDING, "gate coverage")
    require(all(v == "pending" for v in contract["gates"].values()), "gate cannot pass")
    require(contract["native_or_capture_or_process_inventory_started"] is False, "runtime pause")
    rows = contract["sdk_matrix"]
    require([row["sdk"] for row in rows] == list(range(28, 37)), "finite SDK boundary coverage")
    for row in rows:
        sdk = row["sdk"]
        expected = {
            "high_contrast": "available" if sdk >= floors["high-contrast"] else "unavailable-api",
            "system_contrast": "available" if sdk >= floors["system-contrast"] else "unavailable-api",
            "font_weight": "available-preserve-undefined" if sdk >= floors["font-weight"] else "unavailable-api",
            "exact_typed_insets": "available" if sdk >= floors["typed-insets"] else "unavailable-semantics",
            "legacy_insets_equal_typed_union": False,
            "admission": "candidate-existing-checks-only" if sdk >= 36 else "reject",
            "observed_neutral_value_when_api_absent": None,
        }
        require(set(row) == {"sdk", *expected}, "matrix field closure")
        for key, value in expected.items():
            require(row[key] == value, f"SDK{sdk} incorrect {key}")
    require(contract["observer_owner_count"] == 1, "single observer ownership")
    require(contract["capture_mint_count"] == 1, "single native capture authority")
    require(contract["sdk_guards_retained"] == ["NativeEnvironmentV2.Observer", "NativeRenderer.requireV2Live"], "independent support gates")
    require(contract["commit_finish_adapter_calls_allowed"] == 0, "transaction interval")


def run(args):
    meta = read_json("source-map.json")
    source_map = meta["files"]
    require(len(source_map) == 28, "enumerated source closure")
    require(sha(json.dumps(source_map, sort_keys=True, separators=(",", ":")).encode()) == meta["source_map_sha256"], "source map digest")
    require(source_map[ACCEPT]["sha256"] == ACCEPT_SHA, "C5 acceptance anchor")
    for relative, expected in source_map.items():
        path = Path(relative)
        require(not path.is_absolute() and ".." not in path.parts, "source path confinement")
        require(identity((HERE / "inputs" / path).read_bytes()) == expected, "snapshot changed: " + relative)
        if args.live_sources:
            require(identity((ROOT / path).read_bytes()) == expected, "live source drift: " + relative)
    acceptance = json.loads((HERE / "inputs" / ACCEPT).read_text())
    require(acceptance["private_development_scope_accepted"] is True, "accepted owner scope")
    require(acceptance["public_V2_selected"] is False and acceptance["GA_qualified"] is False, "accepted owner has no public/GA authority")
    findings = read_json("official-findings.json")
    require(findings["checked_date"] == "2026-10-26", "official findings date")
    floors = {item["id"]: item["minimum_api"] for item in findings["findings"]}
    require(floors == FLOORS, "reference API floors")
    for item in findings["findings"]:
        require(item["source_class"] == "official-android-reference", "source authority")
        require(item["observed_via"] == "web-tool-search-open-find", "retrieval provenance")
        require(bool(item["finding"]), "finding text")
        for url in item["urls"]:
            parsed = urlparse(url)
            require(parsed.scheme == "https" and parsed.netloc == "developer.android.com" and parsed.path.startswith("/reference/"), "primary platform reference only")
    index = read_json("source-index.json")
    require(index["source_map_sha256"] == meta["source_map_sha256"], "source index binding")
    require(len(index["anchors"]) >= 25, "minimum concrete inventory anchors")
    for item in index["anchors"]:
        require(item["path"] in source_map, "unfrozen reference")
        lines = (HERE / "inputs" / item["path"]).read_text().splitlines()
        require(1 <= item["start"] <= item["end"] <= len(lines), "line bounds")
        snippet = "\n".join(lines[item["start"] - 1:item["end"]])
        require(snippet == item["snippet"] and item["needle"] in snippet, "source anchor changed")
    contract = read_json("contract.json")
    validate_contract(contract, floors)
    controls = []
    for name, change in (
        ("forged-pre36-neutral", lambda c: c["sdk_matrix"][7].update(high_contrast="available", observed_neutral_value_when_api_absent=False)),
        ("invented-pre30-insets-equivalence", lambda c: c["sdk_matrix"][0].update(exact_typed_insets="available", legacy_insets_equal_typed_union=True)),
        ("public-routing-authority", lambda c: c.update(public_v2_enabled=True)),
        ("release-authority", lambda c: c.update(ota_authorized=True)),
        ("gate-promotion", lambda c: c["gates"].update({"native-runtime-effects": "passed"})),
        ("font-fallback-substitution", lambda c: c["policies"].update({"font-fallback-none": "systemSans"})),
    ):
        invalid = copy.deepcopy(contract)
        change(invalid)
        try:
            validate_contract(invalid, floors)
        except ValueError:
            controls.append(name)
        else:
            raise ValueError("negative control was admitted: " + name)
    doc = (ROOT / DOC).read_text()
    for expected in (ACCEPT_SHA, meta["source_map_sha256"], "zero", "source/specification consistency", "not a live HEAD assertion", "No silent V1 fallback", "process inventories remain"):
        require(expected in doc, "document/packet inconsistency: " + expected)
    for relative in (DOC, *(str(p.relative_to(ROOT)) for p in HERE.rglob("*.py"))):
        raw = (ROOT / relative).read_bytes()
        require(raw.endswith(b"\n"), "missing final newline: " + relative)
        require(all(line.rstrip(b" \t") == line for line in raw.splitlines()), "trailing whitespace: " + relative)
    members = None
    if args.manifest:
        manifest = read_json("manifest.json")
        expected_names = {str(p.relative_to(ROOT)) for p in HERE.rglob("*") if p.is_file() and p.name != "manifest.json"}
        expected_names.add(DOC)
        require(set(manifest["files"]) == expected_names, "sealed member closure")
        for relative, expected in manifest["files"].items():
            require(relative == DOC or relative.startswith(str(HERE.relative_to(ROOT)) + "/"), "manifest path confinement")
            require(identity((ROOT / relative).read_bytes()) == expected, "sealed file changed: " + relative)
        members = len(expected_names)
    return {
        "status": "passed-source-spec-consistency-only",
        "snapshot_files": len(source_map), "source_map_sha256": meta["source_map_sha256"],
        "source_anchors": len(index["anchors"]), "official_api_findings": len(findings["findings"]),
        "sdk_rows": len(contract["sdk_matrix"]), "negative_controls_rejected": controls,
        "live_sources_checked": args.live_sources, "sealed_members_checked": members,
        "native_or_public_or_ota_qualification": False,
        "python": sys.version,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-sources", action="store_true", help="Additionally compare the enumerated live files; concurrent root metadata edits may produce honest drift.")
    parser.add_argument("--manifest", action="store_true", help="Verify exact sealed packet/document membership and digests.")
    try:
        print(json.dumps(run(parser.parse_args()), indent=2, sort_keys=True))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as failure:
        print("FAIL source/spec consistency: " + str(failure), file=sys.stderr)
        sys.exit(1)
