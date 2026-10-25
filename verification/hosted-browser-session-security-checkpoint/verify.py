#!/usr/bin/env python3
"""Verify only the ordinary browser security slice's retained source/output bindings."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RECEIPTS = [
    "verification/hosted-browser-configuration-digest/receipt.json",
    "verification/hosted-browser-session-vault/receipt.json",
    "verification/browser-vault-digest-review/receipt.json",
    "verification/hosted-browser-stored-snapshot/receipt.json",
    "verification/hosted-browser-stored-snapshot-review/receipt.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inputs, outputs, receipts = {}, {}, {}
    for name in RECEIPTS:
        path = ROOT / name
        receipt = json.loads(path.read_text())
        assert receipt["status"] == "passed", name
        receipts[name] = sha(path)
        manifest = json.loads((ROOT / receipt["source_inputs"]).read_text())
        for source, digest in manifest["files"].items():
            path = ROOT / source
            if source == "hosted/lib/mixer_hosted/browser_auth/storage_schema.ex":
                # The SQL candidate is intentionally not installed in this commit.
                # Preserve the exact shape-review input as a recovery-only copy.
                archived = ROOT / "verification/implementation-pause-2026-10-25/pending-storage-source" / source
                assert sha(archived) == digest, source
                if not path.exists():
                    path = archived
            assert sha(path) == digest, source
            assert source not in inputs or inputs[source] == digest, source
            inputs[source] = digest
        for command in receipt["commands"]:
            assert command["exit_code"] == 0, command
            for stream in ["stdout", "stderr"]:
                file = command[stream]
                digest = sha(ROOT / file)
                if stream + "_sha256" in command:
                    assert digest == command[stream + "_sha256"], file
                outputs[file] = digest
        for file, digest in receipt.get("outputs", {}).items():
            assert sha(ROOT / file) == digest, file
            outputs[file] = digest
        assert receipt["cleanup"]["owned_scratch_removed"] is True
        assert not Path(receipt["cleanup"]["owned_scratch_path"]).exists()
        report = receipt.get("review_report")
        if report:
            assert sha(ROOT / report) == receipt["review_report_sha256"]

    commands = []
    for name, argv, cwd in [
        ("brand-parity", ["node", "--test", "tests/brand-parity.test.mjs"], ROOT / "console"),
        ("source-diff-check", ["git", "diff", "--check", "--", "PLAN.md", "STATUS.md",
          "work-graph.json", "gates/ga.json", "hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex",
          "hosted/lib/mixer_hosted/browser_auth/vault.ex", "hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex"], ROOT),
    ]:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=60)
        for stream, data in [("stdout", result.stdout), ("stderr", result.stderr)]:
            (HERE / f"{name}.{stream}").write_bytes(data)
        assert result.returncode == 0, result.stderr.decode()
        commands.append({"argv": argv, "cwd": str(cwd), "exit_code": result.returncode,
                         "stdout_sha256": sha(HERE / f"{name}.stdout"),
                         "stderr_sha256": sha(HERE / f"{name}.stderr")})

    value = {"status": "passed", "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
             "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
             "scope": "Root acceptance of reviewed configuration digest, typed AES-GCM vault and data-only snapshot decoder. No database lifecycle acceptance or live login.",
             "receipts": receipts, "current_source_bindings": inputs, "retained_output_bindings": outputs,
             "commands": commands,
             "pending": ["independent SQL lifecycle review and nine-migration CI integration",
                         "runtime owner/provenance and key custody", "provider/OIDC/current identity verifier join",
                         "actual HTTP/console login", "Phoenix transaction timeout investigation",
                         "deployment/browser/native/FieldLog/customer and GA acceptance"]}
    (HERE / "receipt.json").write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({"status": "passed", "source_bindings": len(inputs), "output_bindings": len(outputs)}))


if __name__ == "__main__":
    main()
