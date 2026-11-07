"""Run-local native custody. This module starts no process on import."""
from pathlib import Path
import hashlib
import json
import os
import secrets
import signal
import time
import process_authority

SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
RECIPES = ["version", "fixture-1-ca", "fixture-1-leaf", "fixture-1-sign",
           "fixture-2-ca", "fixture-2-leaf", "fixture-2-sign"]


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def read(path, cap=131072):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > cap:
        raise ValueError("invalid capped ordinary message: " + str(path))
    def reject(value):
        raise ValueError("non-finite JSON: " + value)
    return json.loads(path.read_bytes(), object_pairs_hook=strict_pairs, parse_constant=reject)


def checked_write(fd, data, writer=os.write):
    """A partial/zero write is a retained I/O failure, never durability."""
    count = writer(fd, data)
    if type(count) is not int or count != len(data):
        raise OSError("incomplete durable write: " + repr(count) + "/" + str(len(data)))


def journal_entries(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 131072:
        raise ValueError("journal ordinary file/cap differs")
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError("truncated journal final record")
    lines = raw.splitlines(keepends=True)
    if len(lines) > 128:
        raise ValueError("journal record cap")
    entries = []
    for sequence, line in enumerate(lines):
        entry = json.loads(line, object_pairs_hook=strict_pairs,
                           parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite journal " + value)))
        if type(entry) is not dict or set(entry) != {"sequence", "event", "ordinal", "at_ns", "detail"}:
            raise ValueError("journal exact fields differ")
        if any(type(entry[key]) is not int for key in ["sequence", "ordinal", "at_ns"]) or entry["sequence"] != sequence:
            raise ValueError("journal sequence/types differ")
        if type(entry["event"]) is not str or type(entry["detail"]) is not str or len(entry["detail"]) > 4096:
            raise ValueError("journal event/detail types differ")
        if encoded(entry) != line:
            raise ValueError("journal canonical record bytes differ")
        entries.append(entry)
    return entries, sha(raw)


def publish(path, value, cap=131072):
    """Hard-link publication refuses an existing final path, including symlinks."""
    path = Path(path)
    data = encoded(value)
    if len(data) > cap:
        raise ValueError("message cap exceeded")
    temporary = path.parent / (".tmp-" + secrets.token_hex(12))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            if stream.write(data) != len(data):
                raise OSError("incomplete immutable message write")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path, follow_symlinks=False)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)
    return sha(data)


def absent(pgid):
    try:
        os.killpg(pgid, 0)
        return False
    except ProcessLookupError:
        return True


def identity_live(pid, pgid, sid):
    try:
        return os.getpgid(pid) == pgid and os.getsid(pid) == sid
    except ProcessLookupError:
        return False


def binding(request):
    keys = ["run_nonce", "phase", "ordinal", "recipe_id", "invocation_nonce", "wrapper_pid", "wrapper_pgid"]
    return {key: request[key] for key in keys}


def validate_request(value, config):
    strings = ["run_nonce", "phase", "recipe_id", "invocation_nonce", "wrapper_path", "wrapper_sha256",
               "interpreter_path", "interpreter_sha256", "native_path", "native_sha256"]
    integers = ["ordinal", "wrapper_pid", "wrapper_pgid", "wrapper_sid", "published_ns"]
    if type(value) is not dict or set(value) != set(strings + integers + ["argv"]):
        raise ValueError("request exact fields differ")
    if any(type(value[key]) is not str or len(value[key]) > 4096 for key in strings):
        raise ValueError("request string type/cap")
    if any(type(value[key]) is not int for key in integers):
        raise ValueError("request integer type")
    if type(value["argv"]) is not list or not 1 <= len(value["argv"]) <= 32 or any(type(x) is not str or len(x) > 4096 for x in value["argv"]):
        raise ValueError("request argv type/cap")
    if value["run_nonce"] != config["run_nonce"] or value["phase"] != "test":
        raise ValueError("request run/phase differs")
    if not 0 <= value["ordinal"] < 16 or not 16 <= len(value["invocation_nonce"]) <= 128:
        raise ValueError("request ordinal/nonce differs")
    for role in ["wrapper", "interpreter", "native"]:
        if value[role + "_path"] != config[role + "_path"] or value[role + "_sha256"] != config[role + "_sha256"]:
            raise ValueError("request pinned identity differs")
    pid, pgid, sid = (value[key] for key in ["wrapper_pid", "wrapper_pgid", "wrapper_sid"])
    if pid <= 1 or pid == os.getpid() or pgid != pid or sid <= 1:
        raise ValueError("request exclusive live group leader differs")


def recipe_args(ordinal, args, directories, config):
    if config["mode"] == "controls":
        if args != config["control_args"]:
            raise ValueError("control recipe differs")
        return
    if ordinal == 0:
        if args != ["version"]:
            raise ValueError("version recipe differs")
        return
    fixture, operation = divmod(ordinal - 1, 3)
    if operation == 0:
        if "-keyout" not in args:
            raise ValueError("missing CA key path")
        candidate = Path(args[args.index("-keyout") + 1])
        directory = candidate.parent
        if candidate.name != "ca.key" or directory.parent != Path(config["owned_tmp"]) or not directory.name.startswith("mixer-key-owner-tls-"):
            raise ValueError("fixture directory outside selected temp")
        if str(directory) in directories.values():
            raise ValueError("fixture directory replay")
        directories[fixture] = str(directory)
    directory = directories.get(fixture)
    if directory is None:
        raise ValueError("fixture recipe out of order")
    expected = [
        ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", directory + "/ca.key", "-out", directory + "/ca.pem", "-days", "1", "-subj", "/CN=Mixer Fixture CA"],
        ["req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout", directory + "/leaf.key", "-out", directory + "/leaf.csr", "-subj", "/CN=jwks.fixture.invalid"],
        ["x509", "-req", "-in", directory + "/leaf.csr", "-CA", directory + "/ca.pem", "-CAkey", directory + "/ca.key", "-CAcreateserial", "-out", directory + "/leaf.pem", "-days", "1", "-extfile", directory + "/leaf.ext"],
    ][operation]
    if args != expected:
        raise ValueError("selected fixture recipe differs")


def validate_transition(value, suffix):
    common = ["run_nonce", "phase", "ordinal", "recipe_id", "invocation_nonce", "wrapper_pid", "wrapper_pgid", "registration_sha256", "ack_sha256"]
    extra = (["child_pid", "child_group", "rapid_exit"] if suffix == "child" else
             ["native_started", "child_pid", "child_reaped", "exit_code", "finished_ns", "errors", "process", "evidence_diagnostics"])
    if type(value) is not dict or set(value) != set(common + extra):
        raise ValueError("transition exact fields differ")
    for key in common:
        kind = int if key in ["ordinal", "wrapper_pid", "wrapper_pgid"] else str
        if type(value[key]) is not kind:
            raise ValueError("transition binding type differs")
    for key in ["child_pid"] + (["child_group"] if suffix == "child" else ["exit_code", "finished_ns"]):
        if type(value[key]) is not int:
            raise ValueError("transition integer type differs")
    for key in (["rapid_exit"] if suffix == "child" else ["native_started", "child_reaped"]):
        if type(value[key]) is not bool:
            raise ValueError("transition boolean type differs")
    if suffix == "completion":
        validate_process_snapshot(value["process"])
        validate_evidence_diagnostics(value["evidence_diagnostics"])
    if suffix == "completion" and (type(value["errors"]) is not list or len(value["errors"]) > 16 or any(type(x) is not str or len(x) > 4096 for x in value["errors"])):
        raise ValueError("completion errors type/cap differs")
    if suffix == "child" and (value["child_pid"] <= 1 or value["child_group"] < 0 or (value["child_group"] == 0 and not value["rapid_exit"])):
        raise ValueError("child PID/group/rapid-exit differs")


def validate_ack(value, request, config, request_sha):
    integers = ["ordinal", "wrapper_pid", "wrapper_pgid", "runner_pid", "ack_deadline_ns", "native_work_deadline_ns", "cleanup_deadline_ns"]
    strings = ["run_nonce", "phase", "recipe_id", "invocation_nonce", "registration_sha256", "execution_plan_sha256"]
    if type(value) is not dict or set(value) != set(integers + strings):
        raise ValueError("ACK exact fields differ")
    if any(type(value[key]) is not int for key in integers) or any(type(value[key]) is not str for key in strings):
        raise ValueError("ACK field types differ")
    if any(value[key] != item for key, item in binding(request).items()) or value["registration_sha256"] != request_sha or value["execution_plan_sha256"] != config["execution_plan_sha256"]:
        raise ValueError("ACK binding differs")
    if value["cleanup_deadline_ns"] != config["cleanup_deadline_ns"] or value["native_work_deadline_ns"] > config["work_deadline_ns"] or value["runner_pid"] <= 1:
        raise ValueError("ACK deadline/runner differs")


def process_context(source, request, native_pid=0):
    return {"source": source, **binding(request), "wrapper_sid": request["wrapper_sid"], "native_pid": native_pid}


def validate_process_snapshot(value):
    if type(value) is not dict or set(value) != {"permission_refused", "operations", "diagnostics"} or type(value["permission_refused"]) is not bool:
        raise ValueError("process snapshot fields/types differ")
    if type(value["operations"]) is not list or len(value["operations"]) > 16 or type(value["diagnostics"]) is not list or len(value["diagnostics"]) > 8:
        raise ValueError("process evidence count differs")
    names = set()
    for row in value["operations"]:
        if type(row) is not dict or set(row) != {"operation", "attempts"} or type(row["operation"]) is not str or not 1 <= len(row["operation"]) <= 128 or type(row["attempts"]) is not int or row["attempts"] < 1 or row["operation"] in names:
            raise ValueError("process operation fields/type/duplicate differs")
        names.add(row["operation"])
    validate_evidence_diagnostics(value["diagnostics"])
    if any(row["operation"] not in names for row in value["diagnostics"]):
        raise ValueError("process diagnostic operation missing")


def validate_evidence_diagnostics(diagnostics):
    if type(diagnostics) is not list or len(diagnostics) > 8:
        raise ValueError("diagnostic evidence cap/type")
    strings = ["source", "run_nonce", "phase", "recipe_id", "invocation_nonce", "operation", "errno_name", "strerror", "exception_type", "message", "traceback"]
    integers = ["ordinal", "wrapper_pid", "wrapper_pgid", "wrapper_sid", "native_pid", "errno", "at_ns"]
    for row in diagnostics:
        if type(row) is not dict or set(row) != set(strings + integers + ["permission_refused"]):
            raise ValueError("process diagnostic exact fields differ")
        if any(type(row[key]) is not str for key in strings) or any(type(row[key]) is not int for key in integers) or type(row["permission_refused"]) is not bool:
            raise ValueError("process diagnostic types differ")


class Custodian:
    def __init__(self, directory, config, journal, cancelled=lambda: False):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700)
        self.config = config
        self.journal = Path(journal)
        self.cancelled = cancelled
        self.records = {}
        self.authorities = {}
        self.process_callbacks = {}
        self.seen = {}
        self.nonces = set()
        self.directories = {}
        self.events = []
        self.errors = []
        self.evidence_diagnostics = []
        self.uncertain = False
        self.open = True
        self.next = 0
        self.grants = 0
        self.ack_publish = publish
        self.journal_write = os.write
        self.journal_fsync = os.fsync
        self.journal_reconciled = False
        self.journal_sha256 = ""
        self.offer(0)

    def event(self, kind, ordinal=-1, detail=""):
        self.journal_reconciled = False
        self.journal_sha256 = ""
        if len(self.events) >= 128 or len(detail) > 4096:
            raise ValueError("custody journal event/detail cap")
        entry = {"sequence": len(self.events), "event": kind, "ordinal": ordinal, "at_ns": time.monotonic_ns(), "detail": detail}
        data = encoded(entry)
        fd = os.open(self.journal, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            checked_write(fd, data, self.journal_write)
            self.journal_fsync(fd)
        finally:
            os.close(fd)
        directory = os.open(self.journal.parent, os.O_RDONLY)
        try:
            self.journal_fsync(directory)
        finally:
            os.close(directory)
        # Memory records only complete, fsynced journal acceptance.
        self.events.append(entry)

    def fail(self, error, uncertain=True):
        self.open = False
        self.uncertain |= uncertain
        message = str(error)[:4096]
        if message not in self.errors and len(self.errors) < 32:
            self.errors.append(message)

    def capture(self, operation, exc, record=None):
        if isinstance(exc, (process_authority.OperationFailure, process_authority.AuthorityRefused)):
            return
        context = process_context("custodian", record) if record is not None else {
            "source": "custodian", "run_nonce": self.config["run_nonce"], "phase": "test", "ordinal": -1,
            "recipe_id": "", "invocation_nonce": "", "wrapper_pid": 0, "wrapper_pgid": 0, "wrapper_sid": 0, "native_pid": 0}
        observation = process_authority.diagnostic(context, operation, exc)
        key = (operation, observation["exception_type"], observation["message"])
        existing = {(row["operation"], row["exception_type"], row["message"]) for row in self.evidence_diagnostics}
        if key not in existing and len(self.evidence_diagnostics) < 8:
            self.evidence_diagnostics.append(observation)

    def offer(self, ordinal):
        limit = 1 if self.config["mode"] == "controls" else 7
        if ordinal < limit and self.open:
            publish(self.directory / f"{ordinal:02d}.offer.json", {"run_nonce": self.config["run_nonce"], "phase": "test", "ordinal": ordinal, "recipe_id": RECIPES[ordinal]}, 4096)

    def close(self):
        self.open = False

    def process(self, record, operation, function, *args, missing_ok=False):
        authority = self.authorities[record["ordinal"]]
        if record["permission_denied"]:
            raise process_authority.AuthorityRefused("custody permission refusal is permanent")
        try:
            callback = self.process_callbacks.get(operation, function)
            return authority.call(operation, callback, *args, missing_ok=missing_ok)
        except process_authority.OperationFailure as exc:
            record["permission_denied"] = authority.permission_refused
            record["authority_closed"] = True
            record["identity_lost"] = True
            record["closure"] = "permission-refused" if authority.permission_refused else "lost-observe"
            self.fail(str(exc))
            try:
                self.event("process-refused", record["ordinal"], json.dumps({"operation": operation, "errno": exc.diagnostic["errno"],
                           "diagnostic_sha256": sha(encoded(exc.diagnostic))}, sort_keys=True))
            except BaseException as journal_error:
                self.fail("process-refusal evidence: " + repr(journal_error))
            raise

    def prove(self, record):
        pgid = self.process(record, "os.getpgid(wrapper_pid)", os.getpgid, record["wrapper_pid"], missing_ok=True)
        sid = self.process(record, "os.getsid(wrapper_pid)", os.getsid, record["wrapper_pid"], missing_ok=True)
        runner_group = self.process(record, "os.getpgrp(runner)", os.getpgrp)
        if pgid != record["wrapper_pgid"] or sid != record["wrapper_sid"] or pgid == runner_group:
            raise ValueError("exclusive live wrapper identity differs")
        record["identity_retained"] = True

    def observe_wrapper_exit(self, pid, returncode):
        """Only the caller's retained Popen wait/poll may supply this witness."""
        if type(returncode) is not int:
            raise ValueError("wrapper exit witness requires a completed direct child")
        for record in self.records.values():
            if record["wrapper_pid"] == pid and not record["wrapper_exit_observed"]:
                record["wrapper_exit_observed"] = True
                record["authority_closed"] = True
                if not record["permission_denied"] and not record["group_absent"]:
                    record["closure"] = "exited-observe"
                if not record["released"]:
                    self.fail("fixture observed wrapper exit before accepted release; custody remains unresolved")

    def inspect(self, record):
        if record["group_absent"] or record.get("permission_denied", False) or record.get("identity_lost", False):
            return False
        missing = self.process(record, "os.killpg(wrapper_pgid,0)", os.killpg, record["wrapper_pgid"], 0, missing_ok=True)
        if missing is process_authority.MISSING:
            record["group_absent"] = True
            record["authority_closed"] = True
            record["closure"] = "group-absent"
            if not record["released"]:
                self.fail("group disappeared before completed exit grant")
            self.event("group-absent", record["ordinal"])
            return False
        # A completed acceptance/release closes active authority permanently,
        # even while the leader is present or awaiting its parent's reap.
        if record["released"] or record["wrapper_exit_observed"] or record["authority_closed"]:
            return False
        if not record["identity_retained"]:
            self.fail("unproven wrapper group; no active authority")
            return False
        pgid = self.process(record, "os.getpgid(wrapper_pid)", os.getpgid, record["wrapper_pid"], missing_ok=True)
        sid = self.process(record, "os.getsid(wrapper_pid)", os.getsid, record["wrapper_pid"], missing_ok=True)
        if pgid != record["wrapper_pgid"] or sid != record["wrapper_sid"]:
            record["identity_lost"] = True
            record["authority_closed"] = True
            record["closure"] = "lost-observe"
            self.fail("leader identity lost while group present")
            self.event("identity-lost", record["ordinal"])
            return False
        return True

    def service(self):
        if self.cancelled() or time.monotonic_ns() >= self.config["work_deadline_ns"]:
            self.close()
        stage = "request-scan"
        active_record = None
        try:
            messages = sorted(self.directory.glob("*.request.json"))
            if len(messages) > 16:
                raise ValueError("custody request cap; accounting incomplete")
            for path in messages:
                request = read(path, 4096)
                raw = path.read_bytes()
                digest = sha(raw)
                if path.name in self.seen:
                    if self.seen[path.name] != digest:
                        raise ValueError("immutable request changed")
                    continue
                self.seen[path.name] = digest
                validate_request(request, self.config)
                ordinal = request["ordinal"]
                if path.name != f"{ordinal:02d}.request.json":
                    raise ValueError("request filename binding differs")
                # Retain the claimed identity first; active cleanup requires proof.
                record = {**binding(request), "wrapper_sid": request["wrapper_sid"], "request_sha256": digest,
                          "ack_sha256": "", "completion_sha256": "", "ack_issued": False,
                          "native_started": False, "child_pid": 0, "child_reaped": False,
                          "released": False, "group_absent": False, "identity_lost": False,
                          "permission_denied": False, "authority_closed": False, "identity_retained": False,
                          "wrapper_exit_observed": False, "closure": "active", "refusal_completion_sha256": ""}
                if ordinal in self.records:
                    self.fail("duplicate ordinal; prior custody retained")
                    continue
                self.records[ordinal] = record
                self.authorities[ordinal] = process_authority.Authority(process_context("custodian", record))
                active_record = record
                stage = "registration-identity-proof"
                self.prove(record)
                stage = "registered-journal-acceptance"
                self.event("registered", ordinal, json.dumps({**binding(request), "wrapper_sid": request["wrapper_sid"], "registration_sha256": digest}, sort_keys=True))
                if request["invocation_nonce"] in self.nonces or ordinal != self.next or request["recipe_id"] != RECIPES[ordinal]:
                    self.fail("duplicate nonce/out-of-order recipe")
                    continue
                self.nonces.add(request["invocation_nonce"])
                recipe_args(ordinal, request["argv"], self.directories, self.config)
                if self.open and self.grants < (1 if self.config["mode"] == "controls" else 7):
                    mask = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
                    try:
                        if self.cancelled() or any(x in SIGNALS for x in signal.sigpending()) or time.monotonic_ns() >= self.config["work_deadline_ns"]:
                            self.close()
                        else:
                            ack = {**binding(request), "registration_sha256": digest, "execution_plan_sha256": self.config["execution_plan_sha256"],
                                   "runner_pid": os.getpid(), "ack_deadline_ns": min(self.config["work_deadline_ns"], time.monotonic_ns() + 1_000_000_000),
                                   "native_work_deadline_ns": min(self.config["work_deadline_ns"], time.monotonic_ns() + self.config["native_seconds"] * 1_000_000_000),
                                   "cleanup_deadline_ns": self.config["cleanup_deadline_ns"]}
                            stage = "ACK-intent-journal-acceptance"
                            self.event("ack-intent", ordinal, json.dumps({"value": ack, "sha256": sha(encoded(ack))}, sort_keys=True))
                            record["ack_sha256"] = sha(encoded(ack))
                            record["ack_issued"] = True
                            self.grants += 1
                            stage = "immutable-ACK-publication"
                            self.ack_publish(self.directory / f"{ordinal:02d}.ack.json", ack, 4096)
                    finally:
                        signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            for ordinal, record in list(self.records.items()):
                active_record = record
                stage = "transition-read-and-validation"
                live = False
                for suffix in ["child", "completion"]:
                    path = self.directory / f"{ordinal:02d}.{suffix}.json"
                    if not path.exists():
                        continue
                    digest = sha(path.read_bytes())
                    if path.name in self.seen:
                        if self.seen[path.name] != digest:
                            raise ValueError("immutable transition changed")
                        continue
                    self.seen[path.name] = digest
                    value = read(path)
                    validate_transition(value, suffix)
                    common = {key: record[key] for key in binding(record)}
                    no_ack_completion = suffix == "completion" and not value["native_started"] and value["ack_sha256"] == ""
                    if any(value.get(key) != item for key, item in common.items()) or value.get("registration_sha256") != record["request_sha256"] or (value.get("ack_sha256") != record["ack_sha256"] and not no_ack_completion):
                        raise ValueError("custody transition binding differs")
                    if suffix == "completion" and value["process"]["permission_refused"]:
                        # Refusal closes authority even if the child-publication
                        # transition is incomplete. Never substitute a group kill.
                        record["permission_denied"] = True
                        record["authority_closed"] = True
                        record["identity_lost"] = True
                        record["closure"] = "permission-refused"
                        record["refusal_completion_sha256"] = digest
                        self.fail("wrapper process permission refusal; wait/group custody remains unresolved")
                    for diagnostic in value.get("process", {}).get("diagnostics", []):
                        expected_context = process_context("wrapper", record, value["child_pid"])
                        if any(diagnostic[key] != item for key, item in expected_context.items()):
                            raise ValueError("wrapper process diagnostic context differs")
                    if suffix == "child":
                        if not record["ack_issued"] or record["native_started"]:
                            raise ValueError("duplicate/unauthorized child transition")
                        record["native_started"] = True
                        record["child_pid"] = value["child_pid"]
                        if value["child_group"] not in [0, record["wrapper_pgid"]]:
                            raise ValueError("native child group differs")
                    else:
                        if record["completion_sha256"] or value["native_started"] != record["native_started"]:
                            raise ValueError("duplicate/incomplete completion transition")
                        if value["child_pid"] != record["child_pid"] or (not value["native_started"] and value["child_pid"] != 0):
                            raise ValueError("completion exact child PID differs")
                        # Full validated completion acceptance is durable before
                        # any leader exit grant can be published.
                        stage = "completion-journal-acceptance"
                        self.event("completion", ordinal, json.dumps({"value": value, "sha256": digest}, sort_keys=True))
                        record["completion_sha256"] = digest
                        record["child_reaped"] = value["child_reaped"]
                        if not value["child_reaped"] or value["errors"]:
                            self.fail("wrapper completion failed: " + repr(value["errors"]))
                        if value["process"]["permission_refused"]:
                            record["permission_denied"] = True
                            record["authority_closed"] = True
                            record["identity_lost"] = True
                            record["closure"] = "permission-refused"
                            self.fail("wrapper process permission refusal; custody remains unresolved")
                        if not record["permission_denied"]:
                            live = self.inspect(record)
                        if live and not record["permission_denied"]:
                            grant = {**common, "completion_sha256": digest}
                            stage = "exit-grant-journal-and-publication"
                            self.event("exit-grant-intent", ordinal, json.dumps({"value": grant, "sha256": sha(encoded(grant))}, sort_keys=True))
                            publish(self.directory / f"{ordinal:02d}.exit.json", grant, 4096)
                            record["released"] = True
                            record["authority_closed"] = True
                            record["closure"] = "released-observe"
                    if suffix == "child":
                        stage = "child-journal-acceptance"
                        self.event("child", ordinal, json.dumps({"value": value, "sha256": digest}, sort_keys=True))
                self.inspect(record)
                if record["group_absent"] and record["released"] and ordinal == self.next:
                    self.next += 1
                    self.offer(self.next)
        except BaseException as exc:
            self.capture("Custodian.service/" + stage, exc, active_record)
            self.fail("Custodian.service/" + stage + ": " + type(exc).__name__ + ": " + str(exc))

    def drain(self, deadline):
        self.close()
        self.service()
        processed = set()
        while time.monotonic() < deadline:
            self.service()
            pending = [record for ordinal, record in self.records.items() if ordinal not in processed]
            if not pending:
                break
            record = pending[0]
            processed.add(record["ordinal"])
            try:
                for sig, allowance in [(signal.SIGTERM, 0.4), (signal.SIGKILL, 0.4)]:
                    if time.monotonic() >= deadline:
                        self.fail("custody cleanup deadline")
                        break
                    if self.inspect(record):
                        self.process(record, "os.killpg(wrapper_pgid," + signal.Signals(sig).name + ")", os.killpg, record["wrapper_pgid"], sig)
                        self.event("signal", record["ordinal"], str(int(sig)))
                    until = min(deadline, time.monotonic() + allowance)
                    while time.monotonic() < until and not record["group_absent"]:
                        self.service()
                        time.sleep(0.01)
            except BaseException as exc:
                self.capture("Custodian.drain", exc, record)
                self.fail("group cleanup: " + repr(exc))
        self.service()
        if any(not value["group_absent"] for value in self.records.values()):
            self.fail("registered group remains or identity lost")

    def reconcile(self):
        """Disk journal, accepted memory and immutable spool must agree exactly."""
        entries, digest = journal_entries(self.journal)
        if any(record["permission_denied"] or record["identity_lost"] for record in self.records.values()):
            raise ValueError("process authority refusal/loss remains unresolved")
        if entries != self.events:
            raise ValueError("disk journal differs from accepted memory events")
        stages = {}
        observed_seen = {}
        def message(ordinal, suffix, expected_hash):
            path = self.directory / f"{ordinal:02d}.{suffix}.json"
            value = read(path)
            if sha(path.read_bytes()) != expected_hash:
                raise ValueError("journal/spool " + suffix + " hash differs")
            return value
        def detail(entry):
            value = json.loads(entry["detail"], object_pairs_hook=strict_pairs)
            if type(value) is not dict:
                raise ValueError("journal transition detail type differs")
            return value
        for entry in entries:
            ordinal, kind = entry["ordinal"], entry["event"]
            if ordinal not in self.records:
                raise ValueError("journal has unretained ordinal")
            record = self.records[ordinal]
            state = stages.setdefault(ordinal, {})
            if kind == "registered":
                if state:
                    raise ValueError("duplicate/out-of-order journal registration")
                request = message(ordinal, "request", record["request_sha256"])
                expected = {**binding(request), "wrapper_sid": request["wrapper_sid"], "registration_sha256": record["request_sha256"]}
                if detail(entry) != expected or record["wrapper_sid"] != request["wrapper_sid"] or any(record[key] != value for key, value in binding(request).items()):
                    raise ValueError("journal registration binding differs")
                state["registered"] = request
                observed_seen[f"{ordinal:02d}.request.json"] = record["request_sha256"]
                continue
            if "registered" not in state or "group-absent" in state:
                raise ValueError("journal transition outside retained lifetime")
            if kind in ["ack-intent", "child", "completion", "exit-grant-intent"]:
                if kind in state:
                    raise ValueError("duplicate accepted journal transition")
                payload = detail(entry)
                if set(payload) != {"value", "sha256"} or type(payload["sha256"]) is not str:
                    raise ValueError("journal transition hash fields differ")
                value = payload["value"]
                suffix = {"ack-intent": "ack", "exit-grant-intent": "exit"}.get(kind, kind)
                if value != message(ordinal, suffix, payload["sha256"]):
                    raise ValueError("journal transition/spool bytes differ")
                if kind == "ack-intent":
                    if any(key in state for key in ["child", "completion", "exit-grant-intent"]):
                        raise ValueError("ACK journal order differs")
                    validate_ack(value, state["registered"], self.config, record["request_sha256"])
                    if not record["ack_issued"] or payload["sha256"] != record["ack_sha256"]:
                        raise ValueError("journal ACK/memory differs")
                elif kind in ["child", "completion"]:
                    validate_transition(value, kind)
                    if any(value[key] != item for key, item in binding(record).items()) or value["registration_sha256"] != record["request_sha256"]:
                        raise ValueError("journal child/completion binding differs")
                    if value["ack_sha256"] != record["ack_sha256"]:
                        raise ValueError("journal child/completion ACK differs")
                    if kind == "child":
                        if "ack-intent" not in state or "completion" in state or value["child_pid"] != record["child_pid"] or value["child_group"] not in [0, record["wrapper_pgid"]]:
                            raise ValueError("journal child order/identity differs")
                    else:
                        if value["native_started"] != record["native_started"] or value["child_pid"] != record["child_pid"] or value["child_reaped"] != record["child_reaped"] or payload["sha256"] != record["completion_sha256"]:
                            raise ValueError("journal completion/memory differs")
                        if value["native_started"] and "child" not in state:
                            raise ValueError("journal completion before child acceptance")
                    observed_seen[f"{ordinal:02d}.{kind}.json"] = payload["sha256"]
                else:
                    if "completion" not in state or value != {**binding(record), "completion_sha256": record["completion_sha256"]} or not record["released"]:
                        raise ValueError("exit grant before durable completion acceptance")
                state[kind] = payload
            elif kind == "group-absent":
                if entry["detail"] or not record["group_absent"] or "exit-grant-intent" not in state:
                    raise ValueError("group absence before accepted exit grant")
                state[kind] = True
            elif kind == "identity-lost":
                if entry["detail"] or not record["identity_lost"] or kind in state:
                    raise ValueError("identity-loss journal differs")
                state[kind] = True
            elif kind == "signal":
                if entry["detail"] not in [str(int(signal.SIGTERM)), str(int(signal.SIGKILL))]:
                    raise ValueError("journal signal differs")
            else:
                raise ValueError("unknown journal transition")
        if set(stages) != set(self.records) or observed_seen != self.seen:
            raise ValueError("journal accepted transition membership differs")
        for ordinal, record in self.records.items():
            state = stages[ordinal]
            for flag, kind in [("ack_issued", "ack-intent"), ("native_started", "child"), ("released", "exit-grant-intent"),
                               ("group_absent", "group-absent"), ("identity_lost", "identity-lost")]:
                if record[flag] != (kind in state):
                    raise ValueError("journal/memory terminal flag differs: " + flag)
            if bool(record["completion_sha256"]) != ("completion" in state):
                raise ValueError("journal/memory completion acceptance differs")
        if self.grants != sum(row["ack_issued"] for row in self.records.values()):
            raise ValueError("journal/memory grant count differs")
        allowed = {f"{ordinal:02d}.{suffix}.json" for ordinal, state in stages.items()
                   for suffix, kind in [("request", "registered"), ("ack", "ack-intent"), ("child", "child"), ("completion", "completion"), ("exit", "exit-grant-intent")] if kind in state}
        limit = 1 if self.config["mode"] == "controls" else 7
        allowed.update(f"{ordinal:02d}.offer.json" for ordinal in range(min(self.next + 1, limit)))
        if {path.name for path in self.directory.iterdir()} != allowed:
            raise ValueError("journal/spool exact membership differs")
        for ordinal in range(min(self.next + 1, limit)):
            if read(self.directory / f"{ordinal:02d}.offer.json") != {"run_nonce": self.config["run_nonce"], "phase": "test", "ordinal": ordinal, "recipe_id": RECIPES[ordinal]}:
                raise ValueError("journal/spool offer binding differs")
        self.journal_reconciled = True
        self.journal_sha256 = digest
        return digest

    def finalize(self):
        try:
            self.reconcile()
        except BaseException as exc:
            self.journal_reconciled = False
            self.journal_sha256 = ""
            self.capture("Custodian.finalize/reconcile", exc)
            self.fail("terminal journal reconciliation: " + repr(exc))

    def snapshot(self):
        return {"schema": 1, "run_nonce": self.config["run_nonce"], "phase": "test", "grants": self.grants,
                "launch_latch_open": self.open, "uncertain": self.uncertain, "errors": self.errors,
                "evidence_diagnostics": self.evidence_diagnostics,
                "records": [{**record, "process": self.authorities[ordinal].snapshot()} for ordinal, record in self.records.items()], "events": self.events,
                "journal_reconciled": self.journal_reconciled, "journal_sha256": self.journal_sha256}
