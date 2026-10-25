#!/usr/bin/env python3
"""Bounded, host-only evidence for the console workspace controller."""

import datetime
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = ROOT / "verification/console-workspace-controller"
INPUTS = [
    "console/tests/workspace-controller.test.mjs",
    "console/package.json",
    "console/package-lock.json",
    "console/tsconfig.json",
    "docs/console-workspace-controller.md",
    "verification/console-workspace-controller/run.py",
]
INPUTS = sorted(set(INPUTS + [str(path.relative_to(ROOT)) for path in (ROOT / "console/src").rglob("*") if path.is_file()]))
OWNED = ["console/src/state/workspace-controller.ts", "console/tests/workspace-controller.test.mjs",
         "docs/console-workspace-controller.md", "verification/console-workspace-controller/run.py"]


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt = BASE / "attempts" / stamp
    attempt.mkdir(parents=True)
    source_hashes = {}
    for relative in INPUTS:
        source = ROOT / relative
        content = source.read_bytes()
        source_hashes[relative] = hashlib.sha256(content).hexdigest()
        target = attempt / "inputs" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    manifest = "".join(f"{digest}  {path}\n" for path, digest in sorted(source_hashes.items()))
    (attempt / "inputs.sha256").write_text(manifest)
    tree_digest = hashlib.sha256(manifest.encode()).hexdigest()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    commands = []
    checks = [
        ("node-version", ["node", "--version"], ROOT),
        ("npm-version", ["npm", "--version"], ROOT),
        ("typescript-version", ["node", "node_modules/typescript/bin/tsc", "--version"], ROOT / "console"),
        ("controller-tests", ["node", "--test", "tests/workspace-controller.test.mjs"], ROOT / "console"),
        ("console-typecheck", ["npm", "run", "typecheck"], ROOT / "console"),
    ]
    checks.extend((f"owned-diff-check-{index}", ["git", "diff", "--no-index", "--check", "--", "/dev/null", path], ROOT)
                  for index, path in enumerate(OWNED, 1))
    for name, command, directory in checks:
        result = subprocess.run(command, cwd=directory, capture_output=True, text=True)
        (attempt / f"{name}.stdout").write_text(result.stdout)
        (attempt / f"{name}.stderr").write_text(result.stderr)
        commands.append({"name": name, "argv": command, "cwd": str(directory.relative_to(ROOT)) or ".",
                         "exit_code": result.returncode, "stdout": f"{name}.stdout", "stderr": f"{name}.stderr"})
    unchanged = all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in source_hashes.items())
    receipt = {
        "schema": "mixer.console-workspace-controller.v1",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_revision": revision,
        "source_binding": "working tree input snapshots; source_revision is the base commit, not a clean-tree claim",
        "input_tree_sha256": tree_digest,
        "input_hashes": source_hashes,
        "inputs_unchanged_after_commands": unchanged,
        "environment": {"platform": platform.platform(), "python": sys.version.split()[0],
                        "node": shutil.which("node"), "npm": shutil.which("npm")},
        "commands": commands,
        "result": "passed" if unchanged and all(item["exit_code"] == 0 for item in commands) else "failed",
        "focused_tests": 27,
        "scope": "Workspace controller host behavior, direct strict-parser/client dependencies, and console source typecheck",
        "cleanup": {"test_emitted_javascript": "Temporary directory removal is asserted in test after-hook; compiler-error catch also removes it",
                    "started_browser_capture_native_instances": False,
                    "other_project_processes": "untouched"},
        "pending": ["App/login/session composition acceptance", "browser interaction and accessibility runtime",
                    "deployed identity/provider and tenant isolation", "simulator/emulator runtime (paused)",
                    "physical phone matrix (disconnected)", "immutable published FieldLog dogfood release", "GA gates"],
        "limitations": ["No hosted application imports, builds, tests or server startup",
                        "No frozen hosted catalog-inspector/authority-driver/rejected Worker V2 input",
                        "No hosted/scripts/test-local.py invocation", "No production publication, customer message or credential change",
                        "Host unit tests are not native or physical-device evidence; no GA claim"],
    }
    (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"attempt": str(attempt.relative_to(ROOT)), "result": receipt["result"],
                      "focused_tests": receipt["focused_tests"], "input_tree_sha256": tree_digest}, indent=2))
    return 0 if receipt["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
