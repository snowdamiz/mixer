"""Extend the reviewed F11 issuer inside its short-lived development key lease."""
import argparse
from pathlib import Path
import runpy
import subprocess

HERE = Path(__file__).resolve().parent
PHASES = ("prior", "successor", "rollback")
CONTROL_PHASES = ("wrong-runtime", "wrong-app", "wrong-ui-schema", "excess-memory")


def extend(work, packet, public, manifest, assignment, sign, cbor, sha, json_bytes):
    prior = (work / "export/guest/prior.wasm").read_bytes()
    successor = (work / "export/guest/historical.wasm").read_bytes()
    assert sha(prior) != sha(successor)
    prior_manifest = dict(manifest, release_id="fieldlog-f11-ios-prior",
                          provenance_id="fieldlog-f11-read-only-fixture",
                          payload_sha256=sha(prior), compressed_bytes=len(prior), expanded_bytes=len(prior))

    def write(phase, subject, payload, sequence):
        folder = packet / phase
        folder.mkdir()
        artifact = sha(cbor(subject))
        selection = dict(assignment, sequence=sequence, release_id=subject["release_id"],
                         artifact_sha256=artifact, scope=subject["scope"], runtime=subject["runtime"])
        (folder / "signed-manifest.json").write_bytes(sign(subject, "manifest", "artifact"))
        (folder / "assignment.json").write_bytes(sign(selection, "assignment", "assignment"))
        (folder / "payload.wasm").write_bytes(payload)

    for phase, subject, payload, sequence in zip(PHASES, (prior_manifest, manifest, prior_manifest),
                                                (prior, successor, prior), (1, 2, 3), strict=True):
        write(phase, subject, payload, sequence)
    for phase, subject in zip(CONTROL_PHASES, (
        dict(manifest, runtime="0" * 64),
        dict(manifest, scope=dict(manifest["scope"], app="fieldlog-f11-unregistered")),
        dict(manifest, ui_schema=2),
        dict(manifest, limits=dict(manifest["limits"], memory_bytes=4_194_305)),
    ), strict=True):
        write(phase, subject, successor, 2)

    import json
    identity = json.loads((public / "identity.json").read_bytes())
    execution = identity["execution"]
    host = dict(scope=manifest["scope"], runtime=manifest["runtime"], protocol=manifest["protocol"],
                guest_abi=manifest["guest_abi"], ui_schema=manifest["ui_schema"],
                capability_hashes=manifest["capability_hashes"], state_version=execution["state_schema"],
                max_payload_bytes=execution["max_payload_bytes"],
                limits=dict(memory_bytes=execution["memory_bytes"], fuel=execution["fuel"],
                            startup_milliseconds=execution["startup_ms"]))
    (packet / "host.json").write_bytes(json_bytes(host))
    (packet / "roots.json").write_bytes((public / "roots.json").read_bytes())


def issue(stage, work, public, packet, openssl):
    source = stage / "tests/integration/fieldlog-d8-f11-ios-simulator"
    clang = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
    guest = work / "export/guest"
    subprocess.run([clang / "clang", "--target=wasm32-unknown-none", "-Oz", "-ffreestanding",
                    "-fno-builtin", "-c", HERE / "Prior.c", "-o", guest / "prior.o"], check=True)
    subprocess.run([clang / "wasm-ld", "--no-entry", "--gc-sections", "--strip-all", "-z", "stack-size=16384",
                    "--max-memory=65536", *["--export=mixer_guest_" + name for name in
                        ("ui_start_v1", "ui_hydrate_v1", "ui_event_v1", "capability_ready_v1")],
                    guest / "prior.o", "-o", guest / "prior.wasm"], check=True)
    prepare = runpy.run_path(str(source / "prepare.py"))
    marker = '            shutil.copyfile(fixtures / name, output / name)\n'
    code = prepare["checked_replace"]((source / "issue.py").read_text(), marker, marker +
        "        extend(work, packet, output, manifest, assignment, sign, cbor, sha, json_bytes)\n")
    packet.mkdir()
    namespace = dict(__name__="f11_ota_issuer", extend=extend, packet=packet)
    exec(compile(code, str(source / "issue.py"), "exec"), namespace)
    metadata = namespace["issue"](work, public, openssl)
    for name in ("payload.wasm", "signed-manifest.json", "assignment.json"):
        assert (public / name).read_bytes() == (packet / "successor" / name).read_bytes()
        (public / name).unlink()
    return metadata


if __name__ == "__main__":
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("stage", "work", "public", "packet", "openssl"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(issue(**vars(args)), indent=2))
