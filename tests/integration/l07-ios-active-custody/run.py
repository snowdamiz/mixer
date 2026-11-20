#!/usr/bin/env python3
"""Replay one signed-in iOS cancellation across active worker custody loss."""

import argparse
import ast
from contextlib import ExitStack, closing
import errno
import json
import os
from pathlib import Path
import re
import runpy
import secrets
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BASE = "0151489ca628de071385f0afbe4017a57c784cdc"
HOSTED_TREE = "fea6582650198d5f5b6c38bdca8f9c9ae5fbc064"
OVERLAY = "41d46e475bc1e9ab88beca6338b1b8af8778309a"
DELIVERED_FIXTURE_BLOB = "3819e19c3b80bc3abf51dd179273fc4f377b7cf1"
FIRST_RECEIPT_BLOB = "eb8f497fb7fb05cfa5163f58ec83b3d0c9673817"
# The replay host reports a TCP MSL of 15 seconds. Allow two MSLs plus
# 30 seconds of margin before failing the same-port bind check.
REBIND_SECONDS = 60
BARRIER_SECONDS = 90
INERT_RECIPE_SECONDS = 120
WORKER_TEST = "hosted/scripts/test_native_artifact_worker.py"
HOSTED_FILES = (
    "hosted/lib/mixer_hosted/builds/native_development_dispatch.ex",
    "hosted/priv/development/compiler_worker.py",
    "hosted/priv/development/ios_build_custody.py",
    "hosted/priv/development/native_artifact_worker.py",
    WORKER_TEST,
)
PAIR = "tests/integration/l05-pair25-http"
REGISTRATION = "tests/integration/free-project-starter/registration-runner.py"
API_TEST = "test/mixer_hosted/browser_auth/local_starter_http_sql_spec.exs"


def git(*args):
    return subprocess.check_output(
        ["git", "--no-lazy-fetch", *args], cwd=REPO, timeout=10,
    )


def provision(root, cache, archives, result):
    hosted_tree = git("rev-parse", f"{BASE}:hosted").decode().strip()
    if hosted_tree != HOSTED_TREE:
        raise RuntimeError("pinned hosted tree differs from the first replay")
    result["baseHostedTree"] = hosted_tree
    archive = root / "base.tar"
    with archive.open("xb") as stream:
        subprocess.run(
            ["git", "--no-lazy-fetch", "archive", BASE, "hosted", PAIR, REGISTRATION],
            cwd=REPO, check=True, stdout=stream, timeout=20,
        )
    with tarfile.open(archive) as stream:
        stream.extractall(root, filter="data")
    archive.unlink()

    kit = runpy.run_path(str(root / PAIR / "run.py"))
    result["overlaySHA256"] = {}
    for path in HOSTED_FILES:
        data = git("show", f"{OVERLAY}:{path}")
        (root / path).write_bytes(data)
        result["overlaySHA256"][path] = kit["sha"](data)

    # Change the platform of the existing fixture-only seed, capacity, and
    # processor pause. All production setup and dispatch stay on stock paths.
    for name, changes in {
        "api-case.exs": {
            "serve one ordinary Android build": "serve one ordinary iOS build",
            "$3,'android',$4": "$3,'ios',$4",
            'platform: "android"': 'platform: "ios"',
            "WHERE platform='android'": "WHERE platform='ios'",
        },
        "processor.exs": {
            '%{"platform" => "android"}': '%{"platform" => "ios"}',
            '%{platform: :android}': '%{platform: :ios}',
        },
    }.items():
        path = root / PAIR / name
        source = path.read_text()
        for old, new in changes.items():
            if source.count(old) != (2 if old == 'platform: "android"' else 1):
                raise RuntimeError(f"pinned fixture substitution differs in {name}: {old}")
            source = source.replace(old, new)
        path.write_text(source)
    kit["fixtures"](root / "hosted")

    hosted = root / "hosted"
    mix_lock = (hosted / "mix.lock").read_bytes()
    result["mixLockSHA256"] = kit["sha"](mix_lock)
    packages = re.findall(rb'\{:hex, :(\w+), "([^"]+)"', mix_lock)
    if len(packages) != 21:
        raise RuntimeError("unexpected pinned Hex lock entries")
    hex_home, mix_home = root / "hex", root / "mix"
    tarballs = hex_home / "packages/hexpm"
    tarballs.mkdir(parents=True)
    shutil.copyfile(cache / "cache.ets", hex_home / "cache.ets")
    for name, version in packages:
        filename = f"{name.decode()}-{version.decode()}.tar"
        shutil.copyfile(cache / "packages/hexpm" / filename, tarballs / filename)
    shutil.copytree(archives / "hex-2.5.1", mix_home / "archives/hex-2.5.1")
    return kit


def make_recipe(root, kit):
    source = root / "inert-source"
    source.mkdir()
    lock = b"success"
    (source / "mixer.lock").write_bytes(lock)
    lock_sha = kit["sha"](lock)
    tree_sha = kit["sha"](b"mixer.lock\0" + lock_sha.encode() + b"\n")
    files = {"mixer.lock": lock_sha}
    [fixture] = [
        ast.literal_eval(node.value)
        for node in ast.parse((root / WORKER_TEST).read_bytes()).body
        if isinstance(node, ast.Assign)
        and any(isinstance(name, ast.Name) and name.id == "IOS_CLI_FIXTURE"
                for name in node.targets)
    ]
    # Extend only the two inert test barriers, including the nested child.
    if fixture.count("time.monotonic() + 12") != 2:
        raise RuntimeError("pinned inert barrier deadlines differ")
    fixture = fixture.replace("time.monotonic() + 12", f"time.monotonic() + {BARRIER_SECONDS}")
    cli = root / "inert-cli"
    cli.write_text("#!" + sys.executable + " -I\n" + fixture)
    cli.chmod(0o500)
    xcode = Path("/usr/bin/xcodebuild")
    tools = {str(tool): kit["sha"](tool.read_bytes()) for tool in (cli, xcode)}
    environment = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
    recipe = dict(profile="unsigned-ios-simulator-v1", timeout_seconds=INERT_RECIPE_SECONDS,
                  argv=[str(cli), "build", "--platform", "ios", "--directory", str(source)],
                  cwd=str(source), environment=environment,
                  package_policy="exact-owned-local-manifests-no-external-packages",
                  inputs=files, tools=tools)
    recipe_path = root / "recipe.json"
    recipe_sha = kit["write"](recipe_path, recipe)
    kit["write"](root / "inputs.json", dict(source_tree_sha256=tree_sha,
                 linux_lock_sha256=lock_sha, recipe_sha256=recipe_sha))
    spec = dict(source=dict(kind="revision", reference="starter-" + tree_sha, sha256=tree_sha),
                toolchain_lock_sha256=lock_sha, build_definition_sha256=recipe_sha)
    registration = dict(root=str(source), recipe=str(recipe_path), files=files)
    policy = dict(cli=str(cli), recipe_sha256=recipe_sha, environment=environment, inputs=files, tools=tools)
    return spec, registration, policy


def environment(root):
    (root / "home").mkdir(exist_ok=True)
    return dict(PATH=os.environ["PATH"], HOME=str(root / "home"), MIX_HOME=str(root / "mix"),
                HEX_HOME=str(root / "hex"), HEX_OFFLINE="1", MIX_ENV="test", LC_ALL="C",
                TMPDIR=str(root), PAIR25_RUN=str(root), PAIR25_CANCEL="1",
                PYTHONDONTWRITEBYTECODE="1")


def db_rows(database, operation):
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
        row = db.execute("SELECT value FROM operations WHERE id=?", (operation,)).fetchone()
        claim = db.execute(
            """SELECT parent_pid, launch, terminal, uncertain
               FROM ios_custody_claims WHERE operation=?""", (operation,),
        ).fetchone()
        counts = [db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                  for table in ("operations", "ios_custody_claims")]
    if row and claim and claim[1]:
        parent, launch, terminal, uncertain = claim
        return (json.loads(row[0]), parent, json.loads(launch),
                json.loads(terminal) if terminal else None, uncertain, counts)
    return None


def drive(root, kit, env, pg, result):
    require, read, write, wait = (kit[name] for name in ("require", "read", "write", "wait"))
    owned, wire, http = (kit[name] for name in ("owned", "wire", "http"))
    host, db, commands = kit["HOST"], kit["DB"], result["commands"]
    hosted = root / "hosted"
    result["stage"] = "locked-hosted-compile"
    kit["compile_hosted"](root, hosted, env, commands)
    result["toolchain"] = {
        "postgres": subprocess.check_output([pg / "postgres", "--version"], timeout=3, text=True).strip(),
        "mix": subprocess.check_output(["mix", "--version"], env=env, timeout=5, text=True).strip(),
        "python": sys.version.split()[0],
    }
    result["stage"] = "restricted-services"
    spec, registration, policy = make_recipe(root, kit)
    code = hosted / "priv/development"
    sys.path.insert(0, str(code))
    import ios_build_custody

    _, runtime_pins = ios_build_custody.runtime_image()
    result["runtimeSHA256"] = runtime_pins
    state = root / "worker"
    state.mkdir(mode=0o700)
    db_port, worker_port = kit["port"](), kit["port"]()
    require(db_port != worker_port, "fixture ports collided")
    ports = result["ports"] = [db_port, worker_port]
    env.update(MIXER_BROWSER_STORAGE_PORT=str(db_port),
               MIXER_BROWSER_CATALOG_FIXTURE_ROOT=str(root / "catalog"))
    (root / "catalog").mkdir()
    psql = [pg / "psql", "-XqAtw", "-v", "ON_ERROR_STOP=1", "-h", host,
            "-p", str(db_port), "-U", "fixture_admin"]

    def sql(statement, database=db):
        return subprocess.check_output([*psql, "-d", database, "-c", statement], env=env,
                                       stderr=subprocess.STDOUT, timeout=3, text=True).strip()

    def snapshot():
        return json.loads(sql(kit["SQL_STATE"]))

    def jobs():
        return json.loads(sql("""SELECT COALESCE(json_agg(json_build_array(id, args->>'kind', state::text)
                                ORDER BY id), 'null'::json) FROM oban_jobs"""))

    def start_job():
        [job] = json.loads(sql(
            "SELECT json_agg(json_build_object('id', id, 'state', state::text, "
            "'attemptedAtMS', floor(extract(epoch FROM attempted_at) * 1000)::bigint)) "
            "FROM oban_jobs WHERE args->>'kind' = 'start'"
        ))
        return job

    def ready(name, process, seconds):
        path = root / name
        return wait(lambda: read(path) if path.is_file() else None, seconds, process)

    def mark(path):
        path.touch(exist_ok=False)

    with owned(root, "initdb", [pg / "initdb", "-D", root / "pg", "-U", "fixture_admin",
                               "--locale=C", "--encoding=UTF8", "--auth=trust", "--no-sync"],
               root, env, commands) as process:
        process.wait(timeout=15)

    with ExitStack() as services:
        postgres = services.enter_context(owned(
            root, "postgres", [pg / "postgres", "-D", root / "pg", "-h", host, "-p", str(db_port),
                               "-k", "", "-c", "jit=off"], root, env, commands, stop=signal.SIGINT,
        ))
        wait(lambda: kit["listening"](db_port), 8, postgres)
        require(sql("SHOW data_directory", "postgres") == str(root / "pg"), "unexpected PostgreSQL data directory")
        sql(runpy.run_path(str(root / REGISTRATION))["ROLES"], "postgres")
        api = services.enter_context(owned(
            root, "api", ["mix", "test", "--no-compile", "--only", "pair25_http", API_TEST],
            hosted, env, commands, stop=lambda: mark(root / "api.done"),
        ))
        auth = ready("api.ready", api, 60)
        ports.extend(auth[key] for key in ("port", "issuer", "jwks"))
        require(len(ports) == len(set(ports)), "fixture ports collided")
        owner = auth["cookie"]
        worker_id, token = "l07-native-worker", secrets.token_hex(32)
        processor_env = dict(
            env, MIXER_HOSTED_ROLE="processor", MIXER_PROCESSOR_PROFILE="builds_v1",
            MIXER_BUILD_OPERATION_INTENT="durable_intent_v1", MIXER_DATABASE_HOST=host,
            MIXER_DATABASE_NAME=db, MIXER_DATABASE_USER="mixer_build_processor",
            MIXER_DATABASE_PASSWORD="loopback-fixture", MIXER_DATABASE_POOL_SIZE="2",
            MIXER_QUEUE_BUILDS_CONCURRENCY="1", MIXER_BUILD_DISPATCH="native_development_v1",
            MIXER_NATIVE_RETAINED_ROOT=str(state), MIXER_NATIVE_WORKER_PORT=str(worker_port),
            MIXER_NATIVE_WORKER_ID=worker_id, MIXER_NATIVE_WORKER_TOKEN=token,
        )
        processor = services.enter_context(owned(
            root, "processor", ["mix", "run", "--no-start", "--no-compile", root / PAIR / "processor.exs"],
            hosted, processor_env, commands, stop=lambda: mark(root / "processor.done"),
        ))
        result["processorAdmission"] = ready("processor.ready", processor, 20)
        require(result["processorAdmission"] == {"role": "mixer_build_processor", "paused": True},
                "processor was not restricted and paused")
        require(jobs() is None and all(value is None for value in snapshot().values()),
                "pre-create queue or custody was not empty")

        result["stage"] = "one-customer-build"
        result["buildPOSTs"] += 1
        status, _, raw = http(auth, kit["BUILD"], cookie=owner, body=auth["build"])
        result["buildCreateHTTP"] = status
        require(status == 201, f"ordinary signed-in build create returned {status}: {raw!r}")
        created = json.loads(raw)
        scope = created["selection"]
        require(created["state"] == "queued" and created["outcome"] == "applied"
                and {k: v for k, v in scope.items() if k != "build_id"} ==
                {k: v for k, v in auth["build"].items() if k != "source_input_id"},
                "creation did not queue the pinned iOS input")
        [[created_id, kind, state_name]] = jobs()
        require((kind, state_name) == ("created", "available"), "unexpected job after the sole build POST")
        write(root / "build.selection.tmp", scope)
        (root / "build.selection.tmp").rename(root / "build.selection")
        binding = ready("build.binding", processor, 8)
        record, operation = binding["record_id"], binding["operation_id"]
        spec.update({key: scope[key] for key in kit["SPEC_FIELDS"]})
        require(binding["spec"] == dict(spec, build_id=scope["build_id"])
                and binding["ref"] == {key: scope[key] for key in (*kit["SPEC_FIELDS"], "build_id")}
                | {"attempt": 1, "fence": 1}, "paused processor produced a different attempt")
        [[drained_id, _, drained], [start_id, start_kind, start_state]] = jobs()
        require((drained_id, drained, start_kind, start_state) == (created_id, "completed", "start", "available")
                and snapshot()["operations"] is None and not kit["listening"](worker_port),
                "worker dispatch preceded independent custody binding")

        result.update(binding=binding, originalObanJobs={"created": created_id, "start": start_id})
        config = dict(worker_id=worker_id, token=token, tenant=scope["organization_id"], port=worker_port,
                      registration=dict(registration, spec=spec), policy=policy,
                      ios_custodian=dict(operation_id=operation, runtime_sha256=runtime_pins))
        config_path = root / "worker.json"
        config_sha = write(config_path, config)
        result["workerConfigurationSHA256"] = config_sha
        database = state / "operations.sqlite"
        tmp = state / operation / "tmp"
        log_projection = state / ("customer-log-v1-" + operation)
        query = "?" + urlencode(scope)

        def owner_unavailable(cookie):
            paths = [kit["LOGS"]] + ["/console-api/v1/build-artifacts/" + key
                                    for key in kit["ATTACHMENTS"]]
            observed = {path: http(auth, path + query, cookie=cookie)[0] for path in paths}
            require(set(observed.values()) == {404} and not log_projection.exists(),
                    f"owner output published before closure: {observed}")
            return observed

        def launch(stack, label, role, *, stop=None, exit_codes=(0,)):
            return stack.enter_context(owned(
                root, label, [sys.executable, "-IBS", code / "ios_build_custody.py",
                              role, config_path, config_sha, state],
                root, env, commands, stop=stop, exit_codes=exit_codes,
            ))

        def shutdown():
            require(wire(config, "shutdown") == {"status": "closed"}, "authenticated worker shutdown refused")

        result["stage"] = "nested-live-worker-cut"
        with ExitStack() as workers:
            first = launch(workers, "worker-original", "worker", stop=shutdown, exit_codes=(0, -9))
            wait(lambda: kit["listening"](worker_port) and database.is_file(), 5, first)
            ledger = database.stat()
            observer = launch(workers, "independent-parent", "observe")
            mark(root / "processor.run")
            nested_pid = None

            def fixture_entry():
                return db_rows(database, operation)

            def live_operation():
                entry = fixture_entry()
                row, parent, launch, terminal, uncertain, counts = entry
                require(row["starts"] == 1 and row["status"] in ("running", "uncertain")
                        and (parent, launch, terminal, uncertain, counts) ==
                            (observer.pid, launch_id, None, 0, [1, 1])
                        and row["binding"] == {key: binding[key] for key in ("spec", "ref", "deadline_ms")}
                        and "artifacts" not in row and "manifest_sha256" not in row
                        and observer.poll() is None and os.getpgid(cli_pid) == cli_pid,
                        "original start or outstanding outer custody changed")
                return row

            try:
                wait(lambda: (tmp / "fixture-nested-pid").is_file(), 8, observer)
                row, parent, launch_id, terminal, uncertain, counts = fixture_entry()
                nested_pid = int((tmp / "fixture-nested-pid").read_text())
                cli_pid = int((tmp / "fixture-cli-pid").read_text())
                require(row["starts"] == 1 and row["status"] == "running" and counts == [1, 1]
                        and (parent, terminal, uncertain) == (observer.pid, None, 0)
                        and launch_id == dict(pid=cli_pid, pgid=cli_pid, sid=cli_pid)
                        and len({first.pid, observer.pid, cli_pid, nested_pid}) == 4
                        and os.getpgid(cli_pid) == os.getsid(cli_pid) == cli_pid
                        and os.getpgid(nested_pid) == os.getsid(nested_pid) == nested_pid,
                        "original independent parent or nested process identity differs")
                start_guard = row["ios_custody"]["guard"]
                before = kit["running_admission"](snapshot(), binding)
                original_job = start_job()
                require(original_job["id"] == start_id, "original Oban start job changed before cut")
                require(start_guard["owner_id"].startswith(f"oban:{start_id}:"),
                        "the original start guard was not issued to the original Oban job")
                result["beforeCut"] = {"starts": 1, "claimRows": counts[1], "cli": launch_id,
                                       "observerPID": parent, "nestedPID": nested_pid,
                                       "startAdmission": before, "startJob": original_job, "capacityHeld": True}
                cut_at = time.monotonic()
                os.kill(first.pid, signal.SIGKILL)

                def reaped_worker():
                    seen, status = os.waitpid(first.pid, os.WNOHANG)
                    if seen == first.pid:
                        first.returncode = os.waitstatus_to_exitcode(status)
                        return True

                wait(reaped_worker, 3)
                reaped_at_ms = time.time_ns() // 1_000_000
                require(first.returncode == -9 and kit["group_absent"](first.pid)
                        and kit["connect_errno"](worker_port) == errno.ECONNREFUSED
                        and observer.poll() is None and os.getpgid(nested_pid) == nested_pid
                        and os.getpgid(cli_pid) == cli_pid, "worker-only cut did not preserve the active processes")
                result["workerCut"] = {"pid": first.pid, "exit": -9, "directReaped": True,
                                       "groupAbsent": True, "cliAndNestedSurvived": True}
                result["stage"] = "offline-oban-retry-and-plain-bind"
                bind_until = cut_at + REBIND_SECONDS
                offline_guard = live_operation()["guard"]
                outage = result["workerOutage"] = {
                    "deadlineSeconds": REBIND_SECONDS,
                    "reapedAtMS": reaped_at_ms,
                    "firstPlainBindErrno": kit["plain_bind_errno"](worker_port),
                    "connectErrno": errno.ECONNREFUSED,
                }

                def retried_offline():
                    job = start_job()
                    admission = kit["running_admission"](snapshot(), binding)
                    committed = live_operation()
                    require(job["id"] == start_id and os.getpgid(nested_pid) == nested_pid,
                            "worker outage changed the original Oban job or nested child")
                    # Oban snoozes the original job. attempted_at establishes
                    # that it was executed while the socket worker was down.
                    if (job["state"] == "scheduled" and job["attemptedAtMS"] is not None
                            and job["attemptedAtMS"] > reaped_at_ms and admission[5] > before[5]
                            and committed["guard"] == offline_guard):
                        return {"job": job, "admission": admission, "starts": committed["starts"]}

                outage["offlineRetry"] = wait(retried_offline, bind_until - time.monotonic(), processor)
                outage["ownerHTTP"] = owner_unavailable(owner)
                wait(lambda: kit["plain_bind_errno"](worker_port) is None,
                     bind_until - time.monotonic(), processor, interval=0.2)
                outage["plainBindWaitMS"] = round((time.monotonic() - cut_at) * 1000)
                outage["samePortPlainBind"] = True
                outage["admissionBeforeReopen"] = kit["running_admission"](snapshot(), binding)
                require(live_operation()["guard"] == offline_guard and os.getpgid(nested_pid) == nested_pid
                        and kit["connect_errno"](worker_port) == errno.ECONNREFUSED
                        and start_job()["id"] == start_id and kit["sha"](config_path.read_bytes()) == config_sha,
                        "original start, nested process, or configuration changed during the bind wait")

                result["stage"] = "same-ledger-reopen"
                reopened = launch(workers, "worker-reopened", "worker", stop=shutdown)
                wait(lambda: kit["listening"](worker_port), 5, reopened)
                current = database.stat()
                require((current.st_dev, current.st_ino) == (ledger.st_dev, ledger.st_ino)
                        and reopened.pid != first.pid, "restart opened a different ledger or worker identity")

                def resumed():
                    entry = fixture_entry()
                    if entry and entry[0]["guard"]["epoch"] > offline_guard["epoch"]:
                        return entry

                row, parent, reopened_launch, terminal, uncertain, counts = wait(resumed, 8, processor)
                require((row["starts"], row["status"], parent, reopened_launch, terminal, uncertain, counts)
                        == (1, "uncertain", observer.pid, launch_id, None, 0, [1, 1])
                        and row["guard"]["owner_id"].startswith(f"oban:{start_id}:")
                        and row["binding"] == {key: binding[key] for key in ("spec", "ref", "deadline_ms")},
                        "reopen did not reobserve the single unsettled original operation")
                result["reopen"] = {"workerPID": reopened.pid, "sameLedgerInode": True,
                                    "starts": 1, "workerStatus": row["status"], "guard": row["guard"]}
                result["reopen"]["admission"] = kit["running_admission"](snapshot(), binding)
                result["reopen"]["ownerHTTPBeforeNestedAck"] = owner_unavailable(owner)

                result["stage"] = "nested-ack-with-cli-live"
                require(os.getpgid(nested_pid) == nested_pid, "nested child closed before release")
                mark(tmp / "release-nested")
                wait(lambda: (tmp / "cli-closed").is_file(), 4, observer)
                receipt = tmp / (tmp / "cli-closed").read_text() / "command-fixture/receipt.json"
                nested = read(receipt)
                require(nested["pid"] == nested["ownedPGID"] == nested["ownedSession"] == nested_pid
                        and nested["exitCode"] == 0 and nested["released"] is True
                        and all(nested[key] is True for key in ("ownedGroupAbsent", "directChildReaped",
                            "stdoutEOF", "stderrEOF", "descriptorsClosed", "terminalCustody"))
                        and kit["group_absent"](nested_pid),
                        "nested acknowledgement did not leave the original CLI and parent live")
                acknowledged = live_operation()
                admission = kit["running_admission"](snapshot(), binding)
                result["afterNestedAck"] = {"nestedReceiptSHA256": kit["sha"](receipt.read_bytes()),
                                            "nestedGroupAbsent": True, "cliStillLive": True,
                                            "parentStillLive": True, "outerTerminal": None,
                                            "capacityHeld": True, "starts": acknowledged["starts"],
                                            "admission": admission}

                status, _, raw = http(auth, kit["BUILD"] + query, cookie=owner)
                detail = json.loads(raw)["build"]
                require((status, detail["buildId"], detail["platform"], detail["state"], detail["attempt"],
                         detail["revision"], detail["workerCompletionPending"]) ==
                        (200, scope["build_id"], "ios", "running", 1, 1, True)
                        and not detail.get("artifacts"), "owner did not see the original running attempt")
                result["afterNestedAck"]["ownerHTTP"] = owner_unavailable(owner)

                result["stage"] = "same-attempt-customer-cancel"
                mark(root / "api.cancel-auth.request")
                cancel_auth = auth | ready("api.cancel-auth", api, 4)
                result["cancelPOSTs"] += 1
                result["cancelHTTP"] = kit["request_cancel"](cancel_auth, scope)
                owner = cancel_auth["cookie"]

                def stop_intent():
                    entry = fixture_entry()
                    if entry[0].get("tombstone") and (tmp / "cancel-requested").is_file():
                        return entry

                row, _, _, terminal, _, counts = wait(stop_intent, 5, processor)
                cancel_guard = row["guard"]
                current = snapshot()
                require(row["starts"] == 1 and counts == [1, 1] and terminal is None
                        and cancel_guard["revision"] == 2 and cancel_guard["epoch"] > start_guard["epoch"]
                        and current["record"] == [[record, 2]]
                        and current["capacity"] == [[record, 1, 1, True, None]]
                        and current["operations"][0][:5] ==
                            [operation, record, binding["deadline_ms"], "stop_intent", 2]
                        and os.getpgid(cli_pid) == cli_pid and observer.poll() is None,
                        "customer cancellation changed the attempt or released capacity before outer closure")
                result["beforeCLIRelease"] = {"stopGuard": cancel_guard, "heldCapacity": current["capacity"],
                                              "ownerHTTP": owner_unavailable(owner), "outerTerminal": None}

                result["stage"] = "original-parent-and-oban-settlement"
                mark(tmp / "release-cli")
                observer.wait(timeout=6)
                require(observer.returncode == 0 and kit["group_absent"](observer.pid)
                        and kit["group_absent"](cli_pid), "original parent did not close its exact CLI")
                event = "coordinator:1:2:stopped"

                def settled():
                    current = snapshot()
                    if current["jobs"] == [[kind, "completed"] for kind in ("created", "start", "cancel", "stopped")]:
                        return current

                final = wait(settled, 12, processor)
                row, parent, final_launch, terminal, uncertain, counts = fixture_entry()
                final_jobs = jobs()
                cancel_id = final_jobs[2][0]
                guard = row["guard"]
                require(final["record"] == [[record, 3]] and final["capacity"] == [[record, 1, 1, False, event]]
                        and final["leases"] == [[record, None, None]]
                        and final["operations"] == [[operation, record, binding["deadline_ms"], "stop_intent",
                                                     2, guard["epoch"], guard["owner_id"]]]
                        and final_jobs[:2] == [[created_id, "created", "completed"],
                                              [start_id, "start", "completed"]]
                        and guard["owner_id"].startswith(f"oban:{cancel_id}:"),
                        "original Oban jobs or capacity did not settle once under the current cancel lease")
                require((row["starts"], row["status"], parent, final_launch, uncertain, counts)
                        == (1, "stopped", observer.pid, launch_id, 0, [1, 1])
                        and terminal == {"outer": dict(launch_id, parent_pid=observer.pid, exit=0,
                                                      direct_child_reaped=True, group_absent=True,
                                                      descriptors_closed=True),
                                         "nested": {"receipt_root": receipt.parent.parent.name,
                                                    "receipt_sha256s": [result["afterNestedAck"]["nestedReceiptSHA256"]]},
                                         "outcome": "succeeded"},
                        "terminal evidence did not come from the original CLI parent and nested child")
                digest = row["diagnostic_sha256"]
                diagnostic = (state / "blobs" / digest).read_bytes()
                [[start, cancel, stopped]] = json.loads(sql("SELECT json_agg(journal->'events') FROM mixer_builds"))
                require(kit["sha"](diagnostic) == digest
                        and start["event"] == {"type": "start", "ref": binding["ref"]}
                        and (cancel["id"], cancel["event"]) ==
                            ("customer:cancel", {"type": "cancel", "reason": "customer_requested"})
                        and (stopped["id"], stopped["event"]) ==
                            (event, {"type": "stopped", "ref": binding["ref"], "diagnostic_sha256": digest}),
                        "terminal journal did not reference the original attempt and diagnostic")
                result["settled"] = {"jobs": final_jobs, "journal": [start, cancel, stopped],
                                     "reservation": final["capacity"][0], "guard": guard,
                                     "claim": terminal, "diagnosticSHA256": digest, "starts": row["starts"]}
                result["stage"] = "terminal-owner-readback"
                status, _, raw = http(auth, kit["BUILD"] + query, cookie=owner)
                detail = json.loads(raw)["build"]
                require((status, detail["buildId"], detail["state"], detail["attempt"], detail["revision"],
                         detail["workerCompletionPending"]) == (200, scope["build_id"], "cancelled", 1, 3, False),
                        "owner did not observe the original cancelled build")
                log_status, headers, raw = http(auth, kit["LOGS"] + query, cookie=owner)
                result["settled"].update(ownerState=detail["state"], ownerLogHTTP=log_status)
                require(log_status == 200 and {key.lower(): value for key, value in headers.items()}.get(
                    "cache-control") == "no-store",
                        f"terminal owner log returned HTTP {log_status}: {raw!r}")
                logs = json.loads(raw)["buildLogs"]
                require({key: logs[key] for key in ("buildId", "state", "platform", "attempt", "revision", "events")}
                        == {"buildId": scope["build_id"], "state": "cancelled", "platform": "ios",
                            "attempt": 1, "revision": 3, "events": [
                                {"event": "compiler_finished", "exitCode": nested["exitCode"],
                                 "stdoutBytes": nested["stdoutBytes"], "stderrBytes": nested["stderrBytes"],
                                 "tailTruncated": nested["outputTruncated"], "phases": []},
                                {"event": "build_command_finished", "exitCode": terminal["outer"]["exit"]},
                            ]}, "terminal log did not match the original CLI and nested receipts")
                artifacts = {key: http(auth, "/console-api/v1/build-artifacts/" + key + query, cookie=owner)[0]
                             for key in kit["ATTACHMENTS"]}
                require(set(artifacts.values()) == {404} and "artifacts" not in row,
                        "cancelled build exposed artifacts")
                require(snapshot() == final and jobs() == final_jobs and fixture_entry()[0] == row,
                        "terminal readback changed the release, terminal jobs, or worker ledger")
                result["settled"].update(ownerArtifactHTTP=artifacts, ownerLogEvents=logs["events"],
                                         unchangedAfterReadback=True)
            finally:
                if observer.poll() is None and nested_pid is not None:
                    # Let the owned fixture exit through its normal wait/reap path on assertion failures.
                    (tmp / "release-nested").touch(exist_ok=True)
                    (tmp / "release-cli").touch(exist_ok=True)
                if nested_pid is not None:
                    result["fixtureProcessIDs"] = {"nested": nested_pid, "parent": observer.pid}

    result["stage"] = "settled"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--hex-cache", type=Path, default=Path.home() / ".hex")
    parser.add_argument("--mix-archives", type=Path, default=Path.home() / ".mix/archives")
    parser.add_argument("--pg-bin", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin"))
    args = parser.parse_args()
    if args.receipt.exists() or sys.platform != "darwin":
        parser.error("run on macOS and use a new receipt path")

    os.umask(0o077)
    scratch_parent = REPO / "verification/local"
    scratch_parent.mkdir(mode=0o700, exist_ok=True)
    # Match the production retained-log loader's ancestor requirements.
    for directory in (scratch_parent, *scratch_parent.parents):
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, os.getuid()) or info.st_mode & 0o022:
            parser.error(f"untrusted scratch ancestor: {directory}")
    root = Path(tempfile.mkdtemp(prefix="l07-ios-active-", dir=scratch_parent))
    (root / "custody.jsonl").touch()
    result = {"base": BASE, "overlay": OVERLAY, "fixtureSHA256": None, "stage": "private-stage",
              "deliveredFixtureBlob": DELIVERED_FIXTURE_BLOB, "firstReplayReceiptBlob": FIRST_RECEIPT_BLOB,
              "command": [sys.executable, "-B", *sys.argv],
              "inertTimeoutsSeconds": {"barriers": BARRIER_SECONDS, "recipe": INERT_RECIPE_SECONDS},
              "buildPOSTs": 0, "cancelPOSTs": 0, "commands": {}, "passed": False,
              "backend": "inert nested barrier child", "xcodeInvocations": 0, "scratch": str(root)}
    kit = None
    error = None
    try:
        kit = provision(root, args.hex_cache, args.mix_archives, result)
        result["fixtureSHA256"] = kit["sha"](Path(__file__).read_bytes())
        drive(root, kit, environment(root), args.pg_bin, result)
        result["passed"] = True
    except Exception as failure:
        error = failure
        result["failure"] = {"type": type(failure).__name__, "message": str(failure)}
    finally:
        commands = result["commands"]
        unknown = [name for name, command in commands.items() if not command["groupAbsent"]]
        observer = commands.get("independent-parent", {})
        if "independent-parent" in commands and observer.get("exit") not in (0, 3):
            unknown.append("independent CLI or nested child")
        if kit and isinstance(error, kit["CustodyUnknown"]) and not unknown:
            unknown.append("incomplete process ownership observation")
        if unknown:
            result["custodyHold"] = {"preserved": str(root), "unresolved": unknown}
            result["passed"] = False
        else:
            if kit and result.get("ports"):
                try:
                    kit["verify_port_reuse"](result["ports"], result)
                except OSError as cleanup_error:
                    result["portReuseFailure"] = str(cleanup_error)
                    result["passed"] = False
            shutil.rmtree(root)
        result["scratchRemoved"] = not root.exists()
        with args.receipt.open("x") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    if error is not None:
        raise error
    return 0 if result["passed"] else 74


if __name__ == "__main__":
    sys.exit(main())
