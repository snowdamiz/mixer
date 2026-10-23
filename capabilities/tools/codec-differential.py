#!/usr/bin/env python3
"""Executable owned Swift/Java wire differential. Neither side is a platform engine oracle."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
JAVA = "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/java"
binpath = subprocess.check_output(["swift", "build", "--package-path", "capabilities", "--show-bin-path"], cwd=ROOT, text=True).strip().splitlines()[-1]
SWIFT = str(Path(binpath) / "capability-probe")
hashes = json.loads((ROOT / "capabilities/schema/hashes.json").read_text())["capabilities"]
JCOMMAND = [JAVA, "-cp", "capabilities/.build/java", "mixer.capabilities.CapabilityProbe"]
identity = {"session": "01234567-89ab-4cde-8fab-0123456789ab", "slot": 0, "generation": 1}
encoded = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def call(capability, operation, args):
    return dict(schema=1, kind="call", identity=identity.copy(), capability=capability, schemaHash=hashes[capability], operation=operation, arguments=args)


valid = []
for size in [0, 1, 128, 65536]:
    data = base64.b64encode(bytes((i % 251 for i in range(size)))).decode()
    valid += [call("storage.keyValue.v1", "put", dict(namespace="entries", key="k", valueBase64=data))]
for operation in ["get", "delete"]:
    for size in [1, 128]:
        valid += [call("storage.keyValue.v1", operation, dict(namespace="n" * 64, key="k" * size))]
for method in ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]:
    valid += [call("network.http.v1", "request", dict(url="https://api.example.test:8443/a%20b?q=1", method=method,
        headers=[dict(name="x-one", value='quoted " \\ and slash /')], bodyBase64="AAEC/w==", timeoutMilliseconds=30000))]
valid += [call("network.http.v1", "request", dict(url="https://api.example.test/", method="GET",
    headers=[dict(name="x-%02d" % i, value="v" * 4096) for i in range(32)], bodyBase64=base64.b64encode(bytes(65536)).decode(), timeoutMilliseconds=1))]
for source in list(valid[:4]):
    value = copy.deepcopy(source); value["identity"]["generation"] = 4294967295; value["identity"]["slot"] = 65535; valid.append(value)
for source in list(valid[:4]) + [valid[8]]:
    value = copy.deepcopy(source); value["kind"] = "cancel"; del value["arguments"]; valid.append(value)

invalid = []
base = valid[8]
raw = encoded(base)
invalid += [raw.replace(b'"schema":1', b'"schema":1,"schema":1'),
            raw.replace(b'"schema":1', b'"schema":1,"\\u0073chema":1'),
            raw.replace(b'"schema":1', b'"schema":1.0'), raw.replace(b'"schema":1', b'"schema":1e0'),
            raw.replace(b'"schema":1', b'"schema":-1'), raw.replace(b'"schema":1', b'"schema":01'),
            raw.replace(b'"schema":1', b'"schema":4294967296'), raw.replace(b'"schema":1', b'"schema":true'),
            b'\xff', b'\xef\xbb\xbf' + raw, b' ' * 524289, b'[' * 9 + b'0' + b']' * 9,
            raw + b'{}', raw.replace(b'"GET"', b'"G\\ud800ET"'), raw.replace(b'"GET"', b'"G\\udc00ET"'),
            raw.replace(b'"GET"', b'"G\\uFF11ET"'), raw.replace(b'"GET"', b'"G\\ud83d\\ude00ET"'),
            raw.replace(b'"GET"', '"GE\u0301T"'.encode()), raw.replace(b'"GET"', '"GÉT"'.encode()),
            raw.replace(b'"schema":1', b'"schema":1,"other":false')]
for path, values in [("url", ["http://api.example.test/", "https://USER@api.example.test/", "https://API.example.test/", "https://api.example.test:443/", "https://api.example.test:0001/", "https://api.example.test:65536/", "https://api.example.test/#x", "https://api.example.test/\\evil", "https://api.example.test/%zz", "https://api.example.test/%aA", "https://[::1]/"]),
                     ("method", ["get", "OPTIONS", "GET\r\nInjected", "GÉT"]),
                     ("bodyBase64", ["AAE", "AA=", "Zh==", "===="]),
                     ("timeoutMilliseconds", [0, 30001, True])]:
    for value in values:
        bad = copy.deepcopy(base); bad["arguments"][path] = value; invalid.append(encoded(bad))
for size in [33]:
    bad = copy.deepcopy(base); bad["arguments"]["headers"] = [dict(name="x-%d" % i, value="v") for i in range(size)]; invalid.append(encoded(bad))
for headers in [[dict(name="host", value="evil")], [dict(name="cookie", value="secret")], [dict(name="X-A", value="x")], [dict(name="x-a", value="a"), dict(name="x-a", value="b")], [dict(name="x-a", value="a" * 4097)]]:
    bad = copy.deepcopy(base); bad["arguments"]["headers"] = headers; invalid.append(encoded(bad))
for key in ["../outside", ".", "a/b", "a\\b", "é", "e\u0301", "", "x" * 129]:
    bad = copy.deepcopy(valid[0]); bad["arguments"]["key"] = key; invalid.append(encoded(bad))
for key, value in [("capability", "java.lang.Runtime"), ("schemaHash", "0" * 64), ("operation", "invoke"), ("schema", 2), ("kind", "nativePointer")]:
    bad = copy.deepcopy(base); bad[key] = value; invalid.append(encoded(bad))
for field, value in [("generation", 0), ("generation", 4294967296), ("slot", 65536), ("session", identity["session"].upper())]:
    bad = copy.deepcopy(base); bad["identity"][field] = value; invalid.append(encoded(bad))
bad = copy.deepcopy(base); bad["arguments"]["bodyBase64"] = base64.b64encode(bytes(65537)).decode(); invalid.append(encoded(bad))


def execute(command, mode, data, expected=None):
    args = command + [mode] + ([str(expected)] if expected else [])
    return subprocess.run(args, cwd=ROOT, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


counts = dict(validInbound=0, invalidInbound=0, completionDirections=0, invalidCompletions=0)
work = ROOT / "capabilities/.build/differential"
work.mkdir(parents=True, exist_ok=True)
for i, value in enumerate(valid):
    data = encoded(value)
    swift, java = [execute(command, "roundtrip", data) for command in [[SWIFT], JCOMMAND]]
    assert swift.returncode == java.returncode == 0, ("valid rejected", i, swift.stderr, java.stderr)
    assert swift.stdout == java.stdout == data, ("non-deterministic bytes", i)
    counts["validInbound"] += 1
    if value["kind"] != "call": continue
    expected = work / "expected.json"; expected.write_bytes(data)
    completions = [execute(command, "complete", data) for command in [[SWIFT], JCOMMAND]]
    assert all(result.returncode == 0 for result in completions)
    assert completions[0].stdout == completions[1].stdout
    for command, result in [([SWIFT], completions[1]), (JCOMMAND, completions[0])]:
        decoded = execute(command, "decode-completion", result.stdout, expected)
        assert decoded.returncode == 0 and decoded.stdout == result.stdout, ("completion mismatch", i)
        counts["completionDirections"] += 1
    if i == 0:
        original = json.loads(completions[0].stdout)
        for mutate in [lambda x: x["identity"].update(generation=2), lambda x: x.update(unknown=True), lambda x: x["outcome"].update(unknown=True), lambda x: x.update(operation="get")]:
            bad = copy.deepcopy(original); mutate(bad)
            for command in [[SWIFT], JCOMMAND]: assert execute(command, "decode-completion", encoded(bad), expected).returncode != 0
            counts["invalidCompletions"] += 1
for i, data in enumerate(invalid):
    for command in [[SWIFT], JCOMMAND]:
        result = execute(command, "roundtrip", data)
        assert result.returncode != 0, ("hostile accepted", i, command, data[:200])
    counts["invalidInbound"] += 1
print(json.dumps({"scope": "owned Swift/Java codec differential, not device/JNI execution or guest VM parity", "counts": counts, "passed": True}, sort_keys=True))
