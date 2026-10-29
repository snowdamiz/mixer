"""UNSELECTED, UNRUN: exact frozen comparator synthetic pure-data checker.
Run only after root explicitly selects one isolated Python -I -B -S invocation.
No archive, observed file, filesystem, process, network, native-loader or timer API
is available after guards. All ZIP/tar/gzip bytes below are synthetic in memory.
"""
import binascii
import builtins
import gzip
import hashlib
import io
import json
import stat
import struct
import sys
import tarfile
import zlib

_EXPECTED_SOURCE_SHA = "156ce9f6ab5d5da580c788c051cbc98229ad641bd150810ef0bb93c92c2ff8c2"
_EXPECTED_SOURCE_BYTES = 16443
_SOURCE = "\"\"\"Unselected pure-data comparator. No filesystem, CLI, process or network API.\nCaller must separately bind stable regular-file bytes under guarded Python -I -B -S.\nNo member is extracted, imported, loaded or executed; no runtime admission follows.\n\"\"\"\nimport binascii\nimport gzip\nimport hashlib\nimport io\nimport json\nimport stat\nimport struct\nimport tarfile\nimport zlib\n\nARCHIVE_SIZE = 193594705\nARCHIVE_SHA = \"8b9b611d917e3dfd8419d3566b5949226f69b052fed7e109c1368add1dfe8711\"\nROOT = \"jdk-17.0.21+9\"\nEXPECTED = {\n    \"lib/ct.sym\": {\"bytes\": 8301486, \"sha256\": \"76b7fa16e006d67f7a65c46f0c4d727ec4ead9d982b8f82538e0e6b255e8fdcf\"},\n    \"lib/jrt-fs.jar\": {\"bytes\": 110513, \"sha256\": \"09bed1c9354a0671807504f255229f0c767a02a612eb3be8675216f58cec84ce\"},\n}\nRAW_CAPS = {\"lib/ct.sym\": 16777216, \"lib/jrt-fs.jar\": 1048576}\nCHUNK = 65536\n\n\nclass Refusal(ValueError):\n    pass\n\n\ndef need(ok, reason):\n    if not ok:\n        raise Refusal(reason)\n\n\ndef identity(data):\n    return {\"bytes\": len(data), \"sha256\": hashlib.sha256(data).hexdigest()}\n\n\ndef canonical(value):\n    return json.dumps(value, sort_keys=True, separators=(\",\", \":\"), ensure_ascii=True, allow_nan=False).encode(\"ascii\")\n\n\ndef safe_name(name, directory=False, maximum=1024, depth=32):\n    need(type(name) is str and name and \"\\\\\" not in name and \":\" not in name, \"unsafe archive name\")\n    canonical_name = name[:-1] if directory and name.endswith(\"/\") else name\n    parts = canonical_name.split(\"/\")\n    need(not canonical_name.startswith(\"/\") and len(name.encode(\"utf-8\")) <= maximum and len(parts) <= depth, \"path bound\")\n    need(all(part not in (\"\", \".\", \"..\") for part in parts), \"empty/dot/traversal name\")\n    need(all(32 <= ord(c) < 127 for c in name), \"non-ASCII/control archive name refused without normalization\")\n    return canonical_name\n\n\ndef official_members(archive_bytes):\n    need(type(archive_bytes) is bytes and len(archive_bytes) == ARCHIVE_SIZE, \"exact official immutable archive size required\")\n    need(identity(archive_bytes)[\"sha256\"] == ARCHIVE_SHA, \"official archive SHA256 mismatch before gzip\")\n    class LimitedReader:\n        def __init__(self, stream):\n            self.stream, self.total = stream, 0\n        def read(self, size):\n            need(type(size) is int and 0 <= size <= CHUNK, \"bounded gzip read required\")\n            result = self.stream.read(min(size, 402653184 - self.total + 1))\n            self.total += len(result)\n            need(self.total <= 402653184, \"gzip expansion cap\")\n            return result\n    selected, seen, declared = {}, set(), 0\n    with gzip.GzipFile(fileobj=io.BytesIO(archive_bytes), mode=\"rb\") as gz:\n        limited = LimitedReader(gz)\n        with tarfile.open(fileobj=limited, mode=\"r|\", bufsize=10240) as archive:\n            for member in archive:\n                name = safe_name(member.name, member.isdir(), maximum=4096, depth=64)\n                need(name == ROOT or name.startswith(ROOT + \"/\"), \"unexpected official tar root\")\n                need(name not in seen and len(seen) < 1024, \"duplicate tar name or count cap\")\n                seen.add(name)\n                need(0 <= member.size <= 268435456, \"tar member size cap\")\n                declared += member.size\n                need(declared <= 402653184, \"tar declared expansion cap\")\n                relative = name[len(ROOT) + 1:] if name != ROOT else \"\"\n                if relative not in EXPECTED:\n                    continue\n                need(relative not in selected and member.type in (tarfile.REGTYPE, tarfile.AREGTYPE) and not member.issym() and not member.islnk() and not member.sparse, \"selected tar member must be a unique ordinary file\")\n                need(member.size == EXPECTED[relative][\"bytes\"], \"selected official member declared size mismatch\")\n                stream = archive.extractfile(member)\n                need(stream is not None, \"selected tar data absent\")\n                chunks, size = [], 0\n                with stream:\n                    while True:\n                        chunk = stream.read(min(CHUNK, member.size - size + 1))\n                        if not chunk:\n                            break\n                        size += len(chunk)\n                        need(size <= member.size, \"selected tar data exceeds exact size\")\n                        chunks.append(chunk)\n                data = b\"\".join(chunks)\n                need(identity(data) == EXPECTED[relative], \"selected official member exact identity mismatch\")\n                selected[relative] = data\n        # Drain through gzip EOF so CRC/ISIZE and all delivered padding are checked.\n        while limited.read(CHUNK):\n            pass\n    need(set(selected) == set(EXPECTED), \"the exact two official members are required\")\n    need(len(seen) == 543 and limited.total == 332994560, \"official tar counts differ from frozen data receipt\")\n    return selected, {\"archive\": {\"bytes\": ARCHIVE_SIZE, \"sha256\": ARCHIVE_SHA}, \"tar_members\": len(seen), \"gzip_delivered_bytes\": limited.total, \"selected\": EXPECTED}\n\n\ndef extra_fields(data):\n    need(len(data) <= 4096, \"ZIP extra-field cap\")\n    at, seen = 0, set()\n    while at < len(data):\n        need(at + 4 <= len(data), \"truncated ZIP extra field\")\n        tag, size = struct.unpack_from(\"<HH\", data, at)\n        at += 4\n        need(at + size <= len(data) and tag not in seen, \"truncated/duplicate ZIP extra field\")\n        need(tag not in (1, 0x9901), \"ZIP64/AES extra field refused\")\n        seen.add(tag)\n        at += size\n\n\ndef payload_identity(compressed, method, declared, crc_expected, budget):\n    need(0 <= declared <= 8388608, \"ZIP per-entry expansion cap\")\n    digest, crc, total = hashlib.sha256(), 0, 0\n    def accept(block):\n        nonlocal crc, total\n        total += len(block)\n        budget[\"expanded\"] += len(block)\n        need(total <= declared and budget[\"expanded\"] <= 536870912, \"ZIP actual expansion cap\")\n        digest.update(block)\n        crc = binascii.crc32(block, crc)\n    if method == 0:\n        need(len(compressed) == declared, \"stored ZIP size mismatch\")\n        for at in range(0, len(compressed), CHUNK):\n            accept(compressed[at:at + CHUNK])\n    else:\n        need(method == 8, \"unsupported ZIP compression\")\n        decoder, at = zlib.decompressobj(-15), 0\n        while at < len(compressed):\n            piece = compressed[at:at + CHUNK]\n            at += len(piece)\n            while piece:\n                before = len(piece)\n                block = decoder.decompress(piece, min(CHUNK, declared - total + 1, 536870912 - budget[\"expanded\"] + 1))\n                accept(block)\n                piece = decoder.unconsumed_tail\n                need(not decoder.unused_data, \"trailing bytes after raw DEFLATE stream\")\n                need(not piece or len(piece) < before or bool(block), \"DEFLATE made no progress\")\n                if decoder.eof:\n                    need(not piece and at == len(compressed), \"unconsumed or trailing compressed bytes\")\n                    break\n        need(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, \"incomplete or ambiguous raw DEFLATE stream\")\n    need(total == declared and (crc & 0xffffffff) == crc_expected, \"ZIP payload length/CRC mismatch\")\n    return {\"bytes\": total, \"sha256\": digest.hexdigest(), \"crc32\": crc & 0xffffffff}\n\n\ndef inspect_zip(raw, cap, budget):\n    need(type(raw) is bytes and 22 <= len(raw) <= cap and raw[:4] == b\"PK\\x03\\x04\", \"ordinary bounded ZIP envelope required\")\n    end = raw.rfind(b\"PK\\x05\\x06\", max(0, len(raw) - 65557))\n    need(end >= 0 and end + 22 <= len(raw), \"ZIP EOCD missing\")\n    e = struct.unpack_from(\"<4s4H2IH\", raw, end)\n    need(e[1] == e[2] == 0 and e[3] == e[4] and 1 <= e[4] <= 65534 and e[5] + e[6] == end and end + 22 + e[7] == len(raw), \"ZIP disk/ZIP64/central/trailing ambiguity\")\n    payloads, metadata, compressed_map, aliases, names, ranges, order = {}, {}, {}, set(), set(), [], []\n    cursor, total_declared, metadata_bytes = e[6], 0, len(raw) - end\n    for ordinal in range(e[4]):\n        need(cursor + 46 <= end, \"truncated central header\")\n        c = struct.unpack_from(\"<4s6H3I5H2I\", raw, cursor)\n        need(c[0] == b\"PK\\x01\\x02\" and c[13] == 0, \"central header/disk mismatch\")\n        flags, method, crc, csize, usize = c[3], c[4], c[7], c[8], c[9]\n        nlen, xlen, clen, offset = c[10], c[11], c[12], c[16]\n        need(c[2] <= 20 and not flags & ~(0x800 | 8 | 6) and method in (0, 8), \"ZIP encryption/flags/compression/version refused\")\n        need(csize != 0xffffffff and usize != 0xffffffff and offset != 0xffffffff, \"ZIP64 entry refused\")\n        need(nlen <= 1024 and xlen <= 4096 and clen <= 4096 and cursor + 46 + nlen + xlen + clen <= end, \"central variable-field bound\")\n        central_end = cursor + 46 + nlen + xlen + clen\n        encoded = raw[cursor + 46:cursor + 46 + nlen]\n        name = encoded.decode(\"utf-8\" if flags & 0x800 else \"cp437\", \"strict\")\n        directory = name.endswith(\"/\")\n        canonical_name = safe_name(name, directory)\n        need(canonical_name not in names and canonical_name.casefold() not in aliases, \"ZIP duplicate/case alias\")\n        names.add(canonical_name); aliases.add(canonical_name.casefold()); order.append(name)\n        kind = stat.S_IFMT(c[15] >> 16)\n        need(kind in (0, stat.S_IFDIR if directory else stat.S_IFREG), \"ZIP symlink/nonordinary node\")\n        need(0 <= usize <= 8388608 and usize <= max(1, csize) * 2000, \"ZIP entry size/ratio cap\")\n        total_declared += usize\n        need(total_declared <= 268435456, \"ZIP declared expansion cap\")\n        need(0 <= offset <= e[6] - 30, \"ZIP local offset bound\")\n        local = struct.unpack_from(\"<4s5H3I2H\", raw, offset)\n        lnlen, lxlen = local[-2:]\n        start = offset + 30 + lnlen + lxlen\n        finish = start + csize\n        need(local[0] == b\"PK\\x03\\x04\" and local[1] == c[2] and local[2] == flags and local[3] == method and start <= finish <= e[6], \"ZIP local/central disagreement\")\n        need(lnlen == nlen and lxlen <= 4096 and raw[offset + 30:offset + 30 + lnlen] == encoded, \"ZIP local name/extra mismatch\")\n        central_extra = raw[cursor + 46 + nlen:cursor + 46 + nlen + xlen]\n        local_extra = raw[offset + 30 + lnlen:start]\n        extra_fields(central_extra); extra_fields(local_extra)\n        descriptor_start = finish\n        if flags & 8:\n            descriptor = finish + (4 if raw[finish:finish + 4] == b\"PK\\x07\\x08\" else 0)\n            need(descriptor + 12 <= e[6] and struct.unpack_from(\"<III\", raw, descriptor) == (crc, csize, usize), \"ZIP data descriptor disagreement\")\n            finish = descriptor + 12\n            need(tuple(local[6:9]) in ((0, 0, 0), (crc, csize, usize)), \"ambiguous streaming local size/CRC\")\n        else:\n            need(tuple(local[6:9]) == (crc, csize, usize), \"ZIP local CRC/size disagreement\")\n        metadata_bytes += start - offset + finish - descriptor_start + central_end - cursor\n        need(metadata_bytes <= 8388608, \"ZIP total metadata cap\")\n        compressed = raw[start:start + csize]\n        payload = payload_identity(compressed, method, usize, crc, budget)\n        need(not directory or usize == 0, \"ZIP directory payload refused\")\n        payloads[name] = {\"directory\": directory, **payload}\n        compressed_map[name] = identity(compressed)\n        metadata[name] = {\"central_fields\": list(c[1:]), \"local_fields\": list(local[1:]),\n            \"central_extra_hex\": central_extra.hex(), \"local_extra_hex\": local_extra.hex(),\n            \"entry_comment_hex\": raw[central_end - clen:central_end].hex() if clen else \"\",\n            \"local_header\": identity(raw[offset:start]), \"central_header\": identity(raw[cursor:central_end]),\n            \"data_descriptor\": identity(raw[descriptor_start:finish])}\n        ranges.append((offset, finish)); cursor = central_end\n    need(cursor == end, \"unindexed central-directory bytes\")\n    ranges.sort()\n    need(ranges[0][0] == 0 and ranges[-1][1] == e[6] and all(a[1] == b[0] for a, b in zip(ranges, ranges[1:])), \"ZIP unindexed local bytes/gap/overlap\")\n    files = {name for name, row in payloads.items() if not row[\"directory\"]}\n    for name in names:\n        parts = name.split(\"/\")\n        need(not any(\"/\".join(parts[:i]) in files for i in range(1, len(parts))), \"ZIP file/directory prefix collision\")\n    global_metadata = {\"eocd\": identity(raw[end:]), \"eocd_fields\": list(e[1:]), \"archive_comment_hex\": raw[end + 22:].hex(), \"entry_order\": order}\n    return {\"raw\": identity(raw), \"entries\": len(payloads), \"uncompressed_bytes\": total_declared,\n        \"metadata_bytes\": metadata_bytes, \"payloads\": payloads, \"metadata\": metadata,\n        \"compressed\": compressed_map, \"global_metadata\": global_metadata}\n\n\ndef changed_rows(official, observed):\n    return [{\"path\": path, \"official\": official.get(path), \"observed\": observed.get(path)}\n        for path in sorted(set(official) | set(observed)) if official.get(path) != observed.get(path)]\n\n\ndef summary(inspection):\n    return {key: inspection[key] for key in (\"raw\", \"entries\", \"uncompressed_bytes\", \"metadata_bytes\")} | {\n        \"payload_map_sha256\": identity(canonical(inspection[\"payloads\"]))[\"sha256\"],\n        \"metadata_map_sha256\": identity(canonical(inspection[\"metadata\"]))[\"sha256\"],\n        \"compressed_map_sha256\": identity(canonical(inspection[\"compressed\"]))[\"sha256\"]}\n\n\ndef compare_data(official_archive_bytes, observed_raw_by_member, root_supplied_observed_identities):\n    need(type(observed_raw_by_member) is dict and set(observed_raw_by_member) == set(EXPECTED), \"exact two observed raw members required\")\n    need(type(root_supplied_observed_identities) is dict and set(root_supplied_observed_identities) == set(EXPECTED), \"root must separately bind the exact actual observation identities\")\n    for member in EXPECTED:\n        raw = observed_raw_by_member[member]\n        need(type(raw) is bytes and len(raw) <= RAW_CAPS[member], \"observed immutable raw byte cap\")\n        need(identity(raw) == root_supplied_observed_identities[member], \"observed raw differs from root-supplied actual identity\")\n    official, archive_report = official_members(official_archive_bytes)\n    budget, results = {\"expanded\": 0}, {}\n    for member in EXPECTED:\n        expected = inspect_zip(official[member], RAW_CAPS[member], budget)\n        actual = inspect_zip(observed_raw_by_member[member], RAW_CAPS[member], budget)\n        payload_changes = changed_rows(expected[\"payloads\"], actual[\"payloads\"])\n        compressed_changes = changed_rows(expected[\"compressed\"], actual[\"compressed\"])\n        metadata_changes = changed_rows(expected[\"metadata\"], actual[\"metadata\"])\n        global_changes = expected[\"global_metadata\"] != actual[\"global_metadata\"]\n        same_raw = official[member] == observed_raw_by_member[member]\n        if same_raw:\n            outcome = \"byte-identical\"\n        elif payload_changes:\n            outcome = \"uncompressed-entry-payload-or-name-differs\"\n        elif compressed_changes:\n            outcome = \"uncompressed-payload-identical-compressed-representation-differs\"\n        elif metadata_changes or global_changes:\n            outcome = \"uncompressed-payload-and-compressed-streams-identical-container-metadata-or-layout-differs\"\n        else:\n            raise Refusal(\"unexplained raw container difference; no normalization or acceptance\")\n        results[member] = {\"outcome\": outcome, \"official\": summary(expected), \"observed\": summary(actual),\n            \"payload_changes\": payload_changes, \"compressed_stream_changes\": compressed_changes,\n            \"metadata_changes\": metadata_changes,\n            \"global_metadata_changes\": {\"official\": expected[\"global_metadata\"], \"observed\": actual[\"global_metadata\"]} if global_changes else None,\n            \"all_indexed_bytes_accounted\": True, \"runtime_admitted\": False}\n    report = {\"schema\": 1, \"scope\": \"fixed two archive-data comparisons only\", \"official_archive\": archive_report,\n        \"zip_actual_uncompressed_bytes_all\": budget[\"expanded\"], \"results\": results,\n        \"payload_equivalence_basis\": \"Exact per-entry names/directory-kind/length/CRC32/SHA256; no path/timestamp/payload normalization.\",\n        \"cause_or_provider_provenance_established\": False, \"runtime_admitted\": False,\n        \"prepared13_or152_pass\": False, \"old_focused_allowance_reused\": False}\n    need(len(canonical(report)) <= 67108864, \"comparison report exceeds64MiB cap; no truncated success\")\n    return report\n".encode("utf-8")
if len(_SOURCE) != _EXPECTED_SOURCE_BYTES or hashlib.sha256(_SOURCE).hexdigest() != _EXPECTED_SOURCE_SHA:
    raise SystemExit("embedded frozen source identity mismatch")
if not (sys.flags.isolated and sys.flags.dont_write_bytecode and sys.flags.no_site):
    raise SystemExit("requires Python -I -B -S")

class GuardDenial(PermissionError):
    pass

def _deny(*args, **kwargs):
    raise GuardDenial("synthetic checker forbids filesystem/process/network/native-loader/timer operations")

# All subject imports are already loaded above. No deferred subject import is admitted.
_ALLOWED_IMPORTS = frozenset(("binascii", "gzip", "hashlib", "io", "json", "stat", "struct", "tarfile", "zlib"))
_original_import, _original_exec, _original_compile = builtins.__import__, builtins.exec, builtins.compile

def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name not in _ALLOWED_IMPORTS:
        raise GuardDenial("import refused: " + str(name))
    return _original_import(name, globals, locals, fromlist, level)

def _audit(event, args):
    if event == "open" or event.startswith(("os.", "subprocess.", "socket.", "ctypes.", "signal.", "resource.", "mmap.", "winreg.", "_winapi.", "pty.")):
        raise GuardDenial("audit refused: " + event)
    if event == "import" and args[0] not in _ALLOWED_IMPORTS:
        raise GuardDenial("deferred import refused")

# Deny known no-audit process queries, waits, signals and clocks if their modules
# were loaded transitively. This inspects module dictionaries, never host state.
_os_names = ("open", "fdopen", "listdir", "scandir", "stat", "lstat", "fstat", "readlink", "read", "write", "close", "chdir", "fchdir", "getcwd", "getcwdb", "mkdir", "makedirs", "unlink", "remove", "rmdir", "removedirs", "rename", "renames", "replace", "link", "symlink", "chmod", "fchmod", "chown", "fchown", "lchown", "utime", "truncate", "ftruncate", "system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp", "execlpe", "getpid", "getppid", "getpgid", "getpgrp", "getsid", "setsid", "setpgid", "kill", "killpg", "wait", "waitpid", "waitid", "wait3", "wait4", "pidfd_open", "times", "getloadavg", "sched_getaffinity", "sched_setaffinity", "sched_getscheduler", "sched_setscheduler", "sched_yield", "getpriority", "setpriority", "urandom")
for _modname in ("os", "posix", "nt"):
    _mod = sys.modules.get(_modname)
    if _mod is not None:
        for _name in _os_names:
            if hasattr(_mod, _name):
                setattr(_mod, _name, _deny)
for _modname, _names in {
    "time": ("sleep", "time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns", "process_time", "process_time_ns", "thread_time", "thread_time_ns", "clock_gettime", "clock_gettime_ns", "clock_getres", "clock_settime", "clock_settime_ns"),
    "signal": ("signal", "getsignal", "alarm", "pause", "setitimer", "getitimer", "pthread_kill", "pthread_sigmask", "sigpending", "sigwait", "sigwaitinfo", "sigtimedwait", "raise_signal"),
    "socket": ("socket", "socketpair", "create_connection", "create_server", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostname", "getfqdn"),
    "_socket": ("socket", "socketpair", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostname"),
    "ctypes": ("CDLL", "PyDLL", "WinDLL", "OleDLL", "CFUNCTYPE", "PYFUNCTYPE", "WINFUNCTYPE", "cast", "memmove", "memset", "string_at", "wstring_at"),
    "_ctypes": ("dlopen", "LoadLibrary", "call_function", "call_cdeclfunction", "dlsym"),
    "threading": ("Thread", "Timer"),
    "_thread": ("start_new_thread", "start_new", "allocate_lock", "allocate", "get_ident", "get_native_id"),
    "subprocess": ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"),
}.items():
    _mod = sys.modules.get(_modname)
    if _mod is not None:
        for _name in _names:
            if hasattr(_mod, _name):
                setattr(_mod, _name, _deny)
sys.addaudithook(_audit)
builtins.__import__, builtins.open, io.open = _guarded_import, _deny, _deny
builtins.input, builtins.breakpoint = _deny, _deny

# Source evaluation occurs only after all denials, with exact immutable bytes.
_subject = {"__name__": "frozen_comparator_synthetic_subject", "__builtins__": builtins.__dict__}
_original_exec(_original_compile(_SOURCE, "<frozen-compare-data>", "exec"), _subject)
Refusal = _subject["Refusal"]
_checks = []

def _check(label, ok):
    if not ok:
        raise AssertionError(label)
    _checks.append({"name": label, "pass": True})

def _refuses(label, call, reason=None, errors=None):
    errors = (Refusal,) if errors is None else errors
    try:
        call()
    except errors as error:
        _check(label, reason is None or reason in str(error))
    else:
        raise AssertionError(label + ": accepted")

def _deflate(data, level=6):
    codec = zlib.compressobj(level, zlib.DEFLATED, -15)
    return codec.compress(data) + codec.flush()

def _zip(rows, comment=b""):
    local_parts, central_parts, offset = [], [], 0
    for row in rows:
        name, data = row["name"], row.get("data", b"payload")
        method, flags = row.get("method", 8), row.get("flags", 0)
        compressed = row.get("compressed", data if method == 0 else _deflate(data, row.get("level", 6)))
        crc, usize, csize = row.get("crc", binascii.crc32(data) & 0xffffffff), row.get("usize", len(data)), len(compressed)
        version, stamp, date = row.get("version", 20), row.get("stamp", 0), row.get("date", 0)
        extra, lextra, entry_comment = row.get("extra", b""), row.get("lextra", b""), row.get("comment", b"")
        lname = row.get("lname", name)
        lcrc, lcsize, lusize = row.get("local_sizes", (0, 0, 0) if flags & 8 else (crc, csize, usize))
        local = struct.pack("<4s5H3I2H", b"PK\x03\x04", version, flags, method, stamp, date, lcrc, lcsize, lusize, len(lname), len(lextra)) + lname + lextra + compressed
        if flags & 8:
            local += row.get("descriptor", b"PK\x07\x08" + struct.pack("<III", crc, csize, usize))
        external = row.get("external", (stat.S_IFDIR if name.endswith(b"/") else stat.S_IFREG) << 16)
        central = struct.pack("<4s6H3I5H2I", b"PK\x01\x02", 3 << 8 | 20, version, flags, method, stamp, date, crc, csize, usize, len(name), len(extra), len(entry_comment), 0, 0, external, row.get("offset", offset)) + name + extra + entry_comment
        local_parts.append(local); central_parts.append(central); offset += len(local)
    local, central = b"".join(local_parts), b"".join(central_parts)
    return local + central + struct.pack("<4s4H2IH", b"PK\x05\x06", 0, 0, len(rows), len(rows), len(central), len(local), len(comment)) + comment

def _inspect(raw):
    return _subject["inspect_zip"](raw, 1048576, {"expanded": 0})

def _tar(rows):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for row in rows:
            entry = tarfile.TarInfo(row["name"])
            entry.type = row.get("type", tarfile.REGTYPE)
            entry.linkname = row.get("linkname", "")
            entry.mode, entry.uid, entry.gid, entry.mtime = 0o644, 0, 0, 0
            data = row.get("data", b"")
            entry.size = len(data) if entry.type == tarfile.REGTYPE else 0
            archive.addfile(entry, io.BytesIO(data) if entry.type == tarfile.REGTYPE else None)
    return gzip.compress(output.getvalue(), mtime=0)

def _tar_call(raw, expected, reason):
    originals = {k: _subject[k] for k in ("ARCHIVE_SIZE", "ARCHIVE_SHA", "ROOT", "EXPECTED")}
    try:
        _subject.update(ARCHIVE_SIZE=len(raw), ARCHIVE_SHA=hashlib.sha256(raw).hexdigest(), ROOT="synthetic", EXPECTED=expected)
        _refuses("synthetic tar: " + reason, lambda: _subject["official_members"](raw), reason, (Refusal, gzip.BadGzipFile, EOFError, tarfile.TarError))
    finally:
        _subject.update(originals)

def _run():
    for name in ("os", "subprocess", "socket", "ctypes", "signal", "time", "resource", "pathlib"):
        _refuses("guard import: " + name, lambda name=name: builtins.__import__(name), errors=(GuardDenial,))
    _refuses("guard filesystem open", lambda: builtins.open("/synthetic-forbidden"), errors=(GuardDenial,))
    _check("subject embedded source exact identity", len(_SOURCE) == 16443 and hashlib.sha256(_SOURCE).hexdigest() == _EXPECTED_SOURCE_SHA)
    base = _zip([{"name": b"safe/A.class", "data": b"alpha"}])
    parsed = _inspect(base)
    _check("DEFLATE payload length/SHA/CRC", parsed["payloads"]["safe/A.class"]["sha256"] == hashlib.sha256(b"alpha").hexdigest() and parsed["uncompressed_bytes"] == 5)
    _check("STORED payload accepted", _inspect(_zip([{"name": b"a", "data": b"abc", "method": 0}]))["payloads"]["a"]["bytes"] == 3)
    _check("empty directory accepted", _inspect(_zip([{"name": b"d/", "data": b"", "method": 0}]))["payloads"]["d/"]["directory"])
    _check("signed streaming descriptor accepted", _inspect(_zip([{"name": b"a", "data": b"abc", "flags": 8}]))["entries"] == 1)
    _check("unsigned streaming descriptor accepted", _inspect(_zip([{"name": b"a", "data": b"abc", "flags": 8, "descriptor": struct.pack("<III", binascii.crc32(b"abc") & 0xffffffff, len(_deflate(b"abc")), 3)}]))["entries"] == 1)
    for name in (b"/escape", b"a/../b", b"a//b", b"a/./b", b"a\\b", b"x:y", b"a\x00b", b"x\x80y", b"a/" * 33 + b"x"):
        _refuses("unsafe ZIP name " + repr(name), lambda name=name: _inspect(_zip([{"name": name}])))
    for rows, reason in (([{"name": b"a"}, {"name": b"a"}], "duplicate"), ([{"name": b"A"}, {"name": b"a"}], "case alias"), ([{"name": b"a"}, {"name": b"a/", "data": b""}], "duplicate"), ([{"name": b"a"}, {"name": b"a/b"}], "prefix collision")):
        _refuses("ZIP topology " + reason, lambda rows=rows: _inspect(_zip(rows)), reason)
    boundary = _inspect(_zip([{"name": b"A"}, {"name": b"a/b"}]))
    _check("casefold ancestor boundary preserves exact names without extraction", boundary["entries"] == 2 and set(boundary["payloads"]) == {"A", "a/b"})
    for row, reason in (({"name": b"a", "flags": 1}, "flags"), ({"name": b"a", "method": 99}, "compression"), ({"name": b"a", "version": 45}, "version"), ({"name": b"a", "external": stat.S_IFLNK << 16}, "nonordinary"), ({"name": b"a", "extra": struct.pack("<HH", 1, 0)}, "ZIP64"), ({"name": b"a", "lextra": struct.pack("<HH", 0x9901, 0)}, "AES"), ({"name": b"a", "extra": b"x"}, "truncated"), ({"name": b"a", "extra": struct.pack("<HHHH", 7, 0, 7, 0)}, "duplicate"), ({"name": b"a", "lname": b"b"}, "local name"), ({"name": b"a", "local_sizes": (1, 1, 1)}, "CRC/size"), ({"name": b"a", "flags": 8, "descriptor": b"\x00" * 12}, "descriptor"), ({"name": b"a", "data": b"abc", "crc": 0}, "length/CRC"), ({"name": b"a", "data": b"abc", "usize": 2}, "expansion"), ({"name": b"a", "data": b"abc", "compressed": _deflate(b"abc") + b"x"}, "trailing"), ({"name": b"a", "data": b"abc", "compressed": _deflate(b"abc")[:-1]}, "incomplete"), ({"name": b"d/", "data": b"x"}, "directory payload"), ({"name": b"a", "usize": 8388609}, "size/ratio"), ({"name": b"a", "offset": 1}, "local/central")):
        _refuses("ZIP refusal " + reason, lambda row=row: _inspect(_zip([row])), reason)
    _refuses("ZIP raw trailing byte", lambda: _inspect(base + b"x"), "trailing")
    _refuses("ZIP truncated EOCD", lambda: _inspect(base[:-1]))
    _refuses("ZIP leading unindexed byte", lambda: _inspect(b"x" + base), "envelope")
    _refuses("immutable bytes required", lambda: _inspect(bytearray(base)), "envelope")
    _refuses("actual global expansion budget", lambda: _subject["inspect_zip"](base, 1048576, {"expanded": 536870912}), "actual expansion")
    _refuses("fixed official archive rejects synthetic size", lambda: _subject["official_members"](b"synthetic"), "size")
    tiny_expected = {"lib/ct.sym": _subject["identity"](base), "lib/jrt-fs.jar": _subject["identity"](base)}
    rows = [{"name": "synthetic/" + member, "data": base} for member in tiny_expected]
    _tar_call(_tar(rows), tiny_expected, "official tar counts differ")
    _tar_call(_tar(rows[:1]), tiny_expected, "exact two official members")
    _tar_call(_tar(rows + rows[:1]), tiny_expected, "duplicate tar")
    _tar_call(_tar([{**rows[0], "name": "other/lib/ct.sym"}, rows[1]]), tiny_expected, "unexpected official tar root")
    _tar_call(_tar([{**rows[0], "name": "synthetic/../lib/ct.sym"}, rows[1]]), tiny_expected, "traversal")
    _tar_call(_tar([{**rows[0], "type": tarfile.SYMTYPE, "linkname": "irrelevant"}, rows[1]]), tiny_expected, "ordinary file")
    _tar_call(_tar([{**rows[0], "data": b"wrong"}, rows[1]]), tiny_expected, "declared size")
    damaged = bytearray(_tar(rows)); damaged[-8] ^= 1
    _tar_call(bytes(damaged), tiny_expected, "CRC check failed")
    observed = {member: base for member in tiny_expected}
    bindings = {member: _subject["identity"](base) for member in tiny_expected}
    _refuses("exact observed keys", lambda: _subject["compare_data"](b"synthetic", {}, bindings), "exact two")
    _refuses("root binding mandatory", lambda: _subject["compare_data"](b"synthetic", observed, {}), "root must")
    _refuses("root identity mismatch", lambda: _subject["compare_data"](b"synthetic", observed, {member: {"bytes": 0, "sha256": "0" * 64} for member in tiny_expected}), "root-supplied")
    # Classification branch controls replace only the official-member acquisition
    # function with an explicit synthetic-byte provider. This does not exercise or
    # waive the fixed official archive identity, member identities or tar counters.
    original = _subject["official_members"]
    try:
        _subject["official_members"] = lambda unused: (observed, {"synthetic_only": True})
        cases = (
            (base, "byte-identical"),
            (_zip([{"name": b"safe/A.class", "data": b"beta"}]), "uncompressed-entry-payload-or-name-differs"),
            (_zip([{"name": b"safe/A.class", "data": b"alpha", "method": 0}]), "uncompressed-payload-identical-compressed-representation-differs"),
            (_zip([{"name": b"safe/A.class", "data": b"alpha", "stamp": 2}]), "uncompressed-payload-and-compressed-streams-identical-container-metadata-or-layout-differs"),
            (_zip([{"name": b"safe/A.class", "data": b"alpha"}], comment=b"comment"), "uncompressed-payload-and-compressed-streams-identical-container-metadata-or-layout-differs"),
        )
        for raw, outcome in cases:
            actual = {member: raw for member in tiny_expected}
            actual_bindings = {member: _subject["identity"](raw) for member in tiny_expected}
            report = _subject["compare_data"](b"synthetic", actual, actual_bindings)
            _check("classification " + outcome, all(row["outcome"] == outcome for row in report["results"].values()))
            _check("classification keeps runtime denied " + outcome, report["runtime_admitted"] is False and report["prepared13_or152_pass"] is False and report["cause_or_provider_provenance_established"] is False)
    finally:
        _subject["official_members"] = original
    return {"schema": 1, "status": "synthetic-pure-function-controls-passed", "source_bytes": _EXPECTED_SOURCE_BYTES, "source_sha256": _EXPECTED_SOURCE_SHA, "checks": _checks, "passed": len(_checks), "failed": 0, "real_archive_or_observation_read": False, "actual_comparison_executed": False, "official_success_path_exercised": False, "tar_constants_rebound_for_synthetic_refusal_controls": True, "classification_official_acquisition_stubbed": True, "runtime_admitted": False}

try:
    _result = _run()
except Exception as _error:
    print(json.dumps({"schema": 1, "status": "synthetic-control-failed", "error_type": type(_error).__name__, "error": str(_error), "completed_checks": len(_checks), "runtime_admitted": False}, sort_keys=True))
    raise SystemExit(1)
print(json.dumps(_result, sort_keys=True, separators=(",", ":")))
