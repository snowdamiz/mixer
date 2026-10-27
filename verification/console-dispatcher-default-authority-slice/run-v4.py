#!/opt/homebrew/opt/python@3.14/bin/python3.14
"""Closed root-released default workspace runner; all owned handles survive failures."""
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
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, choices=["candidate-4"])
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
    dependency_pins = [entry for dependency in plan["dependencies"] for entry in dependency["files"]]
    for entry in plan["selected_inputs"] + plan["tool_files"] + dependency_pins:
        source = Path(entry["path"])
        source = source if source.is_absolute() else ROOT / source
        if source.stat().st_size != entry["bytes"] or sha(source) != entry["sha256"]:
            raise SystemExit("frozen input changed: " + entry["path"])

    output = candidate / "execution"
    output.mkdir(exist_ok=False)
    receipt = {"schema": 2, "status": "failed", "started_at": datetime.now(timezone.utc).isoformat(),
               "source_revision": plan["source_revision"], "source_tree": plan["source_tree"],
               "execution_plan_sha256": sha(plan_path), "commands": [], "owned_processes": [],
               "cleanup": {}, "limitations": plan["pending"][1:], "tools": {**plan["tools"], "python_observed": sys.version.splitlines()[0]}, "runtime_started": False}
    started = time.monotonic()
    work_deadline = started + plan["limits"]["total_work_seconds"]
    total_deadline = work_deadline + plan["limits"]["owned_cleanup_seconds"]
    scratch = None
    environment = None
    owned = []
    server_record = None
    server_log = None
    server_output = None
    postgres_port = None
    output_bytes = 0

    def group_exists(pid):
        try:
            os.killpg(pid, 0)
            return True
        except ProcessLookupError:
            return False

    def stop_owned(record, deadline, gentle=False):
        process = record["process"]
        errors = []
        try:
            if gentle and process.poll() is None:
                try:
                    os.kill(process.pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=max(0.001, min(1.5, deadline - time.monotonic())))
                except subprocess.TimeoutExpired:
                    pass
            if group_exists(process.pid):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=max(0.001, deadline - time.monotonic()))
            while group_exists(process.pid) and time.monotonic() < deadline:
                time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        except BaseException as error:
            errors.append(type(error).__name__)
        try:
            absent = not group_exists(process.pid)
        except BaseException as error:
            absent = False
            errors.append(type(error).__name__)
        try:
            reaped = process.poll() is not None
        except BaseException as error:
            reaped = False
            errors.append(type(error).__name__)
        record["terminal"] = {"label": record["label"], "pid": process.pid, "pgid": process.pid,
                              "direct_child_reaped": reaped, "process_group_absent": absent,
                              "exit_code": process.returncode, "cleanup_errors": errors}
        return reaped and absent and not errors

    def launch(label, argv, destination):
        # Register the handle immediately, before any subsequent operation can fail.
        process = subprocess.Popen(list(map(str, argv)), cwd=scratch, env=environment,
                                   stdin=subprocess.DEVNULL, stdout=destination,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        record = {"label": label, "process": process}
        owned.append(record)
        return record

    def run(label, argv, timeout=30):
        nonlocal output_bytes
        deadline = min(work_deadline, time.monotonic() + timeout)
        if time.monotonic() >= deadline:
            raise RuntimeError("total work deadline expired")
        command = {"label": label, "argv": list(map(str, argv)), "cwd": str(scratch)}
        receipt["commands"].append(command)
        begin = time.monotonic()
        data = bytearray()
        record = launch(label, argv, subprocess.PIPE)
        process = record["process"]
        command.update(pid=process.pid, pgid=process.pid)
        selector = selectors.DefaultSelector()
        try:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise RuntimeError("owned command deadline expired: " + label)
                if server_record is not None and server_record["process"].poll() is not None:
                    raise RuntimeError("owned postgres exited before tests completed")
                if server_output is not None and server_output.exists() and server_output.stat().st_size + output_bytes > plan["limits"]["combined_output_bytes"]:
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
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            process.wait(timeout=max(0.001, deadline - time.monotonic()))
            command["exit_code"] = process.returncode
        finally:
            try:
                selector.close()
                if process.stdout is not None:
                    process.stdout.close()
                log = output / (label + ".stdout.txt")
                with log.open("xb") as retained:
                    retained.write(data)
                command.update(duration_seconds=round(time.monotonic() - begin, 3), output=log.name, output_sha256=sha(log))
            finally:
                if not stop_owned(record, min(time.monotonic() + 1, total_deadline)):
                    command["local_cleanup_failed"] = True
        if command.get("exit_code") != 0 or command.get("local_cleanup_failed"):
            raise RuntimeError("owned command or cleanup failed: " + label)
        return bytes(data)

    def port_closed(port):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                return False
        except ConnectionRefusedError:
            return True
        except OSError:
            return None

    def fail(label, error=None):
        receipt["status"] = "failed"
        receipt.setdefault("failure_events", []).append({"stage": label, "class": type(error).__name__ if error else None})

    try:
        # Scratch and every setup operation are protected by this outer finally.
        scratch = Path(tempfile.mkdtemp(prefix="mixer-dispatcher-default-"))
        environment = {key: value for key, value in plan["environment"].items() if key not in ["inherited", "MIXER_DISPATCHER_DEFAULT_TEST_PORT"]}
        environment.update(HOME=str(scratch / "home"), TMPDIR=str(scratch / "tmp"), MIXER_DISPATCHER_DEFAULT_EVIDENCE=str(output))
        for directory in ["home", "tmp", "app-ebin"]:
            (scratch / directory).mkdir()
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
        dependency_path = scratch / "dependency-metadata.json"
        dependency_path.write_text(json.dumps(dependency_metadata))
        pg = Path(plan["postgres_bin"])
        elixir = "/opt/homebrew/Cellar/elixir/1.20.4/bin/elixir"
        receipt["tools"]["elixir_observed"] = run("elixir-version", [elixir, "--erl", "+S 2:2 +A 2", "--version"]).decode("utf-8").strip()
        receipt["tools"]["postgresql_observed"] = run("postgres-version", [pg / "postgres", "--version"]).decode("utf-8").strip()
        receipt["tools"]["openssl_observed"] = run("openssl-version", ["/usr/bin/openssl", "version"]).decode("utf-8").strip()
        run("postgres-init", [pg / "initdb", "-D", scratch / "pg", "-U", "mixer_dispatcher_fixture", "-A", "trust", "--no-locale", "-E", "UTF8"])
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            postgres_port = reservation.getsockname()[1]
        environment["MIXER_DISPATCHER_DEFAULT_TEST_PORT"] = str(postgres_port)
        server_output = scratch / "postgres.log"
        server_log = server_output.open("xb")
        server_argv = [str(pg / "postgres"), "-D", str(scratch / "pg"), "-h", "127.0.0.1", "-p", str(postgres_port), "-k", "", "-c", "timezone=UTC", "-c", "max_connections=15"]
        server_record = launch("postgres-server", server_argv, server_log)
        receipt["runtime_started"] = True
        receipt["commands"].append({"label": "postgres-server", "argv": server_argv, "cwd": str(scratch), "pid": server_record["process"].pid, "pgid": server_record["process"].pid})
        receipt["owned_postgres"] = {"host": "127.0.0.1", "port": postgres_port, "data_directory": str(scratch / "pg"), "tls": False}
        readiness_deadline = min(work_deadline, time.monotonic() + 4)
        while port_closed(postgres_port) is not False:
            if time.monotonic() >= readiness_deadline or server_record["process"].poll() is not None:
                raise RuntimeError("owned postgres readiness failed")
            time.sleep(0.02)
        directory_output = run("owned-cluster-identity", [pg / "psql", "-X", "-A", "-t", "-h", "127.0.0.1", "-p", str(postgres_port), "-U", "mixer_dispatcher_fixture", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", "SHOW data_directory"])
        observed_directory = Path(directory_output.decode("utf-8").strip()).resolve()
        expected_directory = (scratch / "pg").resolve()
        if observed_directory != expected_directory or server_record["process"].poll() is not None:
            raise RuntimeError("loopback cluster identity does not match owned live postgres")
        receipt["owned_cluster_identity"] = {"observed_data_directory": str(observed_directory), "expected_data_directory": str(expected_directory), "match": True, "owned_postgres_alive_before_mutation": True}
        prefix = str(PACKET.relative_to(ROOT))
        run("database-provision", [pg / "psql", "-X", "-h", "127.0.0.1", "-p", str(postgres_port), "-U", "mixer_dispatcher_fixture", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-f", copied[prefix + "/provision.sql"]])
        run("default-authority-tests", [elixir, "--no-color", "--erl", "+S 2:2 +A 2", *code_paths,
             copied[prefix + "/bootstrap-v4.exs"], sources_path,
             copied[prefix + "/default_authority_test-v4.exs"], scratch / "app-ebin", dependency_path], timeout=40)
        result = json.loads((output / "exunit-result.json").read_text())
        components = json.loads((output / "component-cleanup.json").read_text())
        receipt["exunit_result"] = result
        receipt["component_cleanup"] = components
        assert result == {**result, "total": 7, "failures": 0, "skipped": 0, "excluded": 0}
        assert all(components[name] for name in ["owned_components_stopped", "default_owner_absent", "default_repo_absent", "admission_absent", "ephemeral_tls_key_directory_removed"])
        assert components["jwks_tls_requests"] >= 1
        if time.monotonic() > work_deadline:
            raise RuntimeError("total work deadline expired")
        receipt["status"] = "passed"
    except BaseException as error:
        fail("work", error)
        if isinstance(error, RuntimeError):
            receipt["failure"] = str(error)
    finally:
        cleanup_deadline = min(time.monotonic() + plan["limits"]["owned_cleanup_seconds"], total_deadline)
        try:
            # Every handle is revisited even if a run-local cleanup raised.
            all_owned_absent = True
            for record in reversed(owned):
                clean = stop_owned(record, cleanup_deadline, gentle=record is server_record)
                all_owned_absent = clean and all_owned_absent
            receipt["owned_processes"] = [record.get("terminal", {"label": record["label"], "terminal_missing": True}) for record in owned]
            receipt["cleanup"]["all_owned_children_reaped_and_groups_absent"] = all_owned_absent
            if not all_owned_absent:
                fail("owned-child-cleanup")
            if server_log is not None:
                try:
                    server_log.close()
                except BaseException as error:
                    fail("postgres-log-close", error)
            if postgres_port is not None:
                receipt["cleanup"]["postgres_port_closed"] = port_closed(postgres_port)
                receipt["cleanup"]["postmaster_pid_file_absent"] = scratch is not None and not (scratch / "pg/postmaster.pid").exists()
            else:
                receipt["cleanup"]["postgres_not_started"] = True
            tls_start = output / "component-start.json"
            if tls_start.exists():
                try:
                    tls = json.loads(tls_start.read_text())
                    receipt["cleanup"]["fixture_tls_port_closed"] = port_closed(tls["fixture_tls_port"])
                    receipt["cleanup"]["tls_key_directory_removed_at_start"] = tls["ephemeral_tls_key_directory_removed"]
                except BaseException as error:
                    fail("tls-port-observation", error)
            if server_output is not None and server_output.exists():
                try:
                    remaining = plan["limits"]["combined_output_bytes"] - output_bytes
                    with server_output.open("rb") as input_stream:
                        retained = input_stream.read(remaining + 1)
                    with (output / "postgres.stdout.txt").open("xb") as output_stream:
                        output_stream.write(retained[:remaining])
                    if len(retained) > remaining:
                        fail("combined-output-budget")
                except BaseException as error:
                    fail("postgres-log-retention", error)
            postgres_closed = postgres_port is None or all(receipt["cleanup"].get(name) is True for name in ["postgres_port_closed", "postmaster_pid_file_absent"])
            tls_closed = not tls_start.exists() or receipt["cleanup"].get("fixture_tls_port_closed") is True
            safe_to_remove = all_owned_absent and postgres_closed and tls_closed
            if not safe_to_remove:
                fail("cleanup-incomplete-scratch-preserved")
            if scratch is not None and safe_to_remove:
                try:
                    shutil.rmtree(scratch)
                except BaseException as error:
                    fail("scratch-removal", error)
            receipt["cleanup"]["scratch_path"] = str(scratch) if scratch is not None else None
            receipt["cleanup"]["scratch_removed"] = scratch is None or not scratch.exists()
            if not receipt["cleanup"]["scratch_removed"]:
                fail("scratch-remains")
            changes = []
            errors = []
            for entry in plan["selected_inputs"] + plan["tool_files"] + dependency_pins:
                path = Path(entry["path"])
                path = path if path.is_absolute() else ROOT / path
                try:
                    if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
                        changes.append(entry["path"])
                except BaseException as error:
                    errors.append({"path": entry["path"], "class": type(error).__name__})
            receipt["original_input_changes"] = changes
            receipt["original_input_read_errors"] = errors
            if changes or errors:
                fail("postrun-input-integrity")
        except BaseException as error:
            fail("outer-cleanup", error)
        finally:
            # A cleanup/read/hash exception must not skip the terminal receipt.
            receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
            receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
            if time.monotonic() > total_deadline:
                fail("total-55-second-budget")
            try:
                receipt["outputs"] = {file.name: sha(file) for file in output.iterdir() if file.is_file()}
            except BaseException as error:
                fail("output-hash-retention", error)
            with (output / "receipt.json").open("x") as terminal:
                json.dump(receipt, terminal, indent=2)
                terminal.write("\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json"), "cleanup": receipt["cleanup"]}, sort_keys=True))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
