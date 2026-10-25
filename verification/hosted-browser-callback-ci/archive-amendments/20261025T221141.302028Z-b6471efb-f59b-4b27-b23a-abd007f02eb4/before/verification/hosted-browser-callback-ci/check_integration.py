#!/usr/bin/env python3
"""Static syntax/workflow integration evidence; no product or Linux CI execution."""
import ast
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
FILES = ("hosted/test/mixer_hosted/browser_auth/run_callback_fixture.py",
         "verification/hosted-browser-callback-ci/check_runner.py",
         "verification/hosted-browser-callback-ci/check_integration.py",
         ".github/workflows/hosted.yml", "docs/hosted-browser-callback-ci.md",
         "verification/hosted-browser-callback-ci/selected-methods.json")


def main():
    import hashlib
    def manifest():
        return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}
    before = manifest()
    commands, checks = [], []
    def run(label, argv):
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=15)
        commands.append({"label": label, "argv": argv, "cwd": str(ROOT), "exit": result.returncode,
                         "timeout_seconds": 15, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            raise RuntimeError(label + " failed")
        return result.stdout
    revision = run("revision", ["git", "rev-parse", "HEAD"]).strip()
    git_tree = run("git-tree", ["git", "rev-parse", "HEAD^{tree}"]).strip()
    run("ruby-version", ["ruby", "--version"])
    for name in FILES[:3]:
        ast.parse((ROOT / name).read_text(), filename=name)
        checks.append({"name": "Python AST " + name, "passed": True})
    ruby = "require 'yaml'; require 'json'; puts JSON.generate(YAML.load_file('.github/workflows/hosted.yml'))"
    workflow = json.loads(run("workflow-parse", ["ruby", "-e", ruby]))
    for event in ("push", "pull_request"):
        paths = workflow["true"][event]["paths"]
        for path in ("hosted/**", "verification/hosted-browser-callback-ci/selected-methods.json",
                     "verification/hosted-browser-callback-storage/*.exs",
                     "verification/hosted-browser-preauth-store/live.exs",
                     "verification/hosted-browser-begin-login/*.exs"):
            assert path in paths, (event, path)
    checks.append({"name": "Both triggers select the hosted runner and selected fixture inputs", "passed": True})
    steps = workflow["jobs"]["phoenix"]["steps"]
    names = [step.get("name") for step in steps]
    for name in ("Compile workspace client for real HTTP integration",
                 "Browser session storage and migration checks",
                 "Phoenix and disposable PostgreSQL host checks"):
        assert name in names
    index = names.index("Selected browser callback, preauth and begin checks")
    assert names.index("Browser session storage and migration checks") < index
    assert index < names.index("Phoenix and disposable PostgreSQL host checks")
    assert "--pg-bin /usr/lib/postgresql/16/bin" in steps[index]["run"]
    assert "${{ runner.temp }}/browser-callback/" in steps[-1]["with"]["path"]
    assert workflow["jobs"]["phoenix"]["timeout-minutes"] == 15
    checks.append({"name": "Existing checks retained with selected PG16 step and evidence artifact", "passed": True})
    run("workflow-diff-check", ["git", "diff", "--check", "--", ".github/workflows/hosted.yml"])
    checks.append({"name": "Workflow whitespace check", "passed": True})
    after = manifest()
    assert before == after
    receipt = {"schema": 1, "scope": __doc__, "invocation": [sys.executable, *sys.argv],
               "python": sys.version, "revision": revision, "git_tree": git_tree,
               "sources": before, "sources_after": after, "commands": commands,
               "checks": checks, "success": True}
    (BASE / "integration-checks.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"success": True, "checks": len(checks)}))


if __name__ == "__main__":
    main()
