#!/usr/bin/env python3
"""Host-only input replay. Never imports or executes harness/build/runtime code."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def checked_files(root, bindings, mutable=()):
    checked = 0
    for name, expected in bindings.items():
        path = root / name
        if (not isinstance(name, str) or not name or Path(name).is_absolute()
                or any(part in ("", ".", "..") for part in name.split("/"))):
            raise ValueError("unsafe source path")
        if name in mutable:
            continue
        if (path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root)
                or sha(path) != expected):
            raise ValueError("input mismatch: " + name)
        checked += 1
    return checked


def checked_image(image, expected_digest, expected_media):
    descriptor = image.get("Descriptor", {})
    if (image.get("Os") != "linux" or image.get("Architecture") != "arm64"
            or descriptor.get("digest") != expected_digest
            or descriptor.get("mediaType") != expected_media):
        raise ValueError("candidate image identity mismatch")


def audit(root, preparation):
    if preparation.get("schema") != 1 or preparation.get("runtimeAuthorized") is not False:
        raise ValueError("preparation cannot authorize runtime")
    closure = preparation["historicalSourceInputs"]
    if (digest(closure) != preparation["sourceClosureDigest"]
            or preparation["historicalMutablePath"] != "PLAN.md"):
        raise ValueError("historical source closure mismatch")
    fixed_count = checked_files(root, preparation["fixedInputs"])
    source_count = checked_files(root, closure, ("PLAN.md",))
    producer = json.loads((root / preparation["producerSealPath"]).read_text())
    review = json.loads((root / preparation["independentSealPath"]).read_text())
    sealed_count = checked_files(root, producer["files"])
    review_count = checked_files(root, review["files"])
    acceptance = json.loads((root / preparation["rootAcceptancePath"]).read_text())
    if (acceptance.get("sourceAndHostMethodAccepted") is not True
            or acceptance.get("runtimeAuthorized") is not False
            or acceptance.get("LinuxCompilationAccepted") is not False
            or acceptance.get("LinuxRuntimeAccepted") is not False
            or acceptance.get("runtimeRowsExecuted") != 0):
        raise ValueError("unexpected acceptance scope")
    accepted_count = checked_files(root, acceptance["files"])
    dependencies = json.loads((root / preparation["dependencyManifestPath"]).read_text())
    dependency_count = checked_files(root, dependencies["files"])
    prior_tools = json.loads((root / preparation["priorToolManifestPath"]).read_text())
    tool_root = Path(preparation["toolSourceRoot"]).resolve(strict=True)
    hex_bindings = {name.removeprefix("mix/"): expected
                    for name, expected in prior_tools["hexArchiveTree"].items()}
    tool_count = checked_files(tool_root, {**hex_bindings,
        "elixir/1-20-otp-29/rebar3": prior_tools["rebar3SHA256"]})
    image = preparation["candidateImage"]
    for key, expected_digest, media in (
            ("indexObservation", image["indexDigest"], "application/vnd.oci.image.index.v1+json"),
            ("platformObservation", image["platformDigest"], "application/vnd.oci.image.manifest.v1+json")):
        observed = json.loads((root / image[key]).read_text())
        checked_image(observed, expected_digest, media)
    return {
        "schema": 1,
        "status": "passed-host-input-bindings-only",
        "fixedInputCount": fixed_count,
        "liveHistoricalInputCount": source_count,
        "historicalInputCount": len(closure),
        "historicalPlanSha256": closure["PLAN.md"],
        "currentPlanSha256": sha(root / "PLAN.md"),
        "producerSealedFileCount": sealed_count,
        "independentSealedFileCount": review_count,
        "rootAcceptedFileCount": accepted_count,
        "dependencySourceFileCount": dependency_count,
        "hexAndRebarToolFileCount": tool_count,
        "sourceClosureDigest": digest(closure),
        "candidatePlatformDigest": image["platformDigest"],
        "LinuxCompilationAccepted": False,
        "LinuxRuntimeAccepted": False,
        "runtimeAuthorized": False,
        "runtimeRowsExecuted": 0,
        "all30RuntimeMatrixRows": "pending",
        "gaAccepted": False,
        "scope": "File hashes and recorded read-only Docker metadata; no artifact build, ELF resolution or enforcement proof",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    preparation = json.loads((Path(__file__).resolve().parent / "preparation.json").read_text())
    print(json.dumps(audit(root, preparation), indent=2, sort_keys=True))
