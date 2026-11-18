#!/usr/bin/env python3
"""Verify FieldLog in place on an explicit fresh Simulator owned by the operator."""
import copy
import errno
import hashlib
import json
import os
import platform
import plistlib
import shutil
import subprocess
import uuid
from pathlib import Path

from upgrade_artifacts import (
    ENGINE_PRODUCTS, FIELDLOG_REV, FIELDLOG_TREE, MIXER_TREES, PAIRS, TOOLCHAIN,
    sha, tool_environment, tree_sha,
)
from workspace_state import compare, compare_containers, require, validate_workspace

APP_ID = "dev.mixer.fieldlog"
RUNNER_ID = APP_ID + ".uitests.xctrunner"
PLUGIN = "PlugIns/FieldLogUITests.xctest/FieldLogUITests"
SEED_NAME = "FieldLog upgrade photo.png"
MARKER = Path("Library/mixer-upgrade-verification-id")
SIMCTL = ("/usr/bin/xcrun", "simctl")
CASE = "FieldLogInstalledUpgradeTests/"
CREATE = CASE + "testCreateOrdinaryWorkspace"
REOPEN = CASE + "testReopenOrdinaryWorkspace"
EDIT = CASE + "testRestoreAndEditReplacement"
READBACK = CASE + "testReadEditedEntryAfterColdLaunch"
ATTACHMENTS = {
    CREATE: ["01-files-picker", "02-prior-draft-with-photo"],
    REOPEN: ["03-prior-cold-restored"],
    EDIT: ["04-replacement-cold-restored", "05-entry-saved"],
    READBACK: ["06-committed-entry-after-cold-launch", "07-pending-outbox"],
}


def write(path, value):
    with path.open("x") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")


class App:
    def __init__(self, artifacts, side):
        arm = artifacts / side
        self.receipt = json.loads((arm / "build-receipt.json").read_bytes())
        self.bundle = arm / "FieldLog.app"
        run = arm / "template.xctestrun"
        version, build, revision = PAIRS[side]
        require(self.receipt["status"] == "generic_build_for_testing_passed_runtime_pending"
                and self.receipt["mixerRevision"] == revision
                and self.receipt["mixerGitTree"] == MIXER_TREES[side]
                and self.receipt["fieldLogRevision"] == FIELDLOG_REV
                and self.receipt["fieldLogGitTree"] == FIELDLOG_TREE
                and self.receipt["toolchain"] == TOOLCHAIN
                and self.receipt["appVersion"] == version and self.receipt["appBuild"] == build
                and sha(run) == self.receipt["xctestrunSHA256"], f"Wrong {side} build receipt")
        require(tree_sha(self.bundle) == self.receipt["appTreeSHA256"], f"Wrong {side} bundle")
        self.verify_install(self.bundle)
        self.template = plistlib.loads(run.read_bytes())

    def verify_install(self, path):
        info = plistlib.loads((path / "Info.plist").read_bytes())
        require(info["CFBundleIdentifier"] == APP_ID
                and info["CFBundleShortVersionString"] == self.receipt["appVersion"]
                and info["CFBundleVersion"] == self.receipt["appBuild"]
                and info["CFBundleExecutable"] == "FieldLog"
                and info["UIFileSharingEnabled"] is True
                and info["LSSupportsOpeningDocumentsInPlace"] is True
                and info["CFBundleSupportedPlatforms"] == ["iPhoneSimulator"]
                and sha(path / "FieldLog") == self.receipt["appExecutableSHA256"]
                and tree_sha(path) == self.receipt["appTreeSHA256"],
                f"Incorrect installed FieldLog: {path}")
        return {"app": str(path), "version": info["CFBundleShortVersionString"],
                "build": info["CFBundleVersion"], "mixerRevision": self.receipt["mixerRevision"],
                "appTreeSHA256": self.receipt["appTreeSHA256"],
                "appExecutableSHA256": self.receipt["appExecutableSHA256"]}


def selection(app, runner, case):
    require(case in ATTACHMENTS, "Unexpected test selector")
    manifest = copy.deepcopy(app.template)
    require(set(manifest) == {"FieldLogUITests", "__xctestrun_metadata__"}, "Unexpected test targets")
    target = manifest["FieldLogUITests"]
    # Xcode 27.2 uses explicit host products for these installed-app tests.
    test_bundle = runner / PLUGIN.rsplit("/", 1)[0]
    target.pop("UseDestinationArtifacts", None)
    target.update(
        TestHostPath=str(runner),
        UITargetAppPath=str(app.bundle),
        TestBundlePath="__TESTHOST__/PlugIns/FieldLogUITests.xctest",
        DependentProductPaths=[str(app.bundle), str(runner), str(test_bundle)],
        OnlyTestIdentifiers=[case],
        UITargetAppCommandLineArguments=[],
        UITargetAppEnvironmentVariables={},
    )
    return manifest


class Commands:
    def __init__(self, output, device=None):
        self.output = output
        self.device = device
        tmp = output / "tmp"
        tmp.mkdir()
        self.environment = tool_environment() | {"TMPDIR": str(tmp) + "/"}
        self.sequence = 0
        self.unresolved_custody = None

    def command(self, name, argv, timeout=30):
        argv = list(map(str, argv))
        self.sequence += 1
        log = self.output / f"{self.sequence:02d}-{name}"
        write(log.with_suffix(".command.json"), {"argv": argv, "timeoutSeconds": timeout})
        child = None
        with log.with_suffix(".stdout").open("xb") as out, log.with_suffix(".stderr").open("xb") as err:
            try:
                child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                         env=self.environment, start_new_session=True)
                result = child.wait(timeout=timeout)
                try:
                    os.killpg(child.pid, 0)
                except OSError as error:
                    if error.errno != errno.ESRCH:
                        raise
                else:
                    raise RuntimeError("Command group still exists after direct child reap")
            except BaseException as error:
                self.unresolved_custody = {
                    "command": argv, "pid": child.pid if child else None,
                    "pgid": child.pid if child else None, "custody": "UNKNOWN",
                    "device": self.device, "retained": str(self.output), "error": str(error),
                }
                write(self.output / "HOLD.json", self.unresolved_custody)
                raise
        write(log.with_suffix(".result.json"), {"exit": result, "pid": child.pid, "groupAbsent": True})
        require(result == 0, f"{name} exited {result}. See {log}.stderr")
        return log.with_suffix(".stdout")

    def simulator(self, name, *args, timeout=30):
        return self.command(name, [*SIMCTL, *args], timeout)

    def rows(self, uid):
        path = self.simulator("device-inventory", "list", "-j", "devices", uid)
        devices = json.loads(path.read_bytes())["devices"]
        return [(runtime, device) for runtime, group in devices.items()
                for device in group if device["udid"] == uid]

    def inventory(self, excluded):
        devices = Path.home() / "Library/Developer/CoreSimulator/Devices"
        result = {}
        for path in sorted(devices.iterdir()):
            try:
                uid = str(uuid.UUID(path.name)).upper()
            except ValueError:
                continue
            if uid not in excluded:
                rows = self.rows(uid)
                require(len(rows) <= 1, f"Multiple Simulator registrations for {uid}")
                result[uid] = rows
        return result


class Run(Commands):
    def __init__(self, output, device, artifacts, seed_sha):
        super().__init__(output, device)
        self.artifacts = artifacts
        self.runner = artifacts / "FieldLogUITests-Runner.app"
        self.seed = artifacts / SEED_NAME
        self.seed_sha = seed_sha

    def sim(self, name, action, *args, timeout=30):
        return self.simulator(name, action, self.device, *args, timeout=timeout)

    def container(self, label, bundle, kind):
        path = Path(self.sim(f"{label}-{kind}-container", "get_app_container", bundle, kind).read_text().strip())
        require(path.is_absolute() and path.is_dir(), "Expected an absolute app container directory")
        real_path = path.resolve(strict=True)
        devices = (Path.home() / "Library/Developer/CoreSimulator/Devices").resolve(strict=True)
        section = "Bundle" if kind == "app" else "Data"
        parent = devices / self.device / "data/Containers" / section / "Application"
        require(real_path.is_relative_to(parent) and real_path != parent,
                "Container path does not belong to the owned Simulator")
        return real_path

    def preflight(self):
        [(runtime, owned)] = self.rows(self.device)
        path = self.simulator("runtimes", "list", "-j", "runtimes")
        [runtime_info] = [item for item in json.loads(path.read_bytes())["runtimes"]
                          if item["identifier"] == runtime]
        require(owned["state"] == "Booted" and owned["isAvailable"] and owned["deviceTypeIdentifier"]
                == "com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro"
                and runtime_info["version"] == "27.0" and runtime_info["buildversion"] == "24A434",
                "Expected a fresh booted iPhone 17 Pro on iOS 27.0 (24A434)")
        write(self.output / "owned-device.json", {"device": owned, "runtime": runtime_info})
        apps = self.sim("apps-before", "listapps")
        xml = self.command("apps-xml", ["/usr/bin/plutil", "-convert", "xml1", "-o", "-", apps])
        installed = plistlib.loads(xml.read_bytes())
        require(APP_ID not in installed and RUNNER_ID not in installed,
                "FieldLog or the case runner is already installed on the target")

    def verify_runner(self):
        actual = self.container("installed-runner", RUNNER_ID, "app")
        require(sha(actual / PLUGIN) == sha(self.runner / PLUGIN),
                "Unmatched installed UI test executable")

    def place_seed(self):
        data = self.container("seed", APP_ID, "data")
        workspace = data / "Library/Application Support/FieldLog"
        require(not workspace.exists(), "Refusing to seed a previously launched workspace")
        folder = data / "Documents"
        require(not folder.is_symlink(), "Unexpected Documents directory symlink")
        folder.mkdir(exist_ok=True)
        require(folder.resolve(strict=True) == folder, "Unexpected Documents directory")
        destination = folder / SEED_NAME
        with self.seed.open("rb") as source, destination.open("xb") as target:
            shutil.copyfileobj(source, target)
        require(sha(destination) == self.seed_sha, "Seed readback mismatch")
        write(self.output / "seed-file.json", {"path": str(destination), "sha256": self.seed_sha})
        marker = data / MARKER
        require(marker.parent.resolve(strict=True) == marker.parent, "Unexpected marker directory")
        token = os.urandom(32)
        with marker.open("xb") as target:
            target.write(token)
        self.marker_digest = hashlib.sha256(token).hexdigest()
        baseline = self.container_evidence(data)
        write(self.output / "seed-container.json", baseline)
        return baseline

    def container_evidence(self, data):
        marker = data / MARKER
        require(marker.resolve(strict=True) == marker and sha(marker) == self.marker_digest,
                "The installed data container lacks the original continuity marker")
        details = data.stat()
        return {
            "container": str(data),
            "containerMarkerSHA256": self.marker_digest,
            "containerFilesystemID": [details.st_dev, details.st_ino] if details.st_ino else None,
        }

    def case(self, label, app, case):
        run_file = self.output / (label + ".xctestrun")
        with run_file.open("xb") as file:
            plistlib.dump(selection(app, self.runner, case), file)
        result = self.output / (label + ".xcresult")
        self.command(label, [
            "/usr/bin/xcodebuild", "test-without-building", "-xctestrun", run_file,
            "-destination", f"platform=iOS Simulator,id={self.device}", "-destination-timeout", "45",
            "-only-testing:FieldLogUITests/" + case, "-testLanguage", "en", "-testRegion", "US",
            "-parallel-testing-enabled", "NO", "-maximum-concurrent-test-simulator-destinations", "1",
            "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", "240",
            "-maximum-test-execution-time-allowance", "240", "-collect-test-diagnostics", "never",
            "-resultBundlePath", result,
        ], timeout=345)
        base = ["/usr/bin/xcrun", "xcresulttool"]
        summary = json.loads(self.command(label + "-summary", base + [
            "get", "test-results", "summary", "--path", result,
        ]).read_bytes())
        require(all(summary[key] == count for key, count in {
            "totalTestCount": 1, "passedTests": 1, "failedTests": 0, "skippedTests": 0, "expectedFailures": 0,
        }.items()), f"Wrong XCTest summary for {label}")
        directory = self.output / (label + "-attachments")
        self.command(label + "-attachments", base + ["export", "attachments", "--path", result,
                                                     "--output-path", directory])
        entries = json.loads((directory / "manifest.json").read_bytes())
        expected_case = case + "()"
        attachments = [item for entry in entries if entry["testIdentifier"] == expected_case
                       for item in entry["attachments"]]
        hashes = {}
        for name in ATTACHMENTS[case]:
            [item] = [item for item in attachments if item["suggestedHumanReadableName"].startswith(name + "_")]
            file = directory / item["exportedFileName"]
            require(file.parent == directory and file.stat().st_size > 0, f"Missing attachment {name}")
            hashes[name] = sha(file)
        write(self.output / (label + "-screenshots.json"), hashes)

    def snapshot(self, label, app, phase):
        installed = app.verify_install(self.container(label, APP_ID, "app"))
        self.verify_runner()
        data = self.container(label, APP_ID, "data")
        continuity = self.container_evidence(data)
        root = data / "Library/Application Support/FieldLog"
        require(root.resolve(strict=True) == root, "Workspace directory resolves outside the expected path")
        workspace_file = root / "workspace.json"
        require(workspace_file.stat().st_size <= 1024 * 1024, "Unexpected workspace size")
        workspace_sha = sha(workspace_file)
        payload = workspace_file.read_bytes()
        state = json.loads(payload)
        photo = validate_workspace(state, phase)
        photo_directory = root / "photos"
        photo_file = photo_directory / photo["filename"]
        require(photo_directory.resolve(strict=True) == photo_directory
                and list(photo_directory.iterdir()) == [photo_file],
                "Unexpected installed photo directory")
        require(photo_file.stat().st_size == photo["byteCount"], "Wrong stored JPEG size")
        photo_sha = sha(photo_file)
        snapshot = self.output / (label + "-workspace")
        (snapshot / "photos").mkdir(parents=True)
        (snapshot / "workspace.json").write_bytes(payload)
        (snapshot / "photos" / photo["filename"]).write_bytes(photo_file.read_bytes())
        evidence = json.loads(self.command(label + "-photo", [
            self.artifacts / "verify-draft-photo", snapshot, self.seed, phase,
        ]).read_bytes())
        require(evidence["snapshotSHA256"] == workspace_sha and evidence["jpegSHA256"] == photo_sha
                and evidence["seedSHA256"] == self.seed_sha, "Photo verification differs from readback")
        result = continuity | {"installed": installed, "workspaceSHA256": workspace_sha,
                               "photoSHA256": photo_sha, "workspace": state}
        write(self.output / (label + "-snapshot.json"), result)
        return result


def verify_inputs(artifacts):
    require(platform.machine() == "arm64", "Expected the arm64 host")
    toolchain = subprocess.check_output(["/usr/bin/xcodebuild", "-version"], text=True, env=tool_environment()).strip()
    require(toolchain == TOOLCHAIN, "Wrong Xcode version")
    hashes = json.loads((artifacts / "inputs.json").read_bytes())
    defaults = {"prior/build-receipt.json", "new/build-receipt.json", SEED_NAME, "verify-draft-photo"}
    runner = artifacts / "FieldLogUITests-Runner.app"
    require(set(hashes) == defaults | {runner.name}, "Inputs manifest has unexpected paths")
    for file in defaults:
        require(sha(artifacts / file) == hashes[file], f"Prepared file differs: {file}")
    prior, new = App(artifacts, "prior"), App(artifacts, "new")
    for identity in ("appExecutableSHA256", "mixerUISourceGitTree", "mixerSDKFileTreeSHA256"):
        require(prior.receipt[identity] != new.receipt[identity], f"Expected different {identity}")
    require(prior.receipt["fieldLogPreparedFileTreeSHA256"] == new.receipt["fieldLogPreparedFileTreeSHA256"],
            "Expected one shared FieldLog overlay")
    for app in (prior, new):
        require(set(app.receipt["linkedSDKObjectSHA256"]) == set(ENGINE_PRODUCTS), "Missing linked SDK object")
    require(prior.receipt["linkedSDKObjectSHA256"]["MixerUI"] != new.receipt["linkedSDKObjectSHA256"]["MixerUI"],
            "The Mach-O inputs do not distinguish the two SDK builds")
    info = plistlib.loads((runner / "Info.plist").read_bytes())
    require(info["CFBundleIdentifier"] == RUNNER_ID and tree_sha(runner) == hashes[runner.name],
            "Wrong UI test runner bundle")
    sha(runner / PLUGIN)
    for bundle in (prior.bundle, new.bundle, runner):
        subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(bundle)], check=True)
    for case in ATTACHMENTS:
        plistlib.dumps(selection(prior if case in {CREATE, REOPEN} else new, runner, case))
    return prior, new, hashes[SEED_NAME]


def journey(run, prior, new):
    run.preflight()
    run.sim("install-prior", "install", prior.bundle)
    run.sim("install-test-runner", "install", run.runner)
    run.verify_runner()
    write(run.output / "prior-initial-app.json", prior.verify_install(run.container("prior-initial", APP_ID, "app")))
    seeded = run.place_seed()
    run.case("prior-create", prior, CREATE)
    created = run.snapshot("prior-created", prior, "draft")
    continuity = {"create": compare_containers(seeded, created, "create")}
    # XCTest can relocate this same bundle's data between container URLs.
    seed = Path(created["container"]) / "Documents" / SEED_NAME
    require(seed.resolve(strict=True) == seed, "Seed is not an ordinary app document")
    require(sha(seed) == run.seed_sha, "The original seeded document changed")
    seed.unlink()

    run.case("prior-reopen", prior, REOPEN)
    before = run.snapshot("prior-reopened", prior, "draft")
    continuity["restore"] = compare(created, before, "restore")

    run.sim("replace-in-place", "install", new.bundle)
    replaced = run.snapshot("replacement-before-launch", new, "draft")
    continuity["install"] = compare(before, replaced, "install")
    run.case("replacement-edit", new, EDIT)
    edited = run.snapshot("replacement-edited", new, "entry")
    continuity["edit"] = compare(replaced, edited, "edit")
    run.case("replacement-readback", new, READBACK)
    readback = run.snapshot("replacement-readback", new, "entry")
    continuity["readback"] = compare(edited, readback, "readback")
    return {
        "before": before["installed"], "after": readback["installed"],
        "containerContinuity": continuity, "dataContainer": readback["container"],
        "workspaceID": readback["workspace"]["id"], "entryID": readback["workspace"]["entries"][0]["id"],
        "photoSHA256": readback["photoSHA256"],
        "outboxIDs": [operation["id"] for operation in readback["workspace"]["outbox"]],
    }
