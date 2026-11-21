#!/usr/bin/env python3
"""Replay F02's original FieldLog callback bodies through the ordinary macOS-hosted model."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from time import monotonic

MIXER = "2acaac67605c369ff1667e3ccc3eb56d376e536e"
HERE = Path(__file__).resolve().parent
PROJECT_DETAIL = "ios/FieldLog/ProjectDetail.swift"
INPUTS = (
    "Package.swift",
    "Sources/FieldLogModels/Workspace.swift",
    "Sources/FieldLogStorage/WorkspaceRepository.swift",
    "Tests/FieldLogTests/FieldLogTests.swift",
    "ios/FieldLog/WorkspaceModel.swift",
    PROJECT_DETAIL,
)


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


class Replay:
    def __init__(self, scratch, receipt):
        self.scratch = scratch
        self.receipt = receipt
        (scratch / "tmp").mkdir()
        self.env = dict(os.environ, CFFIXED_USER_HOME=str(scratch / "build-home"),
                        TMPDIR=str(scratch / "tmp"), GIT_NO_LAZY_FETCH="1",
                        SWIFTPM_MODULECACHE_OVERRIDE=str(scratch / "modules"))

    def run(self, *argv, timeout=15, home=None, record=False):
        check("unresolvedCustody" not in self.receipt, "Previous command custody is unresolved")
        env = dict(self.env, CFFIXED_USER_HOME=str(home)) if home else self.env
        command = [str(arg) for arg in argv]
        started = monotonic()
        observation = {
            "argv": [arg.replace(str(self.scratch), "$SCRATCH") for arg in command],
            "pid": None, "pgid": None, "exit": None, "groupAbsent": False,
        }
        child = None
        expired = False
        # Popen can be interrupted after spawn and before handing back the child identity.
        self.receipt["unresolvedCustody"] = observation
        try:
            child = subprocess.Popen(command, cwd=self.scratch, env=env, start_new_session=True,
                                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            observation.update(pid=child.pid, pgid=child.pid)
            try:
                stdout, stderr = child.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                expired = True
                if child.poll() is None:
                    try:
                        os.killpg(child.pid, 9)
                    except ProcessLookupError:
                        pass
                stdout, stderr = child.communicate(timeout=3)
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                observation["groupAbsent"] = True
                del self.receipt["unresolvedCustody"]
                self.receipt["reapedGroups"] += 1
        finally:
            observation["seconds"] = round(monotonic() - started, 3)
            if child is not None:
                observation["exit"] = child.returncode
            if record or observation["exit"] != 0 or not observation["groupAbsent"]:
                self.receipt["commands"].append(observation)
            if child is not None:
                child.stdout.close()
                child.stderr.close()
        check(observation["groupAbsent"], "Owned process group absence was unobserved")
        check(not expired, f"{command[0]} exceeded its {timeout}s deadline")
        check(child.returncode == 0, f"{command[0]} exited {child.returncode}\n"
              + (stdout + stderr).decode(errors="replace")[-5000:])
        return stdout

    def git(self, repo, *args):
        return self.run("git", "-C", repo, *args)

    def build(self, repo, case, side):
        revision = case[side]
        source = {path: self.git(repo, "show", f"{revision}:{path}") for path in INPUTS}
        tree = self.git(repo, "rev-parse", f"{revision}^{{tree}}").decode().strip()
        source_ids = {path: sha256(data).hexdigest() for path, data in source.items()}
        metadata = self.receipt["fieldlog"][side] = {
            "commit": revision, "tree": tree, "originalSHA256": source_ids,
        }
        for anchor in case["anchors"]:
            path = anchor["path"]
            data = source[path]
            oid = self.git(repo, "rev-parse", f"{revision}:{path}").decode().strip()
            check(oid == anchor[f"{side}Blob"], f"Blob drift for {path}")
            if side == "after":
                start, end = anchor["afterLines"]
                excerpt = b"".join(data.splitlines(keepends=True)[start - 1:end])
                check(sha256(excerpt).hexdigest() == anchor["afterLinesSHA256"],
                      f"Excerpt drift for {path}")

        probe = (HERE / "Probe.swift").read_bytes()
        probe_lines = [line.strip() for line in probe.splitlines()]
        detail_lines = source[PROJECT_DETAIL].splitlines()
        ranges = [(54, 56)] if side == "before" else [(61, 61), (66, 66)]
        for start, end in ranges:
            body = [line.strip() for line in detail_lines[start - 1:end]]
            check(any(probe_lines[i:i + len(body)] == body for i in range(len(probe_lines))),
                  "Probe must call the exact pinned button or .onMove body")

        package = self.scratch / side / "package"
        target = package / "Sources" / "F02Probe"
        target.mkdir(parents=True)
        for path, data in source.items():
            if path == PROJECT_DETAIL:
                continue
            destination = target / Path(path).name if path.startswith("ios/") else package / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        (target / "Probe.swift").write_bytes(probe)
        manifest = package / "Package.swift"
        settings = ', swiftSettings: [.define("F02_BEFORE")]' if side == "before" else ""
        with manifest.open("a") as file:
            file.write('\npackage.targets.append(.executableTarget(name: "F02Probe", '
                       'dependencies: ["FieldLogModels", "FieldLogStorage"]' + settings + '))\n')
        metadata["overlayManifestSHA256"] = sha256(manifest.read_bytes()).hexdigest()
        build = package.parent / "build"
        self.run("swift", "build", "--package-path", package, "--scratch-path", build,
                 "--cache-path", self.scratch / "cache", "--config-path", self.scratch / "config",
                 "--security-path", self.scratch / "security", "--product", "F02Probe",
                 timeout=90, record=True)
        return build / "debug" / "F02Probe"

    def trial(self, binary, side):
        home = self.scratch / side / "home"
        support = home / "Library" / "Application Support"
        support.mkdir(parents=True)
        workspace = support / "FieldLog"
        snapshot_file = workspace / "workspace.json"

        def perform(action):
            model = json.loads(self.run(binary, action, home, home=home, record=action != "reopen"))
            snapshot = snapshot_file.read_bytes()
            check(model == json.loads(snapshot), f"{action}: model and persisted snapshot differ")
            check(sorted(p.name for p in workspace.iterdir()) == ["workspace.json", "workspace.lock"],
                  f"{action}: unexpected files in workspace")
            return model, snapshot

        baseline, _ = perform("seed")
        project = baseline["restoration"]["selectedProjectID"]
        ids = {task["title"]: task["id"] for task in baseline["tasks"]}

        def ordered_rows(state):
            return sorted((t for t in state["tasks"] if t["projectID"] == project),
                          key=lambda task: task["position"])

        initial = ["Inspect", "Measure", "Record"]
        moved = ["Inspect", "Record", "Measure"]
        check([(t["title"], t["position"], t["completed"]) for t in ordered_rows(baseline)]
              == [("Inspect", 0, False), ("Measure", 1, True), ("Record", 2, False)],
              "Fixture failed to establish the initial checklist")
        operations = [("legacy-drag", moved)] if side == "before" else [
            ("down", moved), ("up", initial), ("reject-top-up", initial),
        ]
        results = self.receipt["fieldlog"][side]["observations"] = []
        for action, order in operations:
            prior, prior_bytes = perform("reopen")
            check(prior == baseline, "Cold pre-action open did not load the preceding snapshot")
            actual, actual_bytes = perform(action)
            expected = deepcopy(prior)
            delta = actual["outbox"][len(prior["outbox"]):]
            if action == "reject-top-up":
                check(actual_bytes == prior_bytes, "Rejected boundary action wrote the snapshot")
            else:
                expected["revision"] += 1
                check(len(delta) == 1, "Expected exactly one new outbox record")
                change = delta[0]
                check(change["kind"] == "taskOrderChanged" and change["recordID"] == project
                      and change["revision"] == expected["revision"]
                      and change["id"] not in {row["id"] for row in prior["outbox"]},
                      "Unexpected outbox change")
                expected["outbox"].append(change)
                positions = {ids[title]: index for index, title in enumerate(order)}
                for task in expected["tasks"]:
                    if task["id"] in positions:
                        task["position"] = positions[task["id"]]
                        task["updatedAt"] = change["createdAt"]
            check(actual == expected, f"{action}: snapshot changed outside the expected fields")
            reopened, reopened_bytes = perform("reopen")
            check(reopened == expected and reopened_bytes == actual_bytes,
                  f"{action}: independent cold reopen did not preserve the exact snapshot")
            results.append({
                "action": action, "from": [t["title"] for t in ordered_rows(prior)],
                "coldOrder": [t["title"] for t in ordered_rows(reopened)],
                "revision": [prior["revision"], reopened["revision"]], "outboxDelta": delta,
                "projectID": project, "rowIDs": [t["id"] for t in ordered_rows(reopened)],
                "workspaceSHA256": sha256(reopened_bytes).hexdigest(),
            })
            baseline = reopened


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mixer", type=Path, required=True, help="Git repository with the Mixer pin")
    parser.add_argument("--fieldlog", type=Path, required=True, help="Git repository with both FieldLog pins")
    parser.add_argument("--receipt", type=Path, help="Create a new receipt here, or emit it on stdout")
    args = parser.parse_args()
    scratch = Path(tempfile.mkdtemp(prefix="fieldlog-f02-")).resolve()
    receipt = {"schema": 1, "case": "F02", "status": "INCOMPLETE", "mixer": MIXER,
               "fieldlog": {}, "commands": [], "reapedGroups": 0, "scratch": str(scratch),
               "limits": "macOS callback bodies and original disk model only. iOS menu delivery, "
                         "gestures, AX, pixels, native launch and OTA remain pending.",
               "overlay": "Added one probe target in each temporary copy of the original package "
                          "manifest. Original models, storage and WorkspaceModel compiled verbatim. "
                          "CFFIXED_USER_HOME isolated the ordinary Application Support path.",
               "historicalDependency": "The pinned FieldLog package has no Mixer SDK dependency."}
    replay = Replay(scratch, receipt)
    try:
        mixer, fieldlog = args.mixer.resolve(), args.fieldlog.resolve()
        receipt["tools"] = {
            "swift": replay.run("swift", "--version").decode().strip(),
            "macOS": replay.run("sw_vers").decode().strip(),
        }
        receipt["mixerTree"] = replay.git(mixer, "rev-parse", f"{MIXER}^{{tree}}").decode().strip()
        manifest = "compiler/experiments/fieldlog-change-corpus/corpus.json"
        case = next(row for row in json.loads(replay.git(mixer, "show", f"{MIXER}:{manifest}"))["cases"]
                    if row["id"] == "F02")
        check(replay.git(fieldlog, "rev-parse", f'{case["after"]}^').decode().strip() == case["before"],
              "The two FieldLog pins do not form the corpus parent/child pair")
        receipt["probeSHA256"] = sha256((HERE / "Probe.swift").read_bytes()).hexdigest()
        receipt["runnerSHA256"] = sha256(Path(__file__).read_bytes()).hexdigest()
        for side in ("after", "before"):
            replay.trial(replay.build(fieldlog, case, side), side)
        receipt["status"] = "PASS_SCOPED_HOST"
    except KeyboardInterrupt:
        receipt["error"] = "Interrupted"
        return 130
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        receipt["error"] = str(exc)
    finally:
        receipt["processGroupsClosed"] = "unresolvedCustody" not in receipt
        receipt["scratchRemoved"] = False
        if receipt["processGroupsClosed"]:
            receipt["scratchBytesBeforeRemoval"] = sum(
                path.stat().st_size for path in scratch.rglob("*")
                if not path.is_symlink() and path.is_file()
            )
            shutil.rmtree(scratch)
            receipt["scratchRemoved"] = not scratch.exists()
        output = json.dumps(receipt, indent=2) + "\n"
        if args.receipt:
            with args.receipt.open("x") as file:
                file.write(output)
        else:
            print(output, end="")
    return int(receipt["status"] != "PASS_SCOPED_HOST")


if __name__ == "__main__":
    raise SystemExit(main())
