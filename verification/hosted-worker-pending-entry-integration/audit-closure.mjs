import {createRequire} from 'node:module';
import {readFile,writeFile,readdir} from 'node:fs/promises';
import {resolve,dirname,relative} from 'node:path';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const require=createRequire(new URL('../../hosted-worker-controller/package.json',import.meta.url)),ts=require('typescript');
const own=import.meta.dirname,project=resolve(own,'candidate'),seen=new Set(),files=[],externals=new Set();
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
async function visit(path){if(seen.has(path))return;seen.add(path);assert(path.startsWith(resolve(project,'dist/src')+'/'));const bytes=await readFile(path);files.push({path:relative(project,path),sha256:sha(bytes),bytes:bytes.length});if(path.endsWith('.sql'))return;const ast=ts.createSourceFile(path,bytes.toString('utf8'),ts.ScriptTarget.ES2022,true,ts.ScriptKind.JS);const imports=[];function walk(n){if((ts.isImportDeclaration(n)||ts.isExportDeclaration(n))&&n.moduleSpecifier){assert(ts.isStringLiteral(n.moduleSpecifier));imports.push(n.moduleSpecifier.text);}if(ts.isCallExpression(n)&&n.expression.kind===ts.SyntaxKind.ImportKeyword)throw new Error('dynamic_import');ts.forEachChild(n,walk);}walk(ast);for(const id of imports){if(id==='cloudflare:workers')externals.add(id);else{assert(id.startsWith('./'));await visit(resolve(dirname(path),id));}}}
await visit(resolve(project,'dist/src/index.js'));
const operation=ts.createSourceFile('operation.js',await readFile(resolve(project,'dist/src/operation.js'),'utf8'),ts.ScriptTarget.ES2022,true,ts.ScriptKind.JS);
const cls=operation.statements.find(n=>ts.isClassDeclaration(n)&&n.name.text==='MixerWorkerOperation');assert(cls);
const methods=cls.members.filter(ts.isMethodDeclaration).map(n=>n.name.text);assert.deepEqual(methods,['fetch','recoverKnown','enrollExisting','alarm']);assert(cls.members.some(n=>ts.isPropertyDeclaration(n)&&ts.isPrivateIdentifier(n.name)&&n.name.text==='#state'));
for(const name of ['engine.ts','registry-context.ts'])assert.equal(await readFile(resolve(project,'src',name),'utf8'),(await readFile(resolve(own,'../hosted-worker-pending-migration-outbox/candidate/src',name),'utf8')).replaceAll('./vendor/','./'));
for(const name of ['ledger.ts','schema.sql'])assert.equal(await readFile(resolve(project,'src',name),'utf8'),await readFile(resolve(own,'../hosted-worker-pending-migration-outbox/candidate/src',name),'utf8'));
for(const name of ['pending-types.ts','pending-registry.ts','pending-audit.ts','public-contract.ts','registry-schema.sql','wire.ts','clock.ts','provider.ts','principal.ts'])assert.equal(await readFile(resolve(project,'src',name),'utf8'),await readFile(resolve(own,'../../hosted-worker-controller/src',name),'utf8'));
const report={status:'passed',scope:'TypeScript AST static production closure; not an OTA authorization or deployment gate',files:files.sort((a,b)=>a.path.localeCompare(b.path)),externals:[...externals],operationRPCMethods:methods,operationStateJavaScriptPrivate:true,fixturesIncluded:false,acceptedEngineBehaviorBytesChanged:false,acceptedEngineVendorImportsRewired:true,liveRegistryComponentBytesChanged:false};
await writeFile(resolve(own,'production-closure.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:'passed',files:files.length,operationRPCMethods:methods}));
