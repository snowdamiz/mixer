#!/usr/bin/env python3
"""Test the produced development variants against the owning local v3 service."""
import argparse
import base64
from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request

from fieldlog_provenance import encoded, file_hash, group_absent, load, require, save, sha, stop_group

PROJECT = "/v3/orgs/mixer-local/projects/fieldlog"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_):
        return None


class Origin:
    def __init__(self, location, executable, hosts, roots):
        self.directory = location
        location.mkdir(mode=0o700)
        self.executable = executable
        self.token = secrets.token_urlsafe(32)
        self.trace = []
        self.lifecycle = []
        self.client = build_opener(ProxyHandler({}), NoRedirect())
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        save(location / "config.json", {
            "developer_mode": True, "listen": f"127.0.0.1:{self.port}", "storage_backend": "local",
            "data_directory": str(location / "store"), "hosts": hosts, "roots": roots,
            "tokens": [{"sha256": sha(self.token.encode()), "actor": "fieldlog-admission-local",
                        "organization": "mixer-local", "project": "fieldlog", "role": "publisher"}],
        })

    def request(self, method, endpoint, expect, body=None, code=None):
        headers = {}
        if body is not None:
            headers = {"Content-Type": "application/json", "Authorization": "Bearer " + self.token,
                       "Idempotency-Key": f"fieldlog-control-{len(self.trace)}"}
        req = Request(f"http://127.0.0.1:{self.port}" + endpoint, method=method, headers=headers,
                      data=encoded(body) if body is not None else None)
        try:
            resp = self.client.open(req, timeout=3)
        except HTTPError as error:
            resp = error
        with resp:
            data = resp.read(65_537)
            record = {"method": method, "endpoint": endpoint, "status": resp.status, "sha256": sha(data)}
            self.trace.append(record)
            require(len(data) <= 65_536 and resp.status == expect,
                    f"Unexpected service reply {record}: {data[:1200]!r}")
            if code:
                observed = json.loads(data)["error"]["code"]
                require(observed == code, f"Expected {code}, got {observed}")
                record["code"] = observed
            return data

    @contextmanager
    def run(self):
        with (self.directory / "service.log").open("ab") as log:
            process = subprocess.Popen([self.executable], env={"MIXER_SERVICE_CONFIG": str(self.directory / "config.json")},
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                deadline = time.monotonic() + 6
                while True:
                    require(time.monotonic() < deadline and process.poll() is None, "Origin did not become ready")
                    try:
                        self.request("GET", "/healthz", 200)
                        break
                    except OSError:
                        time.sleep(0.05)
                yield
            finally:
                if process.poll() is None:
                    process.terminate()
                forced = False
                try:
                    process.wait(timeout=12)
                    gone = group_absent(process.pid, 1)
                    if not gone:
                        forced = True
                        gone = stop_group(process)
                except subprocess.TimeoutExpired:
                    forced = True
                    gone = stop_group(process)
                with socket.socket() as probe:
                    probe.settimeout(1)
                    closed = probe.connect_ex(("127.0.0.1", self.port)) == errno.ECONNREFUSED
                self.lifecycle.append({"pid": process.pid, "exit": process.returncode, "forcedCleanup": forced,
                                       "groupAbsent": gone, "listenerClosed": closed})
                if not (gone and closed):
                    save(self.directory / "HOLD.json", self.lifecycle[-1])
                save(self.directory / "lifecycle.json", self.lifecycle)
                require(gone and closed, f"Unresolved origin custody for PGID {process.pid}. Preserve {self.directory}")
                require(not forced and process.returncode == 0, f"Origin did not exit cleanly: {self.lifecycle[-1]}")

    def publish(self, assignment, expect=200, code=None):
        self.request("POST", PROJECT + "/channels/beta/publish", expect, {"signed_assignment": assignment}, code)

    def upload(self, target, variant, expect=201, code=None):
        assignment = load(target / f"{variant}.assignment.json")["assignment"]
        artifact = assignment["artifact_sha256"]
        self.request("PUT", PROJECT + "/artifacts/" + artifact, expect,
                     {"signed_manifest": load(target / f"{variant}.manifest.json"),
                      "payload": base64.b64encode((target / f"{variant}.wasm").read_bytes()).decode()}, code)
        if expect == 201:
            self.request("POST", PROJECT + "/releases/validate", 200, {"artifact_sha256": artifact})

    def offer(self, host, expect=200):
        installation = f'fieldlog-{host["scope"]["platform"]}-local-1'
        query = urlencode(host["scope"] | {"runtime": host["runtime"], "channel": "beta", "installation": installation})
        return self.request("GET", "/v3/updates?" + query, expect)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("tool", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    run = args.run.resolve()
    results = load(run / "build-result.json")
    identity = results["hosts"]
    changed = results["proposedHosts"]["android"]
    roots = [root for target in identity for root in load(run / f"compatible/{target}/installed/roots.json")]
    before = {}
    old = Origin(args.output.resolve(), args.tool.resolve(), list(identity.values()), roots)
    neg = run / "permission-change/android"
    with old.run():
        for platform, host in identity.items():
            actual = run / "compatible" / platform
            for variant in ("baseline", "candidate"):
                old.upload(actual, variant)
                old.publish(load(actual / f"{variant}.assignment.json"))
            response = old.offer(host)
            envelope = json.loads(response)["signed_assignment"]
            require(envelope == load(actual / "candidate.assignment.json") and envelope["assignment"]["sequence"] == 2,
                    "Origin returned a different signed safe offer")
            wire = json.loads(old.request("GET", json.loads(response)["artifact_url"], 200))
            require(load(actual / "candidate.manifest.json") == wire["signed_manifest"] and
                    (actual / "candidate.wasm").read_bytes() == base64.b64decode(wire["payload"], validate=True),
                    "Origin served a different signed artifact")
            before[platform] = response
        old.upload(neg, "candidate", expect=422, code="unknown_runtime")
        old.publish(load(neg / "candidate.assignment.json"), expect=422, code="not_validated")
        require(old.offer(changed, expect=204) == b"", "Unexpected offer for unregistered runtime")
        require(all(old.offer(host) == before[p] for p, host in identity.items()), "Refusal changed original offer")
    # Reopen the same store and register the separately built runtime. This
    # distinguishes an actual cross-runtime refusal from an unknown-host refusal.
    config = load(old.directory / "config.json")
    config["hosts"].append(changed)
    save(old.directory / "config.json", config)
    with old.run():
        old.upload(neg, "candidate")
        old.publish(load(neg / "cross-runtime.assignment.json"), expect=422, code="artifact_invalid")
        require(all(old.offer(host) == before[p] for p, host in identity.items()), "Cross-runtime publication changed safe offer")
        old.offer(changed, expect=204)
    save(old.directory / "result.json", {
        "serviceSHA256": file_hash(args.tool), "requests": old.trace, "serviceLifecycle": old.lifecycle,
        "retained": {platform: {"sequence": 2, "signedOfferSHA256": sha(wire),
                                "artifactSHA256": json.loads(wire)["signed_assignment"]["assignment"]["artifact_sha256"]}
                     for platform, wire in before.items()},
    })


if __name__ == "__main__":
    main()
