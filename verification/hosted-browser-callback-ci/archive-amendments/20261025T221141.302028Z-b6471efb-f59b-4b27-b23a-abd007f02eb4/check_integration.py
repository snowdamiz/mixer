#!/usr/bin/env python3
"""Archive packaging amendment checks; original sealed checker/receipts remain untouched."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
FILES = ("hosted/test/mixer_hosted/browser_auth/run_callback_fixture.py",
         "verification/hosted-browser-callback-ci/check_runner.py",
         "verification/hosted-browser-callback-ci/check_integration.py",
         ".github/workflows/hosted.yml", "docs/hosted-browser-callback-ci.md",
         "verification/hosted-browser-callback-ci/selected-methods.json",
         str(Path(__file__).resolve().relative_to(ROOT)))


def main():
    import hashlib
    def manifest():
        return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}
    before = manifest()
    output = BASE / "checks-attempts" / str(uuid.uuid4())
    output.mkdir(parents=True)
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
    assert "${{ runner.temp }}/browser-callback/" in steps[names.index("Preserve host evidence")]["with"]["path"]
    assert workflow["jobs"]["phoenix"]["timeout-minutes"] == 15
    checks.append({"name": "Existing checks retained with selected PG16 step and evidence artifact", "passed": True})
    run("workflow-diff-check", ["git", "diff", "--check", "--", ".github/workflows/hosted.yml"])
    checks.append({"name": "Workflow whitespace check", "passed": True})
    baseline_path = BASE / "before/.github/workflows/hosted.yml"
    baseline_code = "require 'yaml'; require 'json'; puts JSON.generate(YAML.load_file(ARGV.fetch(0)))"
    baseline = json.loads(run("workflow-before-parse", ["ruby", "-e", baseline_code, str(baseline_path)]))
    name = "Preserve callback hidden source inputs"
    expected_paths = [
        "${{ runner.temp }}/browser-callback/*/inputs/.github/workflows/hosted.yml",
        "${{ runner.temp }}/browser-callback/*/inputs/hosted/.tool-versions",
    ]
    def validate_archive_scope(candidate):
        candidate_steps = candidate["jobs"]["phoenix"]["steps"]
        matching = [step for step in candidate_steps if step.get("name") == name]
        def require(condition, reason):
            if not condition:
                raise ValueError(reason)
        require(len(matching) == 1, "exactly one dedicated callback source upload")
        dedicated = matching[0]
        require(dedicated.get("if") == "always()", "archive upload must always run")
        require(dedicated.get("uses") == "actions/upload-artifact@v4", "expected artifact action")
        options = dedicated["with"]
        require(options.get("name") == "callback-source-inputs-${{ github.sha }}", "unique callback source artifact")
        require(options.get("retention-days") == 14, "retain for fourteen days")
        require(options.get("if-no-files-found") == "error", "missing dedicated evidence must fail")
        require(options.get("include-hidden-files") is True, "explicit dedicated hidden-file inclusion")
        require(options["path"].splitlines() == expected_paths, "exact two input paths with one attempt wildcard")
        unchanged = copy.deepcopy(candidate)
        unchanged["jobs"]["phoenix"]["steps"].remove(dedicated)
        require(unchanged == baseline, "all existing workflow data including broad upload must stay unchanged")
    validate_archive_scope(workflow)
    checks.append({"name": "Dedicated always-run upload has exactly two scoped hidden inputs; existing workflow unchanged", "passed": True})
    for label, mutate in (
        ("broad callback root rejected", lambda data, step: step["with"].update(path="${{ runner.temp }}/browser-callback/\n")),
        ("recursive input wildcard rejected", lambda data, step: step["with"].update(path="${{ runner.temp }}/browser-callback/**/inputs/**\n")),
        ("third input path rejected", lambda data, step: step["with"].update(path=step["with"]["path"] + "${{ runner.temp }}/browser-callback/*/inputs/**\n")),
        ("hidden files on broad existing artifact rejected", lambda data, step: data["jobs"]["phoenix"]["steps"][names.index("Preserve host evidence")]["with"].update({"include-hidden-files": True})),
        ("ignore missing dedicated evidence rejected", lambda data, step: step["with"].update({"if-no-files-found": "ignore"})),
        ("warn missing dedicated evidence rejected", lambda data, step: step["with"].update({"if-no-files-found": "warn"})),
    ):
        changed = copy.deepcopy(workflow)
        dedicated = next(step for step in changed["jobs"]["phoenix"]["steps"] if step.get("name") == name)
        mutate(changed, dedicated)
        try:
            validate_archive_scope(changed)
        except ValueError:
            checks.append({"name": label, "passed": True})
        else:
            raise AssertionError(label)
    after = manifest()
    assert before == after
    receipt = {"schema": 1, "scope": __doc__, "invocation": [sys.executable, *sys.argv],
               "python": sys.version, "revision": revision, "git_tree": git_tree,
               "sources": before, "sources_after": after, "commands": commands,
               "checks": checks, "success": True}
    (output / "integration-checks.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(output)
    print(json.dumps({"success": True, "checks": len(checks)}))


if __name__ == "__main__":
    main()
