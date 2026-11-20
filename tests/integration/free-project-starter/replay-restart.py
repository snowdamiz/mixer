#!/usr/bin/env python3
"""Replay the closed Starter worker restart and optional former-owner readback."""
import argparse
from contextlib import ExitStack, closing
import errno
import hashlib
import hmac
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
from socketserver import StreamRequestHandler, ThreadingTCPServer
import sqlite3
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from types import ModuleType
from urllib.parse import urlencode

DELIVERY = Path(__file__).resolve().parent
ROOT = DELIVERY.parents[2]
PUBLIC = "201ead70ff68bfe18de24c0642f518701459e0a4"
TREE = "bc795366f84ca7d68890b84a97bd8773fe1dc786"
SDK = "fad0d0b3e65fd3be3b49675601693e5d91999fbe"
PROVENANCE_PATHS = ("cli", "sdk", "updates", "runtime-identity")
HELPERS = {
    "registration-runner": "cc1ac339f3968926395c35b1f403682d25f37805d76819c624b96c7d01b706e9",
    "prepare-starter": "fe28b796ed75e0ada06e82ca591227a59bf15d203f22fa89a7affb47511126d0",
    "run-proof": "b36a5bcec8414929b2d792a483afd669b6e2dc86fffc496eb3fd8ecb229b325a",
}
WORKERS = {
    "native_artifact_worker.py": "f03052a171611ae3da967d61fcbad90c92ab565bef1da64a3570054e27c1119b",
    "compiler_worker.py": "7e9185b80559f8a708ebdc4ac7683c61e7bf4f0ffff897342bb9c05eb6ea3e24",
    "starter_package_closure.py": "b3164d0dfa8210ce26bb5a0f4b21f5ce063d90f5040522ee4d41f61a9960941d",
}
TEST = "test/mixer_hosted/browser_auth/local_starter_http_sql_spec.exs"
PROVIDER = "test/support/browser_login_provider_fixture.ex"
FIXTURE_PREIMAGES = {
    TEST: "2b8e72b6d0ef5a02de2bf67c553da267134c5141de816e0527e94389fd696cfb",
    PROVIDER: "df20f5a5dc43f3e0777095e4e79c5f9b571d2b62e55e672aac2fbcb80a7c03a7",
}
FIXTURE_AFTERIMAGES = {
    TEST: "8557e55c12899b274e7bbf4ffcd63a4fbff0212f59a14e717287cf7f90077648",
    PROVIDER: "c5a2ecb65fa422055e7512a40911d0686a679b688d5bd16a2fef1adf8458d522",
}
FIXTURE_PATCH = "restart-hosted-fixtures.patch"
FIXTURE_PATCH_SHA256 = "197b2006ef124f23ea91e566cada4e58f23c8f9ca88940237d2c6c80e8a43d8a"
EXIT_PUBLIC = "59cab78cd8ac7a43c718914fc83fb56b33e3ef60"
EXIT_TREE = "af45a0414116ae0fa7100e1fce302ca4f8cee0c9"
EXIT_HELPERS = {
    "registration-runner": "66ae38001e95c80f2f3d287c56fc6a3e9382c9579b5a0666ec70943da31bad4e",
    "prepare-starter": "b751187ba1fe77a7cb884f81470b3dbc767dfcac5acf365df58e57ac4bfe7d75",
    "run-proof": "077fcd3f9e1a3a0b43e04a9d6ce92a398858709a88db13fcbfab06fdec3f9f7b",
}
EXIT_WORKERS = WORKERS | {
    "native_artifact_worker.py": "4cd80eca9299e5f34a2e157827919a3b11d91653fb6b3443a693bca3301f81aa",
    "compiler_worker.py": "e702b3392f0baf3a1621ba2c1639bbbb60a769a76fa71ae2419b0dc8f208d546",
}
EXIT_FIXTURE_PREIMAGES = FIXTURE_PREIMAGES | {
    TEST: "3b64cbba36888c3a999f70ff7d59467a9fe917e1fe252bed5f2cd43c079aeeb8",
}
EXIT_FIXTURE_PATCH = "owner-exit-hosted-fixture.patch"
EXIT_FIXTURE_PATCH_SHA256 = "bf3f61542b930e87609e9d818cae16d78286e05c1a32c04fcd5e116cd172f33b"
EXIT_FIXTURE_TEST_SHA256 = "a8cc763876d20deac186804aaaa26ca4887f60b34be641a8f1ff7f3db5823e45"
PROCESSOR = "restart-processor.exs"
PROCESSOR_SHA256 = "eb46daf035472ab6ae5db4a30cdae7cf1e5aebbcc4575779b2c045cb8a0e26d4"
DB = "browser_ordinary_installation_r1422"
HOST = "127.0.0.1"
BUILD = "/console-api/v1/builds"
KEY = "l07-starter-build-once"
LIMIT = 262_144
SCOPE = ("organization_id", "project_id", "application_id", "platform")
KINDS = ("unsigned_native_binary", "debug_symbols", "resource_inventory")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def compact(data):
    return json.dumps(data, separators=(",", ":"), ensure_ascii=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_sha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def record(path, value):
    pending = path.with_suffix(".pending")
    with pending.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    pending.replace(path)


def tree_entries(raw):
    entries = {}
    for item in raw.removesuffix(b"\0").split(b"\0"):
        metadata, path = item.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        require((kind, mode) in {("tree", "040000"), ("blob", "100644"), ("blob", "100755")},
                "provenance Git tree contains a non-regular entry")
        entries[os.fsdecode(path)] = (mode, blob)
    return entries


def verify_source_tree(root, expected):
    require(stat.S_ISDIR(root.lstat().st_mode), "provenance root must be a real directory")
    observed = set()
    files = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        require(relative in expected, f"unexpected provenance entry: {relative}")
        observed.add(relative)
        mode, blob = expected[relative]
        info = path.lstat()
        if mode == "040000":
            require(stat.S_ISDIR(info.st_mode), f"provenance directory changed: {relative}")
            continue
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and bool(info.st_mode & stat.S_IXUSR) == (mode == "100755"),
                f"provenance file type or mode changed: {relative}")
        data = path.read_bytes()
        require(hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() == blob,
                f"provenance file bytes changed: {relative}")
        files[relative] = sha(data)
    require(observed == expected.keys(), "provenance entries are missing")
    # NativeBuildOutput binds the CLI source root with SourceDigest.tree.
    return sha("".join(f"{path}\0{files[path]}\n" for path in sorted(files)).encode())


class Hold(RuntimeError):
    pass


class OwnedProcess(subprocess.Popen):
    def __del__(self):
        # Only the run's explicit observer may check a partially launched child.
        pass


class Run:
    def __init__(self, root, mode, owner_exit=False):
        self.root = root
        self.owner_exit = owner_exit
        self.public = EXIT_PUBLIC if owner_exit else PUBLIC
        self.tree = EXIT_TREE if owner_exit else TREE
        self.helper_pins = EXIT_HELPERS if owner_exit else HELPERS
        self.worker_pins = EXIT_WORKERS if owner_exit else WORKERS
        self.hosted = root / "hosted"
        self.provenance = root / "cli-provenance"
        self.helpers = root / "helpers" / "tests/integration/free-project-starter"
        self.state = root / "worker"
        self.state.mkdir(mode=0o700)
        self.attempts = {}
        self.ports = {}
        self.unknown = False
        self.native_pending = False
        self.source_entries = None
        self.result = {"publicCommit": self.public, "publicTree": self.tree, "mode": mode, "buildPOSTAttempts": 0,
                       "commands": self.attempts, "ports": self.ports, "python": sys.version,
                       "launcherSHA256": digest(Path(__file__))}
        if owner_exit:
            self.result.update(ownerExit=True, paymentServiceConfigured=False)
        self.env = {
            "PATH": f"{Path(sys.executable).parent}:{os.environ['PATH']}",
            "HOME": str(root),
            "TMPDIR": str(root),
            "LC_ALL": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "MIX_ENV": "test",
            "MIX_HOME": str(root / "mix"),
            "HEX_HOME": str(root / "hex"),
            "MIXER_L07_ROOT": str(root),
            "MIXER_L07_REPLAY": mode,
            "MIXER_STARTER_WORKER_CODE": str(self.hosted / "priv/development"),
        }
        if owner_exit:
            self.env["MIXER_L06_OWNER_EXIT"] = "1"

    def start(self, name, argv, *, cwd=None, env=None):
        require(name not in self.attempts, f"duplicate command attempt {name}")
        cmd = self.attempts[name] = {"argv": list(map(str, argv)), "custody": "UNKNOWN"}
        try:
            record(self.root / f"{name}.launch.json", cmd)
            with (self.root / f"{name}.out").open("xb") as out, (self.root / f"{name}.err").open("xb") as err:
                proc = OwnedProcess(
                    cmd["argv"], cwd=cwd or self.root, env=self.env | (env or {}),
                    stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True,
                )
                cmd["pid"] = cmd["pgid"] = proc.pid
            record(self.root / f"{name}.identity.json", cmd)
        except BaseException as error:
            self.unknown = True
            raise Hold(f"{name} launch or identity receipt failed ({type(error).__name__})") from error
        return proc

    def finish(self, name, proc, *, seconds=12, shutdown=None, check=True):
        cmd = self.attempts[name]
        try:
            require(cmd["pid"] == cmd["pgid"] == proc.pid, "owned process identity changed")
            if shutdown is not None and proc.poll() is None:
                os.killpg(proc.pid, shutdown)
            code = proc.wait(timeout=seconds)
            def absent():
                try:
                    os.killpg(proc.pid, 0)
                except ProcessLookupError:
                    return True
                return False

            wait(absent, 3)
            proof = dict(cmd, custody="TERMINAL", exit=code, directChildReaped=True, groupAbsent=True,
                         stdoutSHA256=digest(self.root / f"{name}.out"), stderrSHA256=digest(self.root / f"{name}.err"))
            path = self.root / f"{name}.terminal.json"
            record(path, proof)
            require(read(path) == proof, "terminal receipt differs from owned launch")
            self.attempts[name] = proof
        except BaseException as error:
            self.unknown = True
            raise Hold(f"{name} terminal custody unverified ({type(error).__name__})") from error
        if check and code:
            with (self.root / f"{name}.err").open("rb") as stream:
                stream.seek(max(0, stream.seek(0, os.SEEK_END) - 2400))
                print(stream.read().decode(errors="replace").strip(), file=sys.stderr)
            raise RuntimeError(f"{name} exited {code}")
        return code

    def command(self, name, argv, *, cwd=None, env=None, seconds=15, check=True):
        proc = self.start(name, argv, cwd=cwd, env=env)
        code = self.finish(name, proc, seconds=seconds, check=check)
        return code, self.root / f"{name}.out"

    def evidence(self):
        record(self.root / "result.json", self.result)

    def port(self, name):
        for _ in range(8):
            with socket.socket() as sock:
                sock.bind((HOST, 0))
                port = sock.getsockname()[1]
            if port not in self.ports.values():
                self.ports[name] = port
                return port
        raise RuntimeError("could not reserve a distinct loopback port")

    def closed(self):
        if self.unknown or self.native_pending:
            return False
        for name, proof in self.attempts.items():
            if not (proof["custody"] == "TERMINAL" and proof["directChildReaped"] is True
                    and proof["groupAbsent"] is True and proof["pid"] == proof["pgid"]):
                return False
            if read(self.root / f"{name}.terminal.json") != proof:
                return False
        return True

    def verify_active_services(self):
        active = {"processor": getattr(self, "processor", None), "api": getattr(self, "api", None),
                  "postgres": getattr(self, "pg", None)}
        if getattr(self, "worker", None) is not None:
            name, proc, _ = self.worker
            active[name] = proc
        for name, cmd in self.attempts.items():
            if cmd["custody"] == "TERMINAL":
                require(read(self.root / f"{name}.terminal.json") == cmd,
                        f"{name} terminal receipt no longer matches")
            else:
                proc = active.get(name)
                require(proc is not None and cmd["pid"] == cmd["pgid"] == proc.pid
                        and read(self.root / f"{name}.identity.json") == cmd,
                        f"{name} has no matching live identity")

    def archive(self, label, revision, paths, destination):
        archive = self.root / f"{label}.tar"
        self.command(label, ["git", "archive", "--format=tar", "-o", archive, revision, *paths],
                     cwd=ROOT, seconds=45)
        destination.mkdir(exist_ok=True)
        with tarfile.open(archive) as source:
            source.extractall(destination, filter="data")
        archive.unlink()

    def helper_source(self, name):
        path = self.helpers / f"{name}.py"
        require(path.resolve(strict=True) == path and stat.S_ISREG(path.lstat().st_mode),
                f"pinned helper is not a regular owned file: {name}")
        source = path.read_bytes()
        require(sha(source) == self.helper_pins[name], f"pinned helper changed: {name}")
        return path, source

    def load_helper(self, name):
        path, source = self.helper_source(name)
        module = ModuleType(name)
        module.__file__ = str(path)
        exec(compile(source, str(path), "exec"), vars(module))
        return module

    def stage_provenance(self):
        self.archive("cli-source", self.public, PROVENANCE_PATHS, self.provenance)
        _, listing = self.command("cli-source-tree", ["git", "ls-tree", "-rtz", self.public,
                                                      "--", *PROVENANCE_PATHS], cwd=ROOT)
        self.source_entries = tree_entries(listing.read_bytes())
        self.result["provenanceSourceSHA256"] = verify_source_tree(self.provenance, self.source_entries)
        self.result["provenanceEntries"] = len(self.source_entries)

    def verify_provenance(self, checkpoint):
        if self.source_entries is not None:
            require(verify_source_tree(self.provenance, self.source_entries) ==
                    self.result["provenanceSourceSHA256"], "CLI provenance digest changed")
            self.result.setdefault("provenanceVerifiedAt", []).append(checkpoint)

    def stage_fixtures(self):
        preimages = EXIT_FIXTURE_PREIMAGES if self.owner_exit else FIXTURE_PREIMAGES
        for name, expected in preimages.items():
            path = self.hosted / name
            require(path.resolve(strict=True) == path and stat.S_ISREG(path.lstat().st_mode),
                    f"archived fixture is not a regular owned file: {name}")
            require(digest(path) == expected, f"archived fixture digest differs: {name}")

        self.apply_fixture_patch("fixture-overlay", FIXTURE_PATCH, FIXTURE_PATCH_SHA256)
        afterimages = FIXTURE_AFTERIMAGES
        if self.owner_exit:
            self.apply_fixture_patch("exit-fixture-overlay", EXIT_FIXTURE_PATCH, EXIT_FIXTURE_PATCH_SHA256)
            afterimages = afterimages | {TEST: EXIT_FIXTURE_TEST_SHA256}
            self.result["exitFixtureOverlaySHA256"] = EXIT_FIXTURE_PATCH_SHA256

        for name, expected in afterimages.items():
            require(digest(self.hosted / name) == expected, f"replay fixture digest differs: {name}")
        processor = (DELIVERY / PROCESSOR).read_bytes()
        require(sha(processor) == PROCESSOR_SHA256, "replay processor digest differs")
        (self.root / PROCESSOR).write_bytes(processor)
        self.result["fixturePreimageSHA256"] = preimages
        self.result["fixtureOverlaySHA256"] = FIXTURE_PATCH_SHA256
        self.result["fixtureSHA256"] = afterimages | {PROCESSOR: PROCESSOR_SHA256}
        self.result["hostedLockSHA256"] = digest(self.hosted / "mix.lock")

    def apply_fixture_patch(self, label, name, expected):
        overlay = (DELIVERY / name).read_bytes()
        require(sha(overlay) == expected, "fixture overlay digest differs")
        patch = self.root / name
        patch.write_bytes(overlay)
        self.command(label, ["git", "apply", "--whitespace=error", patch],
                     env={"GIT_CEILING_DIRECTORIES": str(self.root.parent)})

    def stage(self, mode):
        _, revision = self.command("public-tree", ["git", "rev-parse", self.public + "^{tree}"], cwd=ROOT)
        require(revision.read_text().strip() == self.tree, "public tree identity differs")
        paths = [f"tests/integration/free-project-starter/{name}.py" for name in self.helper_pins]
        self.archive("pinned-helpers", self.public, paths, self.root / "helpers")
        self.result["helperSourceSHA256"] = {name: sha(self.helper_source(name)[1]) for name in self.helper_pins}
        paths = ["hosted/priv/development"] if mode == "inert" else ["hosted"]
        self.archive("public-source", self.public, paths, self.root)
        self.worker_code = self.hosted / "priv/development"
        require({name: digest(self.worker_code / name) for name in self.worker_pins} == self.worker_pins,
                "pinned worker source digest differs")
        self.result["workerSourceSHA256"] = self.worker_pins
        if mode != "inert":
            self.stage_fixtures()

    def hosted_dependencies(self):
        _, version = self.command("mix-version", ["mix", "--version"], cwd=self.hosted)
        self.result["mix"] = version.read_text().strip()
        self.command("hex", ["mix", "local.hex", "2.5.1", "--force"], cwd=self.hosted, seconds=45)
        self.command("deps", ["mix", "deps.get", "--check-locked"], cwd=self.hosted, seconds=120)
        self.command("offline-deps", ["mix", "deps.get", "--check-locked"], cwd=self.hosted,
                     env={"HEX_OFFLINE": "1"}, seconds=45)
        require(digest(self.hosted / "mix.lock") == self.result["hostedLockSHA256"], "Mix lock changed")

    def open_database(self, args):
        pg = args.pg_bin.resolve(strict=True)
        _, version = self.command("postgres-version", [pg / "postgres", "--version"])
        self.result["postgres"] = version.read_text().strip()
        require(re.search(r"PostgreSQL\) 17\.", self.result["postgres"]), "fixture needs PostgreSQL 17")
        data = self.root / "pg"
        self.command("initdb", [pg / "initdb", "-D", data, "-U", "fixture_admin",
                                "--locale=C", "--encoding=UTF8", "--auth=trust", "--no-sync"])
        port = self.port("postgres")
        self.psql = [pg / "psql", "-XqAtw", "-v", "ON_ERROR_STOP=1", "-h", HOST,
                     "-p", str(port), "-U", "fixture_admin"]
        self.pg = self.start("postgres", [pg / "postgres", "-D", data, "-h", HOST, "-p", str(port),
                                          "-k", "", "-c", "jit=off"])
        wait(lambda: connected(port), 8, self.pg)
        require(self.sql("postgres-directory", "SHOW data_directory", "postgres") == str(data),
                "loopback PostgreSQL data_directory does not belong to this run")
        self.result["postgresDataDirectoryVerified"] = True
        self.sql("roles", self.load_helper("registration-runner").ROLES, "postgres")

    def sql(self, label, query, database=DB):
        _, out = self.command(label, [*self.psql, "-d", database, "-c", query], seconds=7)
        return out.read_text().strip()

    def launch_api(self, extra):
        if "MIXER_STARTER_PREPARE" in extra:
            require(extra["MIXER_STARTER_PREPARE"] == str(self.helper_source("prepare-starter")[0]),
                    "fixture preparer must use the pinned helper")
        catalog = self.root / "catalog"
        catalog.mkdir()
        self.service_env = dict(extra, HEX_OFFLINE="1",
                                MIXER_BROWSER_CATALOG_FIXTURE_ROOT=str(catalog),
                                MIXER_BROWSER_STORAGE_PORT=str(self.ports["postgres"]))
        self.api = self.start("api", ["mix", "test", "--only", "l07_restart", "--seed", "0", "--trace", TEST],
                              cwd=self.hosted, env=self.service_env)
        self.auth = self.ready("api.ready", self.api, 270 if self.owner_exit else 125)
        for name in ("port", "issuerPort", "jwksPort"):
            port = self.auth[name]
            require(type(port) is int and 0 < port < 65536 and port not in self.ports.values(),
                    f"fixture port collision: {name}")
            self.ports[name] = port
        self.sessions(self.auth)

    def ready(self, name, proc, seconds):
        path = self.root / name
        return wait(lambda: read(path) if path.is_file() else None, seconds, proc)

    def sessions(self, auth):
        for cookie in (auth["cookie"], auth["unrelatedCookie"]):
            require(http(dict(self.auth, cookie=cookie), "/auth/session")[0] == 200, "fixture session denied")
        require(auth["cookie"] != auth["unrelatedCookie"], "fixture sessions are identical")
        self.result["twoAuthenticatedSessions"] = True

    def launch_processor(self, extra=None):
        env = dict(self.service_env, MIXER_HOSTED_ROLE="processor", MIXER_PROCESSOR_PROFILE="builds_v1",
                   MIXER_BUILD_OPERATION_INTENT="durable_intent_v1", MIXER_DATABASE_HOST=HOST,
                   MIXER_DATABASE_NAME=DB, MIXER_DATABASE_USER="mixer_build_processor",
                   MIXER_DATABASE_PASSWORD="loopback-only", MIXER_DATABASE_POOL_SIZE="2")
        self.processor = self.start("processor", ["mix", "run", "--no-start", "--no-compile",
                                                   self.root / PROCESSOR],
                                    cwd=self.hosted, env=env | (extra or {}))
        ready = self.ready("processor.ready", self.processor, 18)
        require(ready == {"role": "mixer_build_processor", "queue": "builds",
                          "durableIntent": True, "paused": True}, "restricted processor not paused")
        self.result["processorAdmission"] = ready

    def close_services(self):
        require(not self.unknown and not self.native_pending, "live service custody is unknown")
        self.verify_active_services()
        # Complete API database teardown only after its dependent processor is closed.
        if getattr(self, "processor", None) is not None:
            self.mark("processor.done")
            self.finish("processor", self.processor, seconds=35, check=False)
        if getattr(self, "relay", None) is not None:
            self.relay.finish()
        close_worker(self)
        if getattr(self, "api", None) is not None:
            self.mark("api.done")
            self.finish("api", self.api, seconds=35, check=False)
        if getattr(self, "pg", None) is not None:
            if self.pg.poll() is None and self.result.get("postgresDataDirectoryVerified"):
                remaining = self.sql("database-closed",
                                     f"SELECT count(*) FROM pg_database WHERE datname='{DB}'", "postgres")
                self.result["databaseDropped"] = remaining == "0"
            self.finish("postgres", self.pg, shutdown=signal.SIGINT, check=False)

    def mark(self, name):
        with (self.root / name).open("x") as stream:
            stream.write(name + "\n")
            stream.flush()
            os.fsync(stream.fileno())


def wait(probe, seconds, proc=None):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(f"required process exited before readiness ({proc.returncode})")
        value = probe()
        if value:
            return value
        time.sleep(0.05)
    raise TimeoutError("fixture readiness or closure deadline expired")


def connected(port):
    with socket.socket() as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((HOST, port)) == 0


def refused(port):
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((HOST, port)) == errno.ECONNREFUSED


def rebound(ports):
    with ExitStack() as sockets:
        for port in ports:
            sock = sockets.enter_context(socket.socket())
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((HOST, port))
            sock.listen(1)
    return sorted(ports)


def http(auth, path, body=None, *, limit=24 * 1024**2):
    headers = {"Cookie": "__Host-mixer-session=" + auth["cookie"]}
    if body is not None:
        headers.update({"Origin": auth["origin"], "X-Mixer-CSRF": auth["csrf"],
                        "Content-Type": "application/json", "Idempotency-Key": KEY})
    with closing(HTTPConnection(HOST, auth["port"], timeout=8)) as connection:
        connection.request("GET" if body is None else "POST", path,
                           None if body is None else compact(body).encode(), headers)
        with connection.getresponse() as reply:
            data = reply.read(limit + 1)
            require(len(data) <= limit, "oversized fixture HTTP response")
            return reply.status, dict((key.lower(), value) for key, value in reply.getheaders()), data


def wire_mac(config, direction, nonce, body):
    return hmac.digest(config["token"].encode(), f"{direction}\n{nonce}\n{body}".encode(), "sha256").hex()


def envelope(config, action, request=None):
    body = compact({"worker_id": config["worker_id"], "action": action, "request": request})
    nonce = secrets.token_hex(16)
    return nonce, (compact({"nonce": nonce, "body": body,
                            "mac": wire_mac(config, "request", nonce, body)}) + "\n").encode()


def verified(config, direction, nonce, frame):
    require(0 < len(frame) <= LIMIT and frame.endswith(b"\n"), "invalid worker frame")
    packet = json.loads(frame)
    if direction == "request":
        nonce = packet["nonce"]
        require(re.fullmatch(r"[0-9a-f]{32}", nonce), "invalid worker nonce")
    require(hmac.compare_digest(packet["mac"], wire_mac(config, direction, nonce, packet["body"])),
            "worker frame failed authentication")
    return nonce, json.loads(packet["body"])


def wire(config, action, request=None, *, port=None):
    nonce, frame = envelope(config, action, request)
    with socket.create_connection((HOST, port or config["port"]), timeout=2) as sock:
        sock.sendall(frame)
        with sock.makefile("rb") as stream:
            reply = stream.readline(LIMIT + 1)
    return verified(config, "response", nonce, reply)[1] if reply else None


class Relay(ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, config, action, validate):
        self.config = config
        self.upstream = config["port"]
        self.pause = False
        self.held = threading.Event()
        self.lock = threading.Lock()
        self.action = action
        self.validate = validate
        self.operation = None
        self.start_request = None
        self.requests = []
        self.failure = None
        self.thread = None
        self.handlers = 0
        self.handler_lock = threading.Lock()
        super().__init__((HOST, 0), RelayRequest)
        self.port = self.server_address[1]

    def begin(self):
        self.thread = threading.Thread(target=self.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()

    def finish(self):
        if self.thread is not None and self.thread.is_alive():
            self.shutdown()
            self.thread.join(3)
            require(not self.thread.is_alive(), "relay serve loop did not close")
        self.server_close()
        wait(self.handlers_closed, 5)

    def handlers_closed(self):
        with self.handler_lock:
            return self.handlers == 0

    def process_request(self, request, client_address):
        with self.handler_lock:
            self.handlers += 1
        try:
            super().process_request(request, client_address)
        except BaseException:
            with self.handler_lock:
                self.handlers -= 1
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self.handler_lock:
                self.handlers -= 1

    def switch(self, new_port):
        with self.lock:
            require(self.pause and self.held.is_set() and self.failure is None,
                    "relay requires one successful retention before switching")
            require(self.upstream != new_port, "replacement worker must use a distinct port")
            self.upstream = new_port
            self.pause = False


class RelayRequest(StreamRequestHandler):
    timeout = 2

    def handle(self):
        relay = self.server
        try:
            frame = self.rfile.readline(LIMIT + 1)
            if not frame:
                return
            nonce, request = verified(relay.config, "request", None, frame)
            require(request["worker_id"] == relay.config["worker_id"], "relay worker identity differs")
            action = request["action"]
            operation = (request.get("request") or {}).get("operation_id")
            with relay.lock:
                if relay.pause:
                    return
                require(action in ("ensure_started", "artifacts", "query"), "unexpected relay action")
                if action == "ensure_started":
                    require(relay.operation is not None and operation == relay.operation
                            and relay.start_request is None,
                            "unexpected additional worker start")
                    relay.start_request = request["request"]
                port = relay.upstream
                upstream = socket.create_connection((HOST, port), timeout=2)
                try:
                    upstream.sendall(frame)
                except BaseException:
                    upstream.close()
                    raise
                relay.requests.append((action, operation, port))
            with upstream, upstream.makefile("rb") as stream:
                response = stream.readline(LIMIT + 1)
            _, reply = verified(relay.config, "response", nonce, response)
            with relay.lock:
                if (action == relay.action and operation == relay.operation and not relay.held.is_set()
                        and relay.validate(request["request"], reply, response)):
                    relay.pause = True
                    self.request.shutdown(socket.SHUT_WR)
                    relay.held.set()
                    return
            self.wfile.write(response)
        except Exception as error:
            with relay.lock:
                relay.failure = error
                relay.pause = True


def start_worker(run, label, config, startup=None, pin=None):
    require({name: digest(run.worker_code / name) for name in run.worker_pins} == run.worker_pins,
            "worker code changed before launch")
    if startup is None:
        startup = run.root / (label + ".config.json")
        record(startup, config)
        startup.chmod(0o400)
        pin = digest(startup)
    require(startup.resolve(strict=True).is_relative_to(run.root) and digest(startup) == pin
            and read(startup) == config, "worker startup file or pin differs")
    proc = run.start(label, [sys.executable, "-B", run.worker_code / "native_artifact_worker.py",
                             startup, pin, run.state])
    run.worker = (label, proc, config)
    wait(lambda: connected(config["port"]), 8, proc)
    return pin


def close_worker(run):
    if getattr(run, "worker", None) is None:
        return
    label, proc, config = run.worker
    try:
        require(wire(config, "shutdown") == {"status": "closed"}, "worker refused authenticated shutdown")
        run.finish(label, proc, seconds=8)
        require(refused(config["port"]), "closed worker port did not refuse TCP")
    except BaseException:
        run.unknown = True
        raise
    run.worker = None
    run.result.setdefault("authenticatedWorkerShutdowns", []).append(config["port"])


def canary(config):
    spec = dict(config["registration"]["spec"], organization_id="l07-unrelated-worker-probe",
                build_id="worker-readiness-probe")
    return {"spec": spec, "operation_id": sha(b"fixture-readiness")}


def ledger_snapshot(state, operation):
    path = state / "operations.sqlite"
    identity = path.lstat()
    require(stat.S_ISREG(identity.st_mode), "operation ledger must be a regular file")
    row = ledger(state, operation)
    require(row is not None and row["status"] == "native_ready", "ledger lacks the expected terminal operation")
    return (identity.st_dev, identity.st_ino), row


def route_replacement(run, relay, config, probe, *, operation):
    require(relay.held.is_set() and relay.pause, "no retained response")
    require(wire(config, "query", probe, port=relay.port) is None, "paused relay did not return EOF")
    run.result["pausedRelayEOF"] = True
    original = ledger_snapshot(run.state, operation)
    require(terminal_payload_sha(original[1]) == run.result["retainedOperationSHA256"],
            "terminal row changed after artifact retention")
    close_worker(run)
    require(ledger_snapshot(run.state, operation) == original, "shutdown changed the ledger or terminal row")
    require(refused(config["port"]), "old upstream did not refuse direct TCP")
    run.result["oldUpstreamTCPRefused"] = True
    require((HOST, relay.port) == relay.socket.getsockname(), "relay listener changed")
    replacement = dict(config, port=run.port("workerRestart"))
    run.result["replacementStartupSHA256"] = start_worker(run, "replacement", replacement)
    require(run.result["replacementStartupSHA256"] != run.result["originalStartupSHA256"],
            "changed worker endpoint did not change the startup pin")
    require(wire(replacement, "query", probe) == {"error": "unavailable"},
            "replacement did not answer an authenticated query")
    require(ledger_snapshot(run.state, operation) == original,
            "replacement changed the ledger or terminal row")
    relay.switch(replacement["port"])
    require(wire(replacement, "query", probe, port=relay.port) == {"error": "unavailable"},
            "relay did not authenticate via replacement")
    run.result.update(sameRelayListener=True, sameLedger=True, workerRestarts=1,
                      ledgerIdentityBeforeShutdown=list(original[0]),
                      terminalRowThroughReplacementSHA256=json_sha(original[1]))
    return replacement


def inert_replay(run):
    from unittest.mock import patch

    run.stage_provenance()
    unrelated = run.hosted / "_build/test/lib/phoenix"
    unrelated.mkdir(parents=True)
    (unrelated / "priv").symlink_to(run.hosted)
    run.verify_provenance("inert-with-hosted-symlink")
    extra = run.provenance / "_build"
    extra.symlink_to(unrelated)
    try:
        run.verify_provenance("inert-unexpected-entry")
    except RuntimeError as error:
        require("unexpected provenance entry" in str(error), "wrong provenance fault")
    else:
        raise RuntimeError("provenance check accepted an unexpected symlink")
    finally:
        extra.unlink()
    run.verify_provenance("inert-after-control")
    run.result["inertProvenanceRejectsExtraEntry"] = True

    # No subprocess is created by either injection below.
    for fault in ("launch", "receipt"):
        root = run.root / f"injected-{fault}"
        root.mkdir()
        control = Run(root, "inert")
        recorder = record

        def failing_record(path, value):
            if path.name == "probe.identity.json":
                raise OSError("injected identity receipt failure")
            recorder(path, value)

        with patch(__name__ + ".OwnedProcess") as popen, patch(__name__ + ".record", failing_record):
            if fault == "launch":
                popen.side_effect = OSError("injected constructor failure")
            else:
                popen.return_value.pid = 99999
            try:
                control.start("probe", ["injected-no-process"])
            except Hold:
                require(control.unknown and "probe" in control.attempts and not control.closed(),
                        "injected failure lost attempted launch custody")
            else:
                raise RuntimeError("injected custody fault was accepted")
    config = {"worker_id": "l07-inert", "token": secrets.token_hex(32), "tenant": "inert",
              "port": run.port("worker"), "registration": {"spec": dict.fromkeys(
                  (*SCOPE, "source", "toolchain_lock_sha256", "build_definition_sha256"), "inert")}}
    run.result["originalStartupSHA256"] = start_worker(run, "worker", config)
    probe = canary(config)

    def hold_inert(_request, reply, _frame):
        require(reply == {"error": "unavailable"}, "unexpected inert worker response")
        return True

    relay = run.relay = Relay(config, "query", hold_inert)
    run.ports["relay"] = relay.port
    relay.operation = probe["operation_id"]
    relay.begin()
    require(wire(config, "query", probe, port=relay.port) is None and relay.held.wait(2),
            "inert relay did not retain its single answer")
    require(ledger(run.state, count=True) == 0, "inert canaries wrote an operation")
    operation = sha(b"inert-terminal-row")
    terminal = {"status": "native_ready", "starts": 1, "binding": {}, "closure": {},
                "artifacts": [], "manifest_sha256": sha(b"inert synthetic manifest")}
    write_inert_row(run.state, operation, terminal)
    run.result["retainedOperationSHA256"] = terminal_payload_sha(terminal)
    replacement = route_replacement(run, relay, config, probe, operation=operation)
    require(relay.failure is None, "inert relay failure")
    require(relay.requests == [("query", probe["operation_id"], config["port"]),
                               ("query", probe["operation_id"], replacement["port"])],
            "inert replay did not use both expected upstreams")
    require(ledger(run.state, count=True) == 1 and ledger(run.state, operation) == terminal,
            "replacement canaries changed the synthetic terminal row")
    inert_closed_failure(run)
    run.result["inertCustodyFaultsRejected"] = ["launch", "identity receipt"]


def write_inert_row(state, operation, row):
    with closing(sqlite3.connect(state / "operations.sqlite")) as db, db:
        db.execute("INSERT OR REPLACE INTO operations (id, value) VALUES (?, ?)", (operation, compact(row)))


def inert_closed_failure(run):
    from types import SimpleNamespace

    # These records exercise the observer with no CLI or nested command launched.
    operation = sha(b"inert-closed-failure")
    spec = dict.fromkeys(SCOPE, "inert")
    selection = dict(spec, build_id="inert-build")
    request = {"operation_id": operation, "spec": selection,
               "ref": dict(selection, attempt=1, fence=1), "deadline_ms": 2,
               "guard": {"record_id": "inert-record", "revision": 1, "epoch": 1,
                         "owner_id": "oban:1:00000000-0000-0000-0000-000000000000", "expires_at": 1}}
    cli = "/inert/mixer"
    relay = SimpleNamespace(lock=threading.Lock(), start_request=request, failure=None, held=threading.Event())
    binding = request_binding(operation, selection, "inert-record", spec, request)
    closure = {"closed": True, "started": True, "cli_reaped": True, "cli_group_absent": True,
               "exit": 1, "pid": 123, "preflight_failed": True, "commands": [
                   {"command": "/usr/bin/swift", "pid": 124, "receipt_sha256": sha(b"inert Swift"),
                    "group_terminate_sent": False, "stop_reason": None}]}
    row = {"status": "closed", "starts": 1, "binding": binding, "closure": closure}
    output = run.state / operation
    output.mkdir()
    launch = {"pid": 123, "argv": [cli, "build", "--platform", "ios", "--directory", str(output / "project"),
                                   "--output", str(output / "native")]}
    record(output / "closure.json", closure)
    record(output / "launch.json", dict(launch, pid=125))
    (output / "stdout").write_text('{"code":"files.symlink","message":"synthetic diagnostic"}')
    observe = lambda: observe_worker(run, relay, operation, selection, "inert-record", spec, cli, seconds=1)
    tested = []
    for case, candidate in (
        ("uncertain row", dict(row, status="uncertain")),
        ("wrong binding", dict(row, binding=dict(binding, deadline_ms=3))),
        ("unproven CLI group", dict(row, closure=dict(closure, cli_group_absent=False))),
        ("wrong launch PID", row),
    ):
        write_inert_row(run.state, operation, candidate)
        run.native_pending = True
        try:
            observe()
        except RuntimeError:
            require(run.native_pending, f"{case} changed native custody")
            tested.append(case)
        else:
            raise RuntimeError(f"{case} was accepted as terminal")
    record(output / "launch.json", launch)
    require(observe() == "failed" and not run.native_pending and run.result["compilerStarts"] == 0
            and run.result["cliFailureCode"] == "files.symlink", "positive preflight closure was not classified")
    keys = ("workerStatus", "workerClosure", "workerStarts", "compilerStarts", "ensureStartedRequests",
            "failedOperationSHA256", "error", "cliStdoutSHA256", "cliFailureCode")
    run.result["inertClosedFailure"] = {key: run.result.pop(key) for key in keys}
    run.result["inertUnprovenClosureRejected"] = tested


def prepare_export(run):
    run.stage_provenance()
    run.archive("pinned-sdk", SDK, ["sdk"], run.root / "pinned")
    cli_source = run.provenance / "cli"
    tools = run.root / "swift-build"
    _, output = run.command("swift-version", ["/usr/bin/swift", "--version"])
    run.result["swift"] = output.read_text().strip()
    _, output = run.command("xcode-version", ["/usr/bin/xcodebuild", "-version"])
    run.result["xcode"] = output.read_text().strip()
    lock = cli_source / "Package.resolved"
    run.result["cliLockSHA256"] = digest(lock)
    argv = ["/usr/bin/swift", "build", "--package-path", cli_source, "--scratch-path", tools,
            "--cache-path", run.root / "swift-cache", "--config-path", run.root / "swift-config",
            "--security-path", run.root / "swift-security", "--manifest-cache", "local",
            "--disable-dependency-cache", "--only-use-versions-from-resolved-file"]
    run.command("cli-build", [*argv, "--product", "mixer"], seconds=240)
    require(digest(lock) == run.result["cliLockSHA256"], "CLI lock changed")
    pins = {item["identity"]: item["state"]["revision"] for item in read(lock)["pins"]}
    dependencies = run.load_helper("prepare-starter").DEPENDENCIES
    require(pins == {name: values[1] for name, values in dependencies.items()},
            "CLI and pinned Starter SDK dependency revisions differ")
    archives = run.root / "sdk-archives"
    archives.mkdir()
    for name, revision in sorted(pins.items()):
        checkout = tools / "checkouts" / name
        archive = archives / f"{name}.tar"
        _, head = run.command(f"{name}-revision", ["git", "rev-parse", "HEAD"], cwd=checkout)
        require(head.read_text().strip() == revision, "SwiftPM checkout differs from its lock")
        run.command(f"{name}-archive", ["git", "archive", "--format=tar", "-o", archive, revision],
                    cwd=checkout, seconds=35)
        require(digest(archive) == dependencies[name][2], "public SDK archive digest differs")
    run.result["sdkDependencyRevisions"] = pins
    cli = (tools / "debug/mixer").resolve(strict=True)
    run.result["cliSHA256"] = digest(cli)
    pinned = run.root / "pinned/sdk"
    workspace = run.root / "starter"
    workspace.mkdir()
    generated, original, local_sdk, derived, exported = (workspace / p for p in (
        "generated", "original", "local-sdk", "derived", "exported"))
    prepare, _ = run.helper_source("prepare-starter")
    run.command("starter-create", [cli, "create", "Starter", "--application", "example.source.app",
                                   "--platform", "ios", "--directory", generated, "--sdk-path", pinned])
    run.command("starter-original", [cli, "export", original, "--directory", generated])
    run.command("starter-local-sdk", [sys.executable, "-B", prepare, "--local-sdk", local_sdk,
                                      pinned, archives], seconds=40)
    run.command("starter-upgrade", [cli, "upgrade", derived, "--directory", original,
                                    "--sdk-path", local_sdk], seconds=40)
    _, output = run.command("starter-complete", [sys.executable, "-B", prepare, "--complete-export", derived])
    source_sha = output.read_text().strip()
    _, output = run.command("starter-export", [cli, "export", exported, "--directory", derived], seconds=40)
    require(re.fullmatch("[a-f0-9]{64}", source_sha) and source_sha in output.read_text(),
            "CLI export does not match complete Starter source")
    run.command("starter-validate", [cli, "config", "validate", "--directory", exported])
    run.verify_provenance("after-export")
    run.result.update(sdkCommit=SDK, starterSourceSHA256=source_sha,
                      starterLockSHA256=digest(exported / "mixer.lock"))
    return {
        "MIXER_STARTER_PROOF_ROOT": str(run.root), "MIXER_STARTER_EXPORT": str(exported),
        "MIXER_STARTER_CLI": str(cli), "MIXER_STARTER_PREPARE": str(prepare),
        "MIXER_STARTER_EXPORT_SHA256": source_sha, "MIXER_STARTER_DISPATCH_ID": "l07-starter-worker",
        "MIXER_STARTER_DISPATCH_PORT": str(run.port("worker")),
    }


def ledger(state, operation=None, *, count=False):
    path = state / "operations.sqlite"
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=0.2)) as db:
        if count:
            return db.execute("SELECT count(*) FROM operations").fetchone()[0]
        if operation is None:
            return db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        row = db.execute("SELECT value FROM operations WHERE id = ?", (operation,)).fetchone()
        return json.loads(row[0]) if row else None


SNAPSHOT = """SELECT json_build_object(
  'builds', (SELECT json_agg(json_build_object('id',id,'buildId',build_id,'revision',revision,
              'journal',journal,'key',request_key)) FROM mixer_builds),
  'jobs', (SELECT json_agg(json_build_object('queue',queue,'state',state,'kind',args->>'kind',
            'attempt',attempt,'errors',errors) ORDER BY id) FROM oban_jobs),
  'capacity', (SELECT json_agg(json_build_object('record',build_record_id,'attempt',attempt,'held',held,
                'fence',worker_fence,'event',terminal_event_id)) FROM mixer_build_reservations),
  'leases', (SELECT json_agg(json_build_object('record',build_record_id,'owner',owner_id,
              'expires',expires_at)) FROM mixer_build_coordinator_leases),
  'operations', (SELECT json_agg(json_build_object('operation',operation_id,'record',record_id,
                  'state',admission_state,'deadline',deadline_ms)) FROM mixer_build_operation_admissions)
)"""


def billing(run, label, owner_org=None):
    names = json.loads(run.sql(f"{label}-billing-tables", r"""
        SELECT json_agg(tablename ORDER BY tablename) FROM pg_tables
        WHERE schemaname='public' AND tablename LIKE 'mixer\_billing\_%'
    """))
    require("mixer_billing_organization_state" in names, "fixture billing table missing")
    result = {}
    for table in names:
        require(re.fullmatch(r"mixer_billing_[a-z_]+", table), "unexpected billing table name")
        rows = run.sql(f"{label}-{table}",
                       f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)), '[]'::jsonb) FROM public.{table} t")
        values = json.loads(rows)
        if owner_org is not None and table == "mixer_billing_organization_state":
            mirror, = (row for row in values if row["organization_id"] == owner_org)
            values.remove(mirror)
            result["ownerMirror"] = mirror
            rows = compact(values)
        result[table] = {"rows": len(values), "sha256": sha(rows.encode())}
    return result


def request_binding(operation, selection, record_id, spec, request, *, live=False):
    ref = dict(selection, attempt=1, fence=1)
    ref = {k: ref[k] for k in (*SCOPE, "build_id", "attempt", "fence")}
    require(request["operation_id"] == operation and request["ref"] == ref
            and request["spec"] == dict(spec, build_id=selection["build_id"]),
            "worker request differs from the single selected operation")
    guard = request["guard"]
    require(guard["record_id"] == record_id and guard["revision"] == 1
            and type(guard["epoch"]) is int and guard["epoch"] > 0
            and re.fullmatch(r"oban:[0-9]+:[a-f0-9-]{36}", guard["owner_id"])
            and type(guard["expires_at"]) is int and type(request["deadline_ms"]) is int
            and 0 < guard["expires_at"] < request["deadline_ms"]
            and (not live or time.time_ns() // 1_000_000 < guard["expires_at"]),
            "worker request guard differs from the admitted attempt")
    return {k: request[k] for k in ("ref", "spec", "deadline_ms")}


def terminal_payload_sha(row):
    return json_sha({k: row[k] for k in ("binding", "status", "starts", "closure", "artifacts", "manifest_sha256")})


def verify_worker_closure(run, operation, row, binding, cli, *, ready):
    require(row["status"] == ("native_ready" if ready else "closed") and row.get("tombstone") is not True
            and type(row["starts"]) is int and row["starts"] == 1 and row["binding"] == binding,
            "durable operation does not match the selected terminal attempt")
    closure = row["closure"]
    require(all(closure.get(k) is True for k in ("closed", "started", "cli_reaped", "cli_group_absent"))
            and type(closure["exit"]) is int and type(closure["pid"]) is int and closure["pid"] > 1,
            "native CLI custody did not close positively")
    commands = closure["commands"]
    require(type(commands) is list and all(
        x["command"].startswith("/") and type(x["pid"]) is int and x["pid"] > 1
        and re.fullmatch(r"[0-9a-f]{64}", x["receipt_sha256"])
        and x["group_terminate_sent"] is False and x["stop_reason"] is None for x in commands),
        "nested command custody did not close positively")
    compiler_starts = sum(x["command"] == "/usr/bin/xcodebuild" for x in commands)
    preflight = closure.get("preflight_failed") is True
    if preflight:
        require(not ready and closure["exit"] > 0 and compiler_starts == 0, "invalid preflight failure closure")
    else:
        require(compiler_starts == 1 and (not ready or closure["exit"] == 0), "invalid compiler closure")
    output = run.state / operation
    launch, terminal = output / "launch.json", output / "closure.json"
    require(output.resolve(strict=True) == output
            and all(stat.S_ISREG(path.lstat().st_mode) for path in (launch, terminal)),
            "worker launch or closure record is outside the owned operation")
    argv = [cli, "build", "--platform", "ios", "--directory", str(output / "project"),
            "--output", str(output / "native")]
    require(read(launch) == {"pid": closure["pid"], "argv": argv} and read(terminal) == closure,
            "worker closure does not match the operation's exact CLI launch")
    return closure, compiler_starts


def retained_state(run, relay, operation, selection, record_id, spec, cli):
    row = ledger(run.state, operation)
    if row and row["status"] == "uncertain":
        raise Hold("pinned worker reported uncertain compiler custody")
    with relay.lock:
        start_request, failure, held = relay.start_request, relay.failure, relay.held.is_set()
    if row and row["status"] == "closed":
        require(start_request is not None, "closed operation lacks its authenticated start request")
        binding = request_binding(operation, selection, record_id, spec, start_request)
        closure, starts = verify_worker_closure(run, operation, row, binding, cli, ready=False)
        run.result.update(workerStatus="closed", workerClosure=closure, workerStarts=1,
                          compilerStarts=starts, ensureStartedRequests=1, failedOperationSHA256=json_sha(row),
                          error="Worker closed the selected native attempt without retained artifacts")
        try:
            with (run.state / operation / "stdout").open("rb") as stream:
                raw = stream.read(LIMIT + 1)
            if len(raw) <= LIMIT:
                run.result["cliStdoutSHA256"] = sha(raw)
                diagnostic = json.loads(raw)
                if isinstance(diagnostic, dict) and re.fullmatch(r"[a-z0-9_.-]{1,100}", diagnostic.get("code") or ""):
                    run.result["cliFailureCode"] = diagnostic["code"]
        except (OSError, ValueError, TypeError):
            pass
        return "failed"
    if failure is not None:
        raise Hold(f"relay could not validate retained response ({type(failure).__name__})")
    return "retained" if held else None


def observe_worker(run, relay, operation, selection, record_id, spec, cli, *, seconds=240):
    terminal = wait(lambda: retained_state(run, relay, operation, selection, record_id, spec, cli),
                    seconds, getattr(run, "processor", None))
    run.native_pending = False
    return terminal


def confirm_closed(run, operation, selection, record_id, spec, cli, request, reply, frame):
    if reply.get("status") != "native_ready":
        return False
    binding = request_binding(operation, selection, record_id, spec, request, live=True)
    row = ledger(run.state, operation)
    closure, _ = verify_worker_closure(run, operation, row, binding, cli, ready=True)
    artifacts = reply["artifacts"]
    require(artifacts == row["artifacts"] and tuple(x["kind"] for x in artifacts) == KINDS
            and all(re.fullmatch(r"[0-9a-f]{64}", x["sha256"])
                    and type(x["sizeBytes"]) is int and x["sizeBytes"] > 0 for x in artifacts),
            "invalid durable native artifact descriptors")
    output = run.state / operation
    manifest = output / "native/native-build.json"
    require(digest(manifest) == row["manifest_sha256"], "persisted native manifest digest differs")
    report = read(manifest)
    compiler_source = report["binding"]["compilerSourceDigest"]
    require(report["commandResult"]["exitCode"] == 0
            and report["binding"]["authoritativeSourceDigest"] == spec["source"]["sha256"]
            and report["binding"]["lockSHA256"] == spec["toolchain_lock_sha256"]
            and report["binding"]["cliExecutableSHA256"] == run.result["cliSHA256"]
            and compiler_source == run.result["provenanceSourceSHA256"],
            "retained manifest does not bind the pinned CLI and selected source")
    run.result.update(workerClosure=closure, terminalFrameSHA256=sha(frame),
                      manifestSHA256=row["manifest_sha256"], compilerSourceSHA256=compiler_source,
                      workerStarts=1, compilerStarts=1, retainedOperationSHA256=terminal_payload_sha(row))
    return True


def settle(run, record_id, operation, selection, previous_billing, config):
    end = time.monotonic() + 32
    for index in range(64):
        state = json.loads(run.sql(f"settle-{index}", SNAPSHOT))
        if (state["builds"][0]["revision"] == 2
                and all(job["state"] == "completed" for job in state["jobs"])):
            break
        require(time.monotonic() < end, "restricted processor failed to settle within the deadline")
        time.sleep(0.3)
    else:
        raise RuntimeError("restricted processor exceeded the settlement observation limit")
    [build] = state["builds"]
    row = ledger(run.state, operation)
    require(ledger(run.state, count=True) == 1 and ledger(run.state)
            and row["starts"] == 1 and row["status"] == "native_ready",
            "replacement did not preserve the single integral worker operation")
    require(build["id"] == record_id and build["buildId"] == selection["build_id"] and build["key"] == KEY
            and build["journal"]["creation"]["spec"] == row["binding"]["spec"],
            "persisted idempotency key or build binding differs")
    start, terminal = build["journal"]["events"]
    event = "coordinator:1:1:completed"
    artifacts = row["artifacts"]
    require(start["id"] == "coordinator:1:0:start" and terminal["id"] == event
            and terminal["event"]["result"] == {"outcome": "native_succeeded", "artifacts": [
                {"kind": a["kind"], "sha256": a["sha256"], "size_bytes": a["sizeBytes"]} for a in artifacts]},
            "journal did not commit the retained artifacts exactly once")
    require(state["jobs"] == [{"queue": "builds", "state": "completed", "kind": kind,
                               "attempt": 1, "errors": []} for kind in ("created", "start", "completed")],
            "restricted job history differs")
    require(state["capacity"] == [{"record": record_id, "attempt": 1, "held": False, "fence": 1, "event": event}]
            and state["leases"] == [{"record": record_id, "owner": None, "expires": None}]
            and state["operations"] == [{"operation": operation, "record": record_id, "state": "admitted",
                                          "deadline": row["binding"]["deadline_ms"]}],
            "capacity, lease, or durable operation readback differs")
    require(billing(run, "after") == previous_billing, "billing rows changed during the free build")
    require(digest(run.state / operation / "native/native-build.json") == run.result["manifestSHA256"],
            "new upstream does not retain the original artifact manifest")

    run.mark("api.refresh")
    fresh = run.ready("api.renewed", run.api, 12)
    run.sessions(fresh)
    require(all(fresh[k] != run.auth[k] for k in ("cookie", "unrelatedCookie")), "sessions did not renew")
    owner = dict(run.auth, cookie=fresh["cookie"])
    outsider = dict(run.auth, cookie=fresh["unrelatedCookie"])
    query = "?" + urlencode(selection)
    code, _, body = http(owner, BUILD + query)
    require(code == 200 and http(owner, BUILD + query)[::2] == (200, body), "owner build readback changed")
    readback = json.loads(body)["build"]
    require((readback["buildId"], readback["revision"], readback["state"]) ==
            (selection["build_id"], 2, "native_succeeded"), "unexpected owner build state")
    denied = http(outsider, BUILD + query)[0]
    require(denied in (403, 404), "unrelated tenant can read the build")
    outputs = []
    for item in artifacts:
        kind = item["kind"]
        path = f"/console-api/v1/build-artifacts/{kind}" + query
        status, headers, payload = http(owner, path)
        other = http(outsider, path)[0]
        require(status == 200 and other in (403, 404)
                and headers["content-type"] == "application/octet-stream"
                and headers["content-disposition"] == f'attachment; filename="{kind}"'
                and (len(payload), sha(payload)) == (item["sizeBytes"], item["sha256"]),
                "retained artifact HTTP bytes or tenant isolation differ")
        outputs.append(dict(item, httpStatus=status, unrelatedTenantHTTP=other))
    run.result.update(buildId=selection["build_id"], revision=2, terminalState="native_succeeded",
                      jobKinds=["created", "start", "completed"], capacityReleases=1,
                      leaseReleased=True, billingUnchanged=True, sqliteIntegrity="ok",
                      persistedIdempotencyKey=True, stableAuthenticatedBuildReads=True,
                      unrelatedTenantBuildHTTP=denied, artifacts=outputs, sameArtifactStore=True,
                      replacementWorkerPort=config["port"])
    return state, outsider


def tenant_scope(auth, scope):
    org, project, app = (scope[key] for key in SCOPE[:3])
    requests = {
        "session": "/auth/session",
        "organizations": "/console-api/v1/orgs",
        "projects": "/console-api/v1/projects?" + urlencode({"organization_id": org}),
        "applications": "/console-api/v1/applications?" + urlencode({
            "organization_id": org, "project_id": project}),
    }
    pages = {}
    for name, path in requests.items():
        status, _, raw = http(auth, path)
        require(status == 200, f"unrelated tenant {name} returned HTTP {status}")
        pages[name] = json.loads(raw)
    require(pages.pop("session")["state"] == "authenticated", "unrelated session is unauthenticated")
    require([item["id"] for item in pages["organizations"]["organizations"]] == [org]
            and [(item["organization_id"], item["id"]) for item in pages["projects"]["projects"]]
            == [(org, project)], "unrelated organization or project is out of scope")
    require(pages["applications"] == {"organizationId": org, "projectId": project, "nextCursor": None,
                                      "applications": [{"applicationId": app}]},
            "unrelated application is out of scope")
    return pages


def owner_session(run, label, auth, *, expire=False):
    # Bind the SQL observation or mutation to the exact synthetic cookie's credential.
    selector = f"""
        FROM public.mixer_browser_sessions s
        JOIN public.mixer_authz_credentials c ON (c.profile_id,c.profile_version,c.reference) =
             (s.profile_id,s.profile_version,s.credential_ref)
        WHERE s.cookie_digest=decode('{sha(auth['cookie'].encode())}','hex') AND s.principal_id='person-1'
          AND c.principal_id=s.principal_id
    """
    if expire:
        changed = run.sql("expire-owner-credential", f"""
            WITH expired AS (
              UPDATE public.mixer_authz_credentials target
              SET expires_at=floor(extract(epoch FROM clock_timestamp()))::bigint-5
              WHERE (target.profile_id,target.profile_version,target.reference) = (
                SELECT c.profile_id,c.profile_version,c.reference {selector}
                  AND LEAST(s.idle_expires_at,s.absolute_expires_at) < extract(epoch FROM clock_timestamp())
              ) AND target.active RETURNING 1
            ) SELECT count(*) FROM expired
        """)
        require(changed == "1", "exact expired owner's fixture credential was not updated")
    sample = json.loads(run.sql(label, f"""
        SELECT json_build_object('principal',s.principal_id,'rowStatus',s.status,
          'sessionExpiresAt',LEAST(s.idle_expires_at,s.absolute_expires_at),
          'credentialExpiresAt',c.expires_at,'credentialActive',c.active,
          'sampleAt',floor(extract(epoch FROM clock_timestamp()))::bigint) {selector}
    """))
    require(sample["rowStatus"] == "active" and sample["credentialActive"] is True,
            "former-owner session or credential is not active in the fixture catalog")
    return sample


def first_owner_read(run, label, auth, path, session, status, error):
    # The marker and receipt count precede the sole GET, even if the response is lost.
    run.mark(label)
    observation = run.result[label] = {"attempts": 1, "session": session}
    run.evidence()
    start = time.monotonic()
    actual, headers, body = http(auth, path, limit=1024)
    observation.update(httpStatus=actual, elapsedMs=round((time.monotonic() - start) * 1000),
                       bodyBytes=len(body), bodySHA256=sha(body))
    require(actual == status and headers.get("content-type", "").startswith("application/json")
            and "set-cookie" not in headers and "retry-after" not in headers,
            f"{label} returned HTTP {actual} or unexpected headers")
    expected = {"code": error}
    if status == 401:
        expected["message"] = "Browser request refused."
    require(json.loads(body) == {"error": expected}, f"{label} returned an unexpected error body")
    observation["errorCode"] = error


def owner_exit_readback(run, selection, outsider):
    org, project = (selection[key] for key in SCOPE[:2])
    require(re.fullmatch(r"org-[0-9a-f]{32}", org), "exit is restricted to the fixture-created organization")
    unrelated = run.auth["unrelatedScope"]
    require(org != unrelated["organization_id"], "owner and unrelated fixture scopes overlap")
    before = tenant_scope(outsider, unrelated)
    billing_before = billing(run, "before-exit", org)
    operation = run.result.get("operationId")
    retained = ledger_snapshot(run.state, operation) if operation else None

    run.mark("api.exit-short")
    owner = dict(run.auth, **run.ready("api.exit-owner", run.api, 12))
    initial = owner_session(run, "short-owner-current", owner)
    deadline = initial["sessionExpiresAt"]
    require(0 < deadline - initial["sampleAt"] <= 45 and initial["credentialExpiresAt"] > initial["sampleAt"],
            "fixture OAuth did not issue a current short owner session")
    admin = "/console-api/v1/workspace-admin"
    status, _, raw = http(owner, admin, {"operation": "export", "organization_id": org}, limit=4096)
    require(status == 200, f"owner workspace export returned HTTP {status}")
    exported = json.loads(raw)
    require(exported["organization"]["id"] == org
            and [(row["id"], row["active"]) for row in exported["projects"]] == [(project, True)]
            and exported["memberships"] == [{"principal_id": "person-1", "role": "owner", "active": True}],
            "workspace export is out of owner scope")
    status, _, raw_exit = http(owner, admin, {
        "operation": "delete_organization", "organization_id": org, "confirm": org}, limit=4096)
    require(status == 200 and json.loads(raw_exit) == {"organization_id": org, "deleted": True,
                                                      "retention": "tombstone"},
            f"owner workspace exit failed with HTTP {status} or invalid tombstone")
    require(run.sql("organization-tombstone", f"""
        SELECT active FROM public.mixer_authz_organizations WHERE id='{org}'
    """) == "f", "owned organization tombstone is missing")
    run.result["workspace"] = {"exportHTTP": 200, "exportSHA256": sha(raw), "exportBytes": len(raw),
                               "exitHTTP": 200, "organizationActive": False, "tombstone": True}

    path = BUILD + "?" + urlencode(selection)
    wait(lambda: int(time.time()) > deadline, 48, run.api)
    expired = owner_session(run, "short-owner-expired", owner, expire=True)
    require(expired["sessionExpiresAt"] == deadline
            and max(expired["credentialExpiresAt"], deadline) < expired["sampleAt"],
            "short owner session and joined credential have not expired")
    first_owner_read(run, "expiredOwnerFirstBuildGET", owner, path, expired, 401, "unauthenticated")
    run.mark("api.exit-renew")
    fresh = run.ready("api.exit-renewed", run.api, 12)
    renewed = dict(run.auth, cookie=fresh["cookie"])
    require(renewed["cookie"] != owner["cookie"], "OAuth renewal reused the expired owner cookie")
    current = owner_session(run, "renewed-owner-current", renewed)
    require(current["sampleAt"] < min(current["credentialExpiresAt"], current["sessionExpiresAt"]),
            "renewed owner's catalog authority is expired")
    first_owner_read(run, "renewedFormerOwnerFirstBuildGET", renewed, path, current, 404, "not_found")

    outsider = dict(run.auth, cookie=fresh["unrelatedCookie"])
    require(tenant_scope(outsider, unrelated) == before and http(outsider, path, limit=1024)[0] == 404,
            "unrelated tenant scope changed or the owner build became readable")
    billing_after = billing(run, "after-exit", org)
    mirror = billing_before.pop("ownerMirror")
    require(mirror["active"] is True and billing_after.pop("ownerMirror") ==
            dict(mirror, active=False, revision=mirror["revision"] + 1) and billing_before == billing_after,
            "workspace exit changed billing beyond the owner's organization mirror")
    run.result.update(unrelatedTenant={"ownScopeVerified": True, "sameScopedContent": True,
                                       "ownerBuildHTTP": 404, "scope": unrelated},
                      billingExitOnlyOwnerMirror=True, postExitStatusRetries=0)
    return retained


def restart_replay(run, preflight):
    startup = Path(run.auth["startup"])
    pin = run.auth["startupPin"]
    require(startup.resolve(strict=True).is_relative_to(run.root), "startup must be owned")
    config = read(startup)
    spec = run.auth["spec"]
    cli = config["policy"]["cli"]
    require(config["port"] == run.ports["worker"] and config["registration"]["spec"] == spec
            and spec["source"]["sha256"] == run.result["starterSourceSHA256"]
            and spec["toolchain_lock_sha256"] == run.result["starterLockSHA256"],
            "worker startup is not bound to the fixture's selected export")
    run.result["originalStartupSHA256"] = start_worker(run, "worker", config, startup, pin)
    probe = canary(config)
    denied = {"error": "unavailable"}
    require(wire(config, "query", probe) == denied, "original worker authentication failed")
    selected = run.auth["selection"]
    witness = {}

    def observe(request, reply, frame):
        return confirm_closed(run, witness["operation"], witness["selection"], witness["record"],
                              spec, cli, request, reply, frame)

    relay = run.relay = Relay(config, "artifacts", observe)
    require(relay.port not in run.ports.values(), "relay listener collision")
    run.ports["relay"] = relay.port
    relay.begin()
    require(wire(config, "query", probe, port=relay.port) == denied, "relay did not reach original worker")
    run.launch_processor({
        "MIXER_BUILD_DISPATCH": "native_development_v1", "MIXER_NATIVE_RETAINED_ROOT": str(run.state),
        "MIXER_NATIVE_WORKER_PORT": str(relay.port), "MIXER_NATIVE_WORKER_ID": config["worker_id"],
        "MIXER_NATIVE_WORKER_TOKEN": config["token"],
    })
    baseline = billing(run, "before")
    require(all(value is None for value in json.loads(run.sql("before-post", SNAPSHOT)).values())
            and ledger(run.state, count=True) == 0, "fixture is not empty before POST")
    require(run.sql("idempotency-index", """
      SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND tablename='mixer_builds'
        AND indexdef LIKE 'CREATE UNIQUE INDEX%'
        AND indexdef LIKE '%(organization_id, project_id, application_id, platform, request_key)%'
    """) == "1", "scoped request-key unique index is missing")
    run.verify_provenance("prepost-ready")
    run.result.update(status="all_real_services_prepost_ready", workerReadyAuthenticated=True,
                      workerStarts=0, compilerStarts=0, paymentServiceConfigured=False)
    run.evidence()
    if preflight:
        return "PASS_L07_PREPOST"

    print("L07 pre-POST checkpoint ready. Confirm the one real build within 90 seconds.", flush=True)
    wait(lambda: (run.root / "prepost-verified").is_file(), 90, run.processor)
    run.verify_provenance("before-post")
    body = {snake: selected[camel] for snake, camel in zip(
        (*SCOPE, "source_input_id", "source_sha256", "toolchain_lock_sha256", "build_definition_sha256"),
        ("organizationId", "projectId", "applicationId", "platform", "sourceInputId", "sourceSha256",
         "toolchainLockSha256", "buildDefinitionSha256"), strict=True)}
    run.mark("single-post-attempt")
    run.result.update(buildPOSTAttempts=1, status="one_post_attempted")
    run.evidence()
    code, _, raw = http(run.auth, BUILD, body)
    require(code == 201, f"one real build POST returned HTTP {code}")
    payload = json.loads(raw)
    components = [x.encode() for x in ("mixer.customer-build.v1", *(body[k] for k in SCOPE), KEY)]
    build = "build-" + sha(b"".join(len(value).to_bytes(4, "big") + value for value in components))
    selection = dict({key: value for key, value in body.items() if key != "source_input_id"}, build_id=build)
    require(payload["outcome"] == "applied" and payload["state"] == "queued"
            and payload["revision"] == 0 and payload["selection"] == selection,
            "build POST did not create the selected deterministic queued build")
    queued = json.loads(run.sql("queued", SNAPSHOT))
    [stored] = queued["builds"]
    require(stored["buildId"] == build and stored["revision"] == 0 and stored["journal"]["events"] == []
            and stored["key"] == KEY and queued["jobs"] == [
                {"queue": "builds", "state": "available", "kind": "created", "attempt": 0, "errors": []}]
            and all(queued[k] is None for k in ("capacity", "leases", "operations")),
            "paused processor or single build queue state differs")
    record_id = stored["id"]
    operation = sha(compact(["mixer-build-operation-v1", record_id,
                             *(selection[k] for k in (*SCOPE[:3], "build_id", "platform")), 1, 1]).encode())
    run.result.update(buildHTTP=code, operationId=operation, buildId=build, billingBefore=baseline)
    witness.update(operation=operation, selection=selection, record=record_id)
    relay.operation = operation
    run.native_pending = True
    run.mark("processor.run")

    terminal = observe_worker(run, relay, operation, selection, record_id, spec, cli)
    if terminal == "failed":
        return "FAILED_CLOSED_NATIVE_BUILD"
    blocked = json.loads(run.sql("before-switch", SNAPSHOT))
    require(blocked["builds"][0]["revision"] == 1 and blocked["capacity"][0]["held"] is True
            and blocked["operations"][0]["operation"] == operation,
            "hosted build settled before the closed-worker switch")
    old_store = (run.state / operation / "native").stat()
    new_config = route_replacement(run, relay, config, probe, operation=operation)
    new_store = (run.state / operation / "native").stat()
    require((old_store.st_dev, old_store.st_ino) == (new_store.st_dev, new_store.st_ino),
            "replacement did not use the same owned artifact store")
    state, outsider = settle(run, record_id, operation, selection, baseline, new_config)
    require(relay.failure is None
            and [item for item in relay.requests if item[0] == "ensure_started"] ==
            [("ensure_started", operation, config["port"])]
            and ("artifacts", operation, new_config["port"]) in relay.requests,
            "replayed query did not use the replacement without another start")
    run.result.update(ensureStartedRequests=1, retainedArtifactReplies=1)
    if run.owner_exit:
        retained = owner_exit_readback(run, selection, outsider)
        require(json.loads(run.sql("after-exit-build-state", SNAPSHOT)) == state
                and ledger_snapshot(run.state, operation) == retained
                and ledger(run.state, count=True) == 1 and ledger(run.state),
                "exit or readback changed the settled build, jobs, capacity, or worker ledger")
        store = run.state / operation / "native"
        require(digest(store / "native-build.json") == run.result["manifestSHA256"],
                "exit changed the retained manifest")
        for artifact in run.result["artifacts"]:
            path = store / artifact["sha256"]
            info = path.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_size == artifact["sizeBytes"]
                    and digest(path) == artifact["sha256"], "exit changed a retained artifact")
        run.result.update(terminalJournalSHA256=json_sha(state["builds"][0]["journal"]),
                          retainedBuildAndWorkerUnchanged=True, retainedArtifactDigestsVerified=True)
        return "PASS_SCOPED_STARTER_OWNER_EXIT"
    return "PASS_SCOPED_STARTER_WORKER_RESTART"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--inert-only", dest="mode", action="store_const", const="inert")
    modes.add_argument("--source-only", dest="mode", action="store_const", const="source",
                       help="verify archived replay inputs without starting services")
    modes.add_argument("--fixture-only", dest="mode", action="store_const", const="fixture")
    modes.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--owner-exit", action="store_true",
                        help="prove first former-owner build reads after the workspace exits")
    parser.add_argument("--pg-bin", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin"))
    args = parser.parse_args()
    mode = args.mode or "full"
    os.umask(0o077)
    parent = ROOT / "verification/local"
    parent.mkdir(parents=True, exist_ok=True)
    prefix = "l06-owner-exit-" if args.owner_exit else "l07-restart-"
    run = Run(Path(tempfile.mkdtemp(prefix=prefix, dir=parent)).resolve(), mode, args.owner_exit)
    print(f"{'L06' if args.owner_exit else 'L07'} run directory {run.root}", flush=True)
    outcome = "FAILED"
    try:
        run.stage(mode)
        if mode == "inert":
            inert_replay(run)
            outcome = "PASS_INERT_L07_RESTART"
        elif mode == "source":
            run.stage_provenance()
            run.verify_provenance("source-admission")
            outcome = "PASS_L07_SOURCE_ADMISSION"
        else:
            run.hosted_dependencies()
            extra = prepare_export(run) if mode == "full" else {}
            run.open_database(args)
            run.launch_api(extra)
            if mode == "fixture":
                run.launch_processor()
                require(run.sql("fixture-zero-builds", "SELECT count(*) FROM mixer_builds") == "0",
                        "fixture unexpectedly created a build")
                run.result["buildRows"] = 0
                if run.owner_exit:
                    selection = dict(run.auth["ownerScope"], platform="ios", build_id="build-" + "0" * 64,
                                     **{k: "0" * 64 for k in ("source_sha256", "toolchain_lock_sha256",
                                                               "build_definition_sha256")})
                    owner_exit_readback(run, selection, dict(run.auth, cookie=run.auth["unrelatedCookie"]))
                    require(run.sql("exit-fixture-zero-builds", "SELECT count(*) FROM mixer_builds") == "0",
                            "exit fixture unexpectedly created a build")
                    outcome = "PASS_ORDINARY_L06_OWNER_EXIT_FIXTURE"
                else:
                    outcome = "PASS_ORDINARY_L07_FIXTURE"
            else:
                outcome = restart_replay(run, args.preflight_only)
    except BaseException as error:
        run.result["error"] = f"{type(error).__name__}: {error}"
        print(run.result["error"], file=sys.stderr)
    receipt = parent / (run.root.name + ".json")
    staged_receipt = receipt.with_suffix(".closed.json")
    try:
        if run.unknown or run.native_pending:
            raise Hold("command or native operation custody is unknown")
        run.close_services()
        require(run.closed(), "missing matching terminal evidence for an attempted launch")
        run.result["portsRebound"] = rebound(run.ports.values())
        if "api" in run.attempts and (outcome.startswith("PASS") or outcome == "FAILED_CLOSED_NATIVE_BUILD"):
            require(run.result.get("databaseDropped") is True
                    and all(run.attempts[name]["exit"] == 0 for name in ("api", "processor", "postgres")),
                    "fixture services did not close cleanly")
        try:
            run.verify_provenance("after-service-shutdown")
            for name in run.helper_pins:
                run.helper_source(name)
        except (RuntimeError, OSError) as error:
            run.result["sourceVerificationError"] = str(error)
            if outcome.startswith("PASS"):
                outcome = "FAILED_SOURCE_VERIFICATION"
        run.result["nativePending"] = run.native_pending
        run.result["status"] = outcome
        record(staged_receipt, run.result)
        run.load_helper("run-proof").remove_closed_tree(run.root)
        staged_receipt.replace(receipt)
    except BaseException as error:
        run.result["status"] = "HOLD"
        run.result["nativePending"] = run.native_pending
        run.result["holdReason"] = f"{type(error).__name__}: {error}"
        try:
            hold = run.root / "HOLD.json" if run.root.is_dir() else receipt.with_suffix(".HOLD.json")
            record(hold, run.result)
        finally:
            print(f"Preserve {run.root} for custody review: {run.result['holdReason']}", file=sys.stderr)
        return 74
    print(f"{outcome} {receipt}", flush=True)
    return 0 if outcome.startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
