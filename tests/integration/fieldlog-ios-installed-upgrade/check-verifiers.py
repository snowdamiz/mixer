#!/usr/bin/env python3
"""Run positive and negative checks for the readback verifiers without a Simulator."""
import argparse
import copy
import json
import plistlib
import subprocess
import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import run
import upgrade_journey as journey
from upgrade_artifacts import FIELDLOG_REV, FIELDLOG_TREE, git_command, git_tree, sha, tool_environment
from workspace_state import NOTE, compare, require, validate_workspace

HERE = Path(__file__).resolve().parent


def identity(n):
    return str(uuid.UUID(int=n)).upper()


def repository_control(path, checkout):
    workspace = path / "workspace.swift"
    repository = path / "repository.swift"
    for target, source in ((workspace, "Sources/FieldLogModels/Workspace.swift"),
                           (repository, "Sources/FieldLogStorage/WorkspaceRepository.swift")):
        target.write_bytes(git_command(checkout, "show", FIELDLOG_REV + ":" + source,
                                       capture_output=True).stdout)
    compiler = ["/usr/bin/swiftc", "-swift-version", "6", "-parse-as-library",
                "-module-cache-path", str(path / "module-cache"), "-I", str(path)]
    products = []
    for name, source in (("FieldLogModels", workspace), ("FieldLogStorage", repository)):
        compiled = path / (name + ".o")
        subprocess.run(
            compiler + ["-emit-module", "-emit-module-path", str(path / (name + ".swiftmodule")),
                        "-emit-object", "-module-name", name, str(source), "-o", str(compiled)],
            env=tool_environment(), check=True)
        products.append(str(compiled))
    control = path / "repository-control"
    subprocess.run(compiler + [str(HERE / "RepositoryReadbackControl.swift"), *products,
                               "-o", str(control)], env=tool_environment(), check=True)
    return control


def write(directory, value):
    snapshot = directory / "workspace.json"
    snapshot.write_text(json.dumps(value))
    return snapshot


def photo_verification(artifacts, directory, phase, failure=None):
    result = subprocess.run([artifacts / "verify-draft-photo", directory, artifacts / journey.SEED_NAME, phase],
                            capture_output=True, text=True)
    if failure is not None:
        require(result.returncode != 0 and failure in result.stderr,
                f"Expected {failure} but saw ({result.returncode}) {result.stderr}")
        return None
    require(result.returncode == 0, result.stderr)
    return json.loads(result.stdout)


def rejects(label, method):
    try:
        method()
    except ValueError:
        print(f"PASS rejects {label}")
    else:
        raise ValueError(f"Accepted invalid state: {label}")


def check_isolation(root, artifacts, prior, new, seed_hash):
    original_command, original_write = journey.Commands.command, journey.write
    external, held, owned, unregistered = (identity(n) for n in range(1, 5))
    for scenario in ("pass", "metadata-drift", "accessibility", "hold", "external-change"):
        passes = scenario in {"pass", "metadata-drift"}
        home = root / scenario
        devices = home / "Library/Developer/CoreSimulator/Devices"
        for uid in (external, held, unregistered):
            (devices / uid).mkdir(parents=True)
        states = {external: {"udid": external, "name": "External", "state": "Booted"}}
        actions = []

        def fake_command(commands, _, argv, timeout=30):
            binary, tool, action, *args = argv
            require((binary, tool) == journey.SIMCTL, "Unexpected tool in root wrapper")
            actions.append((action, args))
            output = commands.output / f"fake-command-{len(actions)}"
            if action == "list":
                require(len(args) == 3 and args[:2] == ["-j", "devices"]
                        and args[2] in {external, owned, unregistered}, "Inventory touched an unapproved target")
                row = states.get(args[2])
                output.write_text(json.dumps({"devices": {run.RUNTIME: [row] if row else []}}))
            elif action == "create":
                name, device_type, runtime = args
                require(device_type == run.DEVICE_TYPE and runtime == run.RUNTIME, "Incorrect owned device type")
                (devices / owned).mkdir()
                states[owned] = {"udid": owned, "name": name, "state": "Shutdown",
                                 "deviceTypeIdentifier": device_type}
                output.write_text(owned)
            else:
                require(args in ([owned], [owned, "-b"]), "Device operation targeted an external UUID")
                if action in {"boot", "shutdown"}:
                    states[owned]["state"] = "Booted" if action == "boot" else "Shutdown"
                    if scenario == "metadata-drift":
                        states[external]["dataPathSize"] = 1024 if action == "boot" else 2048
                elif action == "delete":
                    require(states[owned]["state"] == "Shutdown", "Deleted an active test instance")
                    del states[owned]
                    (devices / owned).rmdir()
                else:
                    require(action == "bootstatus", "Unexpected device operation")
            return output

        def fake_journey(session, _, __):
            require(session.device == owned and states[owned]["state"] == "Booted", "Wrong journey target")
            if scenario == "hold":
                child = Mock(pid=1234)
                child.wait.side_effect = subprocess.TimeoutExpired(["xcodebuild"], 1)

                def write_except_hold(path, value):
                    if path.name == "HOLD.json":
                        raise OSError("Simulated HOLD receipt write failure")
                    original_write(path, value)

                with (patch.object(journey.subprocess, "Popen", return_value=child),
                      patch.object(journey, "write", side_effect=write_except_hold)):
                    original_command(session, "host-custody-control", ["/usr/bin/false"])
            if scenario == "metadata-drift":
                states[external].update(logPathSize=1024, lastUsedAt="2026-11-18T21:25:53Z")
            if scenario == "external-change":
                states[external]["state"] = "Shutdown"
            return {"device": owned}

        output = home / "run"
        with (patch.object(Path, "home", return_value=home),
              patch.object(journey.Commands, "command", fake_command),
              patch.object(run, "accessibility_trusted", return_value=scenario != "accessibility"),
              patch.object(run, "journey", fake_journey)):
            exit_code = run.run_owned(output, artifacts, prior, new, seed_hash, {held})
        result = json.loads((output / "result.json").read_bytes())
        require((exit_code == 0) == passes, f"Wrong terminal outcome for {scenario}")
        if scenario == "hold":
            require(result["hold"]["pid"] == 1234 and owned in states
                    and not (output / "journey/HOLD.json").exists(),
                    "Cleanup crossed an unresolved custody hold when the receipt write failed")
        elif scenario == "accessibility":
            require(not actions, "Simulator discovery started before Accessibility preflight")
        else:
            require(result["ownedRemoved"] and result["externalExact"] == passes
                    and result["externalRawExact"] == (scenario == "pass"),
                    "Wrong owned retirement or external baseline result")
            if scenario == "metadata-drift":
                before, setup, after_journey, after = (
                    json.loads((output / f"external-{phase}.json").read_bytes())[external][0][1]
                    for phase in ("before", "after-setup", "after-journey", "after")
                )
                require("dataPathSize" not in before and setup["dataPathSize"] == 1024
                        and after_journey["logPathSize"] == 1024
                        and after["lastUsedAt"] == "2026-11-18T21:25:53Z"
                        and after["dataPathSize"] == 2048, "Raw inventories lost observed metadata")
    print("PASS mocked Accessibility, exact UUID targeting, held-device exclusion and baseline checks")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fieldlog-git", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    artifacts = args.artifacts.resolve(strict=True)
    checkout = args.fieldlog_git.resolve(strict=True)
    require(git_tree(checkout, FIELDLOG_REV) == FIELDLOG_TREE, "Unexpected public FieldLog tree")
    prior, new, seed_sha = journey.verify_inputs(artifacts)
    runner = artifacts / "FieldLogUITests-Runner.app"
    for case, app in ((journey.CREATE, prior), (journey.REOPEN, prior),
                      (journey.EDIT, new), (journey.READBACK, new)):
        manifest = journey.selection(app, runner, case)
        target = plistlib.loads(plistlib.dumps(manifest))["FieldLogUITests"]
        test_bundle = runner / "PlugIns/FieldLogUITests.xctest"
        require(target["OnlyTestIdentifiers"] == [case]
                and target["TestHostPath"] == str(runner)
                and target["UITargetAppPath"] == str(app.bundle)
                and target["TestBundlePath"] == "__TESTHOST__/PlugIns/FieldLogUITests.xctest"
                and target["DependentProductPaths"] == [str(app.bundle), str(runner), str(test_bundle)]
                and target["UITargetAppCommandLineArguments"] == []
                and target["UITargetAppEnvironmentVariables"] == {}
                and "UseDestinationArtifacts" not in target, "Wrong manifest for this test phase")
    print("PASS fresh signed bundles and four explicit XCTest product manifests")

    with tempfile.TemporaryDirectory(prefix=".verifier-control-", dir=artifacts.parent) as temp:
        root = Path(temp)
        check_isolation(root, artifacts, prior, new, seed_sha)
        directory = root / "workspace"
        control = repository_control(root, checkout)
        seed_jpeg = root / "input.jpg"
        subprocess.run(["/usr/bin/sips", "-z", "1067", "1600", "-s", "format", "jpeg",
                        artifacts / journey.SEED_NAME, "--out", seed_jpeg], check=True, capture_output=True)
        jpeg_bytes = seed_jpeg.read_bytes()
        snapshot = directory / "workspace.json"

        marker = directory / journey.MARKER

        def capture(phase):
            value = json.loads(snapshot.read_bytes())
            record = validate_workspace(value, phase)
            photo = directory / "photos" / record["filename"]
            evidence = photo_verification(artifacts, directory, phase)
            require(record["id"] == evidence["attachmentID"]
                    and evidence["seedSHA256"] == seed_sha
                    and evidence["jpegSHA256"] == sha(photo)
                    and evidence["snapshotSHA256"] == sha(snapshot), "Verifier hashes differ")
            return session.container_evidence(directory) | {
                "workspace": value, "workspaceSHA256": sha(snapshot), "photoSHA256": sha(photo),
            }

        subprocess.run([control, "create", directory, seed_jpeg], check=True)
        marker.parent.mkdir()
        marker.write_bytes(b"independent host continuity control")
        host = root / "host"
        host.mkdir()
        session = journey.Run(host, None, artifacts, seed_sha)
        session.marker_digest = sha(marker)
        snapshots = {"draft": capture("draft")}
        print("PASS verifies repository draft, JPEG linkage, dimensions and four swatches")
        subprocess.run([control, "read", directory], check=True)
        compare(snapshots["draft"], capture("draft"), "restore")
        compare(snapshots["draft"], capture("draft"), "install")
        subprocess.run([control, "edit", directory], check=True)
        snapshots["entry"] = capture("entry")
        compare(snapshots["draft"], snapshots["entry"], "edit")
        subprocess.run([control, "read", directory], check=True)
        compare(snapshots["entry"], capture("entry"), "readback")
        print("PASS observation-only comparisons and a real FieldLog repository commit on macOS")

        draft, edited = (snapshots[phase]["workspace"] for phase in ("draft", "entry"))
        photo = directory / "photos" / edited["attachments"][0]["filename"]

        marker.write_bytes(b"wrong marker bytes")
        rejects("invalid independent marker readback", lambda: session.container_evidence(directory))
        for key, wrong_value in (("containerMarkerSHA256", "a" * 64),
                                 ("containerFilesystemID", [0, 1]),
                                 ("photoSHA256", "f" * 64), ("workspaceSHA256", "e" * 64)):
            changed = snapshots["draft"] | {key: wrong_value}
            rejects(f"changed {key} before first launch",
                    lambda: compare(snapshots["draft"], changed, "install"))

        relocated = snapshots["draft"] | {"container": "/relocated-container", "containerFilesystemID": [0, 1]}
        require(compare(snapshots["draft"], relocated, "restore") ==
                {"samePath": False, "sameFilesystemID": False}, "Missing relocation evidence")
        rejects("different physical directory after replacement",
                lambda: compare(snapshots["draft"], relocated, "install"))
        unknown = snapshots["draft"] | {"containerFilesystemID": None}
        require(compare(snapshots["draft"], unknown, "install") ==
                {"samePath": True, "sameFilesystemID": None}, "Missing filesystem availability evidence")
        print("PASS records relocation and unavailable physical directory identity")

        lost_draft = copy.deepcopy(draft)
        lost_draft["restoration"].pop("openDraftID")
        rejects("lost draft restoration", lambda: validate_workspace(lost_draft, "draft"))
        broken_link = copy.deepcopy(draft)
        broken_link["drafts"][0]["attachmentIDs"] = [identity(9)]
        rejects("broken attachment link", lambda: validate_workspace(broken_link, "draft"))
        missing_edit = copy.deepcopy(edited)
        missing_edit["entries"][0]["note"] = NOTE
        rejects("reverted post-upgrade edit", lambda: validate_workspace(missing_edit, "entry"))
        replaced_outbox = copy.deepcopy(snapshots["entry"])
        replaced_outbox["workspace"]["outbox"][0]["id"] = identity(11)
        rejects("changed queued operation identity",
                lambda: compare(snapshots["draft"], replaced_outbox, "edit"))
        duplicate_outbox = copy.deepcopy(edited)
        duplicate_outbox["outbox"][-1]["id"] = duplicate_outbox["outbox"][0]["id"]
        rejects("duplicate queued operation", lambda: validate_workspace(duplicate_outbox, "entry"))
        write(directory, edited)
        photo_verification(artifacts, directory, "draft", "Expected one record in the requested phase")
        photo.write_bytes(b"\0" * len(jpeg_bytes))
        photo_verification(artifacts, directory, "entry", "Could not decode public.jpeg")
        photo.write_bytes(jpeg_bytes)
        wrong_photo = directory / "wrong.jpg"
        subprocess.run(["/usr/bin/sips", "-f", "horizontal", photo, "--out", wrong_photo],
                       check=True, capture_output=True)
        wrong_photo.replace(photo)
        wrong = copy.deepcopy(edited)
        wrong["attachments"][0]["byteCount"] = photo.stat().st_size
        write(directory, wrong)
        photo_verification(artifacts, directory, "entry", "does not match the seeded photo")
        print("PASS rejects the wrong phase, an undecodable JPEG and a valid JPEG with the wrong pixels")


if __name__ == "__main__":
    main()
