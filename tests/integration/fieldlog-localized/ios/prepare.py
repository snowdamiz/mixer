#!/usr/bin/env python3
"""Stage the exact localized payloads on the maintained iOS checklist fixture."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from identity_binding import require, source_digests, verify


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = "9d0eec8ac194254ce19779d87fbdd93f107c4de6"
TREE = "61f01309897bc22d77fabfb8346554e990710fab"
ROTATION = "capability-activation/verification/fieldlog-ios/rotation"
APPLE_HOST = "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIApple.swift"
SCROLL_FIX = "8ee46c7ecd3a828d638fb5e25af0812e1f707d1e"
STORAGE = "Integrations/InstalledGuest/TaskStorage.swift"
HEADER = "vm/include/mixer_vm_guest_ui_deferred.h"
SELECTOR = "FieldLogUITests/ChecklistJourney/testSignedLocalizedChecklist"
VARIANTS = ("baseline", "reviewed")
# Ordinary iOS inventories of the audited staged rotation sources, before localization.
ROTATION_SOURCE_DIGESTS = {
    "link_inputs_sha256": "a132a2451cd61aafd1d1e315da31efd7d672adfbc68c72d787a9b48914033fee",
    "native_fallback_sha256": "a371d038a130f6b33ef24b2163348482417f1bc13723624f556a4b796dae2e4c",
}


def git(*args, cwd=ROOT):
    return subprocess.check_output(["git", "--no-replace-objects", *args], cwd=cwd)


def apply_patch(directory, name):
    # The staged source may sit under an unrelated Git worktree.
    env = os.environ | {"GIT_CEILING_DIRECTORIES": str(directory.parent)}
    subprocess.run(["git", "apply", "--whitespace=error", str(HERE / name)], cwd=directory, env=env, check=True)


def tracked_json(path):
    return json.loads(git("show", f"{BASE}:{path}"))


def exact(path, size, digest):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size == size,
            f"Unexpected fixture file size or type: {path}")
    data = path.read_bytes()
    require(len(data) == size and sha256(data).hexdigest() == digest, f"Unexpected fixture bytes: {path}")
    return data


def replace_once(content, before, after):
    require(content.count(before) == 1, f"Maintained fixture source changed: {before!r}")
    return content.replace(before, after)


def read_payloads(guests, pins, lock):
    binding_path = guests / "binding.json"
    size = binding_path.stat().st_size
    require(0 < size <= 8192, "Missing or oversized Android source binding")
    binding = json.loads(exact(binding_path, size, lock["guestBindingSHA256"]))
    for key in ("consumer", "selectedGuestSHA256", "localizedGuestSHA256", "payloads"):
        require(binding[key] == pins[key], f"Localized guest binding differs: {key}")
    payloads = {
        name: exact(guests / f"{name}.wasm", pins["payloads"][name]["bytes"], pins["payloads"][name]["sha256"])
        for name in VARIANTS
    }
    return binding, payloads


def prepare(work, guests):
    require(git("rev-parse", "HEAD", "HEAD^{tree}").decode().splitlines() == [BASE, TREE],
            "Use the isolated checkout at the exact public Mixer pin")
    require(not git("diff", "--name-only", "HEAD", "--", ROTATION), "Modified iOS rotation recipe")
    android = "tests/integration/fieldlog-localized/android"
    android_pins = tracked_json(f"{android}/pins.json")
    android_lock = tracked_json(f"{android}/package-pins.json")
    rotation_pins = tracked_json(f"{ROTATION}/pins.json")
    binding, payloads = read_payloads(guests, android_pins, android_lock)
    ios_vm = git("rev-parse", f"{rotation_pins['historicalMixer']}:vm").decode().strip()
    require(ios_vm == android_pins["engine"]["vmTree"], "Android and installed iOS VM sources differ")

    subprocess.run([sys.executable, "-B", str(ROOT / ROTATION / "prepare.py"), str(work)],
                   cwd=ROOT, check=True)
    fieldlog, mixer = (work / "source" / name for name in ("fieldlog", "mixer"))
    require(sha256((mixer / HEADER).read_bytes()).hexdigest() == binding["vmHeaderSHA256"],
            "Deferred guest transport differs")
    require(sha256((fieldlog / STORAGE).read_bytes()).hexdigest() == binding["storageAdapterSHA256"],
            "Selected-task storage adapter differs")

    require(source_digests(work / "source") == ROTATION_SOURCE_DIGESTS,
            "Staged rotation source inventories differ")
    renderer = mixer / APPLE_HOST
    corrected = git("show", f"{SCROLL_FIX}:{APPLE_HOST}")
    require(renderer.read_bytes() == git("show", f"{SCROLL_FIX}^:{APPLE_HOST}") and
            corrected == git("show", f"{BASE}:{APPLE_HOST}"), "Signed Apple V1 scroll host does not bind")
    renderer.write_bytes(corrected)
    apply_patch(fieldlog, "fieldlog-debug.patch")
    apply_patch(fieldlog, "fieldlog-host-layout.patch")
    xctest = fieldlog / "ios/FieldLogUITests/ChecklistJourney.swift"
    shutil.copyfile(HERE / xctest.name, xctest)

    packet = work / "packet"
    pins_path = packet / "pins.json"
    pins = json.loads(pins_path.read_bytes())
    xctest_digest = sha256(xctest.read_bytes()).hexdigest()
    pins.update(payloads=android_pins["payloads"], selector=SELECTOR, xctestSourceSHA256=xctest_digest)
    pins["sourceOverlaySHA256"][f"fieldlog/ios/FieldLogUITests/{xctest.name}"] = xctest_digest
    for name in ("ios/FieldLog/SignedChecklist.swift", "ios/FieldLog/WorkspaceModel.swift"):
        relative = f"fieldlog/{name}"
        updated = sha256((fieldlog / name).read_bytes()).hexdigest()
        require(updated != pins["sourceOverlaySHA256"][relative], f"FieldLog overlay was skipped: {name}")
        pins["sourceOverlaySHA256"][relative] = updated
    pins["sourceOverlaySHA256"][f"mixer/{APPLE_HOST}"] = sha256(corrected).hexdigest()
    write_json(pins_path, pins)

    templates = packet / "templates"
    android_manifest = tracked_json("tests/integration/fieldlog-android-engine-pair/inputs/manifest.json")
    common = android_manifest | {"scope": android_manifest["scope"] | {"platform": "ios"}}
    identity_path = templates / "Installed/identity.json"
    identity = json.loads(identity_path.read_bytes())
    require((identity["engine"]["guest_abi"], identity["engine"]["ui_schema"], identity["engine"]["profile"],
             identity["capability_execution"]["route"], identity["execution"]["startup_export"]) ==
            (2, 1, "mixer-table-memory-v3", "capability-guest-v1", "mixer_guest_ui_start_v1"),
            "Installed iOS guest profile differs")
    build_sources = source_digests(work / "source")
    require(all(build_sources[key] != before and build_sources[key] != identity["build"][key]
                for key, before in ROTATION_SOURCE_DIGESTS.items()), "Localized build inputs were not applied")
    identity["build"].update(build_sources)
    write_json(identity_path, identity)

    for name, payload in payloads.items():
        path = templates / f"{name}.manifest.json"
        manifest = json.loads(path.read_bytes())["manifest"]
        require(all(manifest[key] == value for key, value in common.items()), f"{name}: guest contract differs")
        pin = android_pins["payloads"][name]
        manifest.update(payload_sha256=pin["sha256"], expanded_bytes=pin["bytes"],
                        compressed_bytes=pin["bytes"], release_id=f"fieldlog-localized-{name}",
                        source_commit=android_lock["guestSourceCommit"],
                        provenance_id="fieldlog-localized-" + binding["localizedGuestSHA256"])
        write_json(path, {"manifest": manifest})
        (templates / f"{name}.wasm").write_bytes(payload)

    origin = packet / "origin.py"
    source = replace_once(
        origin.read_text(),
        'PHASES = ("baseline", "revoked-artifact", "revoked-assignment", "offline", "replacement", "complete")',
        'PHASES = ("baseline", "replacement", "offline", "complete")',
    )
    source = replace_once(source, '        elif phase == "replacement":\n'
                                  '            self.data = listener(DataHandler, self.data_port, self)\n', "")
    origin.write_text(source)
    runner = packet / "prepare-run.py"
    runner_source = replace_once(runner.read_text(), rotation_pins["selector"], SELECTOR)
    runner_source = replace_once(runner_source, "import uuid\n", "import uuid\nfrom identity_binding import verify as verify_identity\n")
    runner.write_text(replace_once(
        runner_source, '    expected = packet / "fixture" / "Installed"',
        '    verify_identity(packet, packet / "fixture")\n    expected = packet / "fixture" / "Installed"',
    ))
    host_validation = packet / "validate-host.py"
    host_source = replace_once(host_validation.read_text(), "import time\n",
                               "import time\nfrom identity_binding import verify as verify_identity\n")
    host_validation.write_text(replace_once(
        host_source, "    work.mkdir(mode=0o700)", "    verify_identity(PACKET, fixture)\n    work.mkdir(mode=0o700)",
    ))
    apply_patch(packet, "probe.patch")
    for name in ("identity_binding.py", "verify-readback.py"):
        shutil.copyfile(HERE / name, packet / name)
    bound_files = ("origin.py", "prepare-run.py", "validate-host.py", "probe/main.swift", "verify-readback.py",
                   "identity_binding.py", "pins.json", "Package.swift", "Package.resolved", "signer/main.swift",
                   *(f"templates/{name}{suffix}" for name in VARIANTS for suffix in (".wasm", ".manifest.json")),
                   *(str(path.relative_to(packet)) for path in sorted((templates / "Installed").iterdir())
                     if path != identity_path))
    report = {
        "mixer": BASE, "mixerTree": TREE, "fieldLog": rotation_pins["fieldLog"],
        "vmTree": ios_vm, "scrollFix": SCROLL_FIX, "scrollHostSHA256": sha256(corrected).hexdigest(),
        "storageAdapterSHA256": binding["storageAdapterSHA256"], "vmHeaderSHA256": binding["vmHeaderSHA256"],
        "guestSource": android_lock["guestSourceCommit"], "payloads": android_pins["payloads"],
        "selector": SELECTOR, "xctestSourceSHA256": xctest_digest,
        "rotationSourceDigests": ROTATION_SOURCE_DIGESTS, "buildSourceDigests": build_sources,
        "identityTemplateSHA256": sha256(identity_path.read_bytes()).hexdigest(),
        "overlayFilesSHA256": pins["sourceOverlaySHA256"],
        "packetFilesSHA256": {name: sha256((packet / name).read_bytes()).hexdigest() for name in bound_files},
    }
    write_json(packet / "localized-binding.json", report)
    verify(packet)
    print(json.dumps(report, indent=2))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path, help="new staging directory in owned scratch")
    parser.add_argument("--guests", type=Path, required=True, help="read-only verified Android guest export")
    args = parser.parse_args()
    try:
        prepare(args.work.resolve(), args.guests.resolve(strict=True))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
