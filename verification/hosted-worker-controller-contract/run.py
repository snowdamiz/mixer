#!/usr/bin/env python3
"""Freeze this contract packet. Uses stdlib + installed Node; no product imports.

Only official documentation HTTPS GETs and the explicit local input allowlist are
read. No dependency install, provider API, credential, Git, DB or device access.
This produces byte fixtures; it does not run a controller or qualify Jason.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DOC = ROOT / "docs/hosted-worker-controller-contract.md"
INPUTS = [
    "AGENTS.md", "mixer-product-plan.md",
    "docs/hosted-build-coordinator.md", "docs/hosted-worker-transport-contract.md",
    "docs/hosted-worker-transport-amendment-v2.md",
    "verification/hosted-worker-transport/candidate/context/builds/dispatch.ex",
    "verification/hosted-worker-transport/candidate/context/builds/lifecycle.ex",
    "verification/hosted-worker-transport/candidate/lib/mixer_hosted/builds/worker_wire.ex",
    "verification/hosted-worker-transport/candidate/test/mixer_hosted/builds/worker_wire_test.exs",
]
SOURCES = [
    ("direct-api", "https://developers.cloudflare.com/containers/api/durable-object-container/", "2026-09-30"),
    ("scheduling", "https://developers.cloudflare.com/containers/configuration/scheduling-policy/", "2026-10-12"),
    ("sqlite", "https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/", "2026-09-21"),
    ("alarms", "https://developers.cloudflare.com/durable-objects/api/alarms/", "2026-04-21"),
    ("lifecycle", "https://developers.cloudflare.com/containers/concepts/architecture/", "2026-09-30"),
    ("limits", "https://developers.cloudflare.com/containers/platform/limits/", "2026-10-21"),
    ("ga", "https://developers.cloudflare.com/changelog/post/2026-04-13-containers-sandbox-ga/", "2026-04-13"),
    ("response", "https://developers.cloudflare.com/workers/runtime-apis/response/", None),
    ("node-http", "https://developers.cloudflare.com/workers/runtime-apis/nodejs/http/", None),
]

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def digest(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(raw), "sha256": sha(raw)}

def freeze_source(item):
    key, url, updated = item
    started = now()
    request = Request(url, headers={"User-Agent": "Mixer-contract-source-verification/1", "Accept": "text/html"})
    with urlopen(request, timeout=20) as response:
        final = response.url
        if not final.startswith("https://developers.cloudflare.com/"):
            raise ValueError("official documentation redirected outside allowed origin")
        raw = response.read(2_097_153)
        if len(raw) > 2_097_152:
            raise ValueError("official documentation capture exceeds 2 MiB")
        status = response.status
        content_type = response.headers.get("Content-Type")
        last_modified = response.headers.get("Last-Modified")
    return {"id": key, "url": url, "final_url": final, "retrieved_at": started,
            "status": status, "content_type": content_type, "bytes": len(raw),
            "sha256": sha(raw), "last_modified_header": last_modified,
            "page_update_date_observed_via_web_tool": updated,
            "retention": "digest-only; full copyrighted documentation not reproduced"}

def fixture(name, fence="1", source="main", project="project-a"):
    scope = {"organization_id": "organization-a", "project_id": project,
             "application_id": "application-a", "build_id": "build-a", "platform": "android"}
    ref = {**scope, "attempt": 1, "fence": fence}
    spec = {**scope, "source": {"kind": "revision", "sha256": "a" * 64, "reference": source},
            "toolchain_lock_sha256": "b" * 64, "build_definition_sha256": "c" * 64}
    record = "00000000-0000-4000-8000-000000000001"
    encode = lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    original = ["mixer-build-operation-v1", record, scope["organization_id"], project,
                scope["application_id"], scope["build_id"], "android", 1, int(fence)]
    operation_json = encode(original)
    operation_id = sha(operation_json.encode())
    deadline = "2100000000000"
    binding = ["mixer-worker-binding-v1", operation_id, record,
               [scope["organization_id"], project, scope["application_id"], scope["build_id"], "android", 1, fence],
               [scope["organization_id"], project, scope["application_id"], scope["build_id"], "android",
                "revision", "a" * 64, source, "b" * 64, "c" * 64], deadline]
    binding_json = encode(binding)
    return {"name": name, "request": {
        "version": 1, "environment_id": "development", "pool_id": "native", "controller_id": "controller-1",
        "request_id": "00000000000000000000000000000001", "command": "query",
        "operation_id": operation_id, "immutable_sha256": sha(binding_json.encode()),
        "ref": ref, "spec": spec, "deadline_ms": deadline,
        "guard": {"record_id": record, "revision": "0", "owner_id": "owner-a", "epoch": "1",
                  "expires_at_us": "2000000000001000"}},
        "operation_json": operation_json, "binding_json": binding_json,
        "operation_utf8_bytes": len(operation_json.encode()), "binding_utf8_bytes": len(binding_json.encode())}

def command(argv, expected):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=20, check=False)
    entry = {"argv": argv, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
             "expected_exit_code": expected}
    if result.returncode != expected:
        raise RuntimeError(json.dumps(entry))
    return entry

def main():
    created = now()
    vectors = {"version": 1, "scope": "contract-fixtures-not-controller-or-Jason-qualification",
               "authoring": "independently authored Python stdlib; cross-checked with Node crypto/JSON; no product module loaded",
               "cases": [fixture("ascii"), fixture("beyond-safe-js-int", "9007199254740993"),
                         fixture("max-int64", "9223372036854775807"),
                         fixture("unicode", "9223372036854775807", "refs/heads/été-東京-😀", "café"),
                         fixture("escaping", "1", 'refs/heads/quote"-slash/-backslash\\-tab\t-newline\n')],
               "invalid_decimals": ["", "01", "+1", "-1", "0", "1.0", "1e3", " 1", "1 ", "9223372036854775808", 1, 1.0, None, True]}
    write_json(HERE / "vectors.json", vectors)
    with ThreadPoolExecutor(max_workers=3) as executor:
        sources = list(executor.map(freeze_source, SOURCES))
    write_json(HERE / "sources.json", {"version": 1, "retrieved_at": created,
        "web_tool_review": "Official pages opened/read with web tool before this bounded digest capture.", "sources": sources})
    commands = [command(["python3", "--version"], 0), command(["node", "--version"], 0),
                command(["node", str(HERE / "acceptance.mjs"), "--vectors"], 0),
                command(["node", str(HERE / "acceptance.mjs"), "--inventory"], 0),
                command(["node", str(HERE / "acceptance.mjs")], 77)]
    input_files = [digest(ROOT / p) for p in INPUTS]
    source_tree = sha(json.dumps(input_files, sort_keys=True, separators=(",", ":")).encode())
    artifacts = [digest(p) for p in [DOC, HERE / "README.md", HERE / "acceptance.mjs", HERE / "run.py",
                                    HERE / "verify_packet.py", HERE / "vectors.json", HERE / "sources.json"]]
    receipt = {"version": 1, "created_at": created, "completed_at": now(),
               "scope": "contract-selection-and-executable-test-inventory-only",
               "status": "packet-consistency-passed-controller-implementation-pending",
               "model_assignment": {"requested": "gpt-6.1-sol", "requested_reasoning": "xhigh", "context": "fresh bounded lane", "runtime_model_not_independently_observable": True},
               "root_technical_coordination": "Contract-only proposal approved before documentation/verification writes.",
               "platform": platform.platform(), "python": sys.version,
               "source_revision": "No Git inspected by this bounded lane; explicit allowed-input tree digest is authoritative here.",
               "source_tree_sha256": source_tree, "input_files": input_files, "artifact_files": artifacts,
               "commands": commands,
               "effects": {"read": "explicit input allowlist and official documentation only", "write": "assigned document and verification directory only",
                           "network": "official Cloudflare documentation HTTPS GETs only", "package_installs": 0,
                           "product_modules_loaded": 0, "provider_api_calls": 0, "native_runtime_runs": 0},
               "not_verified": ["controller-source", "Jason-client-interoperability", "actual-DO-SQLite-runtime", "ingress-header-framing-EOF",
                                "bounded-production-clock", "cloudflare-provider", "macos-provider", "isolation", "runner-result-authentication",
                                "Neon-R2", "restore", "zero-traffic-Oban", "signing", "store", "GA"]}
    write_json(HERE / "receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "source_tree_sha256": source_tree,
                      "fixture_cases": len(vectors["cases"]), "official_sources": len(sources),
                      "controller_acceptance_exit": 77}))

if __name__ == "__main__":
    main()
