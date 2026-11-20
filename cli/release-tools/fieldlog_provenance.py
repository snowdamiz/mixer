#!/usr/bin/env python3
"""Produce signed development-only FieldLog build provenance on a local Mac."""
import argparse
import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import stat
import subprocess
import tarfile
from tempfile import mkdtemp
import time
import zipfile

from canonical import cbor

FIELDLOG = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
SCOPE_FIELDS = ("organization", "project", "app", "environment")
PLATFORMS = ("ios", "android")
DOMAIN = b"mixer.local.build-provenance.v1\0"
TOOLS = {"aapt2", "android.jar", "apksigner", "clang", "hostSwift", "iosProbe", "keytool", "mixer",
         "openssl", "probe", "swiftc", "wasm-ld", "zipalign"}
FIELDLOG_STORAGE = {
    "Sources/FieldLogModels/Workspace.swift": "FieldLogModels/Workspace.swift",
    "Sources/FieldLogStorage/WorkspaceRepository.swift": "FieldLogStorage/WorkspaceRepository.swift",
    "Integrations/InstalledGuest/TaskStorage.swift": "FieldLogTaskStorageIntegration/FieldLogTaskStorage.swift",
}
INPUT_FILES = (
    "fieldlog.tar", "fieldlog-l04.patch", "FieldLog-public-development.apk",
    "apk-manifest.xml", "network.zip", "manifest-template.json",
    "project-template/mixer.yml", "project-template/mixer.lock",
    *(f"probe-package/{path}" for path in FIELDLOG_STORAGE.values()),
    *(f"hydrated/{path}" for path in ("Guest.swift", "TaskWire.swift", "CapabilityImports.c")),
)
INPUT_TREES = ("FieldLog.app", "project-template/Generated")

ANDROID_PACKAGE = "dev.fieldlog.generatedr90"
ANDROID_APP = dict(organization="mixer-local", project="fieldlog", app="fieldlog",
                   environment="development", bundle_id=ANDROID_PACKAGE)
HTTPS_BASE = "37e351f5ea58662ce71a85b9a740187a95f5608e"
HTTPS_VARIANTS = {"installed": "old", "proposed": "successor"}
HTTPS_APKS = {role: f"handoff/{name}/FieldLog.apk" for role, name in HTTPS_VARIANTS.items()}
HTTPS_ROOTS = "handoff/old/Installed/roots.json"
HTTPS_SEAL = "handoff/SHA256SUMS"
HTTPS_TOOLS = {"mixer", "hostSwift", "probe", "aapt2", "apksigner", "zipalign", "openssl"}
HTTPS_TEMPLATE = {"project-template/mixer.yml", "project-template/mixer.lock"}
HTTPS_INPUT_FILES = HTTPS_TEMPLATE | set(HTTPS_APKS.values()) | {
    HTTPS_ROOTS, HTTPS_SEAL, "handoff/permissions.json", "handoff/build.json", "handoff/manifest-template.json",
    "handoff/baseline.wasm", "handoff/candidate.wasm",
}
HTTPS_PROBE_SOURCES = {
    "Integrations/GeneratedReport/" + source if source.startswith("Sources/") else source: probe
    for source, probe in FIELDLOG_STORAGE.items()
}
APK_MATERIAL = "assets/ChecklistRelease/"
STORAGE = "storage.keyValue.v1"
HTTP = "network.http.v1"
CAPABILITIES = {
    HTTP: ("http", "fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3"),
    STORAGE: ("storage", "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"),
}
NATIVE_ABI = "29ab6ba4a86990bc99d4f510fc005a17d84426d8c893d36f5061f17c46786adf"
GRANT_SCHEMA = "b394ffd165ef28977de9743b1c1a98c419504787f2912e30d419cfb1582e15e1"
ANDROID_SCOPE = {field: ANDROID_APP[field] for field in SCOPE_FIELDS} | {"platform": "android"}
ANDROID_OTA_KEY_ID = "fieldlog-android-provenance-dev"



def require(condition, description):
    if not condition:
        raise ValueError(description)


def file_hash(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def save(path, value):
    path.write_bytes(encoded(value))


def load(path):
    return json.loads(path.read_bytes())


def strict_json(data):
    def object_from_pairs(pairs):
        value = dict(pairs)
        require(len(value) == len(pairs), "Duplicate JSON field in HTTPS input")
        return value

    return json.loads(data, object_pairs_hook=object_from_pairs)


def group_absent(pgid, seconds=0):
    deadline = time.monotonic() + seconds
    while True:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


def stop_group(process):
    for sig, grace in ((signal.SIGTERM, 2), (signal.SIGKILL, 4)):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        except PermissionError:
            return False
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            continue
        if group_absent(process.pid, grace):
            return True
    return False


def tree_files(root, name):
    tree = root / name
    require(tree.is_dir() and not tree.is_symlink(), f"Expected an input directory: {tree}")
    files = []
    for path in tree.rglob("*"):
        require(not path.is_symlink() and (path.is_file() or path.is_dir()),
                f"Unsupported input entry: {path}")
        if path.is_file():
            files.append(path)
    require(files, f"Empty input tree: {tree}")
    return files


def input_files(root):
    paths = [root / name for name in INPUT_FILES]
    for name in INPUT_TREES:
        paths.extend(tree_files(root, name))
    for path in paths:
        require(path.is_file() and path.resolve() == path, f"Expected a regular input file: {path}")
    return sorted(path.relative_to(root).as_posix() for path in paths)


def https_input_files(root):
    def unreadable(error):
        raise error

    files_found, directories_found = set(), set()
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=unreadable):
        for name in dirs + files:
            path = Path(directory) / name
            relative_path = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                directories_found.add(relative_path)
            else:
                require(stat.S_ISREG(mode) and (relative_path in HTTPS_TEMPLATE
                        or relative_path.startswith(("project-template/Generated/", "handoff/"))),
                        f"Unexpected HTTPS input entry: {relative_path}")
                files_found.add(relative_path)
    parents = {parent.as_posix() for name in files_found for parent in Path(name).parents} - {"."}
    entries = files_found | directories_found
    require(HTTPS_INPUT_FILES <= files_found and any(name.startswith("project-template/Generated/") for name in files_found)
            and parents == directories_found
            and len({name.casefold() for name in entries}) == len(entries),
            "HTTPS input inventory is incomplete, contains an empty directory, or is ambiguous")
    return sorted(files_found)


def tool_companions(tools, java_home):
    mixer_dir = tools["mixer"].parent
    return {
        "java": file_hash(java_home / "bin/java"),
        "apksigner.jar": file_hash(tools["apksigner"].parent / "lib/apksigner.jar"),
        **{path.relative_to(mixer_dir).as_posix(): file_hash(path)
           for path in tree_files(mixer_dir, "MixerCLI_MixerBuild.bundle")},
    }


def relative(path, settings):
    return os.path.relpath(path, settings.parent)


def check_https_approvals(inputs, files, tools, approvals):
    approved = {role: files[name] for role, name in HTTPS_APKS.items()} | {
        "probe": tools["probe"]["sha256"], "roots": files[HTTPS_ROOTS], "handoff": files[HTTPS_SEAL],
    }
    require(approvals == approved and all(re.fullmatch(r"[0-9a-f]{64}", value) for value in approved.values()),
            "The APK, probe, public roots or handoff seal differ from the independently approved SHA-256")
    require(approved["installed"] != approved["proposed"], "Choose two distinct approved APKs")
    seal = {}
    for line in (inputs / HTTPS_SEAL).read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        require(match, "Invalid handoff seal entry")
        digest, name = match.groups()
        require(name not in seal, "Duplicate handoff seal entry")
        seal[name] = digest
    require(seal == {name.removeprefix("handoff/"): digest for name, digest in files.items()
                     if name.startswith("handoff/") and name != HTTPS_SEAL},
            "Handoff differs from its full independent file seal")


def pin(args, *, https=False):
    settings = args.settings.resolve()
    inputs = args.inputs.resolve(strict=True)
    tool_names = HTTPS_TOOLS if https else TOOLS
    tools = dict(args.tool)
    require(len(tools) == len(args.tool) and tools.keys() == tool_names,
            f"Supply each tool once: {', '.join(sorted(tool_names))}")
    tools = {name: Path(os.path.abspath(path)) for name, path in tools.items()}
    java_home = args.java_home.resolve(strict=True)
    inventory = {
        "schema": 1,
        "inputs": relative(inputs, settings),
        "files": {name: file_hash(inputs / name) for name in (https_input_files if https else input_files)(inputs)},
        "javaHome": relative(java_home, settings),
        "tools": {name: {"path": relative(path, settings), "sha256": file_hash(path)}
                  for name, path in tools.items()},
        "toolCompanions": tool_companions(tools, java_home),
    }
    if https:
        require(not settings.is_relative_to(inputs), "Keep HTTPS settings outside the closed input directory")
        inventory["recipe"] = "android-https"
        inventory["approvals"] = {"installed": args.installed_apk_sha256, "proposed": args.proposed_apk_sha256,
                                  "probe": args.probe_sha256, "roots": args.roots_sha256,
                                  "handoff": args.handoff_seal_sha256}
        check_https_approvals(inputs, inventory["files"], inventory["tools"], inventory["approvals"])
    with settings.open("xb") as handle:
        handle.write(encoded(inventory))


class LocalCommands:
    def __init__(self, work, env):
        self.work = work
        self.env = env
        self.commands = []
        self.custody_resolved = True
        for name in ("logs", "tmp"):
            (work / name).mkdir()

    @contextmanager
    def temporary(self, parent=None):
        directory = Path(mkdtemp(dir=parent if parent is not None else self.work / "tmp"))
        try:
            yield directory
        finally:
            if self.custody_resolved:
                shutil.rmtree(directory)

    def run(self, *argv, expected=0, cwd=None, env=None, stdin=None, include_stderr=False, timeout=50,
            mixer_cli=False):
        command = [str(arg) for arg in argv]
        log = self.work / "logs" / str(len(self.commands) + 1)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   cwd=cwd, env=self.env | (env or {}), stdin=stdin, start_new_session=True)
        self.custody_resolved = False
        record = {"argv": command, "pgid": process.pid, "log": log.name}

        def persist(out, err, *, timed_out, eof, gone, inner_unknown=False):
            self.custody_resolved = gone and eof and process.returncode is not None and not inner_unknown
            observation = record | {"exit": process.returncode, "timedOut": timed_out,
                                    "pipeEOF": eof, "groupAbsent": gone}
            if not self.custody_resolved:
                observation["innerCustodyUnknown"] = inner_unknown
                save(self.work / "HOLD.json", observation)
            log.with_suffix(".out").write_bytes(out or b"")
            log.with_suffix(".err").write_bytes(err or b"")
            self.commands.append(observation)
            save(self.work / "commands.json", self.commands)

        try:
            out, err = process.communicate(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as interrupted:
            gone = stop_group(process)
            eof = False
            try:
                out, err = process.communicate(timeout=2)
                eof = True
            except subprocess.TimeoutExpired as pending:
                out, err = pending.output, pending.stderr
                process.stdout.close()
                process.stderr.close()
            persist(out, err, timed_out=isinstance(interrupted, subprocess.TimeoutExpired),
                    eof=eof, gone=gone, inner_unknown=mixer_cli)
            require(self.custody_resolved, f"Unresolved process custody for PGID {process.pid}. Preserve {self.work}")
            raise

        gone = group_absent(process.pid)
        if not gone:
            gone = stop_group(process)
            persist(out, err, timed_out=False, eof=True, gone=gone)
            require(gone, f"Unresolved process custody for PGID {process.pid}. Preserve {self.work}")
            raise RuntimeError(f"Command left descendants running: {command[0]}")
        # Mixer can report custody of a command it launched in its own group.
        inner_unknown = False
        if mixer_cli and process.returncode == 1:
            try:
                report = json.loads(out)
            except ValueError:
                report = None
            inner_unknown = isinstance(report, dict) and report.get("code") in {
                "process.custody-unknown", "process.custody-held",
            }
        persist(out, err, timed_out=False, eof=True, gone=True, inner_unknown=inner_unknown)
        require(self.custody_resolved, f"Unresolved Mixer command custody. Preserve {self.work}")
        if process.returncode != expected:
            raise subprocess.CalledProcessError(process.returncode, command, out, err)
        return out + err if include_stderr else out


class Build(LocalCommands):
    https = False

    def __init__(self, settings_path, work):
        inventory = settings_path.read_bytes()
        settings = (strict_json if self.https else json.loads)(inventory)
        require(settings["schema"] == 1 and settings["tools"].keys() == (HTTPS_TOOLS if self.https else TOOLS)
                and settings.get("recipe") == ("android-https" if self.https else None),
                "Unsupported FieldLog input inventory")
        if self.https:
            require(settings.keys() == {"schema", "recipe", "approvals", "inputs", "files", "javaHome", "tools", "toolCompanions"},
                    "Unsupported HTTPS inventory fields")
            self.approvals = settings["approvals"]
        self.inventory_sha256 = sha(inventory)

        def resolve(value):
            return (settings_path.parent / value).resolve(strict=True)

        self.inputs = resolve(settings["inputs"])
        if self.https:
            require(not work.is_relative_to(self.inputs), "Keep HTTPS output outside the closed input directory")
        require(set((https_input_files if self.https else input_files)(self.inputs)) == settings["files"].keys(),
                "Pinned input file set changed")
        for name, digest in settings["files"].items():
            require(file_hash(self.inputs / name) == digest, f"Pinned input bytes changed: {name}")
        if self.https:
            check_https_approvals(self.inputs, settings["files"], settings["tools"], self.approvals)

        # Keep argv[0] as swiftc even when the bytes are provided by swift-driver.
        self.tools = {name: Path(os.path.abspath(settings_path.parent / item["path"]))
                      for name, item in settings["tools"].items()}
        self.tool_hashes = {name: item["sha256"] for name, item in settings["tools"].items()}
        for name, path in self.tools.items():
            require(file_hash(path) == self.tool_hashes[name], f"Pinned tool bytes changed: {name}")
            require(name == "android.jar" or os.access(path, os.X_OK), f"Tool is not executable: {name}")

        java_home = resolve(settings["javaHome"])
        require(os.access(java_home / "bin/java", os.X_OK), "JAVA_HOME must contain the pinned Java launcher")
        if not self.https:
            require((java_home / "bin/keytool").resolve() == self.tools["keytool"].resolve(),
                    "JAVA_HOME must match the pinned keytool")
        self.companions = settings["toolCompanions"]
        require(tool_companions(self.tools, java_home) == self.companions, "Pinned tool companion bytes changed")
        host_swift = self.tools["hostSwift"]
        require(host_swift.name == "swift", "Select the host Swift executable named swift")
        work.mkdir(mode=0o700)
        (work / "home").mkdir()
        super().__init__(work, {"PATH": f"{host_swift.parent}:/usr/bin:/bin:/usr/sbin:/sbin",
                               "HOME": str(work / "home"), "TMPDIR": str(work / "tmp"),
                               "LC_ALL": "C", "JAVA_HOME": str(java_home)})

    def key(self, path):
        self.run(self.tools["openssl"], "genpkey", "-algorithm", "ED25519", "-out", path)
        der = self.run(self.tools["openssl"], "pkey", "-in", path, "-pubout", "-outform", "DER")
        require(der[:-32].hex() == "302a300506032b6570032100", "Expected a raw Ed25519 key")
        return base64.b64encode(der[-32:]).decode()

    def sign(self, key, content):
        with self.temporary() as directory:
            message = directory / "message"
            message.write_bytes(content)
            return self.run(self.tools["openssl"], "pkeyutl", "-sign", "-rawin", "-inkey", key, "-in", message)

    def project(self, baseline):
        baseline.mkdir()
        archive = self.inputs / "fieldlog.tar"
        with archive.open("rb") as stream:
            revision = self.run("/usr/bin/git", "get-tar-commit-id", stdin=stream).decode().strip()
        require(revision == FIELDLOG, "Expected a git archive of the supported FieldLog revision")
        with tarfile.open(archive) as source:
            require(all(item.isfile() or item.isdir() for item in source.getmembers()),
                    "FieldLog source archive must contain only files and directories")
            source.extractall(baseline, filter="data")
        self.run("/usr/bin/git", "init", "-q", cwd=baseline)
        self.run("/usr/bin/git", "apply", self.inputs / "fieldlog-l04.patch", cwd=baseline)
        template = self.inputs / "project-template"
        shutil.copytree(template / "Generated", baseline / "Generated")
        shutil.copyfile(template / "mixer.lock", baseline / "mixer.lock")
        config = load(template / "mixer.yml")
        config["applicationIdentifiers"] = {"ios": "dev.mixer.fieldlog", "android": ANDROID_PACKAGE}
        save(baseline / "mixer.yml", config)
        guest = baseline / "Integrations/InstalledGuest/SwiftGuest"
        guest.mkdir(parents=True, exist_ok=True)
        for name in ("Guest.swift", "TaskWire.swift", "CapabilityImports.c"):
            shutil.copyfile(self.inputs / "hydrated" / name, guest / name)
        native = baseline / "Integrations/GeneratedReport/Platforms/Android"
        # Use the app lane's exact merged manifest including the local delivery overlay.
        shutil.copyfile(self.inputs / "apk-manifest.xml", native / "AndroidManifest.xml")

    @staticmethod
    def edit_review(project):
        guest = project / "Integrations/InstalledGuest/SwiftGuest/Guest.swift"
        source = guest.read_text()
        before = """        #if REQUIRE_REVIEW
        if !completed {
            update(.review)
            return 0
        }
        #endif
"""
        require(source.count(before) == 1, "FieldLog confirmation edit preimage changed")
        guest.write_text(source.replace(before, before.removeprefix("        #if REQUIRE_REVIEW\n").removesuffix("        #endif\n")))

    def guest(self, project, name, platform):
        output = self.work / name
        source = Path("Integrations/InstalledGuest/SwiftGuest")
        tools = self.tools
        imports = output.with_suffix(".imports.o")
        swift = output.with_suffix(".o")
        wasm = output.with_suffix(".wasm")
        self.run(tools["clang"], "--target=wasm32-unknown-none", "-ffreestanding", "-Oz", "-c",
                 source / "CapabilityImports.c", "-o", imports, cwd=project)
        defines = ["-D", "FIELDLOG_ANDROID_TRIAL"] if platform == "android" else []
        self.run(tools["swiftc"], "-target", "wasm32-unknown-none-wasm", "-enable-experimental-feature", "Embedded",
                 "-enable-experimental-feature", "Extern", "-whole-module-optimization", "-Osize", "-parse-as-library",
                 "-Xfrontend", "-disable-stack-protector", *defines, "-emit-object",
                 source / "Guest.swift", source / "TaskWire.swift", "-o", swift, cwd=project)
        self.run(tools["wasm-ld"], "--no-entry", "--gc-sections", "--strip-all", "-z", "stack-size=16384",
                 "--max-memory=65536", "--export=mixer_guest_ui_start_v1", "--export=mixer_guest_ui_event_v1",
                 "--export=mixer_guest_ui_hydrate_v1", "--export=mixer_guest_capability_ready_v1", swift, imports, "-o", wasm)
        return wasm

    def source(self, project):
        return json.loads(self.run(self.tools["mixer"], "release", "inspect", "--directory", project,
                                   expected=2, timeout=105, mixer_cli=True))

    def android_contract(self, apk, package_id=ANDROID_PACKAGE):
        data = self.run(self.tools["aapt2"], "dump", "permissions", apk).decode()
        package = re.findall(r"^package: (\S+)$", data, re.MULTILINE)
        require(package == [package_id], "Android output has a different installed package ID")
        # Include the decoded compiled manifest so maxSdk, SDK-conditioned permissions,
        # components and scoped permission attributes participate in comparison.
        xml = self.run(self.tools["aapt2"], "dump", "xmltree", apk, "--file", "AndroidManifest.xml").decode()
        return {"bundleID": package[0], "permissions": data.splitlines()[1:], "compiledManifest": xml}

    def native_android(self, project, target, material, key, key_env, installed_contract, *, camera_control=False):
        original = self.inputs / "FieldLog-public-development.apk"
        manifest = project / "Integrations/GeneratedReport/Platforms/Android/AndroidManifest.xml"
        with self.temporary() as temp:
            linked = temp / "manifest.apk"
            self.run(self.tools["aapt2"], "link", "-I", self.tools["android.jar"],
                     "--manifest", manifest, "-R", self.inputs / "network.zip", "-o", linked)
            contract = self.android_contract(linked)
            if camera_control:
                camera = "uses-permission: name='android.permission.CAMERA'"
                require(camera not in installed_contract["permissions"]
                        and sorted(contract["permissions"]) == sorted([*installed_contract["permissions"], camera]),
                        "Expected exactly the added Android camera permission")
            else:
                require(contract == installed_contract, "Baseline manifest or overlay differs from the signed input APK")
            material["identity.json"] = self.bind(material, contract)
            unsigned, aligned = temp / "unsigned.apk", temp / "aligned.apk"
            with zipfile.ZipFile(linked) as new_manifest, zipfile.ZipFile(original) as old, zipfile.ZipFile(unsigned, "x") as out:
                for entry in new_manifest.infolist():
                    out.writestr(entry, new_manifest.read(entry))
                require("classes.dex" in old.namelist()
                        and any(re.fullmatch(r"lib/arm64-v8a/[^/]+\.so", n) for n in old.namelist()),
                        "Expected compiled Android code in the input APK")
                for entry in old.infolist():
                    if entry.filename.startswith(("META-INF/", "assets/ChecklistRelease/")) or entry.filename in new_manifest.namelist():
                        continue
                    with old.open(entry) as src, out.open(entry, "w") as dst:
                        shutil.copyfileobj(src, dst)
                for name, content in material.items():
                    out.writestr("assets/ChecklistRelease/" + name, content)
            self.run(self.tools["zipalign"], "-P", "16", "-f", "4", unsigned, aligned)
            unsigned.unlink()
            self.run(self.tools["apksigner"], "sign", "--ks", key, "--ks-pass", "env:LOCAL_APK_PASSWORD",
                     "--v3-signing-enabled", "true", "--v4-signing-enabled", "false", "--out", target, aligned,
                     env=key_env)
        self.run(self.tools["apksigner"], "verify", "--verbose", target)
        self.run(self.tools["zipalign"], "-c", "-P", "16", "4", target)
        require(self.android_contract(target) == contract, "Packaged Android contract differs from linked manifest")
        with zipfile.ZipFile(target) as apk:
            for name, expected in material.items():
                require(apk.read("assets/ChecklistRelease/" + name) == expected, "Packaged Android identity differs")
            with zipfile.ZipFile(original) as old:
                for name in old.namelist():
                    if re.fullmatch(r"classes(?:[0-9]+)?\.dex", name) or name.startswith("lib/"):
                        with old.open(name) as before, apk.open(name) as after:
                            require(hashlib.file_digest(before, "sha256").digest() ==
                                    hashlib.file_digest(after, "sha256").digest(), f"Native input changed: {name}")
        return contract

    @staticmethod
    def bind(material, contract):
        identity = json.loads(material["identity.json"])
        require(identity["application"]["bundle_id"] == contract["bundleID"], "Identity and packaged application differ")
        identity["build"]["permissions_sha256"] = sha(encoded(contract))
        identity["build"]["trust_roots_sha256"] = sha(material["roots.json"])
        return encoded(identity)

    def native_ios(self, target, material):
        with self.temporary() as temporary:
            app = temporary / "FieldLog.app"
            original = self.inputs / "FieldLog.app"
            shutil.copytree(original, app)
            self.run("/usr/bin/codesign", "--verify", "--strict", app)
            info = plistlib.loads((app / "Info.plist").read_bytes())
            entitlements = self.run("/usr/bin/codesign", "-d", "--entitlements", "-", app)
            executable = app / info["CFBundleExecutable"]
            self.run("/usr/bin/otool", "-h", executable)
            contract = {"bundleID": info["CFBundleIdentifier"], "infoPlistSHA256": file_hash(app / "Info.plist"),
                        "privacyAndTransport": {key: val for key, val in info.items()
                                                if key.endswith("UsageDescription") or key == "NSAppTransportSecurity"},
                        "entitlements": plistlib.loads(entitlements) if entitlements else {}}
            material["identity.json"] = self.bind(material, contract)
            for name, content in material.items():
                (app / "ChecklistRelease" / name).write_bytes(content)
            self.run("/usr/bin/codesign", "--force", "--sign", "-", app)
            self.run("/usr/bin/codesign", "--verify", "--strict", app)
            require(self.run("/usr/bin/codesign", "-d", "--entitlements", "-", app) == entitlements,
                    "Repackaging changed iOS entitlements")
            self.run("/usr/bin/ditto", "-c", "-k", "--keepParent", app, target)
            with zipfile.ZipFile(target) as archive:
                for name, expected in material.items():
                    require(archive.read("FieldLog.app/ChecklistRelease/" + name) == expected, "Packaged iOS identity differs")
        return contract

    def material(self, platform, public):
        if platform == "ios":
            directory = self.inputs / "FieldLog.app/ChecklistRelease"
            result = {path.name: path.read_bytes() for path in directory.iterdir()}
        else:
            prefix = "assets/ChecklistRelease/"
            with zipfile.ZipFile(self.inputs / "FieldLog-public-development.apk") as apk:
                result = {name.removeprefix(prefix): apk.read(name) for name in apk.namelist() if name.startswith(prefix)}
        app = json.loads(result["identity.json"])["application"]
        scope = {key: app[key] for key in SCOPE_FIELDS} | {"platform": platform}
        result["roots.json"] = encoded([{"key_id": f"fieldlog-{platform}-provenance-dev", "public_key": public, "scope": scope,
                                         "artifact": True, "assignment": True, "not_before_unix": 1,
                                         "revoked": False, "not_after_unix": 0}])
        return result

    @staticmethod
    def reify(target, name, material, contract):
        save(target / (name + ".permissions.json"), contract)
        destination = target / name
        destination.mkdir()
        mapping = {"storage.json": "configuration.storage.keyValue.v1.json",
                   "storage-grant.json": "grant.storage.keyValue.v1.json"}
        for filename, content in material.items():
            if filename != "port.txt":
                (destination / mapping.get(filename, filename)).write_bytes(content)
        return {"permissionsSHA256": sha(encoded(contract)), "identitySHA256": sha(material["identity.json"]),
                "archiveSHA256": file_hash(target / (name + ".native"))}

    def release(self, target, platform, name, wasm, material, key, revision, index, sequence):
        identity = json.loads(material["identity.json"])
        template = "handoff/manifest-template.json" if self.https else "manifest-template.json"
        decoded = load(self.inputs / template)["manifest"]
        if self.https:
            decoded.update(https_manifest_capabilities(identity, material))
        scope = {field: identity["application"][field] for field in SCOPE_FIELDS} | {"platform": platform}
        runtime = sha(b"mixer.runtime.identity.v2\0" + cbor(identity))
        payload = wasm.read_bytes()
        maps = encoded({"schema": 1, "sourceDigest": index, "sourceCommit": revision})
        decoded.update(scope=scope, runtime=runtime, release_id="fieldlog-" + name, source_commit=revision,
                       provenance_id="fieldlog-" + index[:32], key_id=f"fieldlog-{platform}-provenance-dev",
                       created_at_unix=int(time.time()), payload_sha256=sha(payload),
                       compressed_bytes=len(payload), expanded_bytes=len(payload), source_map_sha256=sha(maps))
        artifact = sha(cbor(decoded))
        assignment = {"schema": 3, "scope": scope, "channel": "beta", "cohort": "sha256-v1",
                      "rollout_basis_points": 10_000, "sequence": sequence, "release_id": decoded["release_id"],
                      "artifact_sha256": artifact, "runtime": runtime, "key_id": decoded["key_id"],
                      "created_at_unix": decoded["created_at_unix"]}
        for field, value in (("manifest", decoded), ("assignment", assignment)):
            domain = "artifact" if field == "manifest" else field
            signature = self.sign(key, f"mixer.{domain}.v3\0".encode() + cbor(value))
            save(target / f"{name}.{field}.json", {field: value, "signature": base64.b64encode(signature).decode()})
        (target / (name + ".wasm")).write_bytes(payload)
        (target / (name + ".source-map.json")).write_bytes(maps)
        execution = identity["execution"]
        host = {"scope": scope, "runtime": runtime, "capability_hashes": decoded["capability_hashes"],
                "protocol": 3, "guest_abi": 2, "ui_schema": 1, "state_version": 0,
                "max_payload_bytes": execution["max_payload_bytes"],
                "limits": {"fuel": execution["fuel"], "memory_bytes": execution["memory_bytes"],
                           "startup_milliseconds": execution["startup_ms"]}}
        return artifact, host

    def observe(self, target, material, platform, variant, sequence, baseline_seed=None):
        review = variant == "candidate"
        packet = self.work / f"probe-{platform}-{sequence}"
        installed = packet / "Installed"
        installed.mkdir(parents=True)
        offer = {}
        for suffix in ("manifest.json", "assignment.json", "wasm"):
            filename = f"{variant}.{suffix}"
            offer[suffix] = (target / filename).read_bytes()
            (packet / filename).write_bytes(offer[suffix])
        for name, data in material.items():
            (installed / name).write_bytes(data)

        probe = self.tools["iosProbe" if platform == "ios" else "probe"]
        for attempt in range(1, 4):
            directory = self.work / f"behavior-{platform}-{sequence}-{attempt}"
            directory.mkdir()
            if review:
                workspace = directory / "workspace"
                workspace.mkdir()
                shutil.copyfile(baseline_seed, workspace / "workspace.json")
            try:
                self.run(probe, "observe", packet, variant, directory)
            except subprocess.CalledProcessError as failure:
                # Retry only the observed missing-frame failures after the host confirms
                # owner closure. Each attempt uses the same signed offer and fresh storage.
                if platform == "android":
                    missing_frame = failure.stderr == b"FAIL: Owner closure true: Missing successor frame\n"
                else:
                    last_frame = 3 if review else 2
                    missing_frame = failure.stderr in {
                        f"FAIL: Owner retired: Missing Apple host frame {revision}\n".encode()
                        for revision in range(2, last_frame + 1)
                    }
                if attempt == 3 or failure.returncode != 1 or not missing_frame:
                    raise
                continue
            break

        runtime = load(installed / "identity.json")
        manifest = json.loads(offer["manifest.json"])["manifest"]
        assignment = json.loads(offer["assignment.json"])["assignment"]
        binding = {
            "platform": platform,
            "runtime": sha(b"mixer.runtime.identity.v2\0" + cbor(runtime)),
            "manifestSHA256": sha(offer["manifest.json"]),
            "assignmentSHA256": sha(offer["assignment.json"]),
            "payloadSHA256": sha(offer["wasm"]),
            "acceptedSequence": sequence,
        }
        expected = ["Complete task", "Confirm completion", "Reopen task"] if review else ["Complete task", "Reopen task"]
        recovery = load(directory / "recovery/state.json")
        candidate_id = recovery["healthy"]["candidateID"]
        candidate = recovery["candidates"][candidate_id]
        require(binding["runtime"] == manifest["runtime"] == assignment["runtime"]
                and recovery["acceptedSequence"] == candidate["sequence"] == assignment["sequence"] == sequence
                and runtime["platform"]["os"] == manifest["scope"]["platform"] == assignment["scope"]["platform"] == platform
                and candidate["artifactSHA256"] == sha(cbor(manifest)) == assignment["artifact_sha256"]
                and candidate["payloadSHA256"] == binding["payloadSHA256"] == manifest["payload_sha256"]
                and base64.b64decode(candidate["signedManifest"]) == offer["manifest.json"]
                and base64.b64decode(candidate["signedAssignment"]) == offer["assignment.json"],
                "Healthy recovery candidate did not retain the exact signed target offer")

        snapshots = [directory / f"workspace-{index}.json" for index in range(len(expected))]
        hashes = [file_hash(snapshot) for snapshot in snapshots]
        require(not review or hashes[0] == file_hash(baseline_seed) == hashes[1],
                "Guest did not retain the original saved task up to confirmation")
        states = [load(path) for path in snapshots]
        task = next(item["id"] for item in states[0]["tasks"] if item["title"] == "Inspect pump")
        completed = [next(item["completed"] for item in state["tasks"] if item["id"] == task) for state in states]
        initial, final = states[0], states[-1]
        event = final["outbox"][-1]
        require(completed == ([False, False, True] if review else [False, True])
                and final["revision"] == initial["revision"] + 1
                and final["outbox"][:-1] == initial["outbox"]
                and event["kind"] == "taskSaved" and event["revision"] == final["revision"] and event["recordID"] == task,
                "Persisted task completion and outbox differ from one successful commit")
        require(file_hash(directory / "workspace/workspace.json") == hashes[-1],
                "Reopened workspace differs from the observed final state")

        observed = {"offer": binding, "labels": expected, "completed": completed,
                    "revisions": [state["revision"] for state in states],
                    "outboxCounts": [len(state["outbox"]) for state in states], "workspaceSHA256": hashes,
                    "attempt": attempt}
        if platform == "ios":
            trace = directory / "host-observation.json"
            observation = load(trace)
            require(all(observation[key] == value for key, value in binding.items())
                    and observation["candidateID"] == candidate_id and observation["ownerRetired"]
                    and [frame["label"] for frame in observation["frames"]] == expected,
                    "Apple host observation does not bind the healthy signed offer")
            shutil.copyfile(trace, target / f"{variant}.host-observation.json")
            observed["hostObservationSHA256"] = file_hash(trace)
        else:
            observations = load(directory / "observations.json")
            require([item["label"] for item in observations] == expected and all(item["task"] == task for item in observations),
                    "Different Android host action sequence or selected task")
        return observed, directory, packet


def apk_contents(path):
    limit = 256 * 1_048_576
    require(0 < path.stat().st_size <= limit, "APK exceeds the stock inspector archive limit")
    materials, members = {}, {}
    names = set()
    with zipfile.ZipFile(path) as apk:
        entries = apk.infolist()
        require(len(entries) <= 4096 and sum(entry.file_size for entry in entries) <= 2 * limit,
                "APK archive exceeds the material inspection limits")
        for entry in entries:
            name = entry.filename.rstrip("/")
            require(name.casefold() not in names and all(part not in ("", ".", "..") for part in name.split("/"))
                    and "\\" not in name and not stat.S_ISLNK(entry.external_attr >> 16),
                    f"Ambiguous or unsupported APK member: {entry.filename}")
            names.add(name.casefold())
            if entry.is_dir() or re.fullmatch(r"META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))", name, re.IGNORECASE):
                continue
            if name.startswith(APK_MATERIAL):
                asset = name.removeprefix(APK_MATERIAL)
                maximum = 131_072 if asset == "identity.json" else 65_536
                require(re.fullmatch(r"[\w.-]+", asset, re.ASCII) and entry.file_size <= maximum,
                        f"Invalid release asset: {name}")
                materials[asset] = apk.read(entry)
            else:
                with apk.open(entry) as data:
                    members[name] = hashlib.file_digest(data, "sha256").hexdigest()
    require("AndroidManifest.xml" in members and "classes.dex" in members
            and any(re.fullmatch(r"lib/arm64-v8a/[^/]+\.so", name) for name in members),
            "Expected a compiled Android manifest, DEX and arm64 shared library")
    return materials, members


def https_manifest_capabilities(identity, material):
    hashes, grants = {}, []
    for capability in identity["capabilities"]:
        name = capability["id"]
        asset, schema = CAPABILITIES[name]
        configuration, grant = (material[asset + suffix] for suffix in (".json", "-grant.json"))
        require(capability == {"id": name, "schema_sha256": schema, "native_sha256": NATIVE_ABI,
                               "configuration_sha256": sha(configuration), "grants_sha256": sha(grant)},
                f"APK configuration or grant differs from its versioned descriptor: {name}")
        entry = strict_json(grant)
        require(entry.keys() == {"capability_id", "schema_sha256", "permissions", "origins", "methods", "namespaces"}
                and entry["capability_id"] == name and entry["schema_sha256"] == schema,
                f"APK grant does not bind its capability schema: {name}")
        hashes[name] = schema
        grants.append(entry)
    return {"capability_hashes": hashes,
            "capability_grants": {"schema": 1, "schema_sha256": GRANT_SCHEMA, "entries": grants}}


def https_identity(material, *, successor, application):
    identity = strict_json(material["identity.json"])
    require(identity["schema"] == 2 and identity["application"] == application
            and identity["platform"]["os"] == "android" and identity["platform"]["architecture"] == "arm64"
            and identity["build"]["configuration"] == "debug",
            "Expected the configured FieldLog Android development identity")
    require([entry["id"] for entry in identity["capabilities"]] == ([HTTP, STORAGE] if successor else [STORAGE]),
            "Expected storage on both runtimes and HTTPS only on the successor")
    require(identity["build"]["trust_roots_sha256"] == sha(material["roots.json"])
            and identity["capability_execution"]["bridge_policy_sha256"] == sha(material["bridge.json"]),
            "APK roots or bridge policy differ from the runtime descriptor")
    grants = https_manifest_capabilities(identity, material)["capability_grants"]["entries"]
    if successor:
        config = strict_json(material["http.json"])
        grant = grants[0]
        require(config == {"schema": 1, "implementation": "urlsession-normal-tls-v1",
                           "maximum_concurrent_requests": identity["capability_execution"]["maximum_requests"]},
                "Expected the installed normal-TLS HTTPS implementation")
        origins, methods = grant["origins"], grant["methods"]
        require(grant["permissions"] == ["network.https"] and grant["namespaces"] == []
                and isinstance(origins, list) and 1 <= len(origins) <= 32
                and all(isinstance(origin, str) and https_origin(origin) for origin in origins)
                and origins == sorted(set(origins))
                and isinstance(methods, list) and 1 <= len(methods) <= 6
                and all(method in {"DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"} for method in methods)
                and methods == sorted(set(methods)),
                "Expected a nonempty canonical HTTPS-only grant")
    return identity


def https_origin(origin):
    match = re.fullmatch(r"https://([a-z0-9.-]{1,253})(?::([1-9][0-9]{0,4}))?", origin)
    return bool(match and all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                              for label in match[1].split("."))
                and (match[2] is None or 0 < int(match[2]) <= 65535 and int(match[2]) != 443))


def check_https_delta(installed, proposed, *, application=ANDROID_APP):
    old_material, old_members = installed
    new_material, new_members = proposed
    old = https_identity(old_material, successor=False, application=application)
    new = https_identity(new_material, successor=True, application=application)
    require({k: v for k, v in new_material.items() if k not in {"identity.json", "http.json", "http-grant.json"}}
            == {k: v for k, v in old_material.items() if k != "identity.json"}
            and not {"http.json", "http-grant.json"} & old_material.keys(),
            "APK release assets changed outside the HTTPS capability and descriptor")
    require(old["capabilities"][0] == new["capabilities"][1] and cbor(old) != cbor(new),
            "HTTPS successor must preserve storage and change the native fingerprint")
    linked_inputs = {"link_inputs_sha256", "native_fallback_sha256"}
    require({k: v for k, v in old.items() if k not in {"capabilities", "build"}}
            == {k: v for k, v in new.items() if k not in {"capabilities", "build"}}
            and {k: v for k, v in old["build"].items() if k not in linked_inputs}
            == {k: v for k, v in new["build"].items() if k not in linked_inputs},
            "Runtime identity changed outside the HTTPS capability and native link inputs")
    require(old_members.keys() == new_members.keys(), "APK member inventory differs")
    changed = {name for name in old_members if old_members[name] != new_members[name]}
    require(changed and all(re.fullmatch(r"classes(?:[0-9]+)?\.dex|lib/[^/]+/[^/]+\.so", name) for name in changed),
            "Expected a genuine compiled DEX or library change and byte-identical manifest and resources")
    return sorted(changed)


def stock_material(material):
    aliases = {filename + suffix: kind + "." + capability + ".json"
               for capability, (filename, _) in CAPABILITIES.items()
               for suffix, kind in ((".json", "configuration"), ("-grant.json", "grant"))}
    return {aliases[name]: data for name, data in material.items() if name in aliases} | {
        name: material[name] for name in ("identity.json", "roots.json", "bridge.json")
    }


class HTTPSBuild(Build):
    https = True

    def guest_pair(self, project, record):
        handoff = self.inputs / "handoff"
        require(record["mixerRevision"] == HTTPS_BASE and record["fieldlogPublicRevision"] == FIELDLOG
                and record["apkPackage"] == ANDROID_PACKAGE and record["port"] == 41897,
                "Handoff differs from the pinned stock Mixer and FieldLog development contract")
        payloads = {variant: handoff / f"{variant}.wasm" for variant in ("baseline", "candidate")}
        hashes = {path.name: file_hash(path) for path in payloads.values()}
        require(hashes == record["guestsSHA256"] and len(set(hashes.values())) == len(hashes),
                "Expected distinct sealed baseline and confirmation payloads")

        shutil.copytree(handoff / "old/source", project)
        self.run("/usr/bin/git", "init", "-q", cwd=project)
        template = self.inputs / "project-template"
        shutil.copytree(template / "Generated", project / "Generated")
        shutil.copyfile(template / "mixer.lock", project / "mixer.lock")
        config = strict_json((template / "mixer.yml").read_bytes())
        require(config["application"] == ANDROID_PACKAGE and "android" in config["targets"],
                "Select a locked template for the maintained FieldLog Android package")
        config["targets"] = ["android"]
        config["applicationIdentifiers"] = {"android": ANDROID_PACKAGE}
        save(project / "mixer.yml", config)

        guest = project / "Integrations/InstalledGuest/SwiftGuest"
        shutil.copytree(handoff / "hydrated", guest)
        require({item.name: file_hash(item) for item in guest.iterdir()} == record["guestSourceSHA256"],
                "Hydrated guest sources differ from the sealed build")
        for source, probe in HTTPS_PROBE_SOURCES.items():
            require(file_hash(project / source) == file_hash(handoff / "probe-package" / probe)
                    == file_hash(handoff / "successor/source" / source),
                    f"Host probe must use the exact FieldLog source: {source}")
        return payloads

    @staticmethod
    def guest_build_inputs(project, record, variant, payload):
        save(project / "Integrations/InstalledGuest/SwiftGuest/build-inputs.json", {
            "sourceRevision": record["guestSourceRevision"],
            "defines": ["REQUIRE_REVIEW"] if variant == "candidate" else [],
            "payloadSHA256": file_hash(payload),
        })

    def signer(self, apk):
        output = self.run(self.tools["apksigner"], "verify", "--verbose", "--print-certs", apk).decode()
        signers = re.findall(r"^Signer #([0-9]+) certificate SHA-256 digest: ([0-9a-f]{64})$", output, re.MULTILINE)
        require(len(signers) == 1 and signers[0][0] == "1" and "Number of signers: 1" in output.splitlines()
                and re.search(r"^Verified using v[23] scheme \(.+\): true$", output, re.MULTILINE),
                "Expected a single verified modern APK signer")
        self.run(self.tools["zipalign"], "-c", "-P", "16", "4", apk)
        return signers[0][1]

    def native_pair(self, record):
        sources = {role: self.inputs / name for role, name in HTTPS_APKS.items()}
        permissions = (self.inputs / "handoff/permissions.json").read_bytes()
        require(len(permissions) <= 65_536, "APK permissions preimage exceeds the stock inspector limit")
        contract = strict_json(permissions)
        roots = (self.inputs / HTTPS_ROOTS).read_bytes()
        contents, signers = {}, {}
        for role, apk in sources.items():
            variant = HTTPS_VARIANTS[role]
            build_pin = record["apks"][variant]
            require(file_hash(apk) == self.approvals[role], f"Approved APK changed: {role}")
            signers[role] = self.signer(apk)
            require(self.android_contract(apk) == contract, f"Compiled Android manifest differs from its permissions preimage: {role}")
            contents[role] = apk_contents(apk)
            material, members = contents[role]
            identity = strict_json(material["identity.json"])
            require(material["roots.json"] == roots
                    and identity["build"]["permissions_sha256"] == sha(permissions) == build_pin["permissionsSHA256"]
                    and material["port.txt"] in (b"41897", b"41897\n"),
                    f"APK does not bind the approved roots, permissions and port: {role}")
            require(build_pin["apkSHA256"] == self.approvals[role]
                    and build_pin["signerSHA256"] == signers[role]
                    and build_pin["installedSHA256"] == {name: sha(data) for name, data in material.items()}
                    and build_pin["runtimeFingerprint"] == sha(b"mixer.runtime.identity.v2\0" + cbor(identity))
                    and members["AndroidManifest.xml"] == record["compiledManifestSHA256"],
                    f"APK does not match the independently sealed build afterimages: {role}")
        require(signers["installed"] == signers["proposed"], "The sealed APKs have different signing certificates")
        changed_members = check_https_delta(contents["installed"], contents["proposed"])
        return sources, {role: content[0] for role, content in contents.items()}, permissions, {
            "signerSHA256": signers["installed"], "changedCompiledMembers": changed_members,
            "compiledManifestSHA256": contents["installed"][1]["AndroidManifest.xml"],
        }

    def package_evidence(self, target, role, apk, material, permissions):
        archive = target / (role + ".native")
        shutil.copyfile(apk, archive)
        digest = file_hash(archive)
        require(digest == self.approvals[role], f"Packaged archive differs from the sealed APK: {role}")
        (target / (role + ".permissions.json")).write_bytes(permissions)
        destination = target / role
        destination.mkdir()
        for name, content in stock_material(material).items():
            (destination / name).write_bytes(content)
        return {"permissionsSHA256": sha(permissions), "identitySHA256": sha(material["identity.json"]),
                "archiveSHA256": digest}

    @contextmanager
    def ota_key(self, path):
        path = Path(os.path.abspath(path))
        parent = path.parent.stat()
        require(path.parent.resolve() == path.parent and parent.st_uid == os.getuid() and parent.st_mode & 0o077 == 0
                and not path.is_relative_to(self.inputs) and not path.is_relative_to(self.work),
                "Select the separately held OTA key in an operator-private directory")
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as key:
            info = os.fstat(key.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_mode & 0o077 == 0,
                    "The OTA key must be an operator-owned private regular file")
            der = self.run(self.tools["openssl"], "pkey", "-pubout", "-outform", "DER", stdin=key)
            require(len(der) == 44 and der[:-32].hex() == "302a300506032b6570032100", "Expected an Ed25519 OTA key")
            roots = [{"key_id": ANDROID_OTA_KEY_ID, "public_key": base64.b64encode(der[-32:]).decode(),
                      "scope": ANDROID_SCOPE, "artifact": True, "assignment": True, "not_before_unix": 1,
                      "revoked": False, "not_after_unix": 0}]
            pinned = (self.inputs / HTTPS_ROOTS).read_bytes()
            require(sha(pinned) == self.approvals["roots"] and strict_json(pinned) == roots,
                    "Selected OTA key does not derive the approved Android development roots")
            yield key

    def sign(self, key, content):
        if isinstance(key, Path):
            return super().sign(key, content)
        with self.temporary() as directory:
            message = directory / "message"
            message.write_bytes(content)
            key.seek(0)
            return self.run(self.tools["openssl"], "pkeyutl", "-sign", "-rawin", "-inkey", "/dev/stdin",
                            "-in", message, stdin=key)


def commit(build, project, message):
    build.run("/usr/bin/git", "add", "-f", ".", cwd=project)
    build.run("/usr/bin/git", "-c", "user.name=FieldLog local build", "-c", "user.email=local@invalid",
              "-c", "core.hooksPath=/dev/null", "commit", "-qm", message, cwd=project)
    return build.run("/usr/bin/git", "rev-parse", "HEAD", cwd=project).decode().strip()


def verify_https_refusal(build, packet, proposed, state, artifact, observed):
    recovery = state / "recovery/state.json"
    before_launch = load(recovery)
    result = build.run(build.tools["probe"], "refuse", packet, proposed, state)
    before, after = (state / f"refusal-{phase}.json" for phase in ("before", "after"))
    prior, reopened = load(before), load(recovery)
    candidate_id = prior["healthy"]["candidateID"]
    require(result.rstrip(b"\n") ==
            f"Installed runtime rejected v3.manifest.compatibility; retained candidate={candidate_id} sequence=2".encode(),
            "Probe did not report the expected installed-host refusal")
    require(before_launch == prior and before.read_bytes() == after.read_bytes()
            and prior["acceptedSequence"] == reopened["acceptedSequence"] == 2
            and candidate_id == reopened["healthy"]["candidateID"]
            and prior["candidates"][candidate_id]["artifactSHA256"] == artifact
            and reopened["candidates"][candidate_id] == prior["candidates"][candidate_id]
            and file_hash(state / "workspace/workspace.json") == observed["workspaceSHA256"][-1],
            "Refusal did not retain the exact healthy offer and completed task")
    return {"error": "v3.manifest.compatibility", "retainedSequence": 2, "retainedCandidateID": candidate_id,
            "retainedArtifactSHA256": artifact, "recoveryStateSHA256": file_hash(before),
            "workspaceSHA256": observed["workspaceSHA256"][-1]}


def verify_https_inspection(build, source, directory, trust, pins, installed_runtime, candidate_runtime, status):
    report = json.loads(build.run(build.tools["mixer"], "release", "inspect", "--directory", source,
                                  "--qualification", directory, "--producer-trust", trust,
                                  expected=0 if status == "ota-compatible" else 2, timeout=105, mixer_cli=True))
    index = load(directory / "qualification.json")
    require(report["application"] == ANDROID_PACKAGE and report["platforms"] == ["android"]
            and report["qualificationSHA256"] == file_hash(directory / "qualification.json")
            and report["sourceDigest"] == index["sourceDigest"] and report["sdkDigest"] == index["sdkDigest"]
            and report["technicalEligibility"] == status and report["policyAssessment"] == "pending-project-review"
            and report["publicationAllowed"] is False and len(report["targets"]) == 1,
            f"Stock inspector did not report the expected development assessment: {status}")
    target = report["targets"][0]
    require(target["platform"] == "android" and target["status"] == status
            and target["baselineArtifactSHA256"] == pins["baselineArtifactSHA256"]
            and target["candidateArtifactSHA256"] == pins["candidateArtifactSHA256"]
            and target["installedRuntime"] == installed_runtime and target["candidateRuntime"] == candidate_runtime
            and (status != "ota-compatible" or target["behaviorReceiptSHA256"] == pins["behaviorReceiptSHA256"]),
            "Stock Android assessment does not bind both expected native runtimes and signed offers")
    save(directory / "inspection.json", report)


def produce_https(args, output, trust):
    build = HTTPSBuild(args.settings.resolve(strict=True), output)
    require(not trust.is_relative_to(build.inputs), "Keep producer trust outside the closed input directory")
    with build.ota_key(args.ota_key) as ota_key, build.temporary() as private:
        handoff = strict_json((build.inputs / "handoff/build.json").read_bytes())
        sources, materials, permissions, native_record = build.native_pair(handoff)
        baseline, edited = (output / name for name in ("baseline-source", "review-source"))
        payloads = build.guest_pair(baseline, handoff)
        baseline_wasm, candidate_wasm = payloads["baseline"], payloads["candidate"]
        build.guest_build_inputs(baseline, handoff, "baseline", baseline_wasm)
        revisions = {"baseline": commit(build, baseline, "Pin FieldLog Android development baseline")}
        build.run("/usr/bin/git", "clone", "-q", "--no-hardlinks", baseline, edited)
        build.guest_build_inputs(edited, handoff, "candidate", candidate_wasm)
        revisions["candidate"] = commit(build, edited, "Select the sealed FieldLog confirmation build")
        reports = {"baseline": build.source(baseline), "candidate": build.source(edited)}
        require(reports["baseline"]["sourceDigest"] != reports["candidate"]["sourceDigest"]
                and reports["baseline"]["sdkDigest"] == reports["candidate"]["sdkDigest"],
                "Expected a confirmation source edit with the same stock SDK")

        producer_key = private / "producer.key"
        public = build.key(producer_key)
        producer_hash = sha(Path(__file__).read_bytes() + (Path(__file__).parent / "canonical.py").read_bytes())
        anchor = private / "producer-trust.json"
        save(anchor, {"schema": 1, "publicKey": public, "producerSHA256": producer_hash})
        toolchain = {"inputPolicySHA256": build.inventory_sha256, "approvals": build.approvals,
                     "toolSHA256": build.tool_hashes, "toolCompanionSHA256": build.companions,
                     "versions": {name: build.run(build.tools[name], option, include_stderr=True).decode().strip()
                                  for name, option in (("hostSwift", "--version"),
                                                       ("aapt2", "version"), ("apksigner", "version"),
                                                       ("openssl", "version"))},
                     "fieldLogUpstream": FIELDLOG, "revisions": revisions, "native": native_record,
                     "guestBuildSHA256": handoff["guestsSHA256"], "guestSourceRevision": handoff["guestSourceRevision"],
                     "mixerRevision": HTTPS_BASE,
                     "qualificationScope": "local development, macOS host observations for signed Android offers"}
        compatible = output / "compatible"
        https_change = output / "https-change"
        installed = compatible / "android"
        proposed = https_change / "android"
        installed.mkdir(parents=True)
        old = build.package_evidence(installed, "installed", sources["installed"], materials["installed"], permissions)
        baseline_artifact, _ = build.release(installed, "android", "baseline", baseline_wasm, materials["installed"],
                                             ota_key, revisions["baseline"], reports["baseline"]["sourceDigest"], 1)
        compatible_artifact, _ = build.release(installed, "android", "candidate", candidate_wasm, materials["installed"],
                                               ota_key, revisions["candidate"], reports["candidate"]["sourceDigest"], 2)
        baseline_observed, baseline_state, _ = build.observe(installed, materials["installed"], "android", "baseline", 1)
        seed = baseline_state / "workspace-0.json"
        edit_observed, edit_state, packet = build.observe(installed, materials["installed"], "android", "candidate", 2, seed)
        save(installed / "behavior.json", {"baseline": baseline_observed, "candidate": edit_observed})

        shutil.copytree(installed, proposed, ignore=shutil.ignore_patterns("installed.native"))
        shutil.copyfile(installed / "installed.native", proposed / "installed.native")
        require(file_hash(proposed / "installed.native") == old["archiveSHA256"], "Installed APK changed during copy")
        new = build.package_evidence(proposed, "proposed", sources["proposed"], materials["proposed"], permissions)
        https_artifact, _ = build.release(proposed, "android", "candidate", candidate_wasm, materials["proposed"],
                                          ota_key, revisions["candidate"], reports["candidate"]["sourceDigest"], 3)
        https_observed, _, _ = build.observe(proposed, materials["proposed"], "android", "candidate", 3, seed)
        require(https_observed["offer"]["payloadSHA256"] == edit_observed["offer"]["payloadSHA256"]
                and https_observed["offer"]["runtime"] != edit_observed["offer"]["runtime"]
                and all(https_observed[field] == edit_observed[field]
                        for field in ("labels", "completed", "revisions", "outboxCounts")),
                "Successor runtime did not reproduce the exact confirmation payload and behavior")
        refusal = verify_https_refusal(build, packet, proposed, edit_state, compatible_artifact, edit_observed)
        save(proposed / "behavior.json", {"baseline": baseline_observed, "candidate": https_observed,
                                           "installedRefusal": refusal})

        for directory, native, artifact, observation, status in (
                (compatible, old, compatible_artifact, edit_observed, "ota-compatible"),
                (https_change, new, https_artifact, https_observed, "store-build-required")):
            save(directory / "toolchain.json", toolchain)
            pins = {"installed": old, "proposed": native, "baselineArtifactSHA256": baseline_artifact,
                    "candidateArtifactSHA256": artifact,
                    "behaviorReceiptSHA256": file_hash(directory / "android/behavior.json")}
            index = directory / "qualification.json"
            save(index, {"schema": 3, "producerSHA256": producer_hash,
                         "toolchainSHA256": file_hash(directory / "toolchain.json"),
                         "baselineSourceDigest": reports["baseline"]["sourceDigest"],
                         "sourceDigest": reports["candidate"]["sourceDigest"], "sdkDigest": reports["candidate"]["sdkDigest"],
                         "sourceCommit": revisions["candidate"], "targets": {"android": pins},
                         "scope": {field: ANDROID_SCOPE[field] for field in SCOPE_FIELDS}})
            (directory / "qualification.ed25519").write_bytes(build.sign(producer_key, DOMAIN + index.read_bytes()))
            verify_https_inspection(build, edited, directory, anchor, pins, baseline_observed["offer"]["runtime"],
                                    observation["offer"]["runtime"], status)
        public_trust = anchor.read_bytes()
    with trust.open("xb") as handle:
        handle.write(public_trust)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inventory = commands.add_parser("pin", help="Record hashes for operator-selected inputs")
    inventory.add_argument("--inputs", type=Path, required=True)
    inventory.add_argument("--java-home", type=Path, required=True)
    inventory.add_argument("--tool", nargs=2, action="append", default=[], metavar=("NAME", "PATH"))
    inventory.add_argument("--settings", type=Path, required=True)
    produce = commands.add_parser("produce", help="Build and observe the qualification variants")
    produce.add_argument("--settings", type=Path, required=True)
    produce.add_argument("--output", type=Path, required=True, help="Fresh private run directory")
    produce.add_argument("--producer-trust", type=Path, required=True, help="New operator-owned file outside the run")
    https_inventory = commands.add_parser("pin-https", parents=[inventory], add_help=False,
                                          help="Pin the Android-only HTTPS recipe and its independent approvals")
    for name in ("installed-apk", "proposed-apk", "probe", "roots", "handoff-seal"):
        https_inventory.add_argument("--" + name + "-sha256", required=True)
    https_produce = commands.add_parser("produce-https", parents=[produce], add_help=False,
                                        help="Qualify both sealed Android APKs with the stock inspector")
    https_produce.add_argument("--ota-key", type=Path, required=True, help="Private Ed25519 key for the approved APK roots")
    args = parser.parse_args()
    os.umask(0o077)
    if args.command in ("pin", "pin-https"):
        pin(args, https=args.command == "pin-https")
        return

    output = args.output.resolve()
    trust = args.producer_trust.resolve()
    require(not trust.is_relative_to(output) and not os.path.lexists(args.producer_trust) and
            trust.parent.is_dir(), "Choose a new trust file outside the run in an existing directory")
    if args.command == "produce-https":
        produce_https(args, output, trust)
        return
    build = Build(args.settings.resolve(strict=True), output)
    baseline, edited, permission = (build.work / name for name in ("baseline-source", "review-source", "permission-source"))
    build.project(baseline)
    probe_package = build.inputs / "probe-package"
    for source, probe in FIELDLOG_STORAGE.items():
        require(file_hash(baseline / source) == file_hash(probe_package / probe), f"Host probe must use the FieldLog source: {source}")
    revisions = {"baseline": commit(build, baseline, "Pin FieldLog local build baseline")}
    def successor(source, destination):
        # Local file transport, no remote.
        build.run("/usr/bin/git", "clone", "-q", "--no-hardlinks", source, destination)
    successor(baseline, edited)
    build.edit_review(edited)
    revisions["candidate"] = commit(build, edited, "Require confirmation before committing completion")
    successor(edited, permission)
    manifest = permission / "Integrations/GeneratedReport/Platforms/Android/AndroidManifest.xml"
    original = manifest.read_text()
    require(original.count("  <application") == 1 and "android.permission.CAMERA" not in original,
            "Expected a single unmodified FieldLog application")
    manifest.write_text(original.replace("  <application", '  <uses-permission android:name="android.permission.CAMERA" />\n  <application'))
    revisions["permission"] = commit(build, permission, "Request Android camera permission")
    reports = {key: build.source(path) for key, path in zip(revisions, (baseline, edited, permission))}
    guest_root = "Integrations/InstalledGuest/SwiftGuest"
    for entry in (edited / guest_root).iterdir():
        require(file_hash(entry) == file_hash(permission / guest_root / entry.name),
                "Permission control changed a guest compiler input")
    # Keep the exact observed guest bytes when isolating a native-only change.
    payloads = {platform: {
        "baseline": build.guest(baseline, f"{platform}-baseline", platform),
        "candidate": build.guest(edited, f"{platform}-review", platform),
    } for platform in PLATFORMS}
    require(all(file_hash(payloads["ios"][variant]) != file_hash(payloads["android"][variant])
                for variant in ("baseline", "candidate")), "FieldLog guest branches emitted identical payloads")
    require(all(file_hash(guest["baseline"]) != file_hash(guest["candidate"]) for guest in payloads.values()),
            "Confirmation edit did not change the compiled guest")
    build_record = {"inputPolicySHA256": build.inventory_sha256, "toolSHA256": build.tool_hashes,
                    "toolCompanionSHA256": build.companions,
                    "versions": {name: build.run(build.tools[name], option, include_stderr=True).decode().strip()
                                 for name, option in (("hostSwift", "--version"), ("swiftc", "--version"), ("wasm-ld", "--version"),
                                                      ("clang", "--version"), ("aapt2", "version"))},
                    "fieldLogUpstream": FIELDLOG, "revisions": revisions,
                    "qualificationScope": "local development, host owned VM behavior"}
    positive, negative = build.work / "compatible", build.work / "permission-change"
    positive.mkdir()
    negative.mkdir()
    result = {"positive": {}, "negative": {}, "hosts": {}, "packageIds": {}}
    input_apk = build.inputs / "FieldLog-public-development.apk"
    build.run(build.tools["apksigner"], "verify", "--verbose", input_apk)
    installed_android_contract = build.android_contract(input_apk)
    with build.temporary() as private:
        sign_key = private / "producer.key"
        producer_public = build.key(sign_key)
        producer_hash = sha(Path(__file__).read_bytes() + (Path(__file__).parent / "canonical.py").read_bytes())
        apk_key = private / "android.p12"
        apk_env = {"LOCAL_APK_PASSWORD": os.urandom(24).hex()}
        build.run(build.tools["keytool"], "-genkeypair", "-storetype", "PKCS12", "-keystore", apk_key,
                  "-alias", "fieldlog-local", "-storepass:env", "LOCAL_APK_PASSWORD", "-keypass:env", "LOCAL_APK_PASSWORD",
                  "-keyalg", "EC", "-groupname", "secp256r1", "-validity", "1", "-dname", "CN=FieldLog Local",
                  env=apk_env)
        for platform in PLATFORMS:
            target = positive / platform
            target.mkdir()
            key = private / (platform + ".key")
            material = build.material(platform, build.key(key))
            if platform == "ios":
                contract = build.native_ios(target / "installed.native", material)
            else:
                contract = build.native_android(baseline, target / "installed.native", material, apk_key, apk_env,
                                                installed_android_contract)
            native = build.reify(target, "installed", material, contract)
            guests = payloads[platform]
            baseline_artifact, host = build.release(target, platform, "baseline", guests["baseline"], material,
                                                    key, revisions["baseline"], reports["baseline"]["sourceDigest"], 1)
            edit_artifact, _ = build.release(target, platform, "candidate", guests["candidate"], material,
                                            key, revisions["candidate"], reports["candidate"]["sourceDigest"], 2)
            result["positive"][platform] = {"installed": native, "proposed": native,
                                            "baselineArtifactSHA256": baseline_artifact, "candidateArtifactSHA256": edit_artifact}
            result["hosts"][platform] = host
            result["packageIds"][platform] = contract["bundleID"]
            baseline_behavior, baseline_state, _ = build.observe(target, material, platform, "baseline", 1)
            seed = baseline_state / "workspace-0.json"
            edit_behavior, edit_state, packet = build.observe(target, material, platform, "candidate", 2, seed)
            save(target / "behavior.json", {"baseline": baseline_behavior, "candidate": edit_behavior})
            changed = negative / platform
            # Copy small evidence; archives are cloned or regenerated by the producer.
            shutil.copytree(target, changed, ignore=shutil.ignore_patterns("installed.native"))
            build.run("/bin/cp", "-c", target / "installed.native", changed / "installed.native")
            new_material = dict(material)
            proposed = native
            if platform == "android":
                new_contract = build.native_android(permission, changed / "proposed.native", new_material,
                                                    apk_key, apk_env, installed_android_contract, camera_control=True)
                proposed = build.reify(changed, "proposed", new_material, new_contract)
            artifact, new_host = build.release(changed, platform, "candidate", guests["candidate"], new_material,
                                               key, revisions["permission"], reports["permission"]["sourceDigest"], 3)
            result["negative"][platform] = {"installed": native, "proposed": proposed,
                                            "baselineArtifactSHA256": baseline_artifact, "candidateArtifactSHA256": artifact}
            result.setdefault("proposedHosts", {})[platform] = new_host
            proposed_behavior, _, _ = build.observe(changed, new_material, platform, "candidate", 3, seed)
            save(changed / "behavior.json", {"baseline": baseline_behavior, "candidate": proposed_behavior})
            if platform == "android":
                refusal = build.run(build.tools["probe"], "refuse", packet, changed, edit_state)
                before, after = (edit_state / f"refusal-{name}.json" for name in ("before", "after"))
                require(file_hash(before) == file_hash(after), "Refusal changed the durable recovery state")
                prior, reopened = load(before), load(edit_state / "recovery/state.json")
                candidate_id = prior["healthy"]["candidateID"]
                require(refusal.rstrip(b"\n") ==
                        f"Installed runtime rejected v3.manifest.compatibility; retained candidate={candidate_id} sequence=2".encode(),
                        "Probe did not report the expected installed-host refusal")
                require(prior["acceptedSequence"] == reopened["acceptedSequence"] == 2
                        and candidate_id == reopened["healthy"]["candidateID"]
                        and prior["candidates"][candidate_id]["artifactSHA256"] == edit_artifact
                        and reopened["candidates"][candidate_id] == prior["candidates"][candidate_id]
                        and file_hash(edit_state / "workspace/workspace.json") == edit_behavior["workspaceSHA256"][-1],
                        "Refusal did not retain the exact healthy offer and completed task")
                assignment = load(changed / "candidate.assignment.json")["assignment"]
                assignment["runtime"] = host["runtime"]
                signature = build.sign(key, b"mixer.assignment.v3\0" + cbor(assignment))
                save(changed / "cross-runtime.assignment.json", {
                    "assignment": assignment, "signature": base64.b64encode(signature).decode()})
        for directory, pins, variant in ((positive, result["positive"], "candidate"),
                                          (negative, result["negative"], "permission")):
            save(directory / "toolchain.json", build_record)
            for platform, target in pins.items():
                observed = directory / platform / "behavior.json"
                target["behaviorReceiptSHA256"] = file_hash(observed)
            report = reports[variant]
            save(directory / "qualification.json", {
                "schema": 3, "producerSHA256": producer_hash, "toolchainSHA256": file_hash(directory / "toolchain.json"),
                "baselineSourceDigest": reports["baseline"]["sourceDigest"], "sourceDigest": report["sourceDigest"],
                "sdkDigest": report["sdkDigest"], "sourceCommit": revisions[variant], "targets": pins,
                "scope": {key: result["hosts"]["ios"]["scope"][key] for key in SCOPE_FIELDS},
            })
            message = DOMAIN + (directory / "qualification.json").read_bytes()
            (directory / "qualification.ed25519").write_bytes(build.sign(sign_key, message))
    save(build.work / "build-result.json", result)
    with trust.open("xb") as handle:
        handle.write(encoded({"schema": 1, "publicKey": producer_public, "producerSHA256": producer_hash}))


if __name__ == "__main__":
    main()
