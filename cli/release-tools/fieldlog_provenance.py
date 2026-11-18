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


def pin(args):
    settings = args.settings.resolve()
    inputs = args.inputs.resolve(strict=True)
    tools = dict(args.tool)
    require(len(tools) == len(args.tool) and tools.keys() == TOOLS,
            f"Supply each tool once: {', '.join(sorted(TOOLS))}")
    tools = {name: Path(os.path.abspath(path)) for name, path in tools.items()}
    java_home = args.java_home.resolve(strict=True)
    inventory = {
        "schema": 1,
        "inputs": relative(inputs, settings),
        "files": {name: file_hash(inputs / name) for name in input_files(inputs)},
        "javaHome": relative(java_home, settings),
        "tools": {name: {"path": relative(path, settings), "sha256": file_hash(path)}
                  for name, path in tools.items()},
        "toolCompanions": tool_companions(tools, java_home),
    }
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
    def __init__(self, settings_path, work):
        inventory = settings_path.read_bytes()
        settings = json.loads(inventory)
        require(settings["schema"] == 1 and settings["tools"].keys() == TOOLS,
                "Unsupported FieldLog input inventory")
        self.inventory_sha256 = sha(inventory)

        def resolve(value):
            return (settings_path.parent / value).resolve(strict=True)

        self.inputs = resolve(settings["inputs"])
        require(set(input_files(self.inputs)) == settings["files"].keys(), "Pinned input file set changed")
        for name, digest in settings["files"].items():
            require(file_hash(self.inputs / name) == digest, f"Pinned input bytes changed: {name}")

        # Keep argv[0] as swiftc even when the bytes are provided by swift-driver.
        self.tools = {name: Path(os.path.abspath(settings_path.parent / item["path"]))
                      for name, item in settings["tools"].items()}
        self.tool_hashes = {name: item["sha256"] for name, item in settings["tools"].items()}
        for name, path in self.tools.items():
            require(file_hash(path) == self.tool_hashes[name], f"Pinned tool bytes changed: {name}")
            require(name == "android.jar" or os.access(path, os.X_OK), f"Tool is not executable: {name}")

        java_home = resolve(settings["javaHome"])
        require((java_home / "bin/keytool").resolve() == self.tools["keytool"].resolve() and
                os.access(java_home / "bin/java", os.X_OK), "JAVA_HOME must match the pinned keytool")
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
        config["applicationIdentifiers"] = {"ios": "dev.mixer.fieldlog", "android": "dev.fieldlog.generatedr90"}
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

    def android_contract(self, apk):
        data = self.run(self.tools["aapt2"], "dump", "permissions", apk).decode()
        package = re.findall(r"^package: (\S+)$", data, re.MULTILINE)
        require(package == ["dev.fieldlog.generatedr90"], "Android output has a different installed package ID")
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
        decoded = load(self.inputs / "manifest-template.json")["manifest"]
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


def commit(build, project, message):
    build.run("/usr/bin/git", "add", "-f", ".", cwd=project)
    build.run("/usr/bin/git", "-c", "user.name=FieldLog local build", "-c", "user.email=local@invalid",
              "-c", "core.hooksPath=/dev/null", "commit", "-qm", message, cwd=project)
    return build.run("/usr/bin/git", "rev-parse", "HEAD", cwd=project).decode().strip()


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
    args = parser.parse_args()
    os.umask(0o077)
    if args.command == "pin":
        pin(args)
        return

    output = args.output.resolve()
    trust = args.producer_trust.resolve()
    require(not trust.is_relative_to(output) and not os.path.lexists(args.producer_trust) and
            trust.parent.is_dir(), "Choose a new trust file outside the run in an existing directory")
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
