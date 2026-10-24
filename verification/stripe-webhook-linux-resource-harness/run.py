#!/usr/bin/env python3
"""Private exact-profile controller. Default is read-only capability preflight.

No runtime result is manufactured from this module's host tests. The controller
never enters the role cgroup or namespace. All retained output is reconstructed.
"""
import argparse
import array
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import selectors
import signal
import socket
import stat
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT = ROOT / "verification/stripe-webhook-resource-ingress-contract"
PROFILE_SHA = "65adc0ed279a6acd9ba13af2445294b2e6bea3016aa91d29dbadbbc6642a3aec"
SOURCE_SHA = "1b2f03d474f825a6265e0a10f9baf2adda62dffe6c747542207f32753b4df997"
SELECTION_SHA = "4762d82aea2d8974fddca73bc16407ef2ec78899fa05760f3e16ed31b95df5d0"
INDEX_AMENDMENT_SHA = "b18a57f8d8a8596b32e0d429caa3b1b202e4bbf706d35971f419e7213b06028e"
CASES = tuple(f"R{i:02}" for i in range(1, 19))
REASONS = frozenset(json.loads((CONTRACT / "profile.json").read_text())["reasonEnum"])
HARNESS_FILES = ("run.py", "role.exs", "fault_helper.c", "control_nif.c")
# A driver is not a completed matrix row. These rows have bounded drivers for
# independent replay; comprehensive rows remain explicitly unavailable.
EXECUTABLE_CASES = frozenset(("R03", "R09", "R10", "R11", "R12", "R13", "R15"))
FIXED_ENV = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
             "ERL_CRASH_DUMP": "/dev/null", "ERL_CRASH_DUMP_SECONDS": "0"}


class Refusal(Exception):
    def __init__(self, reason, unavailable=False):
        assert reason in REASONS
        self.reason, self.unavailable = reason, unavailable
        super().__init__(reason)


def require(value, reason, unavailable=False):
    if not value:
        raise Refusal(reason, unavailable)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def load(path):
    # Duplicated JSON keys and nonfinite constants are never a closed schema.
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, "profile_invalid")
            result[k] = v
        return result
    def invalid(_):
        raise Refusal("profile_invalid")
    try:
        raw = Path(path).read_bytes()
        require(len(raw) <= 4 * 1024 * 1024, "profile_invalid")
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except (OSError, ValueError, UnicodeError):
        raise Refusal("profile_invalid") from None


def same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(same(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same(a, b) for a, b in zip(actual, expected))
    return actual == expected


def profile(path):
    require(sha(CONTRACT / "profile.json") == PROFILE_SHA, "source_mismatch")
    expected = load(CONTRACT / "profile.json")
    require(same(load(path), expected), "profile_invalid")
    selection_path = ROOT / "verification/stripe-webhook-resource-ingress-root-review/selection.json"
    require(sha(selection_path) == SELECTION_SHA, "source_mismatch")
    selection = load(selection_path)
    require(selection["status"] == "private-linux-profile-selected-for-implementation-runtime-not-accepted",
            "profile_invalid")
    for name, expected_sha in selection["bindings"].items():
        require(sha(ROOT / name) == expected_sha, "source_mismatch")
    return expected


def source_inputs(live=True):
    value = load(CONTRACT / "source-bindings.json")
    require(digest(value["baselineInputs"]) == SOURCE_SHA, "source_mismatch")
    entries = {**value["baselineInputs"], **value["additionalInputs"]}
    amendment_path = ROOT / "verification/stripe-webhook-resource-ingress-root-review/mutable-execution-index-amendment.json"
    require(sha(amendment_path) == INDEX_AMENDMENT_SHA, "source_mismatch")
    amendment = load(amendment_path)
    require(amendment["mutablePath"] == "PLAN.md" and amendment["selectedContractSHA256"] == SELECTION_SHA,
            "source_mismatch")
    if live:
        for name, expected_sha in entries.items():
            if name == "PLAN.md":
                continue  # selected metadata-only exception, recorded separately
            p = ROOT / name
            require(not p.is_symlink() and p.resolve().is_relative_to(ROOT) and sha(p) == expected_sha,
                    "source_mismatch")
    return entries


def harness_digest():
    return digest({name: sha(HERE / name) for name in HARNESS_FILES})


def linux_capabilities():
    # No commands, daemon access, namespace creation, or resource probes here.
    linux = sys.platform == "linux"
    required_caps = sum(1 << bit for bit in (5, 6, 7, 8, 12, 18, 19, 21))
    observed_caps = 0
    genuine_cgroup = False
    if linux:
        try:
            fields = dict(row.split(":", 1) for row in Path("/proc/self/status").read_text().splitlines() if ":" in row)
            observed_caps = int(fields["CapEff"].strip(), 16)
            genuine_cgroup = any(row.split()[3:5] == ["/", "/sys/fs/cgroup"] and " - cgroup2 " in row
                                 for row in Path("/proc/self/mountinfo").read_text().splitlines())
        except (OSError, KeyError, ValueError):
            pass
    return {"schema": 1, "system": platform.system(), "machine": platform.machine(),
            "python": platform.python_version(), "linux": linux,
            "cgroupV2": genuine_cgroup and Path("/sys/fs/cgroup/cgroup.controllers").is_file(),
            "rootLauncherAvailable": linux and os.geteuid() == 0 and observed_caps & required_caps == required_caps,
            "requiredSetupCapabilityMask": required_caps, "observedSetupCapabilityMask": observed_caps,
            "roleEnvironment": FIXED_ENV, "inheritedRoleFDs": [0, 1, 2, 3],
            "capabilityProbeStartedRole": False, "controllerInStressCgroup": False,
            "executionIndex": {"path": "PLAN.md", "historicalSHA256":
                               load(CONTRACT / "source-bindings.json")["additionalInputs"]["PLAN.md"],
                               "currentSHA256": sha(ROOT / "PLAN.md"), "amendmentSHA256": INDEX_AMENDMENT_SHA}}


def safe_relative(name):
    return isinstance(name, str) and bool(name) and not Path(name).is_absolute() and all(
        p not in ("", ".", "..") for p in name.split("/"))


def release_manifest(rootfs):
    rootfs = Path(rootfs)
    require(rootfs.is_absolute() and not rootfs.is_symlink() and rootfs.is_dir(), "source_mismatch")
    require(rootfs.resolve() == rootfs, "source_mismatch")
    require(rootfs.stat().st_uid == 0 and not rootfs.stat().st_mode & 0o6022, "ownership")
    m = load(rootfs / "release-manifest.json")
    fields = {"schema", "platform", "architecture", "libc", "elixir", "otp", "erts", "compiler",
              "imageDigest", "sourceDigest", "sourceClosureDigest", "lockSha256", "files",
              "runtimeLibraries", "productionExportsDigest", "buildReceiptDigest", "nifHeaders",
              "controlNifSourceSha256", "controlNifCompilerSha256"}
    require(set(m) == fields and type(m["schema"]) is int and m["schema"] == 1, "source_mismatch")
    require(m["platform"] == "linux" and m["architecture"] == platform.machine(), "source_mismatch")
    require(m["elixir"] == "1.20.4" and m["otp"] == "29.1.1" and m["erts"] == "17.1",
            "source_mismatch")
    require(m["sourceDigest"] == SOURCE_SHA and m["sourceClosureDigest"] == digest(source_inputs()),
            "source_mismatch")
    require(m["lockSha256"] == sha(ROOT / "hosted/mix.lock"), "source_mismatch")
    require(m["controlNifSourceSha256"] == sha(HERE / "control_nif.c"), "source_mismatch")
    require(m["controlNifCompilerSha256"] == sha(Path("/usr/bin/cc").resolve()), "source_mismatch")
    require(isinstance(m["imageDigest"], str) and m["imageDigest"].startswith("sha256:")
            and len(m["imageDigest"]) == 71 and all(c in "0123456789abcdef" for c in m["imageDigest"][7:]), "source_mismatch")
    for key in ("productionExportsDigest", "buildReceiptDigest"):
        require(isinstance(m[key], str) and len(m[key]) == 64 and all(c in "0123456789abcdef" for c in m[key]),
                "source_mismatch")
    require(type(m["files"]) is dict and 0 < len(m["files"]) <= 50000, "source_mismatch")
    actual = set()
    for path in rootfs.rglob("*"):
        s = path.lstat()
        require(not stat.S_ISLNK(s.st_mode) and (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode)),
                "source_mismatch")
        require(s.st_uid == 0 and not (s.st_mode & 0o6022), "ownership")
        if path.is_file():
            require(s.st_nlink == 1, "ownership")
        if path.is_file() and path != rootfs / "release-manifest.json":
            actual.add(str(path.relative_to(rootfs)))
    require(actual == set(m["files"]), "source_mismatch")
    for name, expected_sha in m["files"].items():
        require(safe_relative(name) and sha(rootfs / name) == expected_sha, "source_mismatch")
    for required in ("usr/bin/elixir", "bin/sh", "dev/null", "opt/harness/role.exs", "opt/harness/fault_helper", "opt/harness/control_nif.so"):
        require(required in actual, "source_mismatch")
    require(all((rootfs / p).is_dir() for p in ("proc", "tmp", "opt/mixer/release/lib")), "source_mismatch")
    require(not (rootfs / "sys/fs/cgroup").exists(), "ownership")
    require(m["files"].get("opt/mixer/build-receipt.json") == m["buildReceiptDigest"]
            and m["files"].get("opt/mixer/production-exports.json") == m["productionExportsDigest"], "source_mismatch")
    # A private build receipt is a content binding, not independently established
    # build provenance. Its actual replay remains the independent reviewer's gate.
    build = load(rootfs / "opt/mixer/build-receipt.json")
    require(build.get("platform") == "linux" and build.get("sourceInputs") == source_inputs()
            and build.get("lockSha256") == m["lockSha256"] and build.get("elixir") == m["elixir"]
            and build.get("otp") == m["otp"], "source_mismatch")
    # A nonrecursive bind must never silently change the source closure by
    # exposing an underlying directory in place of a nested host mount.
    for row in Path("/proc/self/mountinfo").read_text().splitlines():
        mountpoint = row.split()[4]
        for escaped, literal in (("\\040", " "), ("\\011", "\t"), ("\\012", "\n"), ("\\134", "\\")):
            mountpoint = mountpoint.replace(escaped, literal)
        mountpath = Path(mountpoint)
        require(mountpath == rootfs or not mountpath.is_relative_to(rootfs), "namespace")
    require(type(m["runtimeLibraries"]) is dict and {"libc", "libcrypto", "libssl", "beam.smp"}
            <= set(m["runtimeLibraries"]), "source_mismatch")
    for item in m["runtimeLibraries"].values():
        require(type(item) is dict and set(item) == {"path", "sha256"}
                and m["files"].get(item["path"]) == item["sha256"], "source_mismatch")
    require(type(m["nifHeaders"]) is dict and set(m["nifHeaders"]) == {
        "usr/include/erl_nif.h", "usr/include/erl_drv_nif.h", "usr/include/erl_int_sizes_config.h"}, "source_mismatch")
    require(all(m["files"].get(path) == value for path, value in m["nifHeaders"].items()), "source_mismatch")
    # Match actual ELF platform, never a macOS ERTS or native-library substitute.
    for item in m["runtimeLibraries"].values():
        with open(rootfs / item["path"], "rb") as elf:
            header = elf.read(20)
        require(header[:5] == b"\x7fELF\x02" and header[5] == 1, "source_mismatch")
        require(int.from_bytes(header[18:20], "little") == {"aarch64": 183, "x86_64": 62}.get(platform.machine()),
                "source_mismatch")
    for key in ("libc", "compiler"):
        require(isinstance(m[key], str) and 1 <= len(m[key]) <= 256 and all(32 <= ord(c) <= 126 for c in m[key]),
                "source_mismatch")
    return m, digest(m)


def core_policy():
    require(Path("/proc/sys/kernel/core_pattern").read_text().strip() == "core", "dump_policy", True)
    require(Path("/proc/sys/fs/suid_dumpable").read_text().strip() == "0", "dump_policy", True)
    return {"plainLocalCorePattern": 1, "pipedCollector": 0, "suidDumpable": 0}


def read_at(directory, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    try:
        data = os.read(fd, 65536)
        require(len(data) < 65536, "cgroup_readback")
        return data.decode("ascii").strip()
    finally:
        os.close(fd)


def write_at(directory, name, value):
    fd = os.open(name, os.O_WRONLY | os.O_NOFOLLOW, dir_fd=directory)
    try:
        data = str(value).encode("ascii")
        require(os.write(fd, data) == len(data), "cgroup_readback")
    finally:
        os.close(fd)


def counter_file(text):
    out = {}
    for row in text.splitlines():
        key, val = row.split()
        require(key.replace("_", "").isalnum() and val.isdecimal(), "cgroup_readback")
        out[key] = int(val)
    return out


def ancestors(parent, p):
    base = Path("/sys/fs/cgroup")
    require(parent.is_absolute() and parent.resolve() == parent and parent.is_relative_to(base), "delegation")
    inventory = []
    current = parent
    while True:
        require(current.stat().st_uid == os.geteuid(), "ownership")
        values = {}
        for name in ("memory.max", "memory.high", "memory.swap.max", "pids.max", "cpu.max"):
            path = current / name
            if not path.exists():
                require(current == base, "ancestor_limit")
                values[name] = "unlimited-root"
                continue
            value = path.read_text().strip()
            values[name] = value
            if name == "cpu.max":
                quota, period = value.split()
                require(period.isdecimal() and int(period) > 0, "ancestor_limit")
                if quota != "max":
                    require(quota.isdecimal() and int(quota) * 100000 >= 25000 * int(period), "ancestor_limit")
            elif value != "max":
                require(value.isdecimal(), "ancestor_limit")
                require(int(value) >= p["cgroup"][name], "ancestor_limit")
        inventory.append({"path": str(current), "limits": values})
        if current == base:
            return inventory
        current = current.parent


class Cgroup:
    def __init__(self, parent, p, token):
        self.parent, self.p = Path(parent), p
        self.path = self.parent / ("mixer-wh-" + token)
        self.fd, self.identity = None, None
        self.limit_inventory = {}

    def create(self):
        require({"memory", "cpu", "pids"} <= set((self.parent / "cgroup.controllers").read_text().split()),
                "delegation", True)
        require({"memory", "cpu", "pids"} <= set((self.parent / "cgroup.subtree_control").read_text().split()),
                "delegation", True)
        ancestors(self.parent, self.p)
        self.path.mkdir(mode=0o700)
        self.fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.identity = os.fstat(self.fd)
        require(read_at(self.fd, "cgroup.procs") == "", "ownership")
        for name, value in self.p["cgroup"].items():
            if name != "version":
                write_at(self.fd, name, value)
                require(read_at(self.fd, name) == str(value), "cgroup_readback")
        require((self.path / "cgroup.kill").exists(), "capability_unavailable", True)

    def pids(self):
        return [int(n) for n in read_at(self.fd, "cgroup.procs").split()]

    def sample(self):
        v = {"monotonicNs": time.monotonic_ns()}
        for filename in ("memory.current", "memory.peak", "pids.current", "pids.peak"):
            try:
                raw = read_at(self.fd, filename)
            except FileNotFoundError:
                require(filename.endswith(".peak"), "cgroup_readback")
                v[filename + "Supported"] = 0
            else:
                require(raw.isdecimal(), "cgroup_readback")
                v[filename] = int(raw)
                if filename.endswith(".peak"):
                    v[filename + "Supported"] = 1
        for filename in ("memory.events", "pids.events", "cpu.stat"):
            for key, value in counter_file(read_at(self.fd, filename)).items():
                v[filename + "." + key] = value
        rss, fds, sockets, tasks = 0, 0, set(), 0
        for pid in self.pids():
            proc = Path("/proc") / str(pid)
            try:
                fields = dict(row.split(":", 1) for row in (proc / "status").read_text().splitlines() if ":" in row)
                rss += int(fields.get("VmRSS", "0 kB").split()[0]) * 1024
                tasks += int(fields["Threads"].strip())
                limits = (proc / "limits").read_text().splitlines()
                observed = {"pid": pid}
                for prefix, expected in (("Max open files", 256), ("Max core file size", 0), ("Max file size", 0)):
                    row = next(line for line in limits if line.startswith(prefix))
                    soft, hard = row[len(prefix):].split()[:2]
                    require(soft == str(expected) and hard == str(expected), "descriptor_limit")
                    observed[prefix + "Soft"] = int(soft)
                    observed[prefix + "Hard"] = int(hard)
                self.limit_inventory[pid] = observed
                for fd in (proc / "fd").iterdir():
                    try:
                        target = os.readlink(fd)
                    except FileNotFoundError:
                        continue
                    fds += 1
                    if target.startswith("socket:["):
                        sockets.add(target)
            except FileNotFoundError:
                continue  # exiting task; cgroup counters remain authoritative
        v.update(processRSSBytes=rss, aggregateFDs=fds, socketInodes=len(sockets), osTasks=tasks,
                 limitsValidatedProcesses=len(self.limit_inventory))
        return v

    def stop(self, channel):
        started = time.monotonic_ns()
        admission_requested = False
        if channel is not None:
            try:
                channel.send_stop()
                admission_requested = True
            except (OSError, Refusal):
                pass
        # A responsive role closes admission and existing connections first.
        # Frozen/dead roles may never acknowledge: the external kill still owns
        # the same 2500ms disposal deadline and records lack of observation.
        while channel is not None and not channel.stopped and time.monotonic_ns() - started < 150_000_000:
            try:
                if not channel.receive():
                    break
            except BlockingIOError:
                time.sleep(0.002)
            except (OSError, Refusal):
                break
        for pid in self.pids():
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        grace = started + 2_000_000_000
        deadline = started + 2_500_000_000
        while self.pids() and time.monotonic_ns() < grace:
            time.sleep(0.01)
        killed = bool(self.pids())
        if killed:
            write_at(self.fd, "cgroup.kill", "1")
        while self.pids() and time.monotonic_ns() < deadline:
            time.sleep(0.005)
        ended = time.monotonic_ns()
        empty = not self.pids()
        return {"stopStartedMonotonicNs": started, "elapsedNs": ended - started,
                "overshootNs": max(0, ended - deadline), "admissionCloseRequested": admission_requested,
                "admissionClosedObserved": bool(channel and channel.stopped),
                "termGraceMs": 2000, "cgroupKillUsed": killed, "empty": empty}

    def cleanup(self):
        if self.fd is None:
            return {"ownedCgroupCreated": False, "empty": True, "removed": False}
        require(not self.pids(), "cleanup")
        s = self.path.stat()
        require((s.st_dev, s.st_ino) == (self.identity.st_dev, self.identity.st_ino), "ownership")
        os.close(self.fd)
        self.fd = None
        self.path.rmdir()
        return {"ownedCgroupCreated": True, "empty": True, "removed": True}


class Control:
    """Owned descriptor authority, not HTTP, SO_PEERCRED creator PID, or a URL."""
    def __init__(self, sock, generation):
        self.sock, self.generation = sock, generation
        self.ready, self.stopped, self.port = False, False, None
        self.closed = False
        self.stop_sent = False

    def receive(self):
        data, ancillary, flags, _ = self.sock.recvmsg(257, socket.CMSG_SPACE(256))
        for level, kind, raw in ancillary:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                received = array.array("i")
                received.frombytes(raw[:len(raw) - len(raw) % received.itemsize])
                for fd in received:
                    os.close(fd)
        require(not ancillary and not flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC), "output_schema")
        if not data:
            self.closed = True
            return False
        require(0 < len(data) <= 256, "output_schema")
        try:
            parts = data.decode("ascii").split(" ")
        except UnicodeError:
            raise Refusal("output_schema") from None
        if len(parts) == 3 and parts[0] == "ready" and parts[1] == self.generation:
            require(not self.ready and not self.stopped and parts[2].isdecimal(), "output_schema")
            port = int(parts[2])
            require(1 <= port <= 65535, "output_schema")
            self.ready, self.port = True, port
        elif parts == ["stopped", self.generation, "completed"]:
            require(self.ready and self.stop_sent and not self.stopped, "output_schema")
            self.stopped = True
        else:
            raise Refusal("output_schema")
        return True

    def send_stop(self):
        require(not self.stop_sent, "output_schema")
        require(self.sock.send(("stop " + self.generation).encode()) == 37, "output_schema")
        self.stop_sent = True


class OutputAudit:
    EVENTS = {"sample": {"beamTotalBytes", "heapWords", "referencedBinaryBytes", "mailboxLength", "processes"},
              "case": {"checks", "failures", "sentBytes", "ownersDown", "lateSuccesses"},
              "isolation": {"capabilities", "dumpable", "readOnlyRoot", "inheritedFDs", "roleNamespacePid", "preInitDumpable"},
              "fault": {"attempts", "limitReached", "elapsedNs", "kind"}}
    def __init__(self):
        self.buffers = {"stdout": bytearray(), "stderr": bytearray()}
        self.counts = {k: 0 for k in self.buffers}
        self.allowed, self.rejected, self.seen = 0, 0, {}
        self.events = []
        self.case = None
        self.sample_observations = []

    def feed(self, stream, raw):
        self.counts[stream] += len(raw)
        # Never retain raw rejected bytes in the receipt, exception or file.
        for sentinel in (b"MIXER_BODY_SENTINEL", b"MIXER_SIGNATURE_SENTINEL", b"MIXER_TRAILER_SENTINEL"):
            self.seen[sentinel.decode()] = self.seen.get(sentinel.decode(), False) or sentinel in self.buffers[stream] + raw
        if self.counts[stream] > 1048576:
            self.rejected += 1
            self.buffers[stream].clear()
            raise Refusal("output_overflow")
        buf = self.buffers[stream]
        buf.extend(raw)
        while b"\n" in buf:
            line, _, rest = buf.partition(b"\n")
            buf[:] = rest
            try:
                def closed_pairs(items):
                    result = {}
                    for key, value in items:
                        require(key not in result, "output_schema")
                        result[key] = value
                    return result
                v = json.loads(line, object_pairs_hook=closed_pairs)
                event = v["event"]
                require(event in self.EVENTS and set(v) == self.EVENTS[event] | {"schema", "event"}
                        and type(v["schema"]) is int and v["schema"] == 1, "output_schema")
                require(all(type(n) is int and 0 <= n <= 2**63 - 1 for k, n in v.items() if k not in ("schema", "event")),
                        "output_schema")
                # Reconstruct instead of forwarding the parsed input dictionary.
                safe = {"schema": 1, "event": event, **{k: int(v[k]) for k in sorted(self.EVENTS[event])}}
                self.events.append(safe)
                self.allowed += 1
                if event == "sample":
                    self.sample_observations.append({"monotonicNs": time.monotonic_ns(),
                                                     **{k: safe[k] for k in self.EVENTS[event]}})
                if event == "case":
                    require(self.case is None, "output_schema")
                    self.case = safe
            except (ValueError, TypeError, KeyError, Refusal):
                self.rejected += 1
                buf.clear()
                raise Refusal("output_schema") from None
        if len(buf) > 4096:
            self.rejected += 1
            buf.clear()
            raise Refusal("output_schema")

    def finish(self):
        if any(self.buffers.values()):
            self.rejected += 1
            raise Refusal("output_schema")

    def receipt(self):
        return {"allowedSchemaCount": self.allowed, "rejectedOutputCount": self.rejected,
                "stdoutBytes": self.counts["stdout"], "stderrBytes": self.counts["stderr"],
                "sentinelMatches": {k: bool(self.seen.get(v)) for k, v in
                                    {"body": "MIXER_BODY_SENTINEL", "signature": "MIXER_SIGNATURE_SENTINEL",
                                     "trailer": "MIXER_TRAILER_SENTINEL"}.items()}}


def receipt(case, env, release_sha="", status="unavailable", reason="capability_unavailable"):
    return dict(zip(load(CONTRACT / "profile.json")["caseReceiptFields"],
                    (case, status, reason, PROFILE_SHA, SOURCE_SHA, release_sha, digest(env), time.monotonic_ns(),
                     0, {}, {}, [], {}, OutputAudit().receipt(), {"roleStarted": False, "ownedResourcesCreated": False})))


def check_review(path):
    m = load(path)
    require(set(m) == {"schema", "status", "harnessDigest", "profileDigest", "sourceDigest", "reviewer"}, "ownership")
    require(m["schema"] == 1 and m["status"] == "independent-source-review-approved-for-private-runtime"
            and m["harnessDigest"] == harness_digest() and m["profileDigest"] == PROFILE_SHA
            and m["sourceDigest"] == SOURCE_SHA and type(m["reviewer"]) is str and 0 < len(m["reviewer"]) <= 128,
            "ownership")


def remove_scratch(path, identity, selected):
    require(path.is_dir() and not path.is_symlink(), "cleanup")
    now = path.stat()
    require((now.st_dev, now.st_ino, now.st_uid) == (identity.st_dev, identity.st_ino, identity.st_uid), "cleanup")
    marker = load(path / "identity.json")
    require(marker == {"schema": 1, "owner": "stripe-webhook-linux-resource-harness", "pid": os.getpid(),
                       "harnessDigest": harness_digest()}, "cleanup")
    allowed = {"identity.json", "fault_helper", "control_nif.so"} | {"mount-" + c for c in selected}
    require({x.name for x in path.iterdir()} <= allowed, "cleanup")
    # No recursive deletion, no other namespace mount manipulation, no PID search
    # outside the owned cgroup. Busy or nonempty targets remain preserved failures.
    for child in path.iterdir():
        require(not child.is_symlink(), "cleanup")
        if child.is_dir():
            child.rmdir()
        else:
            child.unlink()
    path.rmdir()


def execute(case, args, p, env, release_sha, suite_end, scratch):
    out = receipt(case, env, release_sha, "failed", "runtime_error")
    if case not in EXECUTABLE_CASES:
        return receipt(case, env, release_sha)
    started = out["startedMonotonicNs"]
    cg = Cgroup(args.delegated_cgroup, p, uuid.uuid4().hex)
    proc = channel = endpoint = None
    audit = OutputAudit()
    try:
        cg.create()
        out["cleanup"]["ownedResourcesCreated"] = True
        out["cgroupBefore"] = cg.sample()
        endpoint, child_endpoint = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        # Peer UID/PID here identify socketpair creator only. No sender-PID claim.
        generation = uuid.uuid4().hex
        channel = Control(endpoint, generation)
        argv = [str(scratch / "fault_helper"), "launch", str(cg.path), str(Path(args.release).resolve()),
                str(scratch / ("mount-" + case)), str(child_endpoint.fileno()), generation, case,
                str(HERE / "role.exs"), str(os.getpid()), str(scratch / "control_nif.so")]
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                pass_fds=(child_endpoint.fileno(),), close_fds=True, env=FIXED_ENV,
                                start_new_session=True)
        child_endpoint.close()
        out["cleanup"]["roleStarted"] = True
        deadline = min(started + 120_000_000_000, suite_end)
        sel = selectors.DefaultSelector()
        for name, pipe in (("stdout", proc.stdout), ("stderr", proc.stderr), ("control", endpoint)):
            os.set_blocking(pipe.fileno(), False)
            sel.register(pipe, selectors.EVENT_READ, name)
        next_sample = time.monotonic_ns()
        while time.monotonic_ns() < deadline:
            now = time.monotonic_ns()
            if now >= next_sample:
                out["samples"].append(cg.sample())
                next_sample = now + 20_000_000
            for key, _ in sel.select(0.01):
                if key.data == "control":
                    if not channel.receive():
                        sel.unregister(key.fileobj)
                else:
                    data = os.read(key.fd, 65536)
                    if data:
                        audit.feed(key.data, data)
                    else:
                        sel.unregister(key.fileobj)
            if audit.case is not None:
                break
            if proc.poll() is not None:
                break
        else:
            raise Refusal("deadline")
        require(channel.ready, "namespace")
        if case == "R13":
            after = cg.sample()
            require(after.get("memory.events.oom_kill", 0) > out["cgroupBefore"].get("memory.events.oom_kill", 0), "oom")
        elif case == "R16":
            require(proc.poll() is not None and proc.returncode != 0, "dump_policy")
            require(cg.sample().get("memory.events.oom_kill", 0) == out["cgroupBefore"].get("memory.events.oom_kill", 0), "dump_policy")
        else:
            require(audit.case is not None and audit.case["checks"] > 0 and audit.case["failures"] == 0,
                    "runtime_error")
        if case == "R09":
            after = cg.sample()
            require(after.get("cpu.stat.nr_throttled", 0) > out["cgroupBefore"].get("cpu.stat.nr_throttled", 0)
                    and after.get("cpu.stat.throttled_usec", 0) > out["cgroupBefore"].get("cpu.stat.throttled_usec", 0), "cpu_throttled")
        if case == "R10":
            require(cg.sample().get("pids.events.max", 0) > out["cgroupBefore"].get("pids.events.max", 0), "task_limit")
        if case == "R15":
            for pid in cg.pids():
                try:
                    os.kill(pid, signal.SIGSTOP)
                except ProcessLookupError:
                    pass
        out.update(status="passed", reason="completed")
        sel.close()
    except Refusal as e:
        out.update(status="unavailable" if e.unavailable else "failed", reason=e.reason)
    except (OSError, subprocess.SubprocessError, ValueError):
        out.update(status="failed", reason="runtime_error")
    finally:
        if cg.fd is not None:
            try:
                out["termination"] = cg.stop(channel)
                out["cgroupAfter"] = cg.sample()
                out["cgroupAfter"]["processLimits"] = list(cg.limit_inventory.values())
                require(out["termination"]["empty"] and out["termination"]["overshootNs"] == 0, "cleanup")
                if case == "R15":
                    require(out["termination"]["cgroupKillUsed"], "shutdown")
                out["cleanup"] = {**out["cleanup"], **cg.cleanup()}
            except (OSError, Refusal):
                out.update(status="failed", reason="cleanup")
        if proc is not None:
            try:
                code = proc.wait(timeout=3)
                out["termination"].update(exitCode=code if code >= 0 else None,
                                          signal=-code if code < 0 else None)
            except subprocess.TimeoutExpired:
                out.update(status="failed", reason="cleanup")
            for name, pipe in (("stdout", proc.stdout), ("stderr", proc.stderr)):
                try:
                    while True:
                        data = os.read(pipe.fileno(), 65536)
                        if not data:
                            break
                        audit.feed(name, data)
                except BlockingIOError:
                    out.update(status="failed", reason="cleanup")
                except Refusal as e:
                    out.update(status="failed", reason=e.reason)
                finally:
                    pipe.close()
        if endpoint is not None:
            endpoint.close()
        try:
            audit.finish()
        except Refusal as e:
            out.update(status="failed", reason=e.reason)
        out["outputAudit"] = audit.receipt()
        out["samples"].extend(audit.sample_observations)
        out["samples"].sort(key=lambda sample: sample["monotonicNs"])
        out["elapsedNs"] = time.monotonic_ns() - started
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=CONTRACT / "profile.json")
    parser.add_argument("--delegated-cgroup", type=Path)
    parser.add_argument("--release", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--review", type=Path)
    parser.add_argument("--case", choices=CASES, action="append")
    args = parser.parse_args()
    # Evidence output is constrained to this owned packet, never a request value.
    output = args.output.absolute()
    require(output.is_relative_to(HERE / "results") and not output.exists()
            and all(not q.is_symlink() for q in (output, *output.parents)), "ownership")
    output.mkdir(parents=True, mode=0o700)
    env = linux_capabilities()
    rows = []
    release_sha = ""
    scratch = scratch_identity = None
    suite_cleanup = {"scratchCreated": False, "scratchRemoved": False, "success": True}
    selected = args.case or CASES
    try:
        p = profile(args.profile)
        source_inputs()
        require(env["linux"] and env["cgroupV2"] and env["rootLauncherAvailable"], "capability_unavailable", True)
        require(args.release is not None and args.delegated_cgroup is not None, "capability_unavailable", True)
        manifest, release_sha = release_manifest(args.release)
        compiler_version = subprocess.run(["/usr/bin/cc", "--version"], stdin=subprocess.DEVNULL,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=FIXED_ENV, timeout=10)
        require(compiler_version.returncode == 0 and not compiler_version.stderr, "source_mismatch")
        compiler_first = compiler_version.stdout.decode("ascii").splitlines()[0]
        require(compiler_first == manifest["compiler"], "source_mismatch")
        env.update(corePolicy=core_policy(), ancestors=ancestors(args.delegated_cgroup, p),
                   runtimeLibraries=manifest["runtimeLibraries"], imageDigest=manifest["imageDigest"],
                   compiler={"identity": compiler_first, "sha256": manifest["controlNifCompilerSha256"]})
        require(args.execute, "capability_unavailable", True)
        require(args.review is not None, "ownership")
        check_review(args.review)
        # The compiler is already installed; no software or image installation.
        scratch = HERE / (".owned-scratch-" + uuid.uuid4().hex)
        scratch.mkdir(mode=0o700)
        scratch_identity = scratch.stat()
        suite_cleanup["scratchCreated"] = True
        (scratch / "identity.json").write_bytes(canonical({"schema": 1, "owner": "stripe-webhook-linux-resource-harness",
                                                         "pid": os.getpid(), "harnessDigest": harness_digest()}))
        built = subprocess.run(["/usr/bin/cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                                str(HERE / "fault_helper.c"), "-o", str(scratch / "fault_helper")],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=FIXED_ENV, timeout=30)
        require(built.returncode == 0 and not built.stdout and not built.stderr, "runtime_error")
        nif = subprocess.run(["/usr/bin/cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-fPIC", "-shared",
                              "-I", str(args.release / "usr/include"), str(HERE / "control_nif.c"),
                              "-o", str(scratch / "control_nif.so")], stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=FIXED_ENV, timeout=30)
        require(nif.returncode == 0 and not nif.stdout and not nif.stderr, "runtime_error")
        suite_end = time.monotonic_ns() + 900_000_000_000
        for case in selected:
            rows.append(execute(case, args, p, env, release_sha, suite_end, scratch))
    except Refusal as e:
        rows.extend(receipt(c, env, release_sha, "unavailable" if e.unavailable else "failed", e.reason)
                    for c in selected if c not in {r["caseId"] for r in rows})
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError, TypeError):
        rows.extend(receipt(c, env, release_sha, "failed", "runtime_error")
                    for c in selected if c not in {r["caseId"] for r in rows})
    finally:
        if scratch is not None:
            try:
                require(all(row["cleanup"].get("empty", True) for row in rows), "cleanup")
                remove_scratch(scratch, scratch_identity, selected)
                suite_cleanup["scratchRemoved"] = True
            except (OSError, Refusal):
                suite_cleanup["success"] = False
    for row in rows:
        (output / (row["caseId"] + ".json")).write_bytes(canonical(row) + b"\n")
    summary = {"schema": 1, "status": "failed" if not suite_cleanup["success"] else "unavailable" if all(r["status"] == "unavailable" for r in rows)
               else "passed-private-runtime" if all(r["status"] == "passed" for r in rows) else "failed",
               "runtimeCasesExecuted": sum(bool(r["cleanup"].get("roleStarted")) for r in rows),
               "counts": {s: sum(r["status"] == s for r in rows) for s in ("passed", "failed", "unavailable")},
               "environment": env, "harnessDigest": harness_digest(), "sourceDigest": SOURCE_SHA,
               "profileDigest": PROFILE_SHA, "gaAccepted": False, "publicTrailerPolicy": "unselected",
               "selectedCases": list(selected), "implementedDrivers": sorted(EXECUTABLE_CASES),
               "comprehensiveMatrixAccepted": False, "suiteCleanup": suite_cleanup,
               "pendingSeparateCases": ["T01", "T02", "T03", "T04", "I01"]}
    (output / "summary.json").write_bytes(canonical(summary) + b"\n")
    print(json.dumps({k: summary[k] for k in ("status", "counts", "runtimeCasesExecuted")}, sort_keys=True))
    return 78 if summary["status"] == "unavailable" else 0 if summary["status"] == "passed-private-runtime" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refusal as refusal:
        print(json.dumps({"schema": 1, "status": "failed", "reason": refusal.reason}))
        sys.exit(1)
