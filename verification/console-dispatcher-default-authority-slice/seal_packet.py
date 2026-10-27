#!/opt/homebrew/opt/python@3.14/bin/python3.14
"""Seal the reviewed terminal packet using file reads only; no runtime replay."""
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (PACKET / "freeze.json").exists() or (PACKET / "terminal-audit.json").exists():
        raise SystemExit("refusing to replace retained terminal audit or seal")
    module_spec = importlib.util.spec_from_file_location("dispatcher_terminal_audit", PACKET / "verify_terminal.py")
    audit_module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(audit_module)
    observed = io.StringIO()
    with contextlib.redirect_stdout(observed):
        audit_module.main()
    audit = json.loads(observed.getvalue())
    assert audit["status"] == "passed-offline-terminal-audit" and audit["actual_runtime_replayed"] is False
    context = json.loads((PACKET / "candidate-6/execution-plan.json").read_text())
    terminal_audit = {
        "status": "passed-offline-terminal-audit",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "argv": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", str(Path(__file__).relative_to(ROOT))],
        "python_version": sys.version,
        "audit_source_sha256": sha(PACKET / "verify_terminal.py"),
        "source_revision": context["source_revision"],
        "result": audit,
        "scope": "File/hash/count/receipt observations only; no subprocess, compiler, DB, network, native or test replay"
    }
    with (PACKET / "terminal-audit.json").open("x") as output:
        json.dump(terminal_audit, output, indent=2)
        output.write("\n")
    files = [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path)}
             for path in sorted(PACKET.rglob("*")) if path.is_file() and path.name != "freeze.json"]
    freeze = {
        "schema": 1,
        "status": "producer-terminal-verified-awaiting-independent-root-acceptance",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": context["source_revision"],
        "source_tree": context["source_tree"],
        "accepted_producer_candidate": "candidate-6",
        "execution_plan_sha256": sha(PACKET / "candidate-6/execution-plan.json"),
        "terminal_receipt_sha256": sha(PACKET / "candidate-6/execution/receipt.json"),
        "terminal_audit_sha256": sha(PACKET / "terminal-audit.json"),
        "methods": {"total": 7, "passed": 7, "failures": 0, "skipped": 0, "excluded": 0},
        "compilation": {"ordinary_modules": 39, "test_modules": 3, "warnings": 0},
        "scope": "Actual fixed ordinary default-verifier/default-Repo local host dispatcher qualification only; synthetic local TLS/JWKS identity, PostgreSQL17.11 disposable database, explicit normal fixture-owner lifecycle",
        "limits": "No production provider/startup/supervision/custody, browser/session/cookie/HTTP, PG16 CI, Neon/Cloudflare, race/commit-fault, native/device/customer/FieldLog/G22/GA acceptance",
        "retained_candidates": {"1": "unexecuted-source-review-superseded", "2": "failed-migration-pool-setup", "3": "failed-table-count-setup", "4": "failed-Admission-teardown-after-seven-method-bodies", "5": "unexecuted-source-review-superseded", "6": "passed-terminal"},
        "files": files,
        "tree_sha256": hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    }
    with (PACKET / "freeze.json").open("x") as output:
        json.dump(freeze, output, indent=2)
        output.write("\n")
    print(json.dumps({"status": freeze["status"], "files": len(files), "bytes": sum(item["bytes"] for item in files),
                      "tree_sha256": freeze["tree_sha256"], "freeze_sha256": sha(PACKET / "freeze.json"),
                      "terminal_receipt_sha256": freeze["terminal_receipt_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
