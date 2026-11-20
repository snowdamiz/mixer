"""Drive the installed retained CLI against a disposable Pair24 materialization."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import uuid


PROFILE = "MIXER_WORKER_NATIVE_PROFILE"
PYTHON = "MIXER_WORKER_ANDROID_PYTHON"
HOST_SWIFT = "MIXER_WORKER_ANDROID_HOST_SWIFT"
DEVELOPER = "MIXER_WORKER_ANDROID_DEVELOPER_DIR"
CONTROL = "MIXER_WORKER_COMMAND_CONTROL"
ASN1 = "MIXER_WORKER_ANDROID_SWIFT_ASN1_MIRROR"
CRYPTO = "MIXER_WORKER_ANDROID_SWIFT_CRYPTO_MIRROR"
DRIVER = "Generated/MixerAndroid/android-build.py"
LOCK = "mixer.lock"
PLATFORM_LOCK = "Platforms/Android/Package.resolved"
PREFIX = "mixer-command-receipts-"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def absent(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    return False


class ObservedCLI(subprocess.Popen):
    def __del__(self):
        # A timeout is left for the owner. Disable implicit polling or reaping.
        pass


class Case:
    def __init__(self, scratch, label, descriptor, fixture_python):
        self.root = scratch / label
        self.root.mkdir(mode=0o700)
        self.project = self.root / "project"
        self.project.mkdir(mode=0o700)
        self.tmp = self.root / "tmp"
        self.tmp.mkdir(mode=0o700)
        self.output = self.root / "native"
        source = Path(descriptor["source_root"])
        for relative, expected in descriptor["files"].items():
            content = (source / relative).read_bytes()
            require(digest(content) == expected, f"Pair24 input changed: {relative}")
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.lock = json.loads((self.project / LOCK).read_bytes())
        self.env = {
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "TMPDIR": str(self.tmp),
            "DEVELOPER_DIR": os.environ["MIXER_TEST_HOST_DEVELOPER_DIR"],
            CONTROL: "1", PROFILE: "unsigned-android-local-v1",
            PYTHON: self.lock["android"]["toolchain"]["tools"]["python"]["path"],
            HOST_SWIFT: os.environ["MIXER_TEST_ANDROID_HOST_SWIFT"],
            DEVELOPER: os.environ["MIXER_TEST_ANDROID_DEVELOPER_DIR"],
            ASN1: descriptor["mirrors"]["swift-asn1"]["mirror_url"],
            CRYPTO: descriptor["mirrors"]["swift-crypto"]["mirror_url"],
        }
        if fixture_python is not None:
            self.env[PYTHON] = str(fixture_python)
            self.lock["android"]["toolchain"]["tools"]["python"] = {
                "path": str(fixture_python), "sha256": digest(fixture_python.read_bytes())
            }
            self.write_lock()

    def write_lock(self):
        (self.project / LOCK).write_text(json.dumps(self.lock) + "\n")

    def tree(self):
        return {p.relative_to(self.project).as_posix(): digest(p.read_bytes())
                for p in self.project.rglob("*") if p.is_file()}

    def run(self, mixer, *, platform="android", retained=True, cancel_running=False, expect_ack=True):
        before = self.tree()
        args = [str(mixer), "build", "--platform", platform, "--directory", str(self.project)]
        if retained:
            args += ["--output", str(self.output)]
        with (self.root / "stdout").open("xb") as stdout, (self.root / "stderr").open("xb") as stderr:
            child = ObservedCLI(args, cwd=self.project, env=self.env, stdin=subprocess.DEVNULL,
                                stdout=stdout, stderr=stderr, start_new_session=True)
            (self.root / "launch.json").write_text(json.dumps({"pid": child.pid, "argv": args}))
            if cancel_running:
                deadline = time.monotonic() + 10
                while not list(self.tmp.glob(f"{PREFIX}*/mixer-verify-*/tmp/fixture-ready")):
                    require(not (self.tmp / "cli-closed").exists(), "CLI closed before fixture readiness")
                    require(time.monotonic() < deadline, "Fixture never reached readiness")
                    time.sleep(0.01)
                require(not (self.tmp / "cli-closed").exists(), "CLI acknowledged a live command")
                self.cancel()
            code = child.wait(timeout=20)
        require(absent(child.pid), f"CLI group absence unconfirmed: {child.pid}")
        ack = self.tmp / "cli-closed"
        receipts = []
        if not expect_ack:
            require(not ack.exists(), "Standalone build acknowledged worker closure")
        else:
            root_name = ack.read_text()
            require(root_name.startswith(PREFIX) and
                    root_name == PREFIX + str(uuid.UUID(root_name[len(PREFIX):])).upper(), "Bad acknowledgment")
            receipt_dirs = sorted((self.tmp / root_name).glob("command-*"))
            for directory in receipt_dirs:
                require(not (directory / "HOLD.json").exists(), "Command custody is uncertain")
                receipt = json.loads((directory / "receipt.json").read_bytes())
                require(receipt["schema"] == "mixer.owned-command.2" and receipt["state"] == "TERMINAL" and
                        receipt["terminalNS"] > 0 and all(receipt[k] is True for k in
                        ("released", "terminalCustody", "directChildReaped", "stdoutEOF", "stderrEOF",
                         "descriptorsClosed", "ownedGroupAbsent")), f"Nonterminal custody: {directory}")
                receipts.append(receipt)
        require(self.tree() == before, f"CLI changed the project tree: {self.root}")
        require(not (self.output / "android-build-v1.json").exists(), "Failed build published a manifest")
        require(code == 1, f"Expected positive CLI error exit, got {code}")
        return json.loads((self.root / "stdout").read_bytes()), receipts

    def cancel(self):
        marker = self.tmp / "cancel-requested"
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)

    def driver(self, receipts):
        require(len(receipts) == 2, f"Expected a Swift probe and a driver receipt, got {len(receipts)}")
        probe, receipt = sorted(receipts, key=lambda item: item["runtimeStartedNS"])
        require(probe["command"] == [self.env[HOST_SWIFT], "--version"] and probe["exitCode"] == 0
                and probe.get("directory") is None and probe["retainedInputDirectories"] == []
                and probe["terminalNS"] < receipt["runtimeStartedNS"],
                "The pinned Swift probe must close before the driver starts")
        receipt_root = self.tmp / (self.tmp / "cli-closed").read_text()
        snapshot = Path(receipt["command"][-1]).parent
        suffix = snapshot.name.removeprefix("mixer-verify-")
        require(snapshot == receipt_root / ("mixer-verify-" + str(uuid.UUID(suffix)).upper()), "Bad snapshot path")
        require(receipt["command"] == [self.env[PYTHON], "-I", "-B", "-S", str(self.project / DRIVER),
                "build-retained-v1", str(self.project), str(snapshot / "android-build")], "Wrong driver argv")
        require(receipt["directory"] == str(self.project) and
                receipt["retainedInputDirectories"] == [str(snapshot), str(self.project)], "Bad command custody paths")
        require(not snapshot.exists(), "Terminal snapshot was retained")
        return receipt, snapshot


def check(mixer, scratch, descriptor):
    python = scratch / "fixture-python"
    python.write_text(f"#!{Path(sys.executable).resolve()} -I\n" + """import json
import os
from pathlib import Path
import subprocess
import sys
import time
print("fixture-environment=" + json.dumps(dict(os.environ), sort_keys=True), flush=True)
case = Path(sys.argv[-2]).parent.name
if case == "cancel-running":
    Path(os.environ["TMPDIR"], "fixture-ready").touch()
    time.sleep(60)
elif case == "driver-failure" and os.environ["GIT_ALLOW_PROTOCOL"] == "file":
    refs = []
    for package, tag in [("swift-asn1", "1.7.3"), ("swift-crypto", "5.0.3")]:
        ref = f"refs/tags/{tag}"
        peeled = ref + "^{}"
        command = ["/usr/bin/git", "ls-remote", f"https://github.com/apple/{package}.git", ref, peeled]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        commits = {name: sha for sha, name in map(str.split, result.stdout.splitlines())}
        refs.append(commits[peeled] if peeled in commits else commits[ref])
    print("mirror-revisions=" + json.dumps(refs), flush=True)
sys.exit(23)
""")
    python.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    passed = []

    def case(name, interpreter=python):
        return Case(scratch, name, descriptor, interpreter)

    for label, field, value in [
        ("missing-profile", PROFILE, None), ("wrong-profile", PROFILE, "unsigned-ios-simulator-v1"),
        ("missing-python", PYTHON, None), ("relative-python", PYTHON, "python3"),
        ("missing-host-swift", HOST_SWIFT, None), ("relative-host-swift", HOST_SWIFT, "swift"),
        ("missing-developer-dir", DEVELOPER, None), ("relative-developer-dir", DEVELOPER, "Developer"),
        ("unpinned-python", PYTHON, "/usr/bin/python3"), ("missing-mirror", CRYPTO, None),
        ("remote-mirror", ASN1, "https://github.com/apple/swift-asn1.git"),
        ("remote-file-authority", ASN1, "file://remote/var/mirror.git"),
        ("malformed-mirror", ASN1, "file:///var/%00mirror.git"),
        ("missing-control", CONTROL, None),
    ]:
        trial = case(label)
        if value is None:
            trial.env.pop(field)
        else:
            trial.env[field] = value
        result, receipts = trial.run(mixer, expect_ack=field != CONTROL)
        require(result["code"] == "android.output-worker" and not receipts and not trial.output.exists(), label)
        passed.append(label)

    for label in ["duplicate-mirror", "swapped-mirrors", "invalid-python-digest", "unsupported-resource", "missing-platform-lock",
                  "different-platform-lock", "changed-driver"]:
        trial = case(label)
        if label == "duplicate-mirror":
            trial.env[CRYPTO] = trial.env[ASN1]
        elif label == "swapped-mirrors":
            trial.env[ASN1], trial.env[CRYPTO] = trial.env[CRYPTO], trial.env[ASN1]
        elif label == "invalid-python-digest":
            trial.lock["android"]["toolchain"]["tools"]["python"]["sha256"] = "0" * 64
            trial.write_lock()
        elif label == "missing-platform-lock":
            (trial.project / PLATFORM_LOCK).unlink()
        elif label == "unsupported-resource":
            resources = trial.project / "Resources"
            resources.mkdir()
            (resources / "app.txt").write_text("unsupported")
        else:
            changed = trial.project / (PLATFORM_LOCK if label == "different-platform-lock" else DRIVER)
            changed.write_bytes(changed.read_bytes() + b"\n")
        _, receipts = trial.run(mixer)
        require(not receipts and not trial.output.exists(), label)
        passed.append(label)

    trial = case("driver-failure")
    trial.env.update(GIT_CONFIG_COUNT="99", GIT_ALLOW_PROTOCOL="https",
                     GIT_SSH_COMMAND="unused", HOME="/unowned-home", MIXER_SWIFT="/unowned-swift")
    result, receipts = trial.run(mixer)
    receipt, snapshot = trial.driver(receipts)
    require(receipt["exitCode"] == 23 and "stopReason" not in receipt, "Wrong driver failure")
    lines = result["message"].splitlines()
    environment = json.loads(next(line.removeprefix("fixture-environment=") for line in lines
                                  if line.startswith("fixture-environment=")))
    require(environment["HOME"] == environment["CFFIXED_USER_HOME"] == str(snapshot / "home") and
            environment["TMPDIR"] == str(snapshot / "tmp") and environment["CLANG_MODULE_CACHE_PATH"] ==
            environment["SWIFTPM_MODULECACHE_OVERRIDE"] == str(snapshot / "module-cache"),
            "Driver state escaped its snapshot")
    expected_git = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
                    "GIT_ALLOW_PROTOCOL": "file", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_CONFIG_COUNT": "2",
                    "GIT_CONFIG_KEY_0": f"url.{trial.env[ASN1]}.insteadOf",
                    "GIT_CONFIG_KEY_1": f"url.{trial.env[CRYPTO]}.insteadOf",
                    "GIT_CONFIG_VALUE_0": "https://github.com/apple/swift-asn1.git",
                    "GIT_CONFIG_VALUE_1": "https://github.com/apple/swift-crypto.git"}
    require({k: v for k, v in environment.items() if k.startswith("GIT_")} == expected_git, "Wrong Git configuration")
    require(environment["MIXER_SWIFT"] == trial.lock["android"]["toolchain"]["tools"]["swift"]["path"] and
            environment["DEVELOPER_DIR"] == trial.env[DEVELOPER] and
            not any(key.startswith("MIXER_WORKER_") for key in environment), "Worker environment leaked into driver")
    revisions = json.loads(next(line.removeprefix("mirror-revisions=") for line in lines
                                if line.startswith("mirror-revisions=")))
    require(revisions == [descriptor["mirrors"][name]["revision"] for name in ("swift-asn1", "swift-crypto")],
            "Local Git returned different dependency revisions")
    passed.append("driver-failure-and-environment")

    trial = case("host-swift-lock-drift")
    trial.lock["swiftVersion"] += "-unexpected"
    trial.write_lock()
    result, receipts = trial.run(mixer)
    require(result["code"] == "lock.toolchain-drift" and len(receipts) == 1
            and receipts[0]["command"] == [trial.env[HOST_SWIFT], "--version"]
            and receipts[0]["exitCode"] == 0 and not trial.output.exists(),
            "Host Swift drift must refuse before the driver and store")
    passed.append("host-swift-lock-drift")

    trial = case("real-driver-preflight", None)
    unavailable = str(scratch / "no-android-swift")
    trial.lock["android"]["toolchain"]["tools"]["swift"]["path"] = unavailable
    trial.write_lock()
    result, receipts = trial.run(mixer)
    receipt, _ = trial.driver(receipts)
    require(receipt["exitCode"] == 1 and "Android local build error:" in result["message"]
            and unavailable in result["message"], "Generated driver did not reach Android tool inspection")
    passed.append("real-driver-preflight")

    before = case("cancel-before")
    before.cancel()
    result, receipts = before.run(mixer)
    require(result["code"] == "process.cancelled" and not receipts, "Prelaunch cancel started a command")
    passed.append("cancel-before")
    running = case("cancel-running")
    result, receipts = running.run(mixer, cancel_running=True)
    receipt, _ = running.driver(receipts)
    require(result["code"] == "process.cancelled" and receipt["exitCode"] == 15 and
            receipt["stopReason"] == "cancelled" and receipt["groupTerminateSent"] is True and
            receipt["groupKillSent"] is False, "Running cancel did not close with SIGTERM")
    passed.append("cancel-running")

    for label, platform, retained in [("standalone-retained", "android", True),
                                      ("ordinary-android", "android", False), ("retained-ios", "ios", True)]:
        trial = case(label)
        (trial.project / "mixer.yml").unlink()
        for key in (PROFILE, PYTHON, HOST_SWIFT, DEVELOPER, ASN1, CRYPTO):
            trial.env.pop(key)
        if platform == "android":
            trial.env.pop(CONTROL)
        result, receipts = trial.run(mixer, platform=platform, retained=retained, expect_ack=platform == "ios")
        require(not receipts and result["code"] != "android.output-worker", label)
        require(trial.output.exists() == retained, label)
        passed.append(label)
    return passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mixer", "prepared", "scratch"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    args.scratch.mkdir(mode=0o700)
    descriptor_bytes = args.prepared.read_bytes()
    checks = check(args.mixer.resolve(strict=True), args.scratch.resolve(strict=True), json.loads(descriptor_bytes))
    print(json.dumps({"checks": checks, "preparedSHA256": digest(descriptor_bytes)}, indent=2))
