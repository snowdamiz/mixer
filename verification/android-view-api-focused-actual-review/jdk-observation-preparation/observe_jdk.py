"""DRAFT: fixed JDK/package file data observation; no command or tool admission."""


def exact_manifest(rows):
    if not isinstance(rows, list) or len(rows) != 74:
        raise ValueError("expected runtime manifest must be the exact74-member list")
    paths = []
    total = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise ValueError("unexpected runtime row shape")
        path = row["path"]
        if not isinstance(path, str) or not path or len(path) > 240:
            raise ValueError("invalid runtime member name")
        parts = path.split("/")
        if len(parts) > 8 or any(not p or p in (".", "..") for p in parts):
            raise ValueError("unsafe runtime member name")
        if any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/" for c in path):
            raise ValueError("unexpected runtime member character")
        if path not in ("bin/java", "bin/javac", "release") and not path.startswith(("conf/", "lib/")):
            raise ValueError("runtime member outside the fixed scope")
        if type(row["bytes"]) is not int or not 0 <= row["bytes"] <= 268435456:
            raise ValueError("invalid expected runtime size")
        digest = row["sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid expected runtime hash")
        paths.append(path)
        total += row["bytes"]
    if paths != sorted(paths) or len(set(paths)) != 74 or len({p.casefold() for p in paths}) != 74:
        raise ValueError("runtime paths are not unique and ordered")
    if total != 198674633:
        raise ValueError("expected runtime total changed")
    return rows


def classify(expected, observation):
    if observation["status"] != "stable-regular-file":
        return "unobserved-refused"
    if observation["bytes"] != expected["bytes"] or observation["sha256"] != expected["sha256"]:
        return "differs-from-frozen-expected"
    return "matches-frozen-expected-data-only"


def selected_package(data):
    text = data.decode("utf-8", "strict")
    if "\r" in text or "\x00" in text:
        raise ValueError("unexpected package status encoding")
    selected = []
    offset = 0
    for raw_span in data.split(b"\n\n"):
        if any(line == b"Package: temurin-17-jdk" for line in raw_span.split(b"\n")):
            selected.append((offset, raw_span))
        offset += len(raw_span) + 2
    if len(selected) != 1:
        raise ValueError("exact temurin-17-jdk stanza missing or duplicate")
    start, raw_span = selected[0]
    if len(raw_span) > 65536:
        raise ValueError("selected package stanza exceeds65536 bytes")
    stanza = raw_span.decode("utf-8", "strict")
    fields = {}
    wanted = {"Package", "Version", "Architecture", "Status", "Source"}
    for line in stanza.splitlines():
        if not line or line[0] in " \t":
            continue
        if ": " not in line:
            raise ValueError("malformed selected package field")
        key, value = line.split(": ", 1)
        if key in wanted:
            if key in fields or len(value) > 8192:
                raise ValueError("duplicate or oversized selected package field")
            fields[key] = value
    if fields.get("Package") != "temurin-17-jdk" or any(key not in fields for key in ("Version", "Architecture", "Status")):
        raise ValueError("selected package identity fields missing")
    return {"fields": fields, "exact_selected_stanza": stanza,
        "selected_span": {"start_byte": start, "bytes": len(raw_span),
            "ends_with_lf": raw_span.endswith(b"\n"),
            "separator_after": "\n\n" if start + len(raw_span) < len(data) else None}}


def selected_md5(data):
    text = data.decode("ascii", "strict")
    result = {}
    for member in ("lib/ct.sym", "lib/jrt-fs.jar"):
        target = "usr/lib/jvm/temurin-17-jdk-amd64/" + member
        selected = []
        for line in text.splitlines(keepends=True):
            parts = line.split()
            if parts and parts[-1] == target:
                if len(parts) != 2 or len(parts[0]) != 32 or any(c not in "0123456789abcdef" for c in parts[0]):
                    raise ValueError("malformed selected package MD5")
                selected.append({"path": target, "md5": parts[0], "exact_selected_line": line})
        if len(selected) > 1:
            raise ValueError("duplicate selected package checksum")
        result[member] = selected[0] if selected else {"status": "selected-package-checksum-absent", "path": target}
    return result


def observe(ctx):
    rows = exact_manifest(ctx["runtime_rows"])
    report = {
        "schema": 1, "status": "in-progress-data-only", "diagnostic_only": True,
        "runtime_admitted": False, "prepared13_or152_pass": False,
        "child_commands": [], "owned_java_attempts": 0,
        "fixed_jdk_root": "/usr/lib/jvm/temurin-17-jdk-amd64",
        "expected_manifest": ctx["expected_manifest_identity"],
        "selected_source": ctx["selected_source"],
        "provider": ctx["provider"], "python_bootstrap": ctx["python_identity"],
        "prior_run": {"id": "40854344723", "allowance_consumed": True,
            "refusal": "Refusal: official JDK runtime member changed: lib/ct.sym",
            "actual_mismatch_bytes_or_hash_previously_retained": False},
        "members": [], "differing_members": [], "refused_members": [],
        "raw_archive_data": {}, "package_metadata": {},
        "limits": ctx["limits"], "limitations": ctx["limitations"],
    }
    budget = {"remaining": 335544320, "actual_bytes_read": 0}
    ctx["checkpoint"](report)
    for expected in rows:
        path = expected["path"]
        actual, private_data = ctx["read_regular"](
            "/usr/lib/jvm/temurin-17-jdk-amd64/" + path,
            268435456, budget, retain_cap={"lib/ct.sym": 16777216, "lib/jrt-fs.jar": 1048576}.get(path, 0),
            package_md5=(path in ("lib/ct.sym", "lib/jrt-fs.jar")))
        outcome = classify(expected, actual)
        report["members"].append({"path": path, "expected": expected, "observed": actual, "outcome": outcome})
        if outcome == "differs-from-frozen-expected":
            report["differing_members"].append(path)
        if outcome == "unobserved-refused":
            report["refused_members"].append(path)
        if path in ("lib/ct.sym", "lib/jrt-fs.jar"):
            if actual["status"] == "stable-regular-file" and private_data is not None:
                report["raw_archive_data"][path] = ctx["retain_archive_data"](path, private_data, actual)
            else:
                report["raw_archive_data"][path] = {"status": "omitted", "reason": actual.get("reason", "file exceeds selected raw-export cap"), "bytes_cap": {"lib/ct.sym": 16777216, "lib/jrt-fs.jar": 1048576}[path]}
        report["jdk_actual_bytes_read"] = budget["actual_bytes_read"]
        ctx["checkpoint"](report)
    for name, path, cap, parser in (
        ("status", "/var/lib/dpkg/status", 8388608, selected_package),
        ("md5sums", "/var/lib/dpkg/info/temurin-17-jdk.md5sums", 1048576, selected_md5),
    ):
        actual, private_data = ctx["read_regular"](path, cap, {"remaining": cap, "actual_bytes_read": 0}, retain_cap=cap)
        entry = {"path": path, "observation": actual, "full_inventory_retained": False}
        if private_data is not None and actual["status"] == "stable-regular-file":
            try:
                entry["selected"] = parser(private_data)
                if name == "status":
                    entry["selected"]["selected_span"]["sha256"] = ctx["hash_data"](entry["selected"]["exact_selected_stanza"].encode("utf-8"))
                entry["status"] = "exact-package-data-selected"
            except (ValueError, UnicodeError) as exc:
                entry["status"] = "selection-refused"
                entry["reason"] = "selected package data format refused (" + type(exc).__name__ + ")"
        else:
            entry["status"] = "file-refused-or-absent"
        report["package_metadata"][name] = entry
        ctx["checkpoint"](report)
    report["package_md5_comparisons"] = {}
    for member in ("lib/ct.sym", "lib/jrt-fs.jar"):
        md5 = report["package_metadata"]["md5sums"].get("selected", {}).get(member, {}).get("md5")
        actual = next((row["observed"] for row in report["members"] if row["path"] == member), {})
        report["package_md5_comparisons"][member] = {
            "package_record_md5": md5, "actual_md5": actual.get("package_md5"),
            "matches": (md5 == actual["package_md5"]) if md5 and "package_md5" in actual else None,
            "scope": "Package checksum association only; MD5 does not authorize runtime or establish provenance/cause.",
        }
    partial = bool(report["refused_members"]) or any(report["raw_archive_data"].get(member, {}).get("status") != "retained-stable-observed-bytes" for member in ("lib/ct.sym", "lib/jrt-fs.jar")) or report["package_metadata"]["status"]["status"] != "exact-package-data-selected"
    report["status"] = "partial-data-observation-refusals" if partial else "complete-expected74-data-observation"
    report["expected_members_observed"] = len(report["members"]) - len(report["refused_members"])
    report["unexpected_membership_observed"] = False
    report["old_focused_allowance_reused"] = False
    report["runtime_admitted"] = False
    ctx["checkpoint"](report)
    return 1 if partial else 0
