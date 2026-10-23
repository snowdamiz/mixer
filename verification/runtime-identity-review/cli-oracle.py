#!/usr/bin/env python3
"""Original stdlib oracle/probes; no product encoder/generator is imported."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import os
import socket
import subprocess
import tempfile

def encode_head(kind, n):
    if not 0 <= n < 1 << 64: raise ValueError("uint64")
    if n < 24: return bytes([kind * 32 + n])
    width = next(size for size in (1, 2, 4, 8) if n < 1 << (size * 8))
    return bytes([kind * 32 + {1: 24, 2: 25, 4: 26, 8: 27}[width]]) + n.to_bytes(width, "big")

def encode(value):
    if type(value) is int: return encode_head(0, value)
    if type(value) is bool: return bytes([245 if value else 244])
    if type(value) is str:
        text = value.encode("utf-8")
        return encode_head(3, len(text)) + text
    if type(value) is list: return encode_head(4, len(value)) + b"".join(encode(item) for item in value)
    if type(value) is dict:
        records = sorted((encode(key), encode(item)) for key, item in value.items())
        return encode_head(5, len(records)) + b"".join(key + item for key, item in records)
    raise ValueError("outside restricted identity types")

parser = argparse.ArgumentParser()
parser.add_argument("--tool", required=True)
parser.add_argument("--vectors", required=True)
parser.add_argument("--revision", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
fixtures = json.loads(Path(args.vectors).read_text())
cases = [copy.deepcopy(item["descriptor"]) for item in fixtures]
for state in (0, 23, 24, 255, 256, 65535, 65536, 4294967295, 4294967296, 18446744073709551615):
    case = copy.deepcopy(cases[0]); case["execution"]["state_schema"] = state; cases.append(case)
for name in ("é", "e\u0301", "start.日志.😀", "\u0085.start", "é" * 2048):
    case = copy.deepcopy(cases[0]); case["execution"]["startup_export"] = name; cases.append(case)
for field in cases[0]["build"]:
    if not field.endswith("_sha256"): continue
    case = copy.deepcopy(cases[0]); case["build"][field] = hashlib.sha256(("independent review " + field).encode()).hexdigest(); cases.append(case)
case = copy.deepcopy(cases[0]); case["dependencies"] = []; cases.append(case)
records = []
with tempfile.TemporaryDirectory(prefix="mixer-identity-cli-review-") as temporary:
    root = Path(temporary)

    def execute(name, path, expected=None):
        command = [args.tool, "inspect", str(path)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        record = dict(name=name, command=command, exitCode=result.returncode,
                      stdoutSHA256=hashlib.sha256(result.stdout).hexdigest(), stderrSHA256=hashlib.sha256(result.stderr).hexdigest())
        if expected is None: record["passed"] = result.returncode != 0
        else:
            encoded = encode(expected)
            fingerprint = hashlib.sha256(b"mixer.runtime.identity.v1\0" + encoded).hexdigest()
            actual = json.loads(result.stdout) if result.returncode == 0 else {}
            app, policy = expected["application"], expected["execution"]
            host = dict(scope={key: app[key] for key in ("organization", "project", "app", "environment")},
                runtime=fingerprint, protocol=policy["protocol"], guest_abi=expected["engine"]["guest_abi"], ui_schema=expected["engine"]["ui_schema"],
                capability_hashes={entry["id"]: entry["schema_sha256"] for entry in expected["capabilities"]},
                state_version=policy["state_schema"], max_payload_bytes=policy["max_payload_bytes"],
                limits=dict(memory_bytes=policy["memory_bytes"], fuel=policy["fuel"], startup_milliseconds=policy["startup_ms"]))
            host["scope"]["platform"] = expected["platform"]["os"]
            record.update(expectedFingerprint=fingerprint, expectedCBORBytes=len(encoded),
                passed=result.returncode == 0 and actual.get("schema") == 1 and actual.get("fingerprint") == fingerprint
                and actual.get("canonicalCBORBytes") == len(encoded) and actual.get("installedRuntime") == host and actual.get("buildAttested") is False)
        records.append(record)

    for index, case in enumerate(cases):
        path = root / ("vector-" + str(index) + ".json")
        path.write_text(json.dumps(case, ensure_ascii=index % 2 == 0, sort_keys=index % 3 == 0, indent=2 if index % 2 else None))
        execute("valid-oracle-" + str(index), path, case)
    good = json.dumps(cases[0], separators=(",", ":")).encode()
    for name, data in [("empty", b""), ("over-byte-limit", b" " * 131073), ("invalid-utf8", b"\xff"),
                       ("duplicate-escaped-root", b'{"\\u0073chema":1,' + good[1:]),
                       ("numeric-exponent", good.replace(b'"state_schema":1', b'"state_schema":1e0'))]:
        path = root / (name + ".json"); path.write_bytes(data); execute(name, path)
    exact = root / "exact-limit.json"; exact.write_bytes(good + b" " * (131072 - len(good))); execute("exact-byte-limit", exact, cases[0])
    directory = root / "directory"; directory.mkdir(); execute("directory", directory)
    fifo = root / "fifo"; os.mkfifo(fifo, 0o600); execute("fifo", fifo)
    symlink = root / "symlink"; symlink.symlink_to(exact); execute("final-symlink", symlink)
    with socket.socket(socket.AF_UNIX) as endpoint:
        path = root / "socket"; endpoint.bind(str(path)); execute("unix-socket", path)
record = dict(revision=args.revision, scope="independent restricted RFC8949 deterministic CBOR/SHA256 oracle and bounded public CLI input probes; no attestation or activation authority",
              specification="https://www.rfc-editor.org/rfc/rfc8949.html#section-4.2.1", toolSHA256=hashlib.sha256(Path(args.tool).read_bytes()).hexdigest(),
              validOracleCases=len(cases) + 1, invalidFileOrWireCases=9, commands=records, passed=all(item["passed"] for item in records))
Path(args.output).write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({key: value for key, value in record.items() if key != "commands"}, indent=2))
raise SystemExit(0 if record["passed"] else 1)
