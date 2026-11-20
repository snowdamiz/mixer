#!/usr/bin/env python3
"""One local authenticated Android build, with a paused registration boundary."""
import argparse
from contextlib import contextmanager, closing, ExitStack, nullcontext
from dataclasses import asdict
import hashlib
import hmac
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import re
import runpy
import secrets
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PIN = "ffbd472419c4fd5bb3bf32735738155a9caa9cc8"
INERT_LOCK = b"inert Linux lock\n"
INERT_DRIVER_LOG = {"exitCode": 0, "stdoutBytes": 320, "stderrBytes": 80, "outputTruncated": False}
HOST = "127.0.0.1"
DB = "browser_ordinary_installation_r1422"
BUILD = "/console-api/v1/builds"
CANCEL = BUILD + "/cancel"
LOGS = "/console-api/v1/build-logs"
ATTACHMENTS = {
    "unsigned_native_binary": ("application/vnd.android.package-archive", "unsigned.apk"),
    "debug_symbols": ("application/zip", "debug-symbols.zip"),
    "resource_inventory": ("application/json", "resource-inventory.json"),
}
SPEC_FIELDS = ("organization_id", "project_id", "application_id", "platform")
SQL_STATE = """SELECT json_build_object(
  'record', (SELECT json_agg(json_build_array(id, revision)) FROM mixer_builds),
  'jobs', (SELECT json_agg(json_build_array(args->>'kind', state::text) ORDER BY id) FROM oban_jobs),
  'capacity', (SELECT json_agg(json_build_array(build_record_id, attempt, worker_fence, held,
                            terminal_event_id)) FROM mixer_build_reservations),
  'leases', (SELECT json_agg(json_build_array(build_record_id, owner_id, expires_at))
             FROM mixer_build_coordinator_leases),
  'operations', (SELECT json_agg(json_build_array(operation_id, record_id, deadline_ms, admission_state,
                   journal_revision, lease_epoch, owner_id))
                 FROM mixer_build_operation_admissions)
)"""


class CustodyUnknown(RuntimeError):
    pass


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    with path.open("xb") as stream:
        os.fchmod(stream.fileno(), 0o400)
        stream.write(raw)
    return sha(raw)


def read(path):
    return json.loads(path.read_bytes())


def port():
    with socket.socket() as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def wait(pred, seconds, child=None, *, interval=0.05):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if value := pred():
            return value
        require(child is None or child.poll() is None, "owned service exited before readiness")
        time.sleep(interval)
    raise TimeoutError("fixture readiness or settlement deadline expired")


def listening(port_number):
    with socket.socket() as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((HOST, port_number)) == 0


def group_absent(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    return False


@contextmanager
def owned(root, name, argv, cwd, env, receipts, stop=None):
    output = root / (name + ".log")
    with output.open("xb") as log:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        receipts[name] = {"pid": process.pid, "groupAbsent": False}
        try:
            yield process
        finally:
            try:
                if process.poll() is None:
                    if callable(stop):
                        stop()
                    elif stop is not None:
                        process.send_signal(stop)
                code = process.wait(timeout=16)
                wait(lambda: group_absent(process.pid), 4)
            except (OSError, TimeoutError, subprocess.TimeoutExpired) as error:
                raise CustodyUnknown(f"{name} custody unknown for PGID {process.pid}") from error
            receipts[name].update(exit=code, groupAbsent=True, logSHA256=sha(output.read_bytes()))
            if code:
                print(output.read_text(errors="replace")[-3600:], file=sys.stderr)
                raise RuntimeError(f"{name} exited {code}")


def http(auth, path, *, cookie=None, body=None, empty_post=False):
    headers = {}
    if cookie:
        headers["Cookie"] = "__Host-mixer-session=" + cookie
    post = body is not None or empty_post
    if post:
        headers.update({"Origin": auth["origin"], "X-Mixer-CSRF": auth["csrf"]})
    if body is not None:
        headers.update({"Content-Type": "application/json", "Idempotency-Key": "pair25-one-build"})
    with closing(HTTPConnection(HOST, auth["port"], timeout=10)) as connection:
        payload = json.dumps(body) if body is not None else None
        connection.request("POST" if post else "GET", path, payload, headers)
        with connection.getresponse() as response:
            limit = 128 * 1024 * 1024
            payload = response.read(limit + 1)
            require(len(payload) <= limit, "fixture HTTP body exceeds read budget")
            return response.status, dict(response.getheaders()), payload


def wire(config, action, request=None):
    from native_artifact_worker import mac
    from compiler_worker import literal
    nonce = secrets.token_hex(16)
    body = literal({"action": action, "worker_id": config["worker_id"], "request": request})
    frame = literal({"nonce": nonce, "body": body, "mac": mac(config["token"], "request", nonce, body)})
    with socket.create_connection((HOST, config["port"]), timeout=2) as sock:
        sock.sendall(frame.encode() + b"\n")
        with sock.makefile("rb") as stream:
            reply = json.loads(stream.readline(262_145))
    require(hmac.compare_digest(reply["mac"], mac(config["token"], "response", nonce, reply["body"])),
            "worker response authentication failed")
    return json.loads(reply["body"])


def fixtures(source):
    test = source / "test/mixer_hosted/browser_auth/local_starter_http_sql_spec.exs"
    raw = test.read_text()
    require(raw.count("    c\n    |> put_in(\n") == 1, "stock test setup differs")
    raw = raw.replace("    c\n    |> put_in(\n", '    c\n    |> then(fn c -> if System.get_env("PAIR25_RUN"), do: pair25_processor!(c), else: c end)\n    |> put_in(\n')
    closing_line = raw.rindex("\nend\n")
    case = (HERE / "api-case.exs").read_text()
    test.write_text(raw[:closing_line] + "\n" + "\n".join("  " + line if line else "" for line in case.splitlines()) + raw[closing_line:])

    provider = source / "test/support/browser_login_provider_fixture.ex"
    raw = provider.read_text()
    require(raw.count('"sub" => "subject-1"') == 2 and raw.count("  def handle_call(:count") == 1,
            "stock signed issuer fixture differs")
    raw = raw.replace('"sub" => "subject-1"', '"sub" => Map.get(s, :pair25_subject, "subject-1")')
    raw = raw.replace("  def handle_call(:count", """  def handle_call({:pair25_subject, subject}, _, s) when subject in ["subject-1", "subject-2"],
    do: {:reply, :ok, Map.put(s, :pair25_subject, subject)}

  def handle_call(:count""")
    provider.write_text(raw)


def stage(root, env, result):
    receipts = result["commands"]
    result["hostedTree"] = subprocess.check_output(
        ["git", "rev-parse", f"{PIN}:hosted"], cwd=REPO, env=env, text=True, timeout=5,
    ).strip()
    archive = root / "source.tar"
    with archive.open("xb") as stream:
        subprocess.run(["git", "archive", PIN, "hosted", "tests/integration/free-project-starter/registration-runner.py"],
                       cwd=REPO, env=env, stdout=stream, check=True, timeout=20)
    with tarfile.open(archive) as stream:
        stream.extractall(root, filter="data")
    archive.unlink()
    source = root / "hosted"
    fixtures(source)
    sys.path.insert(0, str(source / "priv/development"))
    return source


def compile_hosted(root, source, env, receipts):
    for name, command in (
        ("deps", ["mix", "deps.get", "--check-locked"]),
        ("compile", ["mix", "compile", "--warnings-as-errors"]),
    ):
        with owned(root, name, command, source, env, receipts) as child:
            try:
                child.wait(timeout=100)
            except subprocess.TimeoutExpired as error:
                receipts[name]["timedOut"] = True
                raise CustodyUnknown(f"{name} timed out for PGID {child.pid}") from error
def recipe_inputs(root, args, result):
    recipe_path = root / "recipe.json"
    if args.operator:
        from linux_android_pair25_layout import ARGUMENTS, ENTRYPOINT, PLATFORM, Pair25Layout, unique_object

        operator = json.loads(args.operator.read_bytes(), object_pairs_hook=unique_object)
        required = {"pair25_root", "docker", "daemon_socket", "daemon_id"}
        require(type(operator) is dict and required <= operator.keys() <= required | {"command_timeout", "image_id"},
                "unexpected operator config fields")
        layout = Pair25Layout.read(operator["pair25_root"])
        require(layout.projection_sha256 is not None, "Pair25 stage needs an operator-approved Noble projection")
        require(not layout.root.is_relative_to(root) and not root.is_relative_to(layout.root),
                "operator stage must be separately owned")
        image_id = operator.pop("image_id", layout.image_ids[0])
        require(image_id in layout.image_ids, "operator image ID does not match the approved layout")
        recipe = write(recipe_path, {
            "image": layout.image, "image_id": image_id, "platform": PLATFORM,
            "entrypoint": ENTRYPOINT, "arguments": list(ARGUMENTS),
        })
        result["approvedLayout"] = {"projectionSHA256": layout.projection_sha256, "imageId": image_id,
                                    "volumeName": layout.volume_name, "volumeLabels": layout.volume_labels}
        return {"command_timeout": 0.5, **operator}, layout.verified_inputs, recipe, recipe_path, layout.root / "readonly/Export"
    recipe = write(recipe_path, {"mode": "inert", "compiler": None})
    (root / "export").mkdir(mode=0o700)
    inputs = {
        "linux_lock_sha256": sha(INERT_LOCK),
        "rendered_driver_sha256": sha(b"inert rendered driver"),
        "source_tree_sha256": sha(b"inert source tree"),
    }
    return None, inputs, recipe, recipe_path, root / "export"


def control_runner(root, runner, grant, lock_digest, cancel):
    # The stock socket, guard, durable store and importer surround this inert adapter.
    from linux_android_runner_server import ContainerObservation, open_runner
    from linux_android_runner import RunnerIdentity
    from linux_android_artifact_importer import write_owned
    from compiler_worker import literal

    class InertAdapter:
        terminal = None
        running = False

        def observe(self, identity):
            if self.running:
                return ContainerObservation(identity, "running", False, False)
            return ContainerObservation(identity, "absent", True, True, completion_pending=self.terminal is not None)

        def ensure_started(self, identity, cutoff):
            require(self.terminal is None and cutoff > time.time_ns() // 1_000_000, "invalid inert start")
            if cancel:
                write(root / "inert.start", {"identity": asdict(identity), "cutoff": cutoff})
                self.running = True
                return
            bundle = Path(grant["bundle"])
            bundle.mkdir(mode=0o700)
            apk = b"inert fixture APK bytes\n"
            symbols = b"inert fixture symbols bytes\n"
            inventory = literal({"formatVersion": 1, "apkSHA256": sha(apk), "debugSymbolsSHA256": sha(symbols)}).encode()
            rows = []
            for kind, name, payload in zip(
                ATTACHMENTS, ("fixture-unsigned.apk", "debug-symbols.zip", "resource-inventory.json"),
                (apk, symbols, inventory), strict=True,
            ):
                write_owned(bundle / name, payload)
                rows.append({"kind": kind, "file": name, "sizeBytes": len(payload), "sha256": sha(payload)})
            require(sha(INERT_LOCK) == lock_digest, "inert lock differs")
            write_owned(bundle / "linux-mixer.lock", INERT_LOCK)
            tree = grant["inputs"]["source_tree_sha256"]
            index = literal({"unsigned": True, "zipCRCVerified": True, "artifacts": rows,
                             "androidDriverLog": INERT_DRIVER_LOG,
                             "build": {"source_tree_sha256": tree, "source_tree_after_sha256": tree}}).encode()
            write_owned(bundle / "readback.json", index)
            self.terminal = {"inputs": grant["inputs"], "readback_sha256": sha(index), "exit_code": 0,
                             "start_fenced": True, "container_absent": True,
                             "processes_absent": True, "resources_removed": True}
            write(root / "inert.start", {"identity": asdict(identity), "cutoff": cutoff})

        def stop(self, identity):
            require(cancel and self.running, "inert stop did not observe the original running operation")
            write(root / "inert.stop", {"identity": asdict(identity)})
            self.running = False

        def complete(self, identity, cutoff):
            require(cutoff > time.time_ns() // 1_000_000, "expired inert completion")
            return self.terminal

    identity = RunnerIdentity(**grant["identity"])
    with open_runner(Path(runner["socket_path"]).parent, recipe_sha256=runner["recipe_sha256"],
                     store_id=runner["store_id"], adapter=InertAdapter(), initialize=True,
                     identity_pins={identity.operation_id: identity}, require_start_pin=True) as server:
        until = time.monotonic() + 48
        while not (root / "runner.done").exists() and time.monotonic() < until:
            server.serve_one()


def verify_downloads(auth, scope, sessions, worker_row, driver_log):
    query = "?" + urlencode(scope)
    owner, outsider = sessions["owner"], sessions["outsider"]
    for cookie in (owner, outsider):
        require(http(auth, "/auth/session", cookie=cookie)[0] == 200, "readback session unavailable")
    status, _, raw = http(auth, BUILD + query, cookie=owner)
    require(status == 200 and http(auth, BUILD + query, cookie=outsider)[0] == 404, "detail authorization differs")
    detail = json.loads(raw)["build"]
    require((detail["buildId"], detail["revision"], detail["state"]) ==
            (scope["build_id"], 2, "native_succeeded"), "ordinary build detail differs")
    require([item["kind"] for item in detail["artifacts"]] == list(ATTACHMENTS), "unexpected artifact kinds")
    outputs = []
    for download, worker in zip(detail["artifacts"], worker_row["artifacts"], strict=True):
        kind = download["kind"]
        path = download["downloadPath"]
        media, filename = ATTACHMENTS[kind]
        require(path.startswith("/console-api/v1/build-artifacts/" + kind + "?"), "invalid download route")
        status, headers, data = http(auth, path, cookie=owner)
        denied = http(auth, path, cookie=outsider)[0]
        anonymous = http(auth, path)[0]
        headers = {key.lower(): value for key, value in headers.items()}
        require((status, denied, anonymous) == (200, 404, 401)
                and headers["content-type"] == media
                and headers["content-disposition"] == f'attachment; filename="{filename}"'
                and {key: download[key] for key in worker} == worker
                and (len(data), sha(data)) == (worker["sizeBytes"], worker["sha256"]), "artifact or ACL differs")
        outputs.append(dict(worker, ownerHTTP=status, outsiderHTTP=denied, anonymousHTTP=anonymous))

    status, headers, body = http(auth, LOGS + query, cookie=owner)
    denied = http(auth, LOGS + query, cookie=outsider)[0]
    anonymous = http(auth, LOGS + query)[0]
    require((status, denied, anonymous) == (200, 404, 401),
            f"stock Linux log status differs: owner={status}, outsider={denied}, anonymous={anonymous}")
    require({key.lower(): value for key, value in headers.items()}["cache-control"] == "no-store",
            "stock Linux logs are cacheable")
    parsed = json.loads(body)["buildLogs"]
    expected_events = [
        {"event": "android_driver_finished", "exitCode": 0, "stdoutBytes": driver_log["stdoutBytes"],
         "stderrBytes": driver_log["stderrBytes"], "tailTruncated": driver_log["outputTruncated"], "phases": []},
        {"event": "build_command_finished", "exitCode": 0},
    ]
    require({key: parsed[key] for key in ("buildId", "revision", "state", "platform", "attempt", "events")} ==
            {"buildId": scope["build_id"], "revision": 2, "state": "native_succeeded", "platform": "android",
             "attempt": 1, "events": expected_events}, "stock Linux log events differ from sealed driver readback")
    logs = {"ownerHTTP": status, "outsiderHTTP": denied, "anonymousHTTP": anonymous,
            "events": parsed["events"]}
    return outputs, logs


def journal_rows(path, statement):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)) as journal:
        return journal.execute(statement).fetchall()


@contextmanager
def cancel_container(runner_dir, operator, recipe_path, identity):
    from linux_android_docker_adapter import DockerContainerAdapter, DockerRecipe, socket_identity
    from linux_android_pair25_layout import Pair25Layout

    path = runner_dir / "docker-operations.sqlite"
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)) as journal:
        [(raw,)] = journal.execute("SELECT value FROM configuration").fetchall()
        configuration = json.loads(raw)
        require((configuration["docker"], configuration["socket"], configuration["daemon_id"],
                 configuration["inputs"], configuration["directory"], configuration["recipe_sha256"],
                 configuration["store_id"]) ==
                (operator["docker"], operator["daemon_socket"], operator["daemon_id"],
                 operator["pair25_root"], str(runner_dir), identity.recipe_sha256, identity.store_id)
                and tuple(configuration["socket_identity"]) == socket_identity(Path(operator["daemon_socket"])),
                "observer differs from the runner's pinned Docker configuration")
        layout = Pair25Layout.read(operator["pair25_root"])
        recipe = DockerRecipe.read(recipe_path, identity.recipe_sha256)
        adapter = DockerContainerAdapter(configuration, recipe, operator["command_timeout"], {}, layout)
        adapter.volume_identity = tuple(configuration["pair25"]["volume_identity"])
        adapter.image_env = configuration["pair25"]["image_env"]
        adapter.db = journal
        yield adapter


def observed_frontend(adapter, identity):
    from compiler_worker import Refusal

    try:
        attempt = adapter._attempt(identity)
        require(attempt is not None and attempt.phase == "starting" and attempt.successful_exit == 0,
                "the pinned Docker attempt left its running phase before cancel")
        output = adapter._output(identity)
        require(adapter._output_present(output, attempt), "pinned Docker output is absent before cancel")
        adapter._check_daemon()
        if adapter._container_state(identity, attempt, output)["Status"] != "running":
            return None
        process_table = adapter._docker("container", "top", attempt.container_id, "-ww", "-eo", "pid,comm,args")
        for line in process_table.splitlines()[1:]:
            words = line.split()
            if len(words) < 5 or not words[0].isdigit() or int(words[0]) <= 0:
                continue
            pid, command, executable, *arguments = words
            if command != "swift-frontend" or Path(executable).name != command:
                continue
            for option, target in zip(arguments, arguments[1:]):
                if option == "-target" and re.fullmatch(r"aarch64-unknown-linux-android[0-9]*", target):
                    if adapter._container_state(identity, attempt, output)["Status"] == "running":
                        return {"container": attempt.container_id, "pid": int(pid), "target": target,
                                "executable": executable,
                                "observedAtMS": time.time_ns() // 1_000_000}
    except Refusal:
        # A failed read supplies no evidence. Only a fully matched observation permits the POST.
        return None


def cancel_journals(state, runner_dir, binding, identity):
    rows = journal_rows(state / "operations.sqlite", "SELECT id, value FROM operations")
    operations = journal_rows(runner_dir / "operations.sqlite",
                              "SELECT id, binding, deadline, guard, phase, completed FROM operation")
    if not rows or not operations:
        return None
    [(worker_id, raw)] = rows
    [(runner_id, fingerprint, deadline, guard, phase, completed)] = operations
    row = json.loads(raw)
    original = {key: binding[key] for key in ("ref", "spec", "deadline_ms")}
    require(worker_id == runner_id == identity.operation_id and row["binding"] == original
            and (fingerprint, deadline, completed) == (identity.binding_sha256, binding["deadline_ms"], 0),
            "worker or runner journal changed the original operation")
    return row, json.loads(guard), phase


def original_start(current, identity):
    if current and current[2] == "started":
        row, guard, _ = current
        require((row["starts"], row["status"], row.get("tombstone"), row["linux_runner"]) ==
                (1, "uncertain", None, asdict(identity)) and guard["revision"] == 1,
                "the original start was not durable in both ledgers")
        return guard


def request_cancel(auth, scope):
    status, _, raw = http(auth, CANCEL + "?" + urlencode(scope), cookie=auth["cookie"], empty_post=True)
    require(status == 202, f"ordinary owner cancel returned {status}: {raw!r}")
    response = json.loads(raw)
    detail = response["build"]
    require((response["outcome"], detail["buildId"], detail["state"], detail["revision"],
             detail["attempt"], detail["workerCompletionPending"]) ==
            ("applied", scope["build_id"], "cancelling", 2, 1, True), "cancel response differs")
    return status


def verify_stop(final, sql, journals, start_guard, state, binding, grant, config):
    from linux_android_runner import TERMINAL, VERSION, sha256

    identity = grant["identity"]
    operation, record, deadline = (binding[key] for key in ("operation_id", "record_id", "deadline_ms"))
    row, runner_guard, phase = journals
    worker_guard = row["guard"]
    event_id = "coordinator:1:2:stopped"
    require(final["record"] == [[record, 3]] and final["capacity"] == [[record, 1, 1, False, event_id]]
            and final["leases"] == [[record, None, None]]
            and final["operations"] == [[operation, record, deadline, "stop_intent", 2,
                                         worker_guard["epoch"], worker_guard["owner_id"]]],
            "cancellation did not settle with one matching capacity release and stop intent")
    expected_reply = {
        "request": {"version": VERSION, "action": "stop", "identity": identity,
                    "guard": runner_guard, "deadline_ms": deadline},
        "status": "stopped", "terminal": TERMINAL,
    }
    require(phase == "stopped" and start_guard["epoch"] < runner_guard["epoch"] <= worker_guard["epoch"]
            and runner_guard["record_id"] == worker_guard["record_id"] == record
            and runner_guard["revision"] == worker_guard["revision"] == 2
            and (runner_guard["epoch"] < worker_guard["epoch"]
                 or (runner_guard["owner_id"] == worker_guard["owner_id"]
                     and runner_guard["expires_at"] <= worker_guard["expires_at"]))
            and (row["starts"], row["status"], row.get("tombstone"), row["linux_runner"], row["closure"]) ==
            (1, "stopped", True, identity, expected_reply)
            and "artifacts" not in row and "manifest_sha256" not in row,
            "runner stop and worker tombstone or containment differ")

    digest = row["diagnostic_sha256"]
    require(sha256(digest), "invalid worker closure digest")
    diagnostic = (state / "blobs" / digest).read_bytes()
    require(sha(diagnostic) == digest and json.loads(diagnostic) ==
            {"operation_id": operation, "closure": row["closure"]}, "durable closure proof differs")

    [cancel_job] = json.loads(sql("SELECT json_agg(id) FROM oban_jobs WHERE args->>'kind' = 'cancel'"))
    require(worker_guard["owner_id"].startswith(f"oban:{cancel_job}:"),
            "stop intent did not come from the restricted Oban cancel job")
    records = json.loads(sql("SELECT json_agg(journal->'events') FROM mixer_builds"))
    [[start_event, cancel_event, stop_event]] = records
    require(start_event["event"] == {"type": "start", "ref": binding["ref"]}
            and (cancel_event["id"], cancel_event["event"]) ==
            ("customer:cancel", {"type": "cancel", "reason": "customer_requested"})
            and (stop_event["id"], stop_event["event"]) ==
            (event_id, {"type": "stopped", "ref": binding["ref"], "diagnostic_sha256": digest}),
            "build journal does not tie the capacity release to the original operation and closure")
    require(wire(config, "artifacts", dict(row["binding"], operation_id=operation, guard=worker_guard)) ==
            {"error": "unavailable"}, "stopped worker exposed an artifact")
    bundle = Path(grant["bundle"])
    require(not any(os.path.lexists(path) for path in
                    (bundle, bundle.with_name(f".mixer-l05-{operation}.pending"), state / operation)),
            "cancelled operation materialized an artifact bundle")
    return {"workerStarts": 1, "runnerStarts": 1, "runnerPhase": phase, "workerTombstone": True,
            "stopIntent": final["operations"][0], "cancellationClosure": row["closure"],
            "diagnosticSHA256": digest, "capacityReleased": True, "capacityReleaseEvent": event_id,
            "cancelObanJobID": cancel_job, "settledJobs": final["jobs"], "workerArtifactRequest": "unavailable"}


def verify_container_stop(adapter, identity, frontend):
    attempt = adapter._attempt(identity)
    require(attempt is not None and (attempt.phase, attempt.container_id, attempt.successful_exit) ==
            ("cleaning", frontend["container"], 0)
            and adapter._seal_record(identity) is None
            and not adapter._output_present(adapter._output(identity), attempt),
            "the original Docker attempt was not removed without sealing")
    adapter._confirm_removed(attempt)
    return {"container": attempt.container_id, "containerAbsent": True,
            "ownedOutputRemoved": True, "sealed": False}


def verify_cancelled(auth, scope, sessions):
    query = "?" + urlencode(scope)
    owner, outsider = sessions["owner"], sessions["outsider"]
    status, _, raw = http(auth, BUILD + query, cookie=owner)
    require(status == 200 and http(auth, BUILD + query, cookie=outsider)[0] == 404,
            "cancelled build detail authorization differs")
    detail = json.loads(raw)["build"]
    require((detail["buildId"], detail["revision"], detail["state"], detail["attempt"],
             detail["workerCompletionPending"]) == (scope["build_id"], 3, "cancelled", 1, False)
            and not detail.get("artifacts"), "cancelled build detail differs")
    downloads = {}
    for kind in ATTACHMENTS:
        path = "/console-api/v1/build-artifacts/" + kind + query
        statuses = (http(auth, path, cookie=owner)[0], http(auth, path, cookie=outsider)[0], http(auth, path)[0])
        require(statuses == (404, 404, 401), f"cancelled artifact {kind} response differs: {statuses}")
        downloads[kind] = dict(zip(("ownerHTTP", "outsiderHTTP", "anonymousHTTP"), statuses, strict=True))
    return {"state": detail["state"], "revision": detail["revision"], "artifactHTTP": downloads}


def drive(root, args, env, result):
    receipts = result["commands"]
    source = stage(root, env, result)
    operator, inputs, recipe, recipe_path, export = recipe_inputs(root, args, result)
    compile_hosted(root, source, env, receipts)
    write(root / "inputs.json", dict(inputs, recipe_sha256=recipe))
    result["inputs"] = dict(inputs, recipe_sha256=recipe)
    pg = args.pg_bin
    result["postgres"] = subprocess.check_output([pg / "postgres", "--version"], text=True, timeout=3).strip()
    result["mix"] = subprocess.check_output(["mix", "--version"], env=env, text=True, timeout=5).strip()
    require(" 17." in result["postgres"], "fixture requires PostgreSQL 17")
    opts = source / "priv/development"
    state, runner_dir = root / "worker", root / "r"
    for directory in (state, runner_dir, root / "catalog"):
        directory.mkdir(mode=0o700)
    db_port, worker_port = port(), port()
    require(db_port != worker_port, "listener port collision")
    ports = [db_port, worker_port]
    env.update(MIXER_BROWSER_STORAGE_PORT=str(db_port), MIXER_BROWSER_CATALOG_FIXTURE_ROOT=str(root / "catalog"))
    psql = [pg / "psql", "-XqAtw", "-v", "ON_ERROR_STOP=1", "-h", HOST, "-p", str(db_port), "-U", "fixture_admin"]

    def sql(statement, db=DB):
        return subprocess.check_output([*psql, "-d", db, "-c", statement], text=True, timeout=5,
                                       stderr=subprocess.STDOUT, env=env).strip()

    def ready(name, service, seconds=15):
        path = root / name
        return wait(lambda: read(path) if path.is_file() else None, seconds, service)

    def mark(name):
        (root / name).touch(exist_ok=False)

    def observed_db():
        return json.loads(sql(SQL_STATE))

    with owned(root, "initdb", [pg / "initdb", "-D", root / "pg", "-U", "fixture_admin", "--locale=C",
                               "--encoding=UTF8", "--auth=trust", "--no-sync"], root, env, receipts) as child:
        child.wait(timeout=15)

    rolename = "mixer_build_processor"
    with ExitStack() as services:
        services.enter_context(owned(root, "postgres", [pg / "postgres", "-D", root / "pg", "-h", HOST,
                                     "-p", str(db_port), "-k", "", "-c", "jit=off"],
                                     root, env, receipts, stop=signal.SIGINT))
        wait(lambda: listening(db_port), 8)
        require(sql("SHOW data_directory", "postgres") == str(root / "pg"), "PostgreSQL directory differs")
        registration = root / "tests/integration/free-project-starter/registration-runner.py"
        sql(runpy.run_path(registration)["ROLES"], "postgres")
        api = services.enter_context(owned(root, "api", ["mix", "test", "--no-compile", "--only", "pair25_http",
                        "test/mixer_hosted/browser_auth/local_starter_http_sql_spec.exs"],
                        source, env, receipts, stop=lambda: mark("api.done")))
        auth = ready("api.ready", api, seconds=65)
        ports.extend(auth[key] for key in ("port", "issuer", "jwks"))
        require(len(set(ports)) == len(ports), "fixture listener collision")

        config = {"tenant": auth["build"]["organization_id"], "worker_id": "pair25-native-worker",
                  "port": worker_port, "token": secrets.token_hex(32)}
        proc_env = dict(env, MIXER_HOSTED_ROLE="processor", MIXER_PROCESSOR_PROFILE="builds_v1",
                        MIXER_BUILD_OPERATION_INTENT="durable_intent_v1", MIXER_DATABASE_HOST=HOST,
                        MIXER_DATABASE_NAME=DB, MIXER_DATABASE_USER=rolename, MIXER_DATABASE_PASSWORD="loopback-fixture",
                        MIXER_DATABASE_POOL_SIZE="2", MIXER_QUEUE_BUILDS_CONCURRENCY="1",
                        MIXER_BUILD_DISPATCH="native_development_v1", MIXER_NATIVE_RETAINED_ROOT=str(state),
                        MIXER_NATIVE_WORKER_PORT=str(worker_port), MIXER_NATIVE_WORKER_ID=config["worker_id"],
                        MIXER_NATIVE_WORKER_TOKEN=config["token"])
        with owned(root, "processor", ["mix", "run", "--no-start", "--no-compile", HERE / "processor.exs"],
                   source, proc_env, receipts, stop=lambda: mark("processor.done")) as processor:
            result["processorAdmission"] = ready("processor.ready", processor)
            require(result["processorAdmission"] == {"role": rolename, "paused": True}, "restricted pause differs")
            result["createAttempts"] = 1
            status, _, raw = http(auth, BUILD, cookie=auth["cookie"], body=auth["build"])
            require(status == 201, f"ordinary build create returned {status}: {raw!r}")
            created = json.loads(raw)
            scope = created["selection"]
            require(created["state"] == "queued" and created["outcome"] == "applied"
                    and {k: v for k, v in scope.items() if k != "build_id"} ==
                    {k: v for k, v in auth["build"].items() if k != "source_input_id"},
                    "ordinary create binding differs")
            require(observed_db()["jobs"] == [["created", "available"]], "expected one queued build job")
            write(root / "build.selection", scope)
            binding = ready("build.binding", processor)
            operation = binding["operation_id"]
            spec = {key: scope[key] for key in SPEC_FIELDS}
            spec.update(source={"kind": "revision", "reference": auth["source_reference"],
                                "sha256": inputs["source_tree_sha256"]},
                        toolchain_lock_sha256=inputs["linux_lock_sha256"], build_definition_sha256=recipe)
            require(binding["spec"] == dict(spec, build_id=scope["build_id"])
                    and binding["ref"] == {key: scope[key] for key in (*SPEC_FIELDS, "build_id")} | {"attempt": 1, "fence": 1}
                    and binding["deadline_ms"] == binding["started_at_ms"] + 1_200_000
                    and binding["deadline_ms"] > time.time_ns() // 1_000_000, "durable launch binding differs")
            paused = observed_db()
            require(paused["record"] == [[binding["record_id"], 1]]
                    and paused["jobs"] == [["created", "completed"], ["start", "available"]]
                    and paused["operations"] is None and not listening(worker_port), "worker dispatch preceded binding")
            result["pausedBoundary"] = {"jobs": paused["jobs"], "operationIntents": 0, "workerListening": False}

            from compiler_worker import literal
            from linux_android_runner import RunnerIdentity
            identity = asdict(RunnerIdentity(
                operation, sha(literal({key: binding[key] for key in ("ref", "spec", "deadline_ms")}).encode()),
                recipe, secrets.token_hex(32),
            ))
            result.update(createHTTP=status, pausedBinding=binding, runnerIdentity=identity)
            grant = {"identity": identity, "bundle": str(root / "bundle"), "inputs": inputs}
            runner = {"socket_path": str(runner_dir / "runner.sock"), "recipe_sha256": recipe,
                      "store_id": identity["store_id"]}
            config.update(registration={"spec": spec, "root": str(export), "recipe": str(recipe_path), "files": {}},
                          linux_runner=runner, linux_artifact_imports={operation: grant})
            config_path = root / "worker.json"
            worker_pin = write(config_path, config)
            if operator:
                runner_path = root / "runner.json"
                runner_pin = write(runner_path, dict(operator, directory=str(runner_dir), manifest=str(recipe_path), recipe_sha256=recipe,
                                                    store_id=runner["store_id"], completions={operation: grant}))
                result["runnerConfigSHA256"] = runner_pin
                runner_cli = opts / "linux_android_runner_cli.py"
                prefix = [sys.executable, "-B", runner_cli]
                with owned(root, "runner-init", [*prefix, "initialize", runner_path, runner_pin],
                           root, env, receipts) as child:
                    child.wait(timeout=15)
                runner_command = [*prefix, "serve", runner_path, runner_pin]
                stop_runner = signal.SIGTERM
            else:
                runner_command = [sys.executable, "-B", HERE / "run.py", "--inert-child", root, opts]
                stop_runner = lambda: mark("runner.done")

            result["workerConfigSHA256"] = worker_pin
            runner_process = services.enter_context(owned(root, "runner", runner_command, root, env, receipts, stop_runner))
            wait(lambda: Path(runner["socket_path"]).is_socket(), 8, runner_process)
            worker_command = [sys.executable, "-B", opts / "native_artifact_worker.py", config_path, worker_pin, state]

            def stop_worker():
                require(wire(config, "shutdown") == {"status": "closed"}, "worker shutdown refused")

            with owned(root, "worker", worker_command, root, env, receipts, stop_worker) as worker:
                wait(lambda: listening(worker_port), 8, worker)
                result["nativeDispatchPossible"] = bool(operator)
                mark("processor.run")

                if args.cancel:
                    runner_identity = RunnerIdentity(**identity)
                    deadline = binding["deadline_ms"]
                    record = binding["record_id"]
                    until = time.monotonic() + args.seconds

                    def journals():
                        require(worker.poll() is None and runner_process.poll() is None,
                                "worker or runner exited during cancel")
                        return cancel_journals(state, runner_dir, binding, runner_identity)

                    guard = wait(lambda: original_start(journals(), runner_identity),
                                 until - time.monotonic(), processor)
                    before = observed_db()
                    require(before["record"] == [[record, 1]] and before["capacity"] == [[record, 1, 1, True, None]]
                            and [row[:5] for row in before["operations"]] == [[operation, record, deadline, "admitted", 1]],
                            "the running attempt must hold its original capacity and admission")
                    result["runningReservation"] = before["capacity"][0]
                    mark("api.cancel-auth.request")
                    cancel_auth = auth | ready("api.cancel-auth", api)
                    observer = cancel_container(runner_dir, operator, recipe_path, runner_identity) if operator else nullcontext()
                    with observer as adapter:
                        if adapter:
                            result["frontendBeforeCancel"] = wait(
                                lambda: observed_frontend(adapter, runner_identity),
                                until - time.monotonic(), processor, interval=0.2,
                            )
                        else:
                            start = read(root / "inert.start")
                            require(start["identity"] == identity and start["cutoff"] <= min(deadline, guard["expires_at"]),
                                    "inert adapter did not receive the original guarded start")
                            result["inertStart"] = start
                        result["cancelAttempts"] = 1
                        result["cancelRequestedAtMS"] = time.time_ns() // 1_000_000
                        result.update(cancelHTTP=request_cancel(cancel_auth, scope), cancellationExercised=True)

                        def cancelled():
                            current = observed_db()
                            if current["jobs"] == [[kind, "completed"] for kind in ("created", "start", "cancel", "stopped")]:
                                return current

                        final = wait(cancelled, max(1, until - time.monotonic()), processor)
                        result.update(verify_stop(final, sql, journals(), guard, state, binding, grant, config))
                        if adapter:
                            result["liveClosure"] = verify_container_stop(
                                adapter, runner_identity, result["frontendBeforeCancel"],
                            )
                        else:
                            stop = read(root / "inert.stop")
                            require(stop == {"identity": identity}, "inert adapter stopped a different operation")
                            result["inertStop"] = stop
                    result["nativeDispatchResolved"] = True
                else:
                    def settled():
                        require(worker.poll() is None and runner_process.poll() is None,
                                "worker or runner exited before settlement")
                        snapshot = observed_db()
                        if snapshot["jobs"] == [["created", "completed"], ["start", "completed"], ["completed", "completed"]]:
                            return snapshot
                        return None

                    final = wait(settled, args.seconds, processor)
                    require(final["record"] == [[binding["record_id"], 2]]
                            and final["capacity"] == [[binding["record_id"], 1, 1, False, "coordinator:1:1:completed"]]
                            and final["leases"] == [[binding["record_id"], None, None]], "settlement or release differs")
                    with closing(sqlite3.connect(state / "operations.sqlite")) as journal:
                        [(row_id, raw)] = journal.execute("SELECT id, value FROM operations").fetchall()
                    row = json.loads(raw)
                    require(row_id == operation and row["linux_runner"] == identity
                            and row["binding"] == {key: binding[key] for key in ("ref", "spec", "deadline_ms")}
                            and (row["starts"], row["status"]) == (1, "native_ready"), "worker journal differs")
                    with closing(sqlite3.connect(runner_dir / "operations.sqlite")) as journal:
                        [(row_id, fingerprint, deadline, guard_raw, phase, completed)] = journal.execute(
                            "SELECT id, binding, deadline, guard, phase, completed FROM operation"
                        ).fetchall()
                    guard = json.loads(guard_raw)
                    worker_guard = row["guard"]
                    require((row_id, fingerprint, deadline, phase, completed) ==
                            (operation, identity["binding_sha256"], binding["deadline_ms"], "started", 1)
                            and guard["record_id"] == worker_guard["record_id"] == binding["record_id"]
                            and guard["revision"] == worker_guard["revision"] == 1
                            and (guard["epoch"], guard["expires_at"]) <=
                            (worker_guard["epoch"], worker_guard["expires_at"]),
                            "runner v1 operation or guard order differs from worker")
                    require(final["operations"] == [[operation, binding["record_id"], deadline, "admitted",
                                                     worker_guard["revision"], worker_guard["epoch"], worker_guard["owner_id"]]],
                            "worker lease guard differs from restricted durable PostgreSQL intent")
                    result.update(runnerGuard=guard, finalWorkerGuard=worker_guard, workerStarts=1,
                                  runnerCompleted=True, capacityReleased=True)
                    readback = (Path(grant["bundle"]) / "readback.json").read_bytes()
                    driver_log = json.loads(readback)["androidDriverLog"]
                    if operator:
                        from linux_android_docker_adapter import DockerContainerAdapter
                        output = Path(operator["pair25_root"]) / "outputs" / DockerContainerAdapter._name(
                            RunnerIdentity(**identity)
                        )
                        with closing(sqlite3.connect(runner_dir / "docker-operations.sqlite")) as journal:
                            [(row_id, fingerprint, phase, container, successful)] = journal.execute(
                                "SELECT operation, binding, phase, cid, successful_exit FROM attempt"
                            ).fetchall()
                            [(sealed_id, readback_sha)] = journal.execute("SELECT operation, readback FROM seal").fetchall()
                        require((row_id, fingerprint, phase, successful) ==
                                (operation, identity["binding_sha256"], "cleaning", 1)
                                and container and sealed_id == operation
                                and sha(readback) == readback_sha
                                and not os.path.lexists(output),
                                "the one live attempt did not seal and remove its owned resources")
                        result["liveClosure"] = {"container": container, "readbackSHA256": readback_sha,
                                                 "successfulAttempts": 1, "ownedOutputRemoved": True}
                    if not operator:
                        require(driver_log == INERT_DRIVER_LOG, "inert driver readback counters differ")
                        start = read(root / "inert.start")
                        require(start["identity"] == identity and start["cutoff"] <= min(deadline, guard["expires_at"]),
                                "inert adapter did not receive the guarded operation")
                        result["inertStart"] = start
                        request = dict(row["binding"], operation_id=operation, guard=worker_guard)
                        require(wire(config, "query", dict(request, deadline_ms=deadline + 1)) == {"error": "unavailable"}
                                and wire(config, "query", dict(request, guard=dict(worker_guard, expires_at=1))) ==
                                {"error": "stale"}, "worker admitted a changed deadline or expired guard")
                        result["changedDeadlineAndExpiredGuardRefused"] = True
                    result["nativeDispatchResolved"] = True

            mark("api.refresh")
            sessions = ready("api.sessions", api)
            if args.cancel:
                result["cancelledBuild"] = verify_cancelled(auth, scope, sessions)
            else:
                result["downloads"], result["logs"] = verify_downloads(
                    auth, scope, sessions, row, driver_log,
                )

    require(not Path(runner["socket_path"]).exists(), "runner socket was retained")
    with ExitStack() as stack:
        for selected in ports:
            sock = stack.enter_context(socket.socket())
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((HOST, selected))
            sock.listen(1)
    result["portsReusable"] = ports


def main():
    if sys.argv[1:2] == ["--inert-child"]:
        root, code = map(Path, sys.argv[2:])
        sys.path.insert(0, str(code))
        config = read(root / "worker.json")
        [grant] = config["linux_artifact_imports"].values()
        control_runner(root, config["linux_runner"], grant, grant["inputs"]["linux_lock_sha256"],
                       cancel=os.environ.get("PAIR25_CANCEL") == "1")
        return

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", required=True, type=Path, help="existing private-parent path on this host")
    parser.add_argument("--pg-bin", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin"))
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--operator", type=Path, help="real Pair25 stage/daemon operator JSON; omitted for inert replay")
    parser.add_argument("--cancel", action="store_true", help="cancel the original operation while it is running")
    parser.add_argument("--seconds", type=int, default=30, help="settlement budget, at most 1,150 seconds")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 1150:
        parser.error("use a settlement budget between 1 and 1,150 seconds")
    require(not args.receipt.exists(), "receipt already exists")
    os.umask(0o077)
    root = Path(tempfile.mkdtemp(prefix="p25-", dir=args.scratch.resolve(strict=True)))
    result = {"productPin": PIN, "mode": "real" if args.operator else "inert", "python": sys.version,
              "fixtureSHA256": {name: sha((HERE / name).read_bytes())
                                for name in ("run.py", "processor.exs", "api-case.exs")},
              "commands": {}, "cancellationExercised": False, "nativeDispatchPossible": False}
    env = {key: os.environ[key] for key in ("PATH", "HOME", "MIX_HOME", "HEX_HOME") if key in os.environ}
    env.update(MIX_ENV="test", HEX_OFFLINE="1", GIT_NO_LAZY_FETCH="1", LC_ALL="C", TMPDIR=str(root),
               PAIR25_RUN=str(root), PYTHONDONTWRITEBYTECODE="1", PYTHONOPTIMIZE=str(sys.flags.optimize))
    if args.cancel:
        env["PAIR25_CANCEL"] = "1"
    try:
        require(len(os.fsencode(root / "r/runner.sock")) < 103, "scratch path exceeds Unix socket budget")
        drive(root, args, env, result)
        result["passed"] = True
    finally:
        unresolved = result["nativeDispatchPossible"] and not result.get("nativeDispatchResolved")
        unknown = any(not meta["groupAbsent"] for meta in result["commands"].values())
        if unknown or unresolved:
            result["scratchHeld"] = str(root)
        else:
            shutil.rmtree(root)
            result["scratchRemoved"] = True
        write(args.receipt, result)


if __name__ == "__main__":
    main()
