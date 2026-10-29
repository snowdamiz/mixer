"""Unselected pure-data comparator. No filesystem, CLI, process or network API.
Caller must separately bind stable regular-file bytes under guarded Python -I -B -S.
No member is extracted, imported, loaded or executed; no runtime admission follows.
"""
import binascii
import gzip
import hashlib
import io
import json
import stat
import struct
import tarfile
import zlib

ARCHIVE_SIZE = 193594705
ARCHIVE_SHA = "8b9b611d917e3dfd8419d3566b5949226f69b052fed7e109c1368add1dfe8711"
ROOT = "jdk-17.0.21+9"
EXPECTED = {
    "lib/ct.sym": {"bytes": 8301486, "sha256": "76b7fa16e006d67f7a65c46f0c4d727ec4ead9d982b8f82538e0e6b255e8fdcf"},
    "lib/jrt-fs.jar": {"bytes": 110513, "sha256": "09bed1c9354a0671807504f255229f0c767a02a612eb3be8675216f58cec84ce"},
}
RAW_CAPS = {"lib/ct.sym": 16777216, "lib/jrt-fs.jar": 1048576}
CHUNK = 65536


class Refusal(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def safe_name(name, directory=False, maximum=1024, depth=32):
    need(type(name) is str and name and "\\" not in name and ":" not in name, "unsafe archive name")
    canonical_name = name[:-1] if directory and name.endswith("/") else name
    parts = canonical_name.split("/")
    need(not canonical_name.startswith("/") and len(name.encode("utf-8")) <= maximum and len(parts) <= depth, "path bound")
    need(all(part not in ("", ".", "..") for part in parts), "empty/dot/traversal name")
    need(all(32 <= ord(c) < 127 for c in name), "non-ASCII/control archive name refused without normalization")
    return canonical_name


def official_members(archive_bytes):
    need(type(archive_bytes) is bytes and len(archive_bytes) == ARCHIVE_SIZE, "exact official immutable archive size required")
    need(identity(archive_bytes)["sha256"] == ARCHIVE_SHA, "official archive SHA256 mismatch before gzip")
    class LimitedReader:
        def __init__(self, stream):
            self.stream, self.total = stream, 0
        def read(self, size):
            need(type(size) is int and 0 <= size <= CHUNK, "bounded gzip read required")
            result = self.stream.read(min(size, 402653184 - self.total + 1))
            self.total += len(result)
            need(self.total <= 402653184, "gzip expansion cap")
            return result
    selected, seen, declared = {}, set(), 0
    with gzip.GzipFile(fileobj=io.BytesIO(archive_bytes), mode="rb") as gz:
        limited = LimitedReader(gz)
        with tarfile.open(fileobj=limited, mode="r|", bufsize=10240) as archive:
            for member in archive:
                name = safe_name(member.name, member.isdir(), maximum=4096, depth=64)
                need(name == ROOT or name.startswith(ROOT + "/"), "unexpected official tar root")
                need(name not in seen and len(seen) < 1024, "duplicate tar name or count cap")
                seen.add(name)
                need(0 <= member.size <= 268435456, "tar member size cap")
                declared += member.size
                need(declared <= 402653184, "tar declared expansion cap")
                relative = name[len(ROOT) + 1:] if name != ROOT else ""
                if relative not in EXPECTED:
                    continue
                need(relative not in selected and member.type in (tarfile.REGTYPE, tarfile.AREGTYPE) and not member.issym() and not member.islnk() and not member.sparse, "selected tar member must be a unique ordinary file")
                need(member.size == EXPECTED[relative]["bytes"], "selected official member declared size mismatch")
                stream = archive.extractfile(member)
                need(stream is not None, "selected tar data absent")
                chunks, size = [], 0
                with stream:
                    while True:
                        chunk = stream.read(min(CHUNK, member.size - size + 1))
                        if not chunk:
                            break
                        size += len(chunk)
                        need(size <= member.size, "selected tar data exceeds exact size")
                        chunks.append(chunk)
                data = b"".join(chunks)
                need(identity(data) == EXPECTED[relative], "selected official member exact identity mismatch")
                selected[relative] = data
        # Drain through gzip EOF so CRC/ISIZE and all delivered padding are checked.
        while limited.read(CHUNK):
            pass
    need(set(selected) == set(EXPECTED), "the exact two official members are required")
    need(len(seen) == 543 and limited.total == 332994560, "official tar counts differ from frozen data receipt")
    return selected, {"archive": {"bytes": ARCHIVE_SIZE, "sha256": ARCHIVE_SHA}, "tar_members": len(seen), "gzip_delivered_bytes": limited.total, "selected": EXPECTED}


def extra_fields(data):
    need(len(data) <= 4096, "ZIP extra-field cap")
    at, seen = 0, set()
    while at < len(data):
        need(at + 4 <= len(data), "truncated ZIP extra field")
        tag, size = struct.unpack_from("<HH", data, at)
        at += 4
        need(at + size <= len(data) and tag not in seen, "truncated/duplicate ZIP extra field")
        need(tag not in (1, 0x9901), "ZIP64/AES extra field refused")
        seen.add(tag)
        at += size


def payload_identity(compressed, method, declared, crc_expected, budget):
    need(0 <= declared <= 8388608, "ZIP per-entry expansion cap")
    digest, crc, total = hashlib.sha256(), 0, 0
    def accept(block):
        nonlocal crc, total
        total += len(block)
        budget["expanded"] += len(block)
        need(total <= declared and budget["expanded"] <= 536870912, "ZIP actual expansion cap")
        digest.update(block)
        crc = binascii.crc32(block, crc)
    if method == 0:
        need(len(compressed) == declared, "stored ZIP size mismatch")
        for at in range(0, len(compressed), CHUNK):
            accept(compressed[at:at + CHUNK])
    else:
        need(method == 8, "unsupported ZIP compression")
        decoder, at = zlib.decompressobj(-15), 0
        while at < len(compressed):
            piece = compressed[at:at + CHUNK]
            at += len(piece)
            while piece:
                before = len(piece)
                block = decoder.decompress(piece, min(CHUNK, declared - total + 1, 536870912 - budget["expanded"] + 1))
                accept(block)
                piece = decoder.unconsumed_tail
                need(not decoder.unused_data, "trailing bytes after raw DEFLATE stream")
                need(not piece or len(piece) < before or bool(block), "DEFLATE made no progress")
                if decoder.eof:
                    need(not piece and at == len(compressed), "unconsumed or trailing compressed bytes")
                    break
        need(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, "incomplete or ambiguous raw DEFLATE stream")
    need(total == declared and (crc & 0xffffffff) == crc_expected, "ZIP payload length/CRC mismatch")
    return {"bytes": total, "sha256": digest.hexdigest(), "crc32": crc & 0xffffffff}


def inspect_zip(raw, cap, budget):
    need(type(raw) is bytes and 22 <= len(raw) <= cap and raw[:4] == b"PK\x03\x04", "ordinary bounded ZIP envelope required")
    end = raw.rfind(b"PK\x05\x06", max(0, len(raw) - 65557))
    need(end >= 0 and end + 22 <= len(raw), "ZIP EOCD missing")
    e = struct.unpack_from("<4s4H2IH", raw, end)
    need(e[1] == e[2] == 0 and e[3] == e[4] and 1 <= e[4] <= 65534 and e[5] + e[6] == end and end + 22 + e[7] == len(raw), "ZIP disk/ZIP64/central/trailing ambiguity")
    payloads, metadata, compressed_map, aliases, names, ranges, order = {}, {}, {}, set(), set(), [], []
    cursor, total_declared, metadata_bytes = e[6], 0, len(raw) - end
    for ordinal in range(e[4]):
        need(cursor + 46 <= end, "truncated central header")
        c = struct.unpack_from("<4s6H3I5H2I", raw, cursor)
        need(c[0] == b"PK\x01\x02" and c[13] == 0, "central header/disk mismatch")
        flags, method, crc, csize, usize = c[3], c[4], c[7], c[8], c[9]
        nlen, xlen, clen, offset = c[10], c[11], c[12], c[16]
        need(c[2] <= 20 and not flags & ~(0x800 | 8 | 6) and method in (0, 8), "ZIP encryption/flags/compression/version refused")
        need(csize != 0xffffffff and usize != 0xffffffff and offset != 0xffffffff, "ZIP64 entry refused")
        need(nlen <= 1024 and xlen <= 4096 and clen <= 4096 and cursor + 46 + nlen + xlen + clen <= end, "central variable-field bound")
        central_end = cursor + 46 + nlen + xlen + clen
        encoded = raw[cursor + 46:cursor + 46 + nlen]
        name = encoded.decode("utf-8" if flags & 0x800 else "cp437", "strict")
        directory = name.endswith("/")
        canonical_name = safe_name(name, directory)
        need(canonical_name not in names and canonical_name.casefold() not in aliases, "ZIP duplicate/case alias")
        names.add(canonical_name); aliases.add(canonical_name.casefold()); order.append(name)
        kind = stat.S_IFMT(c[15] >> 16)
        need(kind in (0, stat.S_IFDIR if directory else stat.S_IFREG), "ZIP symlink/nonordinary node")
        need(0 <= usize <= 8388608 and usize <= max(1, csize) * 2000, "ZIP entry size/ratio cap")
        total_declared += usize
        need(total_declared <= 268435456, "ZIP declared expansion cap")
        need(0 <= offset <= e[6] - 30, "ZIP local offset bound")
        local = struct.unpack_from("<4s5H3I2H", raw, offset)
        lnlen, lxlen = local[-2:]
        start = offset + 30 + lnlen + lxlen
        finish = start + csize
        need(local[0] == b"PK\x03\x04" and local[1] == c[2] and local[2] == flags and local[3] == method and start <= finish <= e[6], "ZIP local/central disagreement")
        need(lnlen == nlen and lxlen <= 4096 and raw[offset + 30:offset + 30 + lnlen] == encoded, "ZIP local name/extra mismatch")
        central_extra = raw[cursor + 46 + nlen:cursor + 46 + nlen + xlen]
        local_extra = raw[offset + 30 + lnlen:start]
        extra_fields(central_extra); extra_fields(local_extra)
        descriptor_start = finish
        if flags & 8:
            descriptor = finish + (4 if raw[finish:finish + 4] == b"PK\x07\x08" else 0)
            need(descriptor + 12 <= e[6] and struct.unpack_from("<III", raw, descriptor) == (crc, csize, usize), "ZIP data descriptor disagreement")
            finish = descriptor + 12
            need(tuple(local[6:9]) in ((0, 0, 0), (crc, csize, usize)), "ambiguous streaming local size/CRC")
        else:
            need(tuple(local[6:9]) == (crc, csize, usize), "ZIP local CRC/size disagreement")
        metadata_bytes += start - offset + finish - descriptor_start + central_end - cursor
        need(metadata_bytes <= 8388608, "ZIP total metadata cap")
        compressed = raw[start:start + csize]
        payload = payload_identity(compressed, method, usize, crc, budget)
        need(not directory or usize == 0, "ZIP directory payload refused")
        payloads[name] = {"directory": directory, **payload}
        compressed_map[name] = identity(compressed)
        metadata[name] = {"central_fields": list(c[1:]), "local_fields": list(local[1:]),
            "central_extra_hex": central_extra.hex(), "local_extra_hex": local_extra.hex(),
            "entry_comment_hex": raw[central_end - clen:central_end].hex() if clen else "",
            "local_header": identity(raw[offset:start]), "central_header": identity(raw[cursor:central_end]),
            "data_descriptor": identity(raw[descriptor_start:finish])}
        ranges.append((offset, finish)); cursor = central_end
    need(cursor == end, "unindexed central-directory bytes")
    ranges.sort()
    need(ranges[0][0] == 0 and ranges[-1][1] == e[6] and all(a[1] == b[0] for a, b in zip(ranges, ranges[1:])), "ZIP unindexed local bytes/gap/overlap")
    files = {name for name, row in payloads.items() if not row["directory"]}
    for name in names:
        parts = name.split("/")
        need(not any("/".join(parts[:i]) in files for i in range(1, len(parts))), "ZIP file/directory prefix collision")
    global_metadata = {"eocd": identity(raw[end:]), "eocd_fields": list(e[1:]), "archive_comment_hex": raw[end + 22:].hex(), "entry_order": order}
    return {"raw": identity(raw), "entries": len(payloads), "uncompressed_bytes": total_declared,
        "metadata_bytes": metadata_bytes, "payloads": payloads, "metadata": metadata,
        "compressed": compressed_map, "global_metadata": global_metadata}


def changed_rows(official, observed):
    return [{"path": path, "official": official.get(path), "observed": observed.get(path)}
        for path in sorted(set(official) | set(observed)) if official.get(path) != observed.get(path)]


def summary(inspection):
    return {key: inspection[key] for key in ("raw", "entries", "uncompressed_bytes", "metadata_bytes")} | {
        "payload_map_sha256": identity(canonical(inspection["payloads"]))["sha256"],
        "metadata_map_sha256": identity(canonical(inspection["metadata"]))["sha256"],
        "compressed_map_sha256": identity(canonical(inspection["compressed"]))["sha256"]}


def compare_data(official_archive_bytes, observed_raw_by_member, root_supplied_observed_identities):
    need(type(observed_raw_by_member) is dict and set(observed_raw_by_member) == set(EXPECTED), "exact two observed raw members required")
    need(type(root_supplied_observed_identities) is dict and set(root_supplied_observed_identities) == set(EXPECTED), "root must separately bind the exact actual observation identities")
    for member in EXPECTED:
        raw = observed_raw_by_member[member]
        need(type(raw) is bytes and len(raw) <= RAW_CAPS[member], "observed immutable raw byte cap")
        need(identity(raw) == root_supplied_observed_identities[member], "observed raw differs from root-supplied actual identity")
    official, archive_report = official_members(official_archive_bytes)
    budget, results = {"expanded": 0}, {}
    for member in EXPECTED:
        expected = inspect_zip(official[member], RAW_CAPS[member], budget)
        actual = inspect_zip(observed_raw_by_member[member], RAW_CAPS[member], budget)
        payload_changes = changed_rows(expected["payloads"], actual["payloads"])
        compressed_changes = changed_rows(expected["compressed"], actual["compressed"])
        metadata_changes = changed_rows(expected["metadata"], actual["metadata"])
        global_changes = expected["global_metadata"] != actual["global_metadata"]
        same_raw = official[member] == observed_raw_by_member[member]
        if same_raw:
            outcome = "byte-identical"
        elif payload_changes:
            outcome = "uncompressed-entry-payload-or-name-differs"
        elif compressed_changes:
            outcome = "uncompressed-payload-identical-compressed-representation-differs"
        elif metadata_changes or global_changes:
            outcome = "uncompressed-payload-and-compressed-streams-identical-container-metadata-or-layout-differs"
        else:
            raise Refusal("unexplained raw container difference; no normalization or acceptance")
        results[member] = {"outcome": outcome, "official": summary(expected), "observed": summary(actual),
            "payload_changes": payload_changes, "compressed_stream_changes": compressed_changes,
            "metadata_changes": metadata_changes,
            "global_metadata_changes": {"official": expected["global_metadata"], "observed": actual["global_metadata"]} if global_changes else None,
            "all_indexed_bytes_accounted": True, "runtime_admitted": False}
    report = {"schema": 1, "scope": "fixed two archive-data comparisons only", "official_archive": archive_report,
        "zip_actual_uncompressed_bytes_all": budget["expanded"], "results": results,
        "payload_equivalence_basis": "Exact per-entry names/directory-kind/length/CRC32/SHA256; no path/timestamp/payload normalization.",
        "cause_or_provider_provenance_established": False, "runtime_admitted": False,
        "prepared13_or152_pass": False, "old_focused_allowance_reused": False}
    need(len(canonical(report)) <= 67108864, "comparison report exceeds64MiB cap; no truncated success")
    return report
