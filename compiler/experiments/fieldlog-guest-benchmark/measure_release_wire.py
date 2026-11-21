#!/usr/bin/env python3
"""Check the exact draft-validation HTTP bodies and measure offline gzip size."""

import argparse
import base64
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zlib

from matched_task import Run, identity, require, sha


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HOST = ROOT / "verification/receipts/l08-android-workerd-control-plane-boundary-d3b23e0d.json"
INSTALLED = ROOT / "verification/receipts/l08-android-installed-workerd-outage-d3b23e0d.json"
ENCODER = HERE / "release_wire.go"


def exact_bytes(value, record):
    require(record["status"] == 200, "size sample must have an HTTP 200 response")
    require(len(value) == record["bytes"] and sha(value) == record["sha256"], "HTTP body differs")
    encoded = gzip.compress(value, compresslevel=9, mtime=0)
    require(gzip.decompress(encoded) == value, "gzip round trip changed the body")
    return {"httpBodyBytes": len(value), "httpBodySHA256": sha(value),
            "offlineGzipBytes": len(encoded), "offlineGzipSHA256": sha(encoded)}


def installed_artifacts(installed):
    device = installed["run"]
    require(device["status"] == "PASS" and device["deviceScratchRemoved"], "missing closed installed replay")
    return {row["sequence"]: row["artifactSHA256"] for row in device["observations"]}


def read_samples(packet, host, installed):
    used = installed_artifacts(installed)
    samples = []
    for stage, name, phase in zip(host["automatic"]["stages"], ("baseline", "corrected"),
                                  ("beforeOriginCut", "beforeEdgeCut"), strict=True):
        sequence = stage["sequence"]
        require(used.get(sequence) == stage["digest"], "signed artifact was not observed installed")
        wasm = (packet / f"{name}.wasm").read_bytes()
        manifest = (packet / f"{name}.manifest.json").read_bytes()
        assignment = (packet / f"sequence-{sequence}.assignment.json").read_bytes()
        require(len(wasm) == stage["payloadBytes"] and sha(wasm) == stage["payloadSha256"]
                and sha(manifest) == stage["signedManifestSha256"]
                and sha(assignment) == stage["assignmentSha256"], "signed packet bytes differ")
        artifact_url = stage["artifactPath"]
        samples.append({"stage": stage, "assignment": assignment, "manifest": manifest, "wasm": wasm,
                        "artifactURL": artifact_url, "recorded": host["automatic"]["phases"][phase]})
    return samples


def measure(sample, encoded):
    artifact_url = sample["artifactURL"]
    manifest, assignment, wasm = (sample[key] for key in ("manifest", "assignment", "wasm"))
    go_offer, artifact = (base64.b64decode(encoded[key], validate=True) for key in ("offer", "artifact"))
    edge_offer = (b'{"signed_assignment":' + assignment.strip() + b',"artifact_url":'
                  + json.dumps(artifact_url).encode() + b'}')
    responses = {}
    for origin, offer in (("origin", go_offer), ("edge", edge_offer)):
        recorded = sample["recorded"][origin]
        [artifact_record] = [row for row in recorded["artifacts"] if row["path"] == artifact_url]
        pair = {"offer": exact_bytes(offer, recorded["offer"]), "artifact": exact_bytes(artifact, artifact_record)}
        pair["fullBodyBytes"] = sum(value["httpBodyBytes"] for value in pair.values())
        pair["separateOfflineGzipBytes"] = pair["offer"]["offlineGzipBytes"] + pair["artifact"]["offlineGzipBytes"]
        responses[origin] = pair
    require(base64.b64decode(json.loads(artifact)["payload"], validate=True) == wasm, "payload differs")
    return {"sequence": sample["stage"]["sequence"], "manifestDigest": sample["stage"]["digest"],
            "payloadBytes": len(wasm), "payloadSHA256": sha(wasm), "signedManifestBytes": len(manifest),
            "signedAssignmentBytes": len(assignment), "base64PayloadBytes": len(base64.b64encode(wasm)),
            "responses": responses}


def campaign(run, packet, go):
    host = json.loads(HOST.read_bytes())
    installed = json.loads(INSTALLED.read_bytes())
    samples = read_samples(packet, host, installed)
    material = [{"signed_assignment": json.loads(sample["assignment"]), "artifact_url": sample["artifactURL"],
                 "artifact": {"signed_manifest": json.loads(sample["manifest"]),
                              "payload": base64.b64encode(sample["wasm"]).decode("ascii")}}
                for sample in samples]
    input_file = run.scratch / "releases.json"
    input_file.write_text(json.dumps(material))
    run.env.update(GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local", GOCACHE=str(run.scratch / "go-cache"))
    go_version = run.command("go-version", go, "version")[0].strip()
    bodies = json.loads(run.command("go-encode", go, "-C", ROOT / "services", "run", ENCODER, input_file,
                                   bound=65)[0])
    terminal = host["automatic"]["phases"]["originCutExpiredLease"]
    require((terminal["edgeOffer"]["status"], terminal["edgeArtifact"]["status"]) == (204, 404),
            "lost empty-response controls")
    return {"schema": 1, "status": "PASS_SCOPED", "observedUTC": datetime.now(timezone.utc).isoformat(),
            "revision": run.command("head", "/usr/bin/git", "rev-parse", "HEAD")[0].strip(),
            "sources": {str(path.relative_to(ROOT)): identity(path) for path in (Path(__file__), ENCODER)},
            "inputReceipts": {str(path.relative_to(ROOT)): identity(path) for path in (HOST, INSTALLED)},
            "tools": {"go": go_version, "python": sys.version.split()[0], "zlib": zlib.ZLIB_RUNTIME_VERSION},
            "rows": [measure(sample, encoded) for sample, encoded in zip(samples, bodies, strict=True)],
            "excludedResponses": [204, 404],
            "scope": "Two installed FieldLog draft-validation releases, each through Go and Workerd.",
            "compression": "Each exact response body separately gzipped offline, level 9 and mtime 0.",
            "limits": ["Body bytes exclude HTTP headers, TLS, framing, retries and APK installation.",
                       "Offline gzip sizes do not describe the transport used by the installed app.",
                       "These two releases are not the dogfood change corpus."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path, help="exact delivery-android directory used by the outage replay")
    args = parser.parse_args()
    go = shutil.which("go")
    require(go is not None, "Go compiler is required")
    local = ROOT / "verification/local"
    local.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="release-wire-", dir=local))
    run = Run(scratch)
    try:
        result = campaign(run, args.packet, go)
    finally:
        if run.active is not None:
            raise RuntimeError(f"UNKNOWN custody for {run.active}; preserve {scratch}")
        shutil.rmtree(scratch)
    result["commands"] = run.commands
    result["scratchRemoved"] = not scratch.exists()
    result["observedPeakScratchBytes"] = run.peak_scratch
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
