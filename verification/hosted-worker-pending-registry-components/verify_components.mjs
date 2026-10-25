// Packet/current-source/compiled-closure integrity only; no OTA authorization.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {resolve,join,dirname,relative} from 'node:path';
const packet=import.meta.dirname,root=resolve(packet,'../..'),candidate=join(packet,'candidate');
const sha=b=>createHash('sha256').update(b).digest('hex');
const json=async p=>JSON.parse(await readFile(p,'utf8'));
const latest=await json(join(packet,'latest-run.json')),run=join(packet,latest.directory),receipt=await json(join(run,'receipt.json')),runtime=await json(join(run,'test-report.json'));
assert.equal(sha(await readFile(join(run,'receipt.json'))),latest.receiptSHA256);assert.equal(receipt.status,'passed');assert.equal(receipt.runtimeGroupsPassed,17);assert.equal(receipt.allOwnedStorageAndProcessesClean,true);assert.equal(receipt.engineIntegration,false);assert.equal(receipt.gaAccepted,false);assert.equal(runtime.results.length,17);assert(runtime.results.every(x=>x.status==='passed'));
const manifest=await json(join(run,'source-manifest.json'));let sources=0;for(const [name,hash] of Object.entries(manifest)){assert.equal(sha(await readFile(join(root,name))),hash,'changed source:'+name);assert.equal(sha(await readFile(join(run,'source',name))),hash,'changed frozen source:'+name);sources++;}
assert.equal(sha(await readFile(join(candidate,'src/public-contract.ts'))),'7bcabae139b5405cfe3856761febb2db69793a9a7cbebba7923a463bfaec2c88');
assert.equal(sha(await readFile(join(root,'docs/hosted-worker-pending-registry-contract.md'))),'5d7ede675cdc83f1a7c000a8bfebf05418e8afe8f99e2c131f22ce52d1f4413a');
assert.equal(sha(await readFile(join(root,'verification/hosted-worker-pending-registry-root-selection/completion-amendment.json'))),'67db5a40f4433699203475d046528600d5939785b0b803b68151febff182e576');
const compiled=await json(join(run,'compiled-manifest.json'));for(const [path,hash] of Object.entries(compiled))assert.equal(sha(await readFile(join(candidate,path))),hash,'compiled changed:'+path);
const require=createRequire(join(root,'hosted-worker-controller/package.json')),ts=require('typescript'),visited=new Set(),externals=new Set(),files=[];
async function visit(path){if(visited.has(path))return;visited.add(path);assert(path.startsWith(join(candidate,'dist/src/')));const bytes=await readFile(path);files.push({path:relative(candidate,path),sha256:sha(bytes),bytes:bytes.length});if(path.endsWith('.sql'))return;
 const tree=ts.createSourceFile(path,bytes.toString('utf8'),ts.ScriptTarget.ES2022,true,ts.ScriptKind.JS),imports=[];function walk(n){if((ts.isImportDeclaration(n)||ts.isExportDeclaration(n))&&n.moduleSpecifier){assert(ts.isStringLiteral(n.moduleSpecifier));imports.push(n.moduleSpecifier.text);}if(ts.isCallExpression(n)&&n.expression.kind===ts.SyntaxKind.ImportKeyword)throw new Error('dynamic_import');ts.forEachChild(n,walk);}walk(tree);for(const id of imports){if(id==='cloudflare:workers')externals.add(id);else if(id.startsWith('.'))await visit(resolve(dirname(path),id));else throw new Error('unselected_dependency:'+id);}}
await visit(join(candidate,'dist/src/pending-registry.js'));await visit(join(candidate,'dist/src/pending-audit.js'));assert.deepEqual([...externals],['cloudflare:workers']);assert.equal(files.length,4);
const coverage=await json(join(packet,'acceptance-coverage.json'));assert.equal(coverage.requiredCases,30);assert.equal(coverage.cases.length,30);assert.equal(new Set(coverage.cases.map(c=>c.id)).size,30);assert.equal(coverage.fullAcceptanceCasesClaimedPassed,0);
const report={status:'passed',scope:'packet-current-source-and-TypeScript-AST-static-component-closure-only',runtimeSourceSHA256:receipt.sourceSHA256,sourceFilesVerified:sources,compiledFilesVerified:Object.keys(compiled).length,productionComponentFiles:files,externalModules:[...externals],testFixtureIncluded:false,otaAuthorization:false,engineIntegration:false,gaAccepted:false};await writeFile(join(packet,'packet-check.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
