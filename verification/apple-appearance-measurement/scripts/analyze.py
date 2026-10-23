#!/usr/bin/env python3
"""Decode native PNG samples exactly; compare same-profile capture pixel data."""
from pathlib import Path
from collections import Counter
import hashlib, json, math, struct, zlib
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent/'apple-appearance-reference'
def png(path):
    data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
    offset=8; compressed=b''; meta=[]
    while offset<len(data):
        n=struct.unpack('>I',data[offset:offset+4])[0];kind=data[offset+4:offset+8];chunk=data[offset+8:offset+8+n];offset+=n+12
        if kind==b'IHDR':
            width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',chunk)
            assert depth==8 and color in (2,6) and compression==0 and filtering==0 and interlace==0
        elif kind==b'IDAT': compressed+=chunk
        elif kind not in (b'IEND',): meta.append(dict(kind=kind.decode('ascii'),bytes=n,sha256=hashlib.sha256(chunk).hexdigest()))
    channels=3 if color==2 else 4;stride=width*channels;raw=zlib.decompress(compressed);out=bytearray(width*height*channels)
    def paeth(a,b,c):
        p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
        return a if pa<=pb and pa<=pc else b if pb<=pc else c
    for y in range(height):
        f=raw[y*(stride+1)];row=raw[y*(stride+1)+1:(y+1)*(stride+1)];base=y*stride
        if f==0:
            out[base:base+stride]=row
        elif f==2:
            prior=out[base-stride:base] if y else bytes(stride)
            out[base:base+stride]=bytes((v+b)&255 for v,b in zip(row,prior))
        else:
            for x,v in enumerate(row):
                a=out[base+x-channels] if x>=channels else 0
                b=out[base-stride+x] if y else 0
                c=out[base-stride+x-channels] if y and x>=channels else 0
                pred=a if f==1 else (a+b)//2 if f==3 else paeth(a,b,c)
                out[base+x]=(v+pred)&255
    return dict(width=width,height=height,channels=channels,pixels=out,metadata=meta)
def compare(a,b):
    assert (a['width'],a['height'],a['channels'])==(b['width'],b['height'],b['channels'])
    ca=a['channels'];count=0;maxdelta=0;box=None
    for i in range(0,len(a['pixels']),ca):
        ap=a['pixels'][i:i+ca];bp=b['pixels'][i:i+ca]
        if ap!=bp:
            count+=1;maxdelta=max(maxdelta,max(abs(x-y) for x,y in zip(ap,bp)))
            pixel=i//ca;x=pixel%a['width'];y=pixel//a['width']
            box=[x,y,x,y] if box is None else [min(box[0],x),min(box[1],y),max(box[2],x),max(box[3],y)]
    return dict(differentPixels=count,totalPixels=a['width']*a['height'],maximumChannelDelta=maxdelta,differenceBoundingBoxPixels=box,
        equalDecodedPixels=count==0)
def crop_samples(image,frame,scale):
    # Only sample measured rectangles; never label a color based on a private view.
    x0=min(image['width'],max(0,int(math.ceil(frame['x']*scale))));y0=min(image['height'],max(0,int(math.ceil(frame['y']*scale))))
    x1=max(0,min(image['width'],int(math.floor((frame['x']+frame['width'])*scale))))
    y1=max(0,min(image['height'],int(math.floor((frame['y']+frame['height'])*scale))))
    counts=Counter();stride=image['width']*image['channels'];c=image['channels']
    for y in range(y0,y1):
        row=image['pixels'][y*stride+x0*c:y*stride+x1*c]
        counts.update(bytes(row[i:i+c]) for i in range(0,len(row),c))
    return dict(rectPixels=dict(x=x0,y=y0,width=max(0,x1-x0),height=max(0,y1-y0)),pixelCount=sum(counts.values()),
        topExactEncodedColors=[dict(rgbHex='#'+pixel[:3].hex().upper(),alpha8=pixel[3] if c==4 else 255,count=n) for pixel,n in counts.most_common(8)])
def main():
    manifest=json.loads((ROOT/'capture-manifest.json').read_text());rows=[];cache={}
    for capture in manifest['captures']:
        name=capture['name'];folder=ROOT/'captures'/name;image=png(folder/'screenshot.png');cache[name]=image
        measurements=json.loads((folder/'measurements.json').read_text());env=json.loads((folder/'environment.json').read_text())
        row=dict(name=name,png=dict(width=image['width'],height=image['height'],channels=image['channels'],metadata=image['metadata'],
            decodedPixelsSHA256=hashlib.sha256(image['pixels']).hexdigest()),
            nodeColorSamples=[dict(id=node['id'],**crop_samples(image,node['frameGlobalPoints'],env['screenScale'])) for node in measurements['nodes']],
            publicUIKitColorSamples=[dict(publicType=node['publicType'],publicSubviewPath=node['publicSubviewPath'],text=node.get('text'),
                **crop_samples(image,node['frameInWindowPoints'],env['screenScale'])) for node in measurements['publicUIKitObservations']
                if node['publicType'] in ['UISwitch','UILabel','UITextField']])
        baseline=BASE/'captures'/name.split('/',1)[1]/'screenshot.png'
        if baseline.exists(): row['historicalUninstrumentedReferenceComparison']=compare(image,png(baseline))
        if name.startswith('release/'):
            debug='debug/'+name.split('/',1)[1]
            row['debugReleasePixelComparison']=compare(image,cache[debug])
            dm=json.loads((ROOT/'captures'/debug/'measurements.json').read_text())
            row['debugReleaseNodeMeasurementsEqual']=measurements['nodes']==dm['nodes']
        rows.append(row)
    result=dict(format='mixer.apple-appearance-pixel-analysis.1',
        scope='Raw decoded PNG encoded channel values, without color-space transformation. No image output/editing or semantic color inference.',captures=rows)
    (ROOT/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    for row in rows:
        hist=row.get('historicalUninstrumentedReferenceComparison');dr=row.get('debugReleasePixelComparison')
        print(row['name'],'historical=',hist['differentPixels'] if hist else 'no prior profile','D/R=',dr['differentPixels'] if dr else '-',
            'node equal=',row.get('debugReleaseNodeMeasurementsEqual','-'))
if __name__=='__main__':main()
