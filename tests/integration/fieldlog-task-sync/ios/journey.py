"""Replay a saved-task conflict through FieldLog's model or its ordinary iOS UI."""

from argparse import ArgumentParser
from contextlib import contextmanager, nullcontext
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import secrets
import shutil
import subprocess
from uuid import UUID, uuid4

HERE = Path(__file__).resolve().parent
APP_ID = "dev.mixer.fieldlog"
TEST_TARGET = "FieldLogUITests/FieldLogUITests/"
OFFLINE_TEST = "testSavedTaskConflictSavesOffline"
ONLINE_TEST = "testSavedTaskConflictResolvesAndReopens"
LOCAL_TITLE = "Inspect valve today"
PEER_TEXT = {"title": "Inspect valve after shutdown", "responsible": "Morgan"}
MERGED_TEXT = {"title": LOCAL_TITLE, "responsible": "Morgan"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def document(path):
    return json.loads(path.read_bytes())


def read_workspace(directory):
    return document(directory / "workspace.json")


def task_record(state, task):
    return next(row for row in state["tasks"] if UUID(row["id"]) == UUID(task))


def task_text(state, task):
    saved = task_record(state, task)
    return {field: saved[field] for field in ("title", "responsible")}


def load_fixture():
    path = HERE / "fixture/verification/host/replay-saved-task-sync.py"
    spec = importlib.util.spec_from_file_location("saved_task_sync_fixture", path)
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    return replay, replay.load("local_entry_sync", "Backend/local_entry_sync.py")


def products():
    path = HERE / "ios/FieldLog_iphonesimulator27.2-arm64.xctestrun"
    run = plistlib.loads(path.read_bytes())
    target = run["FieldLogUITests"]
    require(run["__xctestrun_metadata__"]["FormatVersion"] == 1 and target["IsUITestBundle"],
            "Unexpected XCTest build format")
    app = path.parent / "Debug-iphonesimulator/FieldLog.app"
    runner = app.with_name("FieldLogUITests-Runner.app")
    test = runner / "PlugIns/FieldLogUITests.xctest"
    expected = ["__TESTROOT__/" + item.relative_to(path.parent).as_posix()
                for item in (app, runner, test)]
    require(target["DependentProductPaths"] == expected
            and target["TestHostPath"] == expected[1]
            and target["UITargetAppPath"] == expected[0]
            and target["TestBundlePath"] == "__TESTHOST__/PlugIns/FieldLogUITests.xctest"
            and all(item.is_dir() for item in (app, runner, test)),
            "XCTest build does not point to the packaged app and runner")
    app_info = plistlib.loads((app / "Info.plist").read_bytes())
    require(app_info["CFBundleIdentifier"] == APP_ID, "Unexpected FieldLog bundle identifier")
    return path, run, app, test


class UnknownCustody(RuntimeError):
    pass


class SimulatorReplay:
    def __init__(self, device, scratch, environment):
        self.device = device
        self.scratch = scratch
        self.environment = environment
        self.identity = str(uuid4())
        self.marker = f"fixture-{self.identity}"
        self.run, self.spec, _, _ = products()
        self.unknown = False

    def command(self, args, deadline):
        child = subprocess.Popen(args, cwd=self.scratch, env=self.environment,
                                 start_new_session=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
        try:
            output, _ = child.communicate(timeout=deadline)
        except subprocess.TimeoutExpired:
            self.hold(args[0], child.pid, "deadline expired before direct reap and EOF")
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            pass
        except OSError as error:
            self.hold(args[0], child.pid, str(error))
        else:
            self.hold(args[0], child.pid, "group remains present after direct reap")
        return child.returncode, output

    def hold(self, tool, pid, reason):
        self.unknown = True
        path = self.scratch / "HOLD.json"
        path.write_text(json.dumps({"tool": tool, "pid": pid, "pgid": pid, "reason": reason,
                                    "simulator": self.device, "workspace": self.identity}) + "\n")
        raise UnknownCustody(f"Retained the owned chain for root review. See {path}")

    def container_workspace(self):
        code, output = self.command(
            ["xcrun", "simctl", "get_app_container", self.device, APP_ID, "data"], 15)
        container = Path(os.fsdecode(output).strip())
        require(code == 0 and container.is_absolute() and container.is_dir(),
                "Install the packaged FieldLog app on the owned Simulator before running.")
        return container / "Library/Application Support" / f"FieldLogUITest-{self.identity}"

    @contextmanager
    def seeded(self, workspace):
        target = self.container_workspace()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir(mode=0o700)
        (target / self.marker).touch(exist_ok=False)
        try:
            shutil.copyfile(workspace / "workspace.json", target / "workspace.json")
            yield
        finally:
            if not self.unknown:
                active = self.container_workspace()
                self.verify_marker(active)
                shutil.rmtree(active)
                if active != target and (target / self.marker).is_file():
                    self.verify_marker(target)
                    shutil.rmtree(target)

    def verify_marker(self, workspace):
        require(not workspace.is_symlink() and (workspace / self.marker).is_file()
                and not (workspace / self.marker).is_symlink(),
                "Container does not contain this run's workspace marker")

    def snapshot(self):
        active = self.container_workspace()
        self.verify_marker(active)
        return read_workspace(active)

    def test(self, name, fixture, session):
        variables = {"FIELDLOG_UI_TASK_WORKSPACE": self.identity, "FIELDLOG_UI_TASK_ID": fixture["task"]}
        target = self.spec["FieldLogUITests"]
        base = target["EnvironmentVariables"]
        target["EnvironmentVariables"] = base | variables | session
        path = self.run.with_name(f"task-sync-{self.identity}-{name}.xctestrun")
        with path.open("xb") as file:
            plistlib.dump(self.spec, file)
        label = "offline" if name == OFFLINE_TEST else "resolve"
        try:
            code, output = self.command([
                "xcodebuild", "test-without-building", "-xctestrun", str(path),
                "-destination", f"platform=iOS Simulator,id={self.device}",
                "-parallel-testing-enabled", "NO", "-test-timeouts-enabled", "YES",
                "-default-test-execution-time-allowance", "120",
                f"-only-testing:{TEST_TARGET}{name}",
                "-resultBundlePath", str(self.scratch / f"{label}.xcresult"),
            ], 215)
            text = output.decode(errors="replace")
            if token := session.get("FIELDLOG_TASK_SYNC_TOKEN"):
                text = text.replace(token, "[redacted]")
            (self.scratch / f"{label}.log").write_text(text)
            require(code == 0 and "** TEST EXECUTE SUCCEEDED **" in text
                    and f"test case '-[fieldloguitests.fieldloguitests {name.lower()}]' passed"
                    in text.lower(), f"{name} did not pass. See {label}.log")
        finally:
            target["EnvironmentVariables"] = base
            if not self.unknown:
                path.unlink()


def expected_preservation(before, after, task, extra_events):
    for field in ("id", "projects", "entries", "drafts", "restoration"):
        require(after[field] == before[field], f"{field} changed during task sync")
    require([row for row in before["tasks"] if UUID(row["id"]) != UUID(task)]
            == [row for row in after["tasks"] if UUID(row["id"]) != UUID(task)],
            "An unrelated task changed")
    record = task_record(after, task)
    require(record["completed"] and record["position"] == 1, "Checklist state changed")
    count = len(before["outbox"])
    require(after["outbox"][:count] == before["outbox"], "Existing outbox rows changed")
    suffix = after["outbox"][count:]
    require(len(suffix) == extra_events and all(
        row["kind"] == "taskSaved" and UUID(row["recordID"]) == UUID(task) for row in suffix),
        "Outbox carries unexpected events")


def exercise(root, device):
    replay, backend = load_fixture()
    run = replay.load("task_conflict_replay", "verification/host/replay-task-conflict.py").run
    data, db, temporary = root / "replicas", root / "tasks.sqlite3", root / "tmp"
    data.mkdir()
    temporary.mkdir()
    environment = {key: value for key, value in os.environ.items() if not key.startswith("FIELDLOG_")}
    environment["TMPDIR"] = str(temporary) + "/"
    native = SimulatorReplay(device, root, environment) if device else None

    def phase(name, **variables):
        run([HERE / "host/SavedTaskSyncReplay", name, data], replay.SOURCE, environment | variables)

    phase("seed")
    fixture = {key: str(UUID(value)) for key, value in document(data / "fixture.json").items()}
    task = fixture["task"]
    scope = fixture["workspace"], fixture["project"]
    local, peer = data / "local", data / "peer"
    local_token, peer_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    key = ("fieldlog-ios-fixture", *scope, task)
    accounts = {token: (key[0], {scope}) for token in (local_token, peer_token)}
    traffic = []

    class RecordResponses(backend.EntrySyncHandler):
        def _send_json(self, status, body):
            traffic.append((self.command, int(status)))
            super()._send_json(status, body)

    original = task_text(read_workspace(local), task)
    with replay.listener(backend, db, accounts, RecordResponses) as port:
        backend.provision_task(db, *key, original)
        # Exercise the same model entry point used by the iOS menu for the link.
        session = {
            "FIELDLOG_TASK_SYNC_WORKSPACE": scope[0],
            "FIELDLOG_TASK_SYNC_PROJECT": scope[1],
            "FIELDLOG_TASK_SYNC_TASK": task,
            "FIELDLOG_TASK_SYNC_PORT": str(port),
            "FIELDLOG_TASK_SYNC_TOKEN": local_token,
        }
        phase("ui-sync", **session)
        phase("ui-peer-sync", FIELDLOG_PORT=str(port), FIELDLOG_TOKEN_PEER=peer_token)
    require(traffic == [("GET", 200), ("GET", 200)], f"Unexpected provisioning traffic {traffic}")
    phase("ui-baseline")
    baseline = read_workspace(local)

    with native.seeded(local) if native else nullcontext():
        # The existing loopback server is stopped while both editors save.
        phase("ui-peer-offline")
        if native:
            native.test(OFFLINE_TEST, fixture, {})
            offline = native.snapshot()
        else:
            phase("ui-offline")
            offline = read_workspace(local)
        peer_saved = read_workspace(peer)
        require(replay.readback(db) == ((task, 1, original), []),
                "A saved offline edit reached SQLite early")
        require(task_text(offline, task) == {"title": LOCAL_TITLE, "responsible": "Crew"},
                "Offline editor did not save the local title")
        require(task_text(peer_saved, task) == PEER_TEXT, "Peer editor did not save its competing edit")
        expected_preservation(baseline, offline, task, 1)
        offline_event = UUID(offline["outbox"][-1]["id"])
        peer_event = UUID(peer_saved["outbox"][-1]["id"])
        require(offline_event != peer_event, "Offline replicas reused the same event ID")

        with replay.listener(backend, db, accounts, RecordResponses) as port:
            phase("ui-peer-sync", FIELDLOG_PORT=str(port), FIELDLOG_TOKEN_PEER=peer_token)
            peer_head, peer_events = replay.readback(db)
            require(peer_head == (task, 2, PEER_TEXT) and len(peer_events) == 1
                    and peer_events[0][:5] == (*key, str(peer_event)),
                    "SQLite did not commit the event from the competing saved editor")
            session["FIELDLOG_TASK_SYNC_PORT"] = str(port)
            if native:
                native.test(ONLINE_TEST, fixture, session)
                final = native.snapshot()
            else:
                phase("ui-sync", **session)
                pending = read_workspace(local)
                require(task_text(pending, task) == PEER_TEXT and len(pending["pendingTaskEdits"]) == 1,
                        "Peer receipt did not create the title review")
                expected_preservation(baseline, pending, task, 0)
                phase("ui-resolve", **session)
                phase("ui-sync", **session)
                final = read_workspace(local)
            head, events = replay.readback(db)

        require(traffic == [
            ("GET", 200), ("GET", 200), ("POST", 201), ("POST", 409), ("GET", 200), ("POST", 201)
        ], f"Unexpected task traffic {traffic}")
        expected_preservation(baseline, final, task, 0)
        record = task_record(final, task)
        require(task_text(final, task) == MERGED_TEXT and not final.get("pendingTaskEdits")
                and record["textSync"]["head"]["version"] == 3
                and not record["textSync"]["queued"] and not record["textSync"].get("flight"),
                "Cold reopen did not preserve the resolved task and acknowledgement")
        require(head == (task, 3, MERGED_TEXT) and len(events) == 2 and events[:1] == peer_events
                and events[1][:4] == key and UUID(events[1][4]) not in {offline_event, peer_event}
                and events[1][5]["text"] == MERGED_TEXT,
                "SQLite did not commit exactly one selected merge")
    return {"mode": "iOS Simulator" if native else "macOS model",
            "http": traffic, "taskVersion": head[1], "taskEvents": len(events),
            "finalText": head[2], "preservedOutbox": len(baseline["outbox"]),
            "workspace": fixture["workspace"], "task": task,
            "ownedWorkspaceRemoved": True if native else None}


def main():
    parser = ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", action="store_true")
    mode.add_argument("--host", action="store_true")
    mode.add_argument("--simulator", type=UUID)
    parser.add_argument("--scratch", type=Path)
    args = parser.parse_args()
    if args.inspect:
        path, _, app, test = products()
        print(json.dumps({"xctestrun": str(path), "app": str(app), "testBundle": str(test),
                          "selectors": [TEST_TARGET + name for name in (OFFLINE_TEST, ONLINE_TEST)]}))
        return
    if args.scratch is None:
        parser.error("--scratch must point to a new owned directory")
    root = args.scratch.resolve()
    root.mkdir(mode=0o700)
    result = exercise(root, str(args.simulator).upper() if args.simulator else None)
    text = json.dumps(result, indent=2) + "\n"
    (root / "receipt.json").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
