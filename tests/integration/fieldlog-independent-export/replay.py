#!/usr/bin/env python3
"""Build the maintained FieldLog Android export using the public v74 SDK."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile


REPO = Path(__file__).resolve().parents[3]
V74 = "44aecbeb6a82a4a93321cff6a8ab86c5aa421900"
PAIR23 = "735ecec14e10e2dfed1e58a122c3fab08e569bef"
FIELDLOG = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
FIELDLOG_URL = "https://github.com/snowdamiz/fieldlog.git"
PATCHES = ("public-build.patch", "draft-fields.patch", "photo-return.patch", "report-return.patch")
PLATFORM_LOCK = "Platforms/Android/Package.resolved"
SDK_LOCK = "Generated/MixerSDK/Package.resolved"
APP = "dev.fieldlog.generatedr90"


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory(root):
    """Capture export bytes, executable bits, and empty directories."""
    entries = {}
    for base, dirs, files in os.walk(root):
        if Path(base) == root and ".mixer" in dirs:
            dirs.remove(".mixer")
        for name in sorted(dirs + files):
            item = Path(base) / name
            require(not item.is_symlink(), f"Unexpected export symlink: {item}")
            entries[item.relative_to(root).as_posix()] = (
                None if item.is_dir() else [digest(item), bool(item.stat().st_mode & 0o111)]
            )
    return entries


def map_digest(entries):
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


def group_absent(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


class Replay:
    def __init__(self, scratch, args, receipt):
        self.scratch = scratch
        self.args = args
        self.receipt = receipt
        self.hold = False
        self.logs = scratch / "logs"
        self.logs.mkdir()

    def environment(self, root, developer):
        paths = ("home", "tmp", "clang-cache", "module-cache", "xdg-cache")
        for path in paths:
            (root / path).mkdir(parents=True)
        env = {
            key: os.environ[key] for key in
            ("ANDROID_HOME", "MIXER_JDK", "MIXER_SWIFT", "MIXER_SWIFT_SDKS_PATH", "MIXER_ANDROID_ARTIFACT_PATH")
        }
        env.update(
            DEVELOPER_DIR=str(developer),
            PATH=os.pathsep.join(dict.fromkeys((str(Path(sys.executable).parent), "/usr/bin", "/bin", "/usr/sbin", "/sbin"))),
            HOME=str(root / "home"), CFFIXED_USER_HOME=str(root / "home"),
            TMPDIR=str(root / "tmp") + "/", XDG_CACHE_HOME=str(root / "xdg-cache"),
            CLANG_MODULE_CACHE_PATH=str(root / "clang-cache"),
            SWIFTPM_MODULECACHE_OVERRIDE=str(root / "module-cache"),
            GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
            PYTHONDONTWRITEBYTECODE="1", LC_ALL="C",
        )
        return env

    def run(self, label, argv, cwd, env, timeout=60, nested=0, recipe_output=None):
        """Bound each command and check the groups reserved by the public CLI."""
        argv = list(map(str, argv))
        log = self.logs / f"{label}.log"
        row = {"argv": [arg.replace(str(self.scratch), "$work") for arg in argv],
               "cwd": str(cwd).replace(str(self.scratch), "$work")}
        self.receipt["commands"][label] = row
        env = env.copy()
        if nested:
            temporary = Path(env["TMPDIR"]) / label
            temporary.mkdir()
            env["TMPDIR"] = str(temporary) + "/"
        print(label, flush=True)
        with log.open("wb") as output:
            self.hold = True
            child = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                     stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            row["pgid"] = child.pid
            began = time.monotonic()
            try:
                row["exit"] = child.wait(timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                row["interrupted"] = True
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                row["exit"] = child.wait(timeout=10)
            row["seconds"] = round(time.monotonic() - began, 2)
            row["groupAbsent"] = group_absent(child.pid)
        require(row["groupAbsent"], f"{label} has unresolved custody for PGID {child.pid}")
        if recipe_output is not None:
            recipe_receipt = recipe_output / ".fieldlog-build/commands.json"
            if not recipe_receipt.is_file():
                # On failure the recipe leaves commands.json beside the output.
                candidates = list(recipe_output.parent.glob(f"{recipe_output.name}-logs-*/commands.json"))
                require(len(candidates) == 1, f"{label} has no unique nested recipe receipt")
                recipe_receipt = candidates[0]
            rows = json.loads(recipe_receipt.read_bytes())
            require(len(rows) == 1 and rows[0].get("ownedGroupAbsent") is True,
                    f"{label} has unresolved FieldLog create custody")
            row["recipeCreate"] = {"sha256": digest(recipe_receipt), "exit": rows[0]["exitCode"]}
        if nested:
            records = sorted(temporary.glob("mixer-command-receipts-*/command-*/receipt.json"))
            require(len(records) >= nested and not any(temporary.glob("mixer-command-receipts-*/command-*/HOLD.json")),
                    f"{label} has incomplete nested Mixer receipts")
            facts = ("terminalCustody", "directChildReaped", "ownedGroupAbsent", "stdoutEOF", "stderrEOF", "descriptorsClosed")
            observed = [json.loads(path.read_bytes()) for path in records]
            require(all(item.get("state") == "TERMINAL" and all(item.get(fact) is True for fact in facts)
                        for item in observed), f"{label} has unresolved nested Mixer custody")
            row["nested"] = [{"command": Path(item["command"][0]).name, "exit": item["exitCode"],
                              "receiptSHA256": digest(path)} for item, path in zip(observed, records)]
        self.hold = False
        row["outputSHA256"] = digest(log)
        if row["exit"] or row.get("interrupted"):
            with log.open("rb") as stream:
                stream.seek(max(0, log.stat().st_size - 4096))
                row["outputTail"] = stream.read().decode(errors="replace").replace(str(self.scratch), "$work").strip()
            raise RuntimeError(f"{label} failed with exit {row['exit']}\n{row['outputTail']}")
        return log

    def checkout(self, label, url, revision, paths, env, parent):
        target = parent / label
        self.run(f"{label}-clone", ["git", "clone", "--depth=1", "--filter=blob:none", "--no-checkout",
                                   "--no-tags", url, target], parent, env, timeout=120)
        self.run(f"{label}-fetch", ["git", "fetch", "--depth=1", "--no-tags", "origin", revision], target, env, timeout=120)
        if paths:
            self.run(f"{label}-sparse", ["git", "sparse-checkout", "set", *paths], target, env)
        self.run(f"{label}-checkout", ["git", "checkout", "--detach", revision], target, env, timeout=120)
        identity = self.run(f"{label}-identity", ["git", "rev-parse", "HEAD", "HEAD^{tree}"], target, env).read_text().splitlines()
        require(identity[0] == revision, f"Wrong revision for {label}")
        self.receipt["sources"][label] = {"revision": revision, "tree": identity[1]}
        return target

    def build_cli(self, label, checkout, env, prep):
        build = prep / f"{label}-build"
        lock = checkout / "cli/Package.resolved"
        before = digest(lock)
        command = ["/usr/bin/swift", "build", "--package-path", checkout / "cli", "--scratch-path", build,
                   "--cache-path", build / "cache", "--config-path", build / "config", "--security-path", build / "security",
                   "--manifest-cache", "local", "--disable-dependency-cache", "--only-use-versions-from-resolved-file"]
        self.run(f"{label}-build", [*command, "--product", "mixer"], prep, env, timeout=300)
        binary = Path(self.run(f"{label}-bin-path", [*command, "--show-bin-path"], prep, env).read_text().strip()) / "mixer"
        require(digest(lock) == before and binary.is_file(), f"{label} build changed its lock or failed to produce mixer")
        self.receipt["sources"][label].update(cliSHA256=digest(binary), cliLockSHA256=before)
        return binary

    def execute(self):
        prep = self.scratch / "Prepare"
        build_ci = self.scratch / "Build" / "CI"
        host = self.environment(prep / "tool-state", self.args.host_developer_dir)
        cross = {**host, "DEVELOPER_DIR": os.environ["DEVELOPER_DIR"]}
        ci = self.environment(build_ci / "tool-state", os.environ["DEVELOPER_DIR"])
        self.receipt["environment"]["hostSwift"] = self.run("host-swift", ["/usr/bin/swift", "--version"], prep, host).read_text().strip()
        self.receipt["environment"]["androidXcode"] = self.run("android-xcode", ["xcodebuild", "-version"], build_ci, ci).read_text().strip()
        fieldlog = self.checkout("fieldlog", FIELDLOG_URL, FIELDLOG, (), host, prep)
        require(self.receipt["sources"]["fieldlog"]["tree"] == "1b62520f35c7e57a01b568291078686574f627c4", "FieldLog tree differs from the maintained baseline")
        for patch in PATCHES:
            fixture = prep / patch
            source = f"{V74}:verification/fieldlog-pair23/{patch}"
            log = self.run(f"read-{patch}", ["git", "show", source], REPO, host)
            shutil.copyfile(log, fixture)
            self.run(f"apply-{patch}", ["git", "apply", "--index", fixture], fieldlog, host)
            self.receipt["patches"][patch] = digest(fixture)
        self.receipt["sources"]["fieldlog"]["patchedTree"] = self.run("fieldlog-patched-tree", ["git", "write-tree"], fieldlog, host).read_text().strip()

        paths = ("cli", "sdk", "updates", "runtime-identity", "native/android")
        pair23 = self.checkout("pair23", "https://github.com/snowdamiz/mixer.git", PAIR23, paths, host, prep)
        v74 = prep / "v74"
        v74.mkdir()
        tree = self.run("v74-identity", ["git", "rev-parse", f"{V74}^{{tree}}"], REPO, host).read_text().strip()
        require(tree == "4ac68f788cc806672eede50a842cb153c7199496", "Public v74 tree differs")
        self.receipt["sources"]["v74"] = {"revision": V74, "tree": tree}
        archive = prep / "v74.tar"
        self.run("v74-archive", ["git", "archive", "--format=tar", "-o", archive, V74, *paths], REPO, host)
        self.run("v74-unpack", ["tar", "-xf", archive, "-C", v74], prep, host)
        old = self.build_cli("pair23", pair23, host, prep)
        current = self.build_cli("v74", v74, host, prep)

        original = prep / "FieldLog-pair23"
        upgraded = prep / "FieldLog-v74"
        export = prep / "Export"
        recipe = fieldlog / "Integrations/GeneratedReport/scripts/build-android.py"
        self.run("fieldlog-prepare", [sys.executable, recipe, "--mixer", old, "--sdk-checkout", pair23,
                                      "--android-adapter-path", pair23 / "native/android", "--output", original, "--prepare-only"],
                 prep, cross, timeout=660, nested=2, recipe_output=original)
        (original / ".fieldlog-build").rename(prep / "fieldlog-recipe-logs")
        original_inputs = inventory(original)
        lock = original_inputs[PLATFORM_LOCK][0]
        require(lock == "abf619c18799ea2dbb169494bcb928b47c95d2cc5e70e433328f6380ae035e80", "FieldLog platform lock differs from the maintained lock")
        self.run("v74-upgrade", [current, "upgrade", upgraded, "--directory", original, "--sdk-path", v74 / "sdk",
                                  "--android-adapter-path", v74 / "native/android"], prep, cross, timeout=180, nested=1)
        require(inventory(original) == original_inputs, "Upgrade changed the prepared FieldLog source")
        self.run("v74-export", [current, "export", export, "--directory", upgraded], prep, cross, timeout=120, nested=1)
        exported = inventory(export)
        require(exported == inventory(upgraded), "Export differs from the upgraded FieldLog project")
        app_inputs = {name: item for name, item in original_inputs.items()
                      if not name.startswith("Generated/") and name not in {"Generated", "mixer.lock"}}
        require(app_inputs == {name: item for name, item in exported.items() if name in app_inputs}, "Upgrade changed app-owned files")
        require(exported[PLATFORM_LOCK][0] == lock and
                json.loads((export / PLATFORM_LOCK).read_bytes())["pins"] == json.loads((export / SDK_LOCK).read_bytes())["pins"],
                "v74 bundled SDK pins differ from FieldLog's platform lock")
        self.receipt["export"] = {
            "entries": len(exported), "treeSHA256": map_digest(exported), "appTreeSHA256": map_digest(app_inputs),
            "mixerLockSHA256": exported["mixer.lock"][0], "platformLockSHA256": lock,
            "sdkPackageLockSHA256": exported[SDK_LOCK][0], "driverSHA256": exported["Generated/MixerAndroid/android-build.py"][0],
            "profile": json.loads((export / "mixer.lock").read_bytes())["android"]["profile"],
        }
        destination = build_ci / "FieldLogGenerated"
        export.rename(destination)
        shutil.rmtree(prep)
        require(not prep.exists() and not (destination / ".mixer").exists() and shutil.which("mixer", path=ci["PATH"]) is None,
                "Original inputs, Mixer CLI, or build output reachable in the CI replay")
        self.receipt["export"].update(relocatedTo="Build/CI/FieldLogGenerated", preparationTreeRemovedBeforeBuild=True, priorBuildOutput=False)

        self.run("independent-build", [sys.executable, "Generated/MixerAndroid/android-build.py", "build", destination],
                 destination, ci, timeout=600)
        require(inventory(destination) == exported, "Build changed exported app source or locks")
        self.verify_apk(destination, ci, exported)

    def verify_apk(self, project, env, exported):
        output = project / ".mixer/android-build"
        apk = output / "FieldLogGenerated-unsigned.apk"
        receipt_path = output / "build-receipt.json"
        report = json.loads(receipt_path.read_bytes())
        apk_hash = digest(apk)
        require(report["apk_sha256"] == apk_hash and report["apk_bytes"] == apk.stat().st_size and
                report["source_tree_sha256"] == report["source_tree_after_sha256"] and
                report["platform_dependency_lock"]["sha256"] == exported[PLATFORM_LOCK][0] and
                report["source_profile"] == self.receipt["export"]["profile"], "Build report does not bind the exported inputs and APK")
        tools = Path(env["ANDROID_HOME"]) / "build-tools/37.0.0"
        self.run("apk-alignment", [tools / "zipalign", "-c", "-P", "16", "4", apk], project, env)
        badging = self.run("apk-badging", [tools / "aapt2", "dump", "badging", apk], project, env).read_text().splitlines()
        fields = [line for line in badging if line.startswith(("package:", "launchable-activity:", "native-code:", "minSdkVersion:", "targetSdkVersion:"))]
        expected = (f"package: name='{APP}'", f"launchable-activity: name='{APP}.androidhost.PublicActivity'",
                    "native-code: 'arm64-v8a'", "minSdkVersion:'36'", "targetSdkVersion:'37'")
        require(len(fields) == len(expected) and all(any(line == prefix or line.startswith(prefix + " ") for line in fields)
                                                    for prefix in expected), f"Unexpected FieldLog APK badging: {fields}")
        with zipfile.ZipFile(apk) as bundle:
            entries = bundle.namelist()
            require(len(entries) == len(set(entries)) and bundle.testzip() is None, "APK ZIP failed integrity checks")
            require(not any(name.upper().startswith("META-INF/") for name in entries), "APK contains signature entries")
            with apk.open("rb") as file:
                file.seek(bundle.start_dir - 16)
                require(file.read(16) != b"APK Sig Block 42", "APK contains a signing block")
            libraries = [name for name in entries if name.startswith("lib/") and name.endswith(".so")]
            for name in libraries:
                with bundle.open(name) as library:
                    header = library.read(20)
                require(name.startswith("lib/arm64-v8a/") and header[:6] == b"\x7fELF\x02\x01" and header[18:20] == b"\xb7\x00",
                        f"APK library is not AArch64 ELF64: {name}")
            require({"lib/arm64-v8a/libAppAndroid.so", "lib/arm64-v8a/libmixer_public_android_jni.so", "classes.dex"}.issubset(entries)
                    and any(name.startswith("third-party-notices/") for name in entries), "Expected app, JNI, DEX, or runtime notices missing")
        self.receipt["environment"]["androidToolchain"] = report["toolchain"]
        self.receipt["artifact"] = {
            "sha256": apk_hash, "bytes": apk.stat().st_size, "unsigned": True, "badging": fields,
            "apkEntries": len(entries), "arm64ELFLibraries": len(libraries), "apkAlignmentKiB": 16,
            "buildReceiptSHA256": digest(receipt_path), "driverSourceTreeSHA256": report["source_tree_sha256"],
            "completedToolCommands": len(report["commands"]), "sourceAndLocksUnchanged": True,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True, help="New path for the compact JSON receipt")
    parser.add_argument("--host-developer-dir", type=Path, default=Path("/Applications/Xcode.app/Contents/Developer"))
    args = parser.parse_args()
    with args.receipt.open("x") as destination:
        receipt = {"schema": "mixer.local-development-evidence.v1", "scope": "FieldLog §16.3/W15 independent Android export build only",
                   "recordedAtUTC": datetime.now(timezone.utc).isoformat(), "status": "blocked", "sources": {}, "patches": {},
                   "commands": {}, "environment": {"os": platform.platform(), "python": sys.version.split()[0]}, "deviceOperations": 0}
        root = REPO / "verification/local"
        root.mkdir(exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="fieldlog-v74-export.", dir=root)).resolve()
        replay = Replay(scratch, args, receipt)
        print(f"Build scratch: {scratch}", flush=True)
        try:
            replay.execute()
            receipt["status"] = "passed"
        except (KeyError, OSError, RuntimeError, ValueError, subprocess.SubprocessError, KeyboardInterrupt) as error:
            receipt["failure"] = str(error).replace(str(scratch), "$work")
            print(error, file=sys.stderr)
        finally:
            if not replay.hold:
                shutil.rmtree(scratch)
            receipt["cleanup"] = {"commandCustodyResolved": not replay.hold, "scratchRemoved": not scratch.exists()}
            if replay.hold:
                receipt["cleanup"]["retainedScratch"] = str(scratch)
            json.dump(receipt, destination, indent=2)
            destination.write("\n")
    return 0 if receipt["status"] == "passed" and receipt["cleanup"]["scratchRemoved"] else 1


if __name__ == "__main__":
    sys.exit(main())
