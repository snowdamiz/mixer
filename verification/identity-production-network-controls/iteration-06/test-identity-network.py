#!/usr/bin/env python3
"""Finite remote-only collector for the two frozen identity network methods.

Importing this file is side-effect free. The pure validators are intentionally
shared with stdlib fault controls; they do not establish runtime isolation.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import uuid

FROZEN_PRODUCT_DIGEST = "023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e"
FROZEN_LOCK_SHA256 = "1eada39dcaf4863d02d39f51e218d2bad8908b36a0cba47ff2d16037b7bcf837"
CONTRACT_SHA256 = "695a165d41e9d4eac5fdc582b835a60f5c3bbdd6f0fb3131c0ad27ffbbe135bc"
CONTRACT_PACKET = "a3a806d83e285213df4c0e951282686dcfcfa81701e8005040d5172b3300050d"
PRODUCT_COMMIT = "9e860ea12074ca31bef4087ce34177a03f295dd8"
IMAGES = {
    "test": {
        "ref": "hexpm/elixir@sha256:3571d320ec0656c38c76b4c362a8e0c0fd6f9b58cec6448a08e43a82940d4e43",
        "config": "sha256:6631543fddfe053ddbd30435318916667d5da87b5f5ec0644893d146a539370e",
    },
    "pg": {
        "ref": "library/postgres@sha256:cf5d353f55240ecc2f811827a15c7d1f2d562f08019b49dca12b5a59f4ab5962",
        "config": "sha256:6a35283e53fbe883da6a6ffbce8d3999dc66076cc5c4e2f1d21bdbd9e26bf86f",
    },
}
BOOTSTRAP = {
    "hex": {
        "url": "https://builds.hex.pm/installs/1.20.0/hex-2.5.1-otp-29.ez",
        "sha512": "6629f4b4bb2e040326151ebb853aad065e342c65ad3a0f2a2674dcf7164eb4328d6c929513d7230309ad75042024e72bef0e0a51ebff373b4173d2746b1772b7",
        "version": "2.5.1",
    },
    "rebar": {
        "url": "https://builds.hex.pm/installs/1.18.4/rebar3-3.28.0-otp-29",
        "sha512": "b51946058fbe4aa823185bfe27204be59be439982ac3a3e1dbd9f8260b9af046fcfdfbd9066283c3fbba5a2a45dc3570550c12a9a548daf223b80cac222a6d0f",
        "version": "3.28.0",
    },
}
RESOURCES = {"prepare": (2147483648, 2, 256), "test": (2147483648, 2, 256), "pg": (1073741824, 1, 128)}
TMPFS = {
    "prepare": {"/workspace": "rw,nosuid,nodev,size=1073741824,mode=0755", "/tmp": "rw,nosuid,nodev,size=67108864,mode=1777"},
    "test": {"/workspace": "rw,nosuid,nodev,size=1073741824,mode=0755", "/tmp": "rw,nosuid,nodev,size=67108864,mode=1777", "/run": "rw,nosuid,nodev,size=16777216,mode=0755"},
    "pg": {"/var/lib/postgresql/data": "rw,nosuid,nodev,size=536870912,mode=0700", "/var/run/postgresql": "rw,nosuid,nodev,size=16777216,mode=0775", "/tmp": "rw,nosuid,nodev,size=67108864,mode=1777"},
}
CAPS = {"prepare": set(), "test": {"NET_ADMIN", "NET_BIND_SERVICE"}, "pg": {"CHOWN", "DAC_OVERRIDE", "FOWNER", "SETUID", "SETGID"}}
BASE_ENV = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "LANG": "C.UTF-8", "HOME": "/workspace/home", "MIX_ENV": "test",
    "MIX_HOME": "/workspace/tooling/mix", "MIX_REBAR3": "/workspace/tooling/rebar3",
    "HEX_HOME": "/workspace/tooling/hex", "XDG_CACHE_HOME": "/workspace/cache",
    "ERL_CRASH_DUMP": "/workspace/evidence/erl_crash.dump", "ERL_CRASH_DUMP_SECONDS": "0",
}
TEST_ENV = {**BASE_ENV, "MIXER_TEST_DATABASE_PORT": "5432", "MIXER_TEST_IDENTITY_EVIDENCE": "/workspace/evidence/identity"}
EXPECTED_METHODS = (
    ("Elixir.MixerHosted.Identity.KeyOwnerLinuxNetworkTest", "test K03 production resolver/classifier pins public peer despite rebinding; private sink remains untouched"),
    ("Elixir.MixerHosted.Identity.StartupLinuxNetworkTest", "test IS04 IS05 actual configured startup cold production DNS TLS admission and lifecycle"),
)
TEST_ROOTS = ["test/mixer_hosted/identity/key_owner_linux_network_test.exs", "test/mixer_hosted/identity/startup_linux_network_test.exs"]
MAX_COMMAND_BYTES = 8388608
MAX_LOG_BYTES = 67108864
MAX_ARCHIVE_BYTES = 536870912
MAX_ARTIFACT_BYTES = 268435456


class CollectorError(ValueError):
    """A refusal, partial observation, or failed qualification."""


def require(condition, message):
    if not condition:
        raise CollectorError(message)


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_source_manifest(manifest, expected_digest=FROZEN_PRODUCT_DIGEST, expected_count=177):
    require(isinstance(manifest, dict) and len(manifest) == expected_count, "source path count mismatch")
    for path, row in manifest.items():
        p = PurePosixPath(path)
        require(path.startswith("hosted/") and not p.is_absolute() and ".." not in p.parts and str(p) == path, "unsafe source path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"}, "source row shape")
        require(type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES, "source byte bound")
        require(bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "source hash shape")
    if "hosted/mix.lock" in manifest:
        require(manifest["hosted/mix.lock"]["sha256"] == FROZEN_LOCK_SHA256, "frozen lock mismatch")
    require(canonical_digest(manifest) == expected_digest, "frozen product digest mismatch")
    return manifest


def validate_source_unchanged(before, after):
    require(isinstance(before, dict) and before == after, "source/dependency/tool mutation")
    return after


def validate_environment(caller_env):
    forbidden = ("MIXER_", "ERL_", "ELIXIR_", "MIX_", "HEX_", "AWS_")
    for key in caller_env:
        require(not key.startswith(forbidden) and key not in {"GITHUB_TOKEN", "GH_TOKEN", "BASH_ENV", "ENV", "LD_PRELOAD", "LD_LIBRARY_PATH"}, "inherited startup, isolation, or secret environment refused: " + key)
    return dict(TEST_ENV)


def validate_image_inspect(role, inspected):
    require(role in CAPS, "unknown image role")
    expected = IMAGES["pg" if role == "pg" else "test"]
    require(inspected.get("Id") == expected["config"], "image config mismatch")
    require(inspected.get("Os") == "linux" and inspected.get("Architecture") == "amd64", "image platform mismatch")
    # Docker normalizes library/postgres to postgres in RepoDigests.
    digests = [entry.split("@")[-1] for entry in inspected.get("RepoDigests", [])]
    require(expected["ref"].split("@")[-1] in digests, "image manifest mismatch")
    return inspected


@dataclasses.dataclass
class OwnedContainer:
    cid: str
    name: str
    role: str
    image_id: str
    label: str
    state: str = "owned"


class OwnedRegistry:
    def __init__(self):
        self.records = []
        self.unresolved = []

    def reserve(self, name, role, image_id, label):
        require(bool(re.fullmatch(r"mixer-identity-net-[0-9]+-[0-9]+-[0-9a-f]{32}-(prepare|test|pg)", name)), "unsafe owned name")
        require(role in CAPS and image_id == IMAGES["pg" if role == "pg" else "test"]["config"], "reservation identity mismatch")
        require(len(self.records) + len(self.unresolved) < 3, "container creation count exceeded")
        require(not any(r["name"] == name for r in self.unresolved) and not any(r.name == name for r in self.records), "duplicate reservation")
        self.unresolved.append({"name": name, "role": role, "image_id": image_id, "label": label, "state": "creating"})

    def add(self, cid, name, role, image_id, label):
        require(bool(re.fullmatch("[0-9a-f]{64}", cid)), "missing/invalid exact create CID")
        selected = [r for r in self.unresolved if r["name"] == name and r["state"] == "creating"]
        require(len(selected) == 1 and selected[0] == {"name": name, "role": role, "image_id": image_id, "label": label, "state": "creating"}, "unreserved create response")
        require(not any(r.cid == cid for r in self.records), "duplicate CID")
        self.unresolved.remove(selected[0])
        row = OwnedContainer(cid, name, role, image_id, label)
        self.records.append(row)
        return row

    def refuse(self, cid, reason):
        rows = [row for row in self.records if row.cid == cid]
        require(len(rows) == 1, "unknown refusal CID")
        rows[0].state = "identity_lost"

    def creation_unknown(self, name, reason):
        rows = [row for row in self.unresolved if row["name"] == name]
        require(len(rows) == 1, "unknown create reservation")
        rows[0].update(state="unknown", reason=str(reason))


def _caps(values):
    return {v.removeprefix("CAP_") for v in values or []}


def validate_owned_identity(inspected, owned):
    require(owned.role in CAPS and owned.state == "owned", "owned role/state mismatch")
    require(inspected.get("Id") == owned.cid and inspected.get("Image") == owned.image_id, "exact owned identity mismatch")
    require(inspected.get("Name", "").lstrip("/") == owned.name, "owned name mismatch")
    labels = inspected.get("Config", {}).get("Labels", {})
    require(labels.get("mixer.identity.run") == owned.label and labels.get("mixer.identity.role") == owned.role, "owned labels mismatch")


def validate_container_inspect(role, inspected, owned, test_cid=None):
    require(role == owned.role and owned.state == "owned", "container role/state mismatch")
    validate_owned_identity(inspected, owned)
    config = inspected.get("HostConfig", {})
    network = {"prepare": "default", "test": "none", "pg": "container:" + (test_cid or "")}[role]
    require(config.get("NetworkMode") == network and (role != "pg" or bool(test_cid)), "container network mismatch")
    require(config.get("ReadonlyRootfs") is True and config.get("Privileged") is False, "root/privilege mismatch")
    require(_caps(config.get("CapDrop")) == {"ALL"} and _caps(config.get("CapAdd")) == CAPS[role], "capability mismatch")
    require(config.get("SecurityOpt") == ["no-new-privileges:true"], "security option mismatch")
    for field in ("Binds", "Devices", "DeviceRequests", "PortBindings", "VolumesFrom", "ExtraHosts", "Links"):
        require(not config.get(field), "forbidden container setting: " + field)
    for field in ("PidMode", "IpcMode", "UTSMode", "UsernsMode"):
        require(config.get(field) not in {"host"}, "host namespace forbidden")
    require(not any((inspected.get("NetworkSettings", {}).get("Ports") or {}).values()), "published ports forbidden")
    require(config.get("Tmpfs") == TMPFS[role], "tmpfs contract mismatch")
    for mount in inspected.get("Mounts", []):
        require(mount.get("Type") == "tmpfs" and mount.get("Destination") in TMPFS[role], "host/anonymous mount forbidden")
    memory, cpus, pids = RESOURCES[role]
    require(config.get("Memory") == memory and config.get("MemorySwap") == memory and config.get("NanoCpus") == cpus * 1000000000 and config.get("PidsLimit") == pids, "resource limit mismatch")
    require(config.get("Ulimits") == [{"Name": "nofile", "Soft": 4096, "Hard": 4096}], "nofile mismatch")
    require(inspected.get("State", {}).get("OOMKilled") is not True, "container OOM")
    return inspected


PG_ENV = {"PATH": BASE_ENV["PATH"] + ":/usr/lib/postgresql/16/bin", "GOSU_VERSION": "1.19", "LANG": "en_US.utf8", "PG_MAJOR": "16", "PG_VERSION": "16.15-1.pgdg12+2", "PGDATA": "/var/lib/postgresql/data", "POSTGRES_USER": "mixer_fixture", "POSTGRES_DB": "mixer_startup_test", "POSTGRES_HOST_AUTH_METHOD": "trust"}


def validate_container_environment(role, inspected):
    values = inspected.get("Config", {}).get("Env", [])
    require(isinstance(values, list) and all(isinstance(v, str) and "=" in v for v in values), "container environment missing")
    actual = dict(v.split("=", 1) for v in values)
    require(len(actual) == len(values) and actual == (PG_ENV if role == "pg" else BASE_ENV), "actual container environment differs from allowlist")
    return actual


def validate_namespace(evidence, host_netns):
    require(evidence.get("interfaces") == ["lo"] and evidence.get("default_routes") == [], "external interface/route")
    require(bool(re.fullmatch(r"net:\[[0-9]+\]", evidence.get("netns", ""))) and evidence["netns"] != host_netns, "host/unknown network namespace")
    require(evidence.get("public_address") == "8.8.8.8" and evidence.get("setup_socket_closed") is True and evidence.get("open_setup_sockets", 0) == 0, "loopback setup incomplete")
    require(type(evidence.get("open_setup_sockets")) is int and evidence["open_setup_sockets"] == 0, "setup socket observation missing")
    for field in ("cap_eff", "cap_prm", "cap_bnd"):
        require(int(evidence.get(field, "0"), 16) == 0x1400, "actual capability mismatch")
    return evidence


def safe_members(archive, max_bytes=MAX_ARCHIVE_BYTES):
    require(0 < max_bytes <= MAX_ARCHIVE_BYTES, "archive cap override")
    members, names, total = [], set(), 0
    for member in archive:
        p = PurePosixPath(member.name)
        require(member.isfile() and not p.is_absolute() and ".." not in p.parts and str(p) == member.name and bool(p.parts) and "\\" not in member.name and not any(ord(c) < 32 for c in member.name), "unsafe archive member")
        require(member.name not in names, "duplicate archive member")
        require(not member.pax_headers, "extended archive metadata refused")
        total += member.size
        require(0 <= member.size <= max_bytes and total <= max_bytes and len(members) < 100000, "archive size/member cap")
        names.add(member.name)
        members.append(member)
    require(bool(members), "empty archive")
    return members


def validate_prepared_archive(data, manifest):
    require(len(data) <= MAX_ARCHIVE_BYTES and set(manifest) == {"source", "deps", "tools", "helpers"}, "prepared archive/manifest shape")
    validate_source_manifest(manifest["source"])
    expected = {}
    for section, rows in manifest.items():
        require(isinstance(rows, dict) and rows, "empty prepared section")
        for path, row in rows.items():
            require(path not in expected, "duplicate prepared manifest path")
            require(not any(part in {"_build", "evidence", "downloads", "home", "cache"} or part.startswith("mixer-key-owner-tls-") for part in PurePosixPath(path).parts), "forbidden prepared payload")
            if section == "deps":
                require(path.startswith("hosted/deps/"), "dependency injection path")
            if section == "tools":
                require(path == "tooling/rebar3" or path.startswith("tooling/mix/archives/hex-2.5.1/"), "bootstrap injection path")
            if section == "helpers":
                require(path in {"collector-prerequisites.exs", "collector-manifest.exs", "collector-netns.exs", "collector-observer.exs", "frozen-manifest.json"}, "helper injection path")
            expected[path] = row
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        members = safe_members(archive)
        require({m.name for m in members} == set(expected), "prepared archive path mismatch")
        for member in members:
            body = archive.extractfile(member).read()
            require(expected[member.name] == {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}, "prepared archive hash mismatch")
            if member.name == "tooling/rebar3":
                require(hashlib.sha512(body).hexdigest() == BOOTSTRAP["rebar"]["sha512"], "installed Rebar artifact pin mismatch")
    helper_bytes = {"collector-prerequisites.exs": PREREQUISITES_EXS.encode(), "collector-manifest.exs": MANIFEST_EXS.encode(), "collector-netns.exs": NETNS_EXS.encode(), "collector-observer.exs": OBSERVER_EXS.encode(), "frozen-manifest.json": json.dumps(FROZEN_MANIFEST, sort_keys=True, separators=(",", ":")).encode()}
    require(manifest["helpers"] == {path: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for path, body in helper_bytes.items()}, "collector helper mutation")
    return expected


SEMANTICS = {
    "production-DNS-rebinding.json": {"initialQueries": 2, "authenticatedPeer": "8.8.8.8:443", "publicConnections": 1, "forbiddenSinkConnections": 0, "newPrivateAnswerRejectedBeforeConnect": True, "namespace": "disposable network-none Linux lo:1; no product resolver or loopback bypass"},
    "startup-production-network.json": {"actualApplication": True, "endpointLiveness": 200, "namespace": "owned Linux network-none NET_ADMIN; 8.8.8.8 on lo:1", "resolver": "127.0.0.1:53", "destination": "8.8.8.8:443", "startupDNSQueries": 0, "startupConnections": 0, "coldTokenAdmitted": True, "coldDNSQueries": 2, "coldConnections": 1, "oldLeaseRejectedAfterRestart": True, "restartColdAdmission": True, "shutdownInflightCancelled": True, "allThreeConnectionsClosed": True, "fixtureKeyDirectoryRemoved": True, "publicAdapter": "ConfiguredVerifier.authenticate/2", "productionPolicyBypasses": 0},
}


def validate_events(events, exit_code, semantic):
    require(exit_code == 0 and isinstance(events, list), "test exit/events missing")
    require(len(events) == 6 and events[0].get("event") == "suite_started" and events[-1].get("event") == "suite_finished", "incomplete/extra suite events")
    seen = []
    for offset in (1, 3):
        start, finish = events[offset:offset + 2]
        identity = (start.get("module"), start.get("name"))
        require(start.get("event") == "test_started" and finish.get("event") == "test_finished" and identity == (finish.get("module"), finish.get("name")), "test event ordering/identity")
        require(identity in EXPECTED_METHODS and finish.get("state", "missing") is None, "missing/extra/skipped/failed method")
        seen.append(identity)
    require(len(set(seen)) == 2, "duplicate method")
    require(all(type(events[-1].get(k)) is int and events[-1][k] == v for k, v in {"total": 2, "failures": 0, "skipped": 0, "excluded": 0, "invalid": 0}.items()), "suite accounting mismatch")
    require(set(semantic) == set(SEMANTICS), "semantic receipt count/name mismatch")
    for name, expected in SEMANTICS.items():
        # JSON true must not satisfy a numeric assertion (bool subclasses int).
        require(set(semantic[name]) == set(expected) and all(type(semantic[name][k]) is type(v) and semantic[name][k] == v for k, v in expected.items()), "semantic disagreement: " + name)
    return {"methods": 2, "no_skips": True, "semantic_receipts": sorted(semantic)}


def validate_command_result(returncode, stdout, stderr, *, limit=MAX_COMMAND_BYTES, oom=False):
    require(len(stdout) + len(stderr) <= limit, "output incomplete: cap reached")
    require(not oom, "OOM invalidates command")
    require(returncode == 0, "nonzero/timeout command")
    return True


def cleanup_plan(records):
    require(all(isinstance(r, OwnedContainer) and r.role in CAPS for r in records), "malformed cleanup registry")
    require(len({r.cid for r in records}) == len(records) and len({r.role for r in records}) == len(records) and len({r.name for r in records}) == len(records), "duplicate cleanup identity")
    require(all(r.state in {"owned", "removed"} for r in records), "cleanup identity unknown; no alternate route")
    result = []
    for role in ("pg", "test", "prepare"):
        for row in records:
            if row.role == role and row.state == "owned":
                require(bool(re.fullmatch("[0-9a-f]{64}", row.cid)), "invalid cleanup CID")
                result.extend([["docker", "stop", "--time", "2", row.cid], ["docker", "rm", "--volumes", row.cid]])
    return result


class Budget:
    def __init__(self, start=None, clock=time.monotonic, total=660, reserve=30):
        require(0 < reserve < total <= 660, "budget contract")
        self.clock, self.start, self.total, self.reserve = clock, clock() if start is None else start, total, reserve

    def remaining(self, timeout, cleanup=False):
        remaining = self.start + self.total - self.clock() - (0 if cleanup else self.reserve)
        require(type(timeout) in {int, float} and 0 < timeout <= 180 and remaining > 0, "aggregate deadline/cleanup reserve reached")
        return min(timeout, remaining)


PREREQUISITES_EXS = r'''
emit = fn value -> IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(value))) end
hash = fn path -> :crypto.hash(:sha256, File.read!(path)) |> Base.encode16(case: :lower) end
tools = ["/bin/sh", "/usr/bin/env", "/usr/bin/mkdir", "/usr/bin/curl", "/usr/bin/sha512sum", "/usr/bin/install", "/usr/bin/tar", "/usr/bin/openssl", "/usr/local/bin/elixir", "/usr/local/bin/mix", "/usr/local/bin/erl", "/usr/local/bin/escript"]
rows = Map.new(tools, fn path ->
  %{type: :regular, mode: mode} = File.stat!(path)
  true = Bitwise.band(mode, 0o111) != 0
  {path, %{"sha256" => hash.(path), "bytes" => File.stat!(path).size}}
end)
"/usr/bin/openssl" = System.find_executable("openssl")
"1.20.4" = System.version()
"29" = to_string(:erlang.system_info(:otp_release))
otp_path = Path.join([to_string(:code.root_dir()), "releases", "29", "OTP_VERSION"])
"29.1.1" = File.read!(otp_path) |> String.trim()
{mix, 0} = System.cmd("/usr/local/bin/mix", ["--version"], stderr_to_stdout: true)
true = String.contains?(mix, "Mix 1.20.4")
{openssl, 0} = System.cmd("/usr/bin/openssl", ["version", "-a"], stderr_to_stdout: true)
versions = Map.new([{"/usr/bin/curl", ["--version"]}, {"/usr/bin/sha512sum", ["--version"]}, {"/usr/bin/install", ["--version"]}, {"/usr/bin/tar", ["--version"]}], fn {path, argv} ->
  {output, 0} = System.cmd(path, argv, stderr_to_stdout: true)
  true = byte_size(output) < 65536
  {path, output}
end)
emit.(%{"elixir" => System.version(), "otp_patch" => File.read!(otp_path) |> String.trim(), "mix" => mix, "openssl" => openssl, "crypto" => inspect(:crypto.info_lib()), "tools" => rows, "versions" => versions})
'''

MANIFEST_EXS = r'''
defmodule MixerIdentityNetworkCollector.Manifest do
  def files(path) do
    case File.lstat!(path).type do
      :regular -> [path]
      :directory -> File.ls!(path) |> Enum.sort() |> Enum.flat_map(&files(Path.join(path, &1)))
      _ -> raise "non-regular source/dependency/tool input"
    end
  end
  def entry(path) do
    bytes = File.read!(path)
    %{"bytes" => byte_size(bytes), "sha256" => Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)}
  end
  def run do
    frozen = File.read!("/workspace/frozen-manifest.json") |> :json.decode()
    source = Map.new(frozen, fn {path, expected} ->
      actual = entry("/workspace/" <> path)
      ^expected = actual
      {path, actual}
    end)
    deps = Map.new(files("/workspace/hosted/deps"), fn path -> {Path.relative_to(path, "/workspace"), entry(path)} end)
    tools = Map.new(Enum.flat_map(["/workspace/tooling/mix", "/workspace/tooling/rebar3"], &files/1), fn path -> {Path.relative_to(path, "/workspace"), entry(path)} end)
    helpers = Map.new(Path.wildcard("/workspace/collector-*.exs") ++ ["/workspace/frozen-manifest.json"], fn path -> {Path.relative_to(path, "/workspace"), entry(path)} end)
    value = %{"source" => source, "deps" => deps, "tools" => tools, "helpers" => helpers}
    if System.argv() == ["archive-list"] do
      names = Map.keys(source) ++ Map.keys(deps) ++ Map.keys(tools) ++ Map.keys(helpers)
      true = Enum.all?(names, &(not String.contains?(&1, ["\n", "\r", "\0"])))
      File.write!("/workspace/archive-files.txt", Enum.join(Enum.sort(names), "\n") <> "\n", [:exclusive])
    end
    IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(value)))
  end
end
MixerIdentityNetworkCollector.Manifest.run()
'''

NETNS_EXS = r'''
{:ok, socket} = :socket.open(:inet, :dgram, :udp)
:ok = :socket.ioctl(socket, :sifaddr, ~c"lo:1", %{family: :inet, addr: {8, 8, 8, 8}, port: 0})
{:ok, %{addr: {8, 8, 8, 8}}} = :socket.ioctl(socket, :gifaddr, ~c"lo:1")
:ok = :socket.close(socket)
interfaces = File.read!("/proc/net/dev") |> String.split("\n") |> Enum.drop(2) |> Enum.filter(&String.contains?(&1, ":")) |> Enum.map(&(String.split(&1, ":") |> hd() |> String.trim())) |> Enum.sort()
routes = File.read!("/proc/net/route") |> String.split("\n", trim: true) |> Enum.drop(1) |> Enum.map(&String.split/1)
defaults = Enum.filter(routes, &(Enum.at(&1, 1) == "00000000"))
true = Enum.all?(routes, &(hd(&1) == "lo"))
ipv6 = File.read!("/proc/net/ipv6_route")
true = Enum.all?(String.split(ipv6, "\n", trim: true), &(String.split(&1) |> List.last() == "lo"))
status = File.read!("/proc/self/status") |> String.split("\n")
cap = fn key -> Enum.find_value(status, fn line -> case String.split(line, ":", parts: 2) do [^key, value] -> String.trim(value); _ -> nil end end) end
{:ok, netns} = File.read_link("/proc/self/ns/net")
IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(%{"interfaces" => interfaces, "default_routes" => defaults, "routes" => routes, "ipv6_routes" => ipv6, "netns" => netns, "public_address" => "8.8.8.8", "setup_socket_closed" => true, "open_setup_sockets" => 0, "cap_eff" => cap.("CapEff"), "cap_prm" => cap.("CapPrm"), "cap_bnd" => cap.("CapBnd")})))
'''

OBSERVER_EXS = r'''
defmodule MixerIdentityNetworkCollector.Observer do
  use GenServer
  def init(_options) do
    {:ok, output} = File.open("/workspace/evidence/events.jsonl", [:write, :exclusive])
    {:ok, %{output: output, bytes: 0, total: 0, failures: 0, skipped: 0, excluded: 0, invalid: 0}}
  end
  defp record(value, state) do
    line = Jason.encode!(value) <> "\n"
    true = byte_size(line) < 1048576 and state.bytes + byte_size(line) < 2097152
    :ok = IO.binwrite(state.output, line)
    %{state | bytes: state.bytes + byte_size(line)}
  end
  def handle_cast({:suite_started, _}, state), do: {:noreply, record(%{event: "suite_started"}, state)}
  def handle_cast({:test_started, test}, state), do: {:noreply, record(%{event: "test_started", module: Atom.to_string(test.module), name: Atom.to_string(test.name)}, state)}
  def handle_cast({:test_finished, test}, state) do
    category = case test.state do nil -> nil; {kind, _} -> kind; _ -> :failed end
    state = %{state | total: state.total + 1}
    state = case category do
      nil -> state
      :skipped -> %{state | skipped: state.skipped + 1}
      :excluded -> %{state | excluded: state.excluded + 1}
      :invalid -> %{state | invalid: state.invalid + 1}
      _ -> %{state | failures: state.failures + 1}
    end
    {:noreply, record(%{event: "test_finished", module: Atom.to_string(test.module), name: Atom.to_string(test.name), state: if(test.state == nil, do: nil, else: inspect(test.state, limit: 100))}, state)}
  end
  def handle_cast({:suite_finished, _times}, state) do
    modules = for {module, path} <- :code.all_loaded() do
      path = if is_list(path), do: List.to_string(path), else: inspect(path)
      hash = if File.regular?(path), do: Base.encode16(:crypto.hash(:sha256, File.read!(path)), case: :lower), else: nil
      %{module: Atom.to_string(module), path: path, sha256: hash}
    end
    apps = for {app, _description, version} <- :application.loaded_applications(), do: %{application: Atom.to_string(app), version: to_string(version)}
    otp = Path.join([to_string(:code.root_dir()), "releases", to_string(:erlang.system_info(:otp_release)), "OTP_VERSION"])
    identity = %{modules: Enum.sort_by(modules, & &1.module), applications: Enum.sort_by(apps, & &1.application), elixir: System.version(), otp_patch: File.read!(otp) |> String.trim(), vm: to_string(:erlang.system_info(:system_version)), architecture: to_string(:erlang.system_info(:system_architecture)), crypto: inspect(:crypto.info_lib())}
    :ok = File.write!("/workspace/evidence/runtime.json", Jason.encode!(identity, pretty: true), [:exclusive])
    final = state |> Map.take([:total, :failures, :skipped, :excluded, :invalid]) |> Map.put(:event, "suite_finished")
    state = record(final, state)
    :ok = File.close(state.output)
    {:noreply, state}
  end
  def handle_cast(_event, state), do: {:noreply, state}
end
'''

BOOTSTRAP_SH = r'''
set -eu
/usr/local/bin/elixir /workspace/collector-prerequisites.exs
/usr/bin/mkdir -p /workspace/home /workspace/tooling/mix /workspace/tooling/hex /workspace/cache /workspace/downloads /workspace/evidence
/usr/bin/curl --proto '=https' --tlsv1.2 --max-redirs 0 --max-filesize 16777216 --connect-timeout 10 --max-time 25 --fail --silent --show-error --output /workspace/downloads/hex.ez HEX_URL
/usr/bin/curl --proto '=https' --tlsv1.2 --max-redirs 0 --max-filesize 16777216 --connect-timeout 10 --max-time 25 --fail --silent --show-error --output /workspace/downloads/rebar3 REBAR_URL
printf '%s  %s\n%s  %s\n' HEX_SHA /workspace/downloads/hex.ez REBAR_SHA /workspace/downloads/rebar3 | /usr/bin/sha512sum --check --strict
/usr/local/bin/mix archive.install /workspace/downloads/hex.ez --sha512 HEX_SHA --force
/usr/bin/install -m 0755 /workspace/downloads/rebar3 /workspace/tooling/rebar3
/usr/local/bin/elixir -pa '/workspace/tooling/mix/archives/hex-2.5.1/hex-2.5.1/ebin' -e ':ok = Application.load(:hex); "2.5.1" = Application.spec(:hex, :vsn) |> to_string(); {out, 0} = System.cmd(System.fetch_env!("MIX_REBAR3"), ["--version"], stderr_to_stdout: true); true = String.contains?(out, "rebar 3.28.0"); IO.puts(out)'
'''


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def json_marker(output):
    rows = [line.removeprefix(b"IDENTITY_JSON=") for line in output.splitlines() if line.startswith(b"IDENTITY_JSON=")]
    require(len(rows) == 1, "missing/duplicate structured command observation")
    return json.loads(rows[0])


def source_tar(files):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, body in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size, member.mode, member.mtime = len(body), 0o644, 0
            archive.addfile(member, io.BytesIO(body))
    return output.getvalue()


class Collector:
    """One attempt, no retries; command injection permits offline wiring review."""

    def __init__(self, root, output, sha, *, runner=None):
        self.root, self.output, self.sha = Path(root), Path(output), sha
        self.output.mkdir(exist_ok=False, parents=True)
        (self.output / "logs").mkdir()
        (self.output / ".scratch").mkdir()
        self.registry, self.budget = OwnedRegistry(), Budget()
        self.runner = runner
        self.cancelled, self.log_bytes, self.command_number = False, 0, 0
        self.run_id = os.environ.get("GITHUB_RUN_ID", "")
        self.attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
        require(re.fullmatch("[0-9]+", self.run_id or "") and re.fullmatch("[0-9]+", self.attempt or ""), "remote run identity missing")
        self.label = "mixer-identity-net-" + self.run_id + "-" + self.attempt + "-" + uuid.uuid4().hex
        self.state = {"schema": 1, "run_id": self.run_id, "attempt": self.attempt, "sha": sha, "label": self.label, "started_monotonic": self.budget.start, "status": "in-progress", "execution_scope": "two synthetic production-path network methods only; no GA or held-lane acceptance", "cleanup": {"status": "pending"}}
        self.persist()

    def persist(self):
        self.state.update(containers=[dataclasses.asdict(row) for row in self.registry.records], unresolved_creates=self.registry.unresolved, log_bytes=self.log_bytes, command_number=self.command_number, cancelled=self.cancelled)
        write_json(self.output / "state.json", self.state)

    def command(self, argv, timeout=15, *, input_bytes=None, limit=MAX_COMMAND_BYTES, binary_path=None, cleanup=False, check=True):
        require(cleanup or not self.cancelled, "cancelled; no new work")
        require(isinstance(argv, list) and all(isinstance(v, str) for v in argv), "argv must be literal strings")
        timeout = self.budget.remaining(timeout, cleanup=cleanup)
        self.command_number += 1
        stem = self.output / "logs" / f"{self.command_number:04d}"
        row = {"argv": argv, "cwd": str(self.root), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "timeout_seconds": timeout, "stdin_bytes": len(input_bytes or b""), "stdin_sha256": hashlib.sha256(input_bytes).hexdigest() if input_bytes is not None else None, "stdout_complete": False, "stderr_complete": False}
        started = time.monotonic()
        out, err, process, overflow, timed_out = bytearray(), bytearray(), None, False, False
        # Deliberately excludes caller Docker config, startup flags and credentials.
        environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(self.output / ".scratch"), "DOCKER_CONFIG": str(self.output / ".scratch" / "docker"), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
        row["host_environment"] = environment
        try:
            if self.runner is not None:
                code, stdout, stderr = self.runner(argv, timeout, input_bytes)
                out.extend(stdout)
                err.extend(stderr)
                overflow = len(out) + len(err) > limit
            else:
                process = subprocess.Popen(argv, cwd=self.root, env=environment, stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=False)
                with selectors.DefaultSelector() as selected:
                    for pipe, kind in ((process.stdout, "stdout"), (process.stderr, "stderr")):
                        os.set_blocking(pipe.fileno(), False)
                        selected.register(pipe, selectors.EVENT_READ, kind)
                    pending = memoryview(input_bytes or b"")
                    if process.stdin is not None:
                        os.set_blocking(process.stdin.fileno(), False)
                        selected.register(process.stdin, selectors.EVENT_WRITE, "stdin")
                    while selected.get_map():
                        if time.monotonic() - started >= timeout or (self.cancelled and not cleanup):
                            timed_out = True
                            break
                        for key, _ in selected.select(min(0.1, max(0, timeout - (time.monotonic() - started)))):
                            if key.data == "stdin":
                                if pending:
                                    try:
                                        consumed = os.write(key.fileobj.fileno(), pending[:65536])
                                        pending = pending[consumed:]
                                    except BrokenPipeError:
                                        pending = pending[:0]
                                if not pending:
                                    selected.unregister(key.fileobj)
                                    key.fileobj.close()
                                continue
                            chunk = os.read(key.fileobj.fileno(), 65536)
                            if not chunk:
                                selected.unregister(key.fileobj)
                                key.fileobj.close()
                            else:
                                target = out if key.data == "stdout" else err
                                if len(out) + len(err) + len(chunk) > limit:
                                    overflow = True
                                    break
                                target.extend(chunk)
                        if overflow:
                            break
                if timed_out or overflow:
                    process.terminate()  # Only this direct CLI child, never a process group.
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=1)
                else:
                    process.wait(timeout=max(0.01, timeout - (time.monotonic() - started)))
                code = process.returncode
            row.update(exit_code=code, stdout_complete=not (overflow or timed_out), stderr_complete=not (overflow or timed_out), overflow=overflow, timed_out=timed_out, elapsed_seconds=time.monotonic() - started, stdout_bytes=len(out), stderr_bytes=len(err))
            if binary_path is not None:
                Path(binary_path).write_bytes(out)
                row["stdout_artifact"] = str(Path(binary_path).relative_to(self.output))
                row["stdout_sha256"] = hashlib.sha256(out).hexdigest()
            else:
                self.log_bytes += len(out)
                stem.with_suffix(".stdout").write_bytes(out)
            self.log_bytes += len(err)
            stem.with_suffix(".stderr").write_bytes(err)
            require(self.log_bytes <= MAX_LOG_BYTES, "aggregate raw log cap reached")
            require(not overflow and not timed_out, "command timeout/output incomplete")
            if check:
                validate_command_result(code, out, err, limit=limit)
            return bytes(out), bytes(err), code
        except BaseException as error:
            row["failure"] = str(error)
            row["stdout_complete"], row["stderr_complete"] = False, False
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
            raise
        finally:
            if process is not None:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    if pipe is not None and not pipe.closed:
                        pipe.close()
            write_json(stem.with_suffix(".json"), row)
            self.persist()

    def git_blobs(self, paths):
        raw, _, _ = self.command(["git", "--no-replace-objects", "cat-file", "--batch"], input_bytes="".join(self.sha + ":" + path + "\n" for path in paths).encode())
        result, cursor = {}, 0
        for path in paths:
            end = raw.index(b"\n", cursor)
            header = raw[cursor:end].split()
            require(len(header) == 3 and header[1] == b"blob" and header[2].isdigit(), "missing/nonblob delivered input: " + path)
            size = int(header[2])
            cursor = end + 1
            result[path] = raw[cursor:cursor + size]
            cursor += size
            require(raw[cursor:cursor + 1] == b"\n", "git batch framing")
            cursor += 1
        require(cursor == len(raw), "extra git blobs")
        return result

    def inspect(self, owned, cleanup=False):
        require(owned.state == "owned", "sticky owned identity loss; no retry")
        try:
            output, _, _ = self.command(["docker", "container", "inspect", owned.cid], cleanup=cleanup)
            rows = json.loads(output)
            require(len(rows) == 1, "inspect count mismatch")
            validate_owned_identity(rows[0], owned)
        except BaseException as error:
            self.registry.refuse(owned.cid, str(error))
            self.persist()
            raise
        if not cleanup:
            test = next((row.cid for row in self.registry.records if row.role == "test"), None)
            validate_container_inspect(owned.role, rows[0], owned, test)
        return rows[0]

    def docker(self, owned, argv, timeout=15, **options):
        self.inspect(owned, cleanup=options.get("cleanup", False))
        try:
            return self.command(["docker", *argv, owned.cid], timeout, **options)
        except CollectorError as error:
            # Permission/identity uncertainty is sticky; no other actor or route.
            recent = (self.output / "logs" / f"{self.command_number:04d}.stderr").read_bytes().lower()
            if any(word in recent for word in (b"permission denied", b"operation not permitted", b"access denied")):
                self.registry.refuse(owned.cid, str(error))
                self.persist()
            raise

    def execute(self, owned, argv, timeout=15, *, environment=None, check=True, **options):
        self.inspect(owned)
        env = environment or BASE_ENV
        args = ["docker", "exec", "--workdir", "/" if owned.role == "pg" else "/workspace/hosted"]
        args += [part for key, value in sorted(env.items()) for part in ("--env", key + "=" + value)]
        args += [owned.cid, "/usr/bin/env", "-i", *[key + "=" + value for key, value in sorted(env.items())], *argv]
        try:
            return self.command(args, timeout, check=check, **options)
        except CollectorError:
            recent = (self.output / "logs" / f"{self.command_number:04d}.stderr").read_bytes().lower()
            if any(word in recent for word in (b"permission denied", b"operation not permitted", b"access denied")):
                self.registry.refuse(owned.cid, "Docker exec permission refusal")
            raise

    def create(self, role, test_cid=None):
        image = IMAGES["pg" if role == "pg" else "test"]
        name = self.label + "-" + role
        self.registry.reserve(name, role, image["config"], self.label)
        self.persist()  # Reservation precedes the possibly lost create response.
        memory, cpus, pids = RESOURCES[role]
        argv = ["docker", "create", "--pull", "never", "--platform", "linux/amd64", "--name", name, "--label", "mixer.identity.run=" + self.label, "--label", "mixer.identity.role=" + role, "--network", "container:" + test_cid if role == "pg" else ("none" if role == "test" else "default"), "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--memory", str(memory), "--memory-swap", str(memory), "--cpus", str(cpus), "--pids-limit", str(pids), "--ulimit", "nofile=4096:4096"]
        for cap in sorted(CAPS[role]):
            argv += ["--cap-add", cap]
        for path, options in TMPFS[role].items():
            argv += ["--tmpfs", path + ":" + options]
        env = {"POSTGRES_USER": "mixer_fixture", "POSTGRES_DB": "mixer_startup_test", "POSTGRES_HOST_AUTH_METHOD": "trust"} if role == "pg" else BASE_ENV
        for key, value in sorted(env.items()):
            argv += ["--env", key + "=" + value]
        if role != "pg":
            argv += ["--entrypoint", "/usr/local/bin/elixir", image["config"], "-e", "Process.sleep(:infinity)"]
        else:
            argv += [image["config"], "-c", "listen_addresses=127.0.0.1", "-c", "timezone=UTC"]
        try:
            output, _, _ = self.command(argv)
            row = self.registry.add(output.decode().strip(), name, role, image["config"], self.label)
        except BaseException as error:
            self.registry.creation_unknown(name, str(error))
            self.persist()
            raise
        self.persist()
        self.inspect(row)
        return row

    def copy_in(self, owned, data):
        self.inspect(owned)
        self.command(["docker", "cp", "-", owned.cid + ":/workspace"], 30, input_bytes=data)

    def copy_file_out(self, owned, path, maximum=MAX_COMMAND_BYTES):
        require(path in {"/workspace/prepared.tar", "/workspace/downloads/hex.ez", "/workspace/tooling/rebar3"} or path.startswith("/workspace/evidence/"), "unreviewed copy-out path")
        require(0 < maximum <= MAX_ARCHIVE_BYTES, "copy-out cap")
        literal = "path = " + json.dumps(path) + "; true = File.stat!(path).size <= " + str(maximum) + "; IO.binwrite(File.read!(path))"
        scratch = self.output / ".scratch" / "copy.bin"
        result, _, _ = self.execute(owned, ["/usr/local/bin/elixir", "-e", literal], 30, limit=maximum, binary_path=scratch)
        scratch.unlink()
        return result

    def stop_remove(self, owned):
        self.inspect(owned, cleanup=True)
        self.docker(owned, ["stop", "--time", "2"], cleanup=True)
        terminal = self.inspect(owned, cleanup=True)
        require(terminal.get("State", {}).get("Running") is False, "container still running after stop")
        write_json(self.output / (owned.role + "-terminal.json"), terminal)
        self.docker(owned, ["logs"], cleanup=True, check=False)
        self.docker(owned, ["rm", "--volumes"], cleanup=True)
        try:
            output, stderr, code = self.command(["docker", "container", "inspect", owned.cid], cleanup=True, check=False)
            require(code != 0 and b"No such container" in stderr and not any(word in stderr.lower() for word in (b"permission", b"operation not permitted", b"access denied")), "exact CID absence not observed")
        except BaseException as error:
            self.registry.refuse(owned.cid, "post-remove absence unknown: " + str(error))
            self.persist()
            raise
        owned.state = "removed"
        self.persist()

    def cleanup(self):
        errors = []
        for role in ("pg", "test", "prepare"):
            for row in self.registry.records:
                if row.role == role and row.state == "owned":
                    try:
                        self.stop_remove(row)
                    except BaseException as error:
                        errors.append({"cid": row.cid, "role": role, "failure": str(error)})
        clean = not errors and not self.registry.unresolved and all(row.state == "removed" for row in self.registry.records)
        self.state["cleanup"] = {"status": "verified-exact-created-IDs-absent" if clean else "FAILED-unknown-or-incomplete", "errors": errors, "unresolved_creates": self.registry.unresolved, "container_teardown_is_product_lifecycle_proof": False}
        self.persist()
        return clean

    def seal(self):
        scratch = self.output / ".scratch"
        if scratch.exists():
            shutil.rmtree(scratch)  # Only the output directory exclusively created above.
        self.state["host_scratch_cleanup"] = "removed owned .scratch; package outputs retained"
        self.persist()
        paths = [p for p in self.output.rglob("*") if p.is_file() and p.name != "artifact-manifest.json"]
        total = sum(p.stat().st_size for p in paths)
        if total > MAX_ARTIFACT_BYTES:
            self.state["status"] = "FAILED-artifact-cap"
            self.state["artifact_cap_exceeded_bytes"] = total
            # Retain failure receipts and hashes; do not upload an unbounded archive.
            for path in paths:
                if path.name.endswith(".tar"):
                    self.state.setdefault("omitted_oversize_archives", []).append({"path": str(path.relative_to(self.output)), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                    path.unlink()
            self.persist()
            paths = [p for p in self.output.rglob("*") if p.is_file() and p.name != "artifact-manifest.json"]
        files = {str(p.relative_to(self.output)): {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths}
        write_json(self.output / "artifact-manifest.json", {"schema": 1, "files": files, "tree_digest_sha256": canonical_digest(files), "scope": self.state["execution_scope"]})

    def run(self):
        """Freeze primary outcome before finally; cleanup can only reduce qualification."""
        try:
            self.collect()
            self.state["status"] = "two-methods-passed-pending-owned-cleanup-and-independent-acceptance"
        except BaseException as error:
            self.state["status"] = "FAILED-or-partial"
            self.state["primary_failure"] = {"type": type(error).__name__, "message": str(error)}
        finally:
            self.state["primary_outcome_frozen"] = True
            self.persist()
            clean = self.cleanup()
            if not clean:
                self.state["status"] = "FAILED-cleanup-unknown-or-incomplete"
            self.seal()
        return 0 if self.state["status"] == "two-methods-passed-pending-owned-cleanup-and-independent-acceptance" else 1

    def collect(self):
        require(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_OS") == "Linux" and os.environ.get("RUNNER_ARCH") == "X64", "only selected GitHub Linux AMD64 runner is supported")
        require(os.uname().sysname == "Linux" and os.uname().machine == "x86_64", "actual host platform mismatch")
        validate_environment(os.environ)
        require(re.fullmatch("[0-9a-f]{40}", self.sha), "delivery SHA must be exact")
        head, _, _ = self.command(["git", "--no-replace-objects", "rev-parse", "HEAD"])
        require(head.decode().strip() == self.sha, "checkout delivery revision mismatch")
        validate_source_manifest(FROZEN_MANIFEST)
        product = self.git_blobs(sorted(FROZEN_MANIFEST))
        observed = {path: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for path, body in product.items()}
        validate_source_manifest(observed)  # All static product/lock checks precede create/pull.
        self.state["source"] = {"delivery_revision": self.sha, "frozen_product_commit": PRODUCT_COMMIT, "product_files": len(observed), "product_tree_digest_sha256": canonical_digest(observed), "lock_sha256": FROZEN_LOCK_SHA256}
        write_json(self.output / "product-source-manifest.json", observed)
        control_paths = ["hosted/scripts/test-identity-network.py", "hosted/scripts/test_identity_network_collector.py", "docs/hosted-identity-production-network-ci-contract.md", ".github/workflows/identity-network.yml"]
        controls = self.git_blobs(control_paths)
        for path, body in controls.items():
            require((self.root / path).read_bytes() == body, "dirty delivered collector/control/workflow: " + path)
        write_json(self.output / "collector-source-bindings.json", {path: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for path, body in controls.items()})
        (self.output / "collector-source.tar").write_bytes(source_tar(controls))
        packet_base = "verification/identity-production-network-contract/"
        packet_paths = [packet_base + "contract.json", packet_base + "packet-manifest.json"]
        for image in ("elixir", "postgres"):
            packet_paths += [packet_base + "inputs/registry/" + image + suffix for suffix in ("-index.json", "-amd64-manifest.json", "-amd64-config.json")]
        metadata = self.git_blobs(packet_paths)
        require(hashlib.sha256(metadata[packet_base + "contract.json"]).hexdigest() == CONTRACT_SHA256, "selected contract drift")
        packet = json.loads(metadata[packet_base + "packet-manifest.json"])
        require(packet["tree_digest_sha256"] == CONTRACT_PACKET and canonical_digest(packet["files"]) == CONTRACT_PACKET, "contract packet seal mismatch")
        for path, body in metadata.items():
            if path != packet_base + "packet-manifest.json":
                expected = packet["files"][path.removeprefix(packet_base)]
                require(expected == {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}, "frozen metadata hash mismatch")
        (self.output / "selected-contract-metadata.tar").write_bytes(source_tar(metadata))
        for label, role in (("elixir", "test"), ("postgres", "pg")):
            image = IMAGES[role]
            for suffix, digest in (("-amd64-manifest.json", image["ref"].split("@sha256:")[1]), ("-amd64-config.json", image["config"].removeprefix("sha256:"))):
                require(hashlib.sha256(metadata[packet_base + "inputs/registry/" + label + suffix]).hexdigest() == digest, "static manifest/config pin mismatch")
        write_json(self.output / "host.json", {"uname": list(os.uname()), "python": sys.version, "netns": os.readlink("/proc/self/ns/net"), "runner": "ubuntu-24.04", "github_run_id": self.run_id, "attempt": self.attempt})
        self.command(["git", "--version"])
        self.command(["docker", "version", "--format", "{{json .}}"])
        # Both pulls are completed before any preparation container is created.
        for role in ("test", "pg"):
            image = IMAGES[role]
            self.command(["docker", "pull", "--platform", "linux/amd64", image["ref"]], 120)
            inspected, _, _ = self.command(["docker", "image", "inspect", image["ref"]])
            rows = json.loads(inspected)
            require(len(rows) == 1, "image inspect count")
            validate_image_inspect(role, rows[0])
            write_json(self.output / (role + "-image.json"), rows[0])
        helpers = {"collector-prerequisites.exs": PREREQUISITES_EXS.encode(), "collector-manifest.exs": MANIFEST_EXS.encode(), "collector-netns.exs": NETNS_EXS.encode(), "collector-observer.exs": OBSERVER_EXS.encode(), "frozen-manifest.json": json.dumps(FROZEN_MANIFEST, sort_keys=True, separators=(",", ":")).encode()}
        write_json(self.output / "literal-helper-bindings.json", {path: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for path, body in helpers.items()})
        (self.output / "literal-helpers.tar").write_bytes(source_tar(helpers))
        prepare = self.create("prepare")
        validate_container_environment("prepare", self.inspect(prepare))
        self.docker(prepare, ["start"])
        self.copy_in(prepare, source_tar({**product, **helpers}))
        script = BOOTSTRAP_SH
        for placeholder, value in {"HEX_URL": BOOTSTRAP["hex"]["url"], "HEX_SHA": BOOTSTRAP["hex"]["sha512"], "REBAR_URL": BOOTSTRAP["rebar"]["url"], "REBAR_SHA": BOOTSTRAP["rebar"]["sha512"]}.items():
            script = script.replace(placeholder, value)
        write_json(self.output / "bootstrap-plan.json", {"argv": ["/bin/sh", "-eu", "-c", script], "tool_destination": BASE_ENV["MIX_REBAR3"], "helper_sha256": hashlib.sha256(PREREQUISITES_EXS.encode()).hexdigest(), "no_package_install_or_fallback": True})
        bootstrap, _, _ = self.execute(prepare, ["/bin/sh", "-eu", "-c", script], 60)
        write_json(self.output / "prepare-prerequisites.json", json_marker(bootstrap))
        for tool, path, filename in (("hex", "/workspace/downloads/hex.ez", "bootstrap-hex-2.5.1.ez"), ("rebar", "/workspace/tooling/rebar3", "bootstrap-rebar-3.28.0")):
            artifact = self.copy_file_out(prepare, path, 16777216)
            require(hashlib.sha512(artifact).hexdigest() == BOOTSTRAP[tool]["sha512"], "observed bootstrap artifact digest mismatch")
            (self.output / filename).write_bytes(artifact)
        self.execute(prepare, ["/usr/local/bin/mix", "deps.get", "--check-locked"], 120)
        manifest_output, _, _ = self.execute(prepare, ["/usr/local/bin/elixir", "/workspace/collector-manifest.exs", "archive-list"])
        prepared_manifest = json_marker(manifest_output)
        require(prepared_manifest["source"] == FROZEN_MANIFEST, "prepare source changed")
        write_json(self.output / "prepared-manifest.json", prepared_manifest)
        self.execute(prepare, ["/usr/bin/tar", "--format=ustar", "--sort=name", "--mtime=@0", "--owner=0", "--group=0", "--numeric-owner", "--no-recursion", "-cf", "/workspace/prepared.tar", "-C", "/workspace", "-T", "/workspace/archive-files.txt"], 30)
        prepared = self.copy_file_out(prepare, "/workspace/prepared.tar", MAX_ARCHIVE_BYTES)
        validate_prepared_archive(prepared, prepared_manifest)
        (self.output / "prepared-source-dependencies-tools.tar").write_bytes(prepared)
        self.stop_remove(prepare)  # No networked namespace remains at test creation.
        require(prepare.state == "removed", "prepare removal missing")
        test = self.create("test")
        validate_container_environment("test", self.inspect(test))
        self.docker(test, ["start"])
        self.copy_in(test, prepared)
        self.execute(test, ["/usr/local/bin/elixir", "-e", 'for path <- ["/workspace/home", "/workspace/tooling/hex", "/workspace/cache", "/workspace/evidence", "/workspace/evidence/identity"], do: File.mkdir!(path)'])
        actual_prerequisites, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-prerequisites.exs"])
        write_json(self.output / "test-prerequisites.json", json_marker(actual_prerequisites))
        restored_output, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-manifest.exs"])
        restored = json_marker(restored_output)
        validate_source_unchanged(prepared_manifest, restored)
        host_netns = os.readlink("/proc/self/ns/net")
        namespace_output, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-netns.exs"])
        namespace = validate_namespace(json_marker(namespace_output), host_netns)
        write_json(self.output / "test-namespace.json", namespace)
        pg = self.create("pg", test.cid)
        validate_container_environment("pg", self.inspect(pg))
        self.docker(pg, ["start"])
        pg_netns, _, _ = self.execute(pg, ["/usr/bin/readlink", "/proc/self/ns/net"], environment=PG_ENV)
        require(pg_netns.decode().strip() == namespace["netns"], "PostgreSQL namespace differs from exact test namespace")
        pg_version, _, _ = self.execute(pg, ["/usr/lib/postgresql/16/bin/postgres", "--version"], environment=PG_ENV)
        require(b"PostgreSQL) 16.15" in pg_version, "PostgreSQL executable version mismatch")
        ready_until = time.monotonic() + min(30, self.budget.remaining(30))
        ready = False
        while time.monotonic() < ready_until:
            _, _, result = self.execute(pg, ["/usr/lib/postgresql/16/bin/pg_isready", "-h", "127.0.0.1", "-U", "mixer_fixture", "-d", "mixer_startup_test", "-t", "1"], min(3, max(.01, ready_until - time.monotonic())), environment=PG_ENV, check=False)
            if result == 0:
                ready = True
                break
            require(result in {1, 2}, "PostgreSQL readiness error")
            time.sleep(min(.25, max(0, ready_until - time.monotonic())))
        require(ready and time.monotonic() <= ready_until, "PostgreSQL readiness bound reached")
        sql = "SELECT json_build_object('server_version_num',current_setting('server_version_num'),'timezone',current_setting('TimeZone'),'database',current_database(),'databases',(SELECT json_agg(datname ORDER BY datname) FROM pg_database));"
        database = self.pg_query(pg, sql)
        require(database == {"server_version_num": "160015", "timezone": "UTC", "database": "mixer_startup_test", "databases": ["mixer_startup_test", "postgres", "template0", "template1"]}, "private PostgreSQL scope/version mismatch")
        write_json(self.output / "database-before.json", database)
        status, _, _ = self.execute(pg, ["/usr/bin/cat", "/proc/1/status"], environment=PG_ENV)
        uid = next((line.split()[1:] for line in status.decode().splitlines() if line.startswith("Uid:")), [])
        require(len(uid) == 4 and all(value.isdigit() and int(value) > 0 for value in uid), "PostgreSQL remains root")
        write_json(self.output / "postgres-process.json", {"namespace": pg_netns.decode().strip(), "uid_fields": uid, "version": pg_version.decode()})
        offline_until = time.monotonic() + min(180, self.budget.remaining(180))
        def offline_timeout():
            left = offline_until - time.monotonic()
            require(left > 0, "offline compile/two-test phase aggregate bound reached")
            return left
        self.execute(test, ["/usr/local/bin/mix", "deps.compile"], offline_timeout())
        self.execute(test, ["/usr/local/bin/mix", "compile", "--warnings-as-errors"], offline_timeout())
        before_output, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-manifest.exs"], min(15, offline_timeout()))
        before_tests = json_marker(before_output)
        validate_source_unchanged(prepared_manifest, before_tests)
        write_json(self.output / "before-tests-manifest.json", before_tests)
        compiled_output, _, _ = self.execute(test, ["/usr/local/bin/elixir", "-e", 'rows = Map.new(Path.wildcard("/workspace/hosted/_build/test/lib/*/ebin/*.beam"), fn path -> {path, Base.encode16(:crypto.hash(:sha256, File.read!(path)), case: :lower)} end); true = map_size(rows) > 0; IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(rows)))'], min(15, offline_timeout()))
        write_json(self.output / "compiled-modules-before-tests.json", json_marker(compiled_output))
        validate_container_environment("test", self.inspect(test))
        validate_container_environment("pg", self.inspect(pg))
        fresh_namespace, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-netns.exs"], min(15, offline_timeout()))
        validate_namespace(json_marker(fresh_namespace), host_netns)
        # The flag is constructed here only, after actual source/tool/isolation checks.
        flag_env = {**TEST_ENV, "MIXER_ISOLATED_NETNS": "1"}
        write_json(self.output / "test-authorization.json", {"allowed_environment": flag_env, "owned_test_cid": test.cid, "owned_pg_cid": pg.cid, "actual_namespace": namespace["netns"], "source_unchanged": True, "prerequisites_observed": True, "assertions_before_flag": True})
        argv = ["/usr/local/bin/elixir", "-r", "/workspace/collector-observer.exs", "-S", "mix", "test", "--warnings-as-errors", "--seed", "0", "--trace", "--no-color", "--formatter", "ExUnit.CLIFormatter", "--formatter", "MixerIdentityNetworkCollector.Observer", *TEST_ROOTS]
        _, _, test_exit = self.execute(test, argv, offline_timeout(), environment=flag_env, check=False)
        require(time.monotonic() <= offline_until, "offline phase deadline exceeded")
        events_bytes = self.copy_file_out(test, "/workspace/evidence/events.jsonl", 2097152)
        (self.output / "observer-events.jsonl").write_bytes(events_bytes)
        semantic = {}
        for name in SEMANTICS:
            body = self.copy_file_out(test, "/workspace/evidence/identity/" + name)
            (self.output / name).write_bytes(body)
            semantic[name] = json.loads(body)
        runtime_body = self.copy_file_out(test, "/workspace/evidence/runtime.json")
        (self.output / "loaded-runtime.json").write_bytes(runtime_body)
        runtime = json.loads(runtime_body)
        require(runtime.get("elixir") == "1.20.4" and runtime.get("otp_patch") == "29.1.1" and "x86_64" in runtime.get("architecture", ""), "observed test VM identity mismatch")
        require(any(row.get("module") == "Elixir.MixerHosted.Identity.KeyOwner" and row.get("sha256") and row.get("path", "").startswith("/workspace/hosted/_build/test/") for row in runtime.get("modules", [])), "loaded product module identity missing")
        events = [json.loads(line) for line in events_bytes.splitlines()]
        result = validate_events(events, test_exit, semantic)
        after_output, _, _ = self.execute(test, ["/usr/local/bin/elixir", "/workspace/collector-manifest.exs"])
        after_tests = json_marker(after_output)
        validate_source_unchanged(before_tests, after_tests)
        write_json(self.output / "after-tests-manifest.json", after_tests)
        keydirs, _, _ = self.execute(test, ["/usr/local/bin/elixir", "-e", 'dirs = Path.wildcard("/tmp/mixer-key-owner-tls-*"); IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(%{"remaining_key_directories" => dirs})))'])
        key_evidence = json_marker(keydirs)
        require(key_evidence == {"remaining_key_directories": []}, "synthetic key directories remain")
        write_json(self.output / "key-directory-cleanup.json", key_evidence)
        applied = self.pg_query(pg, "SELECT json_agg(version ORDER BY version) FROM schema_migrations;")
        expected_migrations = sorted(int(PurePosixPath(path).name.split("_")[0]) for path in FROZEN_MANIFEST if path.startswith("hosted/priv/repo/migrations/") and path.endswith(".exs"))
        require(len(expected_migrations) == 10 and applied == expected_migrations, "actual current ten migrations differ")
        write_json(self.output / "applied-migrations.json", {"database": "mixer_startup_test", "versions": applied})
        self.state["test_result"] = result
        self.state["limitations"] = ["Ordinary remote synthetic fixture scope only; no syscall/child-command custody trace", "Existing TLSFixture discards successful OpenSSL child output; executable/parent trace/assertions retained", "No real provider/browser/Neon/Cloudflare/native/physical/GA qualification", "No new production release/exclusion run; root must separately accept exact unchanged-product evidence reuse", "Host loss/hard cancellation can prevent cleanup or upload; missing evidence is unqualified", "Independent root artifact download, digest validation and acceptance remain required"]
        self.persist()

    def pg_query(self, pg, sql):
        output, _, _ = self.execute(pg, ["/usr/lib/postgresql/16/bin/psql", "--no-psqlrc", "--set", "ON_ERROR_STOP=1", "--host", "127.0.0.1", "--username", "mixer_fixture", "--dbname", "mixer_startup_test", "--tuples-only", "--no-align", "--command", sql], environment=PG_ENV)
        return json.loads(output)


# Frozen ordinary product blobs; collector/control source is separately bound.
FROZEN_MANIFEST = {'hosted/.formatter.exs': {'bytes': 74, 'sha256': '0d5f1f1bc0a4d678629084c6f15f96e000b4882594bc829f2adf5eacc9ff42b5'}, 'hosted/.gitignore': {'bytes': 40, 'sha256': '363721e50c7313c16377d1d426ffbef80e6a0ff5943fb500c4a6f96917f336e5'}, 'hosted/.tool-versions': {'bytes': 35, 'sha256': '6286da51456f864e5f1d8f2280e6de86d6fb1ee4517c40819760ec54d203c846'}, 'hosted/README.md': {'bytes': 4195, 'sha256': 'b9e4e05d585bc493d40ff5c5843d9a911667656710087705650622fd79d0c663'}, 'hosted/config/config.exs': {'bytes': 431, 'sha256': '6510b5e0f5eecb2ced799250d7bdcef91b8f8278e19e2c886c60dd624443005c'}, 'hosted/config/runtime.exs': {'bytes': 549, 'sha256': '73cd8edac21bb64c3fba3cd81bb461f2cee651b9f799bd42bfac3e5ffeca6e9f'}, 'hosted/lib/mixer_hosted/application.ex': {'bytes': 1278, 'sha256': 'bbf02752b982e1437564c266772cd4e5dd7190670a575dd6676dda7fc692803f'}, 'hosted/lib/mixer_hosted/audit/customer_artifact_event.ex': {'bytes': 17388, 'sha256': '6e8450558d71af3d0940e7ca7a5725f7bdbc1ad834f4619f9008d8d196976942'}, 'hosted/lib/mixer_hosted/audit/upload_event.ex': {'bytes': 12893, 'sha256': 'daff6c6084be7094bc1a2b97ae386d5fcd4390e245c99f6de77f09572c07f6ad'}, 'hosted/lib/mixer_hosted/authorization.ex': {'bytes': 4183, 'sha256': 'ac5b8a0ed8edc40598d8b02036066460fa8ce7d4cb55abbd05229d18a18a10d3'}, 'hosted/lib/mixer_hosted/authorization/artifact_read.ex': {'bytes': 7879, 'sha256': 'e5b5760c7d81204d9e2ca6a9bf89b1317e8dbbb2353ae39c9171b17e9bd44ef0'}, 'hosted/lib/mixer_hosted/authorization/policy.ex': {'bytes': 14476, 'sha256': '53a60ab1055d82d3bfc3e89bf67925b190fb3f6feb5a9e326a58b935b78f94d1'}, 'hosted/lib/mixer_hosted/authorization/postgres/evidence.ex': {'bytes': 6737, 'sha256': 'fe5e34d6e66b84aa6f4786c7922eeb75faf5d2b142de82d17f184b5b08fff1f7'}, 'hosted/lib/mixer_hosted/authorization/postgres/session.ex': {'bytes': 6489, 'sha256': '8ae27291a2e0777dfde6f995cf8c1a64c6ac8e2e7b0e7660afdb7cac76382727'}, 'hosted/lib/mixer_hosted/authorization/postgres_repository.ex': {'bytes': 3112, 'sha256': '78b77db112d0fb45e0bd645e91049daf016867f5086a4c07d373b7e88fab384b'}, 'hosted/lib/mixer_hosted/authorization/repository.ex': {'bytes': 3591, 'sha256': '76a24ec22292193f5d1ba26ad17711645662939db2b8fe988ea84b3614d1de00'}, 'hosted/lib/mixer_hosted/authorization/scope.ex': {'bytes': 2264, 'sha256': 'b98c7c6f2f3592bf2fcfd0890d86bb503e3c9cdd6558fa1c7b0766ddb61c7b7a'}, 'hosted/lib/mixer_hosted/authorization/transaction/context.ex': {'bytes': 6912, 'sha256': '36c10584932aca726e855891f8c7ef54e35a19625a922cc779fe0eb6238b0bfc'}, 'hosted/lib/mixer_hosted/authorization/transaction/snapshot.ex': {'bytes': 12313, 'sha256': '39bae74a8022ea9884874f8e457568a073fd798fa87ebf901e9b896062528599'}, 'hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex': {'bytes': 7827, 'sha256': 'a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea'}, 'hosted/lib/mixer_hosted/billing/webhook_signature.ex': {'bytes': 4549, 'sha256': '3fa0a2d8bee3e4eb9a4204857aaec0d16565df7c0d3f0aa8062158d51f2e3cb6'}, 'hosted/lib/mixer_hosted/billing/webhook_transport.ex': {'bytes': 22396, 'sha256': '56a26cf3a56f3e5a5b2d8f5104fc7c3371b0e44918b007197be5871cf94ef1a5'}, 'hosted/lib/mixer_hosted/browser_auth/activation_preparation.ex': {'bytes': 2543, 'sha256': 'e208e159719dd29ff75186667404cb6018391a2ecc3b8a3534db131d1bc281f5'}, 'hosted/lib/mixer_hosted/browser_auth/activation_preparation_schema.ex': {'bytes': 19706, 'sha256': 'd58bc6009d6118ba9469f087af99e893df6a99038cdccec11ba5048d48bf4ae8'}, 'hosted/lib/mixer_hosted/browser_auth/catalog.ex': {'bytes': 23235, 'sha256': '6d568887deabc3d573462b7ecd038444bc07e985ee4a9e1f32e6fb4a3ef268af'}, 'hosted/lib/mixer_hosted/browser_auth/catalog_manifest.ex': {'bytes': 3589, 'sha256': '3508c85922a1a716d39eb61ecb5daa699d6141b1aeb88a9565512c78465d1269'}, 'hosted/lib/mixer_hosted/browser_auth/catalog_manifest_v2.ex': {'bytes': 4450, 'sha256': '0c4e4c0186a57979182b90eb4b6e852b8b2b40d9e894bede0e95e382dfc7a8ea'}, 'hosted/lib/mixer_hosted/browser_auth/config.ex': {'bytes': 8033, 'sha256': 'f9e9f1cac7083fbcb282c4a150e65a646228f005522a0b212e602b6495ab588d'}, 'hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex': {'bytes': 2813, 'sha256': 'a2166f04006293598fcb073a2f8e90170a839c2b5d0cc3ecb754bfd8c4d41532'}, 'hosted/lib/mixer_hosted/browser_auth/custody.ex': {'bytes': 1515, 'sha256': '675429fa3daf5c84cf8ee8223aeeea6842889af859a6468c763ffc0ea6033803'}, 'hosted/lib/mixer_hosted/browser_auth/lifecycle_repo.ex': {'bytes': 1683, 'sha256': '66c27f0cac41d04b754532df397ace17370436af7b68707d0d8216dddc4918f9'}, 'hosted/lib/mixer_hosted/browser_auth/preauth_draft.ex': {'bytes': 1569, 'sha256': '143f34f3c0810e290b4ccfa4460b86fee0482b33573a6fc604aeeac27498cbbd'}, 'hosted/lib/mixer_hosted/browser_auth/protocol.ex': {'bytes': 10422, 'sha256': 'a569cabebfd905f1f717137b9180ff5ae47fffb747a9b5e45f049f03b3da3428'}, 'hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex': {'bytes': 47573, 'sha256': 'f71d79b92065d2137363f10de89c137b95ce5758b0e4c21b88faaeb8a779fcfc'}, 'hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex': {'bytes': 1463, 'sha256': '6e6fd520d4b3e37af2d4c3c5cd4c40caf7a1cadc473baed6246db05a49df35da'}, 'hosted/lib/mixer_hosted/browser_auth/runtime_config.ex': {'bytes': 7874, 'sha256': '0ce7e28450b7f5652313fc22cb909ea6e65cc8b4a8edcc960669d5a950da0962'}, 'hosted/lib/mixer_hosted/browser_auth/runtime_owner.ex': {'bytes': 20613, 'sha256': '007ab3e8445820318ed503337b0c2693d0e703227eb8b0202d21cd1330666580'}, 'hosted/lib/mixer_hosted/browser_auth/storage_schema.ex': {'bytes': 63975, 'sha256': '676bb977bbe4c322caf63c1a5f40d86e7861847636029948b55cb01f6dedb6dd'}, 'hosted/lib/mixer_hosted/browser_auth/store.ex': {'bytes': 20860, 'sha256': '6c02fff8454790449b3ebe70695fc3adfd537d899b24411ee6585171578c8e43'}, 'hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex': {'bytes': 9927, 'sha256': 'ce92f99c3990bf9ddd0fbf5d8c7d329ea63bb5dc31ec3df4922907b19986cd3e'}, 'hosted/lib/mixer_hosted/browser_auth/vault.ex': {'bytes': 10754, 'sha256': 'e376cdd7305a520c61e716e3f4fcd3f5493e280ff5424ba822516f9a6f4281b2'}, 'hosted/lib/mixer_hosted/builds/admission.ex': {'bytes': 26456, 'sha256': '87bd56955fa99c2978a407c74cfcc87819ac6059a0bc4a86a36df763424ab0eb'}, 'hosted/lib/mixer_hosted/builds/coordinator.ex': {'bytes': 12726, 'sha256': '1bf162cb617c8a62262c82d8a7038214bd7d229762ced511c2c33d082493e0b3'}, 'hosted/lib/mixer_hosted/builds/dispatch.ex': {'bytes': 3130, 'sha256': 'a535e02f8d4a9ebf8a6c9be5a5ba89b09de0192f8987e2e9ac520af206fcb753'}, 'hosted/lib/mixer_hosted/builds/journal.ex': {'bytes': 18098, 'sha256': '3386d7338d189ffc9bdd97ea9669d9c66569ec300e94154b69e14dafd41053ea'}, 'hosted/lib/mixer_hosted/builds/lifecycle.ex': {'bytes': 19409, 'sha256': '514eac8d0fd2300e6e9506a8b0f4c6c5d77d20e930982e723ce0ee8227c9bc32'}, 'hosted/lib/mixer_hosted/builds/record.ex': {'bytes': 463, 'sha256': '4394feecd6e04eba55e6aec6d3cde832a14616d0ff10a9682700477ad11930c2'}, 'hosted/lib/mixer_hosted/builds/storage.ex': {'bytes': 9880, 'sha256': 'f078d7f113f50e2705c6e4083b16a7b382a509fe0225977f43f339e4cc7b1685'}, 'hosted/lib/mixer_hosted/customer_artifacts.ex': {'bytes': 7971, 'sha256': 'f9143a77e6357720fcca3731d5fcd5dd63458a0fe48807ba992698d6b43f03be'}, 'hosted/lib/mixer_hosted/customer_artifacts/postgres_storage.ex': {'bytes': 18055, 'sha256': 'b6e9fcd0c3df4f28b6da90589eb2d3c465780c4f8ec484ace74f893aeb216340'}, 'hosted/lib/mixer_hosted/customer_artifacts/schema.ex': {'bytes': 36518, 'sha256': '5bd58744af4823374cc9a981b0699dc16c7d88f37bc8077a40b509cdf5426a19'}, 'hosted/lib/mixer_hosted/customer_artifacts/topology.ex': {'bytes': 8906, 'sha256': '35b4cc8f6a91b9b5049dae2ae50d2c056f4066b5c4e88d2e4115d252c137f4cc'}, 'hosted/lib/mixer_hosted/customer_workspace.ex': {'bytes': 1108, 'sha256': 'ea897c99ee520bc57d9dfd086ff7e102b042d2750d91f404561bdc048ebcf8e6'}, 'hosted/lib/mixer_hosted/customer_workspace/input.ex': {'bytes': 3780, 'sha256': '0ede3d8032b9703375f4d4bddd35567979ab8b454278eaaf4adfb8ca91c45fbc'}, 'hosted/lib/mixer_hosted/customer_workspace/storage.ex': {'bytes': 16295, 'sha256': '3ca97ed522b3d088dd098829d27dbd9c81bfb52c399dcf4efd3e377d121c5e34'}, 'hosted/lib/mixer_hosted/identity/access_token_verifier.ex': {'bytes': 5090, 'sha256': '1c17efc4b1a7c9befed39e312fdd3d06f89f4c64a0befbfb7c1cc9a9049d5dcb'}, 'hosted/lib/mixer_hosted/identity/admission.ex': {'bytes': 2723, 'sha256': 'f1a0ea0420a644b06f93910cbf807171e1978b2b0adf6c4186b203bf377a6d85'}, 'hosted/lib/mixer_hosted/identity/bounded_json.ex': {'bytes': 1662, 'sha256': '6f2dfd7ec4c6b85e25e61feb53cc26591129ca484b308ee1d49497fe695eb2e6'}, 'hosted/lib/mixer_hosted/identity/bounded_tcp.ex': {'bytes': 4128, 'sha256': '26e3f47841c99c0b5558317c84b21ab5b1ab77d049518a2df935cab221940529'}, 'hosted/lib/mixer_hosted/identity/configured_verifier.ex': {'bytes': 2377, 'sha256': 'd138c83981d0e0a01c27164fbe74c54635a0947254726a122253f8b2b752f35c'}, 'hosted/lib/mixer_hosted/identity/dns_resolver.ex': {'bytes': 3061, 'sha256': 'aec030a7fc368764230f078155dc2ff29137ec5a19590bc2a2a3a785d0a39567'}, 'hosted/lib/mixer_hosted/identity/encoding.ex': {'bytes': 745, 'sha256': '565338c3669fb9578e086510d6f7d06135958049c918a7df3f3558474e8e01f4'}, 'hosted/lib/mixer_hosted/identity/fetch_flight.ex': {'bytes': 6097, 'sha256': 'ca91467ac1d9011f26ff59382c996ee6186ea8daa789e64ead926a2392a60cf4'}, 'hosted/lib/mixer_hosted/identity/global_address.ex': {'bytes': 1807, 'sha256': 'd28fca0c87120f56e5e40d6ea5bb716a0f765f9e50fb500788233194c0aa74f6'}, 'hosted/lib/mixer_hosted/identity/http_freshness.ex': {'bytes': 3551, 'sha256': '43d49b9704c9f6698bf585f9495c877c37f5645a41a8133e31d5fbde50d77863'}, 'hosted/lib/mixer_hosted/identity/http_wire_guard.ex': {'bytes': 5575, 'sha256': 'cab3b7048e3572420c907acae4ec3445717dee0e62e554dec39fa9d4c0b0fa2e'}, 'hosted/lib/mixer_hosted/identity/jwks_transport.ex': {'bytes': 6140, 'sha256': 'f4e3a77d02c7a85a34223b60bc457821100769bef86e6f8102f0ba91279f02a4'}, 'hosted/lib/mixer_hosted/identity/key_owner.ex': {'bytes': 15903, 'sha256': 'd5d98bec506ad418c37fc36097d2cf714261c3f644875bf2bf93b4360adefe5d'}, 'hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex': {'bytes': 1072, 'sha256': 'cdb7b901a8e521361e1578bf0b47ea521a31c61c681c27d1f164925081238ba2'}, 'hosted/lib/mixer_hosted/identity/manifest.ex': {'bytes': 3157, 'sha256': '4b12b89c3b39177c295f68050aba84dcb2e5ae62421b3ebd4810526d125a30b4'}, 'hosted/lib/mixer_hosted/identity/startup_config.ex': {'bytes': 5214, 'sha256': '0c9b11693d34880ca9e9c05fba95e1f3994a0eadd7189a5fde2f65b036ff4d50'}, 'hosted/lib/mixer_hosted/identity/trust_snapshot.ex': {'bytes': 5390, 'sha256': '5bce1be5dc33155669f30e615bb5ef8c61c41488072608df14b963dfc3edb1f9'}, 'hosted/lib/mixer_hosted/identity/verified_identity.ex': {'bytes': 1098, 'sha256': '02ea302abedbf10555792ae5284f8eb41113edd11bc83c3e869bdbee7b68ae4d'}, 'hosted/lib/mixer_hosted/identity/verifier.ex': {'bytes': 559, 'sha256': '713a64a0bba94b6a1d4e5c8e55dada8807ca1256000b5c62b36fc3b493574a9e'}, 'hosted/lib/mixer_hosted/protocol/artifact_admission.ex': {'bytes': 6176, 'sha256': '8a4712fbfe92f70d4c27466d5f2cd4ff9d720e60208029563ca94aa3590d0cbb'}, 'hosted/lib/mixer_hosted/protocol/artifact_cbor.ex': {'bytes': 5343, 'sha256': '518f5a23b7c6a266c2b0837355446ad6d326cfcd0f5cfd9b0120ea4e851caaa6'}, 'hosted/lib/mixer_hosted/protocol/artifact_json.ex': {'bytes': 5805, 'sha256': 'c17a68db3eac6f2c018612df536b100de7378c74f5dd2f9dd6d6c1e9d42d2957'}, 'hosted/lib/mixer_hosted/protocol/artifact_v3_policy.ex': {'bytes': 8214, 'sha256': '13ddbe90a6942bf05311d58270786bcfb4def75107b6d6377fd451b1e2121a3a'}, 'hosted/lib/mixer_hosted/repo.ex': {'bytes': 107, 'sha256': '034e56f300c8677adc71cee8b63d86825588cbc26a9ec155d9670cbd0a5329ec'}, 'hosted/lib/mixer_hosted/runtime_config.ex': {'bytes': 4199, 'sha256': 'e3b8ab88ae4c12788b09d470a71d051bd817ee919db5fe6281054231d38f0286'}, 'hosted/lib/mixer_hosted_web/browser_workspace_dispatcher.ex': {'bytes': 4531, 'sha256': '49f87b855412261a0bf705d7c9ba5f37048ee3918fe092e754380fa974faff17'}, 'hosted/lib/mixer_hosted_web/browser_workspace_dispatcher/capture_adapter.ex': {'bytes': 1514, 'sha256': 'a8ebc637dc3ac4ffad016b31c5e093dd953de86ae5042788ef82bcb0b973b921'}, 'hosted/lib/mixer_hosted_web/browser_workspace_dispatcher/request.ex': {'bytes': 1377, 'sha256': 'abdeae66e37e3ca015244433c5947dcb9b91f6e0ee847090ff5de80ebfc0cf2a'}, 'hosted/lib/mixer_hosted_web/customer_artifact_controller.ex': {'bytes': 3649, 'sha256': '1597d793de5b78f6f02094535989b240210747e74ac9b86c5ecd82134cefabdf'}, 'hosted/lib/mixer_hosted_web/customer_workspace_controller.ex': {'bytes': 4455, 'sha256': '3035b60c297c1da6665d013f668d48a1ed09433936eab5d22938c06885d63b64'}, 'hosted/lib/mixer_hosted_web/endpoint.ex': {'bytes': 160, 'sha256': '7702c86f462af84fb6ac157d700d1a22352f2eaf117e31565f672dd533313d08'}, 'hosted/lib/mixer_hosted_web/error_json.ex': {'bytes': 187, 'sha256': 'c850deb7ae7656cc8d895cc7dbfb1753b7f13e563f16987677cebc5169bd9915'}, 'hosted/lib/mixer_hosted_web/health_controller.ex': {'bytes': 221, 'sha256': 'f3bb0776dd5015aae029b76c73784254daf831c53d06d20f0ec10103e3fc72cb'}, 'hosted/lib/mixer_hosted_web/plugs/bearer_identity.ex': {'bytes': 10884, 'sha256': '4bb4964827578fe373b64705bce74807191551cc8f870041f11da907a7ef249a'}, 'hosted/lib/mixer_hosted_web/plugs/customer_artifact_request.ex': {'bytes': 13467, 'sha256': '40b39e38f8c3ecdcb36ba006ee0517303a690246c029d1cc6d42b00a5fbf9a1b'}, 'hosted/lib/mixer_hosted_web/plugs/customer_workspace_request.ex': {'bytes': 11149, 'sha256': 'bc1cd4244d436dbf8bd769ed03fc5baf28939661604648434d157c47ed504d3c'}, 'hosted/lib/mixer_hosted_web/router.ex': {'bytes': 938, 'sha256': '71ae9d8a07c2559a76773b2228d740e006315899536866d9ea79ebbbaade256c'}, 'hosted/mix.exs': {'bytes': 1270, 'sha256': 'bf32132975d04d66315974a6a5ef0bc9d9718b6392824d92bbc8e9d764062f0d'}, 'hosted/mix.lock': {'bytes': 7964, 'sha256': '1eada39dcaf4863d02d39f51e218d2bad8908b36a0cba47ff2d16037b7bcf837'}, 'hosted/priv/browser_auth/relation_surface_v1_pg16.json': {'bytes': 132435, 'sha256': '079b8cdeb3c039284b3ae402664230f6abc01782ab5e7f08219a06067e22cadf'}, 'hosted/priv/browser_auth/relation_surface_v1_pg17.json': {'bytes': 132435, 'sha256': '100df9346930b778611b46e821484db025671819b3bb966cfcb496014ce42785'}, 'hosted/priv/repo/migrations/20261024000000_add_oban.exs': {'bytes': 168, 'sha256': 'c4cd9451f54eb37da9d357f8cc451dc0188134799fa5c359d754c07208bb6b3e'}, 'hosted/priv/repo/migrations/20261025000000_add_build_journals.exs': {'bytes': 1562, 'sha256': '9d848ba6c781cd018aca43989313e78320b5e970da7fc4c863a1da644a16d7f2'}, 'hosted/priv/repo/migrations/20261025000001_add_build_admission.exs': {'bytes': 2880, 'sha256': '67da842fb971ace6081c8287792acc1cc5bcb2be630dcad1fcf54b4eae2a87bb'}, 'hosted/priv/repo/migrations/20261025000002_add_build_aggregate_limits.exs': {'bytes': 2572, 'sha256': '443ede59186c0fca9454bcec319965217007c328719dbb152bdf6552901e009b'}, 'hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs': {'bytes': 12665, 'sha256': '110997b341449a04135296b000c6434f84526305c2f70c16b1e51f38dffc3f6c'}, 'hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs': {'bytes': 805, 'sha256': '5248990524d1c2504847fdff2f107a952d850acf8ff5fcdb8e7b0ef77e38bcd7'}, 'hosted/priv/repo/migrations/20261025000005_add_customer_artifact_storage.exs': {'bytes': 1967, 'sha256': '35e00750436666e22ee4a483848b9fca4fa33fa39b529dd39d27b940f0d0f681'}, 'hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs': {'bytes': 7652, 'sha256': '43140162ceaf87b58bcdcdf820a9b95b7ae465a873193ac61c7a725a18bde875'}, 'hosted/priv/repo/migrations/20261025000007_add_browser_sessions.exs': {'bytes': 435, 'sha256': '577b38e600c55e9844bc393ccfe4dfdfb7241db7eaed449956e6a3335442710f'}, 'hosted/priv/repo/migrations/20261025000008_add_browser_activation_preparation.exs': {'bytes': 460, 'sha256': 'efcd051a07ea3cdb4e294bd3d205a2e87d6354cd9b8b6f4adbb4b11bf44007d0'}, 'hosted/scripts/dependency-inventory.exs': {'bytes': 501, 'sha256': 'ed9cb6ec066742d09ae14c82968b4da0600a0ada7728227f255864e7e01619ab'}, 'hosted/scripts/test-local.py': {'bytes': 21455, 'sha256': '78292dbf027bff4fae67d638fec9504c042cbeac39b6bca40e38321178bb5951'}, 'hosted/test/fixtures/audit/coherent-vectors.json': {'bytes': 464560, 'sha256': '7932faecca13772c933048ac3cd39da1dcfc07ee215463243ed551cc0beaf72b'}, 'hosted/test/fixtures/audit/retained-chains.json': {'bytes': 1258404, 'sha256': 'd25955b2e6e8242e2af3e71b718a7c627998df8c9dbf18aa1b94846abc1a16a9'}, 'hosted/test/fixtures/billing/webhook-signature.json': {'bytes': 3328, 'sha256': '064080c913395ec5105e135070b9af055f529247b1893c76f1482171df9ad9c9'}, 'hosted/test/foundation_integration_test.exs': {'bytes': 5619, 'sha256': 'a3c6fcbc09170a23b7b45b93cf3805c176b4728a3bb7eef12278ee8f8c046039'}, 'hosted/test/mixer_hosted/audit/customer_artifact_event_test.exs': {'bytes': 25338, 'sha256': '1e5729064e747fc57c64dd7b28030ef89b0d9e72bbaaef733bdab93dca2aee93'}, 'hosted/test/mixer_hosted/audit/upload_event_test.exs': {'bytes': 12254, 'sha256': '626c11b6fe3785cdcde83966f3871c64240ca07dcb2dc03927f5e37033e3d220'}, 'hosted/test/mixer_hosted/authorization/artifact_read_test.exs': {'bytes': 27053, 'sha256': 'df0599b4b874566901f5c6ef2faaea370f2639d872167a8fb7697a7c795547f0'}, 'hosted/test/mixer_hosted/authorization/jit_policy_spec.exs': {'bytes': 9268, 'sha256': 'e39497fb5dd03edc1ddc00a06a56af26b279bcace2ca9c6810c26a004690656b'}, 'hosted/test/mixer_hosted/authorization/policy_test.exs': {'bytes': 21932, 'sha256': '3b1595799b3cbe5cc080546d07efabb258dd4891bae9702259d95031b9416ae7'}, 'hosted/test/mixer_hosted/authorization/postgres_repository_test.exs': {'bytes': 31469, 'sha256': '63e7c72e351ad0aced90145e4cf3a861d68739c0c06d512f0d17b869704edae4'}, 'hosted/test/mixer_hosted/authorization/transaction_test.exs': {'bytes': 31291, 'sha256': '414cc74e70ca8572919ae82d4f17b10b9deb2095d4310aa6856dd8179dbae6ad'}, 'hosted/test/mixer_hosted/billing/raw_webhook_capture_http2_test.exs': {'bytes': 4874, 'sha256': '4656e1f05e20ddfe8767be837a38d8323313efd7ef77efa7176a748c518c8ce8'}, 'hosted/test/mixer_hosted/billing/raw_webhook_capture_test.exs': {'bytes': 10728, 'sha256': 'd90910cfa91d579be9ab748d6019a7048ed37f6abb4b73ac9686510589878fe7'}, 'hosted/test/mixer_hosted/billing/webhook_signature_test.exs': {'bytes': 8329, 'sha256': 'dce0985cc2e42af41164a7724769b26768f4c85cc0d87f03d6ad0e61b4f84244'}, 'hosted/test/mixer_hosted/billing/webhook_transport_test.exs': {'bytes': 4105, 'sha256': 'f427b0b601e27f5b34d4d4cfe5e6d60eed452ab1d34e2a8474c6bbeb3162c27a'}, 'hosted/test/mixer_hosted/browser_auth/activation_preparation_test.exs': {'bytes': 17926, 'sha256': '0245ef23e333bfd16615644613634dc69e31ef468afe6d1ce825b76d07c9f043'}, 'hosted/test/mixer_hosted/browser_auth/config_test.exs': {'bytes': 15194, 'sha256': '48ef4fed37e5ed94c513fd16fbb6ef7104c1759046e2e6ffc3eeef14cd283c6d'}, 'hosted/test/mixer_hosted/browser_auth/configuration_digest_test.exs': {'bytes': 5649, 'sha256': '42bcf1ea1d1c9d7db3b4756b7d5a070ccb1f163164031d7641268f7e71f37290'}, 'hosted/test/mixer_hosted/browser_auth/custody_test.exs': {'bytes': 5458, 'sha256': 'e907da6a75dc3b5a53d974522ffcabc64f87be78947b914b4ae2f088e5f5f53b'}, 'hosted/test/mixer_hosted/browser_auth/migration_spec.exs': {'bytes': 8211, 'sha256': '47309d3db40cd5ed3569a9dd4493c8e4df563a8f6e175c11fe282b54955bbadc'}, 'hosted/test/mixer_hosted/browser_auth/protocol_test.exs': {'bytes': 17357, 'sha256': 'c60ebced5ae850d4d7e2fe3e4d4c60b8cdb490f2ad40ac8e333faeb49d60bda3'}, 'hosted/test/mixer_hosted/browser_auth/run_migration_fixture.py': {'bytes': 9714, 'sha256': '4497a64dce49287877f58b1cc76171bc7489da352ee91d5f480cc184f8a8ca55'}, 'hosted/test/mixer_hosted/browser_auth/run_storage_fixture.py': {'bytes': 8627, 'sha256': 'bfd5edfa4f4e362e76686fb7de89def23ca79eefe1b1c58f74749f550c9bf92c'}, 'hosted/test/mixer_hosted/browser_auth/runtime_config_test.exs': {'bytes': 20142, 'sha256': 'fcd79eb95485dbe8e20b2fe4ec104daad59fc7eb78b607571132f89c0f0b2e82'}, 'hosted/test/mixer_hosted/browser_auth/storage_fixture.exs': {'bytes': 7108, 'sha256': '9417342d3d5708d21b216383da8cb4bef381e3572036853e6f099ccf08235a06'}, 'hosted/test/mixer_hosted/browser_auth/storage_spec.exs': {'bytes': 45957, 'sha256': 'bbb6f93902f743299e6c4189806757f3366ff20bcfed8fa56b0f9162d38e041c'}, 'hosted/test/mixer_hosted/browser_auth/stored_snapshot_test.exs': {'bytes': 15352, 'sha256': 'bf814937391e70305f853ed5710920b3d7f54587a2497646cb025e03d8c68f2e'}, 'hosted/test/mixer_hosted/browser_auth/vault_test.exs': {'bytes': 20940, 'sha256': '133dc8e8aeeec19a4a6020baa83e3badc021832360ca3a9048c88a3318a8ab38'}, 'hosted/test/mixer_hosted/builds/admission_test.exs': {'bytes': 21354, 'sha256': '9aa895580f54af5f67dc610b7e899963712f12a6becd64f8e63170cd02f4a37a'}, 'hosted/test/mixer_hosted/builds/aggregate_admission_test.exs': {'bytes': 30252, 'sha256': '3c7ba454e32c085e862ac929a49765cf56166e6057e6ba436cda7dfff90bb646'}, 'hosted/test/mixer_hosted/builds/coordinator_test.exs': {'bytes': 21500, 'sha256': 'af70ef055e97ff1ba16b546297f802a7b7dc339fcf7e9c5bc45c5af2b70bfdb6'}, 'hosted/test/mixer_hosted/builds/journal_test.exs': {'bytes': 25263, 'sha256': '8793125673b1a1ded44f47bce833a41bf65cf3eac51fbbd7ebede2ecd478d97e'}, 'hosted/test/mixer_hosted/builds/lifecycle_test.exs': {'bytes': 27848, 'sha256': '79e1628427b75b5280df2d30219cdd286ad11f0916dcc6e39786b1dbecd4f3f7'}, 'hosted/test/mixer_hosted/builds/storage_test.exs': {'bytes': 13131, 'sha256': 'dc31fb40ed3cd586450db63fd20747523ac4594349dcf73b2e4b9fb0ec275ca4'}, 'hosted/test/mixer_hosted/customer_artifacts/postgres_storage_test.exs': {'bytes': 39864, 'sha256': 'b7c9fc606a6ec1bc5916381b1e970a22f5d5251a98e84c57207cd4763b3fe8ec'}, 'hosted/test/mixer_hosted/customer_artifacts_test.exs': {'bytes': 22095, 'sha256': 'b9b6aa3c431d918ef1c70fd62abb3286f128fd148f31f813c41e22ae046e8775'}, 'hosted/test/mixer_hosted/customer_workspace_test.exs': {'bytes': 39431, 'sha256': '1d5b68cb6e3dbace2fe0770764d6e75014cf22e49ebf6b31dfff50d9aafc8a85'}, 'hosted/test/mixer_hosted/identity/access_token_verifier_test.exs': {'bytes': 22379, 'sha256': 'e851fa0315c52e02dd24a9b6c81a8d84c409a352b55acba8c26a4d861cd3d7af'}, 'hosted/test/mixer_hosted/identity/key_owner_inflight_lifecycle_test.exs': {'bytes': 24827, 'sha256': '712dac61a33dbe7805a1e5f41c1f648c5b9ba482ac23952e9bc1ef0136a6cea6'}, 'hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs': {'bytes': 14688, 'sha256': 'b87a38126edc9a96c3721677684007f1870d99736b88e63e15e8ed329d0e215d'}, 'hosted/test/mixer_hosted/identity/key_owner_linux_network_test.exs': {'bytes': 3183, 'sha256': '0ce4ba31eebfaea270e891deabdceba936bb79ee2b3b61e48c957e230844ef9f'}, 'hosted/test/mixer_hosted/identity/key_owner_test.exs': {'bytes': 46346, 'sha256': '0378933f07f780fd4f2616df409b39bbff3a58e0849ca7ff202060d49a9ee483'}, 'hosted/test/mixer_hosted/identity/manifest_endpoint_test.exs': {'bytes': 5208, 'sha256': '5c41caab26b19f204d386e9051906cabae490044b209e21b2557dfd1244f9be3'}, 'hosted/test/mixer_hosted/identity/startup_config_test.exs': {'bytes': 8279, 'sha256': 'bb9fc59f47c2c4bb15c42608ff52cd3dbe88ed71e73957bda3c4775b96214c3a'}, 'hosted/test/mixer_hosted/identity/startup_lifecycle_test.exs': {'bytes': 6531, 'sha256': 'e88301c119b04528879b0b52e896c73075cd2a390bc17ef9b20a2ddf68430ba2'}, 'hosted/test/mixer_hosted/identity/startup_linux_network_test.exs': {'bytes': 4995, 'sha256': '7d28b594476d349b3ca6e35c2dbadb21f6e831f53ace235e3a1e8b85cb712480'}, 'hosted/test/mixer_hosted/protocol/artifact_admission_test.exs': {'bytes': 16835, 'sha256': '8d79277ad933204be02bc540412968842b903cfe444f252a9c4642e1da3dd31f'}, 'hosted/test/mixer_hosted/protocol/artifact_cbor_test.exs': {'bytes': 7872, 'sha256': '083d0479d56a3c77fffc32988fc42746d1968219807debbb687078a812a933a5'}, 'hosted/test/mixer_hosted_web/bearer_identity_compile_test.exs': {'bytes': 3555, 'sha256': '664fec5c8c3ae9001df1836f74e1f76f3fb70696a4b7d7bd03c7074d825be710'}, 'hosted/test/mixer_hosted_web/bearer_identity_test.exs': {'bytes': 25213, 'sha256': '3a2445a9380a6679529d245fa092a5f0c0eab4dc658b41e0f44f563f1a6fda17'}, 'hosted/test/mixer_hosted_web/browser_workspace_dispatcher_capture_adapter_test.exs': {'bytes': 7201, 'sha256': '7fc8cc584d3f1b882386f62903c2c69b1cd7c4a1a75361175556e2bc25f00c61'}, 'hosted/test/mixer_hosted_web/browser_workspace_dispatcher_request_test.exs': {'bytes': 5465, 'sha256': '83649a3f972e13482abe893ab8817f85fec47910722bfa7fafbd246403f53d73'}, 'hosted/test/mixer_hosted_web/browser_workspace_dispatcher_test.exs': {'bytes': 6885, 'sha256': 'e03227fde20ef946e538c17ed41b4d7d50d7fba88ef737c50e9caceb7c47e3ea'}, 'hosted/test/mixer_hosted_web/customer_artifact_http_integration_test.exs': {'bytes': 33067, 'sha256': '81de356fc55106181471b72de93f4664600075f079135a5881f7b6985a810272'}, 'hosted/test/mixer_hosted_web/customer_artifact_transport_test.exs': {'bytes': 28640, 'sha256': '2aa497b77292e380c88b564ee504165f5773e3347da422e97ece664ce152d9bb'}, 'hosted/test/mixer_hosted_web/customer_workspace_http_integration_test.exs': {'bytes': 30280, 'sha256': 'ec04043170f7300293b6a42c3daf47f2f26c1868b77a1b30a03a9259b524a870'}, 'hosted/test/mixer_hosted_web/customer_workspace_transport_test.exs': {'bytes': 22996, 'sha256': '2f5c93b3a2ee6c99fac018b10e66e266b44c4c36d3ec01e5fc91303960a3aabf'}, 'hosted/test/runtime_config_test.exs': {'bytes': 3661, 'sha256': 'bf12eaec3ac8da5b7aec297c16bd3d3e89f62182c3fd00980b60a7c04e3a6daf'}, 'hosted/test/support/build_dispatch_fixture.ex': {'bytes': 4675, 'sha256': 'a2c601c4cdab3a2bb2683fb8564da0fa61a4bf543123b81f5ee1d63418af4c62'}, 'hosted/test/support/build_intent_worker.ex': {'bytes': 468, 'sha256': '48f36bbc27956ce380bf2684826bcb22180636d9e81a3a3a569658f4cfb9ff48'}, 'hosted/test/support/http2_wire_fixture.ex': {'bytes': 21444, 'sha256': 'c0ba4561576060c525e586414fcfeacc88cfa19b14607d4f13dffaca32da7f4e'}, 'hosted/test/support/identity_component_fixture.ex': {'bytes': 525, 'sha256': '1713d06d203ff6ca765e25b2dacc0cb5b8f3c7597308412e7d61ff5f8507953c'}, 'hosted/test/support/identity_dns_fixture.ex': {'bytes': 2874, 'sha256': '67f1dfc30387f48644bfe1d4de3ac43a77f873fe82cac4a02eb881f9d56b9283'}, 'hosted/test/support/identity_raw_fixture.ex': {'bytes': 2664, 'sha256': 'ccfc9105b317d0708d3af2a98f6854c38aed30ed12ba28a1fe49a6cc3ffd6862'}, 'hosted/test/support/identity_socket_probe.ex': {'bytes': 2893, 'sha256': '8135af832ad0f1877e7370ff491c882597c1510d82f15c011a35897e936f9416'}, 'hosted/test/support/identity_startup_fixture.ex': {'bytes': 4539, 'sha256': '075f77531b83d43567c214777ee458cb630f15e62fbd1f009c46100ccacdd761'}, 'hosted/test/support/identity_tls_fixture.ex': {'bytes': 8003, 'sha256': '1ebb466459c4cf07e23bad66dcabc080b3f3348c5c12d974b28ef88ded1de1e2'}, 'hosted/test/support/probe_worker.ex': {'bytes': 365, 'sha256': '1caebaa5ea30e06a114650b67d577c4e31125d2b76e59c1de6900ff2989dfb33'}, 'hosted/test/test_helper.exs': {'bytes': 251, 'sha256': '71a75fc76dcf3c252b4d41c1f3a30adccfae5873028f7d40f174c8a25fd7c646'}}


def finalize(root, output):
    """Always-step continuation, within the original budget and retained exact IDs."""
    output = Path(output)
    state_path = output / 'state.json'
    if not state_path.is_file():
        output.mkdir(parents=True, exist_ok=True)
        receipt = {'schema': 1, 'status': 'unqualified-collector-not-run-or-state-missing', 'cleanup': 'no retained created CID; no Docker operation attempted', 'run_id': os.environ.get('GITHUB_RUN_ID'), 'attempt': os.environ.get('GITHUB_RUN_ATTEMPT'), 'sha': os.environ.get('GITHUB_SHA'), 'independent_acceptance': 'pending'}
        write_json(output / 'finalizer.json', receipt)
        files = {'finalizer.json': {'bytes': (output / 'finalizer.json').stat().st_size, 'sha256': hashlib.sha256((output / 'finalizer.json').read_bytes()).hexdigest()}}
        write_json(output / 'artifact-manifest.json', {'schema': 1, 'files': files, 'tree_digest_sha256': canonical_digest(files), 'scope': 'collector not run; no test/cleanup qualification'})
        return 1
    state = json.loads(state_path.read_bytes())
    require(state.get('run_id') == os.environ.get('GITHUB_RUN_ID') and state.get('attempt') == os.environ.get('GITHUB_RUN_ATTEMPT') and state.get('sha') == os.environ.get('GITHUB_SHA'), 'finalizer run identity mismatch')
    require(re.fullmatch(r'mixer-identity-net-[0-9]+-[0-9]+-[0-9a-f]{32}', state.get('label', '')), 'finalizer label mismatch')
    subject = object.__new__(Collector)
    subject.root, subject.output, subject.sha = Path(root), output, state['sha']
    subject.state, subject.registry = state, OwnedRegistry()
    subject.registry.records = [OwnedContainer(**row) for row in state['containers']]
    subject.registry.unresolved = state['unresolved_creates']
    subject.budget = Budget(start=state['started_monotonic'])
    subject.cancelled, subject.log_bytes, subject.command_number = state['cancelled'], state['log_bytes'], state['command_number']
    subject.run_id, subject.attempt, subject.label, subject.runner = state['run_id'], state['attempt'], state['label'], None
    require(len(subject.registry.records) + len(subject.registry.unresolved) <= 3, 'finalizer registry count')
    require(len({row.cid for row in subject.registry.records}) == len(subject.registry.records), 'finalizer duplicate CID')
    for row in subject.registry.records:
        require(row.role in CAPS and re.fullmatch('[0-9a-f]{64}', row.cid) and row.name == subject.label + '-' + row.role and row.label == subject.label and row.image_id == IMAGES['pg' if row.role == 'pg' else 'test']['config'] and row.state in {'owned', 'removed', 'identity_lost'}, 'finalizer registry identity mismatch')
    (output / '.scratch').mkdir(exist_ok=True)
    clean = subject.cleanup()
    if not clean:
        subject.state['status'] = 'FAILED-cleanup-unknown-or-incomplete'
    write_json(output / 'finalizer.json', {'schema': 1, 'same_original_aggregate_deadline': True, 'cleanup_verified': clean, 'no_retry_of_identity_lost_or_unknown_create': True, 'primary_status': subject.state['status']})
    subject.seal()
    return 0 if clean else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sha')
    parser.add_argument('--output')
    parser.add_argument('--finalize')
    options = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'execution is selected only on the fresh GitHub runner; import controls are host-only')
    selected_output = Path(options.finalize or options.output or '').resolve()
    require(selected_output.parent == root and selected_output.name == 'identity-network-evidence', 'output must be the one owned identity-network-evidence directory')
    if options.finalize:
        require(not options.sha and not options.output, 'finalizer takes only --finalize')
        return finalize(root, selected_output)
    require(options.sha == os.environ.get('GITHUB_SHA') and options.output, 'exact GITHUB_SHA and explicit output required')
    subject = Collector(root, selected_output, options.sha)
    def cancelled(signum, _frame):
        subject.cancelled = True
        subject.state['cancellation_signal'] = signum
    signal.signal(signal.SIGINT, cancelled)
    signal.signal(signal.SIGTERM, cancelled)
    return subject.run()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except CollectorError as error:
        print('identity network collector refused: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
