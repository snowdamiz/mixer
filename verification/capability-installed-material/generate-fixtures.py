#!/usr/bin/env python3
"""Original material fixtures with the real checked native-source preimage.

Other identity fields are bounded test metadata or hashes of named local inputs;
these fixtures do not attest a complete installed graph or final signed binary.
"""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capability-activation/Tests/MixerCapabilityActivationTests/Fixtures"
def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def file_sha(path):
    return sha((ROOT / path).read_bytes())
def write(name, value):
    raw = canonical(value); (OUT / name).write_bytes(raw); return sha(raw)

OUT.mkdir(parents=True, exist_ok=True)
subprocess.run([sys.executable, str(ROOT / "capabilities/tools/export-native-preimage.py"), "--check", "--output", str(OUT / "native-preimage.json")], check=True)
native = sha((OUT / "native-preimage.json").read_bytes())
scope = dict(organization="material-test", project="material-test", app="material-test", environment="development", platform="ios")
roots = [dict(key_id="material-test-root", public_key=base64.b64encode(bytes(range(32))).decode(), scope=scope,
              artifact=True, assignment=True, revoked=False, not_before_unix=0, not_after_unix=0)]
roots_hash = write("roots.json", roots)
bridge_hash = write("bridge.json", dict(schema=1, burst=8, starts_per_second=32))
http_hash = write("http.json", dict(schema=1, implementation="urlsession-normal-tls-v1", maximum_concurrent_requests=8))
storage_hash = write("storage.json", dict(schema=1, implementation="app-private-kv-v1", container="application-private",
                                         directory_component="material_test", maximum_total_bytes=4194304, maximum_entries=1024))
hashes = json.loads((ROOT / "capabilities/schema/hashes.json").read_bytes())
http_id, storage_id = "network.http.v1", "storage.keyValue.v1"
http_grant_hash = write("http-grant.json", dict(capability_id=http_id, schema_sha256=hashes["capabilities"][http_id],
    permissions=["network.https"], origins=["https://a.example", "https://b.example:8443"], methods=["GET", "PUT"], namespaces=[]))
storage_grant_hash = write("storage-grant.json", dict(capability_id=storage_id, schema_sha256=hashes["capabilities"][storage_id],
    permissions=["storage.appPrivate"], origins=[], methods=[], namespaces=["material_test"]))
test_digest = sha(b"original-installed-material-test-metadata-v1")
descriptor = dict(schema=2,
    application={k:v for k,v in scope.items() if k != "platform"} | {"bundle_id":"com.example.material-test"},
    platform=dict(os="ios", architecture="arm64", environment="device", minimum_os="17.0", target="arm64-apple-ios17.0"),
    engine=dict(version="material-test", source_sha256=file_sha("vm/src/lib.rs"),
        artifact_sha256=file_sha("experimental-capability-runtime/build-verification/local/qualified-final-v3/host/lib/libmixer_vm_capability_experimental.a"),
        profile="mixer-table-memory-v3", guest_abi=2, ui_schema=1, ui_contract_sha256=file_sha("contracts/ui-v1.json"), capability_contract_sha256=hashes["contractSHA256"]),
    toolchain=dict(compiler_version="test-metadata", compiler_sha256=test_digest, sdk_version="test-metadata", sdk_sha256=test_digest, build_tools_sha256=file_sha("capabilities/tools/export-native-preimage.py")),
    dependencies=[], capabilities=[
        dict(id=http_id, schema_sha256=hashes["capabilities"][http_id], native_sha256=native, configuration_sha256=http_hash, grants_sha256=http_grant_hash),
        dict(id=storage_id, schema_sha256=hashes["capabilities"][storage_id], native_sha256=native, configuration_sha256=storage_hash, grants_sha256=storage_grant_hash)],
    build=dict(configuration="debug", settings_sha256=test_digest, generated_bridge_sha256=native, link_inputs_sha256=test_digest,
        native_fallback_sha256=test_digest, permissions_sha256=test_digest, entitlements_sha256=test_digest, trust_roots_sha256=roots_hash, resource_policy_sha256=test_digest),
    execution=dict(startup_export="startup", startup_ms=60000, max_payload_bytes=4194304, memory_bytes=4194304, fuel=1000000,
        operand_stack=4096, call_depth=64, host_calls=1024, state_schema=0, protocol=3),
    capability_execution=dict(route="capability-guest-v1", contract_sha256=file_sha("contracts/capability-execution-v1.json"),
        transport_sha256=file_sha("contracts/guest-capability-transport-v1.json"), native_header_sha256=file_sha("vm/include/mixer_vm_capability.h"),
        maximum_requests=8, reservation_bytes=8388608, timeout_milliseconds=30000, turn_milliseconds=50, bridge_policy_sha256=bridge_hash))
write("identity.json", descriptor)
write("provenance.json", dict(test_only=True, native_preimage_sha256=native, native_is_actual_checked_source_preimage=True,
    test_metadata_digest=test_digest, complete_graph_proven=False, signed_application_attested=False,
    description="Original fixtures; no identity-parser synthetic native digests or fixture imported."))
