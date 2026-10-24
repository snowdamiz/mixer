"""C5 bounded data-only ar/tar inspection. Never extracts files on the host."""
import base64
import bz2
import compression.zstd
import datetime
import gzip
import hashlib
import io
import json
import lzma
from pathlib import Path
import posixpath
import re
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SELECTION = ROOT/"verification/stripe-webhook-resource-ingress-root-review/linux-compiler-assembly-selection.json"
SELECTION_SHA = "448788d165d55f062d56eda8f0c10403b7258127dae0aa9d33fc957341490f4b"
ACQUISITION = ROOT/"verification/stripe-resource-linux-compiler-acquisition"
ACQUISITION_SHA = "8a95b1b94b8f1911aa53e161fe54534777987d1dc5eb04aa3494ee2593b649f3"
LOCK = ROOT/"verification/stripe-resource-linux-compiler-metadata-v3/package-lock.json"
LOCK_SHA = "4db8b41afffdf796acaec18bcc3b5574be593af0c11c4cb860b39da5d64a36b4"
LIMIT = 536870912


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            value.update(block)
    return value.hexdigest()


def save(path, value, maximum=16777216):
    raw = (json.dumps(value, indent=2, sort_keys=True)+"\n").encode()
    require(len(raw) <= maximum, "fixed JSON export/metadata bound")
    with path.open("xb") as stream:
        stream.write(raw)


def ar_members(raw):
    require(raw.startswith(b"!<arch>\n") and len(raw) <= 67108864, "invalid or oversized ar envelope")
    result, offset = {}, 8
    while offset < len(raw):
        require(offset+60 <= len(raw), "truncated ar header")
        header = raw[offset:offset+60]
        require(header[58:] == b"`\n", "malformed ar header terminator")
        name = header[:16].decode("ascii").rstrip(" ").removesuffix("/")
        size_raw = header[48:58].decode("ascii").strip()
        require(size_raw.isdigit(), "malformed ar size")
        size = int(size_raw)
        require(name in ("debian-binary", "control.tar.gz", "control.tar.xz", "control.tar.zst",
                         "data.tar.gz", "data.tar.xz", "data.tar.zst") and name not in result, "unsupported/duplicate ar member")
        offset += 60
        require(size <= len(raw)-offset, "truncated ar member")
        result[name] = raw[offset:offset+size]
        offset += size
        if size % 2:
            require(offset < len(raw) and raw[offset:offset+1] == b"\n", "invalid ar padding")
            offset += 1
    require(result.get("debian-binary") == b"2.0\n" and len(result) == 3
            and sum(name.startswith("control.") for name in result) == 1
            and sum(name.startswith("data.") for name in result) == 1, "ambiguous deb envelope")
    return result


class BoundedReader:
    def __init__(self, stream, budget):
        self.stream, self.budget = stream, budget

    def read(self, size=-1):
        require(time.monotonic() < self.budget["deadline"], "host inspection deadline")
        require(size >= 0, "unbounded decompression read")
        data = self.stream.read(min(size, LIMIT-self.budget["expanded"]+1))
        self.budget["expanded"] += len(data)
        require(self.budget["expanded"] <= LIMIT, "decompression bomb / expanded byte bound")
        return data


class BoundedTarInfo(tarfile.TarInfo):
    @classmethod
    def frombuf(cls, buf, encoding, errors):
        member = super().frombuf(buf, encoding, errors)
        require(member.size <= LIMIT, "declared tar member exceeds expanded bound")
        if member.type in (tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK):
            require(member.size <= 4097, "oversized long path header")
        require(member.type not in (tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.GNUTYPE_SPARSE),
                "unsupported PAX/sparse header")
        return member


def decompressed(name, raw, budget):
    source = io.BytesIO(raw)
    if name.endswith(".zst"):
        stream = compression.zstd.ZstdFile(source, "rb")
    elif name.endswith(".xz"):
        stream = lzma.LZMAFile(source, "rb")
    elif name.endswith(".gz"):
        stream = gzip.GzipFile(fileobj=source, mode="rb")
    else:
        raise ValueError("unselected compression")
    return BoundedReader(stream, budget)


def member_path(name):
    require(len(name.encode("utf-8")) <= 4096 and not name.startswith("/") and "\\" not in name,
            "absolute, ambiguous, or overlong member path")
    while name.startswith("./"):
        name = name[2:]
    name = name.rstrip("/")
    if name in ("", "."):
        return ""
    require(all(part not in ("", ".", "..") for part in name.split("/"))
            and re.fullmatch(r"[A-Za-z0-9_+.,@%:=~/-]+", name) is not None,
            "unsupported or traversal member path")
    return name


def target_path(path, target, hard=False):
    require(len(target.encode()) <= 4096 and not target.startswith("/") and "\\" not in target
            and re.fullmatch(r"[A-Za-z0-9_+.,@%:=~/-]+", target) is not None, "absolute or unsupported link target")
    result = posixpath.normpath(target if hard else posixpath.join(posixpath.dirname(path), target))
    while result.startswith("./"):
        result = result[2:]
    require(result not in ("", ".", "..") and not result.startswith("../") and not result.startswith("/"), "link escape")
    return result


def insert(graph, item):
    path = item["path"]
    if path in graph:
        prior = graph[path]
        keys = ("type", "mode", "bytes", "sha256", "target")
        require(all(prior.get(key) == item.get(key) for key in keys), "inconsistent cross-package path collision: "+path)
        prior["packages"].extend(item["packages"])
    else:
        graph[path] = item


def validate_graph(graph):
    for path, item in graph.items():
        parent = posixpath.dirname(path)
        while parent:
            require(parent not in graph or graph[parent]["type"] == "directory", "link/file ancestor alias collision: "+path)
            parent = posixpath.dirname(parent)
        if item["type"] in ("symlink", "hardlink"):
            item["resolvedTarget"] = target_path(path, item["target"], item["type"] == "hardlink")
    dangling = []
    for path, item in graph.items():
        if item["type"] not in ("symlink", "hardlink"):
            continue
        resolved, seen = item["resolvedTarget"], {path}
        while True:
            require(resolved not in seen, "link cycle: "+path)
            seen.add(resolved)
            changed = False
            parts = resolved.split("/")
            for count in range(1, len(parts)+1):
                prefix = "/".join(parts[:count])
                node = graph.get(prefix)
                if node and node["type"] in ("symlink", "hardlink"):
                    require(item["type"] != "hardlink", "hardlink target must be direct regular data")
                    suffix = "/".join(parts[count:])
                    resolved = posixpath.normpath(posixpath.join(node["resolvedTarget"], suffix))
                    require(not resolved.startswith("../") and resolved != "..", "resolved graph escape")
                    changed = True
                    break
            if not changed:
                break
        item["finalTarget"] = resolved
        target = graph.get(resolved)
        if item["type"] == "hardlink":
            require(target is not None and target["type"] == "file", "unsupported hardlink target")
            item["bytes"], item["sha256"] = target["bytes"], target["sha256"]
        elif target is None:
            dangling.append({"path": path, "targetInsidePrefix": resolved})
    return dangling


def content_record(raw):
    result = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    try:
        result["utf8Data"] = raw.decode("utf-8")
    except UnicodeDecodeError:
        result["base64Data"] = base64.b64encode(raw).decode("ascii")
    return result


def inspect_one(package, raw, budget, graph, controls, notices):
    members = ar_members(raw)
    own = set()
    control_fields = None
    for archive_name, compressed in members.items():
        if archive_name == "debian-binary":
            continue
        is_control = archive_name.startswith("control.")
        budget["currentArchive"] = archive_name
        with tarfile.open(fileobj=decompressed(archive_name, compressed, budget), mode="r|", tarinfo=BoundedTarInfo) as archive:
            for member in archive:
                budget["currentMember"] = member.name
                budget["members"] += 1
                require(budget["members"] <= 100000, "member count bound")
                path = member_path(member.name)
                require(member.size >= 0 and member.size <= LIMIT, "member size bound")
                require(not member.sparse and not member.pax_headers, "unsupported sparse/PAX member")
                if not path:
                    require(member.isdir() and member.size == 0, "invalid root marker")
                    continue
                key = (is_control, path)
                require(key not in own, "duplicate path within package")
                own.add(key)
                require(member.mode & 0o6000 == 0, "privileged archive mode")
                if member.isdir():
                    item = {"path": path, "type": "directory", "mode": member.mode, "bytes": 0}
                elif member.issym() or member.islnk():
                    require(not is_control and member.size == 0, "control link or nonzero link data unsupported")
                    kind = "hardlink" if member.islnk() else "symlink"
                    target_path(path, member.linkname, member.islnk())
                    item = {"path": path, "type": kind, "mode": member.mode, "bytes": 0, "target": member.linkname}
                elif member.isfile():
                    notice = (not is_control and re.search(r"(?:^|/)(?:copyright|licen[cs]e(?:[._-].*)?|copying(?:[._-].*)?)$", path, re.I))
                    capture = is_control or bool(notice)
                    if capture:
                        require(member.size <= 1048576, "per-control/notice bound")
                        budget["captured"] += member.size
                        require(budget["captured"] <= 16777216, "aggregate control/notice bound")
                    value, chunks, size = hashlib.sha256(), [], 0
                    source = archive.extractfile(member)
                    require(source is not None, "missing regular data")
                    while True:
                        block = source.read(65536)
                        if not block:
                            break
                        size += len(block)
                        require(size <= member.size, "member data overrun")
                        value.update(block)
                        if capture:
                            chunks.append(block)
                    require(size == member.size, "truncated regular data")
                    item = {"path": path, "type": "file", "mode": member.mode, "bytes": size, "sha256": value.hexdigest()}
                    if capture:
                        data = b"".join(chunks)
                        record = {"package": package["name"], "version": package["version"], "path": path, **content_record(data)}
                        (controls if is_control else notices).append(record)
                        if is_control and path == "control":
                            control_fields = {}
                            for line in data.decode().splitlines():
                                if line and not line.startswith((" ", "\t")) and ":" in line:
                                    k, v = line.split(":", 1)
                                    require(k not in control_fields, "duplicate control field")
                                    control_fields[k] = v.strip()
                else:
                    raise ValueError("special/unsupported tar member")
                if not is_control:
                    item["packages"] = [package["name"]]
                    insert(graph, item)
            while True:
                trailing = archive.fileobj.read(65536)
                if not trailing:
                    break
                require(not any(trailing), "ambiguous nonzero data after tar end")
    require(control_fields is not None and control_fields.get("Package") == package["name"]
            and control_fields.get("Version") == package["version"]
            and control_fields.get("Architecture") == package["architecture"]
            and int(control_fields.get("Installed-Size", "-1")) == package["installedSizeKiB"], "deb control differs from signed lock")


def main():
    require(sha(SELECTION) == SELECTION_SHA and sha(LOCK) == LOCK_SHA and sha(ACQUISITION/"seal.json") == ACQUISITION_SHA,
            "selected inputs changed")
    seal = json.loads((ACQUISITION/"seal.json").read_text())
    for name, expected in {**seal["files"], **seal["localCacheFiles"]}.items():
        require(sha(ROOT/name) == expected, "immutable acquisition input changed")
    output = HERE/"inspection"
    output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    budget = {"expanded": 0, "members": 0, "captured": 0, "deadline": started+30}
    graph, controls, notices = {}, [], []
    records, failure = [], None
    try:
        for package in json.loads(LOCK.read_text())["packages"]:
            budget["currentPackage"] = package["name"]
            path = ACQUISITION/"attempt/packages"/Path(package["filename"]).name
            require(path.stat().st_size == package["bytes"] and sha(path) == package["sha256"], "archive signed size/hash changed")
            inspect_one(package, path.read_bytes(), budget, graph, controls, notices)
            records.append({"package": package["name"], "sha256": package["sha256"], "status": "bounded-data-inspected"})
        dangling = validate_graph(graph)
        save(output/"expected-manifest.json", {"schema": 1, "files": sorted(graph.values(), key=lambda x: x["path"]), "danglingInsidePrefixLinks": dangling})
        save(output/"control-inventory.json", {"schema": 1, "dataOnly": True, "scriptsExecuted": False, "members": controls}, 8388608)
        save(output/"notice-inventory.json", {"schema": 1, "dataOnly": True, "reviewStatus": "root-component-notice-review-pending", "members": notices}, 8388608)
    except Exception as error:
        failure = {"type": type(error).__name__, "reason": str(error)}
        save(output/"partial-graph.json", {"schema": 1, "files": sorted(graph.values(), key=lambda x: x["path"]), "incomplete": True})
        save(output/"partial-controls.json", {"schema": 1, "members": controls, "incomplete": True}, 8388608)
        save(output/"partial-notices.json", {"schema": 1, "members": notices, "incomplete": True}, 8388608)
    save(output/"receipt.json", {"schema": 1, "status": "host-data-inspection-completed" if failure is None else "failed-prerequisite",
        "selectionSha256": SELECTION_SHA, "lockSha256": LOCK_SHA, "sourceSha256": sha(Path(__file__)),
        "hostPython": {"version": sys.version, "executable": sys.executable, "sha256": sha(Path(sys.executable))},
        "librarySources": {module.__name__: {"path": module.__file__, "sha256": sha(Path(module.__file__))} for module in (tarfile, compression.zstd, lzma, gzip)},
        "records": records, "expandedTarBytes": budget["expanded"], "memberCount": budget["members"],
        "capturedControlNoticeBytes": budget["captured"], "graphPaths": len(graph), "error": failure,
        "lastInspectionContext": {key: budget.get(key) for key in ("currentPackage", "currentArchive", "currentMember")},
        "elapsedSeconds": time.monotonic()-started, "hostExtractionExecuted": False, "packageScriptsExecuted": False,
        "nativeAttemptExecuted": False, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    print(json.dumps({"status": "host-data-inspection-completed" if failure is None else "failed-prerequisite",
                      "packagesInspected": len(records), "members": budget["members"], "paths": len(graph), "error": failure}))


if __name__ == "__main__":
    main()
