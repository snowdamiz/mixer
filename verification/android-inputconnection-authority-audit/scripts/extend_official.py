#!/usr/bin/env python3
from pathlib import Path
import base64,hashlib,json,urllib.request
O=Path(__file__).resolve().parents[1]
p='core/java/android/widget/SpellChecker.java'
url='https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/'+p+'?format=TEXT'
r=urllib.request.urlopen(url,timeout=45);data=base64.b64decode(r.read())
dest=O/'official/aosp36/SpellChecker.java';dest.write_bytes(data)
c=json.loads((O/'collection.json').read_text())
c['official'].append({'source':url,'path':str(dest.relative_to(O)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'status':r.status})
(O/'collection.json').write_text(json.dumps(c,indent=2)+'\n')
print(json.dumps(c['official'][-1],indent=2))
