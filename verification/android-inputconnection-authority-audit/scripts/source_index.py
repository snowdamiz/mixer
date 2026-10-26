#!/usr/bin/env python3
"""Frozen navigation spans, never a native-behavior oracle."""
from pathlib import Path
import hashlib,json
O=Path(__file__).resolve().parents[1]
ranges={
'inputs/native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java':[(50,90),(184,220),(715,786)],
'inputs/native/android/app/src/dev/mixer/android/NativeRenderer.java':[(112,128),(214,254),(291,343),(356,416),(462,519)],
'inputs/native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java':[(31,44),(53,122),(201,229)],
'inputs/native/android/app/src/dev/mixer/android/NativeOwnerV2.java':[(177,198),(212,228)],
'inputs/native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java':[(75,104)],
'inputs/native/android/tests/NativeOwnerV2ConcreteHostTests.java':[(458,485),(488,545),(575,581)],
'inputs/native/android/tests/NativeOwnerV2ConcreteHostLeaves/android/view/inputmethod/BaseInputConnection.java':[(1,30)],
'official/aosp36/InputConnectionWrapper.java':[(39,83),(90,135),(252,316),(355,396),(412,455)],
'official/aosp36/EditableInputConnection.java':[(69,132),(151,207),(215,294)],
'official/aosp36/BaseInputConnection.java':[(195,208),(514,685),(725,735),(819,829),(905,981),(1011,1044),(1084,1110)],
'official/aosp36/InputConnection.java':[(379,405),(1007,1009),(1257,1263),(1291,1298),(1314,1328),(1418,1422),(1449,1470)],
'official/aosp36/TextView.java':[(10078,10134),(10186,10206),(10296,10307),(10362,10367)],
'official/aosp36/Editor.java':[(1848,1910),(2025,2072),(4930,4964)],
'official/aosp36/SpellChecker.java':[(219,227),(470,537)]}
spans=[]
for rel,rs in ranges.items():
 lines=(O/rel).read_text().splitlines(keepends=True)
 for start,end in rs:
  end=min(end,len(lines));b=''.join(lines[start-1:end]).encode()
  spans.append({'path':rel,'start':start,'end':end,'sha256':hashlib.sha256(b).hexdigest()})
(O/'source-index.json').write_text(json.dumps({'scope':'Frozen navigation only; not native proof','spans':spans},indent=2)+'\n')
print('Indexed frozen source spans='+str(len(spans)))
