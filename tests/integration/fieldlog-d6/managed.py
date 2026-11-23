#!/usr/bin/env python3
"""One local authenticated stock FieldLog iOS build and artifact replay."""
import argparse
from contextlib import contextmanager, closing, ExitStack
import hashlib
import hmac
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import runpy
import secrets
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import plistlib
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
from prepare import MIXER, PROJECT_SHA, digest, private_env
from release_packet import unpack_app

HOST = "127.0.0.1"
DB = "browser_ordinary_installation_r1422"
BUILD = "/console-api/v1/builds"
LOGS = "/console-api/v1/build-logs"
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


def wait(pred, seconds, child=None):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if value := pred():
            return value
        require(child is None or child.poll() is None, "owned service exited before readiness")
        time.sleep(0.05)
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
        receipts[name] = {"argv": [str(a) for a in argv], "pid": process.pid, "groupAbsent": False}
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


def http(auth, path, *, cookie=None, body=None):
    headers = {}
    if cookie:
        headers["Cookie"] = "__Host-mixer-session=" + cookie
    if body is not None:
        headers.update({"Origin": auth["origin"], "X-Mixer-CSRF": auth["csrf"],
                        "Content-Type": "application/json", "Idempotency-Key": "d6-fieldlog-one-build"})
    with closing(HTTPConnection(HOST, auth["port"], timeout=10)) as connection:
        payload = json.dumps(body) if body is not None else None
        connection.request("GET" if body is None else "POST", path, payload, headers)
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
    marker = "    c\n    |> put_in(\n"
    require(raw.count(marker) == 1, "stock test setup differs")
    raw = raw.replace(marker, '    c\n    |> then(&pair25_processor!/1)\n    |> put_in(\n', 1)
    raw = raw.replace('@test_app "example.source.app"', '@test_app "dev.mixer.fieldlog"', 1)
    close = raw.rindex("\nend\n")
    case = (HERE / "api-case.exs").read_text()
    test.write_text(raw[:close] + "\n" + "\n".join("  " + line if line else "" for line in case.splitlines()) + raw[close:])


def registration(root, project, cli):
    file_pins = {}
    for p in project.rglob("*"):
        require(not p.is_symlink(), f"nonportable source path {p.name}")
        if p.is_file():
            file_pins[p.relative_to(project).as_posix()] = sha(p.read_bytes())
    source_pin = sha("".join(f"{p}\0{digest}\n" for p, digest in sorted(file_pins.items())).encode())
    environment = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
                   "DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer",
                   "LC_ALL": "C"}
    tools = {str(path): sha(path.read_bytes()) for path in (cli, Path("/usr/bin/xcodebuild"))}
    recipe = {"argv": [str(cli), "build", "--platform", "ios", "--directory", str(project)],
              "cwd": str(project), "environment": environment, "inputs": file_pins,
              "tools": tools, "profile": "unsigned-ios-simulator-v1", "timeout_seconds": 215,
              "package_policy": "exact-owned-local-manifests-no-external-packages"}
    recipe_path = root / "recipe.json"
    definition = write(recipe_path, recipe)
    policy = {"recipe_sha256": definition, "cli": str(cli), "environment": environment,
              "inputs": file_pins, "tools": tools}
    return {"source_tree_sha256": source_pin, "lock_sha256": file_pins["mixer.lock"],
            "recipe_sha256": definition}, {"root": str(project), "recipe": str(recipe_path),
                                           "files": file_pins}, policy


def verify_download(auth, scope, sessions, row, store, result, root):
    owner, outsider = sessions["owner"], sessions["outsider"]
    for cookie in (owner, outsider):
        require(http(auth, "/auth/session", cookie=cookie)[0] == 200, "readback session unavailable")
    query = "?" + urlencode(scope)
    status, _, raw = http(auth, BUILD + query, cookie=owner)
    require(status == 200 and http(auth, BUILD + query, cookie=outsider)[0] == 404,
            "build detail authorization differs")
    detail = json.loads(raw)["build"]
    require((detail["buildId"], detail["revision"], detail["state"]) ==
            (scope["build_id"], 2, "native_succeeded"), "build detail binding differs")
    kind = "unsigned_native_binary"
    [descriptor] = [d for d in detail["artifacts"] if d["kind"] == kind]
    [retained] = [d for d in row["artifacts"] if d["kind"] == kind]
    route = descriptor["downloadPath"]
    require(route.startswith("/console-api/v1/build-artifacts/" + kind + "?"), "download route differs")
    status, headers, data = http(auth, route, cookie=owner)
    denied, _, denied_body = http(auth, route, cookie=outsider)
    anonymous, _, anonymous_body = http(auth, route)
    headers = {k.lower(): v for k, v in headers.items()}
    reference = (store / retained["sha256"]).read_bytes()
    require((status, denied, anonymous) == (200, 404, 401), "download authorization differs")
    require(not any(body.startswith(b"MXNATIVE1\n") for body in (denied_body, anonymous_body)),
            "denied response includes artifact")
    require(headers["content-type"] == "application/octet-stream" and
            headers["content-disposition"] == 'attachment; filename="unsigned_native_binary"' and
            headers["cache-control"] == "no-store", "stock attachment headers differ")
    require(data == reference and {k: descriptor[k] for k in retained} == retained and
            (len(data), sha(data)) == (retained["sizeBytes"], retained["sha256"]),
            "HTTP bytes, artifact journal, and retained object disagree")
    result["download"] = dict(retained, byteForByte=True, ownerHTTP=status, outsiderHTTP=denied,
                              anonymousHTTP=anonymous, contentType=headers["content-type"],
                              contentDisposition=headers["content-disposition"])
    # Project the identity from the built app only after the retained bytes agree.
    report = read(store / "native-build.json")
    require(report["nativeProduct"]["nativeBinary"]["sha256"] == retained["sha256"],
            "native build manifest points at a different binary")
    project = store.parent / "project"
    app = project / ".mixer/ios-build/Build/Products/Debug-iphonesimulator/FieldLog.app"
    metadata = plistlib.loads((app / "Info.plist").read_bytes())
    require(metadata["CFBundleIdentifier"] == "dev.mixer.fieldlog"
            and metadata["CFBundleExecutable"] == "FieldLog"
            and metadata["CFBundleSupportedPlatforms"] == ["iPhoneSimulator"], "FieldLog identity differs")
    matching = {p.name: sha(p.read_bytes()) for p in (app / "ChecklistRelease").iterdir() if p.is_file()}
    resources = root.parent / "RegisteredFieldLog/Platforms/iOS/ChecklistRelease"
    require(matching == {p.name: digest(p) for p in resources.iterdir()}, "embedded resources differ")
    download = result["download"]
    download["workerArchiveBinding"] = report["nativeProduct"]["bindingSHA256"]
    download["machOUUID"] = report["nativeProduct"]["uuid"]
    product = root / "owner/Products/Debug-iphonesimulator/FieldLog.app"
    product.parent.mkdir(parents=True)
    files = unpack_app(data, product, download)
    require(files["FieldLog"] == digest(app / "FieldLog"), "owner archive and worker Mach-O differ")
    (root / "owner.mxnative").write_bytes(data)
    result["ownerFiles"] = files
    result["detailHTTP"] = {"owner": 200, "outsider": 404}
    result["app"] = {"identifier": metadata["CFBundleIdentifier"], "displayName": metadata.get("CFBundleDisplayName"),
                     "executable": metadata["CFBundleExecutable"], "machOSHA256": sha((app / "FieldLog").read_bytes()),
                     "runtimeResources": matching, "binarySignature": report["nativeProduct"]["binarySignature"]}


def drive(root, env, result):
    work = root.parent
    source = work / "hosted"
    project = work / "RegisteredFieldLog"
    cli = Path((work / "cli-path").read_text().strip())
    state = root / "worker"
    state.mkdir()
    (root / "catalog").mkdir()
    sys.path.insert(0, str(source / "priv/development"))
    from native_artifact_worker import NativeWorker, Refusal
    opts = source / "priv/development"
    inputs, grant, policy = registration(root, project, cli)
    write(root / "inputs.json", inputs)
    result["inputs"] = inputs
    result["tools"] = policy["tools"]
    result["workerSourceSHA256"] = sha((opts / "native_artifact_worker.py").read_bytes())
    result["hostedTree"] = "ac22272afdbf5efd3e55d3547cd214346b7851ff"
    pg = Path(shutil.which("initdb", path=env["PATH"])).parent
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

    def snapshot():
        return json.loads(sql(SQL_STATE))

    receipts = result["commands"]
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
        registration_fixture = work / "tests/integration/free-project-starter/registration-runner.py"
        sql(runpy.run_path(registration_fixture)["ROLES"], "postgres")
        api = services.enter_context(owned(root, "api", ["mix", "test", "--no-compile", "--only", "pair25_http",
                        "test/mixer_hosted/browser_auth/local_starter_http_sql_spec.exs"],
                        source, env, receipts, stop=lambda: mark("api.done")))
        auth = ready("api.ready", api, seconds=50)
        ports.extend(auth[key] for key in ("port", "issuer", "jwks"))
        require(len(set(ports)) == len(ports), "fixture listener collision")
        spec = {key: auth["build"][key] for key in SPEC_FIELDS}
        spec.update(source={"kind": "revision", "reference": auth["source_reference"],
                            "sha256": inputs["source_tree_sha256"]},
                    toolchain_lock_sha256=inputs["lock_sha256"], build_definition_sha256=inputs["recipe_sha256"])
        config = {"tenant": spec["organization_id"], "worker_id": "fieldlog-d6-native-worker",
                  "port": worker_port, "token": secrets.token_hex(32),
                  "registration": dict(grant, spec=spec), "policy": policy}
        verifier = object.__new__(NativeWorker)
        verifier.config = config
        try:
            verifier.verify(spec)
        except Refusal as error:
            result["stockWorkerRefusal"] = str(error)
            raise
        result["stockWorkerVerifiedRecipe"] = True
        config_path = root / "worker.json"
        worker_pin = write(config_path, config)
        result["workerConfigSHA256"] = worker_pin
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
            status, _, body = http(auth, BUILD, cookie=auth["cookie"], body=auth["build"])
            result["createHTTP"] = status
            require(status == 201, f"stock create returned {status}: {body[:1024]!r}")
            created = json.loads(body)
            scope = created["selection"]
            require((created["state"], created["outcome"]) == ("queued", "applied")
                    and {k: v for k, v in scope.items() if k != "build_id"} ==
                    {k: v for k, v in auth["build"].items() if k != "source_input_id"}, "create binding differs")
            require(snapshot()["jobs"] == [["created", "available"]], "expected a single queued build")
            write(root / "build.selection", scope)
            binding = ready("build.binding", processor)
            operation = binding["operation_id"]
            result["binding"] = binding
            require(binding["spec"] == dict(spec, build_id=scope["build_id"])
                    and binding["ref"] == ({key: scope[key] for key in (*SPEC_FIELDS, "build_id")}
                                           | {"attempt": 1, "fence": 1})
                    and binding["deadline_ms"] == binding["started_at_ms"] + 1_200_000
                    and binding["deadline_ms"] > time.time_ns() // 1_000_000, "launch binding differs")
            paused = snapshot()
            require(paused["jobs"] == [["created", "completed"], ["start", "available"]]
                    and paused["operations"] is None and not listening(worker_port), "worker preceded binding")
            result["pausedBoundary"] = paused

            def stop_worker():
                require(wire(config, "shutdown") == {"status": "closed"}, "worker shutdown refused")

            with owned(root, "worker", [sys.executable, "-B", opts / "native_artifact_worker.py",
                                        config_path, worker_pin, state], root, env, receipts, stop_worker) as worker:
                wait(lambda: listening(worker_port), 8, worker)
                mark("processor.run")

                def worker_row():
                    with closing(sqlite3.connect(state / "operations.sqlite", timeout=2)) as journal:
                        rows = journal.execute("SELECT id, value FROM operations").fetchall()
                    require(len(rows) <= 1, "more than one worker operation")
                    if not rows:
                        return None
                    row_id, raw = rows[0]
                    require(row_id == operation, "worker operation ID differs")
                    return json.loads(raw)

                def settled():
                    require(worker.poll() is None, "worker exited before settlement")
                    row = worker_row()
                    if row and row["status"] in ("uncertain", "closed"):
                        result["workerTerminalObservation"] = row
                        if row["status"] == "closed":
                            for name in ("stdout", "stderr"):
                                output = state / operation / name
                                if output.is_file():
                                    print(output.read_text(errors="replace")[-3000:], file=sys.stderr)
                        if row["status"] == "uncertain":
                            result["nativeCustodyUnknown"] = True
                        raise RuntimeError("worker did not retain native products")
                    final = snapshot()
                    if final["jobs"] == [["created", "completed"], ["start", "completed"], ["completed", "completed"]]:
                        return final

                final = wait(settled, 225, processor)
                row = worker_row()
                result["settledPostgres"] = final
                require(final["record"] == [[binding["record_id"], 2]]
                        and final["capacity"] == [[binding["record_id"], 1, 1, False, "coordinator:1:1:completed"]]
                        and final["leases"] == [[binding["record_id"], None, None]], "settlement or capacity differs")
                require(row["binding"] == {key: binding[key] for key in ("ref", "spec", "deadline_ms")}
                        and (row["starts"], row["status"]) == (1, "native_ready"), "worker binding differs")
                guard = row["guard"]
                require(final["operations"] == [[operation, binding["record_id"], binding["deadline_ms"], "admitted",
                                                 guard["revision"], guard["epoch"], guard["owner_id"]]],
                        "worker guard differs from PostgreSQL intent")
                attempt = state / operation
                closure = row["closure"]
                require(closure["exit"] == 0 and closure["closed"] and closure["cli_reaped"]
                        and closure["cli_group_absent"], "worker CLI did not close")
                [compiler] = [p for p in closure["commands"] if p["command"] == "/usr/bin/xcodebuild"]
                tmp = attempt / "tmp"
                receipt_root = tmp / (tmp / "cli-closed").read_text()
                [command] = [p for p in receipt_root.glob("command-*/receipt.json")
                             if sha(p.read_bytes()) == compiler["receipt_sha256"]]
                xcode = read(command)
                require(xcode["exitCode"] == 0 and all(xcode[k] is True for k in ("terminalCustody",
                        "directChildReaped", "ownedGroupAbsent", "stdoutEOF", "stderrEOF", "descriptorsClosed"))
                        and "CODE_SIGNING_ALLOWED=NO" in xcode["command"]
                        and "generic/platform=iOS Simulator" in xcode["command"], "Xcode closure differs")
                result.update(workerStarts=1, finalWorkerGuard=guard, workerClosure=closure,
                              xcodeClosure={k: xcode[k] for k in ("command", "ownedPGID", "exitCode",
                                  "terminalCustody", "directChildReaped", "ownedGroupAbsent",
                                  "stdoutEOF", "stderrEOF", "descriptorsClosed")})
                mark("api.refresh")
                sessions = ready("api.sessions", api)
                verify_download(auth, scope, sessions, row, attempt / "native", result, root)
                result["nativeDispatchResolved"] = True

    with ExitStack() as stack:
        for selected in ports:
            sock = stack.enter_context(socket.socket())
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((HOST, selected))
            sock.listen(1)
    result["portsReusable"] = ports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    work = parser.parse_args().work.resolve(strict=True)
    root = work / "managed"
    app = work / "RegisteredFieldLog"
    require(not (app / ".mixer").exists(), "registered source contains mutable build state")
    require(digest(app / "Platforms/iOS/FieldLog.xcodeproj/project.pbxproj") == PROJECT_SHA,
            "stock generated project differs")
    os.umask(0o077)
    root.mkdir(mode=0o700)
    result = {"productPin": MIXER, "commands": {}, "profile": "unsigned-ios-simulator-v1"}
    env = private_env(work)
    env.update(MIX_ENV="test", HEX_OFFLINE="1", HEX_HOME=str(work / "hex"),
               MIX_HOME=str(work / "mix"), ERL_FLAGS="+S 4:4", TMPDIR=str(root), PAIR25_RUN=str(root))
    try:
        fixtures(work / "hosted")
        drive(root, env, result)
        result["passed"] = True
    except Exception as error:
        result.update(passed=False, failure=str(error),
                      hold=isinstance(error, CustodyUnknown) or result.get("nativeCustodyUnknown", False))
        raise
    finally:
        write(root / "receipt.json", result)


if __name__ == "__main__":
    main()
