"""Replay two Foundation surface checks against the exact W07/L03 source baseline."""

import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import sys
import tempfile
import time
from datetime import datetime, timezone

FIXTURE = Path(__file__).resolve().parent
REPO = FIXTURE.parents[2]
MIXER = "1e2de0130d001ef9ada0001b59f9ae8b7f67b72a"
MIXER_TREE = "6218549dff3d59b06251d10b20e257f13f565140"
FIELDLOG = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
FIELDLOG_TREE = "e39a5ea393076ca3f64b00648bf86f350ccf03dd"
EVIDENCE = "verification/receipts"
COMBINED = f"{EVIDENCE}/fieldlog-d2-combined-85e6fbe3-compiler-inputs.json"
ORDINARY = f"{EVIDENCE}/fieldlog-d2-ordinary-screens-e39a5ea3"
SWIFT_ROOT = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr"
XCODE = "/Applications/Xcode_26.6.app/Contents/Developer"
GIT = "/usr/bin/git"
LIMIT = 2 * 1024**3
WALL_SECONDS = 600
TARGET = "wasm32-unknown-none-wasm"
NATIVE = "arm64-apple-macosx26.0"
INDICES = ("0", "1", "2", "3")
REORDERED_INDICES = ("3", "0", "3", "1", "2")
PRESENTATION_PATH = "ios/FieldLog/ProjectDetail.swift"
PRESENTATION_LINE = 128
PRESENTATION_CALL = "Text(entry.occurredAt, format: .dateTime.month(.abbreviated).day()).font("
PRESENTATION_SHA256 = "324351b80ba3598fb28dd9419c9769ec68444218e5f639de38f33fe60a736400"
PRESENTATION_BLOB = "f2dda688882d61d05e8d530a639e818128d1f248"
EPOCH_EXPECTED = b"-978307200.5\n-978307200.0\n0.0\n725934600.25\n"
PRESENTATION_EXPECTED = b"Jan 1\n1 janv.\nDec 31\nMar 5\n"


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def identity(path):
    with path.open("rb") as stream:
        return {"bytes": path.stat().st_size, "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


class Campaign:
    def __init__(self, scratch, journal):
        self.scratch = scratch
        self.journal = journal
        self.started = time.monotonic()
        self.deadline = self.started + WALL_SECONDS - 10
        self.record = {
            "schema": 1, "status": "running", "scope": "W07/L03 §7.3 synthetic macOS and Embedded compiler check",
            "startedUTC": datetime.now(timezone.utc).isoformat(),
            "mixerRevision": MIXER, "mixerTree": MIXER_TREE,
            "host": {"machine": platform.machine(), "macOS": platform.mac_ver()[0]},
            "limits": {"wallSeconds": WALL_SECONDS, "allocatedScratchBytes": LIMIT, "maxObservedAllocatedBytes": 0},
            "scratch": {"path": str(scratch)}, "commands": [],
        }
        self.active = None
        for name in ("home", "tmp", "native-cache", "embedded-cache"):
            (scratch / name).mkdir()
        self.env = {
            "PATH": f"{XCODE}/Toolchains/XcodeDefault.xctoolchain/usr/bin:/usr/bin:/bin",
            "HOME": str(scratch / "home"), "CFFIXED_USER_HOME": str(scratch / "home"),
            "TMPDIR": str(scratch / "tmp"), "DEVELOPER_DIR": XCODE,
            "LANG": "en_US.UTF-8", "TZ": "UTC", "SWIFT_BACKTRACE": "enable=no",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
            "CLANG_MODULE_CACHE_PATH": str(scratch / "native-cache"),
        }

    def save(self):
        snapshot = json.dumps(self.record, ensure_ascii=False, indent=2) + "\n"
        self.journal.seek(0)
        self.journal.write(snapshot)
        self.journal.truncate()
        self.journal.flush()
        return snapshot

    def allocation(self):
        paths = [self.scratch, *self.scratch.rglob("*")]
        blocks = sum(path.lstat().st_blocks for path in paths if os.path.lexists(path))
        observed = blocks * 512
        limits = self.record["limits"]
        limits["maxObservedAllocatedBytes"] = max(observed, limits["maxObservedAllocatedBytes"])
        return observed

    def run(self, label, *args, allowed=(0,), cwd=None, bound=40, raw=False):
        check(self.active is None and time.monotonic() < self.deadline, "campaign unavailable")
        stdout, stderr = (self.scratch / f"{label}.{suffix}" for suffix in ("out", "err"))
        entry = {"name": label, "argv": list(map(str, args)), "cwd": str(cwd or self.scratch),
                 "timeoutSeconds": bound, "custody": "UNKNOWN"}
        self.record["commands"].append(entry)
        self.active = entry
        self.save()
        actions = [(os.POSIX_SPAWN_OPEN, 0, "/dev/null", os.O_RDONLY, 0)]
        for fd, path in enumerate((stdout, stderr), 1):
            actions.append((os.POSIX_SPAWN_OPEN, fd, str(path), os.O_WRONLY | os.O_EXCL | os.O_CREAT, 0o600))
        # An exec launcher makes cwd and per-file output limits local to this command.
        launcher = [sys.executable, "-I", "-B", "-c",
                    "import os, resource, sys; os.chdir(sys.argv[1]); "
                    "resource.setrlimit(resource.RLIMIT_FSIZE,(67108864,67108864)); "
                    "resource.setrlimit(resource.RLIMIT_CORE,(0,0)); "
                    "os.execv(sys.argv[2],sys.argv[2:])", str(cwd or self.scratch), *entry["argv"]]
        pid = os.posix_spawn(sys.executable, launcher, self.env, setpgroup=0, file_actions=actions)
        entry["pidPgid"] = pid
        self.save()
        stop = min(self.deadline, time.monotonic() + bound)
        next_sample = 0.0
        interrupted = None
        while True:
            child, status = os.waitpid(pid, os.WNOHANG)
            if child:
                entry["exit"] = os.waitstatus_to_exitcode(status)
                break
            now = time.monotonic()
            if now >= next_sample and not interrupted:
                next_sample = now + 0.25
                if self.allocation() >= LIMIT // 2:
                    interrupted = "scratch allocation stop threshold"
            if now >= stop or interrupted:
                interrupted = interrupted or "deadline"
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    self.reap_killed(pid, entry)
                finally:
                    entry["interruption"] = interrupted
                break
            time.sleep(0.02)

        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            entry["custody"] = "direct-child-reaped/group-absent (ESRCH)"
            self.active = None
        check(self.active is None, f"{label}: process group closure unproven")
        entry.update(stdout=identity(stdout), stderr=identity(stderr))
        for name, path in (("stdout", stdout), ("stderr", stderr)):
            if (name == "stderr" or raw) and path.stat().st_size <= 16384:
                entry[name]["text"] = path.read_bytes().decode("utf-8", errors="replace")
        self.save()
        check(self.allocation() < LIMIT, "scratch allocation exceeded")
        check(not interrupted and entry["exit"] in allowed, f"{label}: unexpected exit {entry['exit']}")
        return stdout, stderr, entry["exit"]

    @staticmethod
    def reap_killed(pid, entry):
        end = time.monotonic() + 3
        while time.monotonic() < end:
            child, status = os.waitpid(pid, os.WNOHANG)
            if child:
                entry["exit"] = os.waitstatus_to_exitcode(status)
                return
            time.sleep(0.02)
        raise RuntimeError("direct child reap unproven after deadline")

    def mixer_blob(self, label, path, revision=MIXER):
        return self.run(label, GIT, "-C", REPO, "show", f"{revision}:{path}")[0]

    def reconstruct(self):
        public_mixer = self.run(
            "mixer-public-commit", "/usr/bin/curl", "--fail", "--silent", "--show-error",
            "--max-time", "20", "--max-filesize", "1000000",
            f"https://api.github.com/repos/snowdamiz/mixer/git/commits/{MIXER}",
        )[0]
        public = json.loads(public_mixer.read_bytes())
        check(public["sha"] == MIXER and public["tree"]["sha"] == MIXER_TREE, "wrong public Mixer commit")
        self.record["publicMixer"] = {"revision": public["sha"], "tree": public["tree"]["sha"],
                                      "response": identity(public_mixer)}
        local_tree = self.run("mixer-tree", GIT, "-C", REPO, "rev-parse", f"{MIXER}^{{tree}}", raw=True)[0]
        check(local_tree.read_text().strip() == MIXER_TREE, "wrong Mixer baseline")
        source = self.record["fieldLog"] = {"publicRevision": FIELDLOG, "ordinaryTree": FIELDLOG_TREE, "patches": []}
        recipe = json.loads(self.mixer_blob("fieldlog-recipe", COMBINED).read_bytes())["fieldLog"]
        prior = json.loads(self.mixer_blob("ordinary-recipe", f"{ORDINARY}.json").read_bytes())
        archive = self.scratch / "fieldlog.tgz"
        self.run("fieldlog-archive", "/usr/bin/curl", "--fail", "--silent", "--show-error",
                 "--location", "--max-time", "20", "--max-filesize", "20000000",
                 f"https://codeload.github.com/snowdamiz/fieldlog/tar.gz/{FIELDLOG}", "-o", archive)
        source["publicArchive"] = identity(archive)
        check(source["publicArchive"]["sha256"] == recipe["publicTarSHA256"], "wrong FieldLog archive")
        app = self.scratch / "fieldlog"
        app.mkdir()
        self.run("fieldlog-extract", "/usr/bin/tar", "-xzf", archive, "--strip-components", "1", "-C", app)

        def git(label, *args):
            return self.run(label, GIT, "-C", app, *args, raw=True)[0].read_text().strip()

        def tree(label, expected):
            check(git(label, "write-tree") == expected, f"{label}: source tree mismatch")

        git("fieldlog-init", "init", "-q")
        git("fieldlog-add", "-c", "core.autocrlf=false", "add", "-f", "--", ".")
        tree("fieldlog-base-tree", recipe["publicTree"])
        material = recipe["orderedMaterial"] + [
            {"path": f"{EVIDENCE}/fieldlog-d2-checklist-move-source.patch",
             "objectRevision": MIXER, "sha256": prior["source"]["reviewedMoveSHA256"],
             "resultingTree": prior["source"]["baselineTree"]},
            {"path": f"{ORDINARY}.patch", "objectRevision": MIXER,
             "sha256": prior["artifacts"]["productPatch"]["sha256"], "resultingTree": FIELDLOG_TREE},
        ]
        for index, item in enumerate(material):
            label = f"fieldlog-material-{index:02}"
            path = item["path"]
            patch = self.mixer_blob(label, path, item["objectRevision"])
            digest = identity(patch)["sha256"]
            check(digest == item["sha256"], f"{path}: material hash mismatch")
            source["patches"].append({"path": path, "revision": item["objectRevision"], "sha256": digest})
            if path.endswith("/EntrySaveDecision.swift"):
                dest = "Integrations/GeneratedReport/Sources/FieldLogFeatures/EntrySaveDecision.swift"
                shutil.copyfile(patch, app / dest)
                git(f"{label}-add", "add", "--", dest)
            else:
                git(f"{label}-apply", "apply", "--index", str(patch))
            if item.get("resultingTree"):
                tree(f"{label}-tree", item["resultingTree"])
        source["verifiedTree"] = FIELDLOG_TREE
        return app

    def tools(self):
        check(platform.machine() == "arm64" and sys.platform == "darwin", "requires native arm64 macOS")
        self.record["host"]["build"] = self.run("macos-build", "/usr/bin/sw_vers", "-buildVersion", raw=True)[0].read_text().strip()
        swift = SWIFT_ROOT / "bin/swiftc"
        version = self.run("swift-version", swift, "--version", raw=True)[0].read_text()
        check("Swift version 6.3.3 (swift-6.3.3-RELEASE)" in version, "wrong Swift toolchain")
        xcode = self.run("xcode-version", "/usr/bin/xcodebuild", "-version", raw=True)[0].read_text()
        check(xcode.splitlines()[0] == "Xcode 26.6", "wrong Xcode")
        sdk = Path(self.run("native-sdk", "/usr/bin/xcrun", "--no-cache", "--sdk", "macosx",
                            "--show-sdk-path", raw=True)[0].read_text().strip())
        self.record["toolchain"] = {
            "swift": version.strip(), "xcode": xcode.strip(), "nativeTarget": NATIVE, "embeddedTarget": TARGET,
            "swiftDriver": identity(swift), "swiftFrontend": identity(SWIFT_ROOT / "bin/swift-frontend"),
            "nativeSDKSettings": identity(sdk / "SDKSettings.json"),
            "embeddedSwiftModule": identity(SWIFT_ROOT / "lib/swift/embedded/Swift.swiftmodule" / f"{TARGET}.swiftmodule"),
        }
        return swift, sdk

    def embedded(self, swift, name, sources, failed_import=None):
        obj = self.scratch / f"{name}.o"
        wasm = obj.with_suffix(".wasm")
        check(not obj.exists() and not wasm.exists(), "Embedded outputs pre-exist")
        stdout, stderr, code = self.run(name, swift, "-target", TARGET,
              "-enable-experimental-feature", "Embedded", "-whole-module-optimization", "-Osize",
              "-parse-as-library", "-Xfrontend", "-disable-stack-protector", "-swift-version", "6",
              "-module-cache-path", self.scratch / "embedded-cache", "-emit-object",
              *sources, "-o", obj, allowed=(0, 1) if failed_import else (0,), raw=True)
        result = {"exit": code, "objectEmitted": obj.exists(), "wasmEmitted": wasm.exists()}
        self.record.setdefault("embedded", {})[name] = result
        if failed_import:
            diagnostic = stderr.read_text()
            expected = f"{failed_import}:1:8: error: no such module 'Foundation'"
            check(code == 1 and not obj.exists() and not wasm.exists() and expected in diagnostic,
                  f"{name}: expected source-located Foundation import refusal before emission")
            result["diagnostic"] = diagnostic
        else:
            check(obj.exists() and obj.stat().st_size > 0 and obj.read_bytes().startswith(b"\0asm"),
                  "Foundation-free control is missing a Wasm object")
            result["object"] = identity(obj)

    def native(self, swift, sdk, name, sources, expected):
        executable = self.scratch / name
        self.run(f"{name}-build", swift, "-target", NATIVE, "-sdk", sdk,
                 "-swift-version", "6", "-parse-as-library", "-module-cache-path",
                 self.scratch / "native-cache", *sources, "-o", executable, bound=90)
        readbacks = []
        lines = expected.splitlines(keepends=True)
        for variant, indices in (("ordered", INDICES), ("reordered", REORDERED_INDICES)):
            observed = self.run(f"{name}-{variant}", executable, *indices, raw=True)[0].read_bytes()
            check(observed == b"".join(lines[int(index)] for index in indices),
                  f"{name}-{variant} readback differs: {observed!r}")
            readbacks.append({"indices": indices, "expectedAndObserved": observed.decode("utf-8")})
        self.record.setdefault("native", {})[name] = {"binary": identity(executable), "readbacks": readbacks}

    def execute(self):
        app = self.reconstruct()
        call_site = app / PRESENTATION_PATH
        call_identity = identity(call_site)
        check(call_identity["sha256"] == PRESENTATION_SHA256, "FieldLog source blob changed")
        call = call_site.read_text().splitlines()[PRESENTATION_LINE - 1].strip()
        check(call == PRESENTATION_CALL, "FieldLog style call changed")
        self.record["fieldLog"]["callSite"] = {
            "path": PRESENTATION_PATH, "line": PRESENTATION_LINE, "source": call,
            "gitBlob": PRESENTATION_BLOB, **call_identity,
        }
        swift, sdk = self.tools()
        cases = FIXTURE / "Cases.swift"
        self.record["fixtures"] = {
            name: identity(FIXTURE / name) for name in (
                "Cases.swift", "Control.swift", "Epoch.swift", "EpochHost.swift",
                "Presentation.swift", "PresentationHost.swift", "replay.py",
            )
        }
        self.embedded(swift, "foundation-free-embedded", [cases, FIXTURE / "Control.swift"])
        for name, stem, expected in (("epoch", "Epoch", EPOCH_EXPECTED),
                                      ("presentation", "Presentation", PRESENTATION_EXPECTED)):
            source = FIXTURE / f"{stem}.swift"
            self.native(swift, sdk, name, [cases, source, FIXTURE / f"{stem}Host.swift"], expected)
            self.embedded(swift, f"{name}-embedded", [cases, source], source)


def publish(output, file, snapshot):
    reserved = os.fstat(file.fileno())

    def verify_destination():
        try:
            current = output.lstat()
        except FileNotFoundError:
            raise RuntimeError(f"receipt destination changed: {output}") from None
        check(os.path.samestat(current, reserved), f"receipt destination changed: {output}")

    verify_destination()
    file.write(snapshot)
    file.flush()
    os.fsync(file.fileno())
    verify_destination()


def run_campaign(scratch, output, file):
    with (scratch / "journal.json").open("x", encoding="utf-8") as journal:
        campaign = Campaign(scratch, journal)
        campaign.save()
        try:
            campaign.execute()
            campaign.record["status"] = "pass"
        except BaseException as error:
            campaign.record.update(status="incomplete", error=str(error))
            raise
        finally:
            if campaign.active is None:
                campaign.allocation()
                campaign.record["scratch"]["cleanup"] = "after-receipt-publication"
            else:
                campaign.record["scratch"]["hold"] = campaign.active
            campaign.record["elapsedSeconds"] = round(time.monotonic() - campaign.started, 3)
            try:
                publish(output, file, campaign.save())
            except (OSError, RuntimeError):
                print(f"Receipt publication failed. Scratch retained at {scratch}", file=sys.stderr)
                raise
            if campaign.active is None:
                shutil.rmtree(scratch)


def main():
    check(len(sys.argv) == 2, "usage: replay.py NEW_RECEIPT.json")
    requested = Path(sys.argv[1])
    output = requested.parent.resolve(strict=True) / requested.name
    with output.open("x", encoding="utf-8") as file:
        scratch = Path(tempfile.mkdtemp(prefix="foundation-date-", dir=output.parent))
        run_campaign(scratch, output, file)


if __name__ == "__main__":
    main()
