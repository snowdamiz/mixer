#!/usr/bin/env python3
"""Run the exact signed-pair service control, or hand off one owned XCTest."""
import argparse
import base64
import errno
import hashlib
import json
import os
from pathlib import Path
import plistlib
import secrets
import socket
import subprocess
import time
import urllib.request
from uuid import UUID

from prepare import TEST, digest, tree_digest

PROJECT = "/v3/orgs/mixer-local/projects/fieldlog"

class Service:
    def __init__(self, build, work):
        self.build = build
        self.work = work
        self.fixtures = build / "signed"
        self.host = self.read("host.json")
        self.token = secrets.token_hex(32)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.origin = f"http://127.0.0.1:{self.port}"
        self.client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.responses = []

    def read(self, name):
        return json.loads((self.fixtures / name).read_text())

    def request(self, route, status, data=None, method="POST", mutation=None):
        url = self.origin + route
        headers = {}
        if data is not None:
            headers = {"Authorization": "Bearer " + self.token, "Content-Type": "application/json",
                       "Idempotency-Key": mutation}
            data = json.dumps(data, separators=(",", ":")).encode()
        request = urllib.request.Request(url, data=data, headers=headers, method=method if data else "GET")
        with self.client.open(request, timeout=3) as response:
            payload = response.read(65537)
            if response.geturl() != url or response.status != status or len(payload) > 65536:
                raise ValueError(f"Unexpected service response for {route}")
            self.responses.append({"method": request.method, "path": route, "status": response.status,
                                   "responseBytes": len(payload)})
            return json.loads(payload)

    def start(self):
        config = self.work / "service.json"
        config.write_text(json.dumps({
            "developer_mode": True,
            "listen": f"127.0.0.1:{self.port}",
            "data_directory": str(self.work / "release-store"),
            "tokens": [{"sha256": hashlib.sha256(self.token.encode()).hexdigest(), "role": "publisher",
                        "organization": "mixer-local", "project": "fieldlog", "actor": "fieldlog-ios-xctest"}],
            "hosts": [self.host],
            "roots": self.read("Installed/roots.json"),
        }, indent=2) + "\n")
        executable = self.build / "mixer-service"
        with (self.work / "service.log").open("xb") as log:
            self.process = subprocess.Popen([str(executable)], env={"MIXER_SERVICE_CONFIG": str(config)},
                                            stdout=log, stderr=subprocess.STDOUT)
        (self.work / "service-launch.json").write_text(json.dumps({
            "pid": self.process.pid, "executable": str(executable), "sha256": digest(executable),
            "config": str(config), "port": self.port,
        }, indent=2) + "\n")

    def ready(self):
        deadline = time.monotonic() + 8
        while self.process.poll() is None and time.monotonic() < deadline:
            try:
                report = self.request("/healthz", 200)
            except OSError:
                time.sleep(.05)
                continue
            if report["mode"] != "developer" or report["production_ready"] is not False:
                raise ValueError("Unexpected mode on the owned loopback port")
            return
        raise RuntimeError("Owned release service did not reach developer readiness")

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
        result = self.process.wait(timeout=15)
        with socket.socket() as sock:
            sock.settimeout(2)
            listener_closed = sock.connect_ex(("127.0.0.1", self.port)) == errno.ECONNREFUSED
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            port_reusable = False
            try:
                sock.bind(("127.0.0.1", self.port))
                port_reusable = True
            except OSError:
                pass
        (self.work / "service-result.json").write_text(json.dumps({
            "exit": result, "listenerClosed": listener_closed, "portReusable": port_reusable,
            "hostRequests": self.responses,
        }, indent=2) + "\n")
        if result != 0 or not listener_closed or not port_reusable:
            raise RuntimeError(f"Release service cleanup did not close cleanly: exit={result}, "
                               f"listenerClosed={listener_closed}, portReusable={port_reusable}")

    def upload(self):
        for index, variant in [(1, "baseline"), (2, "reviewed")]:
            assignment = self.read(f"sequence-{index}.assignment.json")["assignment"]
            artifact = assignment["artifact_sha256"]
            self.request(PROJECT + "/artifacts/" + artifact, 201, {
                "signed_manifest": self.read(variant + ".manifest.json"),
                "payload": base64.b64encode((self.fixtures / (variant + ".wasm")).read_bytes()).decode(),
            }, "PUT", "upload-" + variant)
            self.request(PROJECT + "/releases/validate", 200, {"artifact_sha256": artifact},
                         mutation="validate-" + variant)

    def check(self):
        for sequence, variant in enumerate(["baseline", "reviewed", "baseline"], 1):
            assignment = self.read(f"sequence-{sequence}.assignment.json")
            operation = "rollback" if sequence == 3 else "publish"
            self.request(PROJECT + "/channels/beta/" + operation, 200, {"signed_assignment": assignment},
                         mutation=f"{operation}-{sequence}")
            offer = self.request("/v3/updates?organization=mixer-local&project=fieldlog&app=fieldlog"
                                 f"&environment=development&platform=ios&runtime={self.host['runtime']}"
                                 "&channel=beta&installation=fieldlog-ios-local", 200)
            artifact = assignment["assignment"]["artifact_sha256"]
            expected = f"/v3/artifacts/{artifact}?organization=mixer-local&project=fieldlog"
            if offer["signed_assignment"] != assignment or offer["artifact_url"] != expected:
                raise ValueError("Service changed the selected signed assignment")
            record = self.request(expected, 200)
            if (record["signed_manifest"] != self.read(variant + ".manifest.json")
                or base64.b64decode(record["payload"], validate=True) != (self.fixtures / (variant + ".wasm")).read_bytes()):
                raise ValueError("Service changed the compact signed release")

def prepare_selection(service):
    receipt = json.loads((service.build / "build-receipt.json").read_text())
    original = Path(receipt["xctestrun"])
    if digest(original) != receipt["xctestrunSHA256"] or tree_digest(original.parent, [original.parent]) != receipt["productsTreeSHA256"]:
        raise ValueError("Build products changed since handoff")
    # Keep the original build artifacts immutable, including the xctestrun.
    run = plistlib.loads(original.read_bytes())
    target = run["FieldLogUITests"]
    target["OnlyTestIdentifiers"] = [TEST.split("/", 1)[1]]
    for key, value in run.items():
        if key != "__xctestrun_metadata__" and key != "FieldLogUITests" and isinstance(value, dict):
            raise ValueError(f"Unexpected XCTest target {key}")
    target["EnvironmentVariables"].update({
        "FIELDLOG_OTA_PORT": str(service.port), "FIELDLOG_OTA_PUBLISHER": service.token,
        **{f"FIELDLOG_OTA_ASSIGNMENT_{i}":
           base64.b64encode((service.fixtures / f"sequence-{i}.assignment.json").read_bytes()).decode()
           for i in range(1, 4)},
    })
    def expand(value):
        if isinstance(value, str):
            return value.replace("__TESTROOT__", str(original.parent))
        if isinstance(value, list):
            return [expand(item) for item in value]
        if isinstance(value, dict):
            return {key: expand(item) for key, item in value.items()}
        return value
    selection = service.work / "fieldlog-signed.xctestrun"
    with os.fdopen(os.open(selection, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as file:
        plistlib.dump(expand(run), file)
    selection_contents = plistlib.loads(selection.read_bytes())["FieldLogUITests"]
    for key in ("TestHostPath", "UITargetAppPath"):
        if not Path(selection_contents[key]).is_dir():
            raise ValueError(f"Missing selected test product: {key}")
    return selection

def execute_xctest(service, device):
    selection = prepare_selection(service)
    command = [
        "/usr/bin/xcodebuild", "test-without-building", "-xctestrun", str(selection), "-destination",
        f"platform=iOS Simulator,id={str(device).upper()}", "-destination-timeout", "45", "-only-testing:" + TEST,
        "-parallel-testing-enabled", "NO", "-maximum-concurrent-test-simulator-destinations", "1",
        "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", "330",
        "-maximum-test-execution-time-allowance", "330", "-resultBundlePath", str(service.work / "signed-ota.xcresult"),
    ]
    (service.work / "test-command.json").write_text(json.dumps(command, indent=2) + "\n")
    print("Running the single signed FieldLog UI test on the root-owned Simulator", flush=True)
    with (service.work / "xctest.log").open("xb") as log:
        code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
    (service.work / "test-result.json").write_text(json.dumps({"xcodebuildExit": code, "selector": TEST}, indent=2) + "\n")
    return code

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("output", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Host-only service protocol control")
    mode.add_argument("--device", type=UUID, help="Explicit root-owned, already booted Simulator UDID")
    args = parser.parse_args()
    build = args.build.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(mode=0o700)
    service = Service(build, output)
    service.start()
    try:
        service.ready()
        service.upload()
        if args.check:
            service.check()
            prepare_selection(service)
            return 0
        return execute_xctest(service, args.device)
    finally:
        service.stop()

if __name__ == "__main__":
    raise SystemExit(main())
