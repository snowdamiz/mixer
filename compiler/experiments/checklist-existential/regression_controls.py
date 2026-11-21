"""Compare the authored and corrected wrapper using only inert commands."""

import contextlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


def load(path):
    spec = importlib.util.spec_from_file_location("checklist_replay", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collision(replay, root, *, legacy, stage="prelaunch"):
    root.mkdir()
    receipt = root / "receipt.json"
    moved = root / "reservation.json"
    observed = {}

    def replace_reservation():
        receipt.rename(moved)
        receipt.write_bytes(b"unrelated evidence\n")
        observed["inode"] = receipt.stat().st_ino

    def execute(campaign):
        observed["scratch"] = campaign.scratch
        (campaign.scratch / "owned-marker").write_text("owned scratch")
        if stage == "prelaunch":
            replace_reservation()
            campaign.run("inert", "/usr/bin/false")

    method = "save" if legacy else "write_snapshot"
    original_write = getattr(replay.Receipt, method)

    def write(journal, *args, **kwargs):
        if stage == "finalization" and journal.data["status"] == "pass" and not observed.get("inode"):
            replace_reservation()
        return original_write(journal, *args, **kwargs)

    with patch.object(replay, "SCRATCH_ROOT", root), patch.object(replay.Campaign, "execute", execute), \
            patch.object(replay.Receipt, method, write):
        exit_code = replay.replay(receipt, root)
    replacement_preserved = (receipt.read_bytes() == b"unrelated evidence\n"
                             and receipt.stat().st_ino == observed["inode"])
    scratch = observed["scratch"]
    if legacy:
        assert exit_code and not replacement_preserved
        assert receipt.stat().st_ino != observed["inode"]
        result = json.loads(receipt.read_text())
        assert len(result["commands"]) == 1
        assert result["commands"][0]["exit"] == 1
        assert result["commands"][0]["custody"] == "direct-child-reaped/group-absent"
        assert not scratch.exists()
    else:
        assert exit_code and replacement_preserved
        assert (scratch / "owned-marker").read_text() == "owned scratch"
        assert not (scratch / "inert.err").exists()
        assert json.loads(moved.read_text())["cleanup"]["scratch"] == str(scratch)
        records = [json.loads(row) for row in (root / "receipt.json.journal").read_text().splitlines()
                   if row]
        result = records[-1]
        assert result["status"] == "held"
        assert result["cleanup"]["state"] == "retained-for-publication"
        assert not result["cleanup"]["removed"]
        assert json.loads((scratch / "publication-hold.json").read_text()) == result
        if stage == "finalization":
            assert not result["commands"]
        else:
            assert result["commands"][0]["stage"] == "prelaunch"
            assert "pidPgid" not in result["commands"][0]
    return {"replacementPreserved": replacement_preserved, "scratchRetained": scratch.exists(),
            "commands": len(result["commands"])}


def vanished_caller(replay, root, *, legacy):
    root.mkdir()
    caller = root / "caller"
    caller.mkdir()
    receipt = root / "receipt.json"

    def execute(campaign):
        caller.rmdir()
        output, _, _ = campaign.run("cwd", "/bin/pwd")
        assert output.strip() == str(campaign.scratch)

    error = None
    with contextlib.chdir(caller), patch.object(replay, "SCRATCH_ROOT", root), \
            patch.object(replay.Campaign, "execute", execute):
        try:
            exit_code = replay.replay(receipt, root)
        except FileNotFoundError as exc:
            error = exc
    result = json.loads(receipt.read_text())
    scratch = Path(result["cleanup"]["scratch"])
    if legacy:
        assert error is not None and error.filename == str(caller)
        assert result["status"] == "running" and "completedUTC" not in result
        assert scratch.is_dir()
    else:
        assert error is None and not exit_code
        assert result["status"] == "pass" and "completedUTC" in result
        assert result["cleanup"]["removed"] and not scratch.exists()
    assert [row["custody"] for row in result["commands"]] == ["direct-child-reaped/group-absent"]
    return {"status": result["status"], "scratchRetained": scratch.exists(),
            "cleanupError": type(error).__name__ if error else None}


def main():
    path = Path(sys.argv[1]).resolve(strict=True)
    legacy = sys.argv[2] == "legacy"
    replay = load(path)
    with tempfile.TemporaryDirectory(prefix="w07-publication-controls-", dir=replay.SCRATCH_ROOT) as tmp:
        root = Path(tmp)
        result = {
            "replacement": collision(replay, root / "replace", legacy=legacy),
            "vanishedCaller": vanished_caller(replay, root / "vanish", legacy=legacy),
        }
        if not legacy:
            result["replacementAtFinalization"] = collision(
                replay, root / "replace-final", legacy=legacy, stage="finalization")
    assert not root.exists()
    print(json.dumps({"variant": sys.argv[2], "controls": result, "testScratchRemoved": True}, indent=2))


if __name__ == "__main__":
    main()
