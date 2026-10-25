// Independent static review supports local source acceptance only, never OTA authority.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve,join,dirname} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const out=process.env.MIXER_V2_RUN_DIR,binding=JSON.parse(await readFile(join(out,'bindings.json'),'utf8')),project=join(binding.scratch,'hosted-worker-controller');
const {default:ts}=await import(pathToFileURL(join(project,'node_modules/typescript/lib/typescript.js')));
const bytesHash=b=>createHash('sha256').update(b).digest('hex');
const seen=new Set(),files=[],externals=new Set();
async function walkModule(path){
 if(seen.has(path))return;seen.add(path);assert(path.startsWith(join(project,'dist/src/')));const bytes=await readFile(path);files.push({path:path.slice(project.length+1),bytes:bytes.length,sha256:bytesHash(bytes)});
 const source=bytes.toString();assert(!source.includes('allowUnconfirmed'));if(path.endsWith('.sql')){assert(!source.includes('test_'));return;}
 const ast=ts.createSourceFile(path,source,ts.ScriptTarget.ES2022,true,ts.ScriptKind.JS),imports=[];
 function walk(node){
  if(ts.isCallExpression(node)){assert(node.expression.kind!==ts.SyntaxKind.ImportKeyword);assert(!(ts.isIdentifier(node.expression)&&['require','eval','Function'].includes(node.expression.text)));}
  if(ts.isNewExpression(node))assert(!(ts.isIdentifier(node.expression)&&node.expression.text==='Function'));
  if((ts.isImportDeclaration(node)||ts.isExportDeclaration(node))&&node.moduleSpecifier){assert(ts.isStringLiteral(node.moduleSpecifier));imports.push(node.moduleSpecifier.text);}
  if(ts.isStringLiteral(node)){for(const forbidden of ['__test','synthetic-verification','MIXER_CONTROLLER_TEST_REPORT','test_settings','test_calls','schema1Fixture','claimIdentityFixture'])assert(!node.text.includes(forbidden));}
  ts.forEachChild(node,walk);
 }walk(ast);
 for(const name of imports){if(name==='cloudflare:workers')externals.add(name);else {assert(name.startsWith('.'));await walkModule(resolve(dirname(path),name));}}
}
await walkModule(join(project,'dist/src/index.js'));assert.equal(files.length,9);assert.deepEqual([...externals],['cloudflare:workers']);
const engineBytes=await readFile(join(project,'src/engine.ts')),engine=ts.createSourceFile('engine.ts',engineBytes.toString(),ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
const klass=engine.statements.find(n=>ts.isClassDeclaration(n)&&n.name.text==='Engine'),methods=new Map(klass.members.filter(ts.isMethodDeclaration).map(n=>[n.name.getText(engine),n]));
const claim=methods.get('claim'),finalReturn=claim.body.statements.at(-1);assert(ts.isReturnStatement(finalReturn));assert.equal(finalReturn.expression.expression.getText(engine),'this.ledger.transaction');
let finalAwaits=0,transactionCallbacks=0,acceptSites=[];
function all(node,fn){fn(node);ts.forEachChild(node,n=>all(n,fn));}
all(finalReturn,n=>{if(ts.isAwaitExpression(n))finalAwaits++;});assert.equal(finalAwaits,0);
for(const [method,node]of methods){all(node,n=>{
 if(ts.isCallExpression(n)&&n.expression.getText(engine)==='this.ledger.transaction'){
  transactionCallbacks++;const cb=n.arguments[0];assert(ts.isArrowFunction(cb));assert(!(cb.modifiers??[]).some(m=>m.kind===ts.SyntaxKind.AsyncKeyword));let awaits=0;all(cb,c=>{if(ts.isAwaitExpression(c))awaits++;});assert.equal(awaits,0);
 }
 if(ts.isCallExpression(n)&&n.expression.getText(engine)==='this.acceptTime')acceptSites.push({method,line:engine.getLineAndCharacterOfPosition(n.getStart(engine)).line+1});
});}
assert.equal(acceptSites.length,7);assert.deepEqual(acceptSites.map(x=>x.method),['command','prepare','finalCheck','accept','claim','claim','report']);
const prospective=claim.body.statements.find(n=>ts.isVariableStatement(n)&&n.declarationList.declarations.some(d=>d.name.getText(engine)==='prospective')).declarationList.declarations[0].initializer.arguments[0].body.statements.at(-1).expression;
assert(ts.isObjectLiteralExpression(prospective));const captured=prospective.properties.map(p=>p.name.getText(engine));assert.deepEqual(captured,['operation_id','binding','binding_hash','epoch','revision','owner','expiry_us','provider_kind','provider_key','instance_id','boot_id','claim_id']);
const lock=JSON.parse(await readFile(join(project,'package-lock.json'),'utf8')),inventory=JSON.parse(await readFile(join(project,'THIRD_PARTY.yml'),'utf8'));const packages=new Map(inventory.packages.map(p=>[p.lockPath,p]));assert.equal(packages.size,58);let installed=0;
for(const [path,value]of Object.entries(lock.packages))if(path){const entry=packages.get(path);assert(entry);for(const key of ['version','license','resolved','integrity'])assert.equal(entry[key],value[key]);assert(entry.purpose.trim());assert.equal(entry.scope,'development-only');assert.equal(entry.installScriptsExecuted,false);try{const actual=JSON.parse(await readFile(join(project,path,'package.json'),'utf8'));assert.equal(actual.version,value.version);installed++;}catch(error){if(error.code!=='ENOENT')throw error;}}
const report={status:'passed',scope:'independent-production-AST-and-claim-linearization-static-review-only',source_tree_sha256:binding.source_tree_sha256,production_files:files,production_externals:[...externals],transaction_callbacks_synchronous:transactionCallbacks,final_claim_awaits:finalAwaits,captured_identity_fields:captured,accepted_time_sites:acceptSites,engine_source_sha256:bytesHash(engineBytes),locked_entries:packages.size,installed_package_versions_checked:installed,authorizationGate:false};await writeFile(join(out,'ast-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
