"""Freeze only this source-contract packet. No producer imports or subprocess."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent


def main():
    seal_path = HERE / "seal.json"
    if seal_path.exists():
        raise SystemExit("refuse replacing frozen seal")
    receipts = sorted(HERE.glob("commands/*/receipt.json"))
    assert receipts and json.loads(receipts[-1].read_bytes())["exit_code"] == 0
    members = []
    for path in sorted(HERE.rglob("*"), key=lambda p: p.relative_to(HERE).as_posix()):
        if path.is_file():
            assert path.suffix != ".pyc" and "__pycache__" not in path.parts
            data = path.read_bytes()
            members.append({"path": path.relative_to(HERE).as_posix(), "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest()})
    encoded = json.dumps(members, sort_keys=True, separators=(",", ":")).encode()
    seal = {"schema": 1, "status": "frozen-child-owned-input-source-interface-and-host-model-proposal",
            "member_count": len(members), "member_bytes": sum(x["bytes"] for x in members),
            "tree_sha256": hashlib.sha256(encoded).hexdigest(), "members": members,
            "production_root_policy_or_funding_selected": False,
            "operational_provider_or_authority": False,
            "compiler_invocations": 0, "product_or_loader_executable_launches": 0,
            "native_FieldLog_OTA_GA": False, "all_three_production_selectors": "Pending",
            "Rust_interface_compiled": False, "native_descriptor_or_allocator_adapter_implemented": False,
            "proposed_source146_tree": "acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d"}
    seal_path.write_text(json.dumps(seal, sort_keys=True, indent=2) + "\n")
    print(json.dumps({k: v for k, v in seal.items() if k != "members"}, sort_keys=True))
    for path in HERE.rglob("*"):
        if path.is_file(): path.chmod(0o444)
    for path in sorted((p for p in HERE.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    HERE.chmod(0o555)


if __name__ == "__main__":
    main()
