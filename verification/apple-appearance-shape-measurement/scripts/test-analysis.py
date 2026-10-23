#!/usr/bin/env python3
"""Executable checks of exact pixel decoding, masks and retained native evidence."""
import importlib.util,json,struct,tempfile,unittest,zlib
from pathlib import Path
from png_reader import png,compare
spec=importlib.util.spec_from_file_location('shape_analysis',Path(__file__).with_name('analyze.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
ROOT=Path(__file__).resolve().parents[1]

class AnalysisTests(unittest.TestCase):
    def test_grayscale_png_decode(self):
        def chunk(kind,payload):return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload))
        b=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',3,2,8,0,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\0\x80\xff\0\xff\x40\0'))+chunk(b'IEND',b'')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.png';p.write_bytes(b);image=png(p)
        self.assertEqual((image['width'],image['height'],image['channels']),(3,2,1))
        self.assertEqual(image['pixels'],bytearray([0,128,255,255,64,0]))
        self.assertEqual(a.frontier(image,0,0,3,2,(0,0,0),(255,255,255)),[1,0])
    def test_rgb_projection_and_runs(self):
        image={'width':5,'height':1,'channels':3,'pixels':bytearray([0,0,0,0,0,0,128,128,128,255,255,255,255,255,255])}
        self.assertEqual(a.frontier(image,0,0,5,1,(0,0,0),(255,255,255)),[2])
        self.assertEqual([r['count'] for r in a.runs(image,0,0,5)],[2,1,2])
        with self.assertRaises(ValueError):a.coverage((1,2,3),(0,0,0),(0,0,0))
    def test_pixel_compare_detects_difference(self):
        image={'width':1,'height':1,'channels':3,'pixels':bytearray([1,2,3])}
        other={**image,'pixels':bytearray([1,2,4])}
        self.assertEqual(compare(image,other)['differentPixels'],1)
        self.assertEqual(compare(image,other)['maximumChannelDelta'],1)
    def test_retained_integrity_and_visible_scope(self):
        data=json.loads((ROOT/'analysis.json').read_text())
        self.assertEqual(len(data['captures']),12)
        self.assertEqual(sum('historicalPixelComparison' in c for c in data['captures']),8)
        for capture in data['captures']:
            self.assertTrue(capture['parentPixelComparison']['equalDecodedPixels'])
            self.assertTrue(capture['parentNodesEqual'])
            self.assertTrue(capture.get('historicalPixelComparison',{'equalDecodedPixels':True})['equalDecodedPixels'])
        self.assertEqual(len(data['switches']),10)
        rtl=[s for s in data['switches'] if '/rtl-large-' in s['name']]
        self.assertEqual(len(rtl),2)
        self.assertTrue(all(s['authoredCandidateThumbRectPoints']['x']==2 for s in rtl))
        for c in data['captures']:
            for group in c['groupedList']:
                for row in group['rows']:
                    native=row['publicCell']
                    self.assertEqual(native['cellLayer']['cornerRadius'],0)
                    self.assertEqual(native['backgroundConfiguration']['cornerRadius'],0)
                    self.assertIsNone(native['backgroundView'])
    def test_candidate_paths_are_closed_and_publicly_labeled(self):
        for folder in ['candidates','path-supplement']:
            for shape in json.loads((ROOT/folder/'candidate-paths.json').read_text())['shapes']:
                self.assertEqual(shape['elements'][-1]['op'],'close')
                self.assertTrue(all(c['op'] in ['move','line','quad','cubic','close'] for c in shape['elements']))
                self.assertIn('authored hypothesis',shape['source'])
                self.assertEqual(shape['pathBounds']['width'],shape['width'])
                self.assertEqual(shape['pathBounds']['height'],shape['height'])
if __name__=='__main__':unittest.main(verbosity=2)
