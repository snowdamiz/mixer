"""Retain official Apple contracts only; no native operations."""
from pathlib import Path
import concurrent.futures,datetime,hashlib,json,sys,urllib.request
BASE=Path(__file__).resolve().parent
SOURCES={
 "should-receive-touch":"https://developer.apple.com/documentation/uikit/uigesturerecognizerdelegate/gesturerecognizer(_:shouldreceive:)-16fuh.md",
 "view-should-begin":"https://developer.apple.com/documentation/uikit/uiview/gesturerecognizershouldbegin(_:).md",
 "delegate-should-begin":"https://developer.apple.com/documentation/uikit/uigesturerecognizerdelegate/gesturerecognizershouldbegin(_:).md",
 "recognizer-location":"https://developer.apple.com/documentation/uikit/uigesturerecognizer/location(in:).md",
 "touch-location":"https://developer.apple.com/documentation/uikit/uitouch/location(in:)-8rd36.md",
 "maximum-touches":"https://developer.apple.com/documentation/uikit/uipangesturerecognizer/maximumnumberoftouches.md"}
def retrieve(entry):
 name,url=entry;data=urllib.request.urlopen(url,timeout=20).read(256001)
 if len(data)>256000:raise ValueError("Official source exceeds bound")
 (BASE/(name+".md")).write_bytes(data)
 return dict(url=url,snapshot=name+".md",sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: rows=list(pool.map(retrieve,SOURCES.items()))
value=dict(argv=[sys.executable,"-B",str(Path(__file__).resolve())],python=sys.version,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),scriptSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),sources=rows)
(BASE/"manifest.json").write_text(json.dumps(value,indent=2)+"\n")
print(json.dumps(dict(sources=len(rows),observedUTC=value["observedUTC"])))
