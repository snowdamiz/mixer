#!/usr/bin/env python3
"""Capture declared native build inputs; never attest dependency completeness.

The caller supplies a trusted built mixer-identity executable. The input manifest
contains data only, never commands. Builders must consume the captured objects,
not reopen the original input paths after this tool returns.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile

MAX_MANIFEST = 1_048_576
MAX_DESCRIPTOR = 131_072
MAX_FILES = 4096
MAX_FILE_BYTES = 1_073_741_824
MAX_TOTAL_BYTES = 4_294_967_296
CHUNK = 65_536
HEX = re.compile(r"[0-9a-f]{64}\Z")


class CaptureError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CaptureError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode() + b"\n"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pairs(entries):
    result = {}
    for key, value in entries:
        require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def decode(data):
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(CaptureError("nonfinite JSON")))
    except CaptureError:
        raise
    except (ValueError, RecursionError) as error:
        # JSONDecodeError and UnicodeDecodeError are ValueErrors. Python's
        # bounded integer parser also raises plain ValueError for long tokens.
        raise CaptureError("invalid JSON") from error
    # A bounded file can still encode excessive nested values. Reject before any
    # recursive descriptor traversal. The public Swift validator is authoritative.
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        require(depth <= 16 and count <= 30_000, "JSON structure limit")
        if isinstance(item, dict):
            stack.extend((x, depth + 1) for x in item.values())
        elif isinstance(item, list):
            stack.extend((x, depth + 1) for x in item)
    return value


def fields(value, expected):
    require(type(value) is dict and set(value) == set(expected), "unexpected object fields")


def relative(path):
    require(type(path) is str and 0 < len(path) <= 1024 and
            all(32 <= ord(c) <= 126 and c != "\\" for c in path), "invalid relative path")
    parts = path.split("/")
    require(all(0 < len(x) <= 255 and x not in (".", "..") for x in parts),
            "paths must have bounded printable ASCII components")
    return parts


def open_root(path):
    return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)


def open_file(root_fd, name):
    """Pin every component below the trusted root to an opened directory FD."""
    parts = relative(name)
    current = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                            dir_fd=current)
            os.close(current)
            current = child
        return os.open(parts[-1], os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW,
                       dir_fd=current)
    finally:
        os.close(current)


def stream_file(root_fd, name, limit, sink=None):
    fd = open_file(root_fd, name)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= limit,
                "input must be a bounded regular file")
        digest, size = hashlib.sha256(), 0
        while True:
            block = os.read(fd, min(CHUNK, limit - size + 1))
            if not block:
                break
            size += len(block)
            require(size <= limit, "input grew past its byte limit")
            digest.update(block)
            if sink:
                sink.write(block)
        after = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(identity(before) == identity(after) and size == before.st_size,
                "input changed while being captured")
        return {"sha256": digest.hexdigest(), "bytes": size}
    finally:
        os.close(fd)


def read_file(root_fd, name, limit):
    import io
    buffer = io.BytesIO()
    stream_file(root_fd, name, limit, buffer)
    return buffer.getvalue()


def read_path(path, limit):
    path = Path(path).absolute()
    root_fd = open_root(path.parent)
    try:
        return read_file(root_fd, path.name, limit)
    finally:
        os.close(root_fd)


def digest_paths(value, path=()):
    result = {}
    if type(value) is dict:
        for key, child in value.items():
            if key.endswith("_sha256"):
                require(type(child) is str and HEX.fullmatch(child), "invalid descriptor digest")
                result["/" + "/".join(path + (key,))] = child
            else:
                result.update(digest_paths(child, path + (key,)))
    elif type(value) is list:
        for index, child in enumerate(value):
            result.update(digest_paths(child, path + (str(index),)))
    return result


def replace_digest(descriptor, pointer, digest):
    parts = pointer[1:].split("/")
    value = descriptor
    for part in parts[:-1]:
        value = value[int(part)] if type(value) is list else value[part]
    value[parts[-1]] = digest


def inspect(tool, descriptor_path):
    # File arguments never become shell code. Output is small for the trusted
    # Mixer executable; arbitrary executable trust is outside input capture.
    result = subprocess.run([str(Path(tool).absolute()), "inspect", str(descriptor_path)],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=30, check=False)
    require(result.returncode == 0 and len(result.stdout) <= MAX_MANIFEST,
            "trusted mixer-identity rejected the descriptor")
    value = decode(result.stdout)
    require(type(value) is dict and value.get("buildAttested") is False and
            type(value.get("fingerprint")) is str and HEX.fullmatch(value["fingerprint"]),
            "invalid identity-tool result")
    return value["fingerprint"]


def validate_bindings(manifest, descriptor):
    fields(manifest, ["schema", "bindings"])
    require(type(manifest["schema"]) is int and manifest["schema"] == 1, "unknown binding schema")
    bindings = manifest["bindings"]
    expected = digest_paths(descriptor)
    require(type(bindings) is list and len(bindings) == len(expected), "every descriptor digest needs one binding")
    seen, files = set(), 0
    for binding in bindings:
        fields(binding, ["pointer", "kind", "files"])
        pointer, kind, entries = binding["pointer"], binding["kind"], binding["files"]
        require(type(pointer) is str and pointer in expected and pointer not in seen, "unknown or duplicate digest binding")
        seen.add(pointer)
        require(kind in ("file", "collection") and type(entries) is list, "unknown input binding kind")
        require(kind == "collection" or len(entries) == 1, "file binding requires one file")
        previous = None
        for entry in entries:
            fields(entry, ["name", "path"])
            relative(entry["name"]); relative(entry["path"])
            require(previous is None or previous < entry["name"], "logical input names must be sorted and unique")
            previous = entry["name"]
            files += 1
            require(files <= MAX_FILES, "too many declared files")
    return sorted(bindings, key=lambda x: x["pointer"])


def write_new(path, data):
    with open(path, "xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, 0o400)


def sync_directory(path):
    fd = open_root(path)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def capture(descriptor_path, bindings_path, input_root, output, tool):
    descriptor_bytes = read_path(descriptor_path, MAX_DESCRIPTOR)
    descriptor = decode(descriptor_bytes)
    manifest = decode(read_path(bindings_path, MAX_MANIFEST))
    bindings = validate_bindings(manifest, descriptor)
    output = Path(output).absolute()
    # Exclusive directory creation refuses existing files, links and directories.
    # inputs.json is written last: a partial directory is never a valid capture.
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    root_fd = None
    try:
        original = output / "original-descriptor.json"
        write_new(original, descriptor_bytes)
        inspect(tool, original)
        original.unlink()
        root_fd = open_root(input_root)
        objects = output / "objects"
        objects.mkdir(mode=0o700)
        captured, records, total, object_records = {}, [], 0, {}
        descriptor = copy.deepcopy(descriptor)
        for binding in bindings:
            entries = []
            for entry in binding["files"]:
                source = entry["path"]
                if source not in captured:
                    with tempfile.NamedTemporaryFile(dir=objects, prefix=".copy-", delete=False) as target:
                        temp = Path(target.name)
                        info = stream_file(root_fd, source, min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - total), target)
                        target.flush(); os.fsync(target.fileno())
                    total += info["bytes"]
                    destination = objects / info["sha256"]
                    if destination.exists():
                        temp.unlink()
                    else:
                        os.chmod(temp, 0o400)
                        temp.rename(destination)
                    captured[source] = info
                    object_records[info["sha256"]] = info["bytes"]
                entries.append({"name": entry["name"], **captured[source]})
            if binding["kind"] == "file":
                digest = entries[0]["sha256"]
            else:
                content = canonical({"schema": 1, "files": entries})
                digest = sha(content)
                if digest not in object_records:
                    write_new(objects / digest, content)
                    object_records[digest] = len(content)
            replace_digest(descriptor, binding["pointer"], digest)
            records.append({"pointer": binding["pointer"], "kind": binding["kind"], "sha256": digest, "files": entries})
        encoded = canonical(descriptor)
        require(len(encoded) <= MAX_DESCRIPTOR, "captured descriptor size limit")
        write_new(output / "descriptor.json", encoded)
        fingerprint = inspect(tool, output / "descriptor.json")
        report = {"schema": 1, "fingerprint": fingerprint, "descriptor_sha256": sha(encoded),
                  "bindings": records, "objects": object_records,
                  "build_attested": False, "complete_graph_proven": False}
        report_bytes = canonical(report)
        require(len(report_bytes) <= MAX_MANIFEST, "capture manifest size limit")
        sync_directory(objects)
        write_new(output / "inputs.json", report_bytes)
        sync_directory(output); sync_directory(output.parent)
        return {"fingerprint": fingerprint, "snapshotSHA256": sha(report_bytes), "objects": len(object_records),
                "sourceBytes": total, "buildAttested": False, "completeGraphProven": False}
    except BaseException:
        # The directory is private and exclusively created by this invocation.
        shutil.rmtree(output)
        raise
    finally:
        if root_fd is not None:
            os.close(root_fd)


def verified_descriptor(snapshot, expected_fingerprint, tool):
    """Return metadata and the exact descriptor bytes validated under one root FD.

    Build adapters must use the returned bytes, not reopen descriptor.json after
    verification. This does not attest that any other build input was consumed.
    """
    require(type(expected_fingerprint) is str and HEX.fullmatch(expected_fingerprint), "expected fingerprint required")
    root_fd = open_root(snapshot)
    try:
        report_bytes = read_file(root_fd, "inputs.json", MAX_MANIFEST)
        report = decode(report_bytes)
        fields(report, ["schema", "fingerprint", "descriptor_sha256", "bindings", "objects", "build_attested", "complete_graph_proven"])
        require(type(report["schema"]) is int and report["schema"] == 1 and
                report["build_attested"] is False and report["complete_graph_proven"] is False,
                "unsupported capture contract")
        require(report["fingerprint"] == expected_fingerprint, "unexpected snapshot identity")
        descriptor_bytes = read_file(root_fd, "descriptor.json", MAX_DESCRIPTOR)
        require(sha(descriptor_bytes) == report["descriptor_sha256"], "descriptor byte hash mismatch")
        descriptor = decode(descriptor_bytes)
        remaining = digest_paths(descriptor)
        require(type(report["objects"]) is dict and len(report["objects"]) <= MAX_FILES + 1024,
                "object inventory limit")
        total = 0
        for digest, size in report["objects"].items():
            require(HEX.fullmatch(digest) and type(size) is int and 0 <= size <= MAX_FILE_BYTES, "invalid object record")
            total += size
            require(total <= MAX_TOTAL_BYTES + MAX_MANIFEST, "snapshot total limit")
            actual = stream_file(root_fd, "objects/" + digest, size)
            require(actual == {"sha256": digest, "bytes": size}, "snapshot object hash mismatch")
        require(type(report["bindings"]) is list and len(report["bindings"]) == len(remaining), "binding coverage mismatch")
        used, count = set(), 0
        for binding in report["bindings"]:
            fields(binding, ["pointer", "kind", "sha256", "files"])
            pointer, digest, entries = binding["pointer"], binding["sha256"], binding["files"]
            require(type(pointer) is str and pointer in remaining and remaining.pop(pointer) == digest,
                    "descriptor binding mismatch")
            require(binding["kind"] in ("file", "collection") and type(entries) is list and
                    (binding["kind"] == "collection" or len(entries) == 1), "invalid captured binding")
            previous = None
            for entry in entries:
                fields(entry, ["name", "sha256", "bytes"])
                relative(entry["name"])
                require(previous is None or previous < entry["name"], "captured names must be sorted and unique")
                previous = entry["name"]
                require(type(entry["sha256"]) is str and entry["sha256"] in report["objects"] and
                        type(entry["bytes"]) is int and report["objects"][entry["sha256"]] == entry["bytes"], "missing captured file")
                used.add(entry["sha256"]); count += 1
                require(count <= MAX_FILES, "captured file count limit")
            expected = entries[0]["sha256"] if binding["kind"] == "file" else sha(canonical({"schema": 1, "files": entries}))
            require(expected == digest and digest in report["objects"], "collection hash mismatch")
            used.add(digest)
        require(not remaining and used == set(report["objects"]), "unbound captured objects")
        # Revalidate the exact in-memory descriptor bytes through the trusted tool;
        # do not let a path replacement between checks select different bytes.
        with tempfile.TemporaryDirectory(prefix="mixer-capture-verify-") as temporary:
            path = Path(temporary) / "descriptor.json"
            write_new(path, descriptor_bytes)
            require(inspect(tool, path) == expected_fingerprint, "runtime fingerprint mismatch")
        return ({"fingerprint": expected_fingerprint, "snapshotSHA256": sha(report_bytes),
                 "objects": len(used), "buildAttested": False, "completeGraphProven": False},
                descriptor_bytes)
    finally:
        os.close(root_fd)


def verify(snapshot, expected_fingerprint, tool):
    return verified_descriptor(snapshot, expected_fingerprint, tool)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("capture")
    for flag in ["descriptor", "bindings", "input-root", "output", "identity-tool"]:
        create.add_argument("--" + flag, required=True)
    check = sub.add_parser("verify")
    for flag in ["snapshot", "expected-fingerprint", "identity-tool"]:
        check.add_argument("--" + flag, required=True)
    args = parser.parse_args()
    try:
        if args.command == "capture":
            result = capture(args.descriptor, args.bindings, args.input_root, args.output, args.identity_tool)
        else:
            result = verify(args.snapshot, args.expected_fingerprint, args.identity_tool)
        print(json.dumps(result, sort_keys=True))
    except (CaptureError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, "capture failed: " + str(error) + "\n")


if __name__ == "__main__":
    main()
