"""Finite loopback telemetry bridge, activated only by the root-owned runner.

No request can select a path, process, device, shell command, or input event.
The capability is process memory only; HTTP request/header logging is disabled.
"""
import hashlib
import hmac
import json
import math
import os
import pathlib
import stat
import time
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from oracle import ACTIONS, CASES, CASE_ACTION, CASE_COMMAND_SEQUENCE, COMMANDS, geometry_valid, verdict

MAX_BODY = 8192
MAX_OBSERVATION = 16_000_000
MAX_RESPONSE = 2_000_000

def require(ok, reason):
    if not ok: raise ValueError(reason)

def json_bytes(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def read_observation(documents):
    path = documents / "observations.json"
    require(path.resolve() == path and documents.resolve() == documents, "Observation path redirected")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= MAX_OBSERVATION, "Invalid observation file: mode=" + oct(info.st_mode) + ",links=" + str(info.st_nlink) + ",bytes=" + str(info.st_size) + ",inode=" + str(info.st_ino))
        with os.fdopen(descriptor, "rb", closefd=False) as stream: payload = stream.read(MAX_OBSERVATION + 1)
        require(len(payload) <= MAX_OBSERVATION, "Observation exceeds bound")
    finally: os.close(descriptor)
    value = json.loads(payload)
    require(isinstance(value, dict) and isinstance(value.get("state"), dict) and isinstance(value.get("events"), list) and value["events"], "Malformed observations")
    state = value["state"]
    require(type(state.get("identity")) is str and all(type(state.get(key)) is bool for key in ("isOn", "retainedOn", "enabled", "allowed")), "Malformed native state")
    signature = [info.st_ino, info.st_mtime_ns, len(payload), hashlib.sha256(payload).hexdigest()]
    return value, signature

class Bridge:
    def __init__(self, documents, output, capability, device_identity, lifetime=600, allowed_cases=None):
        require(set(documents) == {"diagnostic", "comparator"}, "Two fixed app containers required")
        self.documents = {key: pathlib.Path(path) for key, path in documents.items()}
        self.output = pathlib.Path(output)
        self.capability = capability
        self.identity = device_identity
        self.deadline = time.monotonic() + min(900, max(60, lifetime))
        self.allowed_cases = set(CASES if allowed_cases is None else allowed_cases)
        require(self.allowed_cases and self.allowed_cases <= CASES, "Unknown closed scope")
        self.last_observation = None
        self.current = None
        self.generation = 0
        self.verdicts = []
        self.failures = []
        self.output.mkdir(parents=True, exist_ok=False)
        self.persist_summary()
    def save(self, suffix, value):
        path = self.output / f"{self.generation:04d}-{suffix}.json"
        require(not path.exists(), "Evidence file already exists")
        with path.open("xb") as stream:
            stream.write(json_bytes(value) + b"\n"); stream.flush(); os.fsync(stream.fileno())
    def persist_summary(self):
        value = {"generation": self.generation, "currentCase": None if self.current is None else self.current["case"],
                 "allowedCases": sorted(self.allowed_cases), "verdicts": self.verdicts, "failures": self.failures,
                 "lastValidObservationAvailable": self.last_observation is not None, "capabilityRetained": False}
        payload = json_bytes(value) + b"\n"
        descriptor, name = tempfile.mkstemp(prefix=".summary-", dir=self.output)
        try:
            with os.fdopen(descriptor, "wb") as stream: stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            os.replace(name, self.output / "bridge-summary.json")
            directory = os.open(self.output, os.O_RDONLY)
            try: os.fsync(directory)
            finally: os.close(directory)
        finally:
            if os.path.exists(name): os.unlink(name)
    def record_failure(self, op, error):
        reason = (type(error).__name__ + ": " + str(error)).replace(self.capability, "[ephemeral-capability-redacted]")
        entry = {"sequence": len(self.failures) + 1, "operation": op if op in {"begin", "ready", "command", "baseline", "evaluate"} else "framing-or-unknown-route",
                 "reason": reason, "generation": self.generation, "case": None if self.current is None else self.current["case"],
                 "lastValidObservationAvailable": self.last_observation is not None}
        self.failures.append(entry)
        self.save("failure-" + str(entry["sequence"]), {**entry, "lastValidObservation": self.last_observation})
        self.persist_summary()
        return reason
    def observe(self):
        observed = read_observation(self.documents[self.current["candidate"]])
        self.last_observation = {"observation": observed[0], "signature": observed[1]}
        return observed
    def write_command(self, command):
        require(command in COMMANDS, "Unsupported fixture command")
        path = self.documents[self.current["candidate"]] / "command.txt"
        require(path.resolve() == path, "Command path redirected")
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(descriptor)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "Invalid command file")
            os.ftruncate(descriptor, 0)
            os.write(descriptor, command.encode()); os.fsync(descriptor)
        finally: os.close(descriptor)
    def wait(self, predicate, seconds=6):
        deadline = min(self.deadline, time.monotonic() + seconds)
        last = None
        while time.monotonic() < deadline:
            try:
                value, signature = self.observe()
                last = (value, signature)
                if predicate(value, signature): return last
            except (FileNotFoundError, json.JSONDecodeError): pass
            time.sleep(0.025)
        if last: self.save("timeout-observation", {"observation": last[0], "signature": last[1]})
        raise TimeoutError("Bounded native observation wait expired")
    def request(self, op, body):
        try:
            result = self._request(op, body)
            self.persist_summary()
            return result
        except BaseException as error:
            self.record_failure(op, error)
            raise
    def _request(self, op, body):
        require(time.monotonic() < self.deadline, "Bridge lifetime exceeded")
        require(isinstance(body, dict), "Object body required")
        if op == "begin":
            require(set(body) == {"candidate", "case"} and body["candidate"] in self.documents and body["case"] in self.allowed_cases, "Invalid begin request")
            require((body["candidate"] == "comparator") == body["case"].startswith("comparator-"), "Candidate/case mismatch")
            require(not any(result["case"] == body["case"] for result in self.verdicts), "Case already completed")
            self.last_observation = None
            self.generation += 1
            self.current = {**body, "generation": self.generation, "begunWallNS": time.time_ns(), "actionIndex": 0}
            try: _, signature = self.observe()
            except FileNotFoundError: signature = None
            self.current["priorSignature"] = signature
            # The reviewed XCTest caller terminates this app before begin. Prime
            # one existing command so a previous failed case cannot replay a
            # self-test or leave the first acknowledged command at the same stage.
            self.write_command("reset")
            self.current["prelaunchCommand"] = "reset"
            self.save("begin", {**self.current, "ownedSimulatorIdentity": self.identity})
            return {"generation": self.generation}
        require(self.current is not None, "Begin required")
        if op == "ready":
            require(not body and "ready" not in self.current, "Invalid ready request")
            value, signature = self.wait(lambda v, s: s != self.current["priorSignature"] and s[1] >= self.current["begunWallNS"] and v["events"][0]["sequence"] == 0)
            self.current["ready"] = True
            self.current["nativeIdentity"] = value["state"]["identity"]
            self.save("ready", {"generation": self.generation, "signature": signature, "observation": value})
            return {"generation": self.generation, "state": value["state"]}
        require(self.current.get("ready"), "New launch generation not acknowledged")
        value, signature = self.observe()
        require(value["state"]["identity"] == self.current["nativeIdentity"], "Native process generation changed")
        if op == "command":
            require(set(body) == {"command"} and body["command"] in COMMANDS, "Invalid fixture command")
            command = body["command"]
            sequence = CASE_COMMAND_SEQUENCE[self.current["case"]]
            index = self.current.get("commandGeneration", 0)
            require(index < len(sequence) and sequence[index] == command, "Command outside fixed case sequence")
            require(command != "self-tests" or "baseline" in self.current, "Direct suite needs baseline before command")
            require(value["stage"] != command, "Same-stage command cannot acknowledge a new generation")
            before_events = len(value["events"])
            self.write_command(command)
            def acknowledged(v, s):
                complete = command != "self-tests" or (v.get("diagnosticSuiteState") == "complete" if self.current["candidate"] == "diagnostic" else len(v.get("checks", [])) == 12)
                return s != signature and len(v["events"]) > before_events and v["stage"] == command and v["state"]["identity"] == self.current["nativeIdentity"] and complete
            after, after_signature = self.wait(acknowledged)
            self.current["commandGeneration"] = self.current.get("commandGeneration", 0) + 1
            self.save("command-" + str(self.current["commandGeneration"]), {"command": command, "generation": self.generation, "commandGeneration": self.current["commandGeneration"], "beforeSignature": signature, "afterSignature": after_signature, "observation": after})
            return {"generation": self.generation, "commandGeneration": self.current["commandGeneration"], "state": after["state"]}
        if op == "baseline":
            require(set(body) == {"action", "geometry"} and body["action"] in ACTIONS and CASE_ACTION[self.current["case"]] == body["action"] and geometry_valid(body["geometry"]), "Invalid closed action/geometry")
            require("baseline" not in self.current, "Previous action not evaluated")
            sequence = CASE_COMMAND_SEQUENCE[self.current["case"]]
            expected = len(sequence) - (1 if body["action"] == "direct-suite" else 0)
            require(self.current.get("commandGeneration", 0) == expected, "All fixed setup commands must be acknowledged before baseline")
            self.current["actionIndex"] += 1
            self.current["baseline"] = value
            self.current["baselineSignature"] = signature
            self.current["action"] = body["action"]
            self.save("before-" + str(self.current["actionIndex"]), {**body, "generation": self.generation, "commandGeneration": self.current.get("commandGeneration", 0), "observation": value, "signature": signature})
            return {"generation": self.generation, "state": value["state"]}
        if op == "evaluate":
            require(not body and "baseline" in self.current, "Invalid evaluate request")
            # Native timers/animations get a finite 350ms settle; no guessed success.
            time.sleep(0.35)
            value, signature = self.observe()
            result = verdict(self.current["candidate"], self.current["case"], self.current["action"], self.current.pop("baseline"), value, signature != self.current.pop("baselineSignature"))
            result.update(generation=self.generation, actionIndex=self.current["actionIndex"], ownedSimulatorIdentity=self.identity)
            self.save("after-" + str(self.current["actionIndex"]), {"observation": value, "signature": signature, "verdict": result})
            self.verdicts.append(result)
            return result
        raise ValueError("Unsupported endpoint")

def server_for(bridge):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"
        def log_message(self, *_): pass
        def do_POST(self):
            self.connection.settimeout(2)
            request_started = False
            try:
                require(self.client_address[0] == "127.0.0.1", "Loopback only")
                require(all(len(self.headers.get_all(key, [])) == 1 for key in ("X-Mixer-Capability", "Content-Type", "Content-Length")), "Duplicate or missing security/framing header")
                require(hmac.compare_digest(self.headers.get("X-Mixer-Capability", ""), bridge.capability), "Invalid capability")
                require(self.path in {"/begin", "/ready", "/command", "/baseline", "/evaluate"}, "Unknown endpoint")
                require(self.headers.get("Content-Type") == "application/json" and self.headers.get("Transfer-Encoding") is None, "Unsupported request framing")
                size = int(self.headers.get("Content-Length", "-1"))
                require(0 <= size <= MAX_BODY, "Request exceeds bound")
                raw = self.rfile.read(size)
                require(len(raw) == size, "Incomplete request")
                def pairs(entries):
                    require(len(dict(entries)) == len(entries), "Duplicate JSON key")
                    return dict(entries)
                body = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite number")))
                request_started = True
                result = bridge.request(self.path[1:], body)
                payload = json_bytes(result)
                require(len(payload) <= MAX_RESPONSE, "Response exceeds bound")
                self.send_response(200)
            except Exception as error:
                # Never retain headers, capability, URL parameters, or request payload.
                reason = (type(error).__name__ + ": " + str(error)).replace(bridge.capability, "[ephemeral-capability-redacted]")
                if not request_started: bridge.record_failure("framing", error)
                payload = json_bytes({"error": reason})
                self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            try: self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError) as error: bridge.record_failure("response-delivery", error)
    result = HTTPServer(("127.0.0.1", 0), Handler)
    result.timeout = 0.2
    return result
