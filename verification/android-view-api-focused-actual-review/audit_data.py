"""Independent bounded data audit. No subject imports, processes or network.

Run under Python -I -B -S. Actual archive review additionally requires the
root-supplied exact delivered/run/job/artifact binding; preparation is not a pass.
"""
import sys
sys.dont_write_bytecode = True
import binascii
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import unicodedata
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SELECTION = "verification/android-view-api-focused-host-selection-2026-10-29"
HOST = "verification/android-view-api-boundary-host-custody-correction"
CANDIDATE = "verification/android-view-api-boundary-candidate"
INSPECTOR = "verification/android-view-api-boundary-bytecode-inspection"
PINS = {
    SELECTION + "/selection.json": "84c2f8562d4a50fe5ed6a910265993e80fc16055c9dc0ff26af368b2a0e9f144",
    SELECTION + "/root-review.json": "d89c69c8e58872f1033f89f4a1677ea0461dd5e841f28a70db0d8c32aac642d4",
    HOST + "/seal.json": "3e3444a4f182ca2ba85a7d8db994917e112d6639985a4a86dceaa1bb39f2ed3c",
    HOST + "/collect.py": "388e7bd459e333ce325a8efed0c2221407f193e4d4829c5516ad47aceb8a1dc8",
    HOST + "/custody.py": "395fecbf7c594c2faf9592387bfeaa53b8124c7fa3e3a5094a9b54d1e65a936d",
    HOST + "/input-manifest.json": "1d15392b79211ada71f4173e1c11cf12321267ddd452c329b9a4af99fadf2f00",
    HOST + "/tool-profile.json": "1bb7db9e598eaa4229997e5a1d50da60809a611196209e49ce40aa67d2972f48",
    CANDIDATE + "/freeze.json": "c458497920a6cf454433f2f96bbcdf42fbf8b6945e55e5a76c813dddb00af8ff",
    CANDIDATE + "/manifest.json": "e52dd5bd9c415a68c843724a24fec03c72c64dbce7fae2d18377c646a4b35834",
    INSPECTOR + "/inspect_artifacts.py": "7e15cfa979f19a72443436dc3f64bba2a6b88c2ed652e8956e96dd454380d83b",
    INSPECTOR + "/seal.json": "26b405d4e8a92120283e8e77084bde55beb2b1f37b2297d975f9b353fe472d35",
    "verification/android-view-api-git-custody-review/review-seal.json": "1c67d7aef5cc9602b6127b4fad4471eab2d2e8081b3214c0689e55646a75ed0a",
    ".github/workflows/android-view-api-focused-admission.yml": "3cfc71add11b490d1f492182de571dea3617b37b8a889cabd14be486b4ec774a",
}
NONCE = "01ff94d91b2bf33285cb01364d69c793d35c1932485d6e0e0a4502f790090e56"
TREE = "d767f19554c88bd24f58663de268d7a80119522380cfeb4043c37d35b432a21e"
COMMANDS = ["java-version", "javac-version", "d8-version", "host-compile", "focused-main", "sdk37-compile", "d8-min28"]
LIMITS = {"archive_bytes": 192 * 1024 * 1024, "members": 4096,
          "member_bytes": 64 * 1024 * 1024, "total_bytes": 256 * 1024 * 1024,
          "compression_ratio": 2000, "path_bytes": 512, "path_depth": 16}


class Refusal(ValueError):
    pass


def need(value, reason):
    if not value:
        raise Refusal(reason)


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def strict_json(data, maximum=8 * 1024 * 1024):
    need(type(data) is bytes and len(data) <= maximum, "JSON type/byte bound")
    def pairs(rows):
        out = {}
        for key, value in rows:
            need(key not in out, "duplicate JSON key: " + key[:120])
            out[key] = value
        return out
    def constant(value):
        raise Refusal("nonfinite JSON constant: " + value)
    try:
        text = data.decode("utf-8", "strict")
        need(not text.startswith("\ufeff"), "JSON BOM refused")
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise Refusal("strict JSON decode: " + type(error).__name__) from error
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        need(nodes <= 200000 and depth <= 64, "JSON node/depth bound")
        if isinstance(item, dict):
            pending.extend((k, depth + 1) for k in item)
            pending.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
        elif isinstance(item, str):
            need(not any(0xd800 <= ord(c) <= 0xdfff for c in item), "JSON lone surrogate refused")
        elif type(item) is float:
            need(math.isfinite(item), "nonfinite JSON number")
    return value


def safe_name(name, directory=False):
    need(type(name) is str and name and "\\" not in name and ":" not in name,
         "noncanonical archive/source path")
    if directory and name.endswith("/"):
        name = name[:-1]
    parts = name.split("/")
    need(all(part not in ("", ".", "..") for part in parts), "empty/dot/escaping path")
    need(not name.startswith("/") and len(name.encode()) <= LIMITS["path_bytes"]
         and len(parts) <= LIMITS["path_depth"], "path byte/depth bound")
    need(all(ord(c) >= 32 and ord(c) != 127 for c in name), "control path character")
    need(unicodedata.normalize("NFC", name) == name, "noncanonical Unicode path")
    return name


def read_regular(path, root=None, maximum=64 * 1024 * 1024):
    path = Path(path).absolute()
    boundary = Path(root).absolute() if root is not None else Path(path.anchor)
    need(path.is_relative_to(boundary), "file escapes selected root")
    for p in (path, *path.parents):
        mode = p.lstat().st_mode
        need(not stat.S_ISLNK(mode), "symlink refused: " + str(p))
        if p == boundary:
            break
    before = path.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "ordinary bounded file required")
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    after = path.stat()
    need(len(data) <= maximum and len(data) == before.st_size
         and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
         == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "file changed during read")
    return data


def verify_rows(root, rows):
    need(type(rows) is list and 1 <= len(rows) <= 512, "row count bound")
    out = []
    seen = set()
    for row in rows:
        name = safe_name(row["path"])
        need(name not in seen, "duplicate source row")
        seen.add(name)
        data = read_regular(Path(root) / name, root)
        need(identity(data) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "source row mismatch: " + name)
        out.append({"path": name, **identity(data)})
    return out


def source_audit(root=ROOT):
    root = Path(root)
    pinned = []
    for name, sha in PINS.items():
        data = read_regular(root / name, root)
        need(identity(data)["sha256"] == sha, "frozen pin mismatch: " + name)
        pinned.append({"path": name, **identity(data)})
    selection = strict_json(read_regular(root / SELECTION / "selection.json", root))
    selected = verify_rows(root, selection["selectedRows"])
    need(len(selected) + 1 == selection["selectedCountIncludingSelf"] == 227, "root delivery membership")
    manifest = strict_json(read_regular(root / HOST / "input-manifest.json", root))
    frozen = verify_rows(root, manifest["members"])
    need(len(frozen) == 148 and manifest["product_tree"] == TREE, "source148/product tree")
    producer = strict_json(read_regular(root / CANDIDATE / "manifest.json", root))
    members = verify_rows(root / CANDIDATE, producer["members"])
    need(len(members) == 115, "producer115 membership")
    expected = {r["path"] for r in members}
    observed, nodes = set(), 0
    for base, dirs, files in os.walk(root / CANDIDATE, followlinks=False):
        nodes += len(dirs) + len(files)
        need(nodes <= 1024, "producer discovery node bound")
        dirs[:] = [d for d in dirs if d != "local"]
        for d in dirs:
            need(not (Path(base) / d).is_symlink(), "producer directory symlink")
        for name in files:
            p = Path(base) / name
            relative = p.relative_to(root / CANDIDATE).as_posix()
            if relative not in ("manifest.json", "freeze.json"):
                read_regular(p, root / CANDIDATE)
                observed.add(relative)
    need(observed == expected, "producer closed directory membership")
    product = {PurePosixPath(r["path"]).name: {"bytes": r["bytes"], "sha256": r["sha256"]}
               for r in members if r["path"].startswith("source/")}
    need(len(product) == 16 and hashlib.sha256(canonical(product)).hexdigest() == TREE, "independent product16 tree")
    source_paths = sorted("source/" + s for s in product)
    leaves = sorted(r["path"] for r in members if r["path"].startswith("tests/host-leaves/") and r["path"].endswith(".java"))
    need(len(leaves) == 86 and manifest["host_sources"] == sorted(source_paths + leaves + ["tests/ViewApiBoundaryTests.java"]), "host103 exact closure")
    need(manifest["sdk_sources"] == sorted(source_paths + ["tests/cross-leaf/NativeBridge.java"]), "SDK17 exact closure")
    need(manifest["copied_input_paths"] == sorted(set(manifest["host_sources"] + manifest["sdk_sources"] + ["tests/descriptor.json"])), "copied inputs exact closure")
    return {"schema": 1, "status": "prepared-source-data-only", "actual_run_reviewed": False,
            "pinned": pinned, "selected_paths_including_selection": 227,
            "manifest_members": len(frozen), "producer_members": len(members),
            "product_sources": 16, "product_tree": TREE, "host_sources": 103, "sdk_sources": 17,
            "source_map_sha256": hashlib.sha256(canonical(manifest["members"])).hexdigest()}


def validate_binding(binding):
    need(type(binding) is dict and binding.get("schema") == 1, "exact root binding required")
    need(binding.get("repository") == "snowdamiz/mixer", "repository binding")
    for field in ("delivered_head", "delivered_tree"):
        need(type(binding.get(field)) is str and re.fullmatch("[0-9a-f]{40}", binding[field]), field)
    need(binding.get("selection_sha256") == PINS[SELECTION + "/selection.json"], "selection binding")
    need(binding.get("workflow_path") == ".github/workflows/android-view-api-focused-admission.yml"
         and binding.get("workflow_sha256") == PINS[".github/workflows/android-view-api-focused-admission.yml"], "workflow binding")
    need(binding.get("dispatch_nonce") == NONCE and binding.get("run_attempt") == 1
         and binding.get("event") == "workflow_dispatch", "nonce/attempt/event binding")
    for field in ("run_id", "job_id", "artifact_id"):
        need(type(binding.get(field)) is int and binding[field] > 0, field + " exact numeric identity")
    need(binding.get("run_head_sha") == binding["delivered_head"], "run delivered head binding")
    need(binding.get("job_name") == "focused", "dedicated focused job required")
    need(binding.get("artifact_name") == "android-view-api-focused-" + binding["delivered_head"] + "-" + str(binding["run_id"]) + "-1", "dedicated artifact name")
    need(type(binding.get("artifact_size_bytes")) is int and 0 < binding["artifact_size_bytes"] <= LIMITS["archive_bytes"], "artifact service size bound")
    digest = binding.get("artifact_digest")
    need(digest is None or (type(digest) is str and re.fullmatch("sha256:[0-9a-f]{64}", digest)), "artifact service digest format")
    need(binding.get("artifact_expired") is False, "expired/unknown artifact refused")
    return binding


def inspect_zip(raw):
    """Validate every member before any extraction; return exact bytes and map.

    Bounds are independent from collector output limits. No extractall, imports,
    execution or network occurs. Unsafe archives never produce partial extraction.
    """
    need(type(raw) is bytes and 22 <= len(raw) <= LIMITS["archive_bytes"], "ZIP archive byte bound")
    need(raw[:4] == b"PK\x03\x04", "ZIP ordinary local-header envelope")
    eocd = raw.rfind(b"PK\x05\x06", max(0, len(raw) - 65557))
    need(eocd >= 0 and eocd + 22 <= len(raw), "ZIP EOCD missing")
    trailer = struct.unpack_from("<4s4H2IH", raw, eocd)
    need(trailer[1] == trailer[2] == 0 and trailer[3] == trailer[4]
         and trailer[4] != 65535 and trailer[5] + trailer[6] == eocd
         and eocd + 22 + trailer[7] == len(raw), "ZIP EOCD disk/size/ZIP64/trailing data")
    result, seen, aliases, ranges, total = {}, set(), set(), [], 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            need(1 <= len(infos) <= LIMITS["members"], "ZIP member count")
            need(len(infos) == trailer[4] and archive.start_dir == trailer[6], "ZIP central-directory identity")
            need(archive.start_dir <= len(raw), "ZIP central directory bound")
            for info in infos:
                name = safe_name(info.filename, info.is_dir())
                need(name not in seen and name.casefold() not in aliases, "ZIP duplicate/case alias")
                seen.add(name); aliases.add(name.casefold())
                mode = info.external_attr >> 16
                kind = stat.S_IFMT(mode)
                need(kind in (0, stat.S_IFDIR if info.is_dir() else stat.S_IFREG), "ZIP symlink/nonordinary node")
                need(not info.flag_bits & ~(0x800 | 8 | 6) and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), "ZIP encryption/flags/compression method")
                need(0 <= info.file_size <= LIMITS["member_bytes"] and info.compress_size >= 0, "ZIP per member bound")
                need(info.file_size <= max(1, info.compress_size) * LIMITS["compression_ratio"], "ZIP compression ratio")
                total += info.file_size
                need(total <= LIMITS["total_bytes"], "ZIP total expansion bound")
                at = info.header_offset
                need(0 <= at <= archive.start_dir - 30, "ZIP local header position")
                fields = struct.unpack_from("<4s5H3I2H", raw, at)
                signature, version, flags, method = fields[:4]
                nlen, xlen = fields[-2:]
                start = at + 30 + nlen + xlen
                end = start + info.compress_size
                need(signature == b"PK\x03\x04" and flags == info.flag_bits and method == info.compress_type
                     and start <= end <= archive.start_dir, "ZIP local/central header disagreement")
                local_name = raw[at + 30:at + 30 + nlen].decode("utf-8" if flags & 0x800 else "cp437", "strict")
                need(local_name == info.filename, "ZIP local path disagreement")
                if not flags & 8:
                    need(fields[6] == info.CRC and fields[7] == info.compress_size and fields[8] == info.file_size, "ZIP local CRC/size disagreement")
                else:
                    descriptor = end + (4 if raw[end:end + 4] == b"PK\x07\x08" else 0)
                    need(descriptor + 12 <= archive.start_dir
                         and struct.unpack_from("<III", raw, descriptor) == (info.CRC, info.compress_size, info.file_size), "ZIP exact data descriptor")
                    end = descriptor + 12
                ranges.append((at, end))
                with archive.open(info, "r") as stream:
                    data = stream.read(info.file_size + 1)
                    need(not stream.read(1), "ZIP member grew beyond declaration")
                need(len(data) == info.file_size and (binascii.crc32(data) & 0xffffffff) == info.CRC, "ZIP member CRC/length")
                if info.is_dir():
                    need(not data, "ZIP directory contains bytes")
                else:
                    result[name] = data
            ranges.sort()
            need(ranges[0][0] == 0 and ranges[-1][1] == archive.start_dir
                 and all(a[1] == b[0] for a, b in zip(ranges, ranges[1:])), "ZIP overlap/gap/unindexed local bytes")
    except (zipfile.BadZipFile, UnicodeError, struct.error, zlib.error, NotImplementedError, RuntimeError) as error:
        raise Refusal("ZIP decoder refusal: " + type(error).__name__ + ": " + str(error)[:500]) from error
    for name in result:
        need(not any(parent.as_posix() in result for parent in PurePosixPath(name).parents if parent.as_posix() != "."), "ZIP file/directory prefix collision")
    rows = [{"path": n, **identity(result[n])} for n in sorted(result)]
    return result, {"schema": 1, "archive": identity(raw), "files": len(result), "total_bytes": total,
                    "members": rows, "member_map_sha256": hashlib.sha256(canonical(rows)).hexdigest()}


def prepare(output):
    output = Path(output).absolute()
    need(output.is_relative_to(HERE / "local"), "review output must stay in ignored local/")
    output.mkdir(parents=True, exist_ok=False)
    report = {"command": list(sys.orig_argv), "python": {"executable": sys.executable, "version": sys.version},
              "audit_source": identity(read_regular(__file__, HERE)), "bootstrap": {"isolated": sys.flags.isolated, "no_site": sys.flags.no_site, "bytecode_disabled": sys.dont_write_bytecode}}
    try:
        need(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.dont_write_bytecode, "isolated no-site bytecode-disabled Python required")
        report["source_audit"] = source_audit()
        report["status"] = "prepared-source-data-only-actual-run-pending"
    except BaseException as error:
        report.update(status="refused-preparation-retained", error=type(error).__name__ + ": " + str(error)[:2000])
    (output / "receipt.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "receipt": str(output / "receipt.json")}))
    if "error" in report:
        raise Refusal(report["error"])


if __name__ == "__main__":
    need(len(sys.argv) == 3 and sys.argv[1] == "prepare", "only source/data preparation CLI exists; acquisition pending root binding")
    prepare(sys.argv[2])
