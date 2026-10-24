#!/usr/bin/env python3
"""Exact measured containing padding, never available credit."""
import json
from run import HERE,enc
layouts=json.loads((HERE/'layouts.json').read_text());assert len(layouts)==16
schema=json.loads((HERE/'inventory-schema.json').read_text());members={cls:{r['field']for r in schema if r['ownerClass']==cls}for cls in ['PermanentPositions','ActivePositions']}
report=[]
for layout in layouts:
 if layout['label']!='candidate':continue
 for cls,size in layout['classes'].items():
  fields=sorted([(name,data)for name,data in layout['fields'].items()if name in members[cls]],key=lambda pair:pair[1]['offset'])
  cursor=0;holes=[];payload=0
  for name,row in fields:
   if row['bytes']==0:continue
   assert row['offset']>=cursor and row['offset']%row['alignment']==0
   if row['offset']>cursor:holes.append(dict(start=cursor,end=row['offset']))
   cursor=row['offset']+row['bytes'];payload+=row['bytes']
  if cursor<size['bytes']:holes.append(dict(start=cursor,end=size['bytes']))
  padding=sum(hole['end']-hole['start']for hole in holes);assert payload+padding==size['bytes']
  report.append(dict(features=layout['features'],profile=layout['profile'],unit=layout['unit'],ownerClass=cls,fields=len(fields),payloadBytes=payload,paddingBytes=padding,containingBytes=size['bytes'],paddingIntervals=holes))
(HERE/'padding.json').write_bytes(enc(report));print('Exact field payload plus every measured padding interval reproduces16 containing layouts')
