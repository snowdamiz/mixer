"""Read retained PNG encoded RGB samples; no image output or native shape inference."""
from pathlib import Path
import importlib.util,json,hashlib
REPO=Path(__file__).resolve().parents[2];root=REPO/'verification/apple-appearance-measurement'
spec=importlib.util.spec_from_file_location('png_reader',root/'scripts/analyze.py');decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
rows=[]
for scheme in ['light','dark']:
 folder=root/'captures/debug'/f'controls-{scheme}'
 file=folder/'screenshot.png';raster=decoder.png(file);data=raster['pixels'];c=raster['channels'];w=raster['width'];m=json.loads((folder/'measurements.json').read_text())
 def pixel(x,y):return '#'+bytes(data[(y*w+x)*c:(y*w+x)*c+3]).hex().upper()
 for view in m['publicUIKitObservations']:
  if view['publicType']!='UISwitch':continue
  frame=view['frameInWindowPoints'];x,y,width,height=[round(frame[k]*3) for k in ['x','y','width','height']]
  scan=[]
  for dy in [0,1,2,3,5,6,12,21,42,62,77,80,81,82,83]:
   colors=[];start=0;prior=pixel(x,y+dy)
   for dx in range(1,width+1):
    current=pixel(x+dx,y+dy) if dx<width else None
    if current!=prior:
     colors.append({'from_px':start,'through_px':dx-1,'rgb':prior});start=dx;prior=current
   scan.append({'relative_y_px':dy,'runs':colors})
  rows.append({'scheme':scheme,'isOn':view['isOn'],'isEnabled':view['isEnabled'],'frame':frame,'scanlines':scan,'image_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
result={'scope':'Encoded screenshot scanlines within public switch outer bounds. Native track/thumb paths and final shared geometry are not inferred or approved by this probe.','captures':rows}
(Path(__file__).parent/'switch-scanlines.json').write_text(json.dumps(result,indent=2)+'\n')
print('Recorded',len(rows),'switches and',sum(len(r['scanlines']) for r in rows),'bounded scanlines')
