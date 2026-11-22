#!/usr/bin/env python3
"""Sign and attach a root-owned, settled v74 iOS Simulator build."""

import argparse
import base64
from contextlib import ExitStack, closing
import errno
import hashlib
from http.client import HTTPConnection
import io
import json
import os
from pathlib import Path
import re
import runpy
import selectors
import signal
import sqlite3
import stat
import sys
import tarfile
import time
from urllib.parse import parse_qsl, urlencode, urlsplit

from live import require

BASE = "44aecbeb6a82a4a93321cff6a8ab86c5aa421900"
REPO = Path(__file__).resolve().parents[3]
SIGNER_TREE = "a55127f07cec85dfbf00d985e72e44c6c905d09a"
IDS = ("organization_id", "project_id", "application_id", "build_id", "platform")
PINS = ("source_sha256", "toolchain_lock_sha256", "build_definition_sha256")
WIRE = ("organizationId", "projectId", "applicationId", "buildId", "platform",
        "sourceSha256", "toolchainLockSha256", "buildDefinitionSha256")
KINDS = ("unsigned_native_binary", "debug_symbols", "resource_inventory")
PROFILE = "mixer.native-build.ios-simulator.development.v2"
HEX = re.compile(r"[0-9a-f]{64}")
ARCHIVE_LIMIT = 256 << 20
INVENTORY_LIMIT = 8 << 20
COMMAND_LOG_LIMIT = 4 << 20
COMMAND_CLEANUP_SECONDS = 3

# Reuse the v74 nested-receipt validators without starting a worker.
sys.path.insert(0, str(REPO / "hosted/priv/development"))
try:
    import ios_build_custody as ios
    import native_artifact_worker as native
finally:
    sys.path.pop(0)

kit = runpy.run_path(str(REPO / "tests/integration/l05-pair25-http/run.py"))
group_absent = kit["group_absent"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def private_path(path, mode=None):
    info = path.lstat()
    require(path.is_absolute() and path == path.resolve() and info.st_uid == os.getuid()
            and (mode is None or info.st_mode == (stat.S_IFREG | mode)),
            "expected a canonical, operator-owned input path")
    return info


class CustodyUnknown(RuntimeError):
    pass


def save_record(path, value):
    pending = path.with_suffix(".pending")
    with pending.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    pending.replace(path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def exec_command(argv, cwd, env, deadline, gate, launch, stdin, stdout, stderr):
    # This child becomes the tool in its own session. There is no launcher
    # process whose exit could be mistaken for closure of the tool's group.
    try:
        os.setsid()
        os.chdir(cwd)
        for source, target in ((stdin, 0), (stdout, 1), (stderr, 2)):
            os.dup2(source, target)
        for fd in os.listdir("/dev/fd"):
            fd = int(fd)
            if fd > 2 and fd not in (gate, launch):
                try:
                    os.close(fd)
                except OSError as error:
                    if error.errno != errno.EBADF:
                        raise
        for name in ("SIGPIPE", "SIGXFZ", "SIGXFSZ"):
            if hasattr(signal, name):
                signal.signal(getattr(signal, name), signal.SIG_DFL)
        os.write(launch, b"R")
        require(os.read(gate, 1) == b"G" and time.monotonic() < deadline, "command gate expired")
        os.close(gate)
        os.execvpe(argv[0], argv, env)
    except BaseException:
        try:
            os.write(launch, b"F")
        finally:
            os._exit(125)
    os._exit(125)


def run_command(work, name, argv, *, seconds, cwd=None, env, secret=None):
    """Run one trusted tool under a shared launch and collection deadline."""
    deadline = time.monotonic() + seconds
    hold = work.parent / "HOLD.json"
    require(not os.path.lexists(hold), "prior command custody is unresolved")
    require(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL, "command requires exclusive child reaping")
    logs = work / "commands" / name
    logs.mkdir(parents=True, mode=0o700)
    argv = list(map(str, argv))
    custody = dict(command=name, argv=argv, cwd=str(cwd or work), seconds=seconds,
                   custody="UNKNOWN", directChildReaped=False, groupAbsent=False,
                   descriptorsClosed=False, signalAttempted=False, stage="launch", logs=str(logs),
                   stdoutEOF=False, stderrEOF=False, execPipeEOF=False, outputLimitExceeded=False)
    buffers = {stream: bytearray() for stream in ("stdout", "stderr")}
    unresolved = None

    def persist_logs():
        for stream, data in buffers.items():
            with (logs / stream).open("xb") as output:
                output.write(data)
        custody["logBytes"] = {stream: len(data) for stream, data in buffers.items()}

    try:
        with ExitStack() as descriptors:
            def pipe():
                read, write = os.pipe()
                return (descriptors.enter_context(os.fdopen(read, "rb", buffering=0)),
                        descriptors.enter_context(os.fdopen(write, "wb", buffering=0)))

            gate_read, gate_write = pipe()
            launch_read, launch_write = pipe()
            output_pipes = {stream: pipe() for stream in buffers}
            stdin_read, stdin_write = pipe()
            if secret is not None:
                # Complete the anonymous token handoff before admitting any child.
                os.set_blocking(stdin_write.fileno(), False)
                require(stdin_write.write(secret) == len(secret), "incomplete token handoff")
            stdin_write.close()
            selector = descriptors.enter_context(selectors.DefaultSelector())
            for stream, (read, _) in output_pipes.items():
                os.set_blocking(read.fileno(), False)
                selector.register(read, selectors.EVENT_READ, stream)
            os.set_blocking(launch_read.fileno(), False)
            selector.register(launch_read, selectors.EVENT_READ, "launch")
            require(time.monotonic() < deadline, "command admission exceeded its budget")
            save_record(hold, custody)
            require(time.monotonic() < deadline, "command admission exceeded its budget")
            pid = os.fork()
            if pid == 0:
                try:
                    exec_command(argv, cwd or work, env, deadline, gate_read.fileno(), launch_write.fileno(),
                                 stdin_read.fileno(),
                                 *(write.fileno() for _, write in output_pipes.values()))
                finally:
                    os._exit(125)
            custody.update(pid=pid, stage="await-session")
            gate_read.close()
            launch_write.close()
            stdin_read.close()
            for _, write in output_pipes.values():
                write.close()
            save_record(hold, custody)

            def pump(until):
                for key, _ in selector.select(max(0, min(0.02, until - time.monotonic()))):
                    stream = key.data
                    try:
                        chunk = os.read(key.fd, 1 if stream == "launch" else 65536)
                    except BlockingIOError:
                        continue
                    if stream == "launch":
                        if custody["stage"] == "await-session":
                            require(chunk == b"R", "owned command session was not confirmed")
                            custody.update(pgid=pid, stage="await-exec")
                            save_record(hold, custody)
                            require(time.monotonic() < deadline, "command launch exceeded its budget")
                            os.set_blocking(gate_write.fileno(), False)
                            require(gate_write.write(b"G") == 1, "incomplete command handoff")
                            gate_write.close()
                        else:
                            require(not chunk, "owned command exec failed")
                            custody["execPipeEOF"] = True
                            selector.unregister(key.fileobj)
                    elif chunk:
                        room = COMMAND_LOG_LIMIT - len(buffers[stream])
                        buffers[stream].extend(chunk[:room])
                        custody["outputLimitExceeded"] |= len(chunk) > room
                    else:
                        custody[stream + "EOF"] = True
                        selector.unregister(key.fileobj)

            def collect(until, *, stopping=False):
                while time.monotonic() < until:
                    pump(until)
                    if not stopping:
                        if custody["outputLimitExceeded"]:
                            return "output-limit"
                        if time.monotonic() >= until:
                            break
                    if selector.get_map():
                        continue
                    custody["stage"] = "reap-direct-child"
                    if not custody["directChildReaped"]:
                        reaped, status = os.waitpid(pid, os.WNOHANG)
                        require(reaped in (0, pid), "unexpected waitpid identity")
                        if reaped == pid:
                            custody.update(exit=os.waitstatus_to_exitcode(status), directChildReaped=True)
                    if custody["directChildReaped"]:
                        custody["stage"] = "observe-group-absence"
                        if group_absent(pid):
                            custody["groupAbsent"] = True
                            return None if time.monotonic() < until else "timeout"
                        time.sleep(max(0, min(0.02, until - time.monotonic())))
                return "timeout"

            stop = collect(deadline)
            if stop:
                custody["stop"] = stop
            if stop and not custody["groupAbsent"]:
                require("pgid" in custody, "owned command session exceeded its budget")
                require(not custody["directChildReaped"], "owned group closure exceeded its budget")
                exec_confirmed = custody["execPipeEOF"]
                if not exec_confirmed:
                    # EOF after SIGKILL cannot establish that exec took place.
                    selector.unregister(launch_read)
                    gate_write.close()
                custody.update(signal="SIGKILL", stage="stop-owned-group")
                save_record(hold, custody)
                custody["signalAttempted"] = True
                try:
                    os.killpg(pid, signal.SIGKILL)
                    custody["signalOutcome"] = "sent"
                except ProcessLookupError:
                    custody["signalOutcome"] = "already-absent"
                except OSError as denied:
                    custody["signalOutcome"] = "denied" if isinstance(denied, PermissionError) else "error"
                    raise
                collect(time.monotonic() + COMMAND_CLEANUP_SECONDS, stopping=True)
                require(custody["groupAbsent"], "owned command closure exceeded its cleanup budget")
                if not exec_confirmed:
                    custody["stage"] = "await-exec"
                    unresolved = TimeoutError("owned command exec exceeded its budget")
            elif custody["exit"] < 0:
                # An unsolicited signal could have closed the launch pipe
                # before exec. A normal close-on-exec EOF is insufficient here.
                custody["stage"] = "await-exec"
                unresolved = RuntimeError("signal left exact command launch unconfirmed")
            if (unresolved is None and name == "go-build"
                    and (custody["signalAttempted"] or custody["exit"] != 0)):
                # Failed or interrupted Go builds can leave tools outside the driver group.
                custody["stage"] = "observe-go-descendants"
                unresolved = RuntimeError("Go build has no descendant closure")
        custody["descriptorsClosed"] = True
        if unresolved is not None:
            raise unresolved
    except BaseException as error:
        try:
            persist_logs()
        except OSError as log_error:
            error.add_note(f"Command log persistence failed: {log_error}")
        if os.path.lexists(hold):
            retain_hold(hold, custody, error)
        raise
    custody["stage"] = "record-terminal"
    try:
        persist_logs()
        custody["custody"] = "TERMINAL"
        save_record(logs / "result.json", custody)
        hold.unlink()
    except BaseException as error:
        retain_hold(hold, custody, error)
    require(not custody.get("stop") and not custody["outputLimitExceeded"] and custody["exit"] == 0,
            f"{name} failed or exceeded its budget. See {logs}")
    return bytes(buffers["stdout"])


def retain_hold(hold, custody, error):
    failure = CustodyUnknown(f"{custody['command']} custody unresolved. Preserve {hold.parent}")
    custody.update(custody="UNKNOWN", errorType=type(error).__name__, error=str(error))
    try:
        save_record(hold, custody)
    except OSError as persistence_error:
        failure.add_note(f"Hold update failed: {persistence_error}")
    raise failure from error


def settlement(args):
    root = args.run_root
    require(private_path(root).st_mode == (stat.S_IFDIR | 0o700), "expected a private run root")
    require(not os.path.lexists(root / "HOLD.json"), "run root has unresolved custody")
    receipt = root / "settlement.json"
    private_path(receipt, 0o600)
    raw = receipt.read_bytes()
    require(sha(raw) == args.settlement_sha256, "settlement receipt digest differs")
    proof = json.loads(raw)
    require(proof["base"] == BASE and proof["xcodeInvocations"] == 1
            and proof["liveCustodyPending"] is False and not proof.get("custodyHold"),
            "expected a fresh v74 compile with closed custody")
    for name in ("processor", "worker"):
        closed = proof["commands"][name]
        require(closed["exit"] == 0 and closed["groupAbsent"] is True, f"{name} did not close")
    closure = proof["liveClosure"]
    require(closure["xcodeExit"] == 0 and HEX.fullmatch(closure["xcodeReceiptSHA256"]),
            "successful Xcode closure is missing")
    selected = proof["binding"]
    record, operation, ref, spec = (selected[k] for k in ("record_id", "operation_id", "ref", "spec"))
    require(re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", record)
            and HEX.fullmatch(operation), "invalid build record or worker operation")
    scope = {key: spec[key] for key in (*IDS, *PINS[1:])}
    scope["source_sha256"] = spec["source"]["sha256"]
    require(scope["platform"] == "ios" and all(HEX.fullmatch(scope[key]) for key in PINS)
            and all(re.fullmatch(r"[A-Za-z0-9._-]{1,128}", scope[key])
                    and scope[key] not in (".", "..") for key in IDS)
            and ref == {key: scope[key] for key in IDS} | {"attempt": 1, "fence": 1},
            "expected one exact first-attempt iOS selection")
    identity = ["mixer-build-operation-v1", record, *(scope[k] for k in IDS), 1, 1]
    require(operation == sha(json.dumps(identity, separators=(",", ":")).encode()),
            "worker operation differs from the stock dispatch identity")

    settled = proof["settled"]
    subjects = settled["artifacts"]
    require([item["kind"] for item in subjects] == list(KINDS), "expected three retained products")
    for subject in subjects:
        limit = INVENTORY_LIMIT if subject["kind"] == KINDS[2] else ARCHIVE_LIMIT
        require(set(subject) == {"kind", "sizeBytes", "sha256"} and HEX.fullmatch(subject["sha256"])
                and type(subject["sizeBytes"]) is int and 0 < subject["sizeBytes"] <= limit,
                "invalid retained product identity")
    start, completed = settled["journal"]
    require(0 < start["now_ms"] <= completed["now_ms"] <= selected["deadline_ms"]
            and start["event"] == {"type": "start", "ref": ref}
            and completed["event"] == {"type": "completed", "ref": ref, "result": {
                "outcome": "native_succeeded",
                "artifacts": [{"kind": a["kind"], "sha256": a["sha256"], "size_bytes": a["sizeBytes"]}
                              for a in subjects],
            }}, "journal did not settle the exact subjects")
    return proof, scope, record, operation, subjects


def admit_worker(root, proof, operation, subjects):
    ledger = root / "worker/operations.sqlite"
    require(stat.S_ISREG(private_path(ledger).st_mode), "invalid fresh worker ledger")
    with closing(sqlite3.connect(ledger.as_uri() + "?mode=ro", uri=True, timeout=1)) as database:
        database.execute("BEGIN")
        entry = database.execute("SELECT value FROM operations WHERE id=?", (operation,)).fetchone()
        claim = database.execute("""SELECT plan_sha256, guard, parent_pid, launch, terminal, uncertain
            FROM ios_custody_claims WHERE operation=?""", (operation,)).fetchone()
    require(entry is not None and claim is not None and claim[-1] == 0
            and claim[3] is not None and claim[4] is not None,
            "exact worker custody claim has no positive terminal authority")
    row = json.loads(entry[0])
    closure = row["closure"]
    selected = proof["binding"]
    require(row["binding"] == {key: selected[key] for key in ("spec", "ref", "deadline_ms")}
            and row["status"] == "native_ready" and type(row["starts"]) is int and row["starts"] == 1
            and not row.get("tombstone")
            and row["artifacts"] == subjects and row["manifest_sha256"] == proof["settled"]["manifestSHA256"]
            and closure["closed"] is True and closure["started"] is True
            and closure["cli_reaped"] is True and closure["cli_group_absent"] is True,
            "worker ledger differs from the closed compile")

    plan, guard, parent, launch, terminal, _ = claim
    intent = row["ios_custody"]
    require(plan == sha(native.literal(dict(operation_id=operation, binding=row["binding"], intent=intent)).encode())
            and guard == native.literal(intent["guard"]) and type(parent) is int and parent > 1,
            "worker custody claim differs from the exact admitted plan")
    try:
        launch, terminal = json.loads(launch), json.loads(terminal)
        pid = launch["pid"]
        expected_launch = dict(pid=pid, pgid=pid, sid=pid)
        expected_outer = dict(expected_launch, parent_pid=parent, exit=0, direct_child_reaped=True,
                              group_absent=True, descriptors_closed=True)
        require(type(pid) is int and pid > 1 and pid != parent
                and native.literal(launch) == native.literal(expected_launch)
                and native.literal(terminal["outer"]) == native.literal(expected_outer)
                and set(terminal) == {"outer", "nested", "outcome"}
                and terminal["outcome"] == closure["ios_outcome"] == "succeeded"
                and native.literal(terminal) == native.literal(closure["ios_custody"])
                == native.literal(proof["liveClosure"]["claim"])
                and native.literal((pid, 0)) == native.literal((closure["pid"], closure["exit"])),
                "worker custody claim differs from the settled outer receipt")
        output = root / "worker" / operation
        tmp = output / "tmp"
        require(not os.path.lexists(tmp / "cancel-requested"), "worker custody claim was cancelled")
        (_, receipts), nested = ios.nested_closure(native, tmp, intent["recipe"]["inputs"])
        require(len(receipts) == 2 and receipts[0][0]["command"] == ["/usr/bin/swift", "--version"]
                and terminal["nested"] == nested and ios.classify(0, receipts, stop_requested=False) == "succeeded",
                "worker custody claim differs from the exact nested receipts")
    except (native.Refusal, KeyError, TypeError, ValueError) as error:
        raise RuntimeError("worker custody claim lacks the v74 terminal receipt contract") from error
    compiler, compiler_sha = receipts[-1]
    commands = [dict(command=item["command"][0], pid=item["pid"], receipt_sha256=digest,
                     stop_reason=item.get("stopReason"), group_terminate_sent=item.get("groupTerminateSent", False))
                for item, digest in receipts]
    require(compiler["command"][0] == "/usr/bin/xcodebuild"
            and compiler_sha == proof["liveClosure"]["xcodeReceiptSHA256"]
            and compiler["directory"] == str(output / "project")
            and receipts[0][0]["exitCode"] == 0 and receipts[0][0].get("stopReason") is None
            and receipts[0][0]["terminalNS"] <= compiler["runtimeStartedNS"]
            and native.literal(closure["commands"]) == native.literal(commands),
            "worker custody claim differs from the settled Swift and Xcode receipts")

    manifest = output / "native/native-build.json"
    require(stat.S_ISREG(private_path(manifest).st_mode), "invalid fresh native report")
    raw = manifest.read_bytes()
    require(sha(raw) == row["manifest_sha256"], "retained native report digest differs")
    report = json.loads(raw)
    binding, spec = report["binding"], selected["spec"]
    command = binding["command"]
    require(report["formatVersion"] == 2 and report["scope"] == "unsigned-simulator/local-development"
            and report["commandResult"]["exitCode"] == 0
            and binding["authoritativeSourceDigest"] == spec["source"]["sha256"]
            and binding["lockSHA256"] == spec["toolchain_lock_sha256"]
            and command == compiler["command"] and command[-1] == "build"
            and command[command.index("-destination") + 1] == "generic/platform=iOS Simulator"
            and command[command.index("-sdk") + 1] == "iphonesimulator"
            and "CODE_SIGNING_ALLOWED=NO" in command, "expected an unsigned generic Simulator compile")


def inspect_postgres(args, work, record, label):
    # record has already been restricted to the canonical UUID grammar.
    statement = f"""
    SELECT json_build_object(
      'dataDirectory', current_setting('data_directory'),
      'scope', json_build_array(b.organization_id,b.project_id,b.application_id,b.build_id,b.platform),
      'revision', b.revision, 'journal', b.journal,
      'reservation', json_build_array(r.attempt,r.worker_fence,r.held,r.terminal_event_id),
      'leaseClosed', l.owner_id IS NULL AND l.expires_at IS NULL,
      'attachments', (SELECT coalesce(json_agg(json_build_array(
        a.journal_revision,a.attempt,a.worker_operation_id,a.native_binding_sha256,
        a.signer_key_sha256,a.signing_origin,encode(a.envelope,'hex')
      )), '[]'::json) FROM public.mixer_native_development_attestations a
        WHERE a.build_record_id=b.id))
    FROM public.mixer_builds b
    JOIN public.mixer_build_reservations r ON r.build_record_id=b.id
    JOIN public.mixer_build_coordinator_leases l ON l.build_record_id=b.id
    WHERE b.id='{record}'::uuid
    """
    env = {"PGCONNECT_TIMEOUT": "3",
           "PGOPTIONS": "-c default_transaction_read_only=on -c statement_timeout=3000"}
    output = run_command(work, label,
        [args.psql, "-XqAtw", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", str(args.pg_port),
         "-U", args.pg_user, "-d", args.pg_database, "-c", statement],
        env=env, seconds=8,
    )
    return json.loads(output)


def get(port, path, token, media, limit):
    with closing(HTTPConnection("127.0.0.1", port, timeout=10)) as connection:
        connection.request("GET", path, headers={"Cookie": "__Host-mixer-session=" + token})
        with connection.getresponse() as response:
            require(response.status == 200 and response.getheader("Content-Type") == media
                    and response.getheader("Cache-Control") == "no-store"
                    and response.getheader("Content-Encoding") is None,
                    "authorized completion or download refused")
            return response.read(limit + 1)


def observe_products(port, query, scope, session, operation, subjects):
    path = "/console-api/v1/build-attestation-completion?" + query
    raw = get(port, path, session, "application/json; charset=utf-8", 16384)
    require(len(raw) <= 16384, "oversized completion detail")
    detail = json.loads(raw)["build"]
    selection = dict(zip(WIRE, (scope[k] for k in (*IDS, *PINS)), strict=True))
    require({k: detail[k] for k in WIRE} == selection
            and (detail["state"], detail["revision"], detail["attempt"], detail["workerOperationId"])
            == ("native_succeeded", 2, 1, operation) and detail["workerCompletionPending"] is False,
            "authorized completion differs from the settled operation")
    for descriptor, subject in zip(detail["artifacts"], subjects, strict=True):
        route = urlsplit(descriptor["downloadPath"])
        expected_path = "/console-api/v1/build-artifacts/" + subject["kind"]
        require({k: descriptor[k] for k in subject} == subject
                and descriptor["downloadPath"] == expected_path + "?" + route.query
                and sorted(parse_qsl(route.query, strict_parsing=True)) == sorted(scope.items()),
                "authorized descriptor differs from the settled product")
        body = get(port, expected_path + "?" + query, session, "application/octet-stream",
                   subject["sizeBytes"])
        require(len(body) == subject["sizeBytes"] and sha(body) == subject["sha256"],
                "authorized download differs from the settled product")
    inventory = json.loads(body)
    binding = inventory["bindingSHA256"]
    require(inventory["version"] == 1 and inventory["kind"] == KINDS[2] and HEX.fullmatch(binding)
            and inventory["parentApp"] == subjects[0]
            and inventory["parentSymbols"] == subjects[1], "resource inventory binding differs")
    return selection, binding


def build_signer(work):
    for name in ("home", "cache", "modules", "tmp", "state"):
        (work / name).mkdir(mode=0o700)
    services = work / "services"
    signer = services / "cmd/mixer-native-attest"
    signer.mkdir(parents=True)
    git = ["git", "--no-lazy-fetch", "--no-replace-objects"]
    git_env = dict(PATH=os.environ["PATH"], HOME=str(work / "home"), TMPDIR=str(work / "tmp"),
                   GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM="1")
    for name in ("go.mod", "go.sum"):
        data = run_command(work, name, [*git, "cat-file", "blob", f"{BASE}:services/{name}"],
                           cwd=REPO, env=git_env, seconds=10)
        (services / name).write_bytes(data)
    archive = run_command(work, "stock-source", [*git, "archive", "--format=tar", SIGNER_TREE],
                          cwd=REPO, env=git_env, seconds=10)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source:
        for member in source:
            require(member.isfile() and re.fullmatch(r"[A-Za-z0-9_.-]+", member.name)
                    and member.name not in {".", ".."} and member.name not in files,
                    "invalid stock signer Git archive entry")
            with source.extractfile(member) as stream:
                files[member.name] = stream.read()

    def object_id(kind, data):
        return hashlib.sha1(f"{kind} {len(data)}\0".encode() + data, usedforsecurity=False).digest()

    tree = b"".join(b"100644 " + name.encode() + b"\0" + object_id("blob", files[name])
                    for name in sorted(files))
    require(object_id("tree", tree).hex() == SIGNER_TREE, "stock signer Git tree differs")
    for name, data in files.items():
        (signer / name).write_bytes(data)
    env = dict(PATH=os.environ["PATH"], HOME=str(work / "home"), CGO_ENABLED="1", CC="/usr/bin/clang",
               GOTOOLCHAIN="local", GOENV="off", GOWORK="off", GOPROXY="off", GOSUMDB="off",
               GOTELEMETRY="off", GOCACHE=str(work / "cache"), GOMODCACHE=str(work / "modules"),
               GOTMPDIR=str(work / "tmp"), TMPDIR=str(work / "tmp"))
    tool = work / "mixer-native-attest"
    version = run_command(work, "go-version", ["go", "version"], env=env, seconds=10).decode().strip()
    run_command(work, "go-build", ["go", "-C", services, "build", "-mod=readonly", "-buildvcs=false",
                                   "-trimpath", "-o", tool, "./cmd/mixer-native-attest"], env=env, seconds=180)
    return tool, version


def prove(args):
    proof, scope, record, operation, subjects = settlement(args)
    root = args.run_root
    work = root / "attestation"
    require(not os.path.lexists(work), "expected fresh attestation state")
    admit_worker(root, proof, operation, subjects)
    work.mkdir(mode=0o700)
    before = inspect_postgres(args, work, record, "psql-before")
    journal = before["journal"]
    require(before["dataDirectory"] == str(root / "pg")
            and before["scope"] == [scope[k] for k in IDS]
            and before["revision"] == 2 and journal["events"] == proof["settled"]["journal"]
            and journal["creation"]["spec"] == proof["binding"]["spec"]
            and before["reservation"] == [1, 1, False, journal["events"][-1]["id"]]
            and before["leaseClosed"] is True and before["attachments"] == [],
            "PostgreSQL does not show the same unattested settlement")

    for path in (args.session, args.bearer, args.private_key, args.public_key):
        private_path(path, 0o600)
        require(not path.is_relative_to(root), "keep credentials and keys outside the build root")
    session = args.session.read_text().removesuffix("\n")
    bearer = args.bearer.read_text().removesuffix("\n")
    require(re.fullmatch(r"[A-Za-z0-9_-]{43}", session)
            and base64.urlsafe_b64encode(base64.urlsafe_b64decode(session + "=")).decode() == session + "="
            and re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", bearer) and len(bearer) <= 4089,
            "expected fresh synthetic session and bearer tokens")
    pem = args.public_key.read_bytes().splitlines()
    require(len(pem) == 3 and pem[0] == b"-----BEGIN PUBLIC KEY-----"
            and pem[2] == b"-----END PUBLIC KEY-----", "expected a public SPKI PEM")
    spki = base64.b64decode(pem[1], validate=True)
    key_id = sha(spki)
    require(len(spki) == 44 and spki.startswith(bytes.fromhex("302a300506032b6570032100"))
            and key_id == args.enrolled_spki_sha256, "public key differs from the enrolled Ed25519 key")

    query = urlencode({key: scope[key] for key in (*IDS, *PINS)})
    origin = f"http://127.0.0.1:{args.api_port}"
    selection, binding = observe_products(args.api_port, query, scope, session, operation, subjects)
    expected = dict(profile=PROFILE, origin=origin, keyId=key_id, selection=selection,
                    provenance=dict(journalRevision=2, attempt=1, nativeBindingSha256=binding,
                                    workerOperationId=operation), subjects=subjects)
    expected_path = work / "expected-statement.json"
    with expected_path.open("x") as stream:
        json.dump(expected, stream)
        os.fchmod(stream.fileno(), 0o400)
    tool, go_version = build_signer(work)
    state = work / "state"

    def call(label, action, key, token, *options, seconds):
        return run_command(work, label,
            [tool, action, "-origin", origin, "-selection", query, "-state", state, "-key", key, *options],
            secret=(token + "\n").encode(), env={"PATH": "/usr/bin:/bin"}, seconds=seconds,
        ).decode().strip()

    filename = sha("\0".join(scope[k] for k in (*IDS[:3], "platform", "build_id")).encode()) + ".json"
    require(call("sign", "sign", args.private_key, session, "-expected-statement", expected_path,
                 seconds=135) == filename,
            "unexpected signed envelope name")
    envelope = (state / filename).read_bytes()
    require(json.loads(envelope)["statement"] == expected, "signed statement differs from the admitted completion")
    stored = before | {"attachments": [[2, 1, operation, binding, key_id, origin, envelope.hex()]]}
    for status in ("attached", "duplicate"):
        require(call("attach-" + status, "attach", args.public_key, bearer, seconds=45) == status,
                f"expected {status} from ordinary Phoenix")
        require(inspect_postgres(args, work, record, "psql-" + status) == stored
                and (state / filename).read_bytes() == envelope,
                "attachment bytes, cardinality, or settled build changed")
    return dict(base=BASE, go=go_version, signerTree=SIGNER_TREE, signerSHA256=sha(tool.read_bytes()), origin=origin,
                settlementSHA256=args.settlement_sha256, recordId=record, workerOperationId=operation,
                journalRevision=2, attempt=1, subjects=subjects, signerKeySHA256=key_id,
                nativeBindingSHA256=binding, attachmentHTTP=[201, 200], persistedRows=1,
                byteExact=True, journalUnchanged=True, envelopeSHA256=sha(envelope),
                envelopeSizeBytes=len(envelope), buildPOSTs=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run-root", "session", "bearer", "private-key", "public-key"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("settlement-sha256", "enrolled-spki-sha256"):
        parser.add_argument("--" + name, required=True)
    for name in ("api-port", "pg-port"):
        parser.add_argument("--" + name, required=True, type=int)
    parser.add_argument("--pg-user", default="fixture_admin")
    parser.add_argument("--pg-database", default="browser_ordinary_installation_r1422")
    parser.add_argument("--psql", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin/psql"))
    args = parser.parse_args()
    if (not all(1024 <= port <= 65535 for port in (args.api_port, args.pg_port))
            or args.api_port == args.pg_port or not args.psql.is_absolute()
            or not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value)
                       for value in (args.pg_user, args.pg_database))
            or not all(HEX.fullmatch(value) for value in (args.settlement_sha256, args.enrolled_spki_sha256))):
        parser.error("expected distinct loopback fixture ports, a psql path, fixture identifiers and SHA-256 pins")
    os.umask(0o077)
    try:
        print(json.dumps(prove(args), indent=2))
    except CustodyUnknown as error:
        print(error, file=sys.stderr)
        return 74
    return 0


if __name__ == "__main__":
    sys.exit(main())
