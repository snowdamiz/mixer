#!/usr/bin/env python3
"""Bounded ordinary-source/design consistency evidence; never runtime qualification."""

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE_REVISION = "c0334a9958df1f1d973310bbbdfc1ac8ec8912f9"
SOURCES = [
    "AGENTS.md",
    "mixer-product-plan.md",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/identity/bounded_json.ex",
    "hosted/lib/mixer_hosted/authorization.ex",
    "hosted/lib/mixer_hosted/authorization/policy.ex",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/evidence.ex",
    "hosted/lib/mixer_hosted/authorization/transaction/context.ex",
    "hosted/lib/mixer_hosted/authorization/transaction/snapshot.ex",
    "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs",
    "hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs",
    "hosted/priv/repo/migrations/20261025000005_add_customer_artifact_storage.exs",
    "hosted/lib/mixer_hosted_web/router.ex",
    "hosted/lib/mixer_hosted_web/customer_artifact_controller.ex",
    "hosted/lib/mixer_hosted_web/plugs/customer_artifact_request.ex",
    "hosted/lib/mixer_hosted_web/plugs/bearer_identity.ex",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    # The fixed allowlist is intentional. No recursive discovery, imports of
    # product code, compilation, services, native processes or shared harness.
    selected = {name: (ROOT / name).read_bytes() for name in SOURCES}
    text = {name: value.decode("utf-8") for name, value in selected.items()}
    contract = json.loads((OUT / "contract.json").read_text())
    doc = (ROOT / "docs/hosted-customer-workspace-contract.md").read_text()
    migration = text[SOURCES[11]]
    checks = {}

    def check(name, value):
        checks[name] = bool(value)

    roles = ["administrator", "billing_manager", "developer", "owner", "release_manager", "viewer"]
    check("six_canonical_directory_roles", contract["roles"] == roles)
    check("closed_new_scope", contract["action"] == "workspace.read" and contract["required_scope"] == "mixer.workspace.read")
    check("two_query_based_collections", {r["path"] for r in contract["routes"].values()} == {"/v3/orgs", "/v3/projects"})
    check("project_org_query_required", contract["routes"]["projects"]["required_query"] == ["organization_id"])
    check("bounded_page", contract["pagination"]["limit_default"] == 50 and contract["pagination"]["limit_max"] == 100)
    check("cursor_bound", contract["pagination"]["cursor_decoded_max_bytes"] == 1024 and contract["pagination"]["cursor_encoded_max_bytes"] == 1400)
    check("role_elevation_forbidden", contract["routes"]["organizations"]["roles_may_be_empty"] and not contract["routes"]["projects"]["roles_may_be_empty"])
    check("names_nullable_id_fallback", contract["display_name"] == {"nullable": True, "utf8_max_bytes": 256, "utf8_min_bytes": 1, "fallback": "id-only-when-null"})
    check("old_org_schema_has_no_display_name", "CREATE TABLE public.mixer_authz_organizations (\n      id text" in migration and "display_name" not in migration)
    check("old_project_schema_has_composite_key", "active boolean NOT NULL, PRIMARY KEY (organization_id, id)" in migration)
    check("binding_modes_explicit", all(s in migration for s in ("organization_only", "all_projects", "exact_project")))
    check("ordinary_scope_full_printable_id", all(s in text[SOURCES[6]] for s in ("byte_size(value) in 1..128", "String.valid?(value)", "String.printable?(value)", 'value != "*"', "not in 127..159")))
    check("ordinary_session_head_lock_order", text[SOURCES[7]].index('lock!(repo, "organization_heads"') < text[SOURCES[7]].index('lock!(repo, "project_heads"'))
    check("ordinary_identity_not_authority", "grants no membership or" in text[SOURCES[2]])
    check("ordinary_bounded_json_rejects_duplicate_keys", "Map.has_key?(result, name)" in text[SOURCES[3]])
    check("existing_force_rls", "FORCE ROW LEVEL SECURITY" in migration and "REVOKE ALL" in migration)
    check("ordinary_policy_six_roles", all(role in text[SOURCES[5]] for role in roles))
    check("plan_customer_api_and_billing_manager", "ordinary customer API authorization" in text[SOURCES[1]] and "billing manager" in text[SOURCES[1]])
    check("design_does_not_claim_runtime", "source-reviewed design, not an implemented or" in doc and "runtime-qualified API" in doc)
    check("design_selected_revoke_serialization", all(s in doc for s in ("Selected-row serialization", "After the final lock wait", "Immediately before commit", "Directory pages are weakly consistent")))
    check("design_no_new_authority_callback", "No external or\ncaller-supplied callback is accepted" in doc)
    check("design_retains_paused_native_checks", "native\nsimulator/emulator and physical-phone runs remain paused/pending" in doc)

    files = {name: {"bytes": len(data), "sha256": sha(data)} for name, data in selected.items()}
    owned = ["docs/hosted-customer-workspace-contract.md", str((OUT / "contract.json").relative_to(ROOT)), str(Path(__file__).resolve().relative_to(ROOT))]
    owned_files = {name: {"bytes": (ROOT / name).stat().st_size, "sha256": sha((ROOT / name).read_bytes())} for name in owned}
    digest = sha(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())
    receipt = {
        "schema": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "scope": "bounded ordinary-source and API-design consistency review only",
        "base_source_revision_from_root": BASE_REVISION,
        "working_source_digest": digest,
        "command": "python3 verification/hosted-customer-workspace-contract/review_sources.py",
        "tools": {"python": sys.version, "platform": platform.platform()},
        "checks": checks,
        "check_count": len(checks),
        "checks_passed": sum(checks.values()),
        "selected_ordinary_sources": files,
        "owned_design_sources": owned_files,
        "runtime_tests_executed": False,
        "services_started": [],
        "native_or_capture_processes_started": [],
        "frozen_lanes_read_imported_compiled_or_executed": False,
        "cleanup": "no scratch, service or native instance created",
        "limitations": [
            "No product implementation or runtime security qualification in this receipt.",
            "The supplied base revision is context; per-file hashes bind the observed working source bytes.",
            "Required PostgreSQL/HTTP/console tests, controlled writers, deployment and GA review remain pending.",
        ],
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    report = f"{sum(checks.values())}/{len(checks)} source/design checks passed; runtime qualification: not run.\n"
    report += f"Working ordinary-source digest: {digest}\n"
    for name, passed in checks.items():
        report += f"{'PASS' if passed else 'FAIL'} {name}\n"
    (OUT / "source-review.stdout").write_text(report)
    print(report, end="")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
