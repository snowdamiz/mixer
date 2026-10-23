#!/usr/bin/env python3
"""Explicit schema2 copied-input capture; no build graph or adapter authority."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

# Reuse the reviewed fd-relative byte-copy primitives, never its v1 entrypoints.
from capture import (CaptureError, require, canonical, sha, decode, fields, relative,
    open_root, stream_file, read_file, read_path, digest_paths, replace_digest,
    validate_bindings, write_new, sync_directory, MAX_MANIFEST, MAX_DESCRIPTOR,
    MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES, HEX)

MAX_MATERIAL_FILE = 65536
MAX_MATERIAL_TOTAL = 327680

def inspect_v2(tool, descriptor_path):
    result = subprocess.run([str(Path(tool).absolute()), 'inspect-v2', str(descriptor_path)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
    require(result.returncode == 0 and len(result.stdout) <= MAX_MANIFEST, 'trusted mixer-identity rejected schema2 descriptor')
    value = decode(result.stdout)
    require(type(value) is dict and type(value.get('schema')) is int and value['schema'] == 2 and
        value.get('buildAttested') is False and type(value.get('fingerprint')) is str and
        HEX.fullmatch(value['fingerprint']), 'invalid schema2 identity-tool result')
    return value['fingerprint']

def uint(value, low, high):
    return type(value) is int and low <= value <= high

def material(raw):
    require(len(raw) <= MAX_MATERIAL_FILE, 'material file limit')
    value = decode(raw)
    require(type(value) is dict and canonical(value) == raw, 'material must be exact canonical JSON object')
    stack, count = [(value, 0)], 0
    while stack:
        item, depth = stack.pop(); count += 1
        require(depth <= 8 and count <= 8192, 'material structure limit')
        require(type(item) in (dict, list, str, int, bool), 'unsupported material value')
        if type(item) is dict:
            require(all(type(k) is str and k.isascii() for k in item), 'material ASCII keys required')
            stack.extend((x, depth+1) for x in item.values())
        elif type(item) is list: stack.extend((x, depth+1) for x in item)
        elif type(item) is int: require(0 <= item <= (1<<64)-1, 'material unsigned integer required')
    return value

def strings(value, maximum):
    require(type(value) is list and len(value) <= maximum, 'grant list limit')
    previous = ''
    for item in value:
        require(type(item) is str and len(item) <= 4096 and all(33 <= ord(c) <= 126 for c in item) and item > previous,
            'grant strings must be sorted unique printable ASCII')
        previous = item
    return value

def origin(value):
    if not value.startswith('https://') or len(value) > 267: return False
    parts = value[8:].split(':')
    if not 1 <= len(parts) <= 2 or not 1 <= len(parts[0]) <= 253: return False
    if not all(1 <= len(label) <= 63 and not label.startswith('-') and not label.endswith('-') and
        all('a' <= c <= 'z' or '0' <= c <= '9' or c == '-' for c in label) for label in parts[0].split('.')): return False
    return len(parts) == 1 or (parts[1].isascii() and parts[1].isdigit() and 1 <= int(parts[1]) <= 65535 and parts[1] != '443' and str(int(parts[1])) == parts[1])

def grant(value, capability):
    fields(value, ['capability_id', 'schema_sha256', 'permissions', 'origins', 'methods', 'namespaces'])
    require(value['capability_id'] == capability['id'] and value['schema_sha256'] == capability['schema_sha256'], 'installed grant binding mismatch')
    permissions = strings(value['permissions'], 1); origins = strings(value['origins'], 32)
    methods = strings(value['methods'], 6); namespaces = strings(value['namespaces'], 32)
    http = capability['id'] == 'network.http.v1'
    require(all(x == ('network.https' if http else 'storage.appPrivate') for x in permissions), 'unsupported installed permission')
    if http:
        require(not namespaces and all(origin(x) for x in origins) and all(x in ['DELETE','GET','HEAD','PATCH','POST','PUT'] for x in methods), 'invalid installed HTTP grant')
    else:
        require(not origins and not methods and all(re.fullmatch(r'[A-Za-z0-9_-]{1,64}', x) for x in namespaces), 'invalid installed storage grant')

def validate_roles(descriptor, records, read_object):
    """Inspect only copied objects, not original paths or independently supplied DTOs."""
    by_pointer = {record['pointer']: record for record in records}
    fixed = ['/engine/ui_contract_sha256', '/engine/capability_contract_sha256',
             '/capability_execution/contract_sha256', '/capability_execution/transport_sha256',
             '/capability_execution/native_header_sha256']
    material_pointers = ['/capability_execution/bridge_policy_sha256']
    for index, cap in enumerate(descriptor['capabilities']):
        fixed.extend([f'/capabilities/{index}/schema_sha256', f'/capabilities/{index}/native_sha256'])
        material_pointers.extend([f'/capabilities/{index}/configuration_sha256', f'/capabilities/{index}/grants_sha256'])
    for pointer in fixed + material_pointers:
        record = by_pointer[pointer]
        require(record['kind'] == 'file' and len(record['files']) == 1, 'schema2 role requires raw-file binding: '+pointer)
        if pointer.endswith('/native_sha256'): require(record['files'][0]['bytes'] > 0, 'native preimage must be nonempty')
    require(len(material_pointers) <= 5, 'material role count limit')
    total, values = 0, {}
    for pointer in material_pointers:
        record = by_pointer[pointer]; size = record['files'][0]['bytes']; total += size
        require(size <= MAX_MATERIAL_FILE and total <= MAX_MATERIAL_TOTAL, 'material byte limit')
        raw = read_object(record['sha256'], MAX_MATERIAL_FILE)
        require(sha(raw) == record['sha256'] and len(raw) == size, 'material copied-byte mismatch')
        values[pointer] = material(raw)
    policy = values[material_pointers[0]]
    fields(policy, ['schema','burst','starts_per_second'])
    require(uint(policy['schema'],1,1) and uint(policy['burst'],1,8) and uint(policy['starts_per_second'],1,32), 'bridge policy bounds')
    for index, cap in enumerate(descriptor['capabilities']):
        prefix = f'/capabilities/{index}/'; config = values[prefix+'configuration_sha256']
        grant(values[prefix+'grants_sha256'], cap)
        if cap['id'] == 'network.http.v1':
            fields(config, ['schema','implementation','maximum_concurrent_requests'])
            require(uint(config['schema'],1,1) and config['implementation'] == 'urlsession-normal-tls-v1' and
                uint(config['maximum_concurrent_requests'],1,8) and config['maximum_concurrent_requests'] == descriptor['capability_execution']['maximum_requests'], 'HTTP configuration binding')
        else:
            fields(config, ['schema','implementation','container','directory_component','maximum_total_bytes','maximum_entries'])
            require(uint(config['schema'],1,1) and config['implementation'] == 'app-private-kv-v1' and
                config['container'] == 'application-private' and type(config['directory_component']) is str and
                re.fullmatch(r'[A-Za-z0-9_-]{1,64}',config['directory_component']) and
                uint(config['maximum_total_bytes'],1,4194304) and uint(config['maximum_entries'],1,1024), 'storage configuration bounds')

def capture(descriptor_path, bindings_path, input_root, output, tool):
    descriptor_bytes = read_path(descriptor_path, MAX_DESCRIPTOR)
    descriptor = decode(descriptor_bytes)
    manifest = decode(read_path(bindings_path, MAX_MANIFEST))
    bindings = validate_bindings(manifest, descriptor)
    output = Path(output).absolute()
    # Exclusive directory creation refuses existing files, links and directories.
    # inputs.json is written last: a partial directory is never a valid capture.
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    root_fd = None
    try:
        original = output / "original-descriptor.json"
        write_new(original, descriptor_bytes)
        inspect_v2(tool, original)
        original.unlink()
        root_fd = open_root(input_root)
        objects = output / "objects"
        objects.mkdir(mode=0o700)
        captured, records, total, object_records = {}, [], 0, {}
        descriptor = copy.deepcopy(descriptor)
        for binding in bindings:
            entries = []
            for entry in binding["files"]:
                source = entry["path"]
                if source not in captured:
                    with tempfile.NamedTemporaryFile(dir=objects, prefix=".copy-", delete=False) as target:
                        temp = Path(target.name)
                        info = stream_file(root_fd, source, min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - total), target)
                        target.flush(); os.fsync(target.fileno())
                    total += info["bytes"]
                    destination = objects / info["sha256"]
                    if destination.exists():
                        temp.unlink()
                    else:
                        os.chmod(temp, 0o400)
                        temp.rename(destination)
                    captured[source] = info
                    object_records[info["sha256"]] = info["bytes"]
                entries.append({"name": entry["name"], **captured[source]})
            if binding["kind"] == "file":
                digest = entries[0]["sha256"]
            else:
                content = canonical({"schema": 1, "files": entries})
                digest = sha(content)
                if digest not in object_records:
                    write_new(objects / digest, content)
                    object_records[digest] = len(content)
            replace_digest(descriptor, binding["pointer"], digest)
            records.append({"pointer": binding["pointer"], "kind": binding["kind"], "sha256": digest, "files": entries})
        checked_fd = open_root(output)
        try:
            validate_roles(descriptor, records, lambda digest, limit: read_file(checked_fd, "objects/"+digest, limit))
        finally:
            os.close(checked_fd)
        encoded = canonical(descriptor)
        require(len(encoded) <= MAX_DESCRIPTOR, "captured descriptor size limit")
        write_new(output / "descriptor.json", encoded)
        fingerprint = inspect_v2(tool, output / "descriptor.json")
        report = {"schema": 2, "identity_schema": 2, "fingerprint": fingerprint, "descriptor_sha256": sha(encoded),
                  "bindings": records, "objects": object_records,
                  "build_attested": False, "complete_graph_proven": False}
        report_bytes = canonical(report)
        require(len(report_bytes) <= MAX_MANIFEST, "capture manifest size limit")
        sync_directory(objects)
        write_new(output / "inputs.json", report_bytes)
        sync_directory(output); sync_directory(output.parent)
        return {"fingerprint": fingerprint, "snapshotSHA256": sha(report_bytes), "objects": len(object_records),
                "sourceBytes": total, "buildAttested": False, "completeGraphProven": False}
    except BaseException:
        # The directory is private and exclusively created by this invocation.
        shutil.rmtree(output)
        raise
    finally:
        if root_fd is not None:
            os.close(root_fd)


def verified_descriptor(snapshot, expected_fingerprint, tool):
    """Return metadata and the exact descriptor bytes validated under one root FD.

    Build adapters must use the returned bytes, not reopen descriptor.json after
    verification. This does not attest that any other build input was consumed.
    """
    require(type(expected_fingerprint) is str and HEX.fullmatch(expected_fingerprint), "expected fingerprint required")
    root_fd = open_root(snapshot)
    try:
        report_bytes = read_file(root_fd, "inputs.json", MAX_MANIFEST)
        report = decode(report_bytes)
        fields(report, ["schema", "identity_schema", "fingerprint", "descriptor_sha256", "bindings", "objects", "build_attested", "complete_graph_proven"])
        require(type(report["schema"]) is int and report["schema"] == 2 and type(report["identity_schema"]) is int and report["identity_schema"] == 2 and
                report["build_attested"] is False and report["complete_graph_proven"] is False,
                "unsupported capture contract")
        require(report["fingerprint"] == expected_fingerprint, "unexpected snapshot identity")
        descriptor_bytes = read_file(root_fd, "descriptor.json", MAX_DESCRIPTOR)
        require(sha(descriptor_bytes) == report["descriptor_sha256"], "descriptor byte hash mismatch")
        descriptor = decode(descriptor_bytes)
        remaining = digest_paths(descriptor)
        require(type(report["objects"]) is dict and len(report["objects"]) <= MAX_FILES + 1024,
                "object inventory limit")
        total = 0
        for digest, size in report["objects"].items():
            require(HEX.fullmatch(digest) and type(size) is int and 0 <= size <= MAX_FILE_BYTES, "invalid object record")
            total += size
            require(total <= MAX_TOTAL_BYTES + MAX_MANIFEST, "snapshot total limit")
            actual = stream_file(root_fd, "objects/" + digest, size)
            require(actual == {"sha256": digest, "bytes": size}, "snapshot object hash mismatch")
        require(type(report["bindings"]) is list and len(report["bindings"]) == len(remaining), "binding coverage mismatch")
        used, count = set(), 0
        for binding in report["bindings"]:
            fields(binding, ["pointer", "kind", "sha256", "files"])
            pointer, digest, entries = binding["pointer"], binding["sha256"], binding["files"]
            require(type(pointer) is str and pointer in remaining and remaining.pop(pointer) == digest,
                    "descriptor binding mismatch")
            require(binding["kind"] in ("file", "collection") and type(entries) is list and
                    (binding["kind"] == "collection" or len(entries) == 1), "invalid captured binding")
            previous = None
            for entry in entries:
                fields(entry, ["name", "sha256", "bytes"])
                relative(entry["name"])
                require(previous is None or previous < entry["name"], "captured names must be sorted and unique")
                previous = entry["name"]
                require(type(entry["sha256"]) is str and entry["sha256"] in report["objects"] and
                        type(entry["bytes"]) is int and report["objects"][entry["sha256"]] == entry["bytes"], "missing captured file")
                used.add(entry["sha256"]); count += 1
                require(count <= MAX_FILES, "captured file count limit")
            expected = entries[0]["sha256"] if binding["kind"] == "file" else sha(canonical({"schema": 1, "files": entries}))
            require(expected == digest and digest in report["objects"], "collection hash mismatch")
            used.add(digest)
        require(not remaining and used == set(report["objects"]), "unbound captured objects")
        # Revalidate the exact in-memory descriptor bytes through the trusted tool;
        # do not let a path replacement between checks select different bytes.
        with tempfile.TemporaryDirectory(prefix="mixer-capture-verify-") as temporary:
            path = Path(temporary) / "descriptor.json"
            write_new(path, descriptor_bytes)
            require(inspect_v2(tool, path) == expected_fingerprint, "runtime fingerprint mismatch")
        validate_roles(descriptor, report["bindings"], lambda digest, limit: read_file(root_fd, "objects/"+digest, limit))
        return ({"fingerprint": expected_fingerprint, "snapshotSHA256": sha(report_bytes),
                 "objects": len(used), "buildAttested": False, "completeGraphProven": False},
                descriptor_bytes)
    finally:
        os.close(root_fd)


def verify(snapshot, expected_fingerprint, tool):
    return verified_descriptor(snapshot, expected_fingerprint, tool)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('capture-v2')
    for flag in ['descriptor','bindings','input-root','output','identity-tool']: create.add_argument('--'+flag, required=True)
    check = sub.add_parser('verify-v2')
    for flag in ['snapshot','expected-fingerprint','identity-tool']: check.add_argument('--'+flag, required=True)
    args = parser.parse_args()
    try:
        result = capture(args.descriptor,args.bindings,args.input_root,args.output,args.identity_tool) if args.command == 'capture-v2' else verify(args.snapshot,args.expected_fingerprint,args.identity_tool)
        print(json.dumps(result,sort_keys=True))
    except (CaptureError,OSError,subprocess.SubprocessError,KeyError,TypeError) as error:
        parser.exit(1,'schema2 capture failed: '+str(error)+'\n')

if __name__ == '__main__': main()
