#!/usr/bin/env python3
"""Run a loopback FieldLog origin with the two newly linked Android cohorts."""
import argparse
import base64
import shutil
import signal
import tempfile
import zipfile
import contextlib
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import urllib.parse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VERIFIER = ROOT / "tools/verify-release"
CHANNEL = "beta"
COMMANDS = []


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def load(path):
    return json.loads(path.read_bytes())


def command(args, expected=0):
    COMMANDS.append([os.fspath(arg) for arg in args])
    result = subprocess.run(args, capture_output=True, timeout=15, check=False)
    check(result.returncode == expected, f"{args[0]} exit={result.returncode}: {result.stdout!r} {result.stderr!r}")
    return result.stdout


def inspect(identity):
    return json.loads(command([VERIFIER, "identity", identity]))


def verify(identity, roots, manifest, payload, assignment, installation, high_water, now,
           error=None, channel=CHANNEL):
    result = json.loads(command([VERIFIER, "verify", identity, roots, manifest, payload,
                                 assignment, channel, installation, str(high_water), str(now)],
                                expected=int(error is not None)))
    if error is not None:
        check(result == {"error": error}, f"unexpected Swift verifier refusal: {result}")
        return error
    return result


def connection_closed(port):
    with socket.socket() as candidate:
        candidate.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        candidate.bind(("127.0.0.1", port))


class Origin:
    def __init__(self, work, config, port, token, evidence):
        self.work, self.config, self.port, self.token, self.evidence = work, config, port, token, evidence
        self.hold = work.parent / (work.name + ".service-custody.json")

    def request(self, method, path, expected, name, body=None, private=False, error=None):
        check(path.startswith("/") and not path.startswith("//"), "request escaped loopback origin")
        headers = {}
        if private:
            headers["Authorization"] = "Bearer " + self.token
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["Idempotency-Key"] = name
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, body=encoded(body) if body is not None else None, headers=headers)
            response = connection.getresponse()
            wire = response.read(1024 * 1024 + 1)
            row = {"method": method, "path": path, "status": response.status,
                   "requestID": response.getheader("X-Request-ID")}
            if error:
                err = json.loads(wire)["error"]
                row["error"] = err["code"]
            self.evidence["http"][name] = row
            check(response.status == expected and row["requestID"], f"{name}: unexpected HTTP {response.status}, {wire[:250]}")
            check(len(wire) <= 1024 * 1024, "loopback response exceeded harness ceiling")
            check(not error or row["error"] == error, f"{name}: unexpected HTTP error {row}")
            check(expected != 204 or not wire, f"{name}: 204 carried a body")
            return wire
        finally:
            connection.close()

    @contextlib.contextmanager
    def start(self, label):
        row = {"port": self.port}
        self.evidence["serviceProcesses"][label] = row
        log_name = self.work / f"origin-{label}.log"
        with log_name.open("xb") as log, self.hold.open("x") as marker:
            json.dump({"work": str(self.work), "stage": label, "port": self.port}, marker)
            marker.flush()
            child = subprocess.Popen([ROOT / "tools/mixer-service"], cwd=self.work,
                                     env={"MIXER_SERVICE_CONFIG": str(self.config), "TMPDIR": str(self.work)},
                                     stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            try:
                row.update(pid=child.pid, pgid=child.pid)
                marker.seek(0)
                json.dump({"work": str(self.work), "stage": label, **row}, marker)
                marker.truncate()
                marker.flush()
                deadline = time.monotonic() + 8
                while True:
                    check(child.poll() is None, f"{label}: origin exited during startup")
                    try:
                        with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                            break
                    except OSError:
                        check(time.monotonic() < deadline, "listener startup deadline")
                        time.sleep(0.03)
                yield
            finally:
                if child.poll() is None:
                    child.terminate()
                row["exit"] = child.wait(timeout=12)
                row["directChildReaped"] = True
                try:
                    os.killpg(child.pid, 0)
                except ProcessLookupError:
                    row["ownedGroupAbsent"] = True
                else:
                    raise RuntimeError(f"owned group still present after {label} stop")
                connection_closed(self.port)
                row["listenerPortReusable"] = True
                row["logSHA256"] = file_digest(log_name)
                self.hold.unlink()
                check(row["exit"] == 0, f"origin exit failure {row}")



def put_json(path, value):
    path.write_bytes(encoded(value))
    return path


def require_digest(path, expected):
    observed = file_digest(path)
    check(observed == expected, f"input digest differs for {path}")
    return observed


def admit(work):
    packaging = load(ROOT / "package-result.json")
    check(packaging["status"] == "apk-pair-verified", "APK qualification is incomplete")
    signed = load(ROOT / "signed-pair.json")
    admitted, releases = {}, {}
    for label in ("old", "new"):
        case, directory = packaging["cases"][label], ROOT / label
        apk = directory / "FieldLog.apk"
        require_digest(apk, case["apk"]["sha256"])
        installed = directory / "Installed"
        pins = load(directory / "installed.sha256.json")
        check(set(pins) == {"bridge.json", "identity.json", "roots.json", "storage.json",
                           "storage-grant.json", "port.txt"}, "unexpected installed pin set")
        with zipfile.ZipFile(apk) as image:
            for name, expected in pins.items():
                packaged = image.read("assets/ChecklistRelease/" + name)
                check(digest(packaged) == expected == file_digest(installed / name), f"{label} {name} pin differs")
                (work / f"{label}-{name}").write_bytes(packaged)
        identity, roots = (work / f"{label}-{name}.json" for name in ("identity", "roots"))
        host = inspect(identity)
        check(host == load(directory / "host.json") == case["host"], "embedded Android identity differs")
        check(file_digest(roots) == load(identity)["build"]["trust_roots_sha256"], "baked trust mismatch")
        check(int((work / f"{label}-port.txt").read_text()) == packaging["port"], "baked origin port differs")
        issued = signed[label]
        check(issued["manifest"] == load(directory / "manifest.json") and
              issued["assignment"] == load(directory / "assignment.json") and
              issued["digest"] == case["artifactSHA256"], "signed packet differs")
        guest = directory / "guest.wasm"
        require_digest(guest, case["guestSHA256"])
        result = verify(identity, roots, directory / "manifest.json", guest, directory / "assignment.json",
                        signed["installation"], 0, int(time.time()))
        check(result["artifactSHA256"] == issued["digest"] and result["cohortBucket"] == signed["bucket"],
              "paired signed manifest and assignment failed packaged trust")
        admitted[label] = (identity, roots, host)
        releases[label] = issued | {"artifact": {"signed_manifest": issued["manifest"],
                                                  "payload": base64.b64encode(guest.read_bytes()).decode()}}
    check(file_digest(admitted["old"][1]) == file_digest(admitted["new"][1]), "pair trust roots differ")
    return admitted, releases, signed, packaging["port"]


def exercise(work, evidence, serve=None, seconds=0):
    now = int(time.time())
    admitted, releases, signed, self_port = admit(work)
    installation, bucket = signed["installation"], signed["bucket"]
    evidence["installation"] = {"id": installation, "bucket": bucket}
    hosts = {label: entry[2] for label, entry in admitted.items()}
    scope = hosts["old"]["scope"]
    org, project = scope["organization"], scope["project"]
    port, token = self_port, secrets.token_hex(32)
    storage = work / "store"
    config = put_json(work / "service.json", {
        "developer_mode": True, "listen": f"127.0.0.1:{port}", "data_directory": str(storage),
        "tokens": [{"sha256": digest(token.encode()), "role": "publisher",
                    "organization": org, "project": project, "actor": "android-cohort-replay"}],
        "roots": load(admitted["old"][1]), "hosts": list(hosts.values()),
    })
    origin = Origin(work, config, port, token, evidence)
    base = f"/v3/orgs/{org}/projects/{project}"
    snapshot = storage / "release.json"

    def query(label, tag, status=200, **overrides):
        params = scope | {"runtime": hosts[label]["runtime"], "channel": CHANNEL,
                          "installation": installation} | overrides
        return origin.request("GET", "/v3/updates?" + urllib.parse.urlencode(params), status, tag)

    def publish(signed_assignment, tag, status=200, error=None):
        return origin.request("POST", base + "/channels/beta/publish", status, tag,
                              {"signed_assignment": signed_assignment}, True, error)

    def artifact_url(release):
        return f"/v3/artifacts/{release['digest']}?organization={org}&project={project}"

    def expose(label):
        release = releases[label]
        artifact = release["digest"]
        origin.request("PUT", base + "/artifacts/" + artifact, 201, f"upload-{label}", release["artifact"], True)
        origin.request("GET", artifact_url(release), 404, f"staged-is-private-{label}", error="not_found")
        validation = json.loads(origin.request("POST", base + "/releases/validate", 200, f"validate-{label}",
                                              {"artifact_sha256": artifact}, True))
        check(validation["protocol_valid"] and validation["artifact_sha256"] == artifact,
              "origin validation returned an unexpected digest")
        published = json.loads(publish(release["assignment"], f"publish-{label}"))
        for key in ("sequence", "rollout_basis_points", "artifact_sha256"):
            check(published[key] == release["assignment"]["assignment"][key], f"wrong published {label} {key}")

    def fetch(label, phase):
        release = releases[label]
        tag = f"{phase}-{label}"
        wire = query(label, f"offer-{tag}")
        expected = {"signed_assignment": release["assignment"], "artifact_url": artifact_url(release)}
        check(json.loads(wire) == expected, f"{tag}: wrong offer")
        artifact_wire = origin.request("GET", expected["artifact_url"], 200, f"artifact-{tag}")
        artifact = json.loads(artifact_wire)
        check(artifact == release["artifact"], f"{tag}: wrong artifact")
        payload = work / f"{tag}.wasm"
        payload.write_bytes(base64.b64decode(artifact["payload"], validate=True))
        files = (put_json(work / f"{tag}.manifest.json", artifact["signed_manifest"]), payload,
                 put_json(work / f"{tag}.assignment.json", expected["signed_assignment"]))
        evidence["wire"][tag] = {"offerSHA256": digest(wire), "artifactSHA256": digest(artifact_wire),
                                  "payloadSHA256": file_digest(payload)}
        return files

    def verify_case(label, files, tag, cursor=0, error=None):
        identity, roots, *_ = admitted[label]
        result = verify(identity, roots, *files,
                        installation, cursor, now, error)
        if error is None:
            assignment = releases[label]["assignment"]["assignment"]
            check(result == {"artifactSHA256": releases[label]["digest"], "sequence": assignment["sequence"],
                             "releaseID": assignment["release_id"], "cohortBucket": bucket}, f"wrong verifier result {tag}")
        evidence["swiftVerifier"][tag] = {"cursor": cursor, "result": result}

    def refusals(phase, old_files, new_files):
        for own, other, own_files, other_files in (
            ("old", "new", old_files, new_files), ("new", "old", new_files, old_files),
        ):
            verify_case(own, other_files, f"{phase}-{other}-artifact-under-{own}", error="v3.manifest.compatibility")
            verify_case(own, (*own_files[:2], other_files[2]), f"{phase}-{other}-assignment-under-{own}",
                        error="v3.assignment.binding")
        query("old", f"{phase}-unknown-fingerprint", 204, runtime=digest(b"unregistered-android-runtime"))
        query("new", f"{phase}-other-app", 204, app="other-fieldlog")
        query("new", f"{phase}-other-platform", 204, platform="ios")
        publish(signed["new_into_old"], f"{phase}-new-artifact-for-old-channel", 422, "artifact_invalid")
        publish(signed["old_into_new"], f"{phase}-old-artifact-for-new-channel", 422, "artifact_invalid")
        origin.request("PUT", base + "/artifacts/" + releases["old"]["digest"], 422, f"{phase}-immutable-transplant",
                       releases["new"]["artifact"], True, "digest_mismatch")

    def audit(tag):
        return json.loads(origin.request("GET", base + "/audit?limit=100", 200, tag, private=True))["events"]

    if serve:
        try:
            with origin.start("native-handoff"):
                expose("old")
                if serve == "both":
                    expose("new")
                print(f"Serving FieldLog {serve} on 127.0.0.1:{port}", flush=True)
                deadline = time.monotonic() + seconds
                while (remaining := deadline - time.monotonic()) > 0:
                    time.sleep(min(0.75, remaining))
        except KeyboardInterrupt:
            pass
        return

    with origin.start("initial"):
        query("old", "empty-old", 204)
        query("new", "empty-new", 204)
        expose("old")
        old_files = fetch("old", "old-only")
        verify_case("old", old_files, "old-before-new-publish")
        query("new", "new-during-old-only", 204)
        expose("new")
        stable = snapshot.read_bytes()
        old_files = fetch("old", "before-restart")
        new_files = fetch("new", "before-restart")
        check(evidence["wire"]["old-only-old"] == evidence["wire"]["before-restart-old"],
              "publishing the new runtime changed the old wire")
        verify_case("old", old_files, "old-before-restart")
        verify_case("new", new_files, "new-before-restart")
        verify_case("new", new_files, "new-using-old-high-water", 7, "v3.assignment.replay")
        verify_case("old", old_files, "old-with-baked-root")
        verify_case("new", new_files, "new-with-baked-root")
        refusals("before-restart", old_files, new_files)
        baseline_audit = audit("audit-before-restart")
        check(snapshot.read_bytes() == stable, "negative requests changed the durable snapshot")
        database = json.loads(stable)
        expected_artifacts, expected_channels = {}, {}
        for label, release in releases.items():
            expected_artifacts[f"{org}/{project}/{release['digest']}"] = {
                "protocol": 3, "artifact_v3": release["artifact"], "validated": True, "published": True,
            }
            key = f"{org}/{project}/{scope['app']}/{scope['environment']}/{scope['platform']}/{hosts[label]['runtime']}/beta"
            expected_channels[key] = {"protocol": 3, "signed_assignment_v3": release["assignment"]}
        check(database["schema"] == 3 and database["artifacts"] == expected_artifacts and
              database["channels"] == expected_channels, "durable catalog differs from two validated signed heads")
        changes = [event["channel_change"] for event in baseline_audit if "channel_change" in event]
        check(len(baseline_audit) == 6 and len(changes) == 2, "unexpected number of audited changes")
        check([change["runtime"] for change in changes] == [hosts[label]["runtime"] for label in releases],
              "audit did not record one new head per runtime")
        evidence["durable"] = {"sha256": digest(stable), "bytes": len(stable), "artifactKeys": list(expected_artifacts),
                               "channelKeys": list(expected_channels), "auditEventCount": len(baseline_audit),
                               "channelChanges": changes, "auditHeadSHA256": baseline_audit[-1]["hash"],
                               "byteIdenticalAfterNegativeRequests": True}
    check(snapshot.read_bytes() == stable, "origin shutdown rewrote durable state")

    with origin.start("restarted"):
        check(snapshot.read_bytes() == stable, "opening the store changed the snapshot")
        restarted_old = fetch("old", "after-restart")
        restarted_new = fetch("new", "after-restart")
        for label, files in (("old", restarted_old), ("new", restarted_new)):
            check(evidence["wire"][f"after-restart-{label}"] == evidence["wire"][f"before-restart-{label}"],
                  f"origin restart changed {label} wire")
            verify_case(label, files, f"{label}-after-restart-fresh-cursor")
            sequence = releases[label]["assignment"]["assignment"]["sequence"]
            verify_case(label, files, f"{label}-after-restart-advanced-cursor", sequence, "v3.assignment.replay")
        refusals("after-restart", restarted_old, restarted_new)
        check(audit("audit-after-restart") == baseline_audit, "audit differs after restart and refusal tests")
        check(snapshot.read_bytes() == stable, "negative requests after restart changed durable state")
    check(snapshot.read_bytes() == stable, "final durable state differs")
    for label, files in (("old", old_files), ("new", new_files)):
        verify_case(label, files, f"{label}-cached-reverification-with-origin-stopped")
    evidence["durable"]["byteIdenticalAcrossRestartAndFinalStop"] = True
    evidence["assignments"] = {label: release["assignment"]["assignment"] for label, release in releases.items()}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verify", "serve"))
    parser.add_argument("--cohorts", choices=("old", "both"), default="both")
    parser.add_argument("--seconds", type=int, choices=range(10, 1801), default=900, metavar="10..1800")
    parser.add_argument("--work-parent", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    check(args.work_parent.is_dir(), "work parent must be a caller-owned directory")
    capacity = shutil.disk_usage(args.work_parent).free
    check(capacity >= 64 * 1024 * 1024, f"loopback file-store budget requires 64 MiB free, observed {capacity}")
    evidence = {"status": "failed", "http": {}, "wire": {}, "swiftVerifier": {},
                "serviceProcesses": {}, "freeBytesBeforeStore": capacity, "storeBudgetBytes": 64 * 1024 * 1024,
                "mode": args.mode, "runnerSHA256": file_digest(Path(__file__)),
                "serviceSHA256": file_digest(ROOT / "tools/mixer-service"),
                "verifierSHA256": file_digest(VERIFIER)}
    work = Path(tempfile.mkdtemp(prefix="fieldlog-cohort-origin-", dir=args.work_parent))

    def stop_request(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop_request)
    try:
        exercise(work, evidence, args.cohorts if args.mode == "serve" else None, args.seconds)
        evidence["status"] = "passed"
    except BaseException as error:
        evidence["failure"] = str(error)
        raise
    finally:
        evidence["childCommands"] = COMMANDS
        evidence["workRemoved"] = (
            not (work.parent / (work.name + ".service-custody.json")).exists()
            and all(row.get("ownedGroupAbsent") for row in evidence["serviceProcesses"].values())
        )
        evidence["ownedBytesBeforeCleanup"] = sum(path.stat().st_size for path in work.rglob("*") if path.is_file()) if evidence["workRemoved"] else None
        if evidence["workRemoved"]:
            shutil.rmtree(work)
        else:
            evidence["retainedWork"] = str(work)
        with args.result.open("x") as result:
            json.dump(evidence, result, indent=2)
            result.write("\n")


if __name__ == "__main__":
    main()
