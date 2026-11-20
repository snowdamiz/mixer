#!/usr/bin/env python3
"""Reconstruct the rotation source and admit only the exact guest payload pair."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PINS = json.loads((HERE / "pins.json").read_bytes())


def verify(path, expected):
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"{path}: expected SHA-256 {expected}, observed {actual}")


def git(*args, cwd=ROOT, **options):
    return subprocess.run(["git", "--no-replace-objects", *args], cwd=cwd,
                          check=True, **options)


def archive(revision, paths, temporary, destination):
    with temporary.open("xb") as stream:
        git("archive", revision, "--", *paths, stdout=stream)
    destination.mkdir()
    with tarfile.open(temporary) as source:
        source.extractall(destination, filter="data")
    temporary.unlink()


def prepare(work):
    for pin in ("publicBase", "signerMixer", "historicalMixer"):
        commit = PINS[pin]
        tree = git("rev-parse", f"{commit}^{{tree}}", capture_output=True, text=True).stdout.strip()
        if tree != PINS[f"{pin}Tree"]:
            raise ValueError(f"Unexpected Mixer tree for {commit}: {tree}")
    for package in ("updates", "runtime-identity"):
        git("diff", "--quiet", PINS["signerMixer"], PINS["historicalMixer"], "--", package)

    work.mkdir(mode=0o700)
    stage = work / "source"
    stage.mkdir()
    fieldlog = stage / "fieldlog"
    mixer = stage / "mixer"
    download = work / "fieldlog.tar.gz"
    subprocess.run([
        "curl", "--fail", "--location", "--max-time", "90",
        f"https://codeload.github.com/snowdamiz/fieldlog/tar.gz/{PINS['fieldLog']}",
        "--output", str(download),
    ], check=True)
    verify(download, PINS["fieldLogTarballSHA256"])
    with tarfile.open(download) as source:
        source.extractall(stage, filter="data")
    (stage / f"fieldlog-{PINS['fieldLog']}").rename(fieldlog)
    download.unlink()
    temporary = work / "source.tar"
    archive(PINS["historicalMixer"], [
        "capability-activation", "experimental-capability-runtime", "runtime-identity",
        "sdk", "updates", "vm/include",
    ], temporary, mixer)
    archive(PINS["signerMixer"], ["cli", "runtime-identity", "sdk", "services", "updates"],
            temporary, stage / "publisher")
    git("apply", str(HERE / "overlays/checklist.patch"), cwd=fieldlog)
    git("apply", str(HERE / "overlays/rotation.patch"), cwd=fieldlog)
    git("apply", str(HERE / "overlays/checklist-sdk.patch"), cwd=mixer)
    shutil.copyfile(HERE / "ChecklistJourney.swift", fieldlog / "ios/FieldLogUITests/ChecklistJourney.swift")
    for relative, expected in PINS["sourceOverlaySHA256"].items():
        verify(stage / relative, expected)

    packet = work / "packet"
    packet.mkdir()
    for name in ("origin.py", "prepare-run.py", "verify-readback.py", "validate-host.py",
                 "Package.swift", "Package.resolved", "pins.json"):
        shutil.copyfile(HERE / name, packet / name)
    for name in ("signer", "probe", "templates"):
        shutil.copytree(HERE / name, packet / name)
    print(json.dumps({
        "mixerBase": PINS["publicBase"],
        "mixerSDK": PINS["historicalMixer"],
        "fieldLog": PINS["fieldLog"],
        "verifiedOverlayFiles": len(PINS["sourceOverlaySHA256"]),
        "selector": PINS["selector"],
        "xctestSourceSHA256": PINS["xctestSourceSHA256"],
    }, indent=2))


def verify_payload(path, pin):
    if path.stat().st_size != pin["bytes"]:
        raise ValueError(f"{path}: expected {pin['bytes']} payload bytes")
    verify(path, pin["sha256"])


def admit_payloads(work, directory):
    differences = []
    for variant, pin in PINS["payloads"].items():
        try:
            verify_payload(directory / f"{variant}.wasm", pin)
        except (OSError, ValueError) as error:
            differences.append(str(error))
    if differences:
        raise ValueError("\n".join(differences))
    templates = work / "packet/templates"
    with tempfile.TemporaryDirectory(dir=templates) as temporary:
        staged = Path(temporary)
        for variant, pin in PINS["payloads"].items():
            name = f"{variant}.wasm"
            shutil.copyfile(directory / name, staged / name)
            verify_payload(staged / name, pin)
        linked = []
        try:
            for file in staged.iterdir():
                destination = templates / file.name
                destination.hardlink_to(file)
                linked.append(destination)
        except OSError:
            for destination in linked:
                destination.unlink()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path, help="new private output directory for source reconstruction")
    parser.add_argument("--payloads", type=Path, help="admit a source-built pair into an existing reconstruction")
    args = parser.parse_args()
    try:
        if args.payloads:
            admit_payloads(args.work.resolve(strict=True), args.payloads.resolve(strict=True))
        else:
            prepare(args.work.resolve())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
