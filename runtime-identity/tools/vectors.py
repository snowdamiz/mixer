#!/usr/bin/env python3
"""Original runtime-identity vectors; stdlib-only independent CBOR/hash oracle.

All hashes name synthetic test inputs. None identifies an installed app build.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def head(major, value):
    if value < 24:
        return bytes([(major << 5) | value])
    for width, suffix in [(1, 24), (2, 25), (4, 26), (8, 27)]:
        if value < 1 << (8 * width):
            return bytes([(major << 5) | suffix]) + value.to_bytes(width, "big")
    raise ValueError("unsigned integer overflow")


def cbor(value):
    if type(value) is bool:
        return b"\xf5" if value else b"\xf4"
    if type(value) is int and value >= 0:
        return head(0, value)
    if type(value) is str:
        encoded = value.encode("utf-8")
        return head(3, len(encoded)) + encoded
    if type(value) is list:
        return head(4, len(value)) + b"".join(map(cbor, value))
    if type(value) is dict and all(type(k) is str for k in value):
        pairs = sorted((cbor(k), cbor(v)) for k, v in value.items())
        return head(5, len(value)) + b"".join(k + v for k, v in pairs)
    raise ValueError("outside restricted canonical data model")


def digest(label):
    return hashlib.sha256(("SYNTHETIC IDENTITY TEST ONLY: " + label).encode()).hexdigest()


def baseline():
    return dict(schema=1,
        application=dict(organization="test-org", project="test-project", app="test-app", environment="development", bundle_id="com.example.identity-test"),
        platform=dict(os="ios", architecture="arm64", environment="device", minimum_os="17.0", target="arm64-apple-ios17.0"),
        engine=dict(version="owned-test-1", source_sha256=digest("engine-source"), artifact_sha256=digest("engine-library"), profile="mixer-integer-v1", guest_abi=1, ui_schema=1, ui_contract_sha256=digest("ui-contract"), capability_contract_sha256=digest("capability-contract")),
        toolchain=dict(compiler_version="synthetic-swift-1", compiler_sha256=digest("compiler"), sdk_version="synthetic-sdk-1", sdk_sha256=digest("sdk"), build_tools_sha256=digest("tools")),
        dependencies=[dict(id="Crypto", version="synthetic-1", artifact_sha256=digest("crypto-library")), dict(id="Foundation", version="target-sdk", artifact_sha256=digest("foundation-sdk-input"))],
        capabilities=[],
        build=dict(configuration="release", **{k + "_sha256": digest(k) for k in ["settings", "generated_bridge", "link_inputs", "native_fallback", "permissions", "entitlements", "trust_roots", "resource_policy"]}),
        execution=dict(startup_export="run", startup_ms=5000, max_payload_bytes=4194304, memory_bytes=4194304, fuel=1000000, operand_stack=4096, call_depth=64, host_calls=1024, state_schema=1, protocol=2))


def vectors():
    base = baseline()
    cases = [("ios-device", base)]
    simulator = copy.deepcopy(base)
    simulator["platform"].update(environment="simulator", target="arm64-apple-ios17.0-simulator")
    cases.append(("ios-simulator", simulator))
    android = copy.deepcopy(base)
    android["platform"].update(os="android", minimum_os="28", target="aarch64-unknown-linux-android28")
    cases.append(("android-device", android))
    capabilities = copy.deepcopy(base)
    capabilities["capabilities"] = [dict(id="network.http.v1", **{k + "_sha256": digest(k) for k in ["schema", "native", "configuration", "grants"]})]
    cases.append(("declared-http-capability", capabilities))
    for profile in ["mixer-numeric-v2", "mixer-table-memory-v3"]:
        variant = copy.deepcopy(base); variant["engine"]["profile"] = profile
        cases.append((profile, variant))
    unicode = copy.deepcopy(base)
    unicode["execution"].update(startup_export="e\u0301.start.日志", state_schema=(1 << 64) - 1)
    cases.append(("unicode-export-and-uint64", unicode))
    return [dict(name=name, descriptor=value, canonicalCBOR=cbor(value).hex(), fingerprint=hashlib.sha256(b"mixer.runtime.identity.v1\0" + cbor(value)).hexdigest()) for name, value in cases]


if __name__ == "__main__":
    path = ROOT / "Tests/MixerRuntimeIdentityTests/Fixtures/vectors.json"
    output = json.dumps(vectors(), ensure_ascii=True, indent=2) + "\n"
    if sys.argv[1:] == ["--check"]:
        if path.read_text() != output:
            raise SystemExit("runtime identity vectors are stale")
        print("Seven independent canonical/hash vectors match")
    elif not sys.argv[1:]:
        path.write_text(output)
    else:
        raise SystemExit("Usage: vectors.py [--check]")
