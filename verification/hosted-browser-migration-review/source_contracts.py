#!/usr/bin/env python3
"""Bounded fixture diff and CI source review; real SQL coverage is separate."""
import ast
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = "1257cbf83f973d3ad05a3a279f94007476f7ce2b"
checks = []

def check(name, condition):
    assert condition, name
    checks.append(name)

def old(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True)

for path in ["hosted/test/foundation_integration_test.exs", "hosted/test/mixer_hosted/builds/storage_test.exs"]:
    before = old(path)
    after = (ROOT / path).read_text()
    check(path + " exact latest version only", after == before.replace("             20_261_025_000_006\n", "             20_261_025_000_006,\n             20_261_025_000_007\n"))
for name in ["admission", "coordinator", "aggregate_admission"]:
    path = f"hosted/test/mixer_hosted/builds/{name}_test.exs"
    expected = old(path).replace("assert length(Ecto.Migrator.run(Repo, path, :up, all: true)) == 8", "assert length(Ecto.Migrator.run(Repo, path, :up, all: true)) == 9")
    if name == "aggregate_admission":
        expected = expected.replace("    assert [\n             20_261_025_000_006,", "    assert [\n             20_261_025_000_007,\n             20_261_025_000_006,")
        expected = expected.replace("] = Ecto.Migrator.run(Repo, path, :down, step: 5)", "] = Ecto.Migrator.run(Repo, path, :down, step: 6)")
        expected = expected.replace("             20_261_025_000_006\n", "             20_261_025_000_006,\n             20_261_025_000_007\n")
    check(path + " bounded migration expectation diff", (ROOT / path).read_text() == expected)
workflow = (ROOT / ".github/workflows/hosted.yml").read_text()
block = workflow.split("      - name: Browser session storage and migration checks\n", 1)[1].split("      - name:", 1)[0]
check("selected CI step compiles dependencies without compiling application", "mix deps.compile\n" in block and "mix compile" not in block)
check("both selected fixtures use PostgreSQL 16", block.count("--pg-bin /usr/lib/postgresql/16/bin") == 2)
check("closed selected runner paths", "python3 test/mixer_hosted/browser_auth/run_storage_fixture.py" in block and "python3 test/mixer_hosted/browser_auth/run_migration_fixture.py" in block)
check("CI migration evidence output retained", '--output "$RUNNER_TEMP/browser-migrations"' in block and "${{ runner.temp }}/browser-migrations/" in workflow)
check("CI storage evidence retained", "verification/hosted-browser-session-storage/attempts/" in workflow)
check("specs remain outside default ExUnit discovery", not any(p.name.endswith("_test.exs") for p in [ROOT / "hosted/test/mixer_hosted/browser_auth/storage_spec.exs", ROOT / "hosted/test/mixer_hosted/browser_auth/migration_spec.exs"]))
for name in ["run_migration_fixture.py", "run_storage_fixture.py"]:
    path = ROOT / "hosted/test/mixer_hosted/browser_auth" / name
    ast.parse(path.read_text(), filename=str(path))
    checks.append(name + " Python syntax")
print(json.dumps({"status": "passed", "checks": checks, "count": len(checks)}, indent=2))
