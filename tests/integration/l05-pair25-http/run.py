#!/usr/bin/env python3
"""One local authenticated Android build, with a paused registration boundary."""
import argparse
from contextlib import contextmanager, closing, ExitStack, nullcontext
from dataclasses import asdict
import errno
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
from urllib.parse import parse_qs, urlencode, urlsplit

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PIN = "ffbd472419c4fd5bb3bf32735738155a9caa9cc8"
RECOVERY_PIN = "11b9cb43e3d90de5580efda9b9e2e3a47e387be3"
STARTER_PIN = "f6577616a8394ca1104f2ba8c430d7ac124ea095"
BROWSER_PIN = "26000a3fa85a96e5e1e13df221528ac7df8b9add"
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
DETAIL_SCOPE = {"organizationId": "organization_id", "projectId": "project_id",
                "applicationId": "application_id", "buildId": "build_id", "platform": "platform",
                "sourceSha256": "source_sha256", "toolchainLockSha256": "toolchain_lock_sha256",
                "buildDefinitionSha256": "build_definition_sha256"}
COMPLETED_JOBS = [[kind, "completed"] for kind in ("created", "start", "completed")]
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


def connect_errno(port_number):
    with socket.socket() as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((HOST, port_number))


def listening(port_number):
    return connect_errno(port_number) == 0


def group_absent(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    return False


def record_custody(root, label, process, *, closed):
    journal = root / "custody.jsonl"
    if journal.is_file():
        with journal.open("a") as stream:
            print(json.dumps({"label": label, "pid_pgid": process.pid, "closed": closed}), file=stream)
            stream.flush()
            os.fsync(stream.fileno())


@contextmanager
def owned(root, name, argv, cwd, env, receipts, stop=None, *, exit_codes=(0,)):
    output = root / (name + ".log")
    with output.open("xb") as log:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        receipts[name] = {"pid": process.pid, "groupAbsent": False}
        try:
            record_custody(root, name, process, closed=False)
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
            record_custody(root, name, process, closed=True)
            if code not in exit_codes:
                if not env.get("PAIR25_BROWSER") or name in {"deps", "compile", "console-deps", "console-bundle"}:
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


def release_snapshot(configuration):
    snapshot = {}
    for kind in ("offer", "artifact"):
        observation = configuration[kind]
        target = urlsplit(observation["url"])
        require(target.scheme == "http" and target.hostname == HOST and target.port
                and target.netloc == f"{HOST}:{target.port}" and target.path.startswith("/v3/")
                and not target.fragment, "release probe must use a pinned IPv4 loopback route")
        with closing(HTTPConnection(HOST, target.port, timeout=1)) as connection:
            connection.request("GET", target.path + ("?" + target.query if target.query else ""))
            with connection.getresponse() as response:
                raw = response.read(65_537)
        require(response.status == 200 and len(raw) <= 65_536 and sha(raw) == observation["sha256"],
                f"committed release {kind} changed")
        snapshot[kind] = {"http": response.status, "bytes": len(raw), "sha256": sha(raw)}
    return snapshot


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
    pin = result["productPin"]
    result["hostedTree"] = subprocess.check_output(
        ["git", "rev-parse", f"{pin}:hosted"], cwd=REPO, env=env, text=True, timeout=5,
    ).strip()
    archive = root / "source.tar"
    paths = ["hosted", "tests/integration/free-project-starter/registration-runner.py"]
    if result.get("browser"):
        paths.append("console")
        result["consoleTree"] = subprocess.check_output(
            ["git", "rev-parse", f"{pin}:console"], cwd=REPO, env=env, text=True, timeout=5,
        ).strip()
    with archive.open("xb") as stream:
        subprocess.run(["git", "archive", pin, *paths],
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


def control_runner(root, runner, grant, lock_digest, cancel, seconds):
    # The stock socket, guard, durable store and importer surround this inert adapter.
    from linux_android_runner_server import ContainerObservation, open_runner
    from linux_android_runner import RunnerIdentity
    from linux_android_artifact_importer import write_owned
    from compiler_worker import literal

    class InertAdapter:
        terminal = None
        running = False

        def observe(self, identity):
            if self.running and (root / "inert.finish-after-reopen").is_file():
                self.finish()
                self.running = False
            if self.running:
                return ContainerObservation(identity, "running", False, False)
            return ContainerObservation(identity, "absent", True, True, completion_pending=self.terminal is not None)

        def ensure_started(self, identity, cutoff):
            require(self.terminal is None and cutoff > time.time_ns() // 1_000_000, "invalid inert start")
            write(root / "inert.start", {"identity": asdict(identity), "cutoff": cutoff})
            self.running = cancel
            if not cancel:
                self.finish()

        def finish(self):
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
        until = time.monotonic() + seconds
        while not (root / "runner.done").exists() and time.monotonic() < until:
            server.serve_one()


def verify_downloads(auth, scope, sessions, worker_row, driver_log):
    query = "?" + urlencode(scope)
    owner, outsider = sessions["owner"], sessions["outsider"]
    for cookie in (owner, outsider):
        require(http(auth, "/auth/session", cookie=cookie)[0] == 200, "readback session unavailable")
    status, _, raw = http(auth, BUILD + query, cookie=owner)
    denied = http(auth, BUILD + query, cookie=outsider)[0]
    anonymous = http(auth, BUILD + query)[0]
    require((status, denied, anonymous) == (200, 404, 401), "detail authorization differs")
    detail = json.loads(raw)["build"]
    terminal = {field: detail[field] for field in (*DETAIL_SCOPE, "revision", "state", "attempt")}
    require(terminal == {field: scope[key] for field, key in DETAIL_SCOPE.items()} |
            {"revision": 2, "state": "native_succeeded", "attempt": 1}, "ordinary build detail differs")
    terminal.update(ownerHTTP=status, outsiderHTTP=denied, anonymousHTTP=anonymous)
    require([item["kind"] for item in detail["artifacts"]] == list(ATTACHMENTS), "unexpected artifact kinds")
    outputs = []
    for download, worker in zip(detail["artifacts"], worker_row["artifacts"], strict=True):
        kind = download["kind"]
        path = download["downloadPath"]
        media, filename = ATTACHMENTS[kind]
        route, _, route_query = path.partition("?")
        require(route == "/console-api/v1/build-artifacts/" + kind
                and parse_qs(route_query) == {key: [value] for key, value in scope.items()},
                "download route differs from the original selection")
        status, headers, data = http(auth, path, cookie=owner)
        denied = http(auth, path, cookie=outsider)[0]
        anonymous = http(auth, path)[0]
        headers = {key.lower(): value for key, value in headers.items()}
        require((status, denied, anonymous) == (200, 404, 401)
                and headers["content-type"] == media
                and headers["content-disposition"] == f'attachment; filename="{filename}"'
                and {key: download[key] for key in worker} == worker
                and (len(data), sha(data)) == (worker["sizeBytes"], worker["sha256"]), "artifact or ACL differs")
        outputs.append(dict(worker, ownerHTTP=status, outsiderHTTP=denied, anonymousHTTP=anonymous,
                            contentType=media, contentDisposition=headers["content-disposition"]))

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
    return outputs, logs, terminal


def journal_rows(path, statement):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)) as journal:
        return journal.execute(statement).fetchall()


def runner_journal(runner_dir):
    return journal_rows(runner_dir / "operations.sqlite",
                        "SELECT id, binding, deadline, guard, phase, completed FROM operation")


@contextmanager
def docker_observer(runner_dir, operator, recipe_path, identity):
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
        if attempt is None or attempt.phase != "starting" or attempt.successful_exit != 0:
            return None
        output = adapter._output(identity)
        if not adapter._output_present(output, attempt):
            return None
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


def cancel_journals(state, runner_dir, binding, identity, *, allow_completed=False):
    rows = journal_rows(state / "operations.sqlite", "SELECT id, value FROM operations")
    operations = runner_journal(runner_dir)
    if not rows or not operations:
        return None
    [(worker_id, raw)] = rows
    [(runner_id, fingerprint, deadline, guard, phase, completed)] = operations
    row = json.loads(raw)
    original = {key: binding[key] for key in ("ref", "spec", "deadline_ms")}
    require(worker_id == runner_id == identity.operation_id and row["binding"] == original
            and (fingerprint, deadline) == (identity.binding_sha256, binding["deadline_ms"])
            and (completed == 0 or (allow_completed and completed == 1)),
            "worker or runner journal changed the original operation")
    return row, json.loads(guard), phase


def original_start(current, identity):
    if current and current[2] == "started":
        row, guard, _ = current
        require((row["starts"], row["status"], row.get("tombstone"), row["linux_runner"]) ==
                (1, "uncertain", None, asdict(identity)) and guard["revision"] == 1,
                "the original start was not durable in both ledgers")
        return guard


def running_admission(snapshot, binding):
    record, operation, deadline = (binding[key] for key in ("record_id", "operation_id", "deadline_ms"))
    [admission] = snapshot["operations"]
    require(snapshot["record"] == [[record, 1]] and snapshot["capacity"] == [[record, 1, 1, True, None]]
            and admission[:5] == [operation, record, deadline, "admitted", 1],
            "the running attempt must hold its original capacity and admission")
    return admission


def verify_running(auth, scope, sessions):
    owner, outsider = sessions["owner"], sessions["outsider"]
    for cookie in (owner, outsider):
        status, _, raw = http(auth, "/auth/session", cookie=cookie)
        require(status == 200 and json.loads(raw)["state"] == "authenticated",
                "live console session unavailable during recovery")
    query = "?" + urlencode(scope)
    status, _, raw = http(auth, BUILD + query, cookie=owner)
    statuses = (status, http(auth, BUILD + query, cookie=outsider)[0], http(auth, BUILD + query)[0])
    require(statuses == (200, 404, 401), f"live build detail authorization differs: {statuses}")
    detail = json.loads(raw)["build"]
    expected = {"organizationId": scope["organization_id"], "projectId": scope["project_id"],
                "applicationId": scope["application_id"], "buildId": scope["build_id"],
                "platform": "android", "revision": 1, "state": "running", "attempt": 1,
                "workerCompletionPending": True}
    require({key: detail[key] for key in expected} == expected and not detail.get("artifacts"),
            "live console detail changed scope, attempt, or advertised an artifact")
    log_statuses = tuple(http(auth, LOGS + query, cookie=cookie)[0] for cookie in (owner, outsider, None))
    require(log_statuses == (404, 404, 401), f"running build exposed logs: {log_statuses}")
    return {"detail": expected, "detailHTTP": statuses, "logsHTTP": log_statuses,
            "artifactHTTP": verify_no_downloads(query, auth, owner, outsider)}


def read_recovery_detail(auth, scope, sessions, receipt, key):
    # Store the first owner's response before validation or additional HTTP calls.
    observation = receipt[key] = {"requestedAtMS": time.time_ns() // 1_000_000}
    query = "?" + urlencode(scope)
    status, _, raw = http(auth, BUILD + query, cookie=sessions["owner"])
    observation.update(ownerHTTP=status, responseAtMS=time.time_ns() // 1_000_000)
    if status == 200:
        try:
            decoded = json.loads(raw)
        except (ValueError, RecursionError):
            observation["invalidJSON"] = True
            return observation
        detail = decoded.get("build") if isinstance(decoded, dict) else None
        if isinstance(detail, dict):
            def scalar(value):
                return value if value is None or type(value) in (int, bool) or (
                    isinstance(value, str) and len(value) <= 128 and value.isprintable()
                ) else "<invalid>"

            fields = (*DETAIL_SCOPE, "revision", "state", "attempt", "workerCompletionPending", "failureCode")
            observation["detail"] = {field: scalar(detail[field]) if field in detail else "<missing>"
                                     for field in fields}
            artifacts = detail.get("artifacts", [])
            observation["artifactCount"] = len(artifacts) if isinstance(artifacts, list) else None
            if isinstance(artifacts, list):
                observation["artifactKinds"] = [scalar(item.get("kind")) if isinstance(item, dict) else None
                                                for item in artifacts[:len(ATTACHMENTS)]]
    return observation


def verify_recovery_detail(observation, scope):
    detail = observation.get("detail", {})
    require(observation["ownerHTTP"] == 200
            and all(detail.get(field) == scope[key] for field, key in DETAIL_SCOPE.items())
            and type(detail.get("attempt")) is int and detail["attempt"] == 1
            and type(detail.get("revision")) is int and detail.get("failureCode") is None,
            "post-reopen owner detail failed its original scope or attempt check")
    if (detail["state"], detail["revision"], detail["workerCompletionPending"], observation["artifactCount"]) == (
            "running", 1, True, 0) and detail["workerCompletionPending"] is True:
        return "running"
    if ((detail["state"], detail["revision"], detail["workerCompletionPending"]) == ("native_succeeded", 2, False)
            and detail["workerCompletionPending"] is False and observation["artifactCount"] == len(ATTACHMENTS)
            and observation["artifactKinds"] == list(ATTACHMENTS)):
        return "native_succeeded"
    raise RuntimeError("unexpected post-reopen owner build state or artifacts")


def plain_bind_errno(port_number):
    # Match the stock TCPServer's bind options. SO_REUSEADDR can give a false pass here.
    with socket.socket() as probe:
        try:
            probe.bind((HOST, port_number))
        except OSError as error:
            if error.errno != errno.EADDRINUSE:
                raise
            return error.errno
    return None


def request_cancel(auth, scope, *, allow_completion_conflict=False):
    status, _, raw = http(auth, CANCEL + "?" + urlencode(scope), cookie=auth["cookie"], empty_post=True)
    if allow_completion_conflict and status == 409:
        require(json.loads(raw).get("error", {}).get("code") == "conflict", "unexpected cancel conflict")
        return status
    require(status == 202, f"ordinary owner cancel returned {status}")
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
    require_no_bundle(state, grant)
    return {"workerStarts": 1, "runnerStarts": 1, "runnerPhase": phase, "workerTombstone": True,
            "stopIntent": final["operations"][0], "cancellationClosure": row["closure"],
            "diagnosticSHA256": digest, "capacityReleased": True, "capacityReleaseEvent": event_id,
            "cancelObanJobID": cancel_job, "settledJobs": final["jobs"], "workerArtifactRequest": "unavailable"}


def require_no_bundle(state, grant):
    bundle = Path(grant["bundle"])
    operation = grant["identity"]["operation_id"]
    require(not any(os.path.lexists(path) for path in
                    (bundle, bundle.with_name(f".mixer-l05-{operation}.pending"), state / operation)),
            "operation materialized an unexpected artifact bundle")


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


def verify_container_success(adapter, identity, frontend, readback_sha):
    attempt = adapter._attempt(identity)
    seal = adapter._seal_record(identity)
    require(attempt is not None and (attempt.phase, attempt.container_id, attempt.successful_exit) ==
            ("cleaning", frontend["container"], 1)
            and seal is not None and seal.readback == readback_sha
            and not adapter._output_present(adapter._output(identity), attempt),
            "the original Docker attempt did not exit successfully, seal its readback, and remove its output")
    require(adapter.db.execute("SELECT operation FROM attempt").fetchall() == [(identity.operation_id,)]
            and adapter.db.execute("SELECT operation FROM seal").fetchall() == [(identity.operation_id,)],
            "Docker journals contain an additional attempt or seal")
    adapter._confirm_removed(attempt)
    return {"container": attempt.container_id, "exitCode": 0, "containerAbsent": True,
            "readbackSHA256": readback_sha, "successfulAttempts": 1, "ownedOutputRemoved": True}


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
    return {"state": detail["state"], "revision": detail["revision"],
            "artifactHTTP": verify_no_downloads(query, auth, owner, outsider)}


def verify_no_downloads(query, auth, owner, outsider):
    downloads = {}
    for kind in ATTACHMENTS:
        path = "/console-api/v1/build-artifacts/" + kind + query
        statuses = (http(auth, path, cookie=owner)[0], http(auth, path, cookie=outsider)[0], http(auth, path)[0])
        require(statuses == (404, 404, 401), f"unavailable artifact {kind} response differs: {statuses}")
        downloads[kind] = dict(zip(("ownerHTTP", "outsiderHTTP", "anonymousHTTP"), statuses, strict=True))
    return downloads


def compile_console(root, args, env, result):
    import browser

    console = root / "console"
    cache = root / "npm-cache"
    dist = root / "dist"
    result["node"] = subprocess.check_output(["node", "--version"], env=env, text=True, timeout=5).strip()
    result["npm"] = subprocess.check_output(["npm", "--version"], env=env, text=True, timeout=5).strip()
    result["npmCacheSeedBytes"] = browser.seed_npm_cache(console / "package-lock.json", args.npm_cache, cache)
    npm_env = dict(env, NPM_CONFIG_CACHE=str(cache), NPM_CONFIG_OFFLINE="true",
                   NPM_CONFIG_UPDATE_NOTIFIER="false", NPM_CONFIG_USERCONFIG=os.devnull)
    for name, command, seconds in (
        ("console-deps", ["npm", "ci", "--offline", "--ignore-scripts", "--no-audit", "--no-fund"], 45),
        ("console-bundle", ["node", "node_modules/vite/bin/vite.js", "build", "--mode", "local-workspace-builds",
                            "--configLoader", "runner", "--outDir", str(dist)], 35),
    ):
        with owned(root, name, command, console, npm_env, result["commands"], stop=signal.SIGTERM) as child:
            child.wait(timeout=seconds)
    result["consoleAssets"] = {
        str(path.relative_to(dist)): sha(path.read_bytes())
        for path in sorted(dist.rglob("*")) if path.is_file()
    }
    require("index.html" in result["consoleAssets"]
            and any(name.endswith(".js") for name in result["consoleAssets"]), "console bundle is incomplete")
    return dist


def verify_port_reuse(ports, result):
    with ExitStack() as stack:
        for selected in ports:
            sock = stack.enter_context(socket.socket())
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((HOST, selected))
            sock.listen(1)
    result["portsReusable"] = ports


def browser_run(root, args, dist, auth, api, sql, worker_port, ports, result):
    import browser

    selection = result["browser"]
    expected = auth["build"]
    require(sql("SELECT count(*) FROM mixer_customer_build_inputs") == "0"
            and sql("SELECT count(*) FROM mixer_managed_linux_pair25_starters") == "1",
            "browser requires one managed registration and zero verified inputs")
    selection.update(verifiedInputsBefore=0, registeredStarters=1, workerListeningBefore=False,
                     createAttempts=0, http=[])
    queue = args.browser != "select"
    evidence = browser.BrowserEvidence(expected, selection)
    with browser.bridge(dist, auth, evidence, queue) as (bridge_port, url):
        require(bridge_port not in ports, "browser listener collision")
        ports.append(bridge_port)
        if args.browser == "smoke":
            browser.smoke(bridge_port, url, evidence.scope)
            selection["finish"] = "http-smoke"
        else:
            handoff = root / "browser.private.json"
            done = root / "browser.done"
            window = selection["windowSeconds"]
            write(handoff, {"url": url, "finishFile": str(done), "starterId": auth["starter"]["id"],
                            "scope": evidence.scope, "seconds": window})
            print(f"Pair25 private browser handoff file {handoff}", flush=True)
            try:
                wait(done.is_file, window, api, interval=0.2)
                selection["finish"] = "operator"
            except TimeoutError:
                selection["finish"] = "deadline"

    snapshot = json.loads(sql(SQL_STATE))
    rows = json.loads(sql("""
        SELECT coalesce(json_agg(json_build_array(
          organization_id,project_id,application_id,platform,input_id,source_kind,source_reference,
          source_sha256,toolchain_lock_sha256,build_definition_sha256,max_attempts,timeout_ms,retry_backoff_ms
        )), '[]') FROM mixer_customer_build_inputs
    """))
    require(rows == [[*(expected[key] for key in SPEC_FIELDS), expected["source_input_id"],
                      "revision", auth["source_reference"], expected["source_sha256"],
                      expected["toolchain_lock_sha256"], expected["build_definition_sha256"],
                      1, 1_200_000, 0]], "browser admission did not persist the exact registered input")
    selection["verifiedInputsAfter"] = len(rows)
    worker_listening = connect_errno(worker_port) != errno.ECONNREFUSED
    require(not worker_listening and not (root / "r/runner.sock").exists()
            and all(snapshot[key] is None for key in ("operations", "capacity", "leases")),
            "browser flow crossed the paused dispatch boundary")
    selection.update(workerListeningAfter=worker_listening, operationIntents=0, capacityReservations=0,
                     coordinatorLeases=0, apiQueuesDisabled=True)
    evidence.verify(queue)
    if not queue:
        require(snapshot["record"] is None and snapshot["jobs"] is None, "selection-only browser flow queued work")
        selection.update(buildRows=0, jobRows=0)
        return

    records = json.loads(sql("""
        SELECT coalesce(json_agg(json_build_object(
          'id', id, 'buildId', build_id, 'requestKey', request_key, 'journal', journal, 'revision', revision
        )), '[]') FROM mixer_builds
    """))
    jobs = json.loads(sql("""
        SELECT coalesce(json_agg(json_build_object(
          'id', id, 'queue', queue, 'worker', worker, 'state', state, 'attempt', attempt, 'args', args
        )), '[]') FROM oban_jobs
    """))
    require(len(records) == len(jobs) == 1, "browser flow did not persist exactly one build and one job")
    record, = records
    job, = jobs
    job_id = job.pop("id")
    queue_scope = {key: evidence.queued[key] for key in (*SPEC_FIELDS, "build_id")}
    journal = record["journal"]
    creation = journal["creation"]
    spec = queue_scope | {
        "source": {"kind": "revision", "reference": auth["source_reference"], "sha256": expected["source_sha256"]},
        "toolchain_lock_sha256": expected["toolchain_lock_sha256"],
        "build_definition_sha256": expected["build_definition_sha256"],
    }
    require(selection["createAttempts"] == 1 and evidence.key is not None
            and record["requestKey"] == creation["request_key"] == evidence.key
            and record["buildId"] == evidence.queued["build_id"] and record["revision"] == 0
            and creation["spec"] == spec and journal["events"] == [],
            "queued build did not persist the exact browser submission")
    require(job == {"queue": "builds", "worker": "MixerHosted.Builds.Coordinator", "state": "available",
                    "attempt": 0, "args": queue_scope | {"build_record_id": record["id"], "revision": 0,
                                                         "kind": "created", "attempt": 1, "fence": 1}},
            "queued build did not persist one undispatched job for the exact record")
    selection.update(buildRows=len(records), jobRows=len(jobs), persistedIdempotencyKeyMatched=True,
                     queuedBuild=evidence.queued | {"record_id": record["id"], "revision": 0},
                     queuedJobID=job_id, jobs=snapshot["jobs"])
    return evidence.queued, record["id"], job_id


def drive(root, args, env, result):
    receipts = result["commands"]
    source = stage(root, env, result)
    operator, inputs, recipe, recipe_path, export = recipe_inputs(root, args, result)
    dist = compile_console(root, args, env, result) if args.browser else None
    compile_hosted(root, source, env, receipts)
    projection = result["approvedLayout"]["projectionSHA256"] if operator else sha(b"inert Pair25 projection")
    write(root / "inputs.json", dict(inputs, recipe_sha256=recipe, projection_sha256=projection))
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

    def billing_state():
        tables = sql("""
            SELECT tablename FROM pg_catalog.pg_tables
            WHERE schemaname = 'public' AND starts_with(tablename, 'mixer_billing_')
            ORDER BY tablename
        """).splitlines()
        require("mixer_billing_organization_state" in tables, "billing state relation missing")
        snapshot = {}
        for table in tables:
            require(re.fullmatch(r"[a-z_]+", table), "unexpected billing relation name")
            rows = sql(f"SELECT to_jsonb(t) FROM public.{table} AS t ORDER BY 1")
            snapshot[table] = {"rows": len(rows.splitlines()), "sha256": sha(rows.encode())}
        return snapshot

    with owned(root, "initdb", [pg / "initdb", "-D", root / "pg", "-U", "fixture_admin", "--locale=C",
                               "--encoding=UTF8", "--auth=trust", "--no-sync"], root, env, receipts) as child:
        child.wait(timeout=15)

    rolename = "mixer_build_processor"
    with ExitStack() as services:
        if args.browser:
            services.callback(verify_port_reuse, ports, result)
        services.enter_context(owned(root, "postgres", [pg / "postgres", "-D", root / "pg", "-h", HOST,
                                     "-p", str(db_port), "-k", "", "-c", "jit=off"],
                                     root, env, receipts, stop=signal.SIGINT))
        wait(lambda: listening(db_port), 8)
        require(sql("SHOW data_directory", "postgres") == str(root / "pg"), "PostgreSQL directory differs")
        registration = root / "tests/integration/free-project-starter/registration-runner.py"
        sql(runpy.run_path(registration)["ROLES"], "postgres")
        if args.select_starter or args.browser:
            require(connect_errno(worker_port) == errno.ECONNREFUSED and not (runner_dir / "runner.sock").exists(),
                    "Starter selection requires unstarted worker and runner")
        api = services.enter_context(owned(root, "api", ["mix", "test", "--no-compile", "--only", "pair25_http",
                        "test/mixer_hosted/browser_auth/local_starter_http_sql_spec.exs"],
                        source, env, receipts, stop=lambda: mark("api.done")))
        auth = ready("api.ready", api, seconds=65)
        ports.extend(auth[key] for key in ("port", "issuer", "jwks"))
        require(len(set(ports)) == len(ports), "fixture listener collision")
        if args.select_starter or args.browser:
            starter = auth["starter"]
            raw = (root / "starter-registration.json").read_bytes()
            spec = {key: auth["build"][key] for key in SPEC_FIELDS}
            spec.update(source={"kind": "revision", "reference": f"starter-{inputs['source_tree_sha256']}",
                                "sha256": inputs["source_tree_sha256"]},
                        toolchain_lock_sha256=inputs["linux_lock_sha256"], build_definition_sha256=recipe)
            require(starter["manifest_sha256"] == sha(raw)
                    and starter["id"] == auth["build"]["source_input_id"] == f"starter-{sha(raw)}"
                    and json.loads(raw) == {"profile": "managed-linux-pair25-v1", "spec": spec,
                                            "projection_sha256": projection,
                                            "rendered_driver_sha256": inputs["rendered_driver_sha256"]}
                    and all(value is None for value in observed_db().values()),
                    "selected Starter differs from the approved runner inputs or enqueued work")
            result["starterRegistration" if args.browser else "starterSelection"] = starter
        result["billingBeforeBuild"] = billing_state()
        if args.release_observation:
            release = read(args.release_observation)
            require(set(release) == {"offer", "artifact"}, "unexpected release observation fields")
            combined = result["combinedOutage"] = {"before": release_snapshot(release)}
        with ExitStack() as dispatch:
            if not args.browser or args.complete:
                config = {"tenant": auth["build"]["organization_id"], "worker_id": "pair25-native-worker",
                          "port": worker_port, "token": secrets.token_hex(32)}
                proc_env = dict(env, MIXER_HOSTED_ROLE="processor", MIXER_PROCESSOR_PROFILE="builds_v1",
                                MIXER_BUILD_OPERATION_INTENT="durable_intent_v1", MIXER_DATABASE_HOST=HOST,
                                MIXER_DATABASE_NAME=DB, MIXER_DATABASE_USER=rolename,
                                MIXER_DATABASE_PASSWORD="loopback-fixture", MIXER_DATABASE_POOL_SIZE="2",
                                MIXER_QUEUE_BUILDS_CONCURRENCY="1", MIXER_BUILD_DISPATCH="native_development_v1",
                                MIXER_NATIVE_RETAINED_ROOT=str(state), MIXER_NATIVE_WORKER_PORT=str(worker_port),
                                MIXER_NATIVE_WORKER_ID=config["worker_id"], MIXER_NATIVE_WORKER_TOKEN=config["token"])
                processor = dispatch.enter_context(owned(
                    root, "processor", ["mix", "run", "--no-start", "--no-compile", HERE / "processor.exs"],
                    source, proc_env, receipts, stop=lambda: mark("processor.done"),
                ))
                result["processorAdmission"] = ready("processor.ready", processor)
                require(result["processorAdmission"] == {"role": rolename, "paused": True}, "restricted pause differs")
            if args.browser:
                if args.complete:
                    require(all(value is None for value in observed_db().values()) and processor.poll() is None,
                            "restricted processor must be ready against an empty queue before opening the bridge")
                    result["browser"]["processorReadyBeforeExposure"] = True
                billing_key = "billingAfterQueue" if args.complete else "billingAfterReadback"
                try:
                    queued = browser_run(root, args, dist, auth, api, sql, worker_port, ports, result)
                finally:
                    result[billing_key] = billing_state()
                require(result["billingBeforeBuild"] == result[billing_key], "browser flow changed billing state")
                if not args.complete:
                    return
                require(args.browser == "smoke" or result["browser"]["finish"] == "operator",
                        "touch the browser finish file to dispatch the verified queued build")
                scope, record_id, job_id = queued
                result.update(createAttempts=result["browser"]["createAttempts"],
                              createHTTP=result["browser"]["createHTTP"])
            else:
                result["createAttempts"] = 1
                status, _, raw = http(auth, BUILD, cookie=auth["cookie"], body=auth["build"])
                require(status == 201, f"ordinary build create returned {status}: {raw!r}")
                created = json.loads(raw)
                scope = created["selection"]
                require(created["state"] == "queued" and created["outcome"] == "applied"
                        and {k: v for k, v in scope.items() if k != "build_id"} ==
                        {k: v for k, v in auth["build"].items() if k != "source_input_id"},
                        "ordinary create binding differs")
                result["createHTTP"] = status
            require(observed_db()["jobs"] == [["created", "available"]], "expected one queued build job")
            selection_path = root / "build.selection.tmp"
            write(selection_path, scope | {"created_job_id": job_id} if args.browser else scope)
            selection_path.rename(root / "build.selection")
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
            if args.browser:
                [drained_job_id] = json.loads(sql("SELECT json_agg(id) FROM oban_jobs WHERE args->>'kind' = 'created'"))
                require(binding["record_id"] == record_id and drained_job_id == job_id,
                        "paused processor did not drain the browser's original job")
                result["browser"]["drainedJobID"] = drained_job_id
            result["pausedBoundary"] = {"jobs": paused["jobs"], "operationIntents": 0, "workerListening": False}

            if (args.select_starter or args.browser) and operator:
                from linux_android_docker_adapter import DockerRecipe
                from linux_android_pair25_layout import Pair25Layout
                admitted_layout = Pair25Layout.read(operator["pair25_root"])
                require(admitted_layout.projection_sha256 == starter["projection_sha256"]
                        and admitted_layout.verified_inputs == inputs
                        and admitted_layout.root / "readonly/Export" == export,
                        "runner layout differs from the selected Starter projection")
                admitted_layout.verify_recipe(DockerRecipe.read(recipe_path, recipe))

            from compiler_worker import literal
            from linux_android_runner import RunnerIdentity
            identity = asdict(RunnerIdentity(
                operation, sha(literal({key: binding[key] for key in ("ref", "spec", "deadline_ms")}).encode()),
                recipe, secrets.token_hex(32),
            ))
            result.update(pausedBinding=binding, runnerIdentity=identity)
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
                runner_seconds = max(48, args.seconds + 15) if args.worker_crash else 48
                runner_command = [sys.executable, "-B", HERE / "run.py", "--inert-child", root, opts,
                                  str(runner_seconds)]
                stop_runner = lambda: mark("runner.done")

            result["workerConfigSHA256"] = worker_pin
            runner_process = services.enter_context(owned(root, "runner", runner_command, root, env, receipts, stop_runner))
            wait(lambda: Path(runner["socket_path"]).is_socket(), 8, runner_process)
            worker_command = [sys.executable, "-B", opts / "native_artifact_worker.py", config_path, worker_pin, state]

            def stop_worker():
                require(wire(config, "shutdown") == {"status": "closed"}, "worker shutdown refused")

            sessions = None
            with ExitStack() as worker_service:
                crash_worker = False

                def stop_initial_worker():
                    if crash_worker:
                        require(os.getpgid(worker.pid) == os.getsid(worker.pid) == worker.pid,
                                "SIGKILL target is not the owned worker session leader")
                        worker.send_signal(signal.SIGKILL)
                        recovery["signal"] = {"name": "SIGKILL", "targetPID": worker.pid, "targetPGID": worker.pid}
                    else:
                        stop_worker()

                worker = worker_service.enter_context(
                    owned(root, "worker", worker_command, root, env, receipts, stop_initial_worker,
                          exit_codes=(0, -signal.SIGKILL) if args.worker_crash else (0,))
                )
                wait(lambda: listening(worker_port), 8, worker)
                if (args.select_starter or args.browser) and operator:
                    admitted_layout.recheck_stage()
                    result["approvedProjectionMatchesSelection"] = True
                result["nativeDispatchPossible"] = bool(operator)
                mark("processor.run")

                if args.cancel or args.worker_crash:
                    runner_identity = RunnerIdentity(**identity)
                    until = time.monotonic() + args.seconds

                    def journals():
                        require(worker.poll() is None and runner_process.poll() is None,
                                "worker or runner exited during cancel")
                        return cancel_journals(state, runner_dir, binding, runner_identity)

                    guard = wait(lambda: original_start(journals(), runner_identity),
                                 until - time.monotonic(), processor)
                    before = observed_db()
                    running_admission(before, binding)
                    result["runningReservation"] = before["capacity"][0]
                    observer = docker_observer(runner_dir, operator, recipe_path, runner_identity) if operator else nullcontext()
                    with observer as adapter:
                        if adapter:
                            frontend = wait(
                                lambda: observed_frontend(adapter, runner_identity),
                                until - time.monotonic(), processor, interval=0.2,
                            )
                        else:
                            start = read(root / "inert.start")
                            require(start["identity"] == identity
                                    and start["cutoff"] <= min(binding["deadline_ms"], guard["expires_at"]),
                                    "inert adapter did not receive the original guarded start")
                            result["inertStart"] = start
                        outcome = "running"
                        if args.worker_crash:
                            mark("api.refresh")
                            sessions = ready("api.sessions", api)
                            recovery = result["workerRecovery"] = {"port": worker_port, "runnerPID": runner_process.pid}
                            if adapter:
                                recovery["frontendBeforeExit"] = frontend
                            recovery["beforeExit"] = verify_running(auth, scope, sessions)
                            runner_socket = Path(runner["socket_path"])
                            paths = (config_path, state / "operations.sqlite", runner_socket, runner_dir / "operations.sqlite")

                            def file_ids():
                                return [(meta.st_dev, meta.st_ino) for meta in (path.stat() for path in paths)]

                            def start_job():
                                [job] = json.loads(sql(
                                    "SELECT json_agg(json_build_array(id, attempt, state::text, "
                                    "floor(extract(epoch FROM attempted_at) * 1000)::bigint)) "
                                    "FROM oban_jobs WHERE args->>'kind' = 'start'"
                                ))
                                return job

                            def require_same_files():
                                require(file_ids() == initial_files and runner_socket.is_socket()
                                        and sha(config_path.read_bytes()) == worker_pin
                                        and config["port"] == read(config_path)["port"] == worker_port,
                                        "worker config, exact port, SQLite store, or independent runner changed")

                            initial_files = file_ids()
                            original_job = start_job()
                            require(worker.poll() is None and runner_process.poll() is None
                                    and runner_process.pid != worker.pid,
                                    "expected a live worker and independent runner before worker exit")
                            killed_at = time.monotonic()
                            crash_worker = True
                            worker_service.close()
                            require("signal" in recovery and receipts["worker"]["exit"] == -signal.SIGKILL
                                    and receipts["worker"]["groupAbsent"],
                                    "original worker was not directly reaped after SIGKILL with group absence")
                            reaped_at_ms = time.time_ns() // 1_000_000
                            recovery["reapedAtMS"] = reaped_at_ms
                            require(connect_errno(worker_port) == errno.ECONNREFUSED,
                                    "exact worker port did not refuse connections after exit")
                            recovery["outageConnectErrno"] = errno.ECONNREFUSED
                            require_same_files()
                            offline_journals = cancel_journals(state, runner_dir, binding, runner_identity)
                            require(original_start(offline_journals, runner_identity), "original start was lost at worker exit")
                            recovery["firstPlainBindErrno"] = plain_bind_errno(worker_port)

                            def retried_offline():
                                job = start_job()
                                admission = running_admission(observed_db(), binding)
                                require(job[0] == original_job[0], "original Oban start job was replaced")
                                # Snoozing resets the Oban attempt counter. Use attempted_at to observe a completed retry.
                                if (job[2] == "scheduled" and job[3] is not None and job[3] > reaped_at_ms
                                        and admission[5] > offline_journals[0]["guard"]["epoch"]):
                                    return job, admission

                            recovery["startJobBeforeExit"] = original_job
                            recovery["offlineRetry"] = wait(retried_offline, until - time.monotonic(), processor)
                            recovery["duringOutage"] = verify_running(auth, scope, sessions)
                            require_no_bundle(state, grant)
                            if args.release_observation:
                                outage_auth = dict(auth, csrf=sessions["owner_csrf"])
                                require(connect_errno(worker_port) == errno.ECONNREFUSED,
                                        "checkout experiment must run during the worker outage")
                                mark("api.checkout.request")
                                combined["saturated"] = ready("api.checkout.ready", api, seconds=4)
                                combined["during"] = release_snapshot(release)
                                status, headers, raw = http(
                                    outage_auth, BUILD, cookie=sessions["owner"], body=auth["build"])
                                combined["refusedHTTP"] = status
                                require(status == 503 and not any(k.lower() == "set-cookie" for k in headers)
                                        and json.loads(raw) == {"error": {"code": "authorization_unavailable",
                                                                          "message": "Build request refused."}},
                                        "original build key did not get the bounded checkout refusal")
                                combined["refusal"] = ready("api.checkout.refused", api, seconds=4)
                                combined["recoveredPool"] = ready("api.checkout.closed", api, seconds=4)
                                require(combined["refusal"]["before_begin"]
                                        and combined["saturated"] == {"held": 2, "queue": 0}
                                        and combined["recoveredPool"]["checked_in"] == 2
                                        and start_job()[0] == original_job[0]
                                        and observed_db()["record"] == [[binding["record_id"], 1]],
                                        "checkout changed the original protected operation")
                            wait(lambda: plain_bind_errno(worker_port) is None,
                                 until - time.monotonic(), processor, interval=0.2)
                            require_same_files()
                            require(connect_errno(worker_port) == errno.ECONNREFUSED and runner_process.poll() is None
                                    and cancel_journals(state, runner_dir, binding, runner_identity) == offline_journals,
                                    "worker or runner ledger changed while the worker was offline")
                            offline_admission = running_admission(observed_db(), binding)
                            recovery["offlineReservation"] = before["capacity"][0]
                            recovery["admissionBeforeReopen"] = offline_admission
                            recovery["downMilliseconds"] = round((time.monotonic() - killed_at) * 1000)
                            recovery["samePortPlainBind"] = True
                            worker = worker_service.enter_context(
                                owned(root, "worker-reopened", worker_command, root, env, receipts, stop_worker)
                            )
                            wait(lambda: listening(worker_port), until - time.monotonic(), worker)
                            recovery["reopenedWorkerPID"] = worker.pid
                            recovery["samePortListening"] = True
                            if args.release_observation:
                                status, headers, raw = http(
                                    outage_auth, BUILD, cookie=sessions["owner"], body=auth["build"])
                                combined["retryHTTP"] = status
                                require(status == 200 and json.loads(raw)["selection"] == scope
                                        and not any(k.lower() == "set-cookie" for k in headers)
                                        and start_job()[0] == original_job[0],
                                        "same session and key did not read the original build after reopen")
                                combined["after"] = release_snapshot(release)
                                require(combined["before"] == combined["during"] == combined["after"],
                                        "signed delivery changed during the checkout and worker outage")
                                combined["sameBuildAndObanJob"] = True

                            def resumed():
                                rows = runner_journal(runner_dir)
                                if len(rows) == 1:
                                    current = rows[0]
                                    runner_guard = json.loads(current[3])
                                    if runner_guard["epoch"] > offline_admission[5]:
                                        return current, runner_guard

                            if args.inert_finish_on_reopen:
                                mark("inert.finish-after-reopen")
                            try:
                                current, guard = wait(resumed, until - time.monotonic(), processor)
                                runner_id, fingerprint, deadline, _, phase, completed = current
                                recovery.update(reopenedRunnerGuard=guard, reopenedRunnerPhase=phase,
                                                reopenedRunnerCompleted=completed,
                                                reopenedRunnerOperation={"operationId": runner_id,
                                                                         "bindingSHA256": fingerprint,
                                                                         "deadlineMS": deadline})
                                if args.inert_finish_on_reopen:
                                    wait(lambda: observed_db()["jobs"] == COMPLETED_JOBS,
                                         until - time.monotonic(), processor)
                            finally:
                                recovery["runnerAliveBeforeFirstRead"] = runner_process.poll() is None
                                recovery["workerAliveBeforeFirstRead"] = worker.poll() is None
                                first = read_recovery_detail(auth, scope, sessions, recovery, "afterReopen")

                            require_same_files()
                            recovery["sameConfigSQLiteAndRunner"] = True
                            job = start_job()
                            recovery["startJobAfterReopen"] = job
                            current_worker, _, _ = cancel_journals(
                                state, runner_dir, binding, runner_identity, allow_completed=True,
                            )
                            [admission] = observed_db()["operations"]
                            require(recovery["runnerAliveBeforeFirstRead"] and recovery["workerAliveBeforeFirstRead"]
                                    and (runner_id, fingerprint, deadline, phase) ==
                                    (operation, identity["binding_sha256"], binding["deadline_ms"], "started")
                                    and completed in (0, 1) and job[0] == original_job[0]
                                    and worker.pid != recovery["signal"]["targetPID"]
                                    and guard["record_id"] == binding["record_id"] and guard["revision"] == 1
                                    and guard["owner_id"].startswith(f"oban:{job[0]}:")
                                    and (current_worker["starts"], current_worker["linux_runner"]) == (1, identity)
                                    and admission[:5] == [operation, binding["record_id"], deadline, "admitted", 1]
                                    and guard["epoch"] <= current_worker["guard"]["epoch"] <= admission[5],
                                    "reopened worker did not observe the original restricted Oban operation")
                            outcome = verify_recovery_detail(first, scope)
                            query = "?" + urlencode(scope)
                            first["outsiderHTTP"] = http(auth, BUILD + query, cookie=sessions["outsider"])[0]
                            first["anonymousHTTP"] = http(auth, BUILD + query)[0]
                            require((first["outsiderHTTP"], first["anonymousHTTP"]) == (404, 401),
                                    "post-reopen detail authorization differs")

                            def active_or_completed():
                                if adapter:
                                    active = observed_frontend(adapter, runner_identity)
                                    if active:
                                        require(active["container"] == recovery["frontendBeforeExit"]["container"],
                                                "reopened worker observed a different Docker container")
                                        return "running", active
                                else:
                                    require(read(root / "inert.start") == start and not (root / "inert.stop").exists(),
                                            "inert runner did not preserve its one active start")
                                    return "running", None
                                observation = read_recovery_detail(auth, scope, sessions, recovery, "latestRecoveryRead")
                                if verify_recovery_detail(observation, scope) == "native_succeeded":
                                    return "native_succeeded", None

                        if args.cancel and outcome == "running":
                            mark("api.cancel-auth.request")
                            cancel_auth = auth | ready("api.cancel-auth", api)
                            if args.worker_crash:
                                outcome, frontend = wait(active_or_completed, until - time.monotonic(), processor,
                                                         interval=0.2)

                        if args.cancel and outcome == "running":
                            if adapter:
                                result["frontendBeforeCancel"] = frontend
                            result["cancelAttempts"] = 1
                            result["cancelRequestedAtMS"] = time.time_ns() // 1_000_000
                            status = request_cancel(cancel_auth, scope, allow_completion_conflict=args.worker_crash)
                            result["cancelHTTP"] = status
                            if status == 409:
                                observation = read_recovery_detail(auth, scope, sessions, recovery, "afterCancelConflict")
                                outcome = verify_recovery_detail(observation, scope)
                                require(outcome == "native_succeeded", "cancel conflict lacks native success evidence")
                            else:
                                result["cancellationExercised"] = True

                                def cancelled():
                                    current = observed_db()
                                    if current["jobs"] == [[kind, "completed"] for kind in
                                                          ("created", "start", "cancel", "stopped")]:
                                        return current

                                final = wait(cancelled, max(1, until - time.monotonic()), processor)
                                result.update(verify_stop(final, sql, journals(), guard, state, binding, grant, config))
                                if args.worker_crash:
                                    settled_job = start_job()
                                    require(settled_job[0] == original_job[0],
                                            "cancellation settled a different Oban start job")
                                    recovery["settledStartJob"] = settled_job
                                if adapter:
                                    result["liveClosure"] = verify_container_stop(adapter, runner_identity, frontend)
                                else:
                                    stop = read(root / "inert.stop")
                                    require(stop == {"identity": identity}, "inert adapter stopped a different operation")
                                    result["inertStop"] = stop
                                result["nativeDispatchResolved"] = True

                if not result["cancellationExercised"]:
                    def settled():
                        require(worker.poll() is None and runner_process.poll() is None,
                                "worker or runner exited before settlement")
                        snapshot = observed_db()
                        if snapshot["jobs"] == COMPLETED_JOBS:
                            return snapshot
                        return None

                    success_budget = until - time.monotonic() if args.worker_crash else args.seconds
                    final = wait(settled, success_budget, processor)
                    require(final["record"] == [[binding["record_id"], 2]]
                            and final["capacity"] == [[binding["record_id"], 1, 1, False, "coordinator:1:1:completed"]]
                            and final["leases"] == [[binding["record_id"], None, None]], "settlement or release differs")
                    [(row_id, raw)] = journal_rows(state / "operations.sqlite", "SELECT id, value FROM operations")
                    row = json.loads(raw)
                    require(row_id == operation and row["linux_runner"] == identity
                            and row["binding"] == {key: binding[key] for key in ("ref", "spec", "deadline_ms")}
                            and (row["starts"], row["status"]) == (1, "native_ready"), "worker journal differs")
                    [(row_id, fingerprint, deadline, guard_raw, phase, completed)] = runner_journal(runner_dir)
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
                    result.update(runnerGuard=guard, finalWorkerGuard=worker_guard, workerStarts=1, runnerStarts=1,
                                  runnerCompleted=True, capacityReleased=True, settledJobs=final["jobs"],
                                  capacityReleaseEvent=final["capacity"][0][-1])
                    if args.worker_crash:
                        settled_job = start_job()
                        require(settled_job[0] == original_job[0]
                                and worker_guard["owner_id"].startswith(f"oban:{settled_job[0]}:")
                                and guard["epoch"] >= recovery["reopenedRunnerGuard"]["epoch"]
                                and not row.get("tombstone"),
                                "native success did not retain the original recovered Oban operation")
                        [[start_event, completed_event]] = json.loads(
                            sql("SELECT json_agg(journal->'events') FROM mixer_builds")
                        )
                        require(start_event["event"] == {"type": "start", "ref": binding["ref"]}
                                and completed_event["id"] == result["capacityReleaseEvent"]
                                and completed_event["event"] == {
                                    "type": "completed", "ref": binding["ref"],
                                    "result": {"outcome": "native_succeeded", "artifacts": [
                                        {"kind": entry["kind"], "sha256": entry["sha256"],
                                         "size_bytes": entry["sizeBytes"]} for entry in row["artifacts"]
                                    ]},
                                }, "native success and capacity release do not match the original build journal")
                        recovery["settledStartJob"] = settled_job
                    readback = (Path(grant["bundle"]) / "readback.json").read_bytes()
                    driver_log = json.loads(readback)["androidDriverLog"]
                    if operator and args.worker_crash:
                        with docker_observer(runner_dir, operator, recipe_path, runner_identity) as adapter:
                            result["liveClosure"] = verify_container_success(
                                adapter, runner_identity, recovery["frontendBeforeExit"], sha(readback),
                            )
                    elif operator:
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
                        require(not (root / "inert.stop").exists(), "successful inert operation was stopped")
                        request = dict(row["binding"], operation_id=operation, guard=worker_guard)
                        require(wire(config, "query", dict(request, deadline_ms=deadline + 1)) == {"error": "unavailable"}
                                and wire(config, "query", dict(request, guard=dict(worker_guard, expires_at=1))) ==
                                {"error": "stale"}, "worker admitted a changed deadline or expired guard")
                        result["changedDeadlineAndExpiredGuardRefused"] = True
                    result["nativeDispatchResolved"] = True

            if sessions is None:
                mark("api.refresh")
                sessions = ready("api.sessions", api)
            if result["cancellationExercised"]:
                result["cancelledBuild"] = verify_cancelled(auth, scope, sessions)
            else:
                result["downloads"], result["logs"], result["terminalBuild"] = verify_downloads(
                    auth, scope, sessions, row, driver_log,
                )
                if args.worker_crash:
                    final_detail = read_recovery_detail(auth, scope, sessions, recovery, "finalOwnerRead")
                    require(verify_recovery_detail(final_detail, scope) == "native_succeeded",
                            "native success changed after artifact and log readback")
            if args.worker_crash:
                recovery["outcome"] = "cancelled" if result["cancellationExercised"] else "native_succeeded"
            result["billingAfterReadback"] = billing_state()
            require(result["billingBeforeBuild"] == result["billingAfterReadback"],
                    "build or readback changed billing state")

    require(not Path(runner["socket_path"]).exists(), "runner socket was retained")
    if not args.browser:
        verify_port_reuse(ports, result)


def main():
    if sys.argv[1:2] == ["--inert-child"]:
        root, code = map(Path, sys.argv[2:4])
        sys.path.insert(0, str(code))
        config = read(root / "worker.json")
        [grant] = config["linux_artifact_imports"].values()
        control_runner(root, config["linux_runner"], grant, grant["inputs"]["linux_lock_sha256"],
                       cancel=os.environ.get("PAIR25_CANCEL") == "1", seconds=int(sys.argv[4]))
        return

    parser = argparse.ArgumentParser(description=__doc__)
    scratch = parser.add_mutually_exclusive_group(required=True)
    scratch.add_argument("--scratch", type=Path, help="existing private-parent path on this host")
    scratch.add_argument("--reserved-scratch", type=Path, help="empty private directory reserved by the outer fixture")
    parser.add_argument("--pg-bin", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin"))
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--operator", type=Path, help="real Pair25 stage/daemon operator JSON; omitted for inert replay")
    parser.add_argument("--select-starter", action="store_true",
                        help="select the operator registration through the authenticated Starter API")
    parser.add_argument("--cancel", action="store_true", help="cancel the original operation while it is running")
    parser.add_argument("--worker-crash", action="store_true",
                        help="SIGKILL and reopen the owned worker, then observe terminal settlement")
    parser.add_argument("--inert-finish-on-reopen", action="store_true",
                        help="with inert worker-crash mode, settle the original operation before the first recovery read")
    parser.add_argument("--browser", choices=("select", "queue", "smoke"),
                        help="serve the compiled console for selection, selection plus one build, or a no-browser HTTP smoke")
    parser.add_argument("--complete", action="store_true",
                        help="dispatch and read back the original build from --browser queue or smoke")
    parser.add_argument("--npm-cache", type=Path, default=Path.home() / ".npm",
                        help="read-only source for locked console package tarballs")
    parser.add_argument("--release-observation", type=Path,
                        help="private loopback signed release observation from the combined L07 launcher")
    parser.add_argument("--seconds", type=int, help="settlement budget and browser handoff window (capped at 300)")
    args = parser.parse_args()
    if args.complete and args.browser not in ("queue", "smoke"):
        parser.error("--complete requires --browser queue or smoke")
    if args.browser and (args.select_starter or args.cancel or args.worker_crash or args.inert_finish_on_reopen):
        parser.error("--browser handles Starter selection and does not support cancellation or recovery")
    if args.browser and args.operator and (args.browser != "queue" or not args.complete):
        parser.error("--operator with --browser requires --browser queue --complete")
    if args.release_observation and (not args.worker_crash or args.cancel):
        parser.error("--release-observation requires completion-only --worker-crash")
    if args.worker_crash and not (args.cancel or args.release_observation):
        parser.error("--worker-crash requires --cancel or --release-observation")
    if args.inert_finish_on_reopen and (not args.worker_crash or args.operator):
        parser.error("--inert-finish-on-reopen requires --worker-crash without --operator")
    if args.seconds is None:
        args.seconds = 120 if args.browser else 75 if args.worker_crash else 30
    limit = (900 if args.complete else 300) if args.browser else 1150
    if not 1 <= args.seconds <= limit:
        parser.error(f"use a time budget between 1 and {limit} seconds")
    require(not args.receipt.exists(), "receipt already exists")
    os.umask(0o077)
    if args.reserved_scratch:
        root = args.reserved_scratch.resolve(strict=True)
        require(root == args.reserved_scratch.absolute() and root.is_dir()
                and root.stat().st_uid == os.getuid() and root.stat().st_mode & 0o777 == 0o700
                and set(root.iterdir()) == {root / "custody.jsonl"}
                and (root / "custody.jsonl").is_file()
                and not (root / "custody.jsonl").is_symlink()
                and (root / "custody.jsonl").stat().st_size == 0,
                "reserved scratch must be a private owned directory with an empty custody journal")
    else:
        root = Path(tempfile.mkdtemp(prefix="p25-", dir=args.scratch.resolve(strict=True)))
    product_pin = BROWSER_PIN if args.browser else STARTER_PIN if args.select_starter else RECOVERY_PIN if args.worker_crash else PIN
    result = {"productPin": product_pin,
              "mode": "real" if args.operator else "inert", "python": sys.version,
              "fixtureSHA256": {name: sha((HERE / name).read_bytes())
                                for name in ("run.py", "processor.exs", "api-case.exs")},
              "commands": {}, "cancelAttempts": 0, "cancellationExercised": False, "nativeDispatchPossible": False}
    if args.browser:
        if not args.complete:
            result["mode"] = "loopback-console"
        result["fixtureSHA256"]["browser.py"] = sha((HERE / "browser.py").read_bytes())
        result["browser"] = {"mode": args.browser, "complete": args.complete,
                             "httpClient": "Python smoke" if args.browser == "smoke" else "external browser"}
        if args.browser != "smoke":
            result["browser"]["windowSeconds"] = min(args.seconds, 300)
    if args.worker_crash and not args.operator:
        result["inertRecoveryMode"] = "finish-on-reopen" if args.inert_finish_on_reopen else "stay-active"
    env = {key: os.environ[key] for key in ("PATH", "HOME", "MIX_HOME", "HEX_HOME") if key in os.environ}
    env.update(MIX_ENV="test", HEX_OFFLINE="1", GIT_NO_LAZY_FETCH="1", LC_ALL="C", TMPDIR=str(root),
               PAIR25_RUN=str(root), PYTHONDONTWRITEBYTECODE="1", PYTHONOPTIMIZE=str(sys.flags.optimize))
    if args.cancel or args.worker_crash:
        env["PAIR25_CANCEL"] = "1"
    if args.select_starter:
        env["PAIR25_SELECT_STARTER"] = "1"
    if args.browser:
        env["PAIR25_BROWSER"] = args.browser
    try:
        require(len(os.fsencode(root / "r/runner.sock")) < 103, "scratch path exceeds Unix socket budget")
        drive(root, args, env, result)
        result["passed"] = True
    except Exception as error:
        result["failure"] = {"type": type(error).__name__}
        if args.browser:
            # Subprocess or parser exceptions can include private fixture paths or wire values.
            if type(error) is RuntimeError:
                result["failure"]["detail"] = str(error)
            print("Pair25 browser fixture failed. See the sanitized receipt.", file=sys.stderr)
            raise SystemExit(1) from None
        result["failure"]["detail"] = str(error)
        raise
    finally:
        unresolved = result["nativeDispatchPossible"] and not result.get("nativeDispatchResolved")
        unknown = any(not meta["groupAbsent"] for meta in result["commands"].values())
        if unknown or unresolved:
            result["scratchHeld"] = str(root)
            result["scratchHoldReason"] = {"unknownGroups": {name: meta["pid"]
                                           for name, meta in result["commands"].items() if not meta["groupAbsent"]},
                                           "liveDispatchUnresolved": unresolved}
        else:
            shutil.rmtree(root)
            result["scratchRemoved"] = True
        write(args.receipt, result)


if __name__ == "__main__":
    main()
