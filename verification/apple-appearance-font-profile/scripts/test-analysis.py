#!/usr/bin/env python3
"""Known-byte PNG filter/crop checks for the measurement analysis tool."""
from pathlib import Path
import importlib.util, struct, tempfile, unittest, zlib
spec=importlib.util.spec_from_file_location('analysis',Path(__file__).with_name('png.py'))
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)
EXPECTED=bytes([10,20,30,40,50,60,11,22,33,44,55,66])
# Fixed manually calculated PNG filter rows, not an implementation of the decoder.
FILTERED={
 0:([10,20,30,40,50,60],[11,22,33,44,55,66]),
 1:([10,20,30,30,30,30],[11,22,33,33,33,33]),
 2:([10,20,30,40,50,60],[1,2,3,4,5,6]),
 3:([10,20,30,35,40,45],[6,12,18,19,19,20]),
 4:([10,20,30,30,30,30],[1,2,3,4,5,6])}
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
def encoded(filter):
 rows=FILTERED[filter];body=bytes([filter])+bytes(rows[0])+bytes([filter])+bytes(rows[1])
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(body))+chunk(b'IEND',b'')
class AnalysisTests(unittest.TestCase):
 def test_all_five_known_png_filters(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'known.png'
   for f in range(5):
    with self.subTest(filter=f):
     p.write_bytes(encoded(f));self.assertEqual(analysis.png(p)['pixels'],EXPECTED)
 def test_comparison_detects_one_changed_pixel_and_bounds(self):
  a=dict(width=2,height=2,channels=3,pixels=bytearray(EXPECTED));b=dict(a,pixels=bytearray(EXPECTED));b['pixels'][-1]+=2
  r=analysis.compare(a,b);self.assertEqual(r['differentPixels'],1);self.assertEqual(r['maximumChannelDelta'],2)
  self.assertEqual(r['differenceBoundingBoxPixels'],[1,1,1,1]);self.assertFalse(r['equalDecodedPixels'])
 def test_crop_clips_to_real_pixels(self):
  im=dict(width=2,height=2,channels=3,pixels=bytearray(EXPECTED))
  r=analysis.crop_samples(im,dict(x=-2,y=-2,width=3,height=3),1)
  self.assertEqual(r['pixelCount'],1);self.assertEqual(r['topExactEncodedColors'][0]['rgbHex'],'#0A141E')
 def test_no_false_pixels_outside_image(self):
  im=dict(width=2,height=2,channels=3,pixels=bytearray(EXPECTED))
  self.assertEqual(analysis.crop_samples(im,dict(x=0,y=3,width=2,height=2),1)['pixelCount'],0)
  self.assertEqual(analysis.crop_samples(im,dict(x=-3,y=0,width=2,height=2),1)['pixelCount'],0)
if __name__=='__main__':unittest.main()
