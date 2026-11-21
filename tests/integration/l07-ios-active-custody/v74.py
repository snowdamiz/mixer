"""Local v74 composition. The preflight never dispatches a compiler."""

import base64
from contextlib import contextmanager
import hashlib
import json
import os
import subprocess
import sys
import time

BASE = "44aecbeb6a82a4a93321cff6a8ab86c5aa421900"
CATALOG_REVISION = "2fa5d18c7d7eed4b8687d2d6159fae8606636431"
CATALOG_HOSTED_TREE = "5f45ec34fa5a3ffa75c878eaeed00d0887171b50"
# Published Ed25519 test vector public key, used only for the zero-build preflight.
PREFLIGHT_SPKI = bytes.fromhex(
    "302a300506032b6570032100d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)


def replace(path, old, new, *, count=1):
    source = path.read_text()
    if source.count(old) != count:
        raise RuntimeError(f"pinned fixture anchor differs in {path.name}")
    path.write_text(source.replace(old, new))


def compose(root, here, pair):
    api = root / pair / "api-case.exs"
    replace(api, "  {cookie, csrf} = login(c)\n\n  pair25_publish!",
            "  {cookie, csrf} = login(c)\n"
            "  v74_check_browser!(c, cookie)\n\n  pair25_publish!")
    replace(api, "  pair25_wait!(c, false, System.monotonic_time(:millisecond) + 1_240_000)",
            "  v74_wait!(c, scope, build, System.monotonic_time(:millisecond) + 1_240_000)")
    with api.open("a") as stream:
        stream.write("\n" + (here / "v74-api.exs").read_text())


def configure_hosted(root, pair, api_test):
    api = root / "hosted" / api_test
    replace(api, "    c\n    |> put_in(\n      [:hosted, Access.key(:create_repo)],",
            "    c\n    |> pair25_processor!()\n    |> v74_endpoint!()\n    |> put_in(\n"
            "      [:hosted, Access.key(:create_repo)],")
    case = (root / pair / "api-case.exs").read_text()
    raw = api.read_text()
    closing_line = raw.rindex("\nend\n")
    api.write_text(raw[:closing_line] + "\n" +
                   "\n".join("  " + line if line else "" for line in case.splitlines()) +
                   raw[closing_line:])

    provider = root / "hosted/test/support/browser_login_provider_fixture.ex"
    replace(provider, 'subject = if s.mode == :other_tenant, do: "subject-2", else: "subject-1"',
            'subject = Map.get(s, :pair25_subject, "subject-1")')
    replace(provider, "  def handle_call(:count", """  def handle_call({:pair25_subject, subject}, _, s)
      when subject in ["subject-1", "subject-2"],
      do: {:reply, :ok, Map.put(s, :pair25_subject, subject)}

  def handle_call(:count""")
    replace(provider, "_ -> 120", "_ -> 720", count=2)

    # Keep the settled database for an unconfirmed attachment. The parent
    # removes the isolated cluster after success or before any attach attempt.
    startup = root / "hosted/test/support/ordinary_browser_startup_fixture.ex"
    replace(startup, '''        Postgrex.query!(
          conn,
          "DROP DATABASE browser_ordinary_installation_r1422 WITH (FORCE)",
          [],
          timeout: 20_000
        )''', '''        unless File.regular?(Path.join(System.fetch_env!("PAIR25_RUN"), "v74.attaching")) do
          Postgrex.query!(
            conn,
            "DROP DATABASE browser_ordinary_installation_r1422 WITH (FORCE)",
            [],
            timeout: 20_000
          )
        end''')


class OwnedProcess(subprocess.Popen):
    # A constructor or unwind failure must never schedule an implicit reap.
    def __del__(self):
        pass

    def poll(self):
        if self.returncode is None:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid == self.pid:
                self.returncode = os.waitstatus_to_exitcode(status)
        return self.returncode

    def wait(self, timeout=None):
        if timeout is None:
            raise ValueError("an owned command requires a finite wait")
        deadline = time.monotonic() + timeout
        while self.poll() is None:
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(self.args, timeout)
            time.sleep(0.02)
        return self.returncode


def owned_runner(kit):
    require = kit["require"]

    @contextmanager
    def owned(root, name, argv, cwd, env, receipts, stop=None, *, exit_codes=(0,)):
        require(name not in receipts, "duplicate process label")
        receipt = receipts[name] = {"argv": list(map(str, argv)), "groupAbsent": False}
        output = root / (name + ".log")
        # Record the attempt before Popen so constructor errors leave a hold.
        kit["write"](root / (name + ".intent.json"), receipt)
        with output.open("xb") as log:
            process = OwnedProcess(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            receipt["pid"] = process.pid
            kit["record_custody"](root, name, process, closed=False)
            own_timeout = False
            try:
                yield process
            except subprocess.TimeoutExpired as error:
                own_timeout = error.cmd == process.args
                raise
            finally:
                wrapper = receipts.get("attest-settled")
                preserve_service = name in ("api", "postgres") and wrapper is not None and (
                    not wrapper["groupAbsent"] or os.path.lexists(root / "HOLD.json"))
                if preserve_service:
                    receipt["preservedForWrapper"] = True
                # Leave the exact timed-out command and services it may still need alone.
                if not own_timeout and not preserve_service:
                    try:
                        if process.poll() is None:
                            if callable(stop):
                                stop()
                            elif stop is not None:
                                require(os.getpgid(process.pid) == os.getsid(process.pid) == process.pid,
                                        "owned shutdown identity changed")
                                os.killpg(process.pid, stop)
                        code = process.wait(timeout=16)
                        kit["wait"](lambda: kit["group_absent"](process.pid), 4)
                        proof = dict(receipt, exit=code, directChildReaped=True, groupAbsent=True,
                                     logSHA256=file_sha(output))
                        kit["write"](root / (name + ".terminal.json"), proof)
                        kit["record_custody"](root, name, process, closed=True)
                        receipt.update(proof)
                    except (OSError, TimeoutError, subprocess.TimeoutExpired) as exc:
                        raise kit["CustodyUnknown"](f"{name} closure left unresolved custody") from exc
                    require(code in exit_codes, f"{name} exited {code}; inspect its fresh receipt")

    return owned


def file_sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def command(root, kit, result, name, argv, env, *, cwd=None, timeout=12):
    with kit["owned"](root, name, argv, cwd or root, env, result["commands"]) as process:
        process.wait(timeout=timeout)
    return root / (name + ".log")


def enroll(root, kit, env, pg, result, api, auth, operator, ready, *, preflight):
    require = kit["require"]
    def closed(name):
        proof = result["commands"][name]
        return (proof.get("exit") == 0 and proof.get("groupAbsent") is True
                and proof.get("directChildReaped") is True)

    require(closed("processor"),
            "restricted processor closure is required before enrollment")
    if not preflight:
        require(result["liveCustodyPending"] is False and result["xcodeInvocations"] == 1
                and result["liveClosure"]["xcodeExit"] == 0
                and closed("worker") and closed("independent-parent"),
                "positive worker, CLI and Xcode closure is required before enrollment")
    origin = f"http://127.0.0.1:{auth['port']}"
    result["stage"] = "v74-origin-preserving-enrollment"
    if preflight:
        spki = PREFLIGHT_SPKI
    else:
        keys = operator / "keys"
        keys.mkdir(mode=0o700)
        private = keys / "development.pem"
        public = keys / "development.pub.pem"
        command(root, kit, result, "keygen",
                ["openssl", "genpkey", "-algorithm", "Ed25519", "-out", private], env)
        command(root, kit, result, "public-key",
                ["openssl", "pkey", "-in", private, "-pubout", "-out", public], env)
        for path in private, public:
            path.chmod(0o600)
        spki = base64.b64decode(public.read_bytes().splitlines()[1], validate=True)
        require(len(spki) == 44 and spki[:12] == PREFLIGHT_SPKI[:12], "unexpected generated public key")
    (root / "v74.enroll").write_bytes(base64.b64encode(spki))
    enrolled = ready("v74.attestation-ready", api, 30)
    pin = kit["sha"](spki)
    result["writerAdmission"] = enrolled
    expected = dict(origin=origin, spkiSHA256=pin, role="mixer_native_attestation_writer",
                    missingBuildHTTP=404, missingScopeHTTP=403, rows=0)
    require({key: enrolled[key] for key in expected} == expected,
            "stock writer, authority or fixed origin differed after enrollment")
    if preflight:
        return
    require(enrolled["browserStorageReady"] and enrolled["freshBrowserSession"],
            "v74 writer grants are incompatible with ordinary browser admission")

    settlement = root / "settlement.json"
    with settlement.open("x") as stream:
        json.dump(result, stream, separators=(",", ":"), sort_keys=True)
    result["stage"] = "v74-attestation-wrapper"
    (root / "v74.attaching").touch(exist_ok=False)
    result["attestationPending"] = True
    credentials = operator / "credentials"
    wrapper = command(root, kit, result, "attest-settled",
                      [sys.executable, "-B", auth["wrapper"], "--run-root", root,
                       "--settlement-sha256", file_sha(settlement), "--api-port", str(auth["port"]),
                       "--pg-port", str(result["ports"][0]), "--psql", pg / "psql",
                       "--session", credentials / "session", "--bearer", credentials / "bearer",
                       "--private-key", private, "--public-key", public, "--enrolled-spki-sha256", pin],
                      env, timeout=600)
    proof = kit["read"](wrapper)
    require(proof["base"] == BASE and proof["origin"] == origin and proof["signerKeySHA256"] == pin
            and proof["settlementSHA256"] == file_sha(settlement)
            and proof["workerOperationId"] == result["binding"]["operation_id"]
            and proof["recordId"] == result["binding"]["record_id"]
            and proof["subjects"] == result["settled"]["artifacts"]
            and proof["attachmentHTTP"] == [201, 200] and proof["persistedRows"] == 1
            and proof["byteExact"] is True and proof["journalUnchanged"] is True
            and proof["buildPOSTs"] == 0,
            "wrapper result does not prove exact stock attachment and duplicate readback")
    (root / "v74.attaching").unlink()
    result.update(attestation=proof, attestationPending=False)
