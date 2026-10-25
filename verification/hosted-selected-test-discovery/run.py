#!/usr/bin/env python3
"""Exercise actual Mix discovery using hosted's evaluated configuration only."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=HERE / "attempts")
args = parser.parse_args()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
out = args.output.resolve() / stamp
out.mkdir(parents=True, exist_ok=False)
selected = [
    "test/mixer_hosted/authorization/jit_policy_spec.exs",
    "test/mixer_hosted/browser_auth/migration_spec.exs",
    "test/mixer_hosted/browser_auth/storage_fixture.exs",
    "test/mixer_hosted/browser_auth/storage_spec.exs",
]
ci_log = ROOT / "verification/github-delivery-browser-lifecycle/phoenix-ci-tests.log"
source_paths = [ROOT / "hosted/mix.exs", HERE / "run.py", HERE / "mix_evidence.exs"]
source_paths += [ROOT / "hosted" / path for path in selected]
source_paths += [ROOT / "hosted/test/mixer_hosted/browser_auth" / path for path in ("run_migration_fixture.py", "run_storage_fixture.py")]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest():
    return {str(p.relative_to(ROOT)): digest(p) for p in source_paths}


before = source_manifest()
(out / "source-manifest.json").write_text(json.dumps(before, indent=2) + "\n")
receipt = {
    "schema": 1, "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_manifest_sha256": digest(out / "source-manifest.json"),
    "source_tree_sha256": hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    "commands": [], "cases": [],
    "scope": "Dependency-free temporary Mix projects execute actual Mix 1.20.4 test discovery with the evaluated hosted project discovery options and alias. No hosted application, dependencies, product tests, database, frozen lane, browser, capture, native runtime or production execution.",
    "pending": ["Exact-push Phoenix CI", "Whole Phoenix suite with its PostgreSQL 16 fixture", "Provider/customer/FieldLog/GA acceptance", "Paused browser and native runtime checks"],
}
env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
for name in ("MIX_BUILD_PATH", "MIX_DEPS_PATH", "MIX_ARCHIVES", "MIX_HOME", "MIX_PATH"):
    env.pop(name, None)
scratch = None
success = False


def run(name, argv, cwd=ROOT, check=True, timeout=30):
    argv = [str(x) for x in argv]
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate(timeout=5)
    (out / f"{name}.stdout").write_bytes(stdout)
    (out / f"{name}.stderr").write_bytes(stderr)
    receipt["commands"].append({
        "name": name, "argv": argv, "cwd": str(cwd), "environment": {"ERL_FLAGS": env["ERL_FLAGS"], "MIX_ENV": env["MIX_ENV"]},
        "timeout_seconds": timeout, "exit_code": process.returncode, "timed_out": timed_out,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
    })
    if timed_out or (check and process.returncode):
        raise RuntimeError(f"{name} failed; see retained output")
    return process.returncode, (stdout + stderr).decode(errors="replace")


ordinary = '''defmodule DiscoveryFixture.OrdinaryTest do
  use ExUnit.Case, async: false
  test "ordinary default test is discovered" do
    IO.puts("ORDINARY_TEST_EXECUTED")
    assert true
  end
end
'''


def fixture(name, config, ordinary_source=ordinary):
    path = scratch / name
    path.mkdir()
    (path / "mix.exs").write_text('''defmodule DiscoveryFixture.MixProject do
  use Mix.Project
  def project do
    [app: :discovery_fixture, version: "0.0.0", deps: []] ++ (
''' + config + ''')
  end
end
''')
    (path / "test").mkdir()
    (path / "test/test_helper.exs").write_text("ExUnit.start()\n")
    (path / "test/ordinary_test.exs").write_text(ordinary_source)
    # Each is an executable tripwire: a broad or incorrect load rule fails.
    for item in selected + ["test/extra_helper.exs", "test/support/non_test_support.exs"]:
        target = path / item
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('raise "SELECTED_OR_DEFAULT_HELPER_WAS_LOADED"\n')
    (path / "test/support/compiled_support.ex").write_text("defmodule DiscoveryFixture.CompiledSupport do\n  def present, do: true\nend\n")
    return path


def check_case(name, path, expected_exit, warnings=(), absent=(), extra_args=()):
    code, output = run(name, ["mix", "test", "--warnings-as-errors", "--seed", "0", "--no-color", *extra_args], cwd=path, check=False)
    assert code == expected_exit, (name, code, expected_exit, output)
    assert "ORDINARY_TEST_EXECUTED" in output, (name, "ordinary test was not executed")
    assert "Result: 1 passed" in output, (name, "ordinary test did not pass", output)
    assert "SELECTED_OR_DEFAULT_HELPER_WAS_LOADED" not in output, (name, "a helper was loaded")
    for item in warnings:
        assert item in output, (name, "expected diagnostic missing", item)
    for item in absent:
        assert item not in output, (name, "unexpected diagnostic", item)
    receipt["cases"].append({"name": name, "passed": True, "expected_exit": expected_exit, "actual_exit": code,
                             "required_output": list(warnings), "forbidden_output": list(absent)})


try:
    receipt["source_revision"] = run("git-head", ["git", "rev-parse", "HEAD"])[1].strip()
    run("python-version", ["python3", "--version"])
    run("elixir-version", ["elixir", "--version"])
    run("mix-version", ["mix", "--version"])
    run("mix-help-test", ["mix", "help", "test"])
    run("mix-implementation", ["elixir", HERE / "mix_evidence.exs", "implementation", out / "mix-implementation.erl"])
    run("hosted-configuration", ["elixir", HERE / "mix_evidence.exs", "configuration", ROOT / "hosted/mix.exs", out])
    fixed = (out / "fixture-config.exs").read_text()
    baseline = (out / "baseline-config.exs").read_text()
    abort = "Test suite aborted after successful execution due to warnings"
    discovery_warning = "do not match any of the configured"
    scratch = Path(tempfile.mkdtemp(prefix="mixer-selected-discovery-"))
    receipt["owned_scratch"] = str(scratch)

    check_case("baseline-four-discovery-warnings", fixture("baseline", baseline), 1, warnings=[discovery_warning, abort, *selected])
    check_case("exact-four-exclusions-and-defaults", fixture("fixed", fixed), 0, absent=["warning:", abort, *selected])

    for name, unknown in [
        ("unknown-sibling-spec-remains-fatal", "test/mixer_hosted/browser_auth/future_spec.exs"),
        ("unknown-test-typo-remains-fatal", "test/ordinary_tests.exs"),
        ("unknown-ex-file-remains-fatal", "test/mixer_hosted/browser_auth/future.ex"),
    ]:
        path = fixture(name, fixed)
        (path / unknown).write_text('raise "UNKNOWN_FILE_WAS_LOADED"\n')
        check_case(name, path, 1, warnings=[discovery_warning, abort, unknown], absent=[*selected, "UNKNOWN_FILE_WAS_LOADED"])

    path = fixture("compile-warning", fixed)
    (path / "test/load_warning_test.exs").write_text('''defmodule DiscoveryFixture.LoadWarning do
  def warning do
    unused = :warn
    :ok
  end
end
''')
    check_case("load-time-compiler-warning-remains-fatal", path, 1,
               warnings=['variable "unused" is unused', abort], absent=[discovery_warning, *selected])

    runtime = ordinary.replace('    assert true', '''    Code.compile_string("defmodule DiscoveryFixture.RuntimeRedefinition do end")
    Code.compile_string("defmodule DiscoveryFixture.RuntimeRedefinition do end")
    assert true''')
    check_case("runtime-redefinition-is-not-discovery-failure", fixture("runtime-warning", fixed, runtime), 0,
               warnings=["warning: redefining module DiscoveryFixture.RuntimeRedefinition"], absent=[discovery_warning, abort, *selected])

    path = fixture("explicit-selected", fixed)
    (path / selected[0]).write_text(ordinary)
    (path / "test/ordinary_test.exs").unlink()
    check_case("explicit-selected-file-remains-runnable", path, 0, absent=["warning:", abort], extra_args=[selected[0]])

    log = ci_log.read_text()
    assert "Result: 615 passed, 2 skipped" in log
    assert abort in log and all(item in log for item in selected)
    receipt["historical_ci"] = {
        "run_id": 40211210237, "source_revision": "7e434330cad8e3566a4a21a6d7ff996da3bc4967",
        "log": str(ci_log.relative_to(ROOT)), "log_sha256": digest(ci_log),
        "result": "615 passed, 2 skipped; exit failure after discovery warnings under --warnings-as-errors",
        "discovery_warning_paths": selected,
        "runtime_redefinition_warning_count": log.count("warning: redefining module"),
        "limitations": "A passing isolated runtime-warning control distinguishes the observed warning classes; it does not rerun or qualify the full CI suite.",
    }
    success = True
except Exception as error:
    receipt["failure"] = str(error)
finally:
    if scratch is not None:
        shutil.rmtree(scratch)
    receipt["cleanup"] = {"owned_temporary_mix_projects_removed": scratch is None or not scratch.exists(),
                           "no_database_browser_capture_or_native_process_started": True}
    receipt["source_unchanged"] = before == source_manifest()
    receipt["success"] = success and receipt["source_unchanged"] and all(receipt["cleanup"].values())
    receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"receipt": str(out / "receipt.json"), "success": receipt["success"], "cases": len(receipt["cases"]), "failure": receipt.get("failure"), "cleanup": receipt["cleanup"]}))
raise SystemExit(0 if receipt["success"] else 1)
