#!/usr/bin/env python3
"""Check root's completed FieldLog XCTest evidence without operating a device."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from uuid import UUID

from prepare import TEST, digest
from readback import verify as read_disk


def load(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def zero(code):
    return type(code) is int and code == 0


def successful(commands, args):
    matches = [command for command in commands if command["args"] == args]
    require(len(matches) == 1, f"Expected one recorded root command: {args[:3]}")
    [command] = matches
    require(zero(command["exit"]), f"Root command failed: {args[:3]}")
    return command


def local_file(directory, name):
    require(Path(name).name == name and name, "Expected a local evidence filename")
    path = directory / name
    require(path.is_file() and not path.is_symlink(), f"Missing local evidence file: {path}")
    return path


def inventory(run, command):
    devices = load(local_file(run, command["log"]))["devices"]
    return {device["udid"]: [runtime, device["name"], device["state"]]
            for runtime, rows in devices.items() for device in rows}


def verify_cleanup(run, record, harness):
    owned = record["owned"]
    commands = record["commands"]
    require(record["ownedRemoved"] is True and record["externalExact"] is True,
            "Root did not record owned-device removal and external baseline agreement")
    device_list = ["xcrun", "simctl", "list", "devices", "-j"]
    delete = successful(commands, ["xcrun", "simctl", "delete", owned])
    require(commands.index(harness) < commands.index(delete), "Device deletion preceded the test")
    before, after = commands[0], commands[-1]
    require(all(command["args"] == device_list and zero(command["exit"]) for command in (before, after))
            and commands.index(delete) < len(commands) - 1, "Missing before/after device inventories")
    lists_before_delete = [command for command in commands[:commands.index(delete)] if command["args"] == device_list]
    shutdown = lists_before_delete[-1]
    require(commands.index(shutdown) > commands.index(harness) and zero(shutdown["exit"])
            and inventory(run, shutdown).get(owned, [None, None, None])[2] == "Shutdown",
            "Missing owned-device Shutdown observation")
    baseline = inventory(run, before)
    require(owned not in baseline and baseline == record["baseline"] == inventory(run, after),
            "Device cleanup disagrees with the recorded external baseline")


def verify_summary(summary, owned):
    counts = {"totalTestCount": 1, "passedTests": 1, "failedTests": 0, "skippedTests": 0, "expectedFailures": 0}
    require(all(type(summary[key]) is int and summary[key] == count for key, count in counts.items())
            and summary["result"] == "Passed" and summary["testFailures"] == [],
            "Expected exactly one XCTest, one pass, and zero failures or skips")
    [configuration] = summary["devicesAndConfigurations"]
    require(configuration["device"]["deviceId"] == owned, "XCTest result belongs to a different device")
    return counts


def verify_disk(build, run, record, attachments):
    [case] = load(attachments / "manifest.json")
    require(case["testIdentifier"] == TEST.split("/", 1)[1] + "()", "Unexpected XCTest attachment case")

    def attachment(label):
        [entry] = [entry for entry in case["attachments"]
                   if entry["suggestedHumanReadableName"].startswith(label + "_")]
        require(entry["deviceId"] == record["owned"] and entry["isAssociatedWithFailure"] is False,
                f"Unexpected attachment device or outcome: {label}")
        return local_file(attachments, entry["exportedFileName"]).read_text().strip()

    workspace = str(UUID(attachment("workspace-id")))
    disk = read_disk(build, run / f"FieldLogSignedOTA-{workspace}")
    for state, phases in (
        ("healthy", ["05-offline-reopen-identity"]),
        ("previousHealthy", ["02-reviewed-confirmation-identity", "03-reviewed-completed-identity"]),
    ):
        for phase in phases:
            marker = attachment(phase)
            match = re.fullmatch(r"candidate=([0-9a-f]{64}) launch=([0-9A-F-]{36})", marker)
            require(match is not None and match[1] == disk[state]["candidate"]
                    and UUID(match[2]) == UUID(disk[state]["launch"]),
                    f"Disk candidate or launch disagrees with {phase}")
    require(disk == record["diskEvidence"], "Copied disk state disagrees with root's readback")
    return workspace, disk


def verify(build, run):
    record = load(run / "run.json")
    require("failure" not in record and record["publicAXTrusted"] is True,
            "Root evidence records a failure or lacks Accessibility trust")
    owned = str(UUID(record["owned"])).upper()
    require(owned == record["owned"], "Expected the exact owned device UUID")
    commands = record["commands"]
    matches = [command for command in commands
               if len(command["args"]) == 7 and Path(command["args"][0]).name == "python3"
               and command["args"][1] == "-B" and Path(command["args"][2]) == Path(__file__).with_name("run.py")
               and command["args"][5:] == ["--device", owned]]
    require(len(matches) == 1, "Expected one recorded signed FieldLog harness invocation")
    [harness] = matches
    require(zero(harness["exit"]), "Signed FieldLog harness did not exit cleanly")
    require(Path(harness["args"][3]).resolve() == build and Path(harness["args"][4]).name == "live",
            "Root harness command selected a different build or output")
    live = run / "live"
    test = load(live / "test-result.json")
    require(zero(test["xcodebuildExit"]) and test["selector"] == TEST, "Selected XCTest command failed")
    service = load(live / "service-result.json")
    require(zero(service["exit"]) and service["listenerClosed"] is True and service["portReusable"] is True,
            "Owned release service did not exit cleanly and close its port")
    recorded_live = Path(harness["args"][4])
    launch = load(live / "service-launch.json")
    require(Path(launch["executable"]) == build / "mixer-service"
            and Path(launch["config"]) == recorded_live / "service.json"
            and launch["sha256"] == digest(build / "mixer-service"),
            "Service launch selected a different build or output")
    bundle = recorded_live / "signed-ota.xcresult"
    test_command = load(live / "test-command.json")
    require(test_command[:2] == ["/usr/bin/xcodebuild", "test-without-building"],
            "Root evidence did not record the XCTest command")
    for flag, expected in (("-destination", f"platform=iOS Simulator,id={owned}"),
                           ("-resultBundlePath", str(bundle))):
        require(test_command[test_command.index(flag) + 1] == expected, f"XCTest command mismatch: {flag}")
    require([arg for arg in test_command if arg.startswith("-only-testing:")] == ["-only-testing:" + TEST],
            "XCTest command selected a different test")
    summary = verify_summary(record["summary"], owned)
    summary_command = ["xcrun", "xcresulttool", "get", "test-results", "summary", "--path"]
    observed = json.loads(subprocess.check_output(summary_command + [str(live / bundle.name)], timeout=15))
    require(record["summary"] == observed, "Root summary disagrees with the retained result bundle")
    with TemporaryDirectory(prefix="fieldlog-ios-accept-") as temporary:
        attachments = Path(temporary) / "attachments"
        subprocess.run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(live / bundle.name),
                        "--output-path", str(attachments)], check=True, capture_output=True, timeout=15)
        workspace, disk = verify_disk(build, run, record, attachments)
    verify_cleanup(run, record, harness)
    return {"harnessExit": 0, "tests": summary, "device": owned, "workspaceID": workspace,
            "serviceExit": 0, "listenerClosed": True, "portReusable": True,
            "ownedRemoved": True, "externalExact": True, "disk": disk,
            "buildReceiptSHA256": digest(build / "build-receipt.json"),
            "rootRunSHA256": digest(run / "run.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("root_run", type=Path, help="Completed root evidence directory containing run.json")
    args = parser.parse_args()
    try:
        result = verify(args.build.resolve(strict=True), args.root_run.resolve(strict=True))
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"FieldLog runtime evidence refused: {exc}\n")
    print(json.dumps(result, indent=2))
