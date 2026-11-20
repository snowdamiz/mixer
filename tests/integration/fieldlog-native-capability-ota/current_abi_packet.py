"""Inventory and bind a closed current-ABI Android handoff."""

import base64
from contextlib import nullcontext
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys
from urllib.parse import urlencode
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "cli/release-tools"))
from canonical import cbor
from package import GUESTS, digest, inventory, read, require, tree

LABELS = ("old", "successor")
GUEST_FOR_OFFER = {"old": "baseline", "successor": "reviewed", "refused": "reviewed"}
INSTALLED = {
    "old": {"bridge.json", "calculation-seed.json", "identity.json", "port.txt", "roots.json",
            "storage-grant.json", "storage.json"},
}
INSTALLED["successor"] = INSTALLED["old"] | {"http.json", "http-grant.json"}
ASSETS = "assets/ChecklistRelease/"
PACKAGED = {"baseline.wasm", "reviewed.wasm", "source-map.json", "verifier.json", "build.json",
            "host-replay.json", "stock-inspection.json", "refused/assignment.json", "refused/manifest.json"}
for label in LABELS:
    PACKAGED.update(f"{label}/{name}" for name in ("FieldLog.apk", "permissions.json", "linked-inputs.json",
                                                   "installed.sha256.json", "host.json", "manifest.json", "assignment.json"))
    PACKAGED.update(f"{label}/Installed/{name}" for name in INSTALLED[label])
SEALED = PACKAGED | {"rebuild.json", "android-origin.py"}
HANDOFF_LIMIT = 512 * 1024 * 1024
METADATA_LIMIT = 8 * 1024 * 1024


def require_members(packet, expected):
    directories = {"old", "old/Installed", "successor", "successor/Installed", "refused"}
    files = set()
    for path in packet.rglob("*"):
        name = path.relative_to(packet).as_posix()
        require(not path.is_symlink() and (path.is_file() or (path.is_dir() and name in directories)),
                f"Unexpected handoff entry: {name}")
        if path.is_file():
            files.add(name)
    require(files == expected,
            f"Handoff member mismatch. Missing {sorted(expected - files)}. Extra {sorted(files - expected)}")


def packet_hashes(packet, expected, snapshot=None):
    require_members(packet, expected)
    remaining = HANDOFF_LIMIT
    hashes = {}
    for name in sorted(expected):
        limit = remaining if name.endswith("/FieldLog.apk") else min(remaining, METADATA_LIMIT)
        if snapshot is not None:
            (snapshot / name).parent.mkdir(parents=True, exist_ok=True)
        target = (snapshot / name).open("xb") if snapshot is not None else nullcontext()
        checksum = sha256()
        with target as output, open(packet / name, "rb", opener=open_packet_file) as source:
            info = os.fstat(source.fileno())
            require(stat.S_ISREG(info.st_mode), f"Expected a regular handoff file: {name}")
            require(info.st_size <= limit, f"Handoff size limit exceeded: {name}")
            while chunk := source.read(min(1024 * 1024, limit + 1)):
                require(len(chunk) <= limit, f"Handoff size limit exceeded: {name}")
                limit -= len(chunk)
                remaining -= len(chunk)
                checksum.update(chunk)
                if output is not None:
                    output.write(chunk)
        hashes[name] = checksum.hexdigest()
    return hashes


def open_packet_file(path, flags):
    return os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK)


def offer_pins(packet, label):
    folder = packet / label
    assignment, manifest = (folder / name for name in ("assignment.json", "manifest.json"))
    body = read(manifest)["manifest"]
    artifact = sha256(cbor(body)).hexdigest()
    payload = digest(packet / f"{GUEST_FOR_OFFER[label]}.wasm")
    require(read(assignment)["assignment"]["artifact_sha256"] == artifact
            and body["payload_sha256"] == payload, f"Signed artifact or payload binding differs for {label}")
    return {"artifactSHA256": artifact, "manifestSHA256": digest(manifest),
            "assignmentSHA256": digest(assignment), "payloadSHA256": payload}


def refusal_responses(packet, host, installation):
    assignment = read(packet / "refused/assignment.json")
    scope = host["scope"]
    tenant = {key: scope[key] for key in ("organization", "project")}
    query = scope | {"channel": "beta", "runtime": host["runtime"], "installation": installation}
    artifact_path = "/v3/artifacts/" + assignment["assignment"]["artifact_sha256"]
    responses = (
        ("/v3/updates", query, {"signed_assignment": assignment, "artifact_url": artifact_path + "?" + urlencode(tenant)}),
        (artifact_path, tenant, {"signed_manifest": read(packet / "refused/manifest.json"),
                                "payload": base64.b64encode((packet / "reviewed.wasm").read_bytes()).decode()}),
    )
    return [{"path": path, "query": query, "status": 200,
             "bodySHA256": sha256(json.dumps(body, separators=(",", ":")).encode()).hexdigest()}
            for path, query, body in responses]


def bindings(packet):
    source_map = digest(packet / "source-map.json")
    require(all(read(packet / label / "manifest.json")["manifest"]["source_map_sha256"] == source_map
                for label in GUEST_FOR_OFFER), "Signed source map binding differs")
    native = {}
    for label in LABELS:
        folder = packet / label
        installed = folder / "Installed"
        native[label] = {"archiveSHA256": digest(folder / "FieldLog.apk"),
                         "installed": inventory(installed, installed), "hostSHA256": digest(folder / "host.json")}
    return {"native": native, "offers": {label: offer_pins(packet, label) for label in GUEST_FOR_OFFER}}


def verify_materials(packet, build, inspection, observed):
    """Cross-check APK members, final material, and the stock qualification pins."""
    targets = inspection["targetPins"]
    require(build["guests"] == GUESTS and all(
        observed["offers"][label]["payloadSHA256"] == GUESTS[guest] for label, guest in GUEST_FOR_OFFER.items()
    ), "Build or offer guest pins differ")
    require(targets["behaviorReceiptSHA256"] == digest(packet / "host-replay.json"), "Inspected replay bytes differ")
    for label, target, offer in zip(LABELS, ("installed", "proposed"), ("baseline", "candidate"), strict=True):
        folder = packet / label
        apk = build["apks"][label]
        native = observed["native"][label]
        installed = native["installed"]
        require(native["archiveSHA256"] == apk["apkSHA256"] == targets[target]["archiveSHA256"],
                f"Final APK differs from build or stock inspection: {label}")
        require(installed == read(folder / "installed.sha256.json") == {
            name.removeprefix(ASSETS): value for name, value in apk["members"].items() if name.startswith(ASSETS)
        }, f"Installed material pins differ for {label}")
        with ZipFile(folder / "FieldLog.apk") as image:
            assets = [entry for entry in image.infolist() if entry.filename.startswith(ASSETS)]
            require(len(assets) == len(installed) and {entry.filename for entry in assets} ==
                    {ASSETS + name for name in installed}, f"Unexpected packaged APK assets: {label}")
            require(all(entry.file_size == (folder / "Installed" / entry.filename.removeprefix(ASSETS)).stat().st_size
                        for entry in assets) and installed == {
                entry.filename.removeprefix(ASSETS): sha256(image.read(entry)).hexdigest() for entry in assets
            }, f"Installed material differs from packaged APK assets: {label}")
        permissions = digest(folder / "permissions.json")
        identity = read(folder / "Installed/identity.json")["build"]
        linked = read(folder / "linked-inputs.json")
        require(installed["identity.json"] == targets[target]["identitySHA256"]
                and permissions == identity["permissions_sha256"] == targets[target]["permissionsSHA256"]
                and installed["roots.json"] == identity["trust_roots_sha256"]
                and identity["link_inputs_sha256"] == tree(linked)
                and {name.removeprefix("installed/"): value for name, value in linked.items()
                     if name.startswith("installed/")} == {name: value for name, value in installed.items()
                                                           if name not in {"identity.json", "roots.json"}},
                f"Inspected identity, permissions or linked Installed material differs for {label}")
        require(read(folder / "host.json")["runtime"] == apk["runtime"]
                == read(folder / "assignment.json")["assignment"]["runtime"]
                and observed["offers"][label]["artifactSHA256"] == targets[offer + "ArtifactSHA256"],
                f"Inspected offer differs for {label}")


def validate_for_seal(packet):
    require_members(packet, PACKAGED)
    build = read(packet / "build.json")
    inspection = read(packet / "stock-inspection.json")
    observed = bindings(packet)
    require(observed == build["handoffInputs"], "Handoff inputs differ from build receipt")
    require(observed == inspection["handoffInputs"], "Handoff inputs differ from inspection receipt")
    verify_materials(packet, build, inspection, observed)
    replay = read(packet / "host-replay.json")
    exchange = replay["refusalExchange"]
    refused = observed["offers"]["refused"]
    verifier = read(packet / "verifier.json")
    require(all(exchange[key] == value for key, value in refused.items())
            and exchange["runtime"] == build["apks"]["old"]["runtime"]
            and exchange["installation"] == verifier["installation"]
            and exchange["responses"] == refusal_responses(packet, read(packet / "old/host.json"), verifier["installation"])
            and replay["observations"]["oldAfterRefusal"]["label"] == "Using saved checklist release"
            and replay["observations"]["oldAfterRefusal"]["candidate"] == replay["observations"]["old"]["candidate"],
            "Refusal exchange and observed fallback do not bind the inspected artifact")
    require(replay["separateVerifierRefusal"] == {
        "code": verifier["manifestRefusal"], "artifactSHA256": refused["artifactSHA256"],
    } and inspection["protocol"]["cases"]["refusedOnBaseline"]["code"] == verifier["manifestRefusal"]
        == "v3.manifest.compatibility",
        "Separate verifier refusal differs")
