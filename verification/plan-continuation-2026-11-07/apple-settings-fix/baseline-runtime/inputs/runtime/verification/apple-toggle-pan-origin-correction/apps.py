"""Retry validation: exact restored archive, finite installed permission policy.

The two app archives and their 267-file handoff remain immutable. No compiler,
subprocess, simulator, physical-device, Git, or UI operation belongs here.
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import plistlib
import stat

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
ORIGINAL = BASE.parent / "apple-toggle-native-failure-analysis"
ORIGINAL_SEAL = "9f91c9e56d964d1c505c96ac84034b49029bf386ac1a43de5ab0eaed33eca451"
spec = importlib.util.spec_from_file_location("mixer_frozen_toggle_handoff", ORIGINAL / "packet.py")
frozen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frozen)
CONFIGS = {key: dict(value) for key, value in frozen.CONFIGS.items()}
SOURCE_CLOSURE = frozen.SOURCE_CLOSURE
file_sha = frozen.file_sha
read_json = frozen.read_json
require = frozen.require
archive_payload = frozen.archive_payload
relative_name = frozen.relative_name
INSTALLED_MODES = {"main": {0o555, 0o755}, "dylib": {0o444, 0o555, 0o644, 0o755}, "metadata": {0o444, 0o644}, "directory": {0o555, 0o755}}


class ValidationError(ValueError):
    def __init__(self, reason, path, observed=None, expected=None):
        self.details = {"reason": reason, "failedPath": path, "observed": observed, "expected": expected}
        mode = observed.get("permissionOctal") if isinstance(observed, dict) else None
        super().__init__(f"{reason}: path={path!r}, observedMode={mode!r}, expected={expected!r}")


def role(path, config):
    if path in {".", "Frameworks", "_CodeSignature"}:
        return "directory"
    if path == config["executable"]:
        return "main"
    if path in {"Frameworks/libMixerCore.dylib", "Frameworks/libMixerUI.dylib"}:
        return "dylib"
    return "metadata"


def kind(mode):
    if stat.S_ISDIR(mode): return "directory"
    if stat.S_ISREG(mode): return "regular"
    if stat.S_ISLNK(mode): return "symlink"
    return "special"


def scan_app(app):
    """Collect every accessible path/type/mode before any validation assertion.

    Never descend through a symlink or open a nonregular file. Scan errors are
    retained in the report and then fail validation; they are not omissions.
    """
    rows, errors = [], []
    def visit(path):
        relative = "." if path == app else str(path.relative_to(app))
        try:
            value = path.lstat()
        except OSError as error:
            errors.append({"path": relative, "error": repr(error)})
            return
        row = {"path": relative, "type": kind(value.st_mode), "statMode": value.st_mode,
               "statModeOctal": oct(value.st_mode), "permissionMode": stat.S_IMODE(value.st_mode),
               "permissionOctal": format(stat.S_IMODE(value.st_mode), "04o"),
               "uid": value.st_uid, "gid": value.st_gid, "linkCount": value.st_nlink,
               "device": value.st_dev, "inode": value.st_ino, "bytes": value.st_size}
        rows.append(row)
        if row["type"] == "directory":
            try:
                children = sorted(path.iterdir())
            except OSError as error:
                errors.append({"path": relative, "error": repr(error)})
                return
            for child in children: visit(child)
    visit(app)
    return {"path": str(app), "entries": rows, "scanErrors": errors, "complete": not errors}


def expected_manifest(key):
    return read_json((BASE / "app" if key == "diagnostic" else ORIGINAL / CONFIGS[key]["folder"]) / "built-app-manifest.json")


def validate_inventory(app, key, inventory, installed):
    config = CONFIGS[key]
    manifest = expected_manifest(key)
    rows = {row["path"]: row for row in inventory["entries"]}
    if inventory["scanErrors"]:
        failure = inventory["scanErrors"][0]
        raise ValidationError("Incomplete app inventory", failure["path"], rows.get(failure["path"]), failure)
    if app.name != config["app"] or app.resolve() != app:
        raise ValidationError("App root identity or canonical path changed", ".", rows.get("."), config["app"])
    expected_dirs = {"."} | {str(parent) for name in manifest["files"] for parent in pathlib.PurePosixPath(name).parents if str(parent) != "."}
    expected = expected_dirs | set(manifest["files"])
    extra, missing = sorted(set(rows) - expected), sorted(expected - set(rows))
    if extra:
        raise ValidationError("Unexpected app path", extra[0], rows[extra[0]], sorted(expected))
    if missing:
        raise ValidationError("Missing app path", missing[0], None, sorted(expected))
    for path, row in rows.items():
        category = "directory" if path in expected_dirs else role(path, config)
        expected_type = "directory" if category == "directory" else "regular"
        if row["type"] != expected_type:
            raise ValidationError("App path type is not permitted", path, row, expected_type)
        if expected_type == "regular" and row["linkCount"] != 1:
            raise ValidationError("Hard-linked payload is not permitted", path, row, "one regular file link")
        mode = row["permissionMode"]
        if mode & 0o7000:
            raise ValidationError("Special permission bits are forbidden", path, row, "no setuid/setgid/sticky bits")
        if mode & 0o022:
            raise ValidationError("Group/world writable app path is forbidden", path, row, "no group/world write bits")
        allowed = INSTALLED_MODES[category] if installed else {0o755 if category in {"main", "dylib", "directory"} else 0o644}
        if mode not in allowed:
            raise ValidationError("Installed permission policy rejected" if installed else "Restored archive mode mismatch", path, row, sorted(format(value, "04o") for value in allowed))
    return rows, manifest


def validate_content(app, key, rows, manifest):
    config = CONFIGS[key]
    content = {}
    for name, expected in manifest["files"].items():
        row = rows[name]
        try:
            descriptor = os.open(app / name, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, "rb") as stream:
                opened = os.fstat(stream.fileno())
                if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_nlink) != (row["device"], row["inode"], row["statMode"], row["linkCount"]):
                    changed = {**row, "statMode": opened.st_mode, "statModeOctal": oct(opened.st_mode), "permissionMode": stat.S_IMODE(opened.st_mode), "permissionOctal": format(stat.S_IMODE(opened.st_mode), "04o"), "linkCount": opened.st_nlink, "inode": opened.st_ino, "device": opened.st_dev}
                    raise ValidationError("App path changed after inventory", name, changed, row)
                payload = stream.read()
        except OSError as error:
            raise ValidationError("App payload could not be read safely", name, row, repr(error)) from error
        if len(payload) != expected["bytes"] or hashlib.sha256(payload).hexdigest() != expected["sha256"]:
            raise ValidationError("App payload hash or length changed", name, row, expected)
        content[name] = payload
    try:
        info = plistlib.loads(content["Info.plist"])
    except Exception as error:
        raise ValidationError("App Info.plist invalid", "Info.plist", rows["Info.plist"], repr(error)) from error
    if info.get("CFBundleIdentifier") != config["bundle"] or info.get("CFBundleExecutable") != config["executable"]:
        raise ValidationError("App Info identity changed", "Info.plist", rows["Info.plist"], config)
    binaries = {}
    for name in [config["executable"], "Frameworks/libMixerCore.dylib", "Frameworks/libMixerUI.dylib"]:
        try:
            identity = frozen.macho(content[name])
        except Exception as error:
            raise ValidationError("App Mach-O identity invalid", name, rows[name], repr(error)) from error
        if identity["fileType"] != (2 if name == config["executable"] else 6):
            raise ValidationError("App Mach-O role changed", name, rows[name], "executable2/dylib6")
        binaries[name] = identity
    return binaries


def verify_restored(app, key):
    inventory = scan_app(app)
    rows, manifest = validate_inventory(app, key, inventory, installed=False)
    binaries = validate_content(app, key, rows, manifest)
    return {"path": str(app), "archiveSHA256": manifest["archiveSHA256"], "exactManifest": True,
            "permissionScope": "exact-restored-archive", "observedPermissions": inventory,
            "binaryBuildVersions": binaries}


def verify_installed(app, key, reporter):
    inventory = scan_app(app)
    # This durable event must precede even the first root/path/type/mode check.
    reporter("installed-app-inventory-before-validation", {"candidate": key, "inventory": inventory,
             "policy": {name: sorted(format(value, "04o") for value in values) for name, values in INSTALLED_MODES.items()}})
    try:
        rows, manifest = validate_inventory(app, key, inventory, installed=True)
        binaries = validate_content(app, key, rows, manifest)
    except ValidationError as error:
        reporter("installed-app-validation-failed", {"candidate": key, "path": str(app), "failure": error.details})
        raise
    result = {"path": str(app), "archiveSHA256": manifest["archiveSHA256"], "exactManifest": True,
              "permissionScope": "finite-installed-role-policy", "observedPermissions": inventory,
              "binaryBuildVersions": binaries}
    reporter("installed-app-validation-passed", {"candidate": key, "result": result})
    return result


def restore(destination, key):
    config = CONFIGS[key]
    require(not destination.is_symlink() and destination.resolve() == destination, "Refusing linked restore destination")
    app = destination / config["app"]
    if app.exists(): return verify_restored(app, key)
    require(not destination.exists(), "Restore destination exists without valid app")
    manifest = expected_manifest(key)
    folder = BASE / "app" if key == "diagnostic" else ORIGINAL / config["folder"]
    payload, modes = archive_payload(folder / "built-app.tar.gz", manifest, config)
    destination.mkdir(parents=True)
    for directory in [app, app / "Frameworks", app / "_CodeSignature"]:
        directory.mkdir(exist_ok=True); directory.chmod(0o755)
    for name, value in payload.items():
        target = app / relative_name(name)
        target.write_bytes(value); target.chmod(modes[name])
    return verify_restored(app, key)


def verify_packet():
    original = frozen.verify_packet()
    app = BASE / "app"
    lock = read_json(app / "source-lock.json")
    actual = {str(path.relative_to(app / "source")): file_sha(path) for path in sorted((app / "source").rglob("*")) if path.is_file()}
    digest = hashlib.sha256(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(actual == lock["sha256"] and digest == lock["sourceClosureSHA256"], "Corrected app source changed")
    baseline = read_json(ORIGINAL / CONFIGS["diagnostic"]["folder"] / "source-lock.json")
    changed = sorted(name for name in set(actual) | set(baseline["sha256"]) if actual.get(name) != baseline["sha256"].get(name))
    require(changed == ["Prototype/AuthoredToggleCarrier.swift", "Prototype/TogglePanAdmission.swift"], "App change escaped narrow admission correction")
    require(file_sha(app / "source/Prototype/TogglePanPolicy.swift") == baseline["sha256"]["Prototype/TogglePanPolicy.swift"], "Frozen 6pt/1.2 policy changed")
    manifest = expected_manifest("diagnostic")
    payload, _ = archive_payload(app / "built-app.tar.gz", manifest, CONFIGS["diagnostic"])
    receipt = read_json(app / "receipt.json")
    require(all(file_sha(pathlib.Path(name)) == digest for name, digest in receipt["toolFiles"].items()), "Corrected app compiler/platform tool changed")
    commands = read_json(app / receipt["buildCommands"])
    require(all(item["exitCode"] == 0 for item in commands), "Corrected app compile failed")
    compiled = {value.split("/source/",1)[1] for command in commands for value in command["argv"] if "/source/" in value and value.endswith(".swift")}
    require(compiled == {name for name in actual if name.endswith(".swift")}, "Corrected app compile source closure mismatch")
    require(receipt["sourceClosureSHA256"] == digest and receipt["archiveSHA256"] == manifest["archiveSHA256"], "Corrected app receipt changed")
    binaries = {name: frozen.macho(payload[name]) for name in [CONFIGS["diagnostic"]["executable"], "Frameworks/libMixerCore.dylib", "Frameworks/libMixerUI.dylib"]}
    info = plistlib.loads(payload["Info.plist"])
    require(info["CFBundleIdentifier"] == CONFIGS["diagnostic"]["bundle"] and info["CFBundleExecutable"] == CONFIGS["diagnostic"]["executable"], "Corrected app identity changed")
    return {"originalFrozenHandoff": original, "comparatorUnchanged": True,
            "diagnostic": {"sourceClosureSHA256": digest, "archiveSHA256": manifest["archiveSHA256"], "binaryBuildVersions": binaries},
            "changedDiagnosticFiles": changed, "frozenPanPolicyUnchanged": True, "nativeExecution": False}
