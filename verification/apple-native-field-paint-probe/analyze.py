#!/usr/bin/env python3
"""Read native PNGs using only Python's standard library; never rewrites images."""
import collections
import hashlib
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "evidence"

def read_png(path, required_rows):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    offset = 8
    compressed = bytearray()
    chunks = []
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset+4])[0]
        kind = data[offset+4:offset+8]
        body = data[offset+8:offset+8+length]
        chunks.append(kind.decode("ascii"))
        if kind == b"IHDR":
            width, height, bits, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", body)
            assert bits == 8 and color in (2, 6) and interlace == 0 and compression == filtering == 0
            bpp = 3 if color == 2 else 4
        elif kind == b"IDAT": compressed.extend(body)
        offset += length + 12
    raw = zlib.decompress(compressed)
    stride = width * bpp
    rows = []
    prior = bytearray(stride)
    for y in range(min(height, required_rows)):
        start = y * (stride+1)
        kind = raw[start]
        row = bytearray(raw[start+1:start+1+stride])
        for x in range(stride):
            a = row[x-bpp] if x >= bpp else 0
            b = prior[x]
            c = prior[x-bpp] if x >= bpp else 0
            if kind == 1: predictor = a
            elif kind == 2: predictor = b
            elif kind == 3: predictor = (a+b)//2
            elif kind == 4:
                p = a+b-c
                da, db, dc = abs(p-a), abs(p-b), abs(p-c)
                predictor = a if da <= db and da <= dc else b if db <= dc else c
            else:
                assert kind == 0
                predictor = 0
            row[x] = (row[x]+predictor)&255
        rows.append(row)
        prior = row
    def pixel(x,y): return tuple(rows[y][x*bpp:x*bpp+3])
    return width, height, pixel, chunks

observations = json.loads((OUT / "observations.json").read_text())
by_stage = {x["stage"]: x for x in observations}
assert [x["stage"] for x in observations][:2] == ["discovery", "native-selection"], "Out-of-order harness discovery"
images = {}
for item in observations:
    stage = item["stage"]
    after = item["after"]
    scale = after["scale"]
    width, height, pixel, chunks = read_png(OUT / (stage+".png"), round((after["fieldRectInWindow"][1]+after["fieldRectInWindow"][3])*scale)+1)
    # The selected six whitespace characters make this interior swatch glyph-free.
    # Fixed native geometry across the initial unmarked stages is retained in JSON.
    selected = by_stage["native-selection"]["after"]["selectionRectsInWindow"][0]
    sx = round((selected[0]+selected[2]/2)*scale)
    sy = round((selected[1]+selected[3]/2)*scale)
    swatch = collections.Counter(pixel(x,y) for y in range(sy-5,sy+6) for x in range(sx-5,sx+6))
    fx,fy,fw,fh = after["fieldRectInWindow"]
    counts = collections.Counter(pixel(x,y) for y in range(round(fy*scale),round((fy+fh)*scale))
                                 for x in range(round(fx*scale), min(width,round((fx+fw)*scale))))
    cx,cy,cw,ch = after["cursorRectInWindow"]
    caret_sample = [round((cx+cw/2)*scale), round((cy+ch/2)*scale)]
    images[stage] = {"width":width,"height":height,"pngChunks":chunks,
        "whitespaceSwatchPixelCoordinate":[sx,sy],
        "whitespaceSwatch": [{"rgb":list(k),"count":v} for k,v in swatch.most_common()],
        "fieldRedPixels":sum(v for (r,g,b),v in counts.items() if r>200 and g<80 and b<80),
        "fieldGreenPixels":sum(v for (r,g,b),v in counts.items() if g>200 and r<80 and b<80),
        "caretCenterPixelCoordinate":caret_sample,
        "caretCenterRGB":list(pixel(*caret_sample)),
        "fieldDominantColors":[{"rgb":list(k),"count":v} for k,v in counts.most_common(8)],
        "sha256":hashlib.sha256((OUT/(stage+".png")).read_bytes()).hexdigest()}

retention = {}
for stage in ["install-selection","reactivate-selection","reinstall-selection","restyle-marked","reinstall-marked"]:
    record = by_stage[stage]
    same = ["fieldIdentity","firstResponder","selectedRange","markedRange","text"]
    retention[stage] = {key:record["before"].get(key)==record["after"].get(key) for key in same}
    assert all(retention[stage].values()), (stage, retention[stage])
marked = by_stage["restyle-marked"]["after"]
assert marked["markedText"] == "にほん"
assert marked["firstResponder"]
assert by_stage["commit-marked"]["after"]["text"] == "alphaにほん!      omega"
assert by_stage["delete-native"]["after"]["text"] == "alphaにほん      omega"
assert not by_stage["disable"]["after"]["enabled"]
expected_swatches = {"selection-alpha61":[194,255,194], "selection-alpha128":[127,255,127],
    "selection-clear":[255,255,255], "selection-caret-green":[255,194,194]}
for stage, expected in expected_swatches.items():
    assert images[stage]["whitespaceSwatch"] == [{"rgb":expected,"count":121}], (stage,images[stage])
expected_carets = {"authored-caret":[255,0,0],"caret-alpha61":[255,194,194],
    "caret-alpha128":[255,127,127],"caret-green":[0,255,0],"caret-clear":[255,255,255]}
for stage, expected in expected_carets.items():
    assert images[stage]["caretCenterRGB"] == expected, (stage,images[stage])
for stage in ["install-selection","reactivate-selection"]:
    assert not by_stage[stage]["after"]["cursorInNativeWindow"]
    assert not by_stage[stage]["after"]["highlightInNativeWindow"]
    assert images[stage]["whitespaceSwatch"] == [{"rgb":[204,204,255],"count":121}]
for stage in ["reinstall-selection","authored-caret","selection-alpha61","selection-alpha128","selection-clear"]:
    after=by_stage[stage]["after"]
    assert after["cursorInNativeWindow"] and after["highlightInNativeWindow"]
    assert after["displayTextInputIsField"] and not after["originalHighlightInWindow"]
    assert after["fieldTintRGBA"] == [0,0,1,1]
assert images["disable"]["fieldRedPixels"] == images["disable"]["fieldGreenPixels"] == 0
result = {"imageAnalysis":images, "nativeProgrammaticStateRetention":retention,
    "assertedScope":"Harness ordering; observed replacement/activation failure; observed public reinstall attachment; exact native PNG independent caret/selection alpha and clear swatches; native field identity/focus/range/marked-text retention and programmatic insert/delete",
    "pending":["iOS17 runtime","real keyboard/IME composition and cancellation","secure input","native drag selection/edit menu","accessibility","physical devices","product transaction integration"]}
(OUT / "analysis.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"nativeProgrammaticStateRetention":retention,
    "swatches":{stage:value["whitespaceSwatch"] for stage,value in images.items()}},indent=2))
