"""Proposed closed byte schemas. Synthetic host scaffolding, never a Rust proof.

Canonical JSON is local evidence serialization, not the product's signed CBOR.
No deserializer in this module can create a ValidatedSwiftReactor.
"""
import hashlib
import json

U64 = (1 << 64) - 1
TYPES = ("I32", "I64", "F32", "F64")
IMPORTS = (
    "ArgsGet", "ArgsSizesGet", "EnvironGet", "EnvironSizesGet", "ClockResGet",
    "ClockTimeGet", "FdClose", "FdFdstatGet", "FdFdstatSetFlags", "FdFilestatGet",
    "FdFilestatSetSize", "FdFilestatSetTimes", "FdPread", "FdPrestatGet",
    "FdPrestatDirName", "FdRead", "FdReaddir", "FdSeek", "FdSync", "FdTell",
    "FdWrite", "PathCreateDirectory", "PathFilestatGet", "PathFilestatSetTimes",
    "PathLink", "PathOpen", "PathReadlink", "PathRemoveDirectory", "PathRename",
    "PathSymlink", "PathUnlinkFile", "PollOneoff", "ProcExit", "RandomGet",
)
USAGE = (
    "input_visible_bytes", "source_bytes", "metadata_reserved", "scratch_reserved",
    "metadata_peak_reserved", "scratch_peak_reserved", "total_peak_reserved",
    "work_used", "elapsed_micros", "deadline_ms",
)
OBSERVATIONS = (
    "types", "type_parameters", "imported_functions", "defined_functions",
    "validated_bodies", "instructions", "globals", "exports", "data_segments",
    "element_segments", "max_parameters_plus_locals", "max_operand_values",
    "max_control_depth", "memory_minimum", "memory_declared_maximum",
    "memory_host_maximum", "table_minimum", "table_declared_maximum",
)
BUFFERS = ("signatures", "parameters", "imports", "functions", "globals", "exports", "data", "elements")
RECORD_CAP = 16 * 1024 * 1024


class SchemaError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SchemaError(message)


def keys(value, names):
    require(type(value) is dict and set(value) == set(names), "closed keys")


def uint(value, maximum=U64):
    require(type(value) is int and 0 <= value <= maximum, "unsigned integer")


def digest(value):
    require(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value), "sha256 lowercase hex")


def option_uint(value, maximum=U64):
    if value is not None:
        uint(value, maximum)


def span(value, source_bytes):
    require(type(value) is list and len(value) == 2, "span pair")
    uint(value[0], (1 << 32) - 1)
    uint(value[1], (1 << 32) - 1)
    require(sum(value) <= source_bytes, "span extent")


def _tree(value, depth=0):
    require(depth <= 16, "depth")
    if type(value) is dict:
        for key, item in value.items():
            require(type(key) is str and key and all(c in "abcdefghijklmnopqrstuvwxyz_0123456789" for c in key), "ASCII key")
            _tree(item, depth + 1)
    elif type(value) is list:
        require(len(value) <= 80000, "array cap")
        for item in value:
            _tree(item, depth + 1)
    elif type(value) is str:
        require(len(value) <= 4096 and value.isascii() and all(32 <= ord(c) <= 126 for c in value), "ASCII value")
    elif value is not None:
        uint(value)


def canonical(magic, value):
    require(type(magic) is bytes and len(magic) == 8 and magic.isalnum(), "magic")
    _tree(value)
    result = magic + b"\n" + json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"
    require(len(result) <= RECORD_CAP, "record cap")
    return result


def decode(magic, data):
    require(type(data) is bytes and len(data) <= RECORD_CAP, "record cap")
    require(data.startswith(magic + b"\n") and data.endswith(b"\n"), "framing")
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "duplicate key")
            out[key] = value
        return out
    try:
        value = json.loads(data[9:-1], object_pairs_hook=pairs, parse_float=lambda _: (_ for _ in ()).throw(SchemaError("float")))
    except (UnicodeError, json.JSONDecodeError) as e:
        raise SchemaError("JSON") from e
    require(canonical(magic, value) == data, "canonical encoding")
    return value


def source_manifest(value):
    keys(value, ("schema", "role", "members"))
    require(value["schema"] == 1 and value["role"] in ("baseline", "candidate"), "manifest schema/role")
    require(type(value["members"]) is list and 1 <= len(value["members"]) <= 4096, "member count")
    previous = ""
    for member in value["members"]:
        keys(member, ("path", "bytes", "sha256", "role"))
        path = member["path"]
        require(type(path) is str and path.isascii() and 0 < len(path) <= 4096, "member path")
        require(all(part and part not in (".", "..") and len(part) <= 255 for part in path.split("/")), "relative path components")
        require(not path.startswith("/") and "\\" not in path and "\x00" not in path, "relative path")
        require(path > previous, "unique byte-ordered members")
        previous = path
        uint(member["bytes"], 64 * 1024 * 1024)
        digest(member["sha256"])
        require(member["role"] in ("distribution", "host_support", "patch", "diagnostic"), "source role")
    return canonical(b"MIXSRC01", value)


def snapshot(value):
    keys(value, ("schema", "validator_revision", "decoder_revision", "policy", "source", "metadata", "resolved_imports", "usage", "observations", "provenance"))
    require(value["schema"] == value["validator_revision"] == value["decoder_revision"] == 1, "snapshot version")
    require(value["policy"] == "swift-reactor-experiment-v1", "policy")
    keys(value["source"], ("bytes", "sha256"))
    n = value["source"]["bytes"]
    uint(n, 64 * 1024 * 1024)
    digest(value["source"]["sha256"])
    metadata = value["metadata"]
    keys(metadata, BUFFERS + ("memory", "table", "declarations", "instructions"))
    caps = dict(signatures=512, parameters=8192, imports=34, functions=79966, globals=8192, exports=4096, data=4096, elements=4096)
    for name in BUFFERS:
        buffer = metadata[name]
        keys(buffer, ("capacity", "charged", "category", "items"))
        uint(buffer["capacity"], caps[name])
        uint(buffer["charged"], 16 * 1024 * 1024)
        require(buffer["category"] == "Metadata", "buffer category")
        require(type(buffer["items"]) is list and len(buffer["items"]) <= buffer["capacity"], "buffer length/capacity")
    for item in metadata["signatures"]["items"]:
        keys(item, ("first", "count", "result"))
        uint(item["first"], 8192)
        uint(item["count"], 128)
        require(item["first"] + item["count"] <= len(metadata["parameters"]["items"]), "signature parameters")
        require(item["result"] is None or item["result"] in TYPES, "result type")
    for item in metadata["parameters"]["items"]:
        require(item in TYPES, "parameter type")
    for item in metadata["imports"]["items"]:
        keys(item, ("module", "name", "type_index"))
        span(item["module"], n)
        span(item["name"], n)
        uint(item["type_index"], (1 << 32) - 1)
        require(item["type_index"] < len(metadata["signatures"]["items"]), "import type index")
    for item in metadata["functions"]["items"]:
        keys(item, ("body", "type_index"))
        span(item["body"], n)
        uint(item["type_index"], (1 << 32) - 1)
        require(item["type_index"] < len(metadata["signatures"]["items"]), "function type index")
    for item in metadata["globals"]["items"]:
        keys(item, ("type", "mutable", "initializer"))
        require(item["type"] in TYPES, "global type")
        uint(item["mutable"], 1)
        span(item["initializer"], n)
    for item in metadata["exports"]["items"]:
        keys(item, ("name", "kind", "index"))
        span(item["name"], n)
        uint(item["kind"], 3)
        uint(item["index"], (1 << 32) - 1)
    for name in ("data", "elements"):
        for item in metadata[name]["items"]:
            keys(item, ("payload", "destination", "count"))
            span(item["payload"], n)
            uint(item["destination"], (1 << 32) - 1)
            uint(item["count"], (1 << 32) - 1)
    for name in ("memory", "table"):
        item = metadata[name]
        if item is not None:
            require(type(item) is list and len(item) == 2, "resolved limits")
            for x in item:
                uint(x, (1 << 32) - 1)
            require(item[0] <= item[1], "limits order")
    keys(metadata["declarations"], ("memory_maximum", "table_maximum", "memory_offset", "table_offset"))
    for name in ("memory_maximum", "table_maximum"):
        option_uint(metadata["declarations"][name], (1 << 32) - 1)
    for name in ("memory_offset", "table_offset"):
        uint(metadata["declarations"][name], n)
    uint(metadata["instructions"], 8000000)
    require(type(value["resolved_imports"]) is list and len(value["resolved_imports"]) == 34, "resolved imports length")
    for item in value["resolved_imports"]:
        require(item in IMPORTS, "closed resolved import")
    keys(value["usage"], USAGE)
    for item in value["usage"].values():
        uint(item)
    keys(value["observations"], OBSERVATIONS)
    for name, item in value["observations"].items():
        (option_uint if name.endswith("declared_maximum") else uint)(item)
    o = value["observations"]
    for field, buf in (("types", "signatures"), ("type_parameters", "parameters"), ("imported_functions", "imports"), ("defined_functions", "functions"), ("globals", "globals"), ("exports", "exports"), ("data_segments", "data"), ("element_segments", "elements")):
        require(o[field] == len(metadata[buf]["items"]), "observation count")
    require(o["imported_functions"] == 34 and o["validated_bodies"] == o["defined_functions"], "profile policy counts")
    require(o["instructions"] == metadata["instructions"], "instruction observation")
    keys(value["provenance"], ("schema", "session_sha256", "owner_ordinal", "candidate_manifest_sha256", "validator_binary_sha256", "exporter_source_sha256", "build_receipt_sha256", "validation_budget", "validation_terminal"))
    p = value["provenance"]
    require(p["schema"] == 1 and p["validation_terminal"] == "success", "provenance schema/terminal")
    for name in ("session_sha256", "candidate_manifest_sha256", "validator_binary_sha256", "exporter_source_sha256", "build_receipt_sha256"):
        digest(p[name])
    uint(p["owner_ordinal"])
    keys(p["validation_budget"], ("source_bytes", "metadata_bytes", "scratch_bytes", "work_credits", "deadline_ms"))
    for item in p["validation_budget"].values():
        uint(item)
    return canonical(b"MIXSNB01", value)


def digest_bytes(data):
    return hashlib.sha256(data).digest()


def event_schema(value):
    keys(value, ("schema", "event_magic", "record_bytes", "byte_order", "fields", "enums", "writer_source"))
    require(value["schema"] == 1 and value["byte_order"] == "little", "event schema")
    require(type(value["event_magic"]) is str and len(value["event_magic"]) == 8 and value["event_magic"].isascii(), "event magic")
    uint(value["record_bytes"], 4096)
    require(value["record_bytes"] > 0, "event record extent")
    require(type(value["fields"]) is list and 1 <= len(value["fields"]) <= 256, "event fields")
    end, names = 0, set()
    for field in value["fields"]:
        keys(field, ("name", "offset", "bytes", "kind"))
        require(type(field["name"]) is str and field["name"] not in names, "unique event name")
        names.add(field["name"])
        uint(field["offset"], 4096)
        require(field["bytes"] in (1, 2, 4, 8, 16, 32, 64, 128), "field width")
        require(field["offset"] == end and field["kind"] in ("unsigned", "enum", "flags", "digest", "reserved_zero", "magic"), "complete ordered event layout")
        end += field["bytes"]
    require(end == value["record_bytes"], "complete event extent")
    require(type(value["enums"]) is list and len(value["enums"]) <= 64, "enum tables")
    for table in value["enums"]:
        keys(table, ("field", "values"))
        require(table["field"] in names and type(table["values"]) is list and 1 <= len(table["values"]) <= 256, "enum field")
        previous = -1
        for entry in table["values"]:
            keys(entry, ("value", "name"))
            uint(entry["value"])
            require(entry["value"] > previous and type(entry["name"]) is str, "enum order")
            previous = entry["value"]
    keys(value["writer_source"], ("path", "sha256"))
    digest(value["writer_source"]["sha256"])
    return canonical(b"MIXEVS01", value)


def layout_receipt(value):
    keys(value, ("schema", "target", "rustc_sha256", "rustc_vv_sha256", "configuration", "candidate_manifest_sha256", "adapter_binary_sha256", "type_inventory_sha256", "types", "totals"))
    require(value["schema"] == 1, "layout schema")
    for name in ("target", "configuration"):
        require(type(value[name]) is str and 0 < len(value[name]) <= 512, "layout build label")
    for name in ("rustc_sha256", "rustc_vv_sha256", "candidate_manifest_sha256", "adapter_binary_sha256", "type_inventory_sha256"):
        digest(value[name])
    require(type(value["types"]) is list and 1 <= len(value["types"]) <= 4096, "layout type inventory")
    previous = -1
    for item in value["types"]:
        keys(item, ("id", "name", "bytes", "alignment"))
        uint(item["id"])
        uint(item["bytes"])
        uint(item["alignment"])
        require(item["id"] > previous and item["alignment"] > 0 and item["alignment"] & (item["alignment"] - 1) == 0 and type(item["name"]) is str, "ordered complete type")
        previous = item["id"]
    keys(value["totals"], ("foundation", "constructor_union", "prepared_bound", "headroom", "row_union", "cleanup_union"))
    for item in value["totals"].values():
        uint(item)
    return canonical(b"MIXLAY01", value)
