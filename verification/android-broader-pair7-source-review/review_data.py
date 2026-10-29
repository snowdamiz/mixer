"""Independent bounded data/AST audit; imports no subject and runs no product."""
import sys

OWNED = "/Users/andreyyurlov/Documents/dev/mixer/verification/android-broader-pair7-source-review"


def guard(event, args):
    if event.startswith(("subprocess.", "socket.", "ctypes.")) or event in {
        "os.system", "os.posix_spawn", "os.fork", "os.forkpty", "os.kill",
        "os.killpg", "os.exec", "pty.spawn",
    }:
        raise RuntimeError("data review denies active API: " + event)
    if event == "import" and args[0].split(".")[0] not in sys.stdlib_module_names:
        raise RuntimeError("data review denies subject import: " + args[0])
    if event == "open":
        path, mode, flags = args
        writing = isinstance(mode, str) and any(c in mode for c in "wax+") or isinstance(flags, int) and flags & 3
        if writing and not str(path).startswith(OWNED + "/"):
            raise RuntimeError("data review denies non-owned write")
    if event in {"os.mkdir", "os.remove", "os.rmdir", "os.rename"}:
        if str(args[0]) != OWNED and not str(args[0]).startswith(OWNED + "/"):
            raise RuntimeError("data review denies non-owned mutation")


sys.addaudithook(guard)

import ast
import datetime
import hashlib
import json
import pathlib
import re

OUT = pathlib.Path(OWNED)
ROOT = OUT.parents[1]
PACKET = ROOT / "verification/android-broader-after-axis-rebase"
SOURCE = PACKET / "proposed-source"
reads = {}
checks = []


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read(path):
    path = pathlib.Path(path)
    data = path.read_bytes()
    assert len(data) <= 1_048_576, str(path)
    name = str(path.relative_to(ROOT))
    actual = identity(data)
    assert name not in reads or reads[name] == actual, ("read drift", name)
    reads[name] = actual
    return data


def unique(rows):
    result = {}
    for key, value in rows:
        assert key not in result, ("duplicate JSON key", key)
        result[key] = value
    return result


def decode(data):
    return json.loads(data, object_pairs_hook=unique)


def projection(rows):
    return hashlib.sha256("".join(p + "\0" + rows[p]["sha256"] + "\n" for p in sorted(rows)).encode()).hexdigest()


def check(name, condition):
    assert condition, name
    checks.append(name)


manifest = decode(read(PACKET / "source-manifest.json"))
seal = decode(read(PACKET / "seal.json"))
profile = decode(read(PACKET / "proposed-profile.json"))
canonical = decode(read(PACKET / "canonical-pair6-profile.json"))
named = decode(read(PACKET / "named-inputs.json"))
for relative, expected in seal["files"].items():
    check("sealed " + relative, identity(read(PACKET / relative)) == expected)
check("seal count and bytes", len(seal["files"]) == seal["sealed_files"] == 68 and sum(x["bytes"] for x in seal["files"].values()) == seal["sealed_bytes"] == 1_206_533)
check("seal projection", projection(seal["files"]) == seal["file_projection"])
check("named count and projection", len(named["files"]) == named["named_count"] == 91 and projection(named["files"]) == named["projection"])
for relative, expected in named["files"].items():
    check("named input unchanged " + relative, identity(read(ROOT / relative)) == expected)
for relative, expected in manifest["staged_sources"].items():
    check("staged " + relative, identity(read(SOURCE / relative)) == {k: expected[k] for k in ("bytes", "sha256")})
check("staged count and projection", len(manifest["staged_sources"]) == manifest["staged_source_count"] == 58 and projection(manifest["staged_sources"]) == manifest["staged_source_projection"])
check("frozen source namespace", {str(p.relative_to(SOURCE)) for p in SOURCE.rglob("*") if p.is_file()} == set(manifest["staged_sources"]))
for kind, count, digest in (("sdk", 22, "bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0"), ("adapter", 24, "ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e")):
    rows = profile[kind + "_files"]
    check(kind + " count and projection", len(rows) == count and projection(rows) == digest == profile[kind + "_compatibility_sha256"] == manifest[kind + "_projection"])
    actual_rows = {r["exported_path"]: {k: r[k] for k in ("bytes", "sha256")} for r in manifest["product_source_rows"] if r["kind"] == kind}
    check(kind + " product map exact", actual_rows == rows)
for row in manifest["product_source_rows"]:
    check("product bytes " + row["kind"] + "/" + row["exported_path"], identity(read(SOURCE / row["canonical_path"])) == {k: row[k] for k in ("bytes", "sha256")})
check("product total", len(manifest["product_source_rows"]) == manifest["product_members"] == 46 and sum(r["bytes"] for r in manifest["product_source_rows"]) == manifest["product_bytes"] == 661_583)
policy = read(SOURCE / "cli/Sources/MixerBuild/AndroidSDKCompatibility.swift").decode()
literal = policy.split('Data(#"""\n', 1)[1].split('\n        """#.utf8)', 1)[0]
check("compiled profile literal matches", decode(literal) == profile)
check("pair7 exact identity", profile["id"] == manifest["id"] == seal["proposed_id"] == "mixer.android-source-pair.7")
check("SDK identical to canonical6", profile["sdk_files"] == canonical["sdk_files"])
check("wire and descriptor unchanged", profile["wire"] == canonical["wire"] == manifest["wire"] and profile["default_descriptor"] == canonical["default_descriptor"] == manifest["descriptor"])
check("descriptor frozen bytes", identity(read(SOURCE / "verification/android-default-appearance-packaging/run-2/created-descriptor.json")) == profile["default_descriptor"])
doc = "Sources/MixerAndroidRuntime/DocumentSession.swift"
check("canonical axis exact", profile["adapter_files"][doc] == canonical["adapter_files"][doc] == {"bytes": 4328, "sha256": "cf1954af12e316bcd7cf8ea4def41d2dc6b26921fffa60177bce477c7f0749b7"})
driver = read(SOURCE / "cli/Sources/MixerBuild/Resources/android-build.py").decode()
previous_driver = driver.replace("value['id'] != 'mixer.android-source-pair.7'", "value['id'] != 'mixer.android-source-pair.6'").replace("('adapter', 24)", "('adapter', 23)").replace("'-proc:none', '-sourcepath', '', ", "")
check("old driver fixture byte exact", previous_driver.encode() == read(ROOT / "cli/Sources/MixerBuild/Resources/android-build.py"))

# Parse/apply the unified patch only as text; never invoke patch or a subject.
lines = read(PACKET / "minimal.patch").decode().splitlines(True)
index = 0
patched = {}
while index < len(lines):
    assert lines[index].startswith("--- ") and lines[index + 1].startswith("+++ ")
    old_name, new_name = lines[index][4:].strip(), lines[index + 1][4:].strip()
    assert new_name.startswith("b/")
    target = new_name[2:]
    before = [] if old_name == "/dev/null" else read(ROOT / target).decode().splitlines(True)
    result, cursor = [], 0
    index += 2
    while index < len(lines) and lines[index].startswith("@@ "):
        match = re.fullmatch(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n", lines[index])
        assert match, lines[index]
        old_start, old_count, new_start, new_count = [int(v) if v is not None else 1 for v in match.groups()]
        start = old_start - 1 if old_start else 0
        assert start >= cursor
        result.extend(before[cursor:start]);cursor = start
        index += 1; consumed = produced = 0
        while index < len(lines) and lines[index][:1] in (" ", "+", "-") and not lines[index].startswith("--- "):
            prefix, body = lines[index][0], lines[index][1:]
            if prefix != "+":
                assert cursor < len(before) and before[cursor] == body, (target, cursor)
                cursor += 1;consumed += 1
            if prefix != "-":
                result.append(body);produced += 1
            index += 1
        assert consumed == old_count and produced == new_count
        assert len(result) == (new_start - 1 if new_start else 0) + new_count
    result.extend(before[cursor:])
    check("patch exact " + target, "".join(result).encode() == read(SOURCE / target))
    assert target not in patched
    patched[target] = identity("".join(result).encode())
check("patch nine exact targets", len(patched) == 9 and set(patched) == {r["canonical_target"] for r in manifest["canonical_overlay_changes"]})
for row in manifest["canonical_overlay_changes"]:
    check("overlay before " + row["canonical_target"], (identity(read(ROOT / row["canonical_target"])) if row["before"] is not None else None) == row["before"] and patched[row["canonical_target"]] == row["proposed"])

ast_files = []
for relative in sorted(manifest["staged_sources"]):
    if relative.endswith(".py"):
        tree = ast.parse(read(SOURCE / relative).decode(), filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.Module)):
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                assert len(methods) == len(set(methods)), (relative, "duplicate method")
        ast_files.append(relative)
check("four Python sources AST only", len(ast_files) == 4)
for name, expected in list(reads.items()):
    assert identity((ROOT / name).read_bytes()) == expected, ("postflight drift", name)
receipt = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "independent-data-and-AST-pass-no-product-execution", "command": "/opt/homebrew/bin/python3 -I -B -S verification/android-broader-pair7-source-review/review_data.py",
    "python": sys.version, "python_executable": sys.executable,
    "source_revision": seal["source_revision"], "source_tree": seal["source_tree"], "revision_provenance": "root supplied; not independently queried",
    "packet_seal": identity(read(PACKET / "seal.json")), "packet_projection": seal["file_projection"],
    "reviewer_source": identity(pathlib.Path(__file__).read_bytes()), "check_count": len(checks), "checks": checks,
    "read_files": reads, "python_AST_only": ast_files,
    "active_API_audit_guard_installed_before_any_subject_import": True,
    "subject_imports": 0, "subject_methods": 0, "compilers": 0, "native_UI_or_process_probes": 0,
    "cleanup": "No runtime, native instance, capture process or helper started; no cleanup needed; existing processes and custody untouched.",
}
(OUT / "data-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
if (OUT / "REVIEW.md").is_file() and (OUT / "decision.json").is_file():
    files = {name: identity((OUT / name).read_bytes()) for name in ("REVIEW.md", "decision.json", "review_data.py", "data-receipt.json")}
    review_seal = {
        "schema": 1, "status": "sealed-source-data-review-no-product-execution",
        "files": files, "file_projection": projection(files),
        "file_count": len(files), "bytes": sum(v["bytes"] for v in files.values()),
        "subject_packet_seal": receipt["packet_seal"], "at": receipt["at"],
    }
    (OUT / "seal.json").write_text(json.dumps(review_seal, indent=2, sort_keys=True) + "\n")
print(json.dumps({k: receipt[k] for k in ("status", "check_count", "python", "packet_seal")}, sort_keys=True))
