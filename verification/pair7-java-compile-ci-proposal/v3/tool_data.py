"""Pure file-only tool verifier derived from the exact reviewed prior collector.

CHECK/file_identity/HERE are supplied by the selected v3 collector before use.
No child command, custody import, product import or fallback is present.
"""
import json
import os
from pathlib import Path
import platform
import stat
import sys
class Refusal(RuntimeError):
    pass
CHECK = lambda: None
HERE = None
file_identity = None
file_snapshot = None

def identity(path):
    CHECK()
    return file_identity(Path(path),268435456,CHECK)

def route_status(value):
    return [value.st_dev,value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,value.st_ctime_ns]

def resolved_snapshot(invocation, maximum):
    """Admit a named invocation separately from its canonical ordinary target."""
    CHECK()
    invocation = Path(invocation).absolute()
    before = invocation.lstat()
    if not (stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode)):
        raise Refusal("Ordinary or symlink invocation required")
    link = os.readlink(invocation) if stat.S_ISLNK(before.st_mode) else None
    target = invocation.resolve(strict=True)
    target_before = target.lstat()
    CHECK()
    data,value = file_snapshot(target,maximum,CHECK)
    CHECK()
    if (invocation.resolve(strict=True) != target or route_status(invocation.lstat()) != route_status(before)
            or (os.readlink(invocation) if invocation.is_symlink() else None) != link
            or route_status(target.lstat()) != route_status(target_before)):
        raise Refusal("Invocation or resolved target changed during bounded read")
    return data,{"invocation_path":str(invocation),"resolved_path":str(target),
                 "symlink_target":link,"invocation_status":route_status(before),
                 "target_status":route_status(target_before),**value}

def python_route(executable, expected, version, isolated, no_site, no_bytecode):
    invocation = str(Path(executable).absolute())
    if expected.get("boundary") == "root-admitted-ubuntu-provider-infrastructure":
        if (invocation != expected["path"] or tuple(version) != tuple(expected["version"])
                or isolated != 1 or no_site != 1 or not no_bytecode):
            raise Refusal("Selected isolated Ubuntu Python invocation changed")
    data,actual = resolved_snapshot(invocation,268435456)
    if expected.get("boundary") != "root-admitted-ubuntu-provider-infrastructure":
        if actual["resolved_path"] != expected["path"] or actual["sha256"] != expected["sha256"]:
            raise Refusal("Collector Python target identity changed")
    return actual

def regular(path, root):
    path, root = Path(path), Path(root)
    if not path.is_relative_to(root):
        raise Refusal("input escapes root")
    for component in (path, *path.parents):
        if component == root.parent:
            break
        if stat.S_ISLNK(component.lstat().st_mode):
            raise Refusal("source symlink refused: " + str(component))
    if not stat.S_ISREG(path.lstat().st_mode):
        raise Refusal("ordinary input required: " + str(path))
    return path

def bounded_files(root, maximum_nodes, prune_local=False, excluded_files=()):
    root = Path(root)
    if root.resolve(strict=True) != root or not stat.S_ISDIR(root.lstat().st_mode):
        raise Refusal("ordinary tool directory required")
    nodes, files, stack = 1, [], [root]
    while stack:
        CHECK()
        directory, names = stack.pop(), []
        with os.scandir(directory) as entries:
            for entry in entries:
                CHECK()
                nodes += 1
                if nodes > maximum_nodes:
                    raise Refusal("tool node discovery bound")
                names.append(entry.name)
        for name in sorted(names):
            CHECK()
            path = directory/name
            relative = path.relative_to(root).as_posix()
            if relative in excluded_files or (prune_local and "local" in path.relative_to(root).parts):
                continue
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                stack.append(path)
            elif stat.S_ISREG(mode):
                regular(path,root); files.append(path)
            else:
                raise Refusal("tool symlink/special node refused")
    return sorted(files)

def distribution_tree(path):
    raise Refusal("Legacy distribution/fallback mode excluded from pair7 v3")

def verify_tools(profile):
    CHECK()
    if sys.platform != profile["host_os"] or platform.machine() != profile["host_machine"]:
        raise Refusal("selected OS/architecture tool profile required")
    actual = {}
    mode = profile.get("identity_mode", "historical-distribution-tree")
    if mode != "package-observed-jdk-runtime-files-v1":
        raise Refusal("Only exact package-observed profile is selected")
    if mode == "package-observed-jdk-runtime-files-v1":
        name = profile["jdk_runtime_manifest"]
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise Refusal("runtime manifest path escapes admission")
        manifest_data,manifest_identity = file_snapshot(HERE/name,262144,CHECK)
        if manifest_identity["sha256"] != profile["jdk_runtime_manifest_sha256"]:
            raise Refusal("selected runtime manifest identity changed")
        expected = json.loads(manifest_data)
        rows = expected["members"] if isinstance(expected, dict) else expected
        if not 1 <= len(rows) <= 256:
            raise Refusal("JDK runtime member bound")
        if len(rows) != profile["jdk_runtime_members"] or sum(e["bytes"] for e in rows) != profile["jdk_runtime_bytes"]:
            raise Refusal("JDK runtime manifest totals")
        seen, observed = set(), []
        for entry in rows:
            CHECK()
            relative = entry["path"]
            if relative in seen or Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise Refusal("JDK runtime path/duplicate")
            seen.add(relative)
            path = Path(profile["jdk"]) / relative
            regular(path, Path(profile["jdk"]))
            resolved = path.resolve(strict=True)
            if not stat.S_ISREG(resolved.lstat().st_mode):
                raise Refusal("JDK runtime regular file required")
            value = identity(resolved)
            if value != {"bytes": entry["bytes"], "sha256": entry["sha256"]}:
                raise Refusal("package-observed JDK runtime member changed: " + relative)
            observed.append({"path": relative, "resolved": str(resolved),
                             "symlink": os.readlink(path) if path.is_symlink() else None, **value})
        jdk = Path(profile["jdk"])
        scoped = {"bin/java", "bin/javac", "release"}
        for folder, excluded in (("conf", ()), ("lib", ("src.zip", "security/cacerts"))):
            scoped.update(folder + "/" + p.relative_to(jdk / folder).as_posix()
                          for p in bounded_files(jdk / folder, 4096, excluded_files=excluded))
        if scoped != seen:
            raise Refusal("JDK runtime conf/lib closed membership changed")
        actual["jdk_runtime"] = {"members": observed, "scope": profile["packaging_boundary"]}
    elif mode == "historical-distribution-tree":
        for name, entry in profile["distributions"].items():
            value = distribution_tree(entry["path"])
            if value["sha256"] != entry["sha256"]:
                raise Refusal("official tool distribution changed: " + name)
            actual[name] = value
    else:
        raise Refusal("unreviewed tool identity mode")
    actual["tool_files"] = {}
    for path, expected in profile["files"].items():
        value = identity(path)
        if value != expected:
            raise Refusal("official tool file changed: " + path)
        actual["tool_files"][path] = value
    for entry in profile["metadata_sha256"].values():
        if identity(entry["path"])["sha256"] != entry["sha256"]:
            raise Refusal("official tool metadata changed")
    expected_python = profile["collector_python"]
    actual["python"] = {**python_route(sys.executable,expected_python,sys.version_info[:3],
                                      sys.flags.isolated,sys.flags.no_site,sys.dont_write_bytecode),
                        "version":sys.version,
                        "bootstrap_independently_pinned_by_running_collector":False}
    if expected_python.get("boundary") == "root-admitted-ubuntu-provider-infrastructure":
        release_data,release_identity = resolved_snapshot("/etc/os-release",65536)
        os_release = release_data.decode("utf-8")
        parsed = dict(line.split("=",1) for line in os_release.splitlines() if "=" in line)
        if parsed.get("ID", "").strip('"') != "ubuntu" or parsed.get("VERSION_ID", "").strip('"') != "24.04":
            raise Refusal("Ubuntu24.04 provider required")
        actual["provider_os_release"] = {"text":os_release,**release_identity}
    return actual
