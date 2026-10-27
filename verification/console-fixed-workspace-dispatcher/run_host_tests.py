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
    for name in ("host.stdout.txt", "host-receipt.json", "host-bootstrap.exs.txt"):
        if (OUT / name).exists():
            raise SystemExit("refusing to overwrite retained host evidence: " + name)
    plan = json.loads(PLAN_PATH.read_text())
    release_path = OUT / "host-execution-release.json"
    if not release_path.exists():
        raise SystemExit("compiler and host execution not released by root")
    release = json.loads(release_path.read_text())
    if release.get("execution_plan_sha256") != digest(PLAN_PATH) or release.get("released") is not True:
        raise SystemExit("root release does not match frozen execution plan")
    if plan.get("runner_sha256") != digest(Path(__file__)):
        raise SystemExit("runner changed since execution-plan freeze")

    all_original_pins = plan["tool_files"] + plan["ordinary_source_closure"] + plan["new_product_sources"] + plan["selected_test_sources"]
    all_original_pins += [entry for dependency in plan["dependencies"] for entry in dependency["files"]]
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
    owned_pid = None
    owned_pgid = None
    direct_child_reaped = False
    group_checks = []
    cleanup_error = None
    child_elapsed = None
    copied_bytes_verified = 0
    original_changes = []
    runner_error = None
    child_begin = None
    process = None
    cleanup_deadline = None

    def group_exists(stage):
        try:
            os.killpg(owned_pgid, 0)
            exists = True
        except ProcessLookupError:
            exists = False
        group_checks.append({"stage": stage, "argv_equivalent": ["killpg", owned_pgid, 0], "group_exists": exists})
        return exists

    def copy_verified(entry, target):
        nonlocal copied_bytes_verified
        shutil.copyfile(verify(entry), target)
        if target.stat().st_size != entry["bytes"] or digest(target) != entry["sha256"]:
            raise RuntimeError("copied execution input mismatch")
        copied_bytes_verified += 1

    def cleanup_owned():
        nonlocal cleanup_deadline, direct_child_reaped, exit_code, cleanup_error, child_elapsed
        if process is None or direct_child_reaped:
            return
        if cleanup_deadline is None:
            cleanup_deadline = min(time.monotonic() + plan["limits"]["owned_cleanup_seconds"], child_begin + plan["limits"]["total_child_seconds"])
        try:
            if group_exists("before-owned-cleanup"):
                try:
                    os.killpg(owned_pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=max(0.001, cleanup_deadline - time.monotonic()))
            direct_child_reaped = True
            exit_code = process.returncode
            while group_exists("after-reap") and time.monotonic() < cleanup_deadline:
                time.sleep(min(0.02, max(0, cleanup_deadline - time.monotonic())))
            if group_checks[-1]["group_exists"]:
                cleanup_error = "owned process group still present after cleanup budget"
        except (OSError, subprocess.TimeoutExpired):
            cleanup_error = "owned cleanup did not complete within budget"
        finally:
            if process.stdout is not None:
                process.stdout.close()
            child_elapsed = round(time.monotonic() - child_begin, 3)

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
                    copy_verified(entry, target)
                    if target.suffix == ".beam":
                        beam_paths.append(str(target))
            copied_sources = []
            copied_tests = []
            for entries, destinations in [(sources, copied_sources), (plan["selected_test_sources"], copied_tests)]:
                for entry in entries:
                    target = scratch / entry["path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    copy_verified(entry, target)
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
            with (OUT / "host-bootstrap.exs.txt").open("x") as retained:
                retained.write(script)
            actual_argv = ["/opt/homebrew/Cellar/elixir/1.20.4/bin/elixir", "--no-color", "--erl", "+S 2:2 +A 2", str(script_path)]
            env = {key: os.environ[key] for key in ("HOME", "USER", "TMPDIR") if key in os.environ}
            env.update({"PATH": "/opt/homebrew/Cellar/erlang/29.1.1_2/bin:/opt/homebrew/Cellar/elixir/1.20.4/bin:/usr/bin:/bin", "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8", "MIX_ENV": "prod", "ERL_CRASH_DUMP": "/dev/null"})
            child_begin = time.monotonic()
            process = subprocess.Popen(actual_argv, cwd=scratch, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
            owned_pid = process.pid
            # start_new_session establishes this child's private group with its
            # PID as PGID even if its leader exits before getpgid can observe it.
            owned_pgid = owned_pid
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            status = "running"
            deadline = child_begin + plan["limits"]["work_wall_seconds"]
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
                    # A leftover child holding stdout open must not hide the
                    # leader's exit until the work deadline. Reap detection is
                    # local to our Popen child and signals only its owned group.
                    if process.poll() is not None and group_exists("leader-exited"):
                        try:
                            os.killpg(owned_pgid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                if status == "running":
                    exit_code = process.wait(timeout=max(0.1, deadline - time.monotonic()))
                    status = "passed" if exit_code == 0 else "failed"
            finally:
                selector.close()
                # A completed leader is insufficient: terminate any remaining
                # members of this exact owned process group before returning.
                cleanup_owned()
                if cleanup_error:
                    status = "cleanup-failed"
    except BaseException:
        # Retain only a fixed classification, never an arbitrary caught term.
        runner_error = "runner-exception"
        if status in ("not-started", "running", "passed"):
            status = "runner-failed"
    finally:
        cleanup_owned()
        if cleanup_error:
            status = "cleanup-failed"
        # The TemporaryDirectory context runs on every exception. Observe its
        # actual absence here as well as after ordinary completion.
        scratch_cleaned = scratch_path is not None and not Path(scratch_path).exists()
        for entry in all_original_pins:
            try:
                verify(entry)
            except (SystemExit, OSError):
                original_changes.append(entry["path"])
        if original_changes:
            status = "original-input-changed"
        if not scratch_cleaned and scratch_path is not None:
            status = "scratch-cleanup-failed"
        with (OUT / "host.stdout.txt").open("xb") as retained:
            retained.write(output)
        receipt = {"schema": 1, "started_at": started, "status": status, "exit_code": exit_code, "elapsed_seconds": round(time.monotonic() - begin, 3), "child_elapsed_seconds": child_elapsed, "runner_argv": plan["runner_argv"], "actual_child_argv": actual_argv, "execution_plan_sha256": digest(PLAN_PATH), "source_revision": plan["source_revision"], "source_tree": plan["source_tree"], "output_bytes": len(output), "output_sha256": hashlib.sha256(output).hexdigest(), "scratch": scratch_path, "scratch_removed": scratch_cleaned, "owned_pid": owned_pid, "owned_pgid": owned_pgid, "direct_child_reaped": direct_child_reaped, "exact_owned_group_checks": group_checks, "owned_group_absent": bool(group_checks) and not group_checks[-1]["group_exists"], "cleanup_error": cleanup_error, "runner_error": runner_error, "copied_bytes_verified": copied_bytes_verified, "postrun_original_hashes_verified": len(all_original_pins) - len(original_changes), "postrun_original_changes": original_changes, "limits": plan["limits"], "scope": "component host tests; configured default-owner-absent negatives and labelled synthetic controller/transport positives only", "pending": plan["pending"], "no_native_capture_database_container_network_resources_started": True}
        with (OUT / "host-receipt.json").open("x") as retained:
            retained.write(json.dumps(receipt, indent=2) + "\n")
        sys.stdout.buffer.write(output)
        print(json.dumps({"status": status, "exit_code": exit_code, "scratch_removed": scratch_cleaned, "output_bytes": len(output)}))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
