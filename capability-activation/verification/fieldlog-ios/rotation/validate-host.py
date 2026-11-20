#!/usr/bin/env python3
"""Verify exact iOS fixture bytes with the pinned v3 verifier and release CLI."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
from urllib.parse import urlencode

PACKET = Path(__file__).resolve().parent
TOOLS = PACKET / "tools"
PHASES = ("baseline", "revoked-artifact", "revoked-assignment", "replacement")
HOST_INSTALLATION = "885d11ae-0000-4000-8000-000000000004"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def check(condition, message):
    if not condition:
        raise RuntimeError(message)

def request(port, path, status, method="GET"):
    client = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        client.request(method, path)
        response = client.getresponse()
        check(response.status == status, f"{method} {path}: HTTP {response.status} expected {status}")
        return response.read(65_537)
    finally:
        client.close()

def group_absent(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    return False

def run(argv, cwd, env):
    with tempfile.TemporaryFile(dir=cwd) as output:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            result = process.wait(timeout=25)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            raise
        check(group_absent(process.pid), f"Unresolved command custody for {process.pid}")
        output.seek(0)
        return result, json.loads(output.read(65_537))

def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("work", type=Path)
    args = parser.parse_args()
    fixture, work = args.fixture.resolve(strict=True), args.work.resolve()
    work.mkdir(mode=0o700)
    installed = fixture / "Installed"
    host = read(fixture / "host.json")
    root_file = installed / "roots.json"
    roots = read(root_file)
    identity = read(installed / "identity.json")
    signing = read(fixture / "signing.json")
    metadata = read(PACKET / "pins.json")
    check(identity["engine"]["artifact_sha256"] == metadata["engineArchiveSHA256"], "Wrong linked VM pin")
    check(identity["platform"] == {"os": "ios", "architecture": "arm64", "environment": "simulator",
          "minimum_os": "26.0", "target": "arm64-apple-ios26.0-simulator"}, "Wrong platform")
    check(host["runtime"] == signing["runtime"] and
          host["scope"] == {"organization": "mixer-local", "project": "fieldlog", "app": "fieldlog",
                            "environment": "development", "platform": "ios"}, "Wrong runtime scope")
    before = read(PACKET / "templates/Installed/identity.json")
    before["build"]["trust_roots_sha256"] = digest(root_file)
    check(identity == before, "Installed descriptor changed beyond the root hash")
    capability, = identity["capabilities"]
    check(capability["id"] == "storage.keyValue.v1" and
          host["capability_hashes"] == {capability["id"]: capability["schema_sha256"]}, "Wrong capability set")
    check(digest(installed / "storage.json") == capability["configuration_sha256"] and
          digest(installed / "storage-grant.json") == capability["grants_sha256"] and
          digest(installed / "bridge.json") == identity["build"]["resource_policy_sha256"],
          "Installed capability material hash mismatch")
    check(all((installed / name).read_bytes() == (PACKET / "templates/Installed" / name).read_bytes()
              for name in ("bridge.json", "storage.json", "storage-grant.json", "port.txt")),
          "Changed baseline bridge, storage or port material")
    check(len(roots) == 6 and len({root["public_key"] for root in roots}) == 6, "Roots must be distinct")
    for root in roots:
        parts = root["key_id"].split("-")
        check(parts[0] == "ios" and parts[1] in {"initial", "replacement", "revoked"} and
              parts[2] in {"artifact", "assignment"} and
              root["scope"] == host["scope"] and root["artifact"] == (parts[2] == "artifact") and
              root["assignment"] == (parts[2] == "assignment") and root["revoked"] == (parts[1] == "revoked") and
              root["not_after_unix"] == (signing["cutoff"] if parts[1] == "initial" else 0) and
              root["not_before_unix"] <= signing["created"], "Unexpected trust policy")
    key_pairs = {
        "baseline": ("initial", "initial"),
        "replacement": ("replacement", "replacement"),
        "revoked-artifact": ("revoked", "replacement"),
        "revoked-assignment": ("replacement", "revoked"),
        "expired-artifact": ("initial", "replacement"),
        "expired-assignment": ("replacement", "initial"),
        "wrong-runtime": ("replacement", "replacement"),
    }
    replacement_envelope = (fixture / "replacement/signed-manifest.json").read_bytes()
    for name, (artifact_key, assignment_key) in key_pairs.items():
        folder = fixture / name
        manifest = read(folder / "signed-manifest.json")["manifest"]
        assignment = read(folder / "assignment.json")["assignment"]
        check(manifest["key_id"] == f"ios-{artifact_key}-artifact" and
              assignment["key_id"] == f"ios-{assignment_key}-assignment", f"Wrong signing roles for {name}")
        if name in ("revoked-assignment", "expired-assignment"):
            check((folder / "signed-manifest.json").read_bytes() == replacement_envelope,
                  f"Assignment control changed artifact envelope for {name}")
        variant = "baseline" if name == "baseline" else "reviewed"
        inherited = read(PACKET / "templates" / f"{variant}.manifest.json")["manifest"]
        for key in ("key_id", "created_at_unix", "runtime"):
            inherited[key] = manifest[key]
        check(manifest == inherited and manifest["scope"] == host["scope"], f"Changed release contract for {name}")
        grant, = manifest["capability_grants"]["entries"]
        check(grant["permissions"] == ["storage.appPrivate"] and grant["namespaces"] == ["fieldlog-task-v1"] and
              grant["origins"] == grant["methods"] == [], f"Unexpected grant for {name}")
        payload = folder / "payload.wasm"
        pin = metadata["payloads"][variant]
        check(digest(payload) == manifest["payload_sha256"] == pin["sha256"] and
              payload.stat().st_size == manifest["expanded_bytes"] == manifest["compressed_bytes"] == pin["bytes"],
              f"Wrong payload for {name}")

    tampered = work / "tampered"
    tampered.mkdir()
    baseline = fixture / "baseline"
    (tampered / "signed-manifest.json").write_bytes((baseline / "signed-manifest.json").read_bytes())
    (tampered / "assignment.json").write_bytes((baseline / "assignment.json").read_bytes())
    payload = bytearray((baseline / "payload.wasm").read_bytes())
    payload[-1] ^= 1
    (tampered / "payload.wasm").write_bytes(payload)
    results = {"verifier": [], "cli": [], "service": {}}
    cases = [
        ("baseline", baseline, 0, signing["created"], None),
        ("replacement", fixture / "replacement", 1, signing["created"], None),
        ("revoked-artifact", fixture / "revoked-artifact", 1, signing["created"], "v3.signature.authority"),
        ("revoked-assignment", fixture / "revoked-assignment", 1, signing["created"], "v3.signature.authority"),
        ("wrong-runtime", fixture / "wrong-runtime", 1, signing["created"], "v3.manifest.compatibility"),
        ("tampered-payload", tampered, 0, signing["created"], "v3.payload.integrity"),
        ("artifact-before-cutoff", fixture / "expired-artifact", 1, signing["cutoff"] - 1, None),
        ("assignment-before-cutoff", fixture / "expired-assignment", 1, signing["cutoff"] - 1, None),
        ("expired-artifact", fixture / "expired-artifact", 1, signing["cutoff"], "v3.signature.authority"),
        ("expired-assignment", fixture / "expired-assignment", 1, signing["cutoff"], "v3.signature.authority"),
        ("replacement-after-cutoff", fixture / "replacement", 1, signing["cutoff"], None),
    ]
    for name, folder, last, now, denied in cases:
        argv = [str(TOOLS / "mixer-update"), "verify-v3", "--manifest", str(folder / "signed-manifest.json"),
                "--payload", str(folder / "payload.wasm"), "--host", str(fixture / "host.json"), "--roots", str(root_file),
                "--assignment", str(folder / "assignment.json"), "--channel", "beta",
                "--installation", HOST_INSTALLATION, "--last-sequence", str(last), "--now", str(now)]
        code, result = run(argv, work, {"TMPDIR": str(work)})
        results["verifier"].append({"case": name, "argv": argv, "exit": code, "result": result})
        if denied:
            check(code == 1 and result["code"] == denied, f"{name}: {result}")
        else:
            check(code == 0 and result["status"] == "protocol-verified" and result["assignmentSequence"] == last + 1
                  and result["artifactSHA256"] == signing["artifactDigests"][folder.name], f"{name}: {result}")

    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    token = secrets.token_urlsafe(32)
    data = work / "store"
    data.mkdir()
    config = work / "config.json"
    write(config, {
        "developer_mode": True, "listen": f"127.0.0.1:{port}", "storage_backend": "local",
        "data_directory": str(data), "hosts": [host], "roots": roots,
        "tokens": [{"sha256": hashlib.sha256(token.encode()).hexdigest(), "actor": "ios-rotation-fixture",
                   "organization": "mixer-local", "project": "fieldlog", "role": "publisher"}],
    })
    env = {"MIXER_RELEASE_ORIGIN": f"http://127.0.0.1:{port}", "MIXER_RELEASE_TOKEN": token, "TMPDIR": str(work)}
    service_argv = [str(TOOLS / "mixer-service")]
    service = None
    try:
        with (work / "service.log").open("wb") as log:
            service = subprocess.Popen(service_argv, cwd=work, env={"MIXER_SERVICE_CONFIG": str(config), "TMPDIR": str(work)},
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + 10
        while service.poll() is None:
            try:
                health = request(port, "/healthz", 200)
                break
            except ConnectionRefusedError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)
        else:
            raise RuntimeError("Local developer release service exited before readiness")
        check(json.loads(health) == {"mode": "developer", "production_ready": False}, "Unexpected service mode")
        query = urlencode({**host["scope"], "runtime": host["runtime"], "channel": "beta",
                           "installation": HOST_INSTALLATION})
        route = "/v3/updates?" + query
        baseline_wire = None
        for name, error, status in [
            ("baseline", None, None),
            ("tampered", "update.upload.rejected", "422 (artifact_invalid)"),
            ("wrong-runtime", "update.upload.rejected", "422 (unknown_runtime)"),
            ("revoked-artifact", "update.upload.rejected", "422 (artifact_invalid)"),
            ("revoked-assignment", "update.publish.rejected", "409 (assignment_rejected)"),
            ("replacement", None, None),
        ]:
            folder = tampered if name == "tampered" else fixture / name
            argv = [str(TOOLS / "mixer"), "update", "publish", str(folder), "--organization", "mixer-local",
                    "--project", "fieldlog", "--assignment", str(folder / "assignment.json"),
                    "--channel", "beta", "--rollout", "100"]
            code, result = run(argv, work, env)
            results["cli"].append({"case": name, "argv": argv, "exit": code, "result": result})
            wire = request(port, route, 200)
            if error:
                check(code == 1 and result["code"] == error and status in result["message"], f"{name}: {result}")
                check(wire == baseline_wire, f"Rejected {name} changed the offered assignment")
                continue
            sequence = 1 if name == "baseline" else 2
            check(code == 0 and result["status"] == "ok" and result["delivery"] == "local_only"
                  and result["sequence"] == sequence and result["artifact_sha256"] == signing["artifactDigests"][name],
                  f"{name}: {result}")
            if name == "baseline":
                baseline_wire = wire
            offer = json.loads(wire)
            check(offer["signed_assignment"] == read(folder / "assignment.json"), "Changed offered assignment")
            route_artifact = offer["artifact_url"]
            check(route_artifact == "/v3/artifacts/" + result["artifact_sha256"] + "?organization=mixer-local&project=fieldlog",
                  "Changed artifact route")
            import base64
            artifact = json.loads(request(port, route_artifact, 200))
            check(artifact["signed_manifest"] == read(folder / "signed-manifest.json") and
                  base64.b64decode(artifact["payload"], validate=True) == (folder / "payload.wasm").read_bytes(),
                  "Changed artifact wire")
    finally:
        if service is not None:
            if service.poll() is None:
                service.terminate()
            code = service.wait(timeout=12)
            closed = group_absent(service.pid)
            try:
                request(port, "/healthz", 200)
                refused = False
            except ConnectionRefusedError:
                refused = True
            results["service"] = dict(argv=service_argv, directChildReaped=True, exit=code, groupAbsent=closed,
                                      connectionRefused=refused, port=port)
            write(work / "results.json", results)
            check(code == 0 and closed and refused, f"Service cleanup incomplete for {service.pid}")
    results["status"] = "passed"
    results["runtime"] = host["runtime"]
    results["files"] = {str(path.relative_to(fixture)): digest(path) for path in sorted(fixture.rglob("*")) if path.is_file()}
    results["toolSHA256"] = {name: digest(TOOLS / name) for name in ("mixer", "mixer-update", "mixer-service")}
    write(work / "results.json", results)

if __name__ == "__main__":
    main()
