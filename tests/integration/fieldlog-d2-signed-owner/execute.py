import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlsplit

root = Path(sys.argv[1]).resolve()
source_commit = sys.argv[2]
binary = root / "swift-build/debug/fieldlog-d2-host"
archive = root / "rust-build/release/libmixer_vm.a"
fixtures = root / "work/mixer/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures"
material = root / "material"
negative = root / "wrong-grant"
workspace = root / "workspace"
material.mkdir()
workspace.mkdir()
installation = "778e1d11-85fe-4423-aa28-59a8fa71feda"


def digest(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def read(directory, name):
    return json.loads((directory / name).read_text())


def execute(*args):
    print("COMMAND", json.dumps([str(binary), *map(str, args)]), flush=True)
    subprocess.run([binary, *args], check=True)


class Origin(BaseHTTPRequestHandler):
    def do_GET(self):
        request = urlsplit(self.path)
        query = parse_qs(request.query, keep_blank_values=True)
        if request.path == "/v3/updates" and query == expected_query:
            self.reply(offer)
        elif request.path == artifact_path and query == artifact_query:
            self.reply(artifact)
        else:
            self.send_error(404)

    def reply(self, value):
        payload = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


with HTTPServer(("127.0.0.1", 0), Origin) as server:
    execute("sign", fixtures, root / "guests", material, digest(archive), digest(binary), source_commit)
    (material / "port.txt").write_text(f"{server.server_port}\n")
    identity = read(material, "identity.json")
    assert identity["build"]["link_inputs_sha256"] == digest(binary)
    assert identity["engine"]["artifact_sha256"] == digest(archive)
    assert len(identity["capabilities"]) == 1 and identity["capabilities"][0]["schema_sha256"] == (
        "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"
    )
    assert identity["build"]["trust_roots_sha256"] == digest(material / "roots.json")
    assignment = read(material, "sequence-1.assignment.json")
    artifact_id = assignment["assignment"]["artifact_sha256"]
    artifact_path = f"/v3/artifacts/{artifact_id}"
    scope = assignment["assignment"]["scope"]
    tenant = {field: scope[field] for field in ("organization", "project")}
    expected_query = {key: [value] for key, value in (
        scope | {"installation": installation, "runtime": assignment["assignment"]["runtime"], "channel": "beta"}
    ).items()}
    artifact_query = {key: [value] for key, value in tenant.items()}
    offer = {"signed_assignment": assignment, "artifact_url": artifact_path + "?" + urlencode(tenant)}
    manifest = read(material, "optional.manifest.json")
    assert manifest["manifest"]["source_commit"] == source_commit
    artifact = {"signed_manifest": manifest,
                "payload": base64.b64encode((material / "optional.wasm").read_bytes()).decode()}
    print("MATERIAL", json.dumps({"hostLinkSHA256": digest(binary), "hostVMSHA256": digest(archive),
          "runtime": assignment["assignment"]["runtime"], "artifact": artifact_id,
          "files": {path.name: digest(path) for path in sorted(material.iterdir())}},
          sort_keys=True), flush=True)
    shutil.copytree(material, negative)
    grant = read(negative, "storage-grant.json")
    grant["namespaces"] = ["wrong-draft-scope"]
    (negative / "storage-grant.json").write_text(json.dumps(grant))
    worker = Thread(target=server.serve_forever)
    worker.start()
    try:
        execute("online", workspace, material, negative)
    finally:
        server.shutdown()
        worker.join()
    address = server.server_address

with HTTPServer(address, Origin):
    print("Owned delivery listener closed and loopback port reusable", flush=True)

def repository_files():
    state = workspace / "FieldLog"
    paths = [state / "workspace.json", *sorted((state / "photos").iterdir())]
    return [(path.name, digest(path), path.stat().st_ino, path.stat().st_mtime_ns) for path in paths]


before = repository_files()
execute("cold", workspace, material, negative)
assert repository_files() == before
print("Cold process preserved exact workspace and JPEG bytes, inodes and mtimes", flush=True)
