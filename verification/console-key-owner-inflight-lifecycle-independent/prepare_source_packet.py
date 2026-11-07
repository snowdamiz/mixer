#!/usr/bin/env python3
"""Capture finite accepted source inputs only; never accesses active producer."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREPARED = REPO / "verification/console-key-owner-lifecycle-implementation/prepared-3"
CONTRACT = REPO / "verification/console-key-owner-lifecycle-contract"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            assert time.monotonic() - START < 55
            data = stream.read(262144)
            if not data:
                return digest.hexdigest()
            digest.update(data)


def strict(values):
    result = {}
    for key, value in values:
        assert key not in result
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=strict)


def main():
    assert not (OUT / "source-bindings.json").exists()
    assert sha(PREPARED / "freeze.json") == "fc4f644bccc627470bdb027a65d2e4d80cde51ca32c684b23a85fd6c1e80e307"
    frozen = {v["path"]: v for v in read(PREPARED / "freeze.json")["files"]}
    assert sha(CONTRACT / "membership-amendment.json") == "6291f022b841804797a4431c6d3af9853fac4d11db549975b1386ea664ced5da"
    contract_pins = {v["path"]: v for v in read(CONTRACT / "membership-amendment.json")["files"]}
    sources = [(PREPARED / "inputs/AGENTS.md", "accepted/AGENTS.md", frozen["inputs/AGENTS.md"])]
    for name in ("admission", "key_owner", "key_owner_supervisor", "fetch_flight", "jwks_transport", "bounded_tcp", "configured_verifier", "dns_resolver", "global_address", "manifest", "trust_snapshot"):
        relative = "inputs/hosted/lib/mixer_hosted/identity/" + name + ".ex"
        sources.append((PREPARED / relative, "accepted/" + relative.removeprefix("inputs/"), frozen[relative]))
    for relative in ("contract.md", "prospective-tests.json", "membership-amendment.json", "inputs/hosted/test/mixer_hosted/identity/key_owner_test.exs", "inputs/hosted/test/mixer_hosted/identity/startup_lifecycle_test.exs", "inputs/hosted/test/support/identity_component_fixture.ex"):
        pin = contract_pins.get(relative)
        sources.append((CONTRACT / relative, "prior-contract/" + relative, pin))
    acceptance = REPO / "verification/console-session-and-checkout-root-review/key-owner-lifecycle-acceptance.json"
    accepted = read(acceptance)["acceptance"]
    assert accepted["status"] == "accepted-bounded-socket-free-ordinary-supervised-lifecycle"
    assert accepted["prepared_seal"]["sha256"] == sha(PREPARED / "freeze.json")
    sources.append((acceptance, "root/key-owner-lifecycle-acceptance.json", None))
    assert len(sources) == 19
    bindings = []
    for source, target, pin in sources:
        assert "console-key-owner-inflight-lifecycle-contract" not in source.as_posix()
        assert source.is_file() and not source.is_symlink()
        digest = sha(source)
        data = source.read_bytes()
        if pin:
            assert len(data) == pin["bytes"] and digest == pin["sha256"]
        destination = OUT / "inputs" / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(data)
        assert sha(destination) == digest
        bindings.append({"source": source.relative_to(REPO).as_posix(), "snapshot": destination.relative_to(OUT).as_posix(), "bytes": len(data), "sha256": digest})
    binding_packet = {"schema": 1, "status": "independent-accepted-source-bindings-before-producer-access", "source_revision": "837e7084a0c6e69a88848b484fa3556563c75a59", "accepted_selected_source_tree_sha256": "4b7b6d97803154d773e76c28d5d6fdaada07f980c3ad198ca0e9cfae36746c4d", "prepared3_freeze_sha256": sha(PREPARED / "freeze.json"), "original_contract_amendment_sha256": sha(CONTRACT / "membership-amendment.json"), "root_acceptance_sha256": sha(acceptance), "sources": bindings}
    (OUT / "source-bindings.json").write_text(json.dumps(binding_packet, indent=2) + "\n")
    result = {"schema": 1, "status": "passed-finite-source-custody-preaccess-only", "created_at": datetime.now(timezone.utc).isoformat(), "command": "python3 -B verification/console-key-owner-inflight-lifecycle-independent/prepare_source_packet.py", "python": sys.version, "script_sha256": sha(Path(__file__)), "source_inputs_copied": len(bindings), "source_revision": binding_packet["source_revision"], "accepted_selected_source_tree_sha256": binding_packet["accepted_selected_source_tree_sha256"], "root_acceptance_sha256": binding_packet["root_acceptance_sha256"], "active_producer_read": False, "product_source_edits": 0, "runtime_compiler_formatter_fixture_version_processes": 0, "global_process_inventory": False, "scope": "Independent prospective lifecycle controls and exact accepted source snapshots only; no producer access or host/TLS execution.", "elapsed_seconds": round(time.monotonic() - START, 6)}
    (OUT / "source-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
