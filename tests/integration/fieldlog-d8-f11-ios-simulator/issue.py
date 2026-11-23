"""Issue a short-lived development packet with an ephemeral Ed25519 key."""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

WASM = "b3def2b5d11c0a350d33a44ff0cd55f4a7e97f6979e547c49ab13bde696d4fe5"
NOTE = "9ac7679b7cb5f00915730fe40c3ccb018d75e82e482a80578e6c974985b42198"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def cbor(value):
    def head(major, count):
        prefix = major << 5
        if count < 24:
            return bytes([prefix | count])
        width = next(width for width in (1, 2, 4, 8) if count < 1 << (8 * width))
        return bytes([prefix | (23 + width.bit_length())]) + count.to_bytes(width, "big")
    if isinstance(value, bool):
        return b"\xf5" if value else b"\xf4"
    if isinstance(value, int) and value >= 0:
        return head(0, value)
    if isinstance(value, str):
        encoded = value.encode()
        return head(3, len(encoded)) + encoded
    if isinstance(value, list):
        return head(4, len(value)) + b"".join(map(cbor, value))
    if isinstance(value, dict):
        pairs = sorted((cbor(key), cbor(item)) for key, item in value.items())
        return head(5, len(value)) + b"".join(key + item for key, item in pairs)
    raise ValueError(f"Unsupported fixture metadata: {value!r}")


def issue(work, output, openssl):
    source = work / "export/source"
    vm = work / "rust/aarch64-apple-ios-sim/release/libmixer_vm.a"
    fixtures = source / "capability-activation/Tests/MixerCapabilityActivationTests/Fixtures"
    vectors = json.loads((source / "runtime-identity/Tests/MixerRuntimeIdentityTests/Fixtures/vectors-v2.json").read_bytes())
    for vector in vectors:
        encoded = cbor(vector["descriptor"])
        if encoded.hex() != vector["canonicalCBOR"] or sha(b"mixer.runtime.identity.v2\0" + encoded) != vector["fingerprint"]:
            raise ValueError("Canonical CBOR or fingerprint differs from the stock vector")

    payload = (work / "export/guest/historical.wasm").read_bytes()
    seed = (work / "export/guest/seed.json").read_bytes()
    if sha(payload) != WASM or sha(seed) != "334f3dbcf08b6b1e363da63fad7388fcf7496c9573c3ac0315fd4e0c87a3876d":
        raise ValueError("Historical payload or seed bytes differ")
    scope = dict(organization="mixer-local", project="fieldlog", app="fieldlog-f11-ios",
                 environment="development", platform="ios")
    key_id = "fieldlog-f11-ios-ephemeral"
    now = int(time.time())
    expires = now + 7200
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="f11-trust-", dir=work) as temporary:
        tmp = Path(temporary)
        key = tmp / "key.pem"
        subprocess.run([openssl, "genpkey", "-algorithm", "ED25519", "-out", key], check=True)
        public = subprocess.check_output([openssl, "pkey", "-in", key, "-pubout", "-outform", "DER"])
        if public[:12] != bytes.fromhex("302a300506032b6570032100") or len(public) != 44:
            raise ValueError("Unexpected Ed25519 public key DER")
        roots = json_bytes([dict(key_id=key_id, public_key=base64.b64encode(public[12:]).decode(),
            scope=scope, artifact=True, assignment=True, revoked=False,
            not_before_unix=now - 60, not_after_unix=expires)])
        identity = json.loads((fixtures / "identity.json").read_bytes())
        identity["application"] = {key: value for key, value in scope.items() if key != "platform"}
        identity["application"]["bundle_id"] = "dev.mixer.fieldlog.f11simulator"
        identity["platform"] = dict(os="ios", architecture="arm64", environment="simulator",
                                    minimum_os="26.0", target="arm64-apple-ios26.0-simulator")
        vm_hash = sha(vm.read_bytes())
        identity["engine"].update(version="fieldlog-d8-f11-ios-fixture", artifact_sha256=vm_hash, ui_contract_sha256=NOTE)
        identity["build"].update(configuration="debug", trust_roots_sha256=sha(roots), link_inputs_sha256=vm_hash)
        identity["execution"]["startup_export"] = "mixer_guest_ui_start_v1"
        if identity["capability_execution"]["turn_milliseconds"] != 50:
            raise ValueError("Expected a 50 ms turn")
        repository = source / "capability-activation/Sources/FieldLogStorage/WorkspaceRepository.swift"
        identity["dependencies"] = [
            {"id": name, "version": "1", "artifact_sha256": digest} for name, digest in [
                ("fieldlog-pair25-repository", sha(repository.read_bytes())),
                ("mixer.fieldlog-f11-note-fixture-v1", NOTE),
                ("mixer.guest-ui-deferred-startup-v1", "cdc8e301305ecfd6abe40872df55d90dce86ea816781904c45d1fa119d2da260"),
                ("mixer.guest-ui-native-header-v1", "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"),
            ]]
        grant = json.loads((fixtures / "storage-grant.json").read_bytes())
        grant["namespaces"] = ["fieldlog-d8-f11-note"]
        storage, = [cap for cap in identity["capabilities"] if cap["id"] == grant["capability_id"]]
        storage["grants_sha256"] = sha(json_bytes(grant))
        identity["capabilities"] = [storage]
        runtime = sha(b"mixer.runtime.identity.v2\0" + cbor(identity))
        release = "fieldlog-f11-ios-successor"
        manifest = dict(schema=3, scope=scope, release_id=release, runtime=runtime, protocol=3, guest_abi=2,
            ui_schema=1, provenance_id="fieldlog-f11-vertical-host-behavior-projection",
            source_commit="c6562ba80b992016c0c963cf4c67a59f1f605fd0",
            capability_hashes={storage["id"]: storage["schema_sha256"]}, state_min=0, state_max=0,
            payload_sha256=WASM, compressed_bytes=len(payload), expanded_bytes=len(payload), compression="none",
            asset_hashes={}, source_map_sha256=sha(b"{}"),
            limits=dict(memory_bytes=65536, fuel=identity["execution"]["fuel"], startup_milliseconds=5000),
            key_id=key_id, created_at_unix=now, capability_grants=dict(schema=1,
                schema_sha256="b394ffd165ef28977de9743b1c1a98c419504787f2912e30d419cfb1582e15e1", entries=[grant]))
        assignment = dict(schema=3, scope=scope, channel="beta", cohort="sha256-v1", rollout_basis_points=10000,
            sequence=2, release_id=release, artifact_sha256=sha(cbor(manifest)), runtime=runtime,
            key_id=key_id, created_at_unix=now)

        def sign(subject, field, domain):
            message, signature, public_key = [tmp / name for name in ("message", "signature", "public.der")]
            message.write_bytes(f"mixer.{domain}.v3\0".encode() + cbor(subject))
            public_key.write_bytes(public)
            subprocess.run([openssl, "pkeyutl", "-sign", "-rawin", "-inkey", key,
                            "-in", message, "-out", signature], check=True)
            subprocess.run([openssl, "pkeyutl", "-verify", "-rawin", "-pubin", "-keyform", "DER",
                            "-inkey", public_key, "-in", message, "-sigfile", signature], check=True)
            return json_bytes({field: subject, "signature": base64.b64encode(signature.read_bytes()).decode()})

        for name, data in {
            "roots.json": roots, "identity.json": json_bytes(identity), "storage-grant.json": json_bytes(grant),
            "workspace.json": seed, "payload.wasm": payload,
            "signed-manifest.json": sign(manifest, "manifest", "artifact"),
            "assignment.json": sign(assignment, "assignment", "assignment"),
        }.items():
            (output / name).write_bytes(data)
        for name in ("bridge.json", "storage.json"):
            shutil.copyfile(fixtures / name, output / name)
    return dict(expiresUnix=expires, runtimeFingerprint=runtime, archiveSHA256=vm_hash, stockIdentityVectors=len(vectors))


if __name__ == "__main__":
    work, output, openssl = map(Path, sys.argv[1:])
    print(json.dumps(issue(work.resolve(strict=True), output.resolve(), openssl), indent=2))
