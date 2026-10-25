// Build provenance only. This is not an independent review or release gate.
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve,relative,dirname} from 'node:path';
import {createHash} from 'node:crypto';
const require=createRequire(new URL('../../hosted-worker-controller/package.json',import.meta.url));
const ts=require('typescript'),project=resolve(import.meta.dirname,'candidate');
const files=[],externals=new Set(),seen=new Set();
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
async function visit(path){
 if(seen.has(path))return;seen.add(path);
 if(!path.startsWith(resolve(project,'dist/src')+'/'))throw new Error('unexpected_build_closure_path');
 const bytes=await readFile(path);files.push({path:relative(project,path),sha256:sha(bytes),bytes:bytes.length});
 if(path.endsWith('.sql'))return;
 const ast=ts.createSourceFile(path,bytes.toString('utf8'),ts.ScriptTarget.ES2022,true,ts.ScriptKind.JS),imports=[];
 function walk(n){if((ts.isImportDeclaration(n)||ts.isExportDeclaration(n))&&n.moduleSpecifier&&ts.isStringLiteral(n.moduleSpecifier))imports.push(n.moduleSpecifier.text);ts.forEachChild(n,walk);}walk(ast);
 for(const id of imports){if(id==='cloudflare:workers')externals.add(id);else if(id.startsWith('./'))await visit(resolve(dirname(path),id));else throw new Error('unexpected_build_dependency');}
}
await visit(resolve(project,'dist/src/index.js'));files.sort((a,b)=>a.path.localeCompare(b.path));
const result={scope:'compiled reachable production closure provenance only; not independent review, OTA authorization, or deployment gate',files,externals:[...externals],fixturesIncluded:false,digest:sha(JSON.stringify(files))};
await writeFile(resolve(import.meta.dirname,'production-closure.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({files:files.length,digest:result.digest}));
