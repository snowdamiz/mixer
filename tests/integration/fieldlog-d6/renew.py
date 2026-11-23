"""Mint disposable D6 release signatures bound to the exact owner-downloaded app."""
import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from canonical import cbor
from prepare import HERE, VM_SHA, digest, require, roster, write
from release_packet import sha, unpack_app

DOMAIN = b"mixer.runtime.identity.v2\0"
RENEWABLE = {"ChecklistRelease/roots.json", "ChecklistRelease/identity.json"}
HISTORICAL_RUNTIMES = [
    "f5cdd219b095a424345d8065e081887a013da9e481eeb0ce95d666a091b43966",
    "895b4c0c7954acb1162483a607a07723a8535f5234f3e43aa329e31b763b4127",
]


def read(path):
    return json.loads(path.read_bytes())


def ledger_hash(entries):
    return sha("".join(f"{value}  {name}\n" for name, value in sorted(entries.items())).encode())


def openssl(*args):
    return subprocess.check_output([shutil.which("openssl"), *map(str, args)], timeout=10)


def materialize(work):
    attempt = work / "managed"
    record = read(attempt / "receipt.json")
    download = record["download"]
    require(record["passed"] and record["createHTTP"] == 201 and download["byteForByte"]
            and (download["ownerHTTP"], download["outsiderHTTP"], download["anonymousHTTP"]) == (200, 404, 401)
            and all(item["groupAbsent"] and item["exit"] == 0 for item in record["commands"].values()),
            "authenticated worker did not pass and close")
    signing = HERE / "fixture"
    payload_dir = work / "guests"
    pair = read(payload_dir / "receipt.json")["payloads"]
    require(set(pair) == {"baseline", "staged"}, "unexpected payloads")
    output = work / "renewed"
    app = output / "Products/Debug-iphonesimulator/FieldLog.app"
    output.mkdir(mode=0o700)
    app.parent.mkdir(parents=True)
    inventory = unpack_app((attempt / "owner.mxnative").read_bytes(), app, download)
    require(inventory == record["ownerFiles"] and inventory["FieldLog"] == record["app"]["machOSHA256"],
            "owner product differs")
    descriptor = read(signing / "identity-template.json")
    fallback = {name.replace("Platforms/iOS/", "ios/FieldLog/", 1): value
                for name, value in read(work / "generation.json")["fallbackFilesSHA256"].items()}
    require(ledger_hash(fallback) == descriptor["build"]["native_fallback_sha256"]
            and inventory["ChecklistRelease/bridge.json"] == descriptor["build"]["resource_policy_sha256"]
            and descriptor["engine"]["artifact_sha256"] == VM_SHA,
            "fallback, bridge, or engine binding differs")
    stable = {name: value for name, value in inventory.items() if name not in RENEWABLE}
    links = {"app/" + name: value for name, value in stable.items()}
    links.update({"VM/archive": VM_SHA, "managed/owner-archive": download["sha256"],
                  "managed/native-product-binding": download["workerArchiveBinding"],
                  "source/authoritative": record["inputs"]["source_tree_sha256"],
                  "source/lock": record["inputs"]["lock_sha256"]})
    descriptor["build"].update(settings_sha256=inventory["Info.plist"],
                               link_inputs_sha256=ledger_hash(links))
    config = read(signing / "config-template.json")
    fixture = output / "fixture"
    fixture.mkdir()
    installed = fixture / "Installed"
    shutil.copytree(app / "ChecklistRelease", installed)
    now = int(time.time())
    with tempfile.TemporaryDirectory(dir=output, prefix=".ephemeral-d6-keys-") as temporary:
        secrets = Path(temporary)
        keys = {}
        public_keys = {}
        for root in config["roots"]:
            key_id = root["key_id"]
            require(key_id in ("ios-initial-artifact", "ios-initial-assignment") and key_id not in keys,
                    "unexpected development trust key")
            key = secrets / f"{key_id}.pem"
            keys[key_id] = key
            openssl("genpkey", "-algorithm", "ED25519", "-out", key)
            key.chmod(0o600)
            public = openssl("pkey", "-in", key, "-pubout", "-outform", "DER")
            require(public[:12] == bytes.fromhex("302a300506032b6570032100") and len(public) == 44,
                    "unexpected Ed25519 public key")
            public_path = secrets / f"{key_id}.der"
            public_path.write_bytes(public)
            public_keys[key_id] = public_path
            root.update(public_key=base64.b64encode(public[12:]).decode(),
                        not_before_unix=now - 5, not_after_unix=now + 3600)
        write(installed / "roots.json", config["roots"])
        descriptor["build"]["trust_roots_sha256"] = digest(installed / "roots.json")
        runtime = sha(DOMAIN + cbor(descriptor))
        require(runtime not in HISTORICAL_RUNTIMES,
                "fixture runtime reused prior identity")
        write(installed / "identity.json", descriptor)
        config["host"]["runtime"] = runtime
        write(fixture / "config.json", config)

        def sign(field, document):
            domain = {"manifest": "artifact", "assignment": "assignment"}[field]
            message = secrets / "message"
            message.write_bytes(f"mixer.{domain}.v3\0".encode() + cbor(document))
            signature = openssl("pkeyutl", "-sign", "-rawin", "-inkey", keys[document["key_id"]], "-in", message)
            require(len(signature) == 64, "unexpected fixture signature")
            signature_path = secrets / "signature"
            signature_path.write_bytes(signature)
            openssl("pkeyutl", "-verify", "-pubin", "-keyform", "DER", "-rawin", "-inkey",
                    public_keys[document["key_id"]], "-in", message, "-sigfile", signature_path)
            return {field: document, "signature": base64.b64encode(signature).decode()}

        artifacts = {}
        for name, pin in pair.items():
            folder = fixture / name
            folder.mkdir()
            payload = payload_dir / f"{name}.wasm"
            require(digest(payload) == pin, "wrong signed payload input")
            shutil.copyfile(payload, folder / "payload.wasm")
            manifest = read(signing / f"{name}-manifest.json")
            require(manifest["scope"] == config["host"]["scope"]
                    and manifest["compressed_bytes"] == manifest["expanded_bytes"] == payload.stat().st_size,
                    "manifest template differs")
            manifest.update(runtime=runtime, created_at_unix=now, payload_sha256=pin)
            artifacts[name] = sha(cbor(manifest))
            write(folder / "signed-manifest.json", sign("manifest", manifest))
        for sequence, name, template in ((1, "baseline", "sequence-1-assignment"),
                                          (2, "staged", "sequence-2-assignment"),
                                          (3, "baseline", "sequence-3-rollback-assignment")):
            assignment = read(signing / f"{template}.json")
            require(assignment["sequence"] == sequence and assignment["scope"] == config["host"]["scope"]
                    and assignment["channel"] == config["channel"] == "beta"
                    and assignment["rollout_basis_points"] == 10000, "assignment template differs")
            assignment.update(runtime=runtime, created_at_unix=now, artifact_sha256=artifacts[name])
            result = fixture / name / "assignment.json" if sequence != 3 else fixture / "rollback.json"
            write(result, sign("assignment", assignment))
    for relative in RENEWABLE:
        shutil.copyfile(installed / Path(relative).name, app / relative)
    rebound = roster(app)
    require({name: value for name, value in rebound.items() if name not in RENEWABLE} == stable
            and sha(DOMAIN + cbor(read(app / "ChecklistRelease/identity.json"))) == runtime
            and digest(app / "ChecklistRelease/roots.json") == descriptor["build"]["trust_roots_sha256"]
            and not list(output.rglob("*.pem")), "installed identity rebind did not preserve product or clean release keys")
    seal = {"ownerAttachmentSHA256": download["sha256"],
            "unsignedMachO": inventory["FieldLog"], "runtime": runtime,
            "identitySHA256": rebound["ChecklistRelease/identity.json"],
            "rootsSHA256": rebound["ChecklistRelease/roots.json"],
            "rootsExpire": now + 3600, "artifacts": artifacts, "payloads": pair,
            "sourceLinkSHA256": descriptor["build"]["link_inputs_sha256"], "fixtureSignaturesVerified": True}
    write(output / "seal-receipt.json", seal)
    write(output / "historical-negative.json", {"runtimes": HISTORICAL_RUNTIMES})
    print(json.dumps(seal, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    args = parser.parse_args()
    materialize(args.work.resolve(strict=True))
