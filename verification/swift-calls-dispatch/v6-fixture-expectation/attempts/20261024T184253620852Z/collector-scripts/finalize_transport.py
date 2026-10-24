import collect as c
import gzip
p=c.HERE/'inventory-v5.json';raw=p.read_bytes();packed=gzip.compress(raw,mtime=0);assert gzip.decompress(packed)==raw
c.save(p.with_suffix('.json.gz'),packed);c.save(c.HERE/'final-inventory-transport.json',{'logicalPath':'inventory-v5.json','transportPath':'inventory-v5.json.gz','logicalSHA256':c.sha(raw),'logicalBytes':len(raw),'transportSHA256':c.sha(packed),'transportBytes':len(packed),'normalization':'none; exact lossless gzip transport','read':'c.read_json resolves missing .json to exact .json.gz bytes'});p.unlink()
print('Final inventory retained as exact lossless gzip bytes')
