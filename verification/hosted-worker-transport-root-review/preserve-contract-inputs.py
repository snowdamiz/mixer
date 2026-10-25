#!/usr/bin/env python3
"""Preserve already-hashed contract context; never import or execute its sources."""
import datetime
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/hosted-worker-transport-contract"
RECOVERY = ROOT / "verification/hosted-build-aggregate-admission/diagnostic-2/source.tar.gz"
RECOVERED = "hosted/lib/mixer_hosted/builds/admission.ex"
EXPECTED = "5308ca39096a9203fbd6b998a9cb784b4e0eed297baecd8141ed82399cfccf62"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    archive_path = OUT / "contract-inputs.tar.gz"
    receipt_path = OUT / "contract-selection.json"
    assert not archive_path.exists() and not receipt_path.exists(), "preserve prior result"
    receipt = json.loads((PRODUCER / "receipt.json").read_bytes())
    manifest_bytes = (PRODUCER / "source-map.json").read_bytes()
    command_bytes = (PRODUCER / "commands.json").read_bytes()
    assert sha(manifest_bytes) == receipt["source_map_sha256"]
    assert sha(command_bytes) == receipt["commands_sha256"]
    manifest = json.loads(manifest_bytes)
    rows = manifest["sources"]
    assert len(rows) == receipt["input_count"] == 88
    assert len({row["path"] for row in rows}) == len(rows)
    assert manifest["source_digest"] == receipt["source_digest"]
    assert sha(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()) == receipt["source_digest"]
    commands = json.loads(command_bytes)["commands"]
    for command in commands:
        assert command["exit_code"] == 0
        for stream in ("stdout", "stderr"):
            assert sha((PRODUCER / f'{command["name"]}.{stream}').read_bytes()) == command[f"{stream}_sha256"]
    with tarfile.open(RECOVERY, "r:gz") as archive:
        members = [member for member in archive.getmembers() if member.name == RECOVERED]
        assert len(members) == 1 and members[0].isfile()
        old_admission = archive.extractfile(members[0]).read()
    assert sha(old_admission) == EXPECTED
    inputs = {}
    moved = []
    for row in rows:
        path = row["path"]
        assert not Path(path).is_absolute() and ".." not in Path(path).parts
        current = (ROOT / path).read_bytes()
        data = current
        if sha(current) != row["sha256"]:
            assert path == RECOVERED and row["sha256"] == EXPECTED
            data = old_admission
            moved.append({"path": path, "contract_sha256": EXPECTED, "current_sha256": sha(current)})
        assert sha(data) == row["sha256"] and len(data) == row["size"]
        inputs[path] = data
    assert len(moved) == 1
    with tarfile.open(archive_path, "w:gz") as archive:
        for path, data in inputs.items():
            member = tarfile.TarInfo(path)
            member.size, member.mode = len(data), 0o644
            archive.addfile(member, io.BytesIO(data))
    with tarfile.open(archive_path, "r:gz") as archive:
        assert archive.getnames() == list(inputs)
        for member in archive:
            assert member.isfile() and archive.extractfile(member).read() == inputs[member.name]
    result = {
        "schema": 1,
        "status": "contract-selected-for-isolated-client-implementation-only",
        "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": ["python3", str(Path(__file__).relative_to(ROOT))],
        "script_sha256": sha(Path(__file__).read_bytes()),
        "producer_receipt_sha256": sha((PRODUCER / "receipt.json").read_bytes()),
        "source_map_sha256": sha(manifest_bytes),
        "commands_sha256": sha(command_bytes),
        "verified_input_count": len(inputs),
        "verified_input_bytes": sum(map(len, inputs.values())),
        "verified_command_count": len(commands),
        "source_digest": receipt["source_digest"],
        "source_archive": archive_path.name,
        "source_archive_sha256": sha(archive_path.read_bytes()),
        "recovered_intermediate_source": moved,
        "recovery_archive": str(RECOVERY.relative_to(ROOT)),
        "recovery_archive_sha256": sha(RECOVERY.read_bytes()),
        "scope": "Historical read context and dependency-only probes; archive inspected as data, no Mixer source executed.",
        "selected_boundaries": [
            "HTTPS client library initially isolated and disabled; no runtime installation selected",
            "strict framed HTTP response requires peer EOF inside total deadline",
            "int64 wire fields use canonical decimal strings",
            "library avoids deliberate secret logging; OS crash and hard resource qualification remains separate",
            "authenticated controller, persistent provider identity and inert execution claim remain separate implementation"
        ],
        "limitations": receipt["limitations"],
        "production_implementation_accepted": False,
        "ga_gate_changed": False,
    }
    receipt_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "verified_input_count", "verified_input_bytes", "verified_command_count")}))


if __name__ == "__main__":
    main()
