#!/usr/bin/env python3
"""Bounded diagnostic artifact transport/extraction; no artifact code execution."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import selectors
import stat
import subprocess
import time
import zipfile

HERE = Path(__file__).resolve().parent
META = json.loads((HERE / "remote-metadata.json").read_text())
ZIP_LIMIT = 64 * 1024 * 1024
EXPANDED_LIMIT = 256 * 1024 * 1024
artifact = META["artifact"]
assert 0 < artifact["size_in_bytes"] <= ZIP_LIMIT
assert not artifact["expired"]
assert artifact["workflow_run"]["head_sha"] == "cc350d3303ca71c5d57e87846f6a61304b658fa7"
archive = HERE / "artifact.zip"
assert not archive.exists()
argv = ["gh", "api", f"repos/snowdamiz/mixer/actions/artifacts/{artifact['id']}/zip"]
started = time.monotonic()
size = 0
child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
try:
    reader = selectors.DefaultSelector()
    reader.register(child.stdout, selectors.EVENT_READ)
    with archive.open("xb") as output:
        while True:
            if time.monotonic() - started > 60:
                raise RuntimeError("artifact transport exceeded 60 seconds")
            if not reader.select(1):
                continue
            chunk = os.read(child.stdout.fileno(), 65536)
            if not chunk:
                break
            size += len(chunk)
            if size > ZIP_LIMIT:
                raise RuntimeError("artifact ZIP exceeded 64 MiB")
            output.write(chunk)
    assert child.wait(timeout=5) == 0, "artifact transport failed; stderr deliberately not persisted"
finally:
    if child.poll() is None:
        child.kill()
        child.wait(timeout=5)
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
assert size == artifact["size_in_bytes"]
assert "sha256:" + digest == artifact["digest"]
destination = HERE / "artifact"
assert not destination.exists()
manifest = {}
expanded = 0
with zipfile.ZipFile(archive) as source:
    entries = source.infolist()
    assert len(entries) <= 5000
    names = [entry.filename for entry in entries]
    assert len(set(names)) == len(names)
    assert sum(entry.file_size for entry in entries) <= EXPANDED_LIMIT
    for entry in entries:
        name = entry.filename
        parts = PurePosixPath(name)
        mode = entry.external_attr >> 16
        assert name and not parts.is_absolute() and ".." not in parts.parts
        assert "\\" not in name and ":" not in name and "\0" not in name
        assert not entry.flag_bits & 1 and not stat.S_ISLNK(mode)
        assert stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR)
    destination.mkdir()
    for entry in entries:
        target = destination / entry.filename
        target.resolve().relative_to(destination.resolve())
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        actual = 0
        hasher = hashlib.sha256()
        with source.open(entry) as input_stream, target.open("xb") as output:
            while chunk := input_stream.read(65536):
                actual += len(chunk)
                expanded += len(chunk)
                assert actual <= entry.file_size and expanded <= EXPANDED_LIMIT
                output.write(chunk)
                hasher.update(chunk)
        assert actual == entry.file_size
        manifest[entry.filename] = {"bytes": actual, "sha256": hasher.hexdigest()}
record = {"argv": argv, "transportSeconds": time.monotonic() - started,
          "zipBytes": size, "zipSHA256": digest, "githubDigestMatches": True,
          "zipLimit": ZIP_LIMIT, "expandedBytes": expanded, "expandedLimit": EXPANDED_LIMIT,
          "files": manifest, "signedURLsPersistedOrPrinted": False,
          "connectorFallbackReason": "connector download returned a remote file reference; bounded local transport and archive inspection used authenticated gh api without exposing redirect URLs"}
(HERE / "artifact-retention.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
print(json.dumps({key: record[key] for key in ("zipBytes", "expandedBytes", "zipSHA256", "githubDigestMatches")}, indent=2))
