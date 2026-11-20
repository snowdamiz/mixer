#!/usr/bin/env python3
"""Serve and verify the two signed FieldLog assignments on loopback."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import sys
import tempfile
import time
from urllib.parse import urlencode

from package import CHANNEL, LABELS, LOCK, PAIR, REPO, SCOPE, import_pair, load, pinned, require, sha


def wait_for_control(control, marker, deadline, *, permit_stop=False):
    while time.monotonic() < deadline:
        if permit_stop and (control / "stop").is_file():
            return False
        if (control / marker).is_file():
            return True
        time.sleep(0.1)
    raise TimeoutError(f"no {marker} control within the origin deadline")


def exercise(handoff, work, control, seconds):
    pair = import_pair("fieldlog_pair_origin", PAIR / "replay/origin.py")
    pair.ROOT = handoff
    pair.VERIFIER = pinned(handoff / "tools/verify-release", LOCK["base"]["tools/verify-release"])
    pinned(handoff / "tools/mixer-service", LOCK["base"]["tools/mixer-service"])
    package = load(handoff / "package-result.json")
    require(package["status"] == "apk-and-two-v3-releases-verified", "packaging is incomplete")
    pinned(handoff / "app/FieldLog.apk", package["apk"]["sha256"])

    route = load(handoff / "routing.json")
    config = load(handoff / "origin-config.template.json")
    host = package["host"]
    listener = route["listen"]
    port = int(listener.rsplit(":", 1)[1])
    require(listener == config["listen"] == f"127.0.0.1:{port}" and 1 <= port <= 65535
            and config["hosts"] == [host] and host["scope"] == SCOPE
            and route["runtime"] == host["runtime"] and config["developer_mode"] is True,
            "origin configuration differs from the packaged loopback runtime")
    installed = handoff / "app/Installed"
    require(int((installed / "port.txt").read_text()) == port
            and sha(installed / "roots.json") == load(installed / "identity.json")["build"]["trust_roots_sha256"]
            and load(installed / "roots.json") == config["roots"]
            and pair.inspect(installed / "identity.json") == host,
            "origin inputs differ from the installed trust and runtime")

    token = secrets.token_hex(32)
    config.update(data_directory=str(work / "store"),
                  tokens=[{"sha256": pair.digest(token.encode()), "role": "publisher",
                           "organization": SCOPE["organization"], "project": SCOPE["project"],
                           "actor": "fieldlog-localized-replay"}])
    path = pair.put_json(work / "service.json", config)
    evidence = {"http": {}, "serviceProcesses": {}, "offers": {},
                "apkSHA256": package["apk"]["sha256"], "runtime": host["runtime"], "port": port}
    origin = pair.Origin(work, path, port, token, evidence)
    installation = package["installationUsedByVerifier"]
    scope = {key: SCOPE[key] for key in ("organization", "project")}
    params = SCOPE | {"runtime": host["runtime"], "channel": CHANNEL, "installation": installation}
    offer_path = "/v3/updates?" + urlencode(params)
    urls = {}

    def fetch(label, tag):
        directory = handoff / label
        offer = origin.request("GET", offer_path, 200, f"offer-{tag}")
        expected = {"signed_assignment": load(directory / "assignment.json"), "artifact_url": urls[label]}
        require(json.loads(offer) == expected, f"{tag}: signed offer differs")
        artifact = origin.request("GET", urls[label], 200, f"artifact-{tag}")
        require(json.loads(artifact) == load(directory / "upload.json"), f"{tag}: signed artifact differs")
        evidence["offers"][tag] = {"sequence": package["releases"][label]["sequence"],
                                   "offerSHA256": pair.digest(offer), "artifactSHA256": pair.digest(artifact)}

    with origin.start("localized"):
        for label in LABELS:
            directory = handoff / label
            expected = package["releases"][label]
            checked = pair.verify(installed / "identity.json", installed / "roots.json",
                                  directory / "manifest.json", directory / "guest.wasm", directory / "assignment.json",
                                  installation, expected["cursor"], int(time.time()))
            require(checked == {key: value for key, value in expected.items() if key != "cursor"},
                    f"{label}: current-time signature verification differs")
            artifact = checked["artifactSHA256"]
            urls[label] = f"/v3/artifacts/{artifact}?" + urlencode(scope)
            origin.request("PUT", route["upload"]["path"].format(digest=artifact), 201, f"upload-{label}",
                           load(directory / "upload.json"), private=True)
            validated = origin.request("POST", route["validate"]["path"], 200, f"validate-{label}",
                                       load(directory / "validate.json"), private=True)
            validation = json.loads(validated)
            require(validation["protocol_valid"] and validation["artifact_sha256"] == artifact,
                    f"{label}: server validation differs")
            origin.request("GET", urls[label], 404, f"private-before-publish-{label}", error="not_found")

        for label in LABELS:
            if label == "reviewed":
                fetch("baseline", "before-reviewed")
                origin.request("GET", urls["reviewed"], 404, "reviewed-still-private", error="not_found")
                if control and not wait_for_control(control, "publish-reviewed", time.monotonic() + seconds,
                                                    permit_stop=True):
                    break
            published = origin.request("POST", route["publish"]["path"], 200, f"publish-{label}",
                                       load(handoff / label / "publish.json"), private=True)
            expected = package["releases"][label]
            observed = json.loads(published)
            require((observed["sequence"], observed["artifact_sha256"]) ==
                    (expected["sequence"], expected["artifactSHA256"]), f"{label}: published assignment differs")
            fetch(label, label)
            if control:
                ready = pair.put_json(control / f"{label}.tmp", evidence["offers"][label] | {"port": port})
                ready.rename(control / f"{label}.ready.json")
        if control and not (control / "stop").is_file():
            wait_for_control(control, "stop", time.monotonic() + seconds)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--control", type=Path, help="fresh directory for publish-reviewed and stop files")
    parser.add_argument("--seconds", type=int, default=900, help="deadline for each control file")
    args = parser.parse_args()
    require(args.seconds > 0, "control deadline must be positive")
    handoff = args.handoff.resolve(strict=True)
    os.umask(0o077)
    control = args.control
    if control:
        control.mkdir(mode=0o700)
        control = control.resolve(strict=True)
    parent = REPO / "verification/local"
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="fieldlog-localized-origin.", dir=parent))
    try:
        result = exercise(handoff, work, control, args.seconds)
    finally:
        hold = work.parent / (work.name + ".service-custody.json")
        if hold.exists():
            print(f"Retained origin scratch with unresolved custody at {work}", file=sys.stderr)
        else:
            shutil.rmtree(work)
    result["scratchRemoved"] = not work.exists()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
