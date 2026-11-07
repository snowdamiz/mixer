// Pure bounded filesystem sealing; no product, compiler or runtime execution.
var fs=await import('node:fs/promises');
var path=await import('node:path');
var crypto=await import('node:crypto');
var root='/Users/andreyyurlov/Documents/dev/mixer/verification/github-delivery-source-pair-and-rebar/ci-review';
var start=Date.now(),limit=45000;
function bound(){if(Date.now()-start>limit)throw new Error('seal deadline');}
function sha(b){return crypto.createHash('sha256').update(b).digest('hex');}
function sorted(v){if(Array.isArray(v))return v.map(sorted);if(v&&typeof v==='object')return Object.fromEntries(Object.keys(v).sort().map(k=>[k,sorted(v[k])]));return v;}
var excluded=['packet-manifest.json','seal-receipt.json'];
var files={},bytes=0;
var entries=(await fs.readdir(root,{recursive:true})).sort();
for(var n of entries){bound();if(excluded.includes(n))continue;var full=path.join(root,n),s=await fs.lstat(full);if(s.isSymbolicLink())throw new Error('link refused '+n);if(s.isDirectory())continue;if(!s.isFile())throw new Error('nonregular '+n);var b=await fs.readFile(full);files[n]={bytes:b.length,sha256:sha(b)};bytes+=b.length;}
var canonical=JSON.stringify(sorted(files));
var manifest={schema:1,source_revision:'8888d8e2c8431ee311c68e94a1abbb280f84802a',source_tree:'4afcac3a7354d7685fa9ebc55292b9871197e24e',scope:'Bounded independent exact8888 CI artifact review; not product or GA acceptance',files:sorted(files),tree_digest_sha256:sha(Buffer.from(canonical)),excluded_self_descriptive_files:excluded};
await fs.writeFile(root+'/packet-manifest.json',JSON.stringify(manifest,null,2)+'\n');
for(var [n,e] of Object.entries(files)){bound();var b=await fs.readFile(path.join(root,n));if(b.length!==e.bytes||sha(b)!==e.sha256)throw new Error('changed after seal '+n);}
var m=await fs.readFile(root+'/packet-manifest.json');
var receipt={schema:1,at:new Date().toISOString(),tool:'mcp__node_repl__js; Node builtin fs/crypto',command:'Execute retained seal.js through node_repl',source_revision:manifest.source_revision,source_tree:manifest.source_tree,source_script:files['seal.js'],maximum_elapsed_ms:limit,elapsed_ms:Date.now()-start,files_rehashed:Object.keys(files).length,total_bytes:bytes,manifest:{path:'packet-manifest.json',bytes:m.length,sha256:sha(m)},tree_digest_sha256:manifest.tree_digest_sha256,excluded_self_descriptive_files:excluded,all_file_bytes_rehashed_after_seal:true,local_product_or_compiler_execution:false,local_child_processes_started:false};
await fs.writeFile(root+'/seal-receipt.json',JSON.stringify(receipt,null,2)+'\n');
nodeRepl.write(receipt);
