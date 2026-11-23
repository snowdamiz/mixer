"""Read the exact authenticated owner attachment and bind a fresh release fixture."""
import hashlib
import json
from pathlib import PurePosixPath

from prepare import require, roster


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unpack_app(data, output, expected):
    magic = b"MXNATIVE1\n"
    require(data.startswith(magic) and len(data) <= 128 * 1024 * 1024
            and (sha(data), len(data)) == (expected["sha256"], expected["sizeBytes"]), "wrong owner attachment")
    end_prefix = len(magic) + 8
    end_header = end_prefix + int.from_bytes(data[len(magic):end_prefix], "big")
    require(end_prefix < end_header <= len(data) and end_header - end_prefix <= 8 * 1024 * 1024,
            "invalid MXNATIVE1 header size")
    header = json.loads(data[end_prefix:end_header])
    entries = header["entries"]
    paths = [e["path"] for e in entries]
    require(header["version"] == 1 and header["kind"] == "unsigned_native_binary"
            and header["binding"] == expected["workerArchiveBinding"] and 0 < len(entries) <= 10000
            and paths == sorted(set(paths)), "worker archive binding or entry order differs")
    output.mkdir()
    offset = end_header
    inventory = {}
    for entry in entries:
        name, mode, size = (entry[k] for k in ("path", "mode", "size"))
        path = PurePosixPath(name)
        require(name.split("/") == list(path.parts) and all(p not in ("", ".", "..", "/") for p in path.parts)
                and "\0" not in name and 0 <= mode <= 0o777
                and 0 <= size <= len(data) - offset, "unsafe MXNATIVE1 entry")
        destination = output / name
        if entry["directory"]:
            require(size == 0 and entry["sha256"] == sha(b""), "invalid directory entry")
            destination.mkdir()
        else:
            value = data[offset:offset + size]
            require(sha(value) == entry["sha256"], "invalid entry digest")
            with destination.open("xb") as stream:
                stream.write(value)
            inventory[name] = entry["sha256"]
            offset += size
        destination.chmod(mode)
    require(offset == len(data) and inventory == roster(output), "archive extraction readback differs")
    return inventory
