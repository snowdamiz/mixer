"""Unselected finite byte grammar. A matching context never grants authority."""
import hashlib
import struct

U64 = (1 << 64) - 1
PARTITIONS = ((0, 4096), (4096, 2048), (6144, 2048))
DIGESTS = (
    "baseline_manifest", "candidate_manifest", "event_schema", "adapter_binary",
    "layout_receipt", "snapshot", "original_input", "row_body", "transport",
    "final_profile", "stream", "session", "build_receipt", "typed_result_schema",
    "custody_schema", "code_applicability",
)
RUN_BUDGET = ("source_bytes", "metadata_bytes", "cache_bytes", "cache_entry_bytes", "cache_entries", "active_pins", "cache_work", "frames", "values", "controls", "memory_pages", "state_bytes", "combined_bytes", "instruction_fuel", "execution_work", "host_calls", "deadline_ms")
VALIDATION_BUDGET = ("source_bytes", "metadata_bytes", "scratch_bytes", "work_credits", "deadline_ms")
WASI_BUDGET = ("calls", "transfer_bytes", "work", "one_transfer_bytes", "iovecs", "log_bytes", "deadline_ms")
GRANTS = ("secure_random", "realtime", "monotonic", "stdout", "stderr")

class Refusal(ValueError):
    pass

def need(value, detail):
    if not value:
        raise Refusal(detail)

def u64(value):
    need(type(value) is int and 0 <= value <= U64, "u64")
    return struct.pack("<Q", value)

def word(data, index):
    return struct.unpack_from("<Q", data, index * 8)[0]

def blank_selection():
    """Synthetic framing fixture, not a selected build/session."""
    out = bytearray(4096)
    out[:8] = b"MIXSEL01"
    values = (1,4096,8192,4096,2048,6144,2048,1,1,1,17,5,0,0,0)
    for i, value in enumerate(values, 1):
        out[i*8:i*8+8] = u64(value)
    for i, name in enumerate(DIGESTS):
        out[128+i*32:160+i*32] = hashlib.sha256(name.encode()).digest()
    # Complete explicit budgets; zeros are exhausted, never default inference.
    # Target bytes are counted and padded, with no NUL terminator requirement.
    target = b"aarch64-apple-darwin"
    out[112:120] = u64(len(target))
    out[912:912+len(target)] = target
    # extent/type/slot/pin/nonce/B/capacity/entry/record-cap/mask
    for i, value in enumerate((64,1,1,1,1,0,1,1,1,33)):
        out[1040+i*8:1048+i*8] = u64(value)
    return bytes(out)

def blank_result():
    out=bytearray(2048)
    out[:8]=b"MIXRES01"
    for i,value in ((1,1),(2,2048),(3,1)):
        out[i*8:i*8+8]=u64(value)
    return bytes(out)

def blank_custody():
    out=bytearray(2048)
    out[:8]=b"MIXCST01"
    for i,value in ((1,1),(2,2048),(3,1),(4,1),(5,1)):
        out[i*8:i*8+8]=u64(value)
    for i in range(8):
        out[64+i*32:96+i*32]=hashlib.sha256(bytes((i,))).digest()
    return bytes(out)

def check_selection(s):
    need(len(s)==4096 and s[:8]==b"MIXSEL01", "selection extent/magic")
    expected={1:1,2:4096,3:8192,4:4096,5:2048,6:6144,7:2048,8:1,9:1,10:1,11:17,12:5,15:0}
    need(all(word(s,i)==v for i,v in expected.items()), "selection versions/offsets/counts/reserved")
    n=word(s,14)
    need(1<=n<=128 and all(32<=c<=126 for c in s[912:912+n]) and not any(s[912+n:1040]), "target extent/ASCII/padding")
    # Width checks correspond to actual source u32 fields, without truncation.
    for offset in (720,840,848,856):  # run.memory_pages, WASI one_transfer/iovecs/log
        need(struct.unpack_from("<Q",s,offset)[0] <= (1<<32)-1, "u32 budget")
    need(all(struct.unpack_from("<Q",s,872+i*8)[0] in (0,1) for i in range(5)), "grant bool")
    need(word(s,13) in (0,1), "WASI budget presence")
    if word(s,13)==0:
        need(not any(s[816:912]), "absent WASI budget/grants")
    p=[struct.unpack_from("<Q",s,1040+i*8)[0] for i in range(10)]
    need(p[0]!=U64 and p[1] <= (1<<32)-1 and 1<=p[2]<=64 and 1<=p[3]<=64 and p[4]==1, "profile scalar domain")
    need(p[5]<=p[6] and all(v!=U64 for v in p[5:8]) and 1<=p[8]<=4194304 and p[9]<64 and p[9]&33==33, "profile capacity/cap/mask")
    need(not any(s[1120:]), "selection tail reserved")

def check_result(r):
    need(len(r)==2048 and r[:8]==b"MIXRES01", "result extent/magic")
    need([word(r,i) for i in (1,2,3)]==[1,2048,1], "result version/variant schema")
    mask=word(r,4)
    need(mask<=7 and (not mask&2 or mask&1), "result option masks")
    need(word(r,5)<=8, "original constructor tag")
    need(not any(r[224:256]), "result header reserved")
    # Metadata is separately validated by the Rust data codec. This framing
    # control only enforces absent payloads; it never claims applicability.
    if not mask&1:
        need(not any(r[256:1024]), "absent failure and at_failure")
    if not mask&2:
        need(not any(r[1024:1536]), "absent after_cleanup")
    if not mask&4:
        need(not any(r[1536:2048]), "absent final consumption")
    need(word(r,5)!=0 or (word(r,7)==0 and not any(r[96:128])), "absent constructor receipt")

def check_custody(c):
    need(len(c)==2048 and c[:8]==b"MIXCST01", "custody extent/magic")
    need([word(c,i) for i in (1,2,3)]==[1,2048,1], "custody version/scope")
    need(1<=word(c,4)<=32 and 0<word(c,5)<=65536 and word(c,6)<=32 and word(c,7)==0, "custody counts/receipt cap/reserved")
    need(not any(c[320:]), "custody tail reserved")

def observe_framing(raw):
    need(type(raw) is bytes and len(raw)==8192, "exact context extent")
    selection,result,custody=(raw[o:o+n] for o,n in PARTITIONS)
    check_selection(selection)
    check_result(result)
    check_custody(custody)
    return {"data_framing_observed":True,"real_binding_verified":False,"stored_prefix_validated":False,"semantic_metrics_valid":False,"full_replay_accepted":False}

def digest_join(artifacts, expected):
    need(type(artifacts) is dict and type(expected) is dict and set(artifacts)==set(DIGESTS)==set(expected), "closed digest names")
    for name in DIGESTS:
        need(type(artifacts[name]) is bytes and type(expected[name]) is bytes and len(expected[name])==32, "digest input types")
        need(hashlib.sha256(artifacts[name]).digest()==expected[name], "digest mismatch:"+name)
    return {"byte_digest_join_observed":True,"producer_provenance_verified":False}
