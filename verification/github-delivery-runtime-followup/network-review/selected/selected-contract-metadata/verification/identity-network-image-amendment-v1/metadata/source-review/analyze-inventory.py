#!/usr/bin/env python3
"""Read retained layer inventories and text only; no image/tool execution."""
import base64
import hashlib
import json
import posixpath
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROWS = {row["path"]: row for row in map(json.loads, (BASE / "inputs/layers/bookworm-merged-inventory.jsonl").read_text().splitlines())}

def resolve(path):
    path = posixpath.normpath("/" + path.lstrip("/"))
    trace = []
    for _ in range(64):
        parts = path.lstrip("/").split("/")
        replaced = False
        for i in range(1, len(parts) + 1):
            prefix = "/".join(parts[:i])
            row = ROWS.get(prefix)
            if row and row["type"] == "2":
                link = row["linkname"]
                target = link if link.startswith("/") else "/" + posixpath.join(posixpath.dirname(prefix), link)
                path = posixpath.normpath(posixpath.join(target, *parts[i:]))
                trace.append({"at": "/" + prefix, "symlink": link, "result": path})
                replaced = True
                break
        if replaced:
            continue
        row = ROWS.get(path.lstrip("/"))
        if row and row["type"] == "1":
            next_path = "/" + row["linkname"].lstrip("/")
            trace.append({"at": path, "hardlink": row["linkname"], "result": next_path})
            path = next_path
            continue
        if row is None:
            raise ValueError("missing source object: " + path)
        return {"requested": "/" + str(path).lstrip("/"), "resolved": path, "resolution": trace, "object": row}
    raise ValueError("source link depth exceeded")

required = ["/usr/bin/env", "/usr/bin/tar", "/usr/bin/openssl", "/usr/local/bin/elixir", "/usr/local/bin/mix", "/usr/local/bin/erl", "/usr/local/bin/escript", "/bin/sh", "/usr/local/lib/erlang/erts-17.1/bin/beam.smp", "/usr/local/lib/erlang/erts-17.1/bin/erlexec", "/usr/local/lib/erlang/lib/crypto-5.10/priv/lib/crypto.so", "/usr/lib/x86_64-linux-gnu/libsctp.so.1", "/etc/ssl/certs/ca-certificates.crt"]
objects = []
for path in required:
    result = resolve(path)
    result["requested"] = path
    obj = result["object"]
    if obj["type"] != "0":
        raise ValueError("required source target not regular: " + path)
    if path not in {"/etc/ssl/certs/ca-certificates.crt", "/usr/lib/x86_64-linux-gnu/libsctp.so.1"} and int(obj["mode"], 8) & 0o111 == 0:
        raise ValueError("required executable source mode missing: " + path)
    objects.append(result)

queue = [r["resolved"] for r in objects if "elf" in r["object"]]
static = {}
while queue:
    path = queue.pop()
    if path in static:
        continue
    row = resolve(path)["object"]
    elf = row["elf"]
    if elf["machine"] != 62:
        raise ValueError("required ELF is not x86_64")
    deps = []
    if elf["interpreter"]:
        interp = resolve(elf["interpreter"])
        deps.append({"kind": "PT_INTERP", "name": elf["interpreter"], "resolved": interp["resolved"], "sha256": interp["object"]["sha256"]})
        queue.append(interp["resolved"])
    for name in elf["needed"]:
        matches = []
        for directory in ["/lib/x86_64-linux-gnu", "/usr/lib/x86_64-linux-gnu", "/lib64", "/usr/lib64", "/lib", "/usr/lib", "/usr/local/lib"]:
            try:
                obj = resolve(directory + "/" + name)
                if obj["object"].get("elf"):
                    matches.append(obj)
            except ValueError:
                pass
        if not matches:
            raise ValueError("required static ELF dependency absent: " + path + ":" + name)
        if len({m["object"]["sha256"] for m in matches}) != 1:
            raise ValueError("ambiguous static ELF library source: " + name)
        match = matches[0]
        deps.append({"kind": "DT_NEEDED", "name": name, "resolved": match["resolved"], "sha256": match["object"]["sha256"]})
        queue.append(match["resolved"])
    static[path] = {"sha256": row["sha256"], "elf": elf, "dependencies": deps}

status = BASE / "inputs/layers/selected-text/bookworm-runtime-packages/var__lib__dpkg__status"
packages = []
for stanza in status.read_text().split("\n\n"):
    fields = dict(line.split(": ", 1) for line in stanza.splitlines() if ": " in line and not line.startswith(" "))
    if fields.get("Package") in {"openssl", "libssl3", "ca-certificates", "tar", "coreutils", "libsctp1", "libc6", "libstdc++6", "libodbc1", "libodbc2"}:
        if fields.get("Status") != "install ok installed":
            raise ValueError("required source package not recorded installed")
        packages.append({key: fields[key] for key in ["Package", "Status", "Version", "Architecture"]})

ca = BASE / "inputs/layers/selected-text/bookworm-runtime-packages/etc__ssl__certs__ca-certificates.crt"
ca_raw = ca.read_bytes()
certificates = []
for part in ca_raw.split(b"-----BEGIN CERTIFICATE-----")[1:]:
    encoded, end = part.split(b"-----END CERTIFICATE-----", 1)
    der = base64.b64decode(b"".join(encoded.split()), validate=True)
    if der[0] != 0x30:
        raise ValueError("CA certificate is not DER SEQUENCE")
    certificates.append({"der_bytes": len(der), "der_sha256": hashlib.sha256(der).hexdigest()})
if not certificates:
    raise ValueError("empty candidate CA source")
otp = (BASE / "inputs/layers/selected-text/bookworm-otp/usr__local__lib__erlang__releases__29__OTP_VERSION").read_text().strip()
if otp != "29.1.1":
    raise ValueError("candidate source OTP patch mismatch")
for app in ["elixir", "mix"]:
    text = (BASE / f"inputs/layers/selected-text/bookworm-elixir/usr__local__lib__elixir__lib__{app}__ebin__{app}.app").read_text()
    if '{vsn,"1.20.4"}' not in text:
        raise ValueError("candidate source application version mismatch")
result = {"schema": 1, "status": "required-paths-and-static-source-dependencies-present", "capability_scope": "bytes, archive metadata, source version declarations and static ELF dependency objects only; no runtime or dynamic-loader claim", "required_objects": objects, "static_elf_dependency_objects": static, "static_elf_object_count": len(static), "package_source_inventory": packages, "version_source_declarations": {"OTP_VERSION": otp, "elixir.app_vsn": "1.20.4", "mix.app_vsn": "1.20.4"}, "ca_bundle": {"path": "/etc/ssl/certs/ca-certificates.crt", "bytes": len(ca_raw), "sha256": hashlib.sha256(ca_raw).hexdigest(), "pem_certificate_count": len(certificates), "certificates": certificates, "scope": "PEM base64/DER-sequence shape and immutable source hashes only; no local certificate trust validation"}, "pending_runtime": ["Docker isolation/read-only root/capability/environment validation", "required executable/version commands and cryptographic library load", "OTP cacerts_get nonempty/CA-bundle binding and real HTTPS peer+hostname verified downloads", "Hex2.5.1 and Rebar3.28.0 bootstrap exact-artifact execution/compatibility", "offline dependencies/product compilation and both unchanged synthetic network methods", "cleanup and independent receipt acceptance"]}
(BASE / "analysis/capabilities.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": result["status"], "required_objects": len(objects), "static_elf_objects": len(static), "ca_certificates": len(certificates), "package_source_inventory": packages, "version_source_declarations": result["version_source_declarations"]}, sort_keys=True))
