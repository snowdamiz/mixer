#!/usr/bin/env python3
"""Exact pixels and public native geometry, with explicitly authored shape comparisons."""
from pathlib import Path
from collections import Counter
import hashlib, json, math
from png_reader import png, compare
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT.parent/'apple-appearance-measurement'
BASE=ROOT.parent/'apple-appearance-reference'

def rgb(image,x,y):
    c=image['channels'];i=(y*image['width']+x)*c
    a=tuple(image['pixels'][i:i+c])
    return (a[0],)*3 if c<3 else a[:3]
def hexrgb(v):return '#'+bytes(v).hex().upper()
def runs(image,y,x0,x1):
    result=[];start=x0;previous=rgb(image,x0,y)
    for x in range(x0+1,x1+1):
        current=rgb(image,x,y) if x<x1 else None
        if current!=previous:
            result.append({'fromPixel':start,'throughPixel':x-1,'count':x-start,'rgb':hexrgb(previous)})
            start=x;previous=current
    return result
def coverage(value,background,foreground):
    delta=[f-b for b,f in zip(background,foreground)]
    den=sum(d*d for d in delta)
    if not den:raise ValueError('Palette cannot identify coverage')
    return sum((v-b)*d for v,b,d in zip(value,background,delta))/den
def frontier(image,x,y,width,height,background,foreground,threshold=.5):
    rows=[]
    for dy in range(height):
        hit=next((dx for dx in range(width) if coverage(rgb(image,x+dx,y+dy),background,foreground)>=threshold),None)
        rows.append(hit)
    return rows
def frontier_comparison(native,candidate):
    deltas=[a-b for a,b in zip(native,candidate) if a is not None and b is not None]
    return {'nativeFirstHalfCoverageXPixelByRow':native,'candidateFirstHalfCoverageXPixelByRow':candidate,
        'matchingRows':sum(a==b for a,b in zip(native,candidate)), 'rows':len(native),
        'maximumAbsoluteFrontierDifferencePixels':max(map(abs,deltas),default=0),
        'meanAbsoluteFrontierDifferencePixels':sum(map(abs,deltas))/len(deltas) if deltas else None}

def switch_frontier(image,x,y,width,height,background,foreground,mirror=False,minimums=None):
    rows=[]
    for dy in range(height):
        start=minimums[dy] if minimums else 0
        hit=next((dx for dx in range(start,width) if coverage(rgb(image,x+(width-1-dx if mirror else dx),y+dy),background,foreground)>=.5),None)
        rows.append(hit)
    return rows

def main():
    allrows=[];switches=[];group_contours=[]
    track=png(ROOT/'candidates/track-continuous-r14.png')
    thumb=png(ROOT/'candidates/thumb-continuous-r12.png')
    group=png(ROOT/'candidates/group-continuous-r26.png')
    for entry in json.loads((ROOT/'capture-manifest.json').read_text())['captures']:
        name=entry['name'];folder=ROOT/'captures'/name
        image=png(folder/'screenshot.png');m=json.loads((folder/'measurements.json').read_text())
        env=json.loads((folder/'environment.json').read_text());scale=env['screenScale'];assert scale==3
        doc=json.loads((folder/'rendered-document.json').read_text());sections=doc['root']['children'][0]['children']
        nodes={n['id']:n for n in m['nodes']}
        collection=next(n for n in m['publicUIKitObservations'] if n['publicType']=='UICollectionView')
        cells=collection['shapeProbe']['cells'];bysection={}
        for cell in cells:bysection.setdefault(cell['section'],[]).append(cell)
        listnode=next(n for n in m['nodes'] if n['kind']=='list')['frameGlobalPoints']
        canvas=(0,0,0) if name.endswith('dark') else (242,242,247)
        surface=(28,28,30) if name.endswith('dark') else (255,255,255)
        measured=[];previous_bottom=None
        for index,section_cells in sorted(bysection.items()):
            s=sections[index];header=nodes[s['id']+'.header']['frameGlobalPoints']
            first=section_cells[0]['frameInWindowPoints'];last=section_cells[-1]['frameInWindowPoints']
            bottom=last['y']+last['height'];rowrecords=[]
            for cell in section_cells:
                row=s['children'][cell['item']];node=nodes.get(row['id']);frame=cell['frameInWindowPoints']
                r={'id':row['id'],'kind':row['kind'],'publicCell':cell,'nativeNode':node}
                if node:
                    n=node['frameGlobalPoints'];r['contentGeometryRelativeToCell']={
                        'left':n['x']-frame['x'],'right':frame['x']+frame['width']-n['x']-n['width'],
                        'top':n['y']-frame['y'],'bottom':frame['y']+frame['height']-n['y']-n['height'],
                        'rowHeightMinusContentHeight':frame['height']-n['height']}
                visible_boundary=frame['y']+frame['height']<=min(listnode['y']+listnode['height'],image['height']/scale)
                if cell['item']<len(s['children'])-1 and visible_boundary:
                    x=round(frame['x']*scale);endx=round((frame['x']+frame['width'])*scale);end=round((frame['y']+frame['height'])*scale)
                    scans=[]
                    for y in range(end-3,end+2):
                        if y<image['height']:
                            scans.append({'yPixel':y,'relativeToCellBottomPixel':y-end,'runs':runs(image,y,x,endx)})
                    r['separatorBoundaryRawScanlines']=scans
                elif cell['item']<len(s['children'])-1:
                    r['separatorBoundaryNotSampled']='cell boundary below native List viewport; no visible paint assertion'
                rowrecords.append(r)
            measured.append({'sectionID':s['id'],'headerFrame':header,'firstCellY':first['y'],
                'lastObservedCellBottom':bottom,'allSectionCellsObserved':len(section_cells)==len(s['children']),
                'listTopToFirstHeaderTop' :header['y']-listnode['y'] if index==0 else None,
                'previousGroupBottomToHeaderTop':header['y']-previous_bottom if previous_bottom is not None else None,
                'headerBottomToFirstCellTop':first['y']-header['y']-header['height'],
                'previousGroupBottomToFirstCellTop':first['y']-previous_bottom if previous_bottom is not None else None,
                'rows':rowrecords})
            previous_bottom=bottom
            # First group corner: top-left scanline frontiers. No inference of native paths.
            if index==0:
                x,y=round(first['x']*3),round(first['y']*3)
                native=frontier(image,x,y,140,100,canvas,surface)
                candidate=frontier(group,0,0,140,100,(0,0,0),(255,255,255))
                contour={'name':name,'sectionID':s['id'],'halfCoverageMethod':'least-squares encoded RGB interpolation of canvas/surface; threshold0.5, not physical alpha',
                    'candidate':'authored public SwiftUI continuous r26; not native geometry',**frontier_comparison(native,candidate)}
                if (ROOT/'path-supplement').exists():
                    h=first['height']
                    candidate_name='cell52-continuous-r26' if abs(h-52)<.01 else 'cell63third-continuous-r26' if abs(h-(63+2/3))<.01 else 'cell101-continuous-r26' if abs(h-101)<.01 else None
                    if candidate_name:
                        candidate_image=png(ROOT/'path-supplement'/f'{candidate_name}.png')
                        contour['cellHeightConstrainedCandidate']=dict(name=candidate_name,**frontier_comparison(native,frontier(candidate_image,0,0,140,100,(0,0,0),(255,255,255))))
                group_contours.append(contour)
        original=BASE/'captures'/name.split('/',1)[1]/'screenshot.png'
        row={'name':name,'sourcePNG':str((folder/'screenshot.png').relative_to(ROOT)),
            'pngSHA256':hashlib.sha256((folder/'screenshot.png').read_bytes()).hexdigest(),
            'decodedPixelsSHA256':hashlib.sha256(image['pixels']).hexdigest(),
            'parentPixelComparison':compare(image,png(PARENT/'captures'/name/'screenshot.png')),
            'parentNodesEqual':m['nodes']==json.loads((PARENT/'captures'/name/'measurements.json').read_text())['nodes'],
            'groupedList':measured}
        if original.exists():row['historicalPixelComparison']=compare(image,png(original))
        allrows.append(row)
        for switch in [n for n in m['publicUIKitObservations'] if n['publicType']=='UISwitch']:
            f=switch['frameInWindowPoints'];x,y=round(f['x']*3),round(f['y']*3)
            # Skip controls below the native List viewport. Public objects may remain present.
            viewport_bottom=min(listnode['y']+listnode['height'],image['height']/3)
            if f['y']<listnode['y'] or f['y']+f['height']>viewport_bottom:continue
            on=switch['isOn'];enabled=switch['isEnabled'];dark=name.endswith('dark')
            trackcolor=(38,119,59) if dark and not enabled else (153,227,172) if not enabled else (48,209,88) if dark and on else (52,199,89) if on else (90,90,94) if dark else (197,197,199)
            thumbcolor=(142,142,143) if dark and not enabled else (255,255,255)
            thumbx=24 if on != (env['swiftUILayoutDirection']=='rightToLeft') else 2
            # Mirror samples to the side opposite the thumb. This avoids sampling
            # the thumb as track and does not claim a native shape path.
            if thumbx==2:
                ntrack=switch_frontier(image,x,y,189,84,surface,trackcolor,mirror=True)
                ntrack=[a if a is None or a<72 else None for a in ntrack]
            else:ntrack=frontier(image,x,y,72,84,surface,trackcolor)
            ctrack=frontier(track,0,0,72,84,(0,0,0),(255,255,255))
            # White canvas and white thumb are indistinguishable outside the
            # track. Exclude the candidate outer-edge neighborhood explicitly;
            # do not turn those pixels into a false thumb boundary.
            track_edge=frontier(track,0,0,189,84,(0,0,0),(255,255,255))
            minimums=[max(0,(track_edge[dy+6] or 0)-thumbx*3+2) for dy in range(72)]
            nthumb=switch_frontier(image,x+thumbx*3,y+6,111,72,trackcolor,thumbcolor,minimums=minimums)
            cthumb=frontier(thumb,0,0,111,72,(0,0,0),(255,255,255))
            scans=[{'relativeYPixel':dy,'runs':runs(image,y+dy,x,x+189)} for dy in [0,1,2,3,6,7,12,21,36,42,62,71,76,77,78,80,82,83]]
            switches.append({'name':name,'publicSwitch':switch,'rawScanlines':scans,'trackInteriorRGBObservedPalette':hexrgb(trackcolor),
                'thumbInteriorRGBObservedPalette':hexrgb(thumbcolor),'authoredCandidateThumbRectPoints':{'x':thumbx,'y':2,'width':37,'height':24},
                'trackLeftFrontierComparison':frontier_comparison(ntrack,ctrack),
                'thumbLeftFrontierComparison':frontier_comparison(nthumb,cthumb),
                'coverageLimit':'Encoded RGB projection at0.5 is an analysis threshold, not native alpha/path. Track is sampled on opposite-thumb side; thumb sampling explicitly excludes outer-track neighborhood using candidate mask. Thumb rectangle remains authored hypothesis.'})
    result={'format':'mixer.apple-appearance-shape-analysis.1','scope':'Public properties, exact RGB scanlines and explicitly authored candidate comparisons; no parity or acceptance',
        'captures':allrows,'groupCornerComparisons':group_contours,'switches':switches}
    (ROOT/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    assert all(r['parentPixelComparison']['equalDecodedPixels'] and r['parentNodesEqual'] for r in allrows)
    assert all(r.get('historicalPixelComparison',{'equalDecodedPixels':True})['equalDecodedPixels'] for r in allrows)
    print('PASS',len(allrows),'parent pixel/node comparisons;',sum('historicalPixelComparison' in r for r in allrows),'historical exact pixel comparisons;',len(switches),'fully visible switches')
    for x in group_contours:print('group',x['name'],x['matchingRows'],'/',x['rows'],'max frontier delta',x['maximumAbsoluteFrontierDifferencePixels'])
    for x in switches:print('switch',x['name'],x['publicSwitch']['isOn'],x['publicSwitch']['isEnabled'],'track',x['trackLeftFrontierComparison']['maximumAbsoluteFrontierDifferencePixels'],'thumb',x['thumbLeftFrontierComparison']['maximumAbsoluteFrontierDifferencePixels'])
if __name__=='__main__':main()
