import base64
import hashlib
import json
from pathlib import Path
import re

from run import CAP

HERE = Path(__file__).resolve().parent
SOURCE = Path("Sources/FieldLogStorage/WorkspaceRepository.swift")
EXPORT = Path("Integrations/GeneratedReport")
REVIEWED = "eb08569c13b5f65e25edd0dfde1fe70fc8278ece"

def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def git_blob(path):
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()

def single(root, pattern):
    hit, = root.rglob(pattern)
    return hit

def link_roster(snapshot):
    references = []
    for group in ("tasks", "drafts", "entries"):
        for record in snapshot[group]:
            references.append([group, record["id"], record["projectID"], record.get("attachmentIDs", [])])
    return {
        "records": references,
        "photos": [[row["id"], row["filename"], row["byteCount"]] for row in snapshot["attachments"]],
        "outbox": [[row["id"], row["kind"], row["recordID"], row["revision"]] for row in snapshot["outbox"]],
        "restoration": snapshot["restoration"],
    }

def compare(work, output):
    campaign = work / "commands"
    afterimages = {}
    report = {}
    for platform in ("apple", "export"):
        base_label = f"baseline-{platform}-r2-disk"
        if not (campaign / (base_label + ".log")).exists():
            base_label = f"baseline-{platform}-disk"
        baseline = campaign / (base_label + ".log")
        candidate = campaign / f"final-{platform}-disk.log"
        assert baseline.read_bytes() == candidate.read_bytes(), platform
        rows = [json.loads(line) for line in candidate.read_text().splitlines()]
        assert len(rows) == 11
        checkpoints = {row["checkpoint"]: row["roster"] for row in rows}
        for name in ("legacy", "current"):
            assert checkpoints[name + "-refused"] == checkpoints[name + "-task-saved"]
        for row in rows:
            workspace = json.loads(base64.b64decode(row["roster"]["workspace.json"]))
            row["linkRoster"] = link_roster(workspace)
        afterimages[platform] = rows
        report[platform] = {"identical": True, "checkpoints": len(rows), "replaySHA256": digest(candidate),
                            "coldLegacyAndCurrentExactBytes": True, "refusedPrecommitNoRosterMutation": True}
    target = output / "afterimages.json"
    target.write_text(json.dumps(afterimages, separators=(",", ":"), ensure_ascii=False) + "\n")
    return {"packages": report, "afterimages": target.name, "afterimagesSHA256": digest(target)}

def source_identity(work):
    baseline = work / "baseline"
    final = work / "final"
    paths = {"apple": SOURCE, "export": EXPORT / SOURCE}
    identities = {}
    for key, path in paths.items():
        original = baseline / "fieldlog" / path
        shared = final / "fieldlog" / path
        identities[key] = {
            "path": str(path),
            "baselineGitBlob": git_blob(original), "baselineSHA256": digest(original), "baselineLines": len(original.read_bytes().splitlines()),
            "candidateGitBlob": git_blob(shared), "candidateSHA256": digest(shared), "candidateLines": len(shared.read_bytes().splitlines()),
        }
    assert identities["apple"]["candidateSHA256"] == identities["export"]["candidateSHA256"]
    return identities

def native(work):
    commands = work / "commands"
    arm64 = work / "final-android/build/aarch64-unknown-linux-android28/release"
    source_path = work / "final/App" / SOURCE
    storage_list = arm64 / "FieldLogStorage.build/sources"
    sources = storage_list.read_text().splitlines()
    assert sources == [str(source_path)]
    library = arm64 / "libAppAndroid.so"
    with library.open("rb") as f:
        elf = f.read(20)
    assert elf[:6] == b"\x7fELF\x02\x01" and int.from_bytes(elf[18:20], "little") == 183
    readelf = (commands / "read-android-elf.log").read_text()
    loads = [line.split() for line in readelf.splitlines() if line.lstrip().startswith("LOAD ")]
    assert loads and all(int(row[-1], 16) >= 16_384 for row in loads)
    android_log = (commands / "final-android.log").read_text()
    assert "Swift version 6.3.3" in android_log
    link_line, = [row for row in android_log.splitlines() if "/ld.lld" in row and row.startswith(' "') and "libAppAndroid.so" in row]
    object_name = "FieldLogStorage.build/WorkspaceRepository.swift.o"
    assert link_line.count(object_name) == 1
    assert "WorkspaceRepositoryC11attachPhoto" in (commands / "read-android-symbols.log").read_text()
    apple = work / "final-iphoneos/derived/Build"
    apple_list = single(apple, "FieldLogStorage.SwiftFileList")
    apple_path = work / "final/fieldlog" / SOURCE
    assert apple_list.read_text().splitlines() == [str(apple_path)]
    assert source_path.read_bytes() == apple_path.read_bytes()
    linklist = single(apple, "FieldLog.LinkFileList")
    assert sum(line.endswith("/FieldLogStorage.o") for line in linklist.read_text().splitlines()) == 1
    linkmap = single(apple, "FieldLog-LinkMap-normal-arm64.txt")
    assert b"WorkspaceRepositoryC8addPhoto" in linkmap.read_bytes()
    apple_symbols = (commands / "read-ios-storage-symbols.log").read_text()
    assert "WorkspaceRepositoryC8addPhoto" in apple_symbols
    assert "WorkspaceRepositoryC11attachPhoto" not in apple_symbols
    binary = apple / "Products/Debug-iphoneos/FieldLog.app/FieldLog"
    macho = (commands / "read-ios-macho.log").read_text()
    assert "ARM64" in macho and re.search(r"\bplatform\s+IOS\b", macho), macho[:1000]
    return {
        "android": {"target": "aarch64-unknown-linux-android28",
                    "toolchain": "Swift 6.3.3 / Xcode 26.6 (17F113)",
                    "compilerSource": str(source_path.relative_to(work)),
                    "compilerSourceSHA256": digest(source_path),
                    "linkedObject": object_name, "linkedSHA256": digest(library),
                    "linkedBytes": library.stat().st_size,
                    "loadAlignment": [int(row[-1], 16) for row in loads],
                    "attachPhotoSymbol": True},
        "iphoneos": {"target": "arm64-apple-ios26.0", "toolchain": "Xcode 27.2 (27B52)",
                     "compilerSource": str(apple_path.relative_to(work)),
                     "compilerSourceSHA256": digest(apple_path),
                     "linkedTargetObject": "FieldLogStorage.o",
                     "linkedSHA256": digest(binary), "linkedBytes": binary.stat().st_size,
                     "addPhotoSymbol": True, "attachPhotoSymbol": False,
                     "scope": "Unsigned generic iPhoneOS link and static inspection. Existing guest resource placeholders."},
    }

def summarize(work, output, checked_receipts, host_only=False):
    receipts = {}
    checkout = str(HERE.parents[2])
    for name, entry in sorted(checked_receipts.items()):
        row = json.dumps(entry).replace(str(work), "$WORK").replace(str(HERE), "$REPLAY").replace(checkout, "$MIXER")
        receipts[name] = json.loads(row)
    peak = max(row["peakAllocatedBytes"] for row in receipts.values())
    assert peak < CAP
    return {
        "patchSHA256": digest(HERE / "fieldlog-workspace-repository.patch"),
        "baselineTree": REVIEWED,
        "candidateTree": (HERE / "candidate-tree.txt").read_text().strip(),
        "fieldLogPublicCommit": "552559d2d3278abb9b1aa7dcf0288102c09a202b",
        "mixerPublicCommit": "6bc461f4fc7c29771718c7c5ce5a2a39b78f4d2d",
        "mixerPublicTree": "d888b6a1ef9331079b98a0dc21c3a1b8ee482894",
        "repositorySources": source_identity(work), "replay": compare(work, output),
        "native": None if host_only else native(work),
        "peakSampledAllocatedBytes": peak, "allocatedByteCap": CAP, "commands": receipts,
    }
