"""Check current ABI admission with stock CLI and exact calculation evidence."""

import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CALC = HERE.parent / "fieldlog-task-calculation"
sys.path.insert(0, str(CALC / "android-packaging"))
sys.path.insert(0, str(REPO / "cli/release-tools"))
from canonical import cbor
from package import digest, require, read, write

LABELS = ("old", "successor")


def invoke(*command, expected=0):
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    require(result.returncode == expected, f"{command[0]} returned {result.returncode}: {result.stdout}\n{result.stderr}")
    return result.stdout


def project_view(work, template, variant, name, mixer):
    project = work / f"stock-{name}-view"
    shutil.copytree(template, project)
    config = project / "mixer.yml"
    android_only = read(config) | {"targets": ["android"]}
    config.unlink()
    write(config, android_only)
    projection = project / "FieldLog"
    projection.mkdir()
    invoke("git", "-C", variant / "fieldlog", "checkout-index", "--all", f"--prefix={projection}/")
    guest = project / "CalculationGuest"
    guest.mkdir()
    for file in ("Guest.swift", "TaskWire.swift"):
        shutil.copyfile(CALC / "guest" / file, guest / file)
    shutil.copyfile(CALC.parent / "fieldlog-saved-draft/guest/CapabilityImports.c", guest / "CapabilityImports.c")
    invoke("git", "-C", guest, "apply", "--whitespace=error", CALC / "patches/row-guest-completion-preview.patch")
    if name == "successor":
        invoke("git", "-C", guest, "apply", "--whitespace=error", CALC / "patches/completion-fix.patch")
    report = json_report(mixer, "release", "inspect", "--directory", project, expected=2)
    require(report["platforms"] == ["android"] and report["publicationAllowed"] is False, "Unexpected stock project scope")
    return project, report


def json_report(*args, expected):
    return json.loads(invoke(*args, expected=expected))


def protocol_check(work, packet):
    verifier = work / "update-build/debug/mixer-update"
    installation = read(packet / "verifier.json")["installation"]
    now = max(read(packet / label / "manifest.json")["manifest"]["created_at_unix"] for label in LABELS)
    cases = {}
    for name, runtime, manifest, assignment, payload, code in (
        ("baseline", "old", "old", "old", "baseline", None),
        ("successor", "successor", "successor", "successor", "reviewed", None),
        ("successorOnBaseline", "old", "successor", "successor", "reviewed", "v3.manifest.compatibility"),
        ("baselineOnSuccessor", "successor", "old", "old", "baseline", "v3.manifest.compatibility"),
        ("misboundAssignment", "old", "old", "successor", "baseline", "v3.assignment.binding"),
        ("wrongGuest", "old", "old", "old", "reviewed", "v3.payload.integrity"),
    ):
        host = packet / runtime
        result = json_report(verifier, "verify-v3",
                             "--host", host / "host.json", "--roots", host / "Installed/roots.json",
                             "--manifest", packet / manifest / "manifest.json", "--assignment", packet / assignment / "assignment.json",
                             "--payload", packet / f"{payload}.wasm", "--channel", "beta", "--installation", installation,
                             "--last-sequence", "0", "--now", str(now), expected=int(code is not None))
        if code is None:
            require(result["status"] == "protocol-verified"
                    and result["artifactSHA256"] == read(packet / assignment / "assignment.json")["assignment"]["artifact_sha256"],
                    "Stock verifier did not admit the exact signed offer")
        else:
            require(result["code"] == code, f"{name} failed at an unexpected check: {result}")
        cases[name] = result
    return {"verifierSHA256": digest(verifier), "cases": cases}


def stage_target(packet, target, label, native_name, offer_name, guest):
    folder = packet / label
    directory = target / native_name
    directory.mkdir()
    installed = folder / "Installed"
    materials = {
        "identity.json": "identity.json", "roots.json": "roots.json", "bridge.json": "bridge.json",
        "storage.json": "configuration.storage.keyValue.v1.json",
        "storage-grant.json": "grant.storage.keyValue.v1.json",
    }
    if label == "successor":
        materials.update({"http.json": "configuration.network.http.v1.json", "http-grant.json": "grant.network.http.v1.json"})
    for filename, destination in materials.items():
        shutil.copyfile(installed / filename, directory / destination)
    shutil.copyfile(folder / "FieldLog.apk", target / f"{native_name}.native")
    shutil.copyfile(folder / "permissions.json", target / f"{native_name}.permissions.json")
    for source, destination in (
        (folder / "manifest.json", "manifest.json"), (folder / "assignment.json", "assignment.json"),
        (packet / f"{guest}.wasm", "wasm"), (packet / "source-map.json", "source-map.json"),
    ):
        shutil.copyfile(source, target / f"{offer_name}.{destination}")
    return {
        "archiveSHA256": digest(folder / "FieldLog.apk"), "permissionsSHA256": digest(folder / "permissions.json"),
        "identitySHA256": digest(installed / "identity.json"),
    }


def inspect(work, packet):
    mixer = work / "stock-build/debug/mixer"
    openssl = Path("/opt/homebrew/opt/openssl@3/bin/openssl")
    require(invoke(openssl, "version").startswith("OpenSSL 3."), "Ed25519 diagnostic signing requires OpenSSL 3")
    template = work / "stock-project"
    _, baseline = project_view(work, template, work, "old", mixer)
    project, proposed = project_view(work, template, work / "successor", "successor", mixer)
    require(baseline["sourceDigest"] != proposed["sourceDigest"] and baseline["sdkDigest"] == proposed["sdkDigest"],
            "Stock project source or SDK binding differs")

    qualification = work / "stock-diagnostic"
    android = qualification / "android"
    android.mkdir(parents=True)
    pins = {
        "installed": stage_target(packet, android, "old", "installed", "baseline", "baseline"),
        "proposed": stage_target(packet, android, "successor", "proposed", "candidate", "reviewed"),
    }
    for name, label in zip(("baseline", "candidate"), LABELS, strict=True):
        folder = packet / label
        artifact = sha256(cbor(read(folder / "manifest.json")["manifest"])).hexdigest()
        require(artifact == read(folder / "assignment.json")["assignment"]["artifact_sha256"], "Signed digest drift")
        pins[name + "ArtifactSHA256"] = artifact

    # Use the actual calculation observations. The inspector's confirmation
    # observation schema differs and should stop this diagnostic at decode.
    behavior = android / "behavior.json"
    shutil.copyfile(packet / "host-replay.json", behavior)
    pins["behaviorReceiptSHA256"] = digest(behavior)
    producer = digest(Path(__file__))
    toolchain = qualification / "toolchain.json"
    per_variant = {label: read(packet / label / "Installed/identity.json")["toolchain"] for label in LABELS}
    write(toolchain, {"android": per_variant, "stockMixerSHA256": digest(mixer),
                      "stockSwiftVersion": invoke("/usr/bin/swift", "--version").splitlines(),
                      "opensslVersion": invoke(openssl, "version").strip()})
    manifest = read(packet / "successor/manifest.json")["manifest"]
    scope = {key: manifest["scope"][key] for key in ("organization", "project", "app", "environment")}
    index = qualification / "qualification.json"
    write(index, {
        "schema": 3, "sourceDigest": proposed["sourceDigest"], "sdkDigest": proposed["sdkDigest"],
        "baselineSourceDigest": baseline["sourceDigest"], "sourceCommit": manifest["source_commit"],
        "producerSHA256": producer, "toolchainSHA256": digest(toolchain), "scope": scope,
        "targets": {"android": pins},
    })

    trust = work / "stock-producer-trust.json"
    key = work / "stock-producer-private.pem"
    public = work / "stock-producer-public.der"
    message = work / "stock-signature-input"
    message.write_bytes(b"mixer.local.build-provenance.v1\0" + index.read_bytes())
    try:
        invoke(openssl, "genpkey", "-algorithm", "ed25519", "-out", key)
        invoke(openssl, "pkey", "-in", key, "-pubout", "-outform", "DER", "-out", public)
        der = public.read_bytes()
        require(len(der) == 44 and der[:12] == bytes.fromhex("302a300506032b6570032100"), "Unexpected Ed25519 encoding")
        write(trust, {"schema": 1, "producerSHA256": producer, "publicKey": base64.b64encode(der[12:]).decode()})
        invoke(openssl, "pkeyutl", "-sign", "-inkey", key, "-rawin", "-in", message,
               "-out", qualification / "qualification.ed25519")
    finally:
        key.unlink(missing_ok=True)

    command = (mixer, "release", "inspect", "--directory", project, "--qualification", qualification,
               "--producer-trust", trust)
    exact = json_report(*command, expected=2)
    require(exact["blockers"] == ["android release.invalid-evidence"] and exact["technicalEligibility"] == "blocked"
            and exact["publicationAllowed"] is False, f"Exact pair did not reach the behavior decoder: {exact}")
    candidate = android / "candidate.wasm"
    original = candidate.read_bytes()
    try:
        candidate.write_bytes((android / "baseline.wasm").read_bytes())
        wrong_guest = json_report(*command, expected=2)
        require(wrong_guest["blockers"] == ["android v3.payload.integrity"], f"Unexpected payload control: {wrong_guest}")
    finally:
        candidate.write_bytes(original)
    require(json_report(*command, expected=2) == exact, "Restored exact pair inspection changed")
    write(packet / "stock-inspection.json", {
        "scope": "Stock native ABI, exact native bytes and signed offer admission through the behavior decoder",
        "stockMixerSHA256": digest(mixer), "exact": exact, "wrongCandidateGuest": wrong_guest,
        "reason": "Stock confirmation behavior schema differs from the observed calculation behavior",
        "protocol": protocol_check(work, packet), "targetPins": pins,
    })


if __name__ == "__main__":
    os.umask(0o077)
    inspect(*(Path(arg).resolve(strict=True) for arg in sys.argv[1:]))
