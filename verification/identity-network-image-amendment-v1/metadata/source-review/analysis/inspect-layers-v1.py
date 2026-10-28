#!/usr/bin/env python3
"""Bounded OCI layer source inspection. Never extract or execute image files."""
import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import signal
import struct
import sys
import tarfile
import time
import urllib.request

BASE = Path(__file__).resolve().parent
DEST = BASE / "inputs" / "layers"
PLAN = json.loads((BASE / "layer-review-plan.json").read_text())
TEXT_PATHS = {"var/lib/dpkg/status", "etc/ssl/certs/ca-certificates.crt", "etc/ssl/openssl.cnf", "etc/os-release", "usr/lib/os-release", "usr/local/lib/erlang/releases/29/OTP_VERSION", "usr/local/lib/elixir/lib/elixir/ebin/elixir.app", "usr/local/lib/elixir/lib/mix/ebin/mix.app", "usr/local/lib/erlang/bin/erl", "usr/local/lib/erlang/bin/escript", "usr/local/lib/elixir/bin/elixir", "usr/local/lib/elixir/bin/mix"}

def alarm(_number, _frame):
    raise TimeoutError("absolute 55 second HTTP deadline exceeded")

def elf_metadata(data):
    if not data.startswith(b"\x7fELF"):
        return None
    if data[4:6] != b"\x02\x01":
        raise ValueError("unexpected ELF class/endianness")
    header = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    machine, phoff, phentsize, phnum = header[1], header[4], header[8], header[9]
    loads, dynamic, interpreter = [], None, None
    for index in range(phnum):
        kind, flags, offset, vaddr, paddr, size, memsize, align = struct.unpack_from("<IIQQQQQQ", data, phoff + index * phentsize)
        if kind == 1:
            loads.append((vaddr, offset, size))
        if kind == 2:
            dynamic = (offset, size)
        if kind == 3:
            interpreter = data[offset:offset+size].rstrip(b"\0").decode("ascii")
    needed, soname, strings = [], None, None
    entries = []
    if dynamic:
        for at in range(dynamic[0], dynamic[0] + dynamic[1], 16):
            key, value = struct.unpack_from("<qQ", data, at)
            if key == 0:
                break
            entries.append((key, value))
            if key == 5:
                strings = next(offset + value - address for address, offset, size in loads if address <= value < address + size)
        for key, value in entries:
            if key in (1, 14, 15, 29):
                start = strings + value
                value_text = data[start:data.index(0, start)].decode("ascii")
                if key == 1:
                    needed.append(value_text)
                elif key == 14:
                    soname = value_text
    return {"machine": machine, "class_bits": 64, "little_endian": True, "interpreter": interpreter, "needed": needed, "soname": soname}

class BoundedTar:
    def __init__(self, source, aggregate):
        self.source, self.aggregate = source, aggregate
        self.count = 0
        self.hash = hashlib.sha256()
    def read(self, size=-1):
        data = self.source.read(size)
        self.count += len(data)
        self.aggregate[0] += len(data)
        if self.count > PLAN["each_uncompressed_cap_bytes"] or self.aggregate[0] > PLAN["aggregate_uncompressed_cap_bytes"]:
            raise ValueError("decompressed source cap exceeded")
        self.hash.update(data)
        return data

def get_token():
    signal.alarm(55)
    try:
        with urllib.request.urlopen("https://auth.docker.io/token?service=registry.docker.io&scope=repository:hexpm/elixir:pull", timeout=50) as response:
            raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError("anonymous bearer cap exceeded")
            return json.loads(raw)["token"]
    finally:
        signal.alarm(0)

def fetch_layer(row, token):
    digest, cap = row["digest"], row["compressed_cap_bytes"]
    target = DEST / (row["label"] + ".tar.gz")
    if target.exists():
        raise ValueError("owned target already exists")
    url = "https://registry-1.docker.io/v2/hexpm/elixir/blobs/" + digest
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "User-Agent": "mixer-image-prerequisite-source-review/1"})
    record = {"url": url, "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "absolute_deadline_seconds": 55, "socket_timeout_seconds": 50, "response_cap_bytes": cap, "scope": "root-selected bounded layer source-only inspection; never execute/import/mount/extract", "label": row["label"], "retained_temporarily": str(target.relative_to(BASE))}
    started, count, hashed = time.monotonic(), 0, hashlib.sha256()
    signal.alarm(55)
    try:
        with urllib.request.urlopen(request, timeout=50) as response, target.open("xb") as output:
            record["status"] = response.status
            record["content_type"] = response.headers.get("Content-Type")
            while True:
                chunk = response.read(min(65536, cap + 1 - count))
                if not chunk:
                    break
                count += len(chunk)
                if count > cap:
                    raise ValueError("declared layer compressed cap exceeded")
                hashed.update(chunk)
                output.write(chunk)
            if count != cap or "sha256:" + hashed.hexdigest() != digest:
                raise ValueError("compressed size/digest mismatch")
            record.update(bytes=count, sha256=hashed.hexdigest(), complete=True)
    except Exception as error:
        record.update(error=type(error).__name__ + ": " + str(error), complete=False)
        raise
    finally:
        signal.alarm(0)
        record["elapsed_seconds"] = round(time.monotonic() - started, 6)
        with (BASE / "requests.jsonl").open("a") as output:
            output.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps(record, sort_keys=True), flush=True)
    return target

def inspect_layer(row, source, expected_diffid, aggregate):
    inventory = DEST / (row["label"] + "-inventory.jsonl")
    selected = DEST / "selected-text" / row["label"]
    selected.mkdir(parents=True, exist_ok=False)
    entries, text_rows = [], []
    with gzip.open(source, "rb") as decompressor, inventory.open("x") as output:
        stream = BoundedTar(decompressor, aggregate)
        with tarfile.open(fileobj=stream, mode="r|") as archive:
            for member in archive:
                if len(entries) >= PLAN["each_layer_member_count_cap"]:
                    raise ValueError("member count cap exceeded")
                path = member.name.removeprefix("./").rstrip("/")
                if path in ("", "."):
                    continue
                if PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts or "\\" in path or "\0" in path:
                    raise ValueError("unsafe member path")
                if member.issparse():
                    raise ValueError("sparse source member refused")
                item = {"path": path, "type": member.type.decode("ascii"), "bytes": member.size, "mode": oct(member.mode), "linkname": member.linkname, "uid": member.uid, "gid": member.gid}
                if member.isfile():
                    data_hash, content, total = hashlib.sha256(), bytearray(), 0
                    with archive.extractfile(member) as data:
                        first = data.read(min(65536, member.size))
                        retain_elf = first.startswith(b"\x7fELF")
                        retain_text = path in TEXT_PATHS
                        if retain_elf and member.size > 32 * 1024 * 1024:
                            raise ValueError("ELF inspection memory cap exceeded")
                        if retain_text and member.size > 1024 * 1024:
                            raise ValueError("selected text cap exceeded")
                        chunk = first
                        while chunk:
                            total += len(chunk)
                            data_hash.update(chunk)
                            if retain_elf or retain_text:
                                content.extend(chunk)
                            chunk = data.read(65536)
                    if total != member.size:
                        raise ValueError("source member truncated")
                    item["sha256"] = data_hash.hexdigest()
                    if retain_elf:
                        item["elf"] = elf_metadata(content)
                    if retain_text:
                        content.decode("utf-8")
                        text_target = selected / path.replace("/", "__")
                        text_target.write_bytes(content)
                        item["selected_text"] = str(text_target.relative_to(BASE))
                        text_rows.append({"path": path, "sha256": item["sha256"], "bytes": total, "retained": item["selected_text"]})
                entries.append(item)
                output.write(json.dumps(item, sort_keys=True) + "\n")
        while stream.read(65536):
            pass
        diffid = "sha256:" + stream.hash.hexdigest()
        if diffid != expected_diffid:
            raise ValueError("uncompressed diff_id mismatch")
    raw_inventory = inventory.read_bytes()
    record = {"label": row["label"], "compressed_sha256": row["digest"].split(":")[1], "compressed_bytes": source.stat().st_size, "uncompressed_bytes": stream.count, "uncompressed_diff_id": diffid, "members": len(entries), "inventory": str(inventory.relative_to(BASE)), "inventory_bytes": len(raw_inventory), "inventory_sha256": hashlib.sha256(raw_inventory).hexdigest(), "selected_text": text_rows, "no_image_execution_or_extraction": True}
    source.unlink()
    record["owned_compressed_blob_removed_after_verified_inventory"] = not source.exists()
    print(json.dumps({k: v for k, v in record.items() if k != "selected_text"}, sort_keys=True), flush=True)
    return entries, record

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGALRM, alarm)
    candidate = json.loads((BASE / "inputs/official/bookworm-candidate-amd64-config.json").read_text())
    selected = json.loads((BASE / "inputs/local/verification/identity-production-network-contract/inputs/registry/elixir-amd64-config.json").read_text())
    diffids = [selected["rootfs"]["diff_ids"][1]] + candidate["rootfs"]["diff_ids"]
    token, aggregate, records, merged = get_token(), [0], [], {}
    for number, (row, diffid) in enumerate(zip(PLAN["layers"], diffids, strict=True)):
        source = fetch_layer(row, token)
        entries, record = inspect_layer(row, source, diffid, aggregate)
        records.append(record)
        if number:
            for entry in entries:
                path = entry["path"]
                name = PurePosixPath(path).name
                parent = str(PurePosixPath(path).parent)
                if name == ".wh..wh..opq":
                    prefix = "" if parent == "." else parent + "/"
                    merged = {p: e for p, e in merged.items() if not p.startswith(prefix)}
                elif name.startswith(".wh."):
                    removed = str(PurePosixPath(parent) / name[4:])
                    merged = {p: e for p, e in merged.items() if p != removed and not p.startswith(removed + "/")}
                else:
                    if entry["type"] != "5":
                        merged = {p: e for p, e in merged.items() if not p.startswith(path + "/")}
                    merged[path] = dict(entry, layer=row["label"])
    merged_file = DEST / "bookworm-merged-inventory.jsonl"
    with merged_file.open("x") as output:
        for path, entry in sorted(merged.items()):
            output.write(json.dumps(entry, sort_keys=True) + "\n")
    raw_merged = merged_file.read_bytes()
    result = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "source-inventories-verified-only", "python": sys.version, "root_scope_selection": "Root message selected exact bounded5-layer plan before first download", "layers": records, "compressed_bytes_total": sum(r["compressed_bytes"] for r in records), "decompressed_bytes_total": aggregate[0], "merged_inventory": {"path": str(merged_file.relative_to(BASE)), "members": len(merged), "bytes": len(raw_merged), "sha256": hashlib.sha256(raw_merged).hexdigest()}, "anonymous_bearer_retained": False, "image_execution": False, "image_filesystem_extraction": False, "runtime_qualified": False}
    (BASE / "layer-inspection.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "layers"}, sort_keys=True))

if __name__ == "__main__":
    main()
