#!/usr/bin/env python3
"""Check the build products or run the upgrade on one fresh root-owned Simulator."""
import argparse
import ctypes
import json
import uuid
from pathlib import Path

from upgrade_artifacts import TOOLCHAIN, sha
from upgrade_journey import Commands, Run, journey, verify_inputs, write
from workspace_state import require

RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
DEVICE_TYPE = "com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro"
HELD_DEVICES = {"3BE9FB17-6348-42C8-944B-9140BEC5541F"}

VOLATILE_DEVICE_FIELDS = {"dataPathSize", "logPathSize", "lastUsedAt"}


def external_inventory_identity(inventory):
    """Compare registrations and lifecycle while preserving raw inventory receipts."""
    return {
        uid: [(runtime, {key: value for key, value in device.items() if key not in VOLATILE_DEVICE_FIELDS})
              for runtime, device in rows]
        for uid, rows in inventory.items()
    }


def accessibility_trusted():
    library = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
    check = library.AXIsProcessTrusted
    check.argtypes = []
    check.restype = ctypes.c_bool
    return check()


def device_state(commands, owned, name):
    [(runtime, device)] = commands.rows(owned)
    require(runtime == RUNTIME and device["name"] == name and device["deviceTypeIdentifier"] == DEVICE_TYPE,
            "Registered device no longer matches the owned Simulator")
    return device["state"]


def run_owned(output, artifacts, prior, new, seed_hash, excluded):
    output.mkdir(mode=0o700)
    commands = Commands(output)
    live = output / "journey"
    owned = None
    session = None
    creating = False
    result = {"toolchain": TOOLCHAIN, "inputManifestSHA256": sha(artifacts / "inputs.json"),
              "excludedDeviceUUIDs": sorted(excluded)}

    try:
        require(accessibility_trusted(), "macOS Accessibility preflight failed")
        baseline = commands.inventory(excluded)
        write(output / "external-before.json", baseline)
        baseline_identity = external_inventory_identity(baseline)
        require(accessibility_trusted(), "macOS Accessibility trust changed before creation")
        name = "FieldLog Upgrade " + str(uuid.uuid4())
        creating = True
        path = commands.simulator("create-owned", "create", name, DEVICE_TYPE, RUNTIME)
        uid = str(uuid.UUID(path.read_text().strip())).upper()
        require(uid not in baseline and uid not in excluded, "Creation did not return a new UUID")
        require(device_state(commands, uid, name) == "Shutdown", "Expected a new Shutdown device")
        owned = commands.device = uid
        creating = False
        write(output / "ownership.json", {"uuid": owned, "name": name, "runtime": RUNTIME,
                                         "deviceType": DEVICE_TYPE})
        commands.simulator("boot-owned", "boot", owned)
        commands.simulator("bootstatus-owned", "bootstatus", owned, "-b", timeout=240)
        require(device_state(commands, owned, name) == "Booted", "Owned device did not boot")
        external = excluded | {owned}
        setup = commands.inventory(external)
        write(output / "external-after-setup.json", setup)
        require(external_inventory_identity(setup) == baseline_identity, "External inventory changed during setup")
        live.mkdir(mode=0o700)
        session = Run(live, owned, artifacts, seed_hash)
        observation = journey(session, prior, new)
        during = commands.inventory(external)
        write(output / "external-after-journey.json", during)
        require(external_inventory_identity(during) == baseline_identity, "External inventory changed during the journey")
        result["journey"] = observation
    except (Exception, KeyboardInterrupt) as error:
        result["failure"] = repr(error)
    finally:
        custody = commands.unresolved_custody or (session and session.unresolved_custody)
        if creating or custody is not None:
            result["hold"] = custody or "Device creation did not establish ownership."
        elif owned is not None:
            try:
                if device_state(commands, owned, name) != "Shutdown":
                    commands.simulator("shutdown-owned", "shutdown", owned, timeout=90)
                require(device_state(commands, owned, name) == "Shutdown", "Owned device is still active")
                commands.simulator("delete-owned", "delete", owned, timeout=90)
                require(commands.rows(owned) == [], "Owned UUID is still registered")
                after = commands.inventory(excluded)
                write(output / "external-after.json", after)
                result.update(ownedRemoved=True, externalRawExact=after == baseline,
                              externalExact=external_inventory_identity(after) == baseline_identity)
            except (Exception, KeyboardInterrupt) as error:
                result["cleanupError"] = repr(error)
                if commands.unresolved_custody is not None:
                    result["hold"] = commands.unresolved_custody

    result["ownedUUID"] = owned
    passed = "journey" in result and result.get("ownedRemoved") and result.get("externalExact")
    result["status"] = "passed" if passed else "incomplete"
    write(output / "result.json", result)
    print(json.dumps({"status": result["status"], "receipt": str(output / "result.json")}))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--output", type=Path, help="New directory for the root-owned Simulator run")
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--exclude-simulator", type=uuid.UUID, action="append", default=[],
                        help="Exclude an additional held UUID from inventory and targeting")
    args = parser.parse_args()
    artifacts = args.artifacts.resolve(strict=True)
    prior, new, seed_hash = verify_inputs(artifacts)
    if args.check:
        print(json.dumps({"status": "host_inputs_verified", "toolchain": TOOLCHAIN,
                          "prior": prior.verify_install(prior.bundle),
                          "replacement": new.verify_install(new.bundle)}, indent=2))
        return 0
    excluded = HELD_DEVICES | {str(uid).upper() for uid in args.exclude_simulator}
    return run_owned(args.output.resolve(), artifacts, prior, new, seed_hash, excluded)


if __name__ == "__main__":
    raise SystemExit(main())
