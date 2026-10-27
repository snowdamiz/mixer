#!/opt/homebrew/opt/python@3.14/bin/python3.14
"""Released, closed default-workspace test environment. Never invoke a broad harness."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, choices=["candidate-1", "candidate-2", "candidate-3"])
    args = parser.parse_args()
    candidate = PACKET / args.candidate
    plan_path = candidate / "execution-plan.json"
    plan = json.loads(plan_path.read_text())
    release_path = candidate / "root-execution-release.json"
    if not release_path.is_file():
        raise SystemExit("default-authority runtime is not released by root")
    release = json.loads(release_path.read_text())
    if release.get("released") is not True or release.get("execution_plan_sha256") != sha(plan_path):
        raise SystemExit("root release does not match exact frozen plan")
    if plan["runner_sha256"] != sha(Path(__file__)):
        raise SystemExit("runner differs from frozen input")
    for entry in plan["selected_inputs"] + plan["tool_files"] + [entry for dependency in plan["dependencies"] for entry in dependency["files"]]:
        source = Path(entry["path"])
        source = source if source.is_absolute() else ROOT / source
        if source.stat().st_size != entry["bytes"] or sha(source) != entry["sha256"]:
            raise SystemExit("frozen input changed: " + entry["path"])

    output = candidate / "execution"
    output.mkdir(exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-dispatcher-default-"))
    environment = {key: value for key, value in plan["environment"].items() if key not in ["inherited", "MIXER_DISPATCHER_DEFAULT_TEST_PORT"]}
    environment.update(HOME=str(scratch / "home"), TMPDIR=str(scratch / "tmp"), MIXER_DISPATCHER_DEFAULT_EVIDENCE=str(output))
    (scratch / "home").mkdir()
    (scratch / "tmp").mkdir()
    (scratch / "app-ebin").mkdir()
    receipt = {"schema": 1, "status": "failed", "started_at": datetime.now(timezone.utc).isoformat(),
               "source_revision": plan["source_revision"], "source_tree": plan["source_tree"],
               "execution_plan_sha256": sha(plan_path), "commands": [], "owned_processes": [],
               "cleanup": {}, "limitations": plan["pending"], "tools": plan["tools"]}
    started = time.monotonic()
    work_deadline = started + plan["limits"]["total_work_seconds"]
    output_bytes = 0
    server = None
    server_log = None
    postgres_port = None
    server_output = scratch / "postgres.log"
    runtime_started = False

    def group_exists(pid):
        try:
            os.killpg(pid, 0)
            return True
        except ProcessLookupError:
            return False

    def stop_owned(process, deadline, gentle=False):
        if gentle and process.poll() is None:
            os.kill(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=max(0.001, min(4, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                pass
        if group_exists(process.pid):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=max(0.001, deadline - time.monotonic()))
        while group_exists(process.pid) and time.monotonic() < deadline:
            time.sleep(min(0.02, max(0, deadline - time.monotonic())))
        absent = not group_exists(process.pid)
        receipt["owned_processes"].append({"pid": process.pid, "pgid": process.pid,
                                           "direct_child_reaped": process.poll() is not None,
                                           "process_group_absent": absent, "exit_code": process.returncode})
        if not absent:
            raise RuntimeError("owned child group cleanup incomplete")

    def run(label, argv, timeout=30):
        nonlocal output_bytes
        deadline = min(work_deadline, time.monotonic() + timeout)
        if time.monotonic() >= deadline:
            raise RuntimeError("total work deadline expired")
        command = {"label": label, "argv": list(map(str, argv)), "cwd": str(scratch), "started_monotonic": time.monotonic()}
        receipt["commands"].append(command)
        data = bytearray()
        process = subprocess.Popen(command["argv"], cwd=scratch, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        command.update(pid=process.pid, pgid=process.pid)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise RuntimeError("owned command deadline expired: " + label)
                if server is not None and server.poll() is not None:
                    raise RuntimeError("owned postgres exited before tests completed")
                if server_output.exists() and server_output.stat().st_size + output_bytes > plan["limits"]["combined_output_bytes"]:
                    raise RuntimeError("combined output budget exceeded")
                for key, _ in selector.select(timeout=min(0.1, max(0, deadline - time.monotonic()))):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        break
                    remaining = plan["limits"]["combined_output_bytes"] - output_bytes
                    data.extend(chunk[:remaining])
                    output_bytes += min(len(chunk), remaining)
                    if len(chunk) > remaining:
                        raise RuntimeError("combined output budget exceeded")
                if process.poll() is not None and group_exists(process.pid):
                    # A descendant retaining the pipe cannot extend the deadline.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            process.wait(timeout=max(0.001, deadline - time.monotonic()))
            command["exit_code"] = process.returncode
        finally:
            selector.close()
            process.stdout.close()
            log = output / (label + ".stdout.txt")
            log.write_bytes(data)
            command.update(duration_seconds=round(time.monotonic() - command["started_monotonic"], 3),
                           output=log.name, output_sha256=sha(log))
            stop_owned(process, min(time.monotonic() + 2, work_deadline + plan["limits"]["owned_cleanup_seconds"]))
        if command["exit_code"] != 0:
            raise RuntimeError("owned command failed: " + label)

    def port_closed(port):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return False
        except ConnectionRefusedError:
            return True
        except OSError:
            return None

    try:
        copied = {}
        for entry in plan["selected_inputs"]:
            source = candidate / "inputs" / entry["path"]
            if source.stat().st_size != entry["bytes"] or sha(source) != entry["sha256"]:
                raise RuntimeError("retained frozen source copy differs")
            target = scratch / "inputs" / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if sha(target) != entry["sha256"]:
                raise RuntimeError("scratch input copy differs")
            copied[entry["path"]] = target
        code_paths = []
        dependency_metadata = []
        for dependency in plan["dependencies"]:
            ebin = scratch / "deps" / dependency["name"] / "ebin"
            ebin.mkdir(parents=True)
            code_paths += ["-pa", str(ebin)]
            dependency_metadata.append({"name": dependency["name"], "version": dependency["version"], "ebin": str(ebin)})
            for entry in dependency["files"]:
                target = ebin / Path(entry["path"]).name
                shutil.copyfile(ROOT / entry["path"], target)
                if sha(target) != entry["sha256"]:
                    raise RuntimeError("scratch dependency copy differs")
        sources_path = scratch / "sources.json"
        sources_path.write_text(json.dumps([str(copied[name]) for name in plan["source_roster"]]))
        dependencies_path = scratch / "dependency-metadata.json"
        dependencies_path.write_text(json.dumps(dependency_metadata))
        pg = Path(plan["postgres_bin"])
        elixir = "/opt/homebrew/Cellar/elixir/1.20.4/bin/elixir"
        run("elixir-version", [elixir, "--erl", "+S 2:2 +A 2", "--version"])
        run("postgres-version", [pg / "postgres", "--version"])
        run("openssl-version", ["/usr/bin/openssl", "version"])
        run("postgres-init", [pg / "initdb", "-D", scratch / "pg", "-U", "mixer_dispatcher_fixture", "-A", "trust", "--no-locale", "-E", "UTF8"])
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            postgres_port = reservation.getsockname()[1]
        environment["MIXER_DISPATCHER_DEFAULT_TEST_PORT"] = str(postgres_port)
        server_argv = [str(pg / "postgres"), "-D", str(scratch / "pg"), "-h", "127.0.0.1", "-p", str(postgres_port), "-k", "", "-c", "timezone=UTC", "-c", "max_connections=15"]
        server_log = server_output.open("xb")
        server = subprocess.Popen(server_argv, cwd=scratch, env=environment, stdin=subprocess.DEVNULL,
                                  stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
        runtime_started = True
        receipt["commands"].append({"label": "postgres-server", "argv": server_argv, "cwd": str(scratch), "pid": server.pid, "pgid": server.pid})
        receipt["owned_postgres"] = {"host": "127.0.0.1", "port": postgres_port, "data_directory": str(scratch / "pg"), "tls": False}
        readiness_deadline = min(work_deadline, time.monotonic() + 5)
        while port_closed(postgres_port) is not False:
            if time.monotonic() >= readiness_deadline or server.poll() is not None:
                raise RuntimeError("owned postgres readiness failed")
            time.sleep(0.02)
        packet_relative = str(PACKET.relative_to(ROOT))
        run("database-provision", [pg / "psql", "-X", "-h", "127.0.0.1", "-p", str(postgres_port), "-U", "mixer_dispatcher_fixture", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-f", copied[packet_relative + "/provision.sql"]])
        run("default-authority-tests", [elixir, "--no-color", "--erl", "+S 2:2 +A 2", *code_paths,
             copied[packet_relative + "/bootstrap.exs"], sources_path,
             copied[packet_relative + "/default_authority_test.exs"], scratch / "app-ebin", dependencies_path], timeout=45)
        result = json.loads((output / "exunit-result.json").read_text())
        components = json.loads((output / "component-cleanup.json").read_text())
        receipt["exunit_result"] = result
        receipt["component_cleanup"] = components
        assert result == {**result, "total": 7, "failures": 0, "skipped": 0, "excluded": 0}
        assert all(components[name] for name in ["owned_components_stopped", "default_owner_absent", "default_repo_absent", "admission_absent", "ephemeral_tls_key_directory_removed"])
        assert components["jwks_tls_requests"] >= 1
        receipt["cleanup"]["fixture_tls_port_closed"] = port_closed(components["fixture_tls_port"])
        assert receipt["cleanup"]["fixture_tls_port_closed"] is True
        receipt["status"] = "passed"
    except BaseException as error:
        receipt["failure_class"] = type(error).__name__
        receipt["failure"] = str(error) if isinstance(error, (AssertionError, RuntimeError)) else "runner exception; retained owned output"
    finally:
        cleanup_deadline = min(time.monotonic() + plan["limits"]["owned_cleanup_seconds"], work_deadline + plan["limits"]["owned_cleanup_seconds"])
        if server is not None:
            try:
                stop_owned(server, cleanup_deadline, gentle=True)
                receipt["cleanup"]["postgres_direct_child_reaped"] = server.poll() is not None
                receipt["cleanup"]["postgres_owned_group_absent"] = not group_exists(server.pid)
                receipt["cleanup"]["postgres_port_closed"] = port_closed(postgres_port)
                receipt["cleanup"]["postmaster_pid_file_absent"] = not (scratch / "pg/postmaster.pid").exists()
            except BaseException as error:
                receipt["cleanup"]["postgres_cleanup_failure"] = type(error).__name__
        if server_log is not None:
            server_log.close()
        if server_output.exists():
            with server_output.open("rb") as retained_input:
                retained = retained_input.read(plan["limits"]["combined_output_bytes"] - output_bytes + 1)
            remaining = plan["limits"]["combined_output_bytes"] - output_bytes
            (output / "postgres.stdout.txt").write_bytes(retained[:remaining])
            if len(retained) > remaining:
                receipt["status"] = "failed"
                receipt["failure"] = "combined output budget exceeded"
        clean_server = server is None or all(receipt["cleanup"].get(name) is True for name in ["postgres_direct_child_reaped", "postgres_owned_group_absent", "postgres_port_closed", "postmaster_pid_file_absent"])
        if clean_server:
            shutil.rmtree(scratch)
        receipt["cleanup"]["scratch_removed"] = not scratch.exists()
        receipt["cleanup"]["scratch_path"] = str(scratch)
        receipt["runtime_started"] = runtime_started
        receipt["original_input_changes"] = [entry["path"] for entry in plan["selected_inputs"] if sha(ROOT / entry["path"]) != entry["sha256"]]
        receipt["original_dependency_or_tool_changes"] = [entry["path"] for entry in plan["tool_files"] + [entry for dependency in plan["dependencies"] for entry in dependency["files"]]
                                                                  if sha(Path(entry["path"]) if Path(entry["path"]).is_absolute() else ROOT / entry["path"]) != entry["sha256"]]
        if not clean_server or not receipt["cleanup"]["scratch_removed"] or receipt["original_input_changes"] or receipt["original_dependency_or_tool_changes"]:
            receipt["status"] = "failed"
            receipt["failure"] = "cleanup or frozen input integrity incomplete"
        receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        receipt["outputs"] = {file.name: sha(file) for file in output.iterdir() if file.is_file()}
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json"), "cleanup": receipt["cleanup"]}, sort_keys=True))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
