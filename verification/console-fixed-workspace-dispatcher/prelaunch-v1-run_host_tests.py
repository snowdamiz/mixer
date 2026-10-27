#!/opt/homebrew/opt/python@3.14/bin/python3.14
"""Bounded isolated host check. Requires root's exact execution-plan release."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PLAN_PATH = OUT / "execution-plan.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(entry):
    path = Path(entry["path"])
    path = path if path.is_absolute() else ROOT / path
    if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
        raise SystemExit("frozen execution input changed: " + entry["path"])
    return path


def main():
    plan = json.loads(PLAN_PATH.read_text())
    release_path = OUT / "host-execution-release.json"
    if not release_path.exists():
        raise SystemExit("compiler and host execution not released by root")
    release = json.loads(release_path.read_text())
    if release.get("execution_plan_sha256") != digest(PLAN_PATH) or release.get("released") is not True:
        raise SystemExit("root release does not match frozen execution plan")
    if plan.get("runner_sha256") != digest(Path(__file__)):
        raise SystemExit("runner changed since execution-plan freeze")

    for entry in plan["tool_files"]:
        verify(entry)
    sources = plan["ordinary_source_closure"] + plan["new_product_sources"]
    for entry in sources + plan["selected_test_sources"]:
        verify(entry)
    for dependency in plan["dependencies"]:
        for entry in dependency["files"]:
            verify(entry)

    started = datetime.now(timezone.utc).isoformat()
    begin = time.monotonic()
    output = bytearray()
    status = "not-started"
    exit_code = None
    scratch_path = None
    actual_argv = None
    scratch_cleaned = False
    try:
        with tempfile.TemporaryDirectory(prefix="mixer-fixed-dispatcher-") as temporary:
            scratch = Path(temporary)
            scratch_path = str(scratch)
            compile_output = scratch / "app-ebin"
            compile_output.mkdir()
            paths = []
            beam_paths = []
            dependency_versions = []
            for dependency in plan["dependencies"]:
                ebin = scratch / "deps" / dependency["name"] / "ebin"
                ebin.mkdir(parents=True)
                paths.append(str(ebin))
                dependency_versions.append((dependency["name"], dependency["version"]))
                for entry in dependency["files"]:
                    source = verify(entry)
                    target = ebin / source.name
                    shutil.copyfile(source, target)
                    if target.suffix == ".beam":
                        beam_paths.append(str(target))
            copied_sources = []
            copied_tests = []
            for entries, destinations in [(sources, copied_sources), (plan["selected_test_sources"], copied_tests)]:
                for entry in entries:
                    target = scratch / entry["path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(verify(entry), target)
                    destinations.append(str(target))
            quoted = lambda value: json.dumps(value, ensure_ascii=False)
            dep_checks = "\n".join(
                f'case Application.load(:{name}) do :ok -> :ok; {{:error, {{:already_loaded, :{name}}}}} -> :ok; _ -> raise "dependency metadata unavailable" end\n'
                f'true = to_string(Application.spec(:{name}, :vsn)) == {quoted(version)}'
                for name, version in dependency_versions
            )
            script = f'''# Generated bounded runner, containing paths and no credentials.
true = System.version() == "1.20.4"
true = System.otp_release() == "29"
IO.puts("TOOLS Elixir=" <> System.version() <> " OTP=" <> System.otp_release())
paths = {quoted(paths)}
Enum.each(paths, &Code.prepend_path/1)
false = Enum.any?(:code.get_path(), &String.contains?(to_string(&1), "_build"))
Enum.each({quoted(beam_paths)}, fn path ->
  {{:ok, {{module, _}}}} = :beam_lib.chunks(String.to_charlist(path), [:exports])
  false = String.starts_with?(Atom.to_string(module), "Elixir.MixerHosted")
end)
{dep_checks}
{{:ok, mix_state}} = Mix.State.start_link([])
true = Mix.env() == :prod
sources = {quoted(copied_sources)}
case Kernel.ParallelCompiler.compile_to_path(sources, {quoted(str(compile_output))}) do
  {{:ok, modules, []}} -> IO.puts("COMPILED " <> Integer.to_string(length(modules)) <> " ordinary/new modules")
  _ -> System.halt(2)
end
true = is_nil(Process.whereis(MixerHosted.Identity.KeyOwner))
true = is_nil(Process.whereis(MixerHosted.Repo))
:absent = :persistent_term.get({{MixerHosted.Identity.Admission, MixerHosted.Identity.KeyOwner}}, :absent)
ExUnit.start(autorun: false, seed: 0, max_cases: 1, timeout: 5_000, colors: [enabled: false])
Enum.each({quoted(copied_tests)}, &Code.require_file/1)
result = ExUnit.run()
true = is_nil(Process.whereis(MixerHosted.Identity.KeyOwner))
true = is_nil(Process.whereis(MixerHosted.Repo))
:absent = :persistent_term.get({{MixerHosted.Identity.Admission, MixerHosted.Identity.KeyOwner}}, :absent)
for app <- [:mixer_hosted, :ecto, :ecto_sql, :db_connection, :postgrex, :plug, :jose, :mint, :mix] do
  false = List.keymember?(Application.started_applications(), app, 0)
end
GenServer.stop(mix_state)
IO.puts("SCOPE component host controls only; synthetic controller positives; default verifier/default Repo 200 and all database/session/HTTP acceptance pending")
IO.puts("RESULT " <> Jason.encode!(result))
System.halt(if(result.failures == 0, do: 0, else: 1))
'''
            script_path = scratch / "run.exs"
            script_path.write_text(script)
            # Retain the exact executed bootstrap: paths only, no application data.
            (OUT / "host-bootstrap.exs.txt").write_text(script)
            actual_argv = ["/opt/homebrew/Cellar/elixir/1.20.4/bin/elixir", "--no-color", "--erl", "+S 2:2 +A 2", str(script_path)]
            env = {key: os.environ[key] for key in ("HOME", "USER", "TMPDIR") if key in os.environ}
            env.update({"PATH": "/opt/homebrew/Cellar/erlang/29.1.1_2/bin:/opt/homebrew/Cellar/elixir/1.20.4/bin:/usr/bin:/bin", "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8", "MIX_ENV": "prod", "ERL_CRASH_DUMP": "/dev/null"})
            process = subprocess.Popen(actual_argv, cwd=scratch, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            status = "running"
            deadline = time.monotonic() + plan["limits"]["wall_seconds"]
            try:
                while selector.get_map():
                    if time.monotonic() >= deadline:
                        status = "time-limit"
                        break
                    for key, _ in selector.select(timeout=min(0.1, max(0, deadline - time.monotonic()))):
                        data = os.read(key.fileobj.fileno(), 65536)
                        if not data:
                            selector.unregister(key.fileobj)
                            break
                        remaining = plan["limits"]["combined_output_bytes"] - len(output)
                        output.extend(data[:remaining])
                        if len(data) > remaining:
                            status = "output-limit"
                            break
                    if status != "running":
                        break
                if status == "running":
                    exit_code = process.wait(timeout=max(0.1, deadline - time.monotonic()))
                    status = "passed" if exit_code == 0 else "failed"
            finally:
                selector.close()
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
                exit_code = process.returncode
                process.stdout.close()
        scratch_cleaned = not Path(scratch_path).exists()
    finally:
        (OUT / "host.stdout.txt").write_bytes(output)
        receipt = {"schema": 1, "started_at": started, "status": status, "exit_code": exit_code, "elapsed_seconds": round(time.monotonic() - begin, 3), "runner_argv": plan["runner_argv"], "actual_child_argv": actual_argv, "execution_plan_sha256": digest(PLAN_PATH), "source_revision": plan["source_revision"], "source_tree": plan["source_tree"], "output_bytes": len(output), "output_sha256": hashlib.sha256(output).hexdigest(), "scratch": scratch_path, "scratch_removed": scratch_cleaned, "limits": plan["limits"], "scope": "component host tests; configured default-owner-absent negatives and labelled synthetic controller/transport positives only", "pending": plan["pending"], "no_native_capture_database_container_network_resources_started": True}
        (OUT / "host-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        sys.stdout.buffer.write(output)
        print(json.dumps({"status": status, "exit_code": exit_code, "scratch_removed": scratch_cleaned, "output_bytes": len(output)}))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
