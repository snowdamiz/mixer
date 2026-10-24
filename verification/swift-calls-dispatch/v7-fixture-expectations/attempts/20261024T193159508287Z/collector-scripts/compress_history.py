import collect as c
import gzip,json
result={}
for name in ['inventory-v2.json','inventory-v3.json','inventory-v4.json']:
 p=c.HERE/name;data=p.read_bytes();packed=gzip.compress(data,mtime=0);assert gzip.decompress(packed)==data
 dest=p.with_suffix(p.suffix+'.gz');c.save(dest,packed);result[name]={'transport':dest.name,'logicalSHA256':c.sha(data),'logicalBytes':len(data),'gzipSHA256':c.sha(packed),'gzipBytes':len(packed),'normalization':'none; lossless gzip only','restore':'gzip decompression reproduces the exact original bytes'};c.save(c.HERE/'historical-json-transports.json',result);p.unlink()
print('Historical inventories preserved as exact lossless gzip transports')
